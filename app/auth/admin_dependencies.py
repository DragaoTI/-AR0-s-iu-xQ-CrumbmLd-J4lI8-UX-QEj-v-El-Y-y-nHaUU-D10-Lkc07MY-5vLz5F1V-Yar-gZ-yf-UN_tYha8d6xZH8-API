# app/auth/admin_dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
import uuid

from app.auth.admin_jwt_handler import verify_admin_token
from app.schemas.admin_schemas import AdminTokenData
# Precisa da instância do AdminService
# from app.services import admin_service_instance # Assumindo que você criou a instância
from app.models.admin import Administrator
from app.core.config import settings # Para o tokenUrl
from app.services import admin_service_instance


# Este é o URL onde o admin faz login para obter o token
# Ajuste o prefixo do router de admin se for diferente
ADMIN_PANEL_TOKEN_URL = f"{settings.API_V1_STR}/admin-panel/auth/token" 

oauth2_scheme_admin_panel = OAuth2PasswordBearer(tokenUrl=ADMIN_PANEL_TOKEN_URL)

async def get_current_admin_user(
    token: str = Depends(oauth2_scheme_admin_panel)
    # admin_service: AdminService = Depends(get_admin_service_dependency) # Se você usar injeção de dependência para o serviço
) -> Administrator:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data: Optional[AdminTokenData] = verify_admin_token(token, credentials_exception)
    if not token_data or not token_data.admin_id:
        raise credentials_exception
    
    # Para usar o admin_service, você precisará injetá-lo.
    # Uma forma simples por agora é importá-lo diretamente se você criou uma instância global.
    # Senão, você precisará de uma função de dependência para obter o admin_service.
    # Exemplo com importação direta (requer que admin_service_instance exista globalmente):
    from app.services import admin_service_instance # CUIDADO COM IMPORTAÇÕES CIRCULARES

    admin_id_uuid = uuid.UUID(token_data.admin_id)
    admin = await admin_service_instance.get_admin_by_id(admin_id_uuid)
    
    if admin is None:
        raise credentials_exception
    if admin.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is inactive.")
        
    return admin
