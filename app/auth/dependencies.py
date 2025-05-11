from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from app.auth.jwt_handler import verify_token
from app.auth.schemas import TokenData
from app.services.supabase_service import supabase_service # Importa a instância
from app.models.user import User
from typing import Optional
import uuid

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login") # Ajuste o tokenUrl

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data: Optional[TokenData] = verify_token(token, credentials_exception)
    if not token_data or token_data.token_type != "access":
        raise credentials_exception
    
    if token_data.user_id is None: # Checagem adicional
        raise credentials_exception

    user_id_uuid = uuid.UUID(token_data.user_id) # Converter string para UUID
    user = await supabase_service.get_user_by_id(user_id_uuid) # Usar a instância

    if user is None:
        raise credentials_exception
    
    # Se a role estiver no token E for confiável (ex: você acabou de gerar o token)
    # você pode usar token_data.role. Caso contrário, busque do banco.
    # O get_user_by_id já deve trazer a role do Supabase user_metadata.
    # print(f"Current user from token: ID={user.id}, Role={user.role}") # Debug
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active: # Supondo que User tem 'is_active'
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    # print(f"Checking admin status for user: {current_user.id}, role: {current_user.role}") # Debug
    if not current_user.role or current_user.role.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges (admin required)",
        )
    return current_user
