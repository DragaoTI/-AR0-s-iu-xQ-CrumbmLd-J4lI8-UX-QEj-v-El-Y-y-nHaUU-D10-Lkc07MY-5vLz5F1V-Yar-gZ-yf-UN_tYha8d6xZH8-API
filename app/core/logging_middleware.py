# app/core/logging_middleware.py
import time
import json
from typing import Optional, Any, Dict, Callable, Awaitable # Adicionado Callable, Awaitable

# Tentar importar DispatchFunction que é mais específico para call_next
try:
    from starlette.middleware.base import BaseHTTPMiddleware, DispatchFunction
    CALL_NEXT_TYPE = DispatchFunction
except ImportError:
    # Fallback para uma tipagem mais genérica se DispatchFunction não estiver disponível
    # (comum em versões muito recentes ou muito antigas do Starlette)
    CALL_NEXT_TYPE = Callable[[Request], Awaitable[Response]]
    from starlette.middleware.base import BaseHTTPMiddleware


from starlette.types import ASGIApp # Receive, Scope, Send não são diretamente usados aqui
from starlette.requests import Request
from starlette.responses import Response
from jose import jwt, JWTError

from app.core.config import settings
# Assegure que estas constantes sejam definidas se você usar JWTs diferentes para admin e user
ADMIN_JWT_ALGORITHM = getattr(settings, 'ADMIN_JWT_ALGORITHM', settings.JWT_ALGORITHM)
USER_JWT_ALGORITHM = settings.JWT_ALGORITHM


# Funções auxiliares (get_request_body_for_log, get_id_from_token)
# Essas funções permanecem como antes, assumindo que estão corretas.
async def get_request_body_for_log(request: Request) -> Optional[Dict[str, Any]]:
    # Omitindo a leitura real do corpo para evitar consumir o stream
    return None 

def get_id_from_token(token_str: Optional[str], key: str, algorithm: str) -> Optional[str]:
    if not token_str:
        return None
    try:
        if token_str.startswith("Bearer "):
            token_str = token_str.split("Bearer ", 1)[1]
        
        payload = jwt.decode(token_str, key, algorithms=[algorithm], options={"verify_aud": False})
        return payload.get("sub") 
    except JWTError:
        return None
    except Exception: # Captura mais genérica para outras possíveis falhas de decodificação
        return None


class ApiLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: CALL_NEXT_TYPE) -> Response:
        start_time = time.time()
        
        request_body_log = await get_request_body_for_log(request) # Chamada da função
        response: Optional[Response] = None # Inicializa response como Optional[Response]
        status_code_for_log = 500 # Default em caso de erro antes da resposta ser formada
        process_time = 0.0
        error_in_app_message: Optional[str] = None

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            status_code_for_log = response.status_code
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            error_in_app_message = str(e)
            # Log do erro aqui, pois a resposta pode não ser formada pelo logging se a exceção for re-levantada e tratada por outro middleware
            print(f"ERRO NA APLICAÇÃO DURANTE REQUEST (Middleware): {e} para {request.method} {request.url.path}")
            # A exceção será re-levantada para que o FastAPI/Starlette a trate e retorne uma resposta de erro adequada.
            # O status_code_for_log permanecerá 500 ou o que o ErrorMiddleware do FastAPI definir.
            # O middleware de erro do FastAPI tipicamente define o status_code da resposta.
            # Se pudéssemos interceptar a resposta APÓS o error middleware, seria mais preciso.
            # Para este middleware, se uma exceção ocorre em call_next, é difícil saber o status code final
            # que será enviado ao cliente sem adicionar outro middleware "externo".
            # Vamos assumir 500 para o log se a exceção propagar para fora daqui.
            status_code_for_log = 500 # Mantém 500 como indicativo de erro interno
            raise e # Re-levanta a exceção

        # Garantir que temos um objeto Response para retornar
        if response is None:
            # Isso só aconteceria se call_next não retornasse ou levantasse uma exceção inesperada
            # que não foi pega acima (muito improvável com a estrutura try/except/raise).
            # Para segurança, criamos uma resposta de erro genérica.
            print(f"AVISO: Nenhuma resposta foi gerada por call_next para {request.method} {request.url.path}. Retornando 500.")
            response = Response("Internal server error after middleware processing.", status_code=500)
            status_code_for_log = 500 # Confirma o status
            if not error_in_app_message: error_in_app_message = "No response from application stack."


        user_id_from_token: Optional[str] = None
        admin_id_from_token: Optional[str] = None
        auth_header = request.headers.get("authorization")

        if auth_header:
            admin_id_from_token = get_id_from_token(auth_header, settings.JWT_PUBLIC_KEY_CONTENT, ADMIN_JWT_ALGORITHM)
            if not admin_id_from_token:
                user_id_from_token = get_id_from_token(auth_header, settings.JWT_PUBLIC_KEY_CONTENT, USER_JWT_ALGORITHM)
        
        log_entry: Dict[str, Any] = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code_for_log, # Usa o status_code capturado
            "client_host": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent"),
            "user_id": user_id_from_token,
            "admin_id": admin_id_from_token,
            "request_body": request_body_log, 
            "processing_time_ms": round(process_time, 2),
            "error_message": error_in_app_message,
            "tags": ["api_request"]
        }
        
        path_for_tags = request.url.path
        if path_for_tags.startswith(f"{settings.API_V1_STR}/admin-panel"):
            log_entry["tags"].append("admin_panel_api")
        elif path_for_tags.startswith(f"{settings.API_V1_STR}/auth"):
            log_entry["tags"].append("user_auth_api")
        elif path_for_tags.startswith(f"{settings.API_V1_STR}/4L8FJYy4eWGL_admin"):
             log_entry["tags"].append("original_admin_api")

        if status_code_for_log >= 500:
            log_entry["tags"].append("error_server")
        elif status_code_for_log >= 400:
            log_entry["tags"].append("error_client")
        
        try:
            from app.services.supabase_service import supabase_service
            
            if supabase_service and supabase_service.client:
                # Conversão para string se forem UUIDs
                if log_entry.get("user_id") and not isinstance(log_entry["user_id"], (str, type(None))):
                    log_entry["user_id"] = str(log_entry["user_id"])
                if log_entry.get("admin_id") and not isinstance(log_entry["admin_id"], (str, type(None))):
                    log_entry["admin_id"] = str(log_entry["admin_id"])
                
                # Remover campos que são None antes de inserir, se a tabela não os aceitar explicitamente como NULL
                # (O Supabase Python client geralmente lida bem com None para campos que permitem NULL)
                # clean_log_entry = {k: v for k, v in log_entry.items() if v is not None}
                # Usaremos log_entry diretamente, pois definimos os campos como Optional na tabela/schema.
                
                print(f"DEBUG LOGGING: Preparando para salvar log: { {k: v for k,v in log_entry.items() if k != 'request_body'} }") # Evita logar body no console
                await supabase_service.client.table("api_logs").insert(log_entry).execute()
            else:
                print("AVISO DE LOGGING: Cliente Supabase não disponível, log da API não será salvo.")
        except Exception as log_e:
            print(f"ERRO CRÍTICO AO SALVAR LOG DA API: {log_e}")
            # Não re-levanta a exceção de logging para não quebrar a resposta principal ao cliente
            import traceback
            traceback.print_exc()

        return response
