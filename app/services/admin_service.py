# app/services/admin_service.py
from supabase import Client
from typing import Optional, Dict, List
import uuid
from datetime import datetime, timezone

from app.models.admin import Administrator
from app.schemas.admin_schemas import AdminCreateSchema, AdminUpdateSchema
from app.utils.security import get_password_hash, verify_password, hash_identifier

class AdminService:
    def __init__(self, supabase_client: Client):
        self.db: Optional[Client] = supabase_client
        if not self.db:
            print("ERRO CRÍTICO em AdminService: supabase_client não foi fornecido ou é None.")
            # Considerar levantar uma exceção para impedir a criação da instância se o client for essencial.
            # raise ValueError("AdminService requer uma instância válida do cliente Supabase.")

    async def get_admin_by_id(self, admin_id: uuid.UUID) -> Optional[Administrator]:
        if not self.db: return None
        try:
            response = self.db.table("administrators").select("*").eq("id", str(admin_id)).maybe_single().execute()
            if response.data:
                return Administrator(**response.data)
            return None
        except Exception as e:
            print(f"Erro ao buscar admin por ID {admin_id}: {e}")
            return None

    async def get_admin_by_username(self, username: str) -> Optional[Administrator]:
        if not self.db:
            print("DEBUG_GET_ADMIN: self.db é None em get_admin_by_username, retornando None.")
            return None
        
        target_username = str(username)
        print(f"DEBUG_GET_ADMIN: Tentando buscar admin com username EXATO: '{target_username}' na tabela 'administrators'")
        
        try:
            response = self.db.table("administrators").select("*").eq("username", target_username).execute()
            print(f"DEBUG_GET_ADMIN: Resposta bruta do Supabase para username '{target_username}': data='{response.data}', count='{response.count}'")
                
            if response and hasattr(response, 'data'):
                if response.data and len(response.data) > 0:
                    admin_data_dict = response.data[0]
                    print(f"DEBUG_GET_ADMIN: Dados encontrados para '{target_username}': {admin_data_dict}")
                    return Administrator(**admin_data_dict)
                else:
                    print(f"DEBUG_GET_ADMIN: Nenhum dado encontrado para '{target_username}' (response.data está vazio ou é None).")
                    return None
            else:
                print(f"ERRO_GET_ADMIN: Objeto de resposta do Supabase inválido ou None para '{target_username}'. Response: {response}")
                return None
        except Exception as e:
            print(f"EXCEÇÃO em get_admin_by_username para '{target_username}': {e}")
            import traceback
            traceback.print_exc()
            return None

    async def create_admin(self, admin_data: AdminCreateSchema) -> Optional[Administrator]:
        if not self.db: return None
        hashed_password = get_password_hash(admin_data.password)
        client_hwid_hash = None
        if admin_data.client_hwid_identifier:
            temp_hash = hash_identifier(admin_data.client_hwid_identifier)
            if temp_hash:
                client_hwid_hash = temp_hash
        
        db_data = {
            "username": admin_data.username,
            "password_hash": hashed_password,
            "client_hwid_identifier_hash": client_hwid_hash,
            "status": "active",
        }
        try:
            response = self.db.table("administrators").insert(db_data).execute()
            if response.data and len(response.data) > 0:
                return Administrator(**response.data[0])
            print(f"Falha ao criar admin {admin_data.username} - Supabase não retornou dados. Resposta: {response}")
            return None
        except Exception as e: 
            print(f"Erro ao criar admin {admin_data.username}: {e}")
            return None

    async def authenticate_admin(self, username: str, plain_password: str, client_hwid_identifier: str) -> Optional[Administrator]:
        if not self.db: return None
        print(f"--- AUTHENTICATE_ADMIN: Iniciando para user '{username}' ---")
        print(f"DEBUG: Client HWID/Fingerprint recebido do frontend: '{client_hwid_identifier}' (Tipo: {type(client_hwid_identifier)})")

        admin = await self.get_admin_by_username(username)
        if not admin:
            print(f"DEBUG: Admin '{username}' NÃO encontrado no banco de dados.")
            return None 
        
        print(f"DEBUG: Admin '{username}' encontrado. ID: {admin.id}. Status: {admin.status}")

        if not verify_password(plain_password, admin.password_hash):
            print(f"DEBUG: Senha INVÁLIDA para admin '{username}'.")
            return None
        
        print(f"DEBUG: Senha VÁLIDA para admin '{username}'. Prosseguindo para verificação de HWID.")

        hashed_client_hwid = hash_identifier(client_hwid_identifier)
        print(f"DEBUG: Hash do Client HWID/Fingerprint (SHA256 a ser usado): '{hashed_client_hwid}'")
        print(f"DEBUG: HWID Hash armazenado no DB para '{username}': '{admin.client_hwid_identifier_hash}' (Tipo: {type(admin.client_hwid_identifier_hash)})")

        if admin.client_hwid_identifier_hash:
            if admin.client_hwid_identifier_hash == hashed_client_hwid:
                print(f"DEBUG: Verificação de HWID bem-sucedida para '{username}'. HWIDs (registrado e fornecido) correspondem.")
            else:
                print(f"FALHA NA VERIFICAÇÃO DE HWID para admin '{username}'.")
                print(f"       Esperado (DB): '{admin.client_hwid_identifier_hash}'")
                print(f"       Recebido (hash do frontend): '{hashed_client_hwid}'")
                return None
        elif (not admin.client_hwid_identifier_hash) and hashed_client_hwid: 
            print(f"DEBUG: Admin '{username}' não possui HWID registrado ou está vazio. Tentando registrar o novo HWID hash: '{hashed_client_hwid}'")
            try:
                updated_hwid_success = await self.update_admin_hwid(admin.id, hashed_client_hwid)
                if updated_hwid_success:
                    admin.client_hwid_identifier_hash = hashed_client_hwid
                    print(f"DEBUG: HWID hash '{hashed_client_hwid}' registrado com sucesso para '{username}'.")
                else:
                    print(f"ERRO: Falha ao ATUALIZAR/REGISTRAR HWID para '{username}' no banco (update_admin_hwid retornou False). Login negado por precaução.")
                    return None 
            except Exception as e:
                print(f"EXCEÇÃO ao tentar registrar HWID para '{username}': {e}")
                return None
        elif (not admin.client_hwid_identifier_hash) and (not hashed_client_hwid):
            print(f"DEBUG: Admin '{username}' não tem HWID registrado e nenhum HWID válido foi fornecido pelo cliente. Login permitido (HWID opcional neste ponto).")

        print(f"DEBUG: Autenticação COMPLETA E BEM-SUCEDIDA para '{username}'.")
        return admin
            
    async def update_admin_hwid(self, admin_id: uuid.UUID, new_hwid_hash: str) -> bool:
        if not self.db: return False
        try:
            response = self.db.table("administrators").update({
                "client_hwid_identifier_hash": new_hwid_hash,
            }).eq("id", str(admin_id)).execute()
            return bool(response.data and len(response.data) > 0)
        except Exception as e:
            print(f"Erro ao atualizar HWID para admin {admin_id}: {e}")
            return False

    # >>> MÉTODO FALTANTE ADICIONADO ABAIXO <<<
    async def update_last_login(self, admin_id: uuid.UUID) -> bool:
        """Atualiza o campo last_login_at para o administrador especificado."""
        if not self.db:
            print(f"ERRO: update_last_login chamado para admin ID {admin_id}, mas self.db é None.")
            return False
        try:
            print(f"DEBUG: Atualizando last_login_at para admin ID: {admin_id}")
            response = self.db.table("administrators").update({
                "last_login_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", str(admin_id)).execute()
            # Verifica se a atualização teve efeito (Supabase retorna os dados atualizados)
            if response.data and len(response.data) > 0:
                print(f"DEBUG: last_login_at atualizado com sucesso para admin ID: {admin_id}")
                return True
            else:
                # Isso pode acontecer se o ID não existir, ou se a atualização não retornar dados (improvável para update bem-sucedido)
                print(f"AVISO: update_last_login para admin ID {admin_id} não retornou dados indicando sucesso, ou admin não encontrado. Resposta: {response}")
                # Considerar se isso deve ser um erro ou apenas um aviso.
                # Se o admin foi autenticado, ele existe. Então, o update deveria funcionar.
                # Se response.data for vazio, pode ser um problema de permissão de update pela service_role key?
                # Ou a tabela não tem a coluna `last_login_at`? (Verifique sua tabela no Supabase)
                return False # Ou True se você não se importa se a atualização foi confirmada, apenas que não houve exceção.
                            # Mas é melhor ser estrito aqui.
        except Exception as e:
            print(f"Erro ao atualizar último login para admin {admin_id}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def update_admin(self, admin_id: uuid.UUID, admin_update_data: AdminUpdateSchema) -> Optional[Administrator]:
        if not self.db: return None
        update_fields = admin_update_data.model_dump(exclude_unset=True, exclude_none=True)
        
        if "password" in update_fields and update_fields["password"]:
            update_fields["password_hash"] = get_password_hash(update_fields.pop("password"))
        
        if "client_hwid_identifier" in update_fields:
            hwid_input = update_fields.pop("client_hwid_identifier")
            if hwid_input is None:
                update_fields["client_hwid_identifier_hash"] = None
            elif hwid_input:
                update_fields["client_hwid_identifier_hash"] = hash_identifier(hwid_input)

        if not update_fields:
            print(f"DEBUG: Nenhuma alteração válida para admin {admin_id}.")
            return await self.get_admin_by_id(admin_id)

        try:
            response = self.db.table("administrators").update(update_fields).eq("id", str(admin_id)).execute()
            if response.data and len(response.data) > 0:
                return Administrator(**response.data[0])
            existing_admin = await self.get_admin_by_id(admin_id)
            if not existing_admin:
                 print(f"AVISO: Admin com ID {admin_id} não encontrado após tentativa de update.")
            return existing_admin
        except Exception as e:
            print(f"Erro ao atualizar admin {admin_id}: {e}")
            return None

    async def list_admins(self, skip: int = 0, limit: int = 100) -> List[Administrator]:
        if not self.db: return []
        try:
            response = self.db.table("administrators").select("*").order("username").offset(skip).limit(limit).execute()
            return [Administrator(**admin_data) for admin_data in response.data] if response.data else []
        except Exception as e:
            print(f"Erro ao listar administradores: {e}")
            return []
