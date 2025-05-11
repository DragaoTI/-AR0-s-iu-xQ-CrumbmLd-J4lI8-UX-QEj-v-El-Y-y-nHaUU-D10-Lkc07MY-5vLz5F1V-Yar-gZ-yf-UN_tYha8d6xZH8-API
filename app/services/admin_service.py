# app/services/admin_service.py
from supabase import Client
from typing import Optional, Dict, List # Adicionado List se não estava
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

    # As funções get_admin_by_id e get_admin_by_username são async porque podem ser chamadas
    # de endpoints async, mas as operações de DB dentro delas agora são síncronas.
    async def get_admin_by_id(self, admin_id: uuid.UUID) -> Optional[Administrator]:
        if not self.db: return None
        try:
            response = self.db.table("administrators").select("*").eq("id", str(admin_id)).maybe_single().execute() # SÍNCRONO
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
            response = self.db.table("administrators").select("*").eq("username", target_username).execute() # SÍNCRONO
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

    # Tornando síncrono se todas as operações internas são síncronas
    def create_admin(self, admin_data: AdminCreateSchema) -> Optional[Administrator]:
        if not self.db: return None
        hashed_password = get_password_hash(admin_data.password)
        client_hwid_hash = None
        if admin_data.client_hwid_identifier:
            temp_hash = hash_identifier(admin_data.client_hwid_identifier)
            if temp_hash: client_hwid_hash = temp_hash
        db_data = {
            "username": admin_data.username, "password_hash": hashed_password,
            "client_hwid_identifier_hash": client_hwid_hash, "status": "active",
        }
        try:
            response = self.db.table("administrators").insert(db_data).execute() # SÍNCRONO
            if response.data and len(response.data) > 0:
                return Administrator(**response.data[0])
            print(f"Falha ao criar admin {admin_data.username} - Supabase não retornou dados. Resposta: {response}")
            return None
        except Exception as e: 
            print(f"Erro ao criar admin {admin_data.username}: {e}")
            return None

    # authenticate_admin é async por causa das chamadas await a get_admin_by_username e update_admin_hwid (que também se tornará síncrona)
    async def authenticate_admin(self, username: str, plain_password: str, client_hwid_identifier: str) -> Optional[Administrator]:
        if not self.db: return None
        print(f"--- AUTHENTICATE_ADMIN: Iniciando para user '{username}' ---")
        print(f"DEBUG: Client HWID/Fingerprint recebido do frontend: '{client_hwid_identifier}' (Tipo: {type(client_hwid_identifier)})")
        admin = await self.get_admin_by_username(username) # get_admin_by_username ainda é async
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
                print(f"DEBUG: Verificação de HWID bem-sucedida para '{username}'. HWIDs correspondem.")
            else:
                print(f"FALHA NA VERIFICAÇÃO DE HWID para admin '{username}'."); return None
        elif (not admin.client_hwid_identifier_hash) and hashed_client_hwid: 
            print(f"DEBUG: Admin '{username}' não possui HWID. Registrando: '{hashed_client_hwid}'")
            try:
                if self.update_admin_hwid(admin.id, hashed_client_hwid): # update_admin_hwid agora é síncrono
                    admin.client_hwid_identifier_hash = hashed_client_hwid
                    print(f"DEBUG: HWID hash registrado com sucesso para '{username}'.")
                else:
                    print(f"ERRO: Falha ao ATUALIZAR/REGISTRAR HWID para '{username}'. Login negado."); return None 
            except Exception as e: print(f"EXCEÇÃO ao registrar HWID: {e}"); return None
        elif (not admin.client_hwid_identifier_hash) and (not hashed_client_hwid):
            print(f"DEBUG: Admin '{username}' sem HWID e nenhum HWID fornecido. Login permitido.")
        print(f"DEBUG: Autenticação COMPLETA E BEM-SUCEDIDA para '{username}'.")
        return admin
            
    # Tornando síncrono
    def update_admin_hwid(self, admin_id: uuid.UUID, new_hwid_hash: str) -> bool:
        if not self.db: return False
        try:
            response = self.db.table("administrators").update({"client_hwid_identifier_hash": new_hwid_hash}).eq("id", str(admin_id)).execute() # SÍNCRONO
            return bool(response.data and len(response.data) > 0)
        except Exception as e: print(f"Erro ao atualizar HWID para admin {admin_id}: {e}"); return False

    # Tornando síncrono
    def update_last_login(self, admin_id: uuid.UUID) -> bool:
        if not self.db: print(f"ERRO: update_last_login para admin {admin_id}, mas self.db é None."); return False
        try:
            print(f"DEBUG: Atualizando last_login_at para admin ID: {admin_id}")
            response = self.db.table("administrators").update({"last_login_at": datetime.now(timezone.utc).isoformat()}).eq("id", str(admin_id)).execute() # SÍNCRONO
            if response.data and len(response.data) > 0: print(f"DEBUG: last_login_at atualizado para admin ID: {admin_id}"); return True
            else: print(f"AVISO: update_last_login para admin ID {admin_id} não retornou dados. Resposta: {response}"); return False
        except Exception as e: print(f"Erro ao atualizar último login para admin {admin_id}: {e}"); import traceback; traceback.print_exc(); return False

    # Tornando síncrono
    def update_admin(self, admin_id: uuid.UUID, admin_update_data: AdminUpdateSchema) -> Optional[Administrator]:
        if not self.db: return None
        update_fields = admin_update_data.model_dump(exclude_unset=True, exclude_none=True)
        if "password" in update_fields and update_fields["password"]:
            update_fields["password_hash"] = get_password_hash(update_fields.pop("password"))
        if "client_hwid_identifier" in update_fields:
            hwid_input = update_fields.pop("client_hwid_identifier")
            if hwid_input is None: update_fields["client_hwid_identifier_hash"] = None
            elif hwid_input: update_fields["client_hwid_identifier_hash"] = hash_identifier(hwid_input)
        if not update_fields: print(f"DEBUG: Nenhuma alteração válida para admin {admin_id}."); return self.get_admin_by_id_sync(admin_id) # Precisa de versão sync
        try:
            response = self.db.table("administrators").update(update_fields).eq("id", str(admin_id)).execute() # SÍNCRONO
            if response.data and len(response.data) > 0: return Administrator(**response.data[0])
            existing_admin = self.get_admin_by_id_sync(admin_id) # Precisa de versão sync
            if not existing_admin: print(f"AVISO: Admin {admin_id} não encontrado após update.")
            return existing_admin
        except Exception as e: print(f"Erro ao atualizar admin {admin_id}: {e}"); return None

    # Tornando síncrono
    def list_admins(self, skip: int = 0, limit: int = 100) -> List[Administrator]:
        if not self.db: return []
        try:
            response = self.db.table("administrators").select("*").order("username").offset(skip).limit(limit).execute() # SÍNCRONO
            return [Administrator(**admin_data) for admin_data in response.data] if response.data else []
        except Exception as e: print(f"Erro ao listar administradores: {e}"); return []

    # Métodos síncronos auxiliares para get_admin_by_id e get_admin_by_username se chamados de métodos síncronos
    def get_admin_by_id_sync(self, admin_id: uuid.UUID) -> Optional[Administrator]:
        # Esta é uma simplificação. Idealmente, você não misturaria sync/async assim.
        # Mas para o AdminService se tornar totalmente síncrono, get_admin_by_username também precisaria ser.
        # Por ora, chamadas diretas ao DB no update_admin não podem chamar os async getters.
        # Isso se torna complexo se AdminService for totalmente síncrono.
        # A melhor abordagem seria usar supabase-py v2 e fazer TUDO async.
        # DADO O CONTEXTO, vamos manter os getters async e os chamadores dos getters async
        # E os métodos que só fazem UMA chamada síncrona ao DB podem ser síncronos.
        # Com isso, update_admin como está não pode chamar get_admin_by_id (async).
        # VAMOS REVERTER update_admin para async para manter consistência por enquanto, e remover _sync
        # OU fazer TODO o AdminService síncrono.
        # Assumindo que o `authenticate_admin` precisa continuar async por causa do `get_admin_by_username` (que faz IO).
        # Os métodos de update/create/list podem ser síncronos.
        # O `update_last_login` é chamado de um endpoint async, então ele pode ser `async` e fazer a chamada sync.
        # Isso é um pouco confuso devido ao cliente sync sendo usado em um contexto async.
        # Se a biblioteca cliente é síncrona, os métodos de serviço que a usam devem ser definidos como síncronos
        # e chamados de endpoints FastAPI usando `await run_in_threadpool` ou similar se forem bloqueantes.
        # Dada a simplicidade das queries, elas podem não bloquear por muito tempo.
        # VAMOS MANTER OS MÉTODOS DE SERVIÇO COMO `async def` e remover `await` do `.execute()`
        # Isso significa que são "async falsos" do ponto de vista do IO do DB, mas se encaixam no FastAPI.
        pass # Este método auxiliar não será usado se mantivermos os outros async.
