from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
import os

from app.core.config import settings
from app.routers import auth_router, admin_router
from app.routers.admin_panel_router import admin_panel_router
from app.utils.rate_limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from contextlib import asynccontextmanager
from app.auth.dependencies import get_current_active_user
from app.models.user import User as UserModel
from app.core.logging_middleware import ApiLoggingMiddleware # << NOVO IMPORT

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_ADMIN_DIR = BASE_DIR / "admin_frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"INFO:     Aplicação '{settings.APP_NAME}' iniciando...")
    # Verificar se supabase_service e admin_service_instance foram inicializados
    # Isso acontece quando app.services é importado, o que ocorre antes do lifespan
    # se os routers que os usam são importados globalmente.
    # from app.services import supabase_service, admin_service_instance # Para checagem
    # if not supabase_service or not supabase_service.client:
    #     print("ALERTA LIFESPAN: Supabase service client não parece estar inicializado!")
    # if not admin_service_instance:
    #     print("ALERTA LIFESPAN: Admin service instance não parece estar inicializado!")
    yield
    print(f"INFO:     Aplicação '{settings.APP_NAME}' finalizando...")

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Ordem dos Middlewares é importante:
# 1. Error handling (implícito ou explícito)
# 2. CORS
# 3. Outros middlewares (como o de logging, segurança de headers)
# 4. Middleware de Autenticação (se não for por dependência)

# Adicionado primeiro o middleware de logging para capturar o máximo possível.
# No entanto, se um middleware anterior (como CORS) rejeitar a requisição,
# o middleware de logging pode não capturar a resposta final.
# Considere a ordem baseada no que você quer logar.
# Se o logging vier depois do CORS, ele pegará os headers CORS na resposta.
app.add_middleware(ApiLoggingMiddleware) # << ADICIONADO AQUI (ou depois do CORS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://four3nuihgv7834hgv783h8fvhn2847nrv8h3hn7.onrender.com",
        "http://localhost",
        "http://localhost:8000", # Comum para desenvolvimento local do frontend
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

@app.middleware("http")
async def add_security_headers_basic(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.scheme == "https":
         response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # CSP é complexa e melhor configurada com mais granularidade,
    # ou através de um gateway/CDN se possível.
    # response.headers["Content-Security-Policy"] = "default-src 'self'; ..." 
    return response

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if FRONTEND_ADMIN_DIR.is_dir():
    print(f"INFO:     Montando UI do Admin em /x9A7uQvP2LmZn53BqC de: {FRONTEND_ADMIN_DIR}")
    app.mount("/x9A7uQvP2LmZn53BqC", StaticFiles(directory=FRONTEND_ADMIN_DIR, html=True), name="admin_frontend_static_files") # Nome único

    @app.get("/painel-admin", include_in_schema=False)
    async def redirect_to_admin_login_page_main(): # Nome único para a função
        return RedirectResponse(url="/x9A7uQvP2LmZn53BqC/admin_login.html", status_code=301)
    print("INFO:     Rota de redirecionamento /painel-admin configurada.")
else:
    print(f"AVISO:    Diretório UI do Admin NÃO ENCONTRADO em '{FRONTEND_ADMIN_DIR}'. UI não será servida.")
    print(f"          Caminho base do projeto detectado: {BASE_DIR}")

app.include_router(auth_router.router, prefix=settings.API_V1_STR)
app.include_router(admin_router.router, prefix=settings.API_V1_STR) # Seu router admin original
app.include_router(admin_panel_router, prefix=settings.API_V1_STR) # API para o painel visual

@app.get("/", tags=["Root"])
async def read_root_main(): # Nome único
    return {"message": f"Bem-vindo à API: {settings.APP_NAME}"}

@app.get(f"{settings.API_V1_STR}/protected-data", tags=["Protected"])
async def get_protected_data_main(current_user: UserModel = Depends(get_current_active_user)): # Nome único
    return {
        "message": "Estes são dados protegidos!",
        "user_email": current_user.email,
        "user_id": current_user.id,
        "user_role": current_user.role
    }

@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
async def health_check_main(): # Nome único
    return {"status": "ok"}
