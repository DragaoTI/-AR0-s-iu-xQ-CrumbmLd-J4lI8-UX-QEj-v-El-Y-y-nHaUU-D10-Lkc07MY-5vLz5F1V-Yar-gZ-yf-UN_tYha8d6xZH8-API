# app/services/admin_service.py
from supabase import Client
from typing import Optional, Dict, List
import uuid
from datetime import datetime, timezone

from app.core.config import settings # Se precisar de configurações
from app.models.admin import Administrator
from app.schemas.admin_schemas import AdminCreateSchema, AdminUpdateSchema
from app.utils.security import get_password_hash, verify_password, hash_identifier

class AdminService:
    def __init__(self, supabase_client: Client):
        self.db: Client = supabase_client # Injetar o cliente Supabase

    async def get_admin_by_id(self, admin_id: uuid.UUID) -> Optional[Administrator]:
        try:
            response = self.db.table("administrators").select("*").eq("id", str(admin_id)).maybe_single().execute()
            if response.data:
                return Administrator(**response.data)
            return None
        except Exception as e:
            print(f"Erro ao buscar admin por ID {admin_id}: {e}")
            return None

    async def get_admin_by_username(self, username: str) -> Optional[Administrator]:
        try:
            response = self.db.table("administrators").select("*").eq("username", username).maybe_single().execute()
            if response.data:
                return Administrator(**response.data)
            return None
        except Exception as e:
            print(f"Erro ao buscar admin por username {username}: {e}")
            return None

    async def create_admin(self, admin_data: AdminCreateSchema) -> Optional[Administrator]:
        hashed_password = get_password_hash(admin_data.password)
        client_hwid_hash = hash_identifier(admin_data.client_hwid_identifier) if admin_data.client_hwid_identifier else None
        
        db_data = {
            "username": admin_data.username,
            "password_hash": hashed_password,
            "client_hwid_identifier_hash": client_hwid_hash,
            "status": "active", # Default
            # created_at e updated_at são definidos pelo DB
        }
        try:
            response = self.db.table("administrators").insert(db_data).execute()
            if response.data:
                return Administrator(**response.data[0])
            return None
        except Exception as e: # Capturar erros de duplicação de username, etc.
            print(f"Erro ao criar admin {admin_data.username}: {e}")
            return None

    async def authenticate_admin(self, username: str, plain_password: str, client_hwid_identifier: str) -> Optional[Administrator]:
        admin = await self.get_admin_by_username(username)
        if not admin:
            return None # Usuário não encontrado
        
        if not verify_password(plain_password, admin.password_hash):
            return None # Senha inválida

        # Verificar HWID (identificador do cliente)
        # Se o admin não tiver um HWID registrado, este login pode ser o primeiro para registrar.
        # Ou, se for obrigatório, falhar aqui. Vamos assumir que se estiver registrado, deve corresponder.
 #       hashed_client_hwid = hash_identifier(client_hwid_identifier)
 #       if admin.client_hwid_identifier_hash and admin.client_hwid_identifier_hash != hashed_client_hwid:
 #           print(f"Falha na verificação de HWID para admin: {username}. Esperado: {admin.client_hwid_identifier_hash}, Recebido (hash): {hashed_client_hwid}")
 #           return None # HWID não corresponde
 #
 #       # Se o admin não tem HWID registrado e este é o primeiro login válido, você pode querer registrá-lo:
 #       if not admin.client_hwid_identifier_hash and hashed_client_hwid:
 #           # print(f"Registrando HWID para admin {username} no primeiro login válido.")
 #          await self.update_admin_hwid(admin.id, hashed_client_hwid)
 #           admin.client_hwid_identifier_hash = hashed_client_hwid # Atualiza o objeto em memória

        return admin # Autenticação bem-sucedida

    async def update_last_login(self, admin_id: uuid.UUID) -> bool:
        try:
            self.db.table("administrators").update({
                "last_login_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", str(admin_id)).execute()
            return True
        except Exception as e:
            print(f"Erro ao atualizar último login para admin {admin_id}: {e}")
            return False
            
    async def update_admin_hwid(self, admin_id: uuid.UUID, new_hwid_hash: str) -> bool:
        try:
            self.db.table("administrators").update({
                "client_hwid_identifier_hash": new_hwid_hash,
                "updated_at": datetime.now(timezone.utc).isoformat() # Forçar atualização do updated_at
            }).eq("id", str(admin_id)).execute()
            return True
        except Exception as e:
            print(f"Erro ao atualizar HWID para admin {admin_id}: {e}")
            return False

    async def update_admin(self, admin_id: uuid.UUID, admin_update_data: AdminUpdateSchema) -> Optional[Administrator]:
        update_fields = admin_update_data.model_dump(exclude_unset=True)
        
        if "password" in update_fields and update_fields["password"]:
            update_fields["password_hash"] = get_password_hash(update_fields.pop("password"))
        
        if "client_hwid_identifier" in update_fields and update_fields["client_hwid_identifier"]:
            update_fields["client_hwid_identifier_hash"] = hash_identifier(update_fields.pop("client_hwid_identifier"))
        elif "client_hwid_identifier" in update_fields and update_fields["client_hwid_identifier"] is None: # Permitir limpar HWID
             update_fields["client_hwid_identifier_hash"] = None
             update_fields.pop("client_hwid_identifier")


        if not update_fields:
            return await self.get_admin_by_id(admin_id) # Nenhuma alteração

        try:
            # updated_at será atualizado pelo trigger do banco de dados
            response = self.db.table("administrators").update(update_fields).eq("id", str(admin_id)).execute()
            if response.data:
                return Administrator(**response.data[0])
            # Se o update não retornou dados (ex: admin não encontrado com esse ID), buscar explicitamente
            return await self.get_admin_by_id(admin_id)
        except Exception as e:
            print(f"Erro ao atualizar admin {admin_id}: {e}")
            return None

    async def list_admins(self, skip: int = 0, limit: int = 100) -> List[Administrator]:
        try:
            response = self.db.table("administrators").select("*").order("username").offset(skip).limit(limit).execute()
            return [Administrator(**admin_data) for admin_data in response.data] if response.data else []
        except Exception as e:
            print(f"Erro ao listar administradores: {e}")
            return []

# Você precisará instanciar este serviço, provavelmente onde você instancia o SupabaseService
# Exemplo, no seu __init__.py do app, ou onde o supabase_service é criado:
# from app.services.supabase_service import supabase_client # Supondo que você exponha o client
# admin_service = AdminService(supabase_client=supabase_client)
# Ou injetar a instância do client Supabase de outra forma.
