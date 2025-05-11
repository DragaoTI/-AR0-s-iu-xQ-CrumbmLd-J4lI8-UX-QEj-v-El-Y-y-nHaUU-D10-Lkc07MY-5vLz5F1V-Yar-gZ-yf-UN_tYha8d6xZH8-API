# app/core/logging_middleware.py
import time
import json
from typing import Optional, Any, Dict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send, RequestResponseCallNext
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from jose import jwt, JWTError

# Importar supabase_service diretamente pode causar problemas de importação circular
# se ele, por sua vez, importar algo que depende da aplicação FastAPI (que usa este middleware).
# Uma solução mais robusta seria usar um sistema de logging desacoplado ou
# passar a função de salvar log via dependência/configuração.
# Por ora, vamos tentar a importação direta, mas esteja ciente.
# from app.services.supabase_service import supabase_service # << CUIDADO COM IMPORT CIRCULAR
# Alternativa: Obter o cliente Supabase do request.app.state se você o armazenar lá na inicialização.

from app.core.config import settings
# Assumindo que você tem algo assim para os diferentes algoritmos/chaves de token se forem diferentes
# Se forem iguais, você só precisa de um.
ADMIN_JWT_ALGORITHM = getattr(settings, 'ADMIN_JWT_ALGORITHM', settings.JWT_ALGORITHM)
USER_JWT_ALGORITHM = settings.JWT_ALGORITHM # Para tokens de usuário normal

# Função auxiliar para tentar obter o corpo do request de forma segura
async def get_request_body_for_log(request: Request) -> Optional[Dict[str, Any]]:
    try:
        # Tenta ler o corpo. Importante: request.body() só pode ser chamado uma vez.
        # Se o endpoint precisa do corpo, ele não estará mais disponível.
        # FastAPI geralmente lida com isso "rebobinando" o stream para o endpoint.
        # Mas em um middleware, isso é mais arriscado.
        # Se você realmente precisa do corpo aqui, considere as implicações.
        # Para JSON, FastAPI já terá parseado, mas o middleware roda antes.
        # Por segurança e simplicidade, vamos omitir o corpo da requisição por enquanto.
        # Se você precisar, pesquise sobre como ler e repassar o corpo em middlewares Starlette/FastAPI.
        # body = await request.body()
        # if body:
        #     try:
        #         # Tenta decodificar como JSON se for o caso
        #         if "application/json" in request.headers.get("content-type", ""):
        #             return json.loads(body.decode())
        #         # Poderia adicionar lógica para outros tipos ou apenas retornar a string truncada
        #         return {"raw_body_preview": body.decode(errors='ignore')[:250]} # Preview truncado
        #     except Exception:
        #         return {"raw_body_preview": body.decode(errors='ignore')[:250]}
        return None # Omitindo por padrão
    except Exception:
        return {"error": "Failed to read request body for logging"}


def get_id_from_token(token_str: Optional[str], key: str, algorithm: str) -> Optional[str]:
    if not token_str:
        return None
    try:
        if token_str.startswith("Bearer "):
            token_str = token_str.split("Bearer ", 1)[1]
        
        payload = jwt.decode(token_str, key, algorithms=[algorithm], options={"verify_aud": False}) # verify_aud: False se não usar audience
        return payload.get("sub") 
    except JWTError:
        # print(f"DEBUG LOGGING: JWTError ao decodificar token para log: {token_str[:20]}...")
        return None
    except Exception as e:
        # print(f"DEBUG LOGGING: Exceção ao decodificar token para log: {e}")
        return None


class ApiLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Não inicialize supabase_service aqui para evitar múltiplas instâncias
        # ou dependências de inicialização complexas.

    async def dispatch(self, request: Request, call_next: RequestResponseCallNext) -> Response:
        start_time = time.time()
        
        # O corpo da requisição é complexo de logar em middleware sem consumi-lo.
        # Deixaremos request_body_log como None por agora.
        request_body_log = None 
        response = None
        status_code = 500 # Default em caso de erro antes da resposta ser formada
        process_time = 0
        error_in_app_message = None

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            status_code = response.status_code
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            # O ErrorMiddleware do FastAPI/Starlette deve lidar com a formatação da resposta de erro.
            # Aqui, apenas capturamos o fato de que ocorreu um erro para o log.
            error_in_app_message = str(e)
            # É crucial re-levantar a exceção para que os handlers de erro do FastAPI funcionem.
            # Se não re-levantarmos, o cliente pode receber uma resposta inesperada ou nenhuma.
            # A resposta será formada pelo ErrorMiddleware.
            # No entanto, para o log, já temos o status_code = 500 (inicial).
            # Se o ErrorMiddleware mudar o status_code, esse log pode não refletir o final.
            # Uma forma mais avançada seria ter outro middleware "externo" para capturar o status final.
            # Por ora, vamos assumir que a exceção será tratada e logaremos 500.
            print(f"ERRO NA APLICAÇÃO (Middleware): {e}") # Logar o erro aqui também
            raise e # Re-levanta a exceção

        # Tentativa de obter ID do usuário/admin
        user_id_from_token: Optional[str] = None
        admin_id_from_token: Optional[str] = None
        auth_header = request.headers.get("authorization")

        if auth_header:
            # Tenta como token de admin
            admin_id_from_token = get_id_from_token(auth_header, settings.JWT_PUBLIC_KEY_CONTENT, ADMIN_JWT_ALGORITHM)
            if not admin_id_from_token:
                # Se não for admin, tenta como token de usuário
                user_id_from_token = get_id_from_token(auth_header, settings.JWT_PUBLIC_KEY_CONTENT, USER_JWT_ALGORITHM)
        
        log_entry = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "client_host": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent"),
            "user_id": user_id_from_token,
            "admin_id": admin_id_from_token,
            "request_body": request_body_log, # Omitido por padrão, pode ser muito grande/sensível
            # "response_body": None, # Omitido, difícil de capturar de forma confiável aqui
            "processing_time_ms": round(process_time, 2),
            "error_message": error_in_app_message,
            "tags": ["api_request"]
        }
        
        # Adicionar tags baseadas no path
        path_for_tags = request.url.path
        if path_for_tags.startswith(f"{settings.API_V1_STR}/admin-panel"):
            log_entry["tags"].append("admin_panel_api")
        elif path_for_tags.startswith(f"{settings.API_V1_STR}/auth"):
            log_entry["tags"].append("user_auth_api")
        elif path_for_tags.startswith(f"{settings.API_V1_STR}/4L8FJYy4eWGL_admin"): # Seu admin router original
             log_entry["tags"].append("original_admin_api")


        if status_code >= 500:
            log_entry["tags"].append("error_server")
        elif status_code >= 400:
            log_entry["tags"].append("error_client")
        
        # Salvar o log no Supabase
        # Esta operação deve ser rápida e não bloquear. Idealmente, async ou em background task.
        try:
            # Importar supabase_service aqui para tentar evitar problemas de importação circular na inicialização
            # e para garantir que a instância já foi criada.
            from app.services.supabase_service import supabase_service
            
            if supabase_service and supabase_service.client:
                # Converter UUIDs para string se eles forem objetos UUID, pois o Supabase client espera strings para colunas UUID
                if log_entry.get("user_id") and not isinstance(log_entry["user_id"], (str, type(None))):
                    log_entry["user_id"] = str(log_entry["user_id"])
                if log_entry.get("admin_id") and not isinstance(log_entry["admin_id"], (str, type(None))):
                    log_entry["admin_id"] = str(log_entry["admin_id"])
                
                # Garantir que campos JSONB sejam None se não houver dados
                if log_entry.get("request_body") is None: log_entry["request_body"] = None 
                # if log_entry.get("response_body") is None: log_entry["response_body"] = None


                # Executar a inserção de forma assíncrona, mas não esperar aqui para não bloquear a resposta
                # Isso requer uma maneira de executar tarefas em segundo plano com FastAPI/Starlette
                # Exemplo simples (não ideal para alta carga, mas funciona):
                # asyncio.create_task(supabase_service.client.table("api_logs").insert(log_entry).execute())
                
                # Para este exemplo, vamos fazer de forma "síncrona" dentro do async dispatch,
                # mas o cliente Supabase é assíncrono.
                # print(f"DEBUG LOGGING: Preparando para salvar log: {log_entry}")
                await supabase_service.client.table("api_logs").insert(log_entry).execute()
                # print(f"DEBUG LOGGING: Log da API salvo (ou tentativa).")
            else:
                print("AVISO DE LOGGING: Cliente Supabase (via supabase_service) não disponível, log da API não será salvo.")
        except Exception as log_e:
            print(f"ERRO CRÍTICO AO SALVAR LOG DA API: {log_e}")
            import traceback
            traceback.print_exc()
            # Não deixar que um erro de logging quebre a requisição principal para o cliente

        return response
