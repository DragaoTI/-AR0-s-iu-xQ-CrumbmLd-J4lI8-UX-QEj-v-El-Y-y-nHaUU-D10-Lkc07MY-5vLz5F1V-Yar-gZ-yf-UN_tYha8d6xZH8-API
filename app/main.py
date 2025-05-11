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
from app.core.logging_middleware import ApiLoggingMiddleware

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_ADMIN_DIR = BASE_DIR / "admin_frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"INFO:     Aplicação '{settings.APP_NAME}' iniciando...")
    yield
    print(f"INFO:     Aplicação '{settings.APP_NAME}' finalizando...")

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://four3nuihgv7834hgv783h8fvhn2847nrv8h3hn7.onrender.com", # Sua URL de produção
        "http://localhost", # Para desenvolvimento local do frontend em qualquer porta
        "http://localhost:8000", # Se você rodar o frontend em localhost:8000
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        # Adicione outras origens se necessário, mas seja restrito em produção.
        # "*" NÃO é recomendado para produção.
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], # Métodos específicos
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"], # Headers específicos
)

# Headers de segurança básicos (X-Content-Type-Options e X-Frame-Options)
# Para CSP e HSTS, um middleware mais robusto ou configurações no nível do proxy/CDN são ideais.
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    # response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; ..." # Exemplo, configure corretamente!
    if request.url.scheme == "https":
         response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if FRONTEND_ADMIN_DIR.is_dir():
    print(f"INFO:     Montando UI do Admin em /admin-ui de: {FRONTEND_ADMIN_DIR}")
    app.mount("/x9A7uQvP2LmZn53BqC", StaticFiles(directory=FRONTEND_ADMIN_DIR, html=True), name="x9A7uQvP2LmZn53BqC-admin")

    @app.get("/x9A7uQvP2LmZn53BqC-adm", include_in_schema=False)
    async def redirect_to_admin_login_page():
        return RedirectResponse(url="/x9A7uQvP2LmZn53BqC/admin_login.html", status_code=301) # 301 para redirecionamento permanente
    print("INFO:     Rota de redirecionamento /painel-admin configurada.")
else:
    print(f"AVISO:    Diretório UI do Admin NÃO ENCONTRADO em '{FRONTEND_ADMIN_DIR}'. UI não será servida.")
    print(f"          Caminho base do projeto detectado: {BASE_DIR}")

app.add_middleware(CORSMiddleware) 
app.add_middleware(ApiLoggingMiddleware)
app.include_router(auth_router.router, prefix=settings.API_V1_STR)
app.include_router(admin_router.router, prefix=settings.API_V1_STR)
app.include_router(admin_panel_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": f"Bem-vindo à API: {settings.APP_NAME}"}

@app.get(f"{settings.API_V1_STR}/protected-data", tags=["Protected"])
async def get_protected_data(current_user: UserModel = Depends(get_current_active_user)):
    return {
        "message": "Estes são dados protegidos!",
        "user_email": current_user.email,
        "user_id": current_user.id,
        "user_role": current_user.role
    }

# Adicionar um health check endpoint simples
@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}
