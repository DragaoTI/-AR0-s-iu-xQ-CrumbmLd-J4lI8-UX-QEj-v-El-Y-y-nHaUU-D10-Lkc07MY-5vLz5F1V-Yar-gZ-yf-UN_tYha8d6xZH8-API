# app/routers/admin_panel_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import List, Optional
import uuid

from app.schemas.admin_schemas import (
    AdminLoginSchema, AdminToken, AdminResponseSchema, 
    AdminCreateSchema, AdminUpdateSchema
)
from app.schemas.log_schemas import ApiLogResponseSchema
from app.auth.admin_jwt_handler import create_admin_access_token
from app.auth.admin_dependencies import get_current_admin_user
from app.models.admin import Administrator
from app.core.config import settings
from app.services import admin_service_instance, supabase_service

admin_panel_router = APIRouter(
    prefix="/admin-panel",
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
    # A chamada para update_last_login é síncrona se self.db.table().update().execute() for síncrono
    admin_service_instance.update_last_login(admin.id) # REMOVIDO await, pois o método em AdminService foi ajustado
    
    access_token_payload = {"sub": str(admin.id)}
    access_token = create_admin_access_token(data=access_token_payload)
    return {"access_token": access_token, "token_type": "bearer"}

@admin_panel_router.get("/me", response_model=AdminResponseSchema, summary="Obter Informações do Administrador Logado")
async def read_current_admin(current_admin: Administrator = Depends(get_current_admin_user)):
    return current_admin

@admin_panel_router.get("/administrators", response_model=List[AdminResponseSchema], summary="Listar Todos os Administradores")
async def list_all_administrators(
    skip: int = Query(0, ge=0), 
    limit: int = Query(20, ge=1, le=100),
    current_admin: Administrator = Depends(get_current_admin_user)
):
    if not admin_service_instance:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Serviço de administração indisponível.")
    admins = admin_service_instance.list_admins(skip=skip, limit=limit) # REMOVIDO await
    return admins

@admin_panel_router.get("/administrators/{admin_id}", response_model=AdminResponseSchema, summary="Obter um Administrador por ID")
async def get_administrator_by_id_route(
    admin_id: uuid.UUID, 
    current_admin: Administrator = Depends(get_current_admin_user)
):
    if not admin_service_instance:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Serviço de administração indisponível.")
    admin = await admin_service_instance.get_admin_by_id(admin_id) # Mantido await se get_admin_by_id for async e suas operações internas forem sync
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Administrador com ID {admin_id} não encontrado.")
    return admin

@admin_panel_router.post("/administrators", response_model=AdminResponseSchema, status_code=status.HTTP_201_CREATED, summary="Criar Novo Administrador")
async def create_new_admin(
    admin_in: AdminCreateSchema, current_admin: Administrator = Depends(get_current_admin_user)
):
    if not admin_service_instance:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Serviço de administração indisponível.")
    existing_admin = await admin_service_instance.get_admin_by_username(admin_in.username) # Mantido await
    if existing_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome de usuário já registrado para um administrador.")
    new_admin = admin_service_instance.create_admin(admin_in) # REMOVIDO await
    if not new_admin:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao criar administrador.")
    return new_admin

@admin_panel_router.put("/administrators/{admin_id}", response_model=AdminResponseSchema, summary="Atualizar Administrador Existente")
async def update_existing_admin(
    admin_id: uuid.UUID, admin_in: AdminUpdateSchema, current_admin: Administrator = Depends(get_current_admin_user)
):
    if not admin_service_instance:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Serviço de administração indisponível.")
    updated_admin = admin_service_instance.update_admin(admin_id, admin_in) # REMOVIDO await
    if not updated_admin:
        check_admin_exists = await admin_service_instance.get_admin_by_id(admin_id) # Mantido await
        if not check_admin_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Administrador com ID {admin_id} não encontrado.")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Falha ao atualizar administrador com ID {admin_id}, mas o administrador ainda existe.")
    return updated_admin

@admin_panel_router.get("/logs/api", response_model=List[ApiLogResponseSchema], summary="Visualizar Logs da API")
async def get_api_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    method: Optional[str] = Query(None, min_length=3, max_length=10), 
    status_code_filter: Optional[int] = Query(None, alias="status_code", ge=100, le=599),
    path_contains: Optional[str] = Query(None, min_length=1),
    user_id_filter: Optional[uuid.UUID] = Query(None, alias="user_id"),
    admin_id_filter: Optional[uuid.UUID] = Query(None, alias="admin_id"),
    current_admin: Administrator = Depends(get_current_admin_user)
):
    if not supabase_service or not supabase_service.client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Serviço Supabase indisponível para logging.")
    try:
        query = supabase_service.client.table("api_logs").select("*").order("timestamp", desc=True).offset(skip).limit(limit)
        if method: query = query.eq("method", method.upper())
        if status_code_filter is not None: query = query.eq("status_code", status_code_filter)
        if path_contains: query = query.ilike("path", f"%{path_contains}%")
        if user_id_filter: query = query.eq("user_id", str(user_id_filter))
        if admin_id_filter: query = query.eq("admin_id", str(admin_id_filter))
        
        response = query.execute() # REMOVIDO 'await' DAQUI
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Erro ao buscar logs da API: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao buscar logs da API.")
