from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.schemas import Token, UserLoginSchema, RefreshTokenRequest # Supondo que estes schemas existem
from app.schemas.user_schemas import UserCreate, UserResponse
from app.services.supabase_service import supabase_service
from app.services.geoip_service import get_geoip_data
from app.schemas.geo_log_schemas import GeoLogCreate
from app.auth.jwt_handler import create_access_token, create_refresh_token, verify_token
from app.models.user import User
from app.auth.dependencies import get_current_active_user
from app.utils.rate_limiter import limiter
from app.core.config import settings
from datetime import timedelta, datetime, timezone
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour") # Limite para registro
async def register_user(request: Request, user_in: UserCreate):
    email_exists = await supabase_service.get_user_by_email_for_check(user_in.email)
    if email_exists:
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
    # Opcional: você pode querer logar o usuário e retornar tokens aqui
    # ou apenas retornar os dados do usuário e exigir um login separado.
    return new_user


@router.post("/login/json", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN_ATTEMPTS)
async def login_for_access_token_json(
    request: Request,
    form_data: UserLoginSchema
):
    user = await supabase_service.login_user(email=form_data.email, password=form_data.password)
    if not user or not user.id: # Checar se user e user.id são válidos
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
        log_entry_data = {
            "user_id": user.id,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
        if geoip_data:
            log_entry_data.update({
                "country": geoip_data.get("country_name"),
                "city": geoip_data.get("city"),
                "region": geoip_data.get("region"),
                "latitude": geoip_data.get("latitude"),
                "longitude": geoip_data.get("longitude"),
            })
        await supabase_service.add_geo_log(GeoLogCreate(**log_entry_data))


    access_token_expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token_payload = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(
        data=access_token_payload, expires_delta=access_token_expires_delta
    )
    
    raw_refresh_token, refresh_token_expires_at = create_refresh_token(
        data={"sub": str(user.id)}, expires_delta=refresh_token_expires_delta
    )

    stored_token_info = await supabase_service.store_refresh_token(
        user_id=user.id,
        token_str=raw_refresh_token,
        expires_at=refresh_token_expires_at
    )
    if not stored_token_info:
        print(f"AVISO: Falha ao armazenar refresh token para o usuário {user.id} durante o login.")
        # Decidir se isso deve ser um erro fatal para o login.
        # Por ora, permite o login, mas o refresh pode falhar.

    return {"access_token": access_token, "refresh_token": raw_refresh_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN_ATTEMPTS)
async def login_for_access_token_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user_login_schema = UserLoginSchema(email=form_data.username, password=form_data.password)
    return await login_for_access_token_json(request, user_login_schema)


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
async def refresh_access_token(request: Request, token_request: RefreshTokenRequest):
    client_refresh_token_str = token_request.refresh_token
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    auth_failed_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, # Usar 403 para falhas de autorização de token
        detail="Invalid or revoked refresh token",
    )

    # 1. Obter dados do token do banco de dados usando o HASH
    db_token_data = await supabase_service.get_refresh_token_data_by_hash(client_refresh_token_str)

    if not db_token_data:
        # print(f"Debug: /refresh - Token não encontrado no DB para o hash de: {client_refresh_token_str[:20]}...")
        raise auth_failed_exception

    db_token_id = uuid.UUID(db_token_data["id"])
    db_user_id_str = db_token_data["user_id"]

    # 2. Verificar se foi revogado
    if db_token_data.get("revoked"):
        # print(f"Debug: /refresh - Token (DB ID: {db_token_id}) está revogado.")
        # Medida de segurança: se um token revogado é usado, revogar toda a família de tokens descendentes.
        # Esta lógica pode ser mais complexa se você rastrear a cadeia de `parent_token_hash`.
        # Por simplicidade aqui, vamos apenas revogar todos os tokens do usuário se um revogado for usado.
        await supabase_service.revoke_all_user_refresh_tokens(uuid.UUID(db_user_id_str))
        raise auth_failed_exception

    # 3. Verificar se expirou
    expires_at_str = db_token_data.get("expires_at")
    if not expires_at_str: # Checagem de segurança
        # print(f"Debug: /refresh - Token (DB ID: {db_token_id}) não tem expires_at no DB.")
        await supabase_service.revoke_refresh_token(db_token_id)
        raise auth_failed_exception

    expires_at_utc = datetime.fromisoformat(expires_at_str).replace(tzinfo=timezone.utc)
    if expires_at_utc < datetime.now(timezone.utc):
        # print(f"Debug: /refresh - Token (DB ID: {db_token_id}) expirou em {expires_at_utc}.")
        await supabase_service.revoke_refresh_token(db_token_id) # Revoga o token expirado
        raise auth_failed_exception
        
    # 4. Validar o JWT do refresh token em si (opcional, mas bom para consistência)
    # Isto verifica a assinatura do token, expiração JWT (redundante com a do DB, mas ok), tipo, e 'sub'.
    try:
        jwt_payload = verify_token(client_refresh_token_str, credentials_exception) # Reutiliza verify_token
        if not jwt_payload or jwt_payload.token_type != "refresh" or jwt_payload.user_id != db_user_id_str:
            # print(f"Debug: /refresh - Payload JWT inválido ou não corresponde ao DB. JWT UserID: {jwt_payload.user_id if jwt_payload else 'N/A'}, DB UserID: {db_user_id_str}")
            await supabase_service.revoke_refresh_token(db_token_id)
            raise auth_failed_exception
    except HTTPException as e: # Captura a credentials_exception de verify_token
        # print(f"Debug: /refresh - verify_token falhou para o token do cliente: {e.detail}")
        await supabase_service.revoke_refresh_token(db_token_id)
        raise auth_failed_exception # Re-levanta a exceção com o detalhe apropriado

    # 5. Revogar o token antigo que foi usado (CRUCIAL para rotação segura)
    if not await supabase_service.revoke_refresh_token(db_token_id):
        print(f"ERRO CRÍTICO: Falha ao revogar o refresh token usado (DB ID: {db_token_id}) para o usuário {db_user_id_str}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token refresh process failed internally.")

    # 6. Obter dados do usuário para o novo token
    user = await supabase_service.get_user_by_id(uuid.UUID(db_user_id_str))
    if not user or not user.is_active:
        # print(f"Debug: /refresh - Usuário {db_user_id_str} não encontrado ou inativo.")
        # O usuário pode ter sido desativado/deletado. Não emitir novos tokens.
        raise auth_failed_exception # Ou credentials_exception

    # 7. Gerar novo access token
    new_access_token_expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token_payload = {"sub": str(user.id), "role": user.role}
    new_access_token = create_access_token(
        data=new_access_token_payload, expires_delta=new_access_token_expires_delta
    )

    # 8. Gerar novo refresh token (rotação)
    new_refresh_token_expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    new_raw_refresh_token, new_refresh_token_expires_at = create_refresh_token(
        data={"sub": str(user.id)}, expires_delta=new_refresh_token_expires_delta
    )

    # 9. Armazenar o novo refresh token no banco de dados
    new_stored_token_info = await supabase_service.store_refresh_token(
        user_id=user.id,
        token_str=new_raw_refresh_token,
        expires_at=new_refresh_token_expires_at,
        parent_token_str=client_refresh_token_str # Rastreia a origem
    )
    if not new_stored_token_info:
        print(f"ERRO CRÍTICO: Falha ao armazenar o NOVO refresh token para o usuário {user.id} durante o refresh.")
        # Neste ponto, o token antigo já foi revogado. O usuário ficará sem refresh token.
        # É uma situação ruim. Retornar erro 500.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store new refresh token.")

    # print(f"Debug: /refresh - Sucesso. Novo access token e refresh token emitidos para user {user.id}.")
    return {"access_token": new_access_token, "refresh_token": new_raw_refresh_token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute") # Ajustar limite conforme necessidade
async def logout_user(
    request: Request,
    token_request: Optional[RefreshTokenRequest] = None,
    current_user: Optional[User] = Depends(get_current_active_user) # Tornar opcional se quisermos permitir logout anônimo de um token específico
):
    """
    Revoga refresh tokens.
    - Se 'refresh_token' é fornecido no corpo, tenta revogar esse token específico.
      Isso permite que um cliente revogue um token mesmo que o access token associado tenha expirado.
    - Se 'refresh_token' não é fornecido E um usuário está autenticado (current_user),
      revoga todos os tokens ativos para esse usuário. (Logout de todas as sessões)
    """
    revoked_something = False
    if token_request and token_request.refresh_token:
        # print(f"Debug: /logout - Tentando revogar refresh token específico fornecido.")
        if await supabase_service.revoke_refresh_token_by_hash(token_request.refresh_token):
            revoked_something = True
            # print(f"Debug: /logout - Refresh token específico revogado com sucesso.")
        # else:
            # print(f"Debug: /logout - Falha ao revogar refresh token específico (pode já estar inválido/revogado).")
    
    elif current_user and current_user.id: # Se nenhum token específico foi dado, mas há um usuário logado
        # print(f"Debug: /logout - Tentando revogar todos os refresh tokens para o usuário {current_user.id}.")
        if await supabase_service.revoke_all_user_refresh_tokens(current_user.id):
            revoked_something = True
            # print(f"Debug: /logout - Todos os refresh tokens para o usuário {current_user.id} solicitados para revogação.")
        # else:
            # print(f"Debug: /logout - Falha ao solicitar revogação de todos os tokens para o usuário {current_user.id}.")
    
    else: # Nenhum token para revogar ou usuário para identificar
        # print("Debug: /logout - Nenhuma ação de revogação de token realizada (sem token específico ou usuário autenticado).")
        # Pode ser um logout onde o cliente apenas descarta tokens localmente sem informar o servidor.
        # Ou um erro se o cliente esperava que um token fosse revogado.
        # Se o objetivo é SEMPRE ter um usuário para revogar todos os tokens, remova a opcionalidade de current_user.
        pass

    # O status 204 significa "No Content", então não retornamos corpo.
    return None


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        role=current_user.role
        # user_metadata=current_user.user_metadata # Se o UserResponse tiver este campo
    )
