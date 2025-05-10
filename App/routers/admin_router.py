from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.auth.dependencies import get_current_admin_user
from app.models.user import User
from app.services.supabase_service import supabase_service
from app.schemas.geo_log_schemas import GeoLogResponse
from typing import List

router = APIRouter(prefix="/4L8FJYy4eWGL_admin", tags=["Admin"], dependencies=[Depends(get_current_admin_user)])

@router.get("/4L8FJYy4eWGL", summary="Painel de Admin Simples")
async def admin_dashboard(current_admin: User = Depends(get_current_admin_user)):
    return {
        "message": f"Bem-vindo ao painel de admin, {current_admin.email}!",
        "role": current_admin.role
    }

@router.get("/geologs", response_model=List[GeoLogResponse], summary="Listar Logs de GeoIP")
async def list_geo_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(get_current_admin_user) # Garante que é admin
):
    logs = await supabase_service.get_all_geo_logs(limit=limit, offset=offset)
    return logs

# Você pode adicionar outras rotas aqui:
# - Listar usuários (cuidado com a paginação e dados sensíveis)
# - Banir/ativar usuários
# - Mudar role de usuário (com muita cautela)
