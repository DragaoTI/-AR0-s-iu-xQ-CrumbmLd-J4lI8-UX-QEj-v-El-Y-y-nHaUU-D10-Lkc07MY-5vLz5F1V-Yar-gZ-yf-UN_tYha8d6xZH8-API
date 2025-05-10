from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm # Usa form-data, não JSON
from app.auth.schemas import Token, UserLoginSchema, RefreshTokenRequest
from app.schemas.user_schemas import UserCreate, UserResponse
from app.services.supabase_service import supabase_service
from app.services.geoip_service import get_geoip_data
from app.schemas.geo_log_schemas import GeoLogCreate
from app.auth.jwt_handler import create_access_token, create_refresh_token, verify_token
from app.models.user import User
from app.auth.dependencies import get_current_active_user
from app.utils.rate_limiter import limiter
from app.core.config import settings # Para RATE_LIMIT_LOGIN_ATTEMPTS
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour") # Limite para registro
async def register_user(request: Request, user_in: UserCreate):
    existing_user = await supabase_service.get_user_by_email(user_in.email) # Verifica se já existe
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    new_user = await supabase_service.create_user(user_in)
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user in Supabase",
        )
    return new_user


# Se quiser usar JSON para login em vez de form-data:
@router.post("/login/json", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN_ATTEMPTS) # Aplicar rate limit específico para login
async def login_for_access_token_json(
    request: Request, # Necessário para o rate limiter pegar o IP e para GeoIP
    form_data: UserLoginSchema # Nosso schema Pydantic para JSON
):
    user = await supabase_service.login_user(email=form_data.email, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    # Log GeoIP
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    if ip_address != "unknown":
        geoip_data = await get_geoip_data(ip_address)
        if geoip_data:
            log_entry = GeoLogCreate(
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                country=geoip_data.get("country_name"),
                city=geoip_data.get("city")
            )
            await supabase_service.add_geo_log(log_entry)
        else:
            # Log básico mesmo sem GeoIP detalhado
            log_entry = GeoLogCreate(user_id=user.id, ip_address=ip_address, user_agent=user_agent)
            await supabase_service.add_geo_log(log_entry)


    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Incluir 'role' no payload do token de acesso
    access_token_payload = {"sub": str(user.id), "role": user.role}
    
    access_token = create_access_token(
        data=access_token_payload, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}, expires_delta=refresh_token_expires # Refresh token não precisa de role
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# Rota de login padrão com OAuth2PasswordRequestForm (espera form-data)
@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN_ATTEMPTS)
async def login_for_access_token_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # Reutiliza a lógica do login JSON
    user_login_schema = UserLoginSchema(email=form_data.username, password=form_data.password)
    return await login_for_access_token_json(request, user_login_schema)


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute") # Limite para refresh
async def refresh_access_token(request: Request, token_request: RefreshTokenRequest):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_token(token_request.refresh_token, credentials_exception)

    if not token_data or token_data.token_type != "refresh" or token_data.user_id is None:
        raise credentials_exception

    user = await supabase_service.get_user_by_id(uuid.UUID(token_data.user_id))
    if not user or not user.is_active:
        raise credentials_exception

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Incluir 'role' no novo token de acesso
    access_token_payload = {"sub": str(user.id), "role": user.role}
    
    new_access_token = create_access_token(
        data=access_token_payload, expires_delta=access_token_expires
    )
    # O refresh token original pode ser reutilizado ou um novo pode ser gerado.
    # Para simplificar, reutilizamos o que foi enviado se ainda for válido,
    # ou o cliente precisaria de um novo refresh_token também.
    # Para maior segurança, um novo refresh token deve ser gerado e o antigo invalidado (mais complexo).
    return {"access_token": new_access_token, "refresh_token": token_request.refresh_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    # O UserResponse precisa do campo 'role'
    # O objeto User que vem de get_current_active_user já deve ter a role
    # print(f"User /me: ID={current_user.id}, Email={current_user.email}, Role={current_user.role}")
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        role=current_user.role
    )
