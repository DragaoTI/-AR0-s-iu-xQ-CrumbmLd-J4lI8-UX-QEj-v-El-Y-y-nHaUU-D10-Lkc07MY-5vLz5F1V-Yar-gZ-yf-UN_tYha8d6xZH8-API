# app/core/logging_middleware.py
import time
import json
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseCallNext
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from jose import jwt, JWTError # Para tentar decodificar tokens e pegar IDs

from app.services.supabase_service import supabase_service # Para salvar o log
# Cuidado com importação circular se supabase_service importar algo que importa este middleware
# Idealmente, a função de salvar log poderia ser mais desacoplada.
from app.core.config import settings # Para chaves JWT, se necessário para decodificar
from app.auth.admin_jwt_handler import ADMIN_JWT_ALGORITHM # Se usar o mesmo algo
from app.auth.jwt_handler import JWT_ALGORITHM as USER_JWT_ALGORITHM # Para tokens de usuário normal

async def get_body_if_json(request: Request) -> Optional[dict]:
    content_type = request.headers.get("content-type")
    if content_type and "application/json" in content_type:
        try:
            return await request.json()
        except json.JSONDecodeError:
            return {"error": "Invalid JSON body"} # Ou apenas o corpo como string
    # Para outros content types, você pode tentar request.body() e decodificar
    return None # Ou uma representação em string

def get_user_id_from_token(token_str: str, key: str, algorithm: str) -> Optional[str]:
    if not token_str:
        return None
    try:
        if token_str.startswith("Bearer "):
            token_str = token_str.split("Bearer ")[1]
        
        payload = jwt.decode(token_str, key, algorithms=[algorithm])
        return payload.get("sub") # "sub" geralmente contém o user_id ou admin_id
    except JWTError:
        return None # Token inválido ou expirado
    except Exception:
        return None # Outro erro

class ApiLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Evite inicializar o cliente Supabase aqui para não criar múltiplas instâncias
        # Use a instância global supabase_service

    async def dispatch(self, request: Request, call_next: RequestResponseCallNext) -> Response:
        start_time = time.time()
        
        # Tentar ler o corpo da requisição (apenas se for JSON neste exemplo)
        # Ler o corpo aqui consome o stream. Se o endpoint também precisar ler,
        # precisamos de uma forma de "rebobinar" ou passar o corpo lido.
        # FastAPI lida com isso internamente para seus path operations,
        # mas para middleware é mais complexo.
        # Para simplificar, vamos obter o corpo de forma segura ou pular.
        # Uma forma mais segura é capturar o corpo na resposta (se o endpoint o incluir)
        # ou usar um request_body = await request.body() e depois recriar o stream se necessário.
        # Por ora, vamos focar no que é fácil de obter.
        
        # Para não consumir o corpo e quebrar o endpoint, não vamos ler o corpo aqui.
        # Os endpoints podem logar seus próprios corpos de requisição se necessário.
        request_body_log = None # Inicialmente None

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000  # em milissegundos
            status_code = response.status_code
            response_body_log = None # Inicialmente None

            # Tentar obter o corpo da resposta se for JSON e não for um stream
            # Isso pode ser pesado para respostas grandes.
            # if "application/json" in response.headers.get("content-type", ""):
            #     try:
            #         # Esta é uma forma de obter o corpo da resposta, mas é complexa
            #         # e pode interferir com o streaming.
            #         # Uma abordagem melhor seria o próprio endpoint logar sua resposta se necessário.
            #         pass 
            #     except Exception:
            #         response_body_log = {"error": "Could not parse response body for logging"}

        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            status_code = 500 # Erro interno do servidor
            response_body_log = {"error_in_app": str(e)}
            # Precisamos recriar uma resposta aqui se a exceção não foi tratada pelo FastAPI
            # Normalmente, o ErrorMiddleware do Starlette/FastAPI já faria isso.
            # Este bloco 'except' aqui é mais para capturar o tempo de processamento em caso de erro.
            raise e # Re-levanta a exceção para que o FastAPI a trate

        # Extrair user_id ou admin_id do token de autorização
        user_id = None
        admin_id = None
        auth_header = request.headers.get("authorization")
        if auth_header:
            # Tentar decodificar como token de admin primeiro
            temp_admin_id = get_user_id_from_token(auth_header, settings.JWT_PUBLIC_KEY_CONTENT, ADMIN_JWT_ALGORITHM)
            if temp_admin_id:
                admin_id = temp_admin_id
            else:
                # Se não for admin, tentar como token de usuário normal
                temp_user_id = get_user_id_from_token(auth_header, settings.JWT_PUBLIC_KEY_CONTENT, USER_JWT_ALGORITHM)
                if temp_user_id:
                    user_id = temp_user_id
        
        log_entry = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "client_host": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent"),
            "user_id": user_id,
            "admin_id": admin_id,
            # "request_body": request_body_log, # Omitido por simplicidade/segurança
            # "response_body": response_body_log, # Omitido por simplicidade/segurança
            "processing_time_ms": round(process_time, 2),
            "error_message": None, # Preencher se houver uma exceção específica
            "tags": ["api_request"] # Tag genérica
        }

        # Adicionar tags específicas
        if request.url.path.startswith(f"{settings.API_V1_STR}/admin-panel"):
            log_entry["tags"].append("admin_panel")
        elif request.url.path.startswith(f"{settings.API_V1_STR}/auth"):
            log_entry["tags"].append("user_auth")
        
        if status_code >= 500:
            log_entry["tags"].append("error")
            log_entry["tags"].append("critical") # Exemplo
        elif status_code >= 400:
            log_entry["tags"].append("error")
            log_entry["tags"].append("warning") # Exemplo

        # Salvar no Supabase
        # É importante que esta operação seja rápida e não bloqueie a resposta.
        # Idealmente, isso seria feito em uma tarefa de background.
        # Para este exemplo, faremos de forma síncrona (dentro do async).
        try:
            if supabase_service and supabase_service.client:
                # Convertendo UUIDs para string se eles forem objetos UUID
                if log_entry.get("user_id") and not isinstance(log_entry["user_id"], str):
                    log_entry["user_id"] = str(log_entry["user_id"])
                if log_entry.get("admin_id") and not isinstance(log_entry["admin_id"], str):
                    log_entry["admin_id"] = str(log_entry["admin_id"])

                await supabase_service.client.table("api_logs").insert(log_entry).execute()
            else:
                print("AVISO DE LOGGING: Cliente Supabase não disponível, log não será salvo.")
        except Exception as log_e:
            print(f"ERRO AO SALVAR LOG DA API: {log_e}")
            # Não deixar que um erro de logging quebre a requisição principal

        return response
