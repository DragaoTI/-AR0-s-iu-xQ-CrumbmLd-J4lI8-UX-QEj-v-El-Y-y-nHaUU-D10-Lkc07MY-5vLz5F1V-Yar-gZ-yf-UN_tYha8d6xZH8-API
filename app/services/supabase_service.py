from supabase import create_client, Client
from app.core.config import settings
from app.schemas.user_schemas import UserCreate
from app.models.user import User
from app.schemas.geo_log_schemas import GeoLogCreate
from app.utils.security import hash_token # Supondo que hash_token é para refresh tokens
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime, timezone

class SupabaseService:
    def __init__(self):
        self.client: Optional[Client] = None # Inicializa como None
        print(f"INFO:     Tentando inicializar SupabaseService...")
        print(f"INFO:     Usando SUPABASE_URL: '{settings.SUPABASE_URL[:30] if settings.SUPABASE_URL else 'NÃO DEFINIDA!'}...'")
        print(f"INFO:     Usando SUPABASE_KEY (primeiros 5 chars): '{settings.SUPABASE_KEY[:5] if settings.SUPABASE_KEY else 'NÃO DEFINIDA!'}...'")

        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            print("ERRO FATAL: SUPABASE_URL ou SUPABASE_KEY não estão definidas nas configurações.")
            print("          A inicialização do cliente Supabase será abortada.")
            return # self.client permanece None

        try:
            self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            if self.client:
                # Você pode tentar uma operação simples aqui para verificar a conexão, mas cuidado com chamadas síncronas em __init__ se não for necessário.
                # Exemplo (não recomendado em __init__ se for bloquear):
                # try:
                #     self.client.table("users").select("id", head=True).limit(1).execute()
                #     print("INFO:     Teste de conexão inicial com Supabase bem-sucedido.")
                # except Exception as db_test_e:
                #     print(f"AVISO:    Supabase client criado, mas teste de conexão inicial falhou: {db_test_e}")
                #     print(f"AVISO:    Verifique as políticas RLS e se a service_role key tem permissões.")

                print(f"INFO:     Supabase client INICIALIZADO COM SUCESSO.")
            else:
                # Este caso é estranho, pois create_client geralmente levanta exceção em falha, ou retorna um objeto client.
                print(f"AVISO CRÍTICO: create_client retornou um valor 'falsey' (None ou similar) sem levantar uma exceção.")
                self.client = None # Garante que é None
        except Exception as e:
            print(f"ERRO FATAL AO INICIALIZAR O OBJETO SUPABASE CLIENT: {e}")
            print(f"          Stacktrace do erro de inicialização do Supabase Client:")
            import traceback
            traceback.print_exc() # Imprime o stacktrace completo do erro
            self.client = None # Garante que é None em caso de qualquer exceção

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        if not self.client:
            print("ERRO: get_user_by_id chamado, mas self.client é None.")
            return None
        try:
            user_data_res = self.client.auth.admin.get_user_by_id(str(user_id))
            if user_data_res and user_data_res.user:
                supabase_user = user_data_res.user
                role = supabase_user.user_metadata.get("role", "user") if supabase_user.user_metadata else "user"
                return User(
                    id=supabase_user.id,
                    email=supabase_user.email,
                    is_active=True,
                    role=role,
                    user_metadata=supabase_user.user_metadata or {}
                )
            return None
        except Exception as e:
            print(f"Erro ao buscar usuário {user_id} no Supabase: {e}")
            return None

    async def get_user_by_email_for_check(self, email: str) -> bool:
        if not self.client:
            print("ERRO: get_user_by_email_for_check chamado, mas self.client é None.")
            return False
        try:
            response = self.client.auth.admin.list_users(email=email, limit=1)
            return bool(response.users)
        except Exception as e:
            print(f"Erro ao verificar usuário por email {email} no Supabase: {e}")
            return False

    async def create_user(self, user_create: UserCreate) -> Optional[User]:
        if not self.client:
            print("ERRO: create_user chamado, mas self.client é None.")
            return None
        try:
            user_metadata_with_role = user_create.model_dump(exclude_unset=True).get("user_metadata", {})
            if "role" not in user_metadata_with_role:
                user_metadata_with_role["role"] = "user"

            response = self.client.auth.admin.create_user(
                email=user_create.email,
                password=user_create.password,
                email_confirm=True,
                user_metadata=user_metadata_with_role
            )
            if response and response.user:
                created_user = response.user
                return User(
                    id=created_user.id,
                    email=created_user.email,
                    is_active=True,
                    role=created_user.user_metadata.get("role", "user"),
                    user_metadata=created_user.user_metadata or {}
                )
            print(f"Falha ao criar usuário no Supabase. Resposta: {response}")
            return None
        except Exception as e:
            print(f"Erro ao criar usuário no Supabase: {e}")
            return None

    async def login_user(self, email: str, password: str) -> Optional[User]:
        if not self.client:
            print("ERRO: login_user chamado, mas self.client é None.")
            return None
        try:
            response = self.client.auth.sign_in_with_password({"email": email, "password": password})
            if response and response.user:
                return await self.get_user_by_id(response.user.id)
            return None
        except Exception as e:
            print(f"Erro ao logar usuário no Supabase: {e}")
            return None

    async def add_geo_log(self, log_data: GeoLogCreate) -> bool:
        if not self.client:
            print("ERRO: add_geo_log chamado, mas self.client é None.")
            return False
        try:
            response = self.client.table("geo_login_logs").insert(log_data.model_dump()).execute()
            return bool(response.data and len(response.data) > 0)
        except Exception as e:
            print(f"Erro ao adicionar geo log no Supabase: {e}")
            return False

    async def get_all_geo_logs(self, limit: int = 100, offset: int = 0) -> list:
        if not self.client:
            print("ERRO: get_all_geo_logs chamado, mas self.client é None.")
            return []
        try:
            response = self.client.table("geo_login_logs").select("*").order("timestamp", desc=True).limit(limit).offset(offset).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Erro ao buscar geo logs: {e}")
            return []

    async def store_refresh_token(self, user_id: uuid.UUID, token_str: str, expires_at: datetime, parent_token_str: Optional[str] = None) -> Optional[Dict]:
        if not self.client:
            print("ERRO: store_refresh_token chamado, mas self.client é None.")
            return None
        token_hashed = hash_token(token_str)
        parent_hash = hash_token(parent_token_str) if parent_token_str else None
        
        data_to_insert = {
            "user_id": str(user_id),
            "token_hash": token_hashed,
            "expires_at": expires_at.isoformat(),
            "issued_at": datetime.now(timezone.utc).isoformat()
        }
        if parent_hash:
            data_to_insert["parent_token_hash"] = parent_hash
            
        try:
            response = self.client.table("refresh_tokens").insert(data_to_insert).execute()
            return response.data[0] if response.data and len(response.data) > 0 else None
        except Exception as e:
            print(f"Erro ao armazenar refresh token (hash: {token_hashed[:10]}...): {e}")
            return None

    async def get_refresh_token_data_by_hash(self, token_str: str) -> Optional[Dict]:
        if not self.client:
            print("ERRO: get_refresh_token_data_by_hash chamado, mas self.client é None.")
            return None
        token_hashed = hash_token(token_str)
        try:
            response = self.client.table("refresh_tokens").select("*").eq("token_hash", token_hashed).maybe_single().execute()
            return response.data if response.data else None
        except Exception as e:
            print(f"Erro ao buscar refresh token por hash (hash: {token_hashed[:10]}...): {e}")
            return None

    async def revoke_refresh_token(self, token_db_id: uuid.UUID) -> bool:
        if not self.client:
            print("ERRO: revoke_refresh_token chamado, mas self.client é None.")
            return False
        try:
            response = self.client.table("refresh_tokens").update({"revoked": True}).eq("id", str(token_db_id)).execute()
            return bool(response.data and len(response.data) > 0) # Verifica se alguma linha foi afetada
        except Exception as e:
            print(f"Erro ao revogar refresh token ID {token_db_id}: {e}")
            return False

    async def revoke_refresh_token_by_hash(self, token_str: str) -> bool:
        if not self.client:
            print("ERRO: revoke_refresh_token_by_hash chamado, mas self.client é None.")
            return False
        token_hashed = hash_token(token_str)
        try:
            response = self.client.table("refresh_tokens").update({"revoked": True}).eq("token_hash", token_hashed).eq("revoked", False).execute()
            return bool(response.data and len(response.data) > 0)
        except Exception as e:
            print(f"Erro ao revogar refresh token (hash: {token_hashed[:10]}...): {e}")
            return False

    async def revoke_all_user_refresh_tokens(self, user_id: uuid.UUID) -> bool:
        if not self.client:
            print("ERRO: revoke_all_user_refresh_tokens chamado, mas self.client é None.")
            return False
        try:
            response = self.client.table("refresh_tokens").update({"revoked": True}).eq("user_id", str(user_id)).eq("revoked", False).execute()
            # Mesmo que nenhuma linha seja atualizada (o usuário não tinha tokens ativos), a operação é considerada "bem-sucedida" se não houver erro.
            return True 
        except Exception as e:
            print(f"Erro ao revogar todos os refresh tokens para o usuário {user_id}: {e}")
            return False

supabase_service = SupabaseService()
