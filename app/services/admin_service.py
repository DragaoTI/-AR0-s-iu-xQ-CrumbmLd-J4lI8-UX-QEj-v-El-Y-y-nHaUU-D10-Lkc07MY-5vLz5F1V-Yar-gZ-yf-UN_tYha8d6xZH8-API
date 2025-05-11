# app/services/admin_service.py
from supabase import Client
from typing import Optional, Dict, List
import uuid
from datetime import datetime, timezone

# Removido import de settings se não for usado diretamente aqui
# from app.core.config import settings 
from app.models.admin import Administrator
from app.schemas.admin_schemas import AdminCreateSchema, AdminUpdateSchema
from app.utils.security import get_password_hash, verify_password, hash_identifier

class AdminService:
    def __init__(self, supabase_client: Client):
        self.db: Client = supabase_client # Injetar o cliente Supabase
        if not self.db:
            # Isso seria um erro de programação se o client não fosse passado.
            # Ou um erro se o supabase_service.client falhou ao inicializar antes de criar AdminService.
            print("ERRO CRÍTICO em AdminService: supabase_client não foi fornecido ou é None.")
            # Poderia levantar uma exceção aqui para impedir a criação da instância.
            # raise ValueError("AdminService requer uma instância válida do cliente Supabase.")

    async def get_admin_by_id(self, admin_id: uuid.UUID) -> Optional[Administrator]:
        if not self.db: return None # Checagem de segurança se o client não inicializou
        try:
            response = self.db.table("administrators").select("*").eq("id", str(admin_id)).maybe_single().execute()
            if response.data:
                return Administrator(**response.data)
            return None
        except Exception as e:
            print(f"Erro ao buscar admin por ID {admin_id}: {e}")
            return None

    # Em app/services/admin_service.py
    async def get_admin_by_username(self, username: str) -> Optional[Administrator]:
        if not self.db:
            print("DEBUG_GET_ADMIN: self.db é None, retornando None.")
            return None
        print(f"DEBUG_GET_ADMIN: Tentando buscar admin '{username}'...")
        try:
            # TESTE: Tentar selecionar apenas o ID, e não usar maybe_single() por enquanto
            response = self.db.table("administrators").select("id, username, password_hash, client_hwid_identifier_hash, status, last_login_at, created_at, updated_at").eq("username", username).limit(1).execute()
            
            print(f"DEBUG_GET_ADMIN: Resposta bruta do Supabase: {response}") # LOG IMPORTANTE
            
            if response and hasattr(response, 'data'): # Verifica se response e response.data existem
                if response.data and len(response.data) > 0:
                    print(f"DEBUG_GET_ADMIN: Dados encontrados para '{username}': {response.data[0]}")
                    return Administrator(**response.data[0])
                else:
                    print(f"DEBUG_GET_ADMIN: Nenhum dado encontrado para '{username}' (response.data está vazio).")
                    return None
            else:
                # Se response for None ou não tiver 'data', isso é um problema sério com a chamada ao Supabase
                print(f"ERRO_GET_ADMIN: Objeto de resposta do Supabase inválido ou None para '{username}'. Response: {response}")
                return None
        except Exception as e:
            print(f"EXCEÇÃO em get_admin_by_username para '{username}': {e}")
            import traceback
            traceback.print_exc()
            return None

    async def create_admin(self, admin_data: AdminCreateSchema) -> Optional[Administrator]:
        if not self.db: return None
        hashed_password = get_password_hash(admin_data.password)
        
        # Tratar client_hwid_identifier: se for None ou string vazia, client_hwid_hash será None
        client_hwid_hash = None
        if admin_data.client_hwid_identifier: # Apenas calcula o hash se não for None e não for vazio
            temp_hash = hash_identifier(admin_data.client_hwid_identifier)
            if temp_hash: # Garante que o hash_identifier não retornou string vazia
                client_hwid_hash = temp_hash
        
        db_data = {
            "username": admin_data.username,
            "password_hash": hashed_password,
            "client_hwid_identifier_hash": client_hwid_hash, # Será None se não fornecido ou se o hash for vazio
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
            # Para depuração extrema, não logue hashes de senha em produção
            # temp_hashed_provided_password = get_password_hash(plain_password)
            # print(f"       Password hash no DB: {admin.password_hash[:20]}... Hash da senha fornecida: {temp_hashed_provided_password[:20]}...")
            return None
        
        print(f"DEBUG: Senha VÁLIDA para admin '{username}'. Prosseguindo para verificação de HWID.")

        hashed_client_hwid = hash_identifier(client_hwid_identifier) # Retorna "" se client_hwid_identifier for vazio/None
        print(f"DEBUG: Hash do Client HWID/Fingerprint (SHA256 a ser usado): '{hashed_client_hwid}'")
        print(f"DEBUG: HWID Hash armazenado no DB para '{username}': '{admin.client_hwid_identifier_hash}' (Tipo: {type(admin.client_hwid_identifier_hash)})")

        # Cenário 1: Admin já tem um HWID registrado no banco. Deve corresponder.
        # admin.client_hwid_identifier_hash pode ser None ou uma string de hash.
        if admin.client_hwid_identifier_hash: # True se for uma string não vazia
            if admin.client_hwid_identifier_hash == hashed_client_hwid:
                print(f"DEBUG: Verificação de HWID bem-sucedida para '{username}'. HWIDs (registrado e fornecido) correspondem.")
            else:
                print(f"FALHA NA VERIFICAÇÃO DE HWID para admin '{username}'.")
                print(f"       Esperado (DB): '{admin.client_hwid_identifier_hash}'")
                print(f"       Recebido (hash do frontend): '{hashed_client_hwid}'")
                return None # HWID não corresponde
        # Cenário 2: Admin NÃO tem HWID registrado (é None ou string vazia) E um HWID válido (hash não vazio) foi enviado pelo cliente. Registra-o.
        elif (not admin.client_hwid_identifier_hash) and hashed_client_hwid: 
            print(f"DEBUG: Admin '{username}' não possui HWID registrado ou está vazio. Tentando registrar o novo HWID hash: '{hashed_client_hwid}'")
            try:
                updated_hwid_success = await self.update_admin_hwid(admin.id, hashed_client_hwid)
                if updated_hwid_success:
                    admin.client_hwid_identifier_hash = hashed_client_hwid # Atualiza o objeto admin em memória
                    print(f"DEBUG: HWID hash '{hashed_client_hwid}' registrado com sucesso para '{username}'.")
                else:
                    print(f"ERRO: Falha ao ATUALIZAR/REGISTRAR HWID para '{username}' no banco (update_admin_hwid retornou False). Login negado por precaução.")
                    return None 
            except Exception as e:
                print(f"EXCEÇÃO ao tentar registrar HWID para '{username}': {e}")
                return None
        # Cenário 3: Admin não tem HWID no DB E o HWID fornecido pelo cliente também resultou em hash vazio (ou seja, cliente não enviou HWID).
        # Se o HWID for opcional, permite o login. Se for obrigatório, deveria retornar None aqui.
        # A lógica atual permite login se a senha estiver correta e não houver conflito de HWID.
        elif (not admin.client_hwid_identifier_hash) and (not hashed_client_hwid):
            print(f"DEBUG: Admin '{username}' não tem HWID registrado e nenhum HWID válido foi fornecido pelo cliente. Login permitido (HWID opcional neste ponto).")
        # Outros casos (ex: HWID no DB, mas cliente não envia HWID) podem ser tratados aqui se necessário.
        # Se admin.client_hwid_identifier_hash existe E hashed_client_hwid é vazio (cliente não enviou),
        # a política atual é negar o login (primeiro if).

        print(f"DEBUG: Autenticação COMPLETA E BEM-SUCEDIDA para '{username}'.")
        return admin
            
    async def update_admin_hwid(self, admin_id: uuid.UUID, new_hwid_hash: str) -> bool:
        if not self.db: return False
        try:
            # updated_at será atualizado pelo trigger do banco de dados se configurado,
            # ou podemos definir explicitamente aqui.
            response = self.db.table("administrators").update({
                "client_hwid_identifier_hash": new_hwid_hash,
                # "updated_at": datetime.now(timezone.utc).isoformat() # Opcional, se não houver trigger
            }).eq("id", str(admin_id)).execute()
            # Supabase update retorna uma lista de registros atualizados.
            # Se a lista não estiver vazia, a atualização ocorreu.
            return bool(response.data and len(response.data) > 0)
        except Exception as e:
            print(f"Erro ao atualizar HWID para admin {admin_id}: {e}")
            return False

    async def update_admin(self, admin_id: uuid.UUID, admin_update_data: AdminUpdateSchema) -> Optional[Administrator]:
        if not self.db: return None
        update_fields = admin_update_data.model_dump(exclude_unset=True, exclude_none=True) # exclude_none para não enviar campos None
        
        if "password" in update_fields and update_fields["password"]:
            update_fields["password_hash"] = get_password_hash(update_fields.pop("password"))
        
        # Lógica para client_hwid_identifier no update:
        # Se explicitamente None, define o hash como None (para limpar).
        # Se uma string não vazia, calcula o hash.
        # Se não presente no payload de update, não mexe no HWID hash existente.
        if "client_hwid_identifier" in update_fields:
            hwid_input = update_fields.pop("client_hwid_identifier")
            if hwid_input is None: # Intenção explícita de limpar
                update_fields["client_hwid_identifier_hash"] = None
            elif hwid_input: # Se for uma string não vazia
                update_fields["client_hwid_identifier_hash"] = hash_identifier(hwid_input)
            # Se hwid_input for uma string vazia "", o hash será "" e pode ser salvo,
            # ou você pode querer tratá-lo como None também:
            # elif not hwid_input: update_fields["client_hwid_identifier_hash"] = None

        if not update_fields: # Se nada mudou ou só campos None foram enviados (e exclude_none os removeu)
            print(f"DEBUG: Nenhuma alteração válida para admin {admin_id}.")
            return await self.get_admin_by_id(admin_id)

        try:
            response = self.db.table("administrators").update(update_fields).eq("id", str(admin_id)).execute()
            if response.data and len(response.data) > 0:
                return Administrator(**response.data[0])
            # Se o update não afetou linhas (ex: ID não existe), buscar o admin pode retornar None ou o estado antigo
            existing_admin = await self.get_admin_by_id(admin_id)
            if not existing_admin:
                 print(f"AVISO: Admin com ID {admin_id} não encontrado após tentativa de update.")
            return existing_admin # Retorna o estado atual (que pode não ter sido alterado)
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

# A instância do AdminService deve ser criada onde você tem acesso ao supabase_service.client
# Geralmente em app/services/__init__.py
# from .supabase_service import supabase_service
# admin_service_instance = AdminService(supabase_client=supabase_service.client)
