# app/routers/admin_panel_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Optional # Adicionado Optional se não estiver
import uuid # Certifique-se que uuid está importado

from app.schemas.admin_schemas import (
    AdminLoginSchema,
    AdminToken,
    AdminResponseSchema,
    AdminCreateSchema,
    AdminUpdateSchema
)
from app.auth.admin_jwt_handler import create_admin_access_token
from app.auth.admin_dependencies import get_current_admin_user
from app.models.admin import Administrator # O modelo Pydantic para o admin
from app.core.config import settings # Para o prefixo API_V1_STR

# Importar a instância do serviço
# Esta é a forma como estávamos fazendo. Garanta que app/services/__init__.py
# está criando e exportando admin_service_instance corretamente.
from app.services import admin_service_instance

admin_panel_router = APIRouter(
    prefix="/admin-panel", # Removido settings.API_V1_STR daqui, pois é aplicado no main.py
    tags=["Admin Panel - Gerenciamento de Administradores do Sistema"]
)

@admin_panel_router.post("/auth/token", response_model=AdminToken, summary="Login do Administrador do Painel")
async def login_for_admin_panel_token(form_data: AdminLoginSchema):
    if not admin_service_instance:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Serviço de administração indisponível.")

    admin = await admin_service_instance.authenticate_admin(
        username=form_data.username,
        plain_password=form_data.password,
        client_hwid_identifier=form_data.client_hwid_identifier
    )
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário, senha ou identificador de dispositivo incorreto.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if admin.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta de administrador inativa.")

    await admin_service_instance.update_last_login(admin.id)
    
    access_token_payload = {"sub": str(admin.id)} # 'sub' (subject) é o admin_id
    access_token = create_admin_access_token(data=access_token_payload)
    
    return {"access_token": access_token, "token_type": "bearer"}

@admin_panel_router.get("/me", response_model=AdminResponseSchema, summary="Obter Informações do Administrador Logado")
async def read_current_admin(current_admin: Administrator = Depends(get_current_admin_user)):
    return current_admin

@admin_panel_router.get("/administrators", response_model=List[AdminResponseSchema], summary="Listar Todos os Administradores")
async def list_all_administrators(
    skip: int = 0,
    limit: int = 20,
    current_admin: Administrator = Depends(get_current_admin_user) # Protegido
):
    if not admin_service_instance:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Serviço de administração indisponível.")
    # Adicionar verificação de permissões aqui se houver diferentes níveis de admin no futuro
    admins = await admin_service_instance.list_admins(skip=skip, limit=limit)
    return admins

# --- ENDPOINT CORRIGIDO/ADICIONADO ---
@admin_panel_router.get("/administrators/{admin_id}", response_model=AdminResponseSchema, summary="Obter um Administrador por ID")
async def get_administrator_by_id_route(
    admin_id: uuid.UUID, 
    current_admin: Administrator = Depends(get_current_admin_user) # Protegido
):
    if not admin_service_instance:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Serviço de administração indisponível.")
        
    admin = await admin_service_instance.get_admin_by_id(admin_id)
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Administrador com ID {admin_id} não encontrado.")
    return admin
# --- FIM DO ENDPOINT CORRIGIDO/ADICIONADO ---

@admin_panel_router.post("/administrators", response_model=AdminResponseSchema, status_code=status.HTTP_201_CREATED, summary="Criar Novo Administrador")
async def create_new_admin(
    admin_in: AdminCreateSchema,
    current_admin: Administrator = Depends(get_current_admin_user) # Protegido
):
    if not admin_service_instance:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Serviço de administração indisponível.")
    
    # Adicionar verificação de permissões (ex: só super-admin pode criar outros admins)
    existing_admin = await admin_service_instance.get_admin_by_username(admin_in.username)
    if existing_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome de usuário já registrado para um administrador.")
    
    new_admin = await admin_service_instance.create_admin(admin_in)
    if not new_admin:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao criar administrador.")
    return new_admin

@admin_panel_router.put("/administrators/{admin_id}", response_model=AdminResponseSchema, summary="Atualizar Administrador Existente")
async def update_existing_admin(
    admin_id: uuid.UUID,
    admin_in: AdminUpdateSchema,
    current_admin: Administrator = Depends(get_current_admin_user) # Protegido
):
    if not admin_service_instance:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Serviço de administração indisponível.")

    # Adicionar verificação de permissões aqui se necessário
    # Ex: if current_admin.id != admin_id and not current_admin.is_superuser:
    #         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    updated_admin = await admin_service_instance.update_admin(admin_id, admin_in)
    if not updated_admin:
        # O serviço já deve logar o erro. Se chegou aqui e updated_admin é None,
        # pode ser que o admin não foi encontrado ou houve um erro no update.
        # get_admin_by_id dentro de update_admin retornaria o admin se ele ainda existir
        # mas o update não retornou dados (o que seria estranho para um update bem-sucedido).
        # Se o admin foi deletado entre o fetch e o update, get_admin_by_id retornaria None.
        check_admin_exists = await admin_service_instance.get_admin_by_id(admin_id)
        if not check_admin_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Administrador com ID {admin_id} não encontrado.")
        else: # Admin existe, mas o update falhou em retornar o objeto atualizado.
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Falha ao atualizar administrador com ID {admin_id}, mas o administrador ainda existe.")
    return updated_admin

# Adicionar aqui outros endpoints do painel se necessário (logs, configurações, etc.)
