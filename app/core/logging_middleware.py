# app/core/logging_middleware.py
import time
import json
from typing import Optional, Any, Dict, Callable, Awaitable

try:
    from starlette.middleware.base import BaseHTTPMiddleware, DispatchFunction
    CALL_NEXT_TYPE = DispatchFunction
except ImportError:
    CALL_NEXT_TYPE = Callable[[Request], Awaitable[Response]]
    from starlette.middleware.base import BaseHTTPMiddleware

from starlette.types import ASGIApp
from starlette.requests import Request
from starlette.responses import Response
from jose import jwt, JWTError

from app.core.config import settings
ADMIN_JWT_ALGORITHM = getattr(settings, 'ADMIN_JWT_ALGORITHM', settings.JWT_ALGORITHM)
USER_JWT_ALGORITHM = settings.JWT_ALGORITHM


async def get_request_body_for_log(request: Request) -> Optional[Dict[str, Any]]:
    # Omitindo a leitura real do corpo para evitar consumir o stream e por segurança/simplicidade
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
    except Exception:
        return None


class ApiLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: CALL_NEXT_TYPE) -> Response:
        start_time = time.time()
        
        request_body_log = await get_request_body_for_log(request)
        response: Optional[Response] = None 
        status_code_for_log = 500 
        process_time = 0.0
        error_in_app_message: Optional[str] = None

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            status_code_for_log = response.status_code
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            error_in_app_message = str(e)
            status_code_for_log = 500 
            print(f"ERRO NA APLICAÇÃO DURANTE REQUEST (Middleware): {e} para {request.method} {request.url.path}")
            raise e 

        if response is None: # Cenário de fallback improvável
            print(f"AVISO: Nenhuma resposta foi gerada por call_next para {request.method} {request.url.path}. Retornando 500.")
            response = Response("Internal server error after middleware processing.", status_code=500)
            status_code_for_log = 500
            if not error_in_app_message: error_in_app_message = "No response from application stack."

        user_id_from_token: Optional[str] = None
        admin_id_from_token: Optional[str] = None
        auth_header = request.headers.get("authorization")

        if auth_header:
            admin_id_from_token = get_id_from_token(auth_header, settings.JWT_PUBLIC_KEY_CONTENT, ADMIN_JWT_ALGORITHM)
            if not admin_id_from_token:
                user_id_from_token = get_id_from_token(auth_header, settings.JWT_PUBLIC_KEY_CONTENT, USER_JWT_ALGORITHM)
        
        log_entry: Dict[str, Any] = {
            "method": request.method, "path": request.url.path, "status_code": status_code_for_log,
            "client_host": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent"), "user_id": user_id_from_token,
            "admin_id": admin_id_from_token, "request_body": request_body_log, 
            "processing_time_ms": round(process_time, 2), "error_message": error_in_app_message,
            "tags": ["api_request"]
        }
        
        path_for_tags = request.url.path
        if path_for_tags.startswith(f"{settings.API_V1_STR}/admin-panel"): log_entry["tags"].append("admin_panel_api")
        elif path_for_tags.startswith(f"{settings.API_V1_STR}/auth"): log_entry["tags"].append("user_auth_api")
        elif path_for_tags.startswith(f"{settings.API_V1_STR}/4L8FJYy4eWGL_admin"): log_entry["tags"].append("original_admin_api")

        if status_code_for_log >= 500: log_entry["tags"].append("error_server")
        elif status_code_for_log >= 400: log_entry["tags"].append("error_client")
        
        try:
            from app.services.supabase_service import supabase_service # Importar aqui para tentar mitigar startup issues
            
            if supabase_service and supabase_service.client:
                current_user_id = log_entry.get("user_id")
                if current_user_id and not isinstance(current_user_id, str): log_entry["user_id"] = str(current_user_id)
                elif current_user_id is None: log_entry["user_id"] = None
                current_admin_id = log_entry.get("admin_id")
                if current_admin_id and not isinstance(current_admin_id, str): log_entry["admin_id"] = str(current_admin_id)
                elif current_admin_id is None: log_entry["admin_id"] = None
                if log_entry.get("request_body") is None: log_entry["request_body"] = None 
                
                print(f"DEBUG LOGGING - Payload para Inserção em api_logs: {json.dumps(log_entry, default=str)}")
                
                # REMOVIDO 'await' DA LINHA ABAIXO
                supabase_service.client.table("api_logs").insert(log_entry).execute()
            else:
                print("AVISO DE LOGGING: Cliente Supabase não disponível, log da API não será salvo.")
        except Exception as log_e:
            print(f"ERRO CRÍTICO AO SALVAR LOG DA API: {log_e}")
            if hasattr(log_e, 'message') and log_e.message: print(f"   Detalhe do APIError (se houver): {log_e.message}")
            if hasattr(log_e, 'hint') and log_e.hint: print(f"   Dica do APIError (se houver): {log_e.hint}")
            if hasattr(log_e, 'details') and log_e.details: print(f"   Detalhes adicionais do APIError (se houver): {log_e.details}")
            import traceback
            traceback.print_exc()
        return response
