from fastapi import FastAPI, Request, HTTPException, Depends # Depends foi adicionado
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import auth_router, admin_router
from app.utils.rate_limiter import limiter # Assegure-se que _rate_limit_exceeded_handler está em rate_limiter.py ou importe-o
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler # Importação direta do handler padrão se for o caso
from contextlib import asynccontextmanager
from app.auth.dependencies import get_current_active_user # Para a rota protegida
from app.models.user import User as UserModel # Renomeado para evitar conflito, como você já tinha

# Gerenciador de contexto para inicialização/finalização
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código de inicialização (ex: conectar ao DB se não for por request, carregar modelos ML)
    print("Aplicação iniciando...")
    # Inicializar Supabase Client aqui se preferir uma única instância global,
    # mas a SupabaseService já cria um por instância dela.
    yield
    # Código de finalização (ex: fechar conexões)
    print("Aplicação finalizando...")


app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan # Para FastAPI >= 0.93.0
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # ATENÇÃO: Em produção, especifique os domínios permitidos! Ex: ["https://seufrontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adiciona o state do limiter e o handler de exceção
app.state.limiter = limiter
# Se _rate_limit_exceeded_handler é uma função customizada em app.utils.rate_limiter:
# from app.utils.rate_limiter import _rate_limit_exceeded_handler
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# Se for usar o handler padrão do slowapi:
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) # Usando o importado de slowapi


# Routers
app.include_router(auth_router.router, prefix=settings.API_V1_STR)
app.include_router(admin_router.router, prefix=settings.API_V1_STR) # Já tem /admin no prefixo do router

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": f"Bem-vindo à {settings.APP_NAME}"}

# Rota protegida de exemplo
@app.get(f"{settings.API_V1_STR}/protected-data", tags=["Protected"])
async def get_protected_data(current_user: UserModel = Depends(get_current_active_user)):
    return {
        "message": "Estes são dados protegidos!",
        "user_email": current_user.email,
        "user_id": current_user.id,
        "user_role": current_user.role
    }
