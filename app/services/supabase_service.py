from supabase import create_client, Client
from app.core.config import settings
from app.schemas.user_schemas import UserCreate # Certifique-se que este path está correto
from app.models.user import User # Certifique-se que este path está correto
from app.schemas.geo_log_schemas import GeoLogCreate # Certifique-se que este path está correto
from app.utils.security import hash_token
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime, timezone

class SupabaseService:
    def __init__(self):
        try:
            self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        except Exception as e:
            print(f"ERRO FATAL: Falha ao inicializar Supabase client: {e}")
            # Em um cenário real, você poderia levantar uma exceção aqui para parar a aplicação
            # ou ter um mecanismo de retry, mas para este exemplo, apenas logamos.
            self.client = None # Para evitar AttributeError se a inicialização falhar

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        if not self.client: return None
        try:
            user_data_res = self.client.auth.admin.get_user_by_id(str(user_id))
            if user_data_res and user_data_res.user:
                supabase_user = user_data_res.user
                role = supabase_user.user_metadata.get("role", "user") if supabase_user.user_metadata else "user"
                return User(
                    id=supabase_user.id,
                    email=supabase_user.email,
                    is_active=True, # Assumindo ativo se o usuário existe e não há campo explícito
                    role=role,
                    user_metadata=supabase_user.user_metadata or {}
                )
            return None
        except Exception as e:
            print(f"Erro ao buscar usuário {user_id} no Supabase: {e}")
            return None

    async def get_user_by_email_for_check(self, email: str) -> bool:
        """Verifica se um usuário com o email fornecido já existe."""
        if not self.client: return False
        try:
            # Usar list_users com filtro de email. Pode não ser o mais performático para muitos usuários.
            # Supabase não tem um "check_email_exists" direto na API de admin.
            response = self.client.auth.admin.list_users(email=email, limit=1)
            return bool(response.users)
        except Exception as e:
            print(f"Erro ao verificar usuário por email {email} no Supabase: {e}")
            return False

    async def create_user(self, user_create: UserCreate) -> Optional[User]:
        if not self.client: return None
        try:
            user_metadata_with_role = user_create.model_dump().get("user_metadata", {})
            if "role" not in user_metadata_with_role:
                user_metadata_with_role["role"] = "user"

            response = self.client.auth.admin.create_user(
                email=user_create.email,
                password=user_create.password,
                email_confirm=True, # Ou False se você não quer confirmação de email inicialmente
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
        if not self.client: return None
        try:
            response = self.client.auth.sign_in_with_password({"email": email, "password": password})
            if response and response.user:
                # Após o login, buscar dados completos, incluindo metadados/role
                return await self.get_user_by_id(response.user.id)
            return None
        except Exception as e:
            print(f"Erro ao logar usuário no Supabase: {e}")
            return None

    async def add_geo_log(self, log_data: GeoLogCreate) -> bool:
        if not self.client: return False
        try:
            response = self.client.table("geo_login_logs").insert(log_data.model_dump()).execute()
            return len(response.data) > 0 if response.data is not None else False
        except Exception as e:
            print(f"Erro ao adicionar geo log no Supabase: {e}")
            return False

    async def get_all_geo_logs(self, limit: int = 100, offset: int = 0) -> list:
        if not self.client: return []
        try:
            response = self.client.table("geo_login_logs").select("*").order("timestamp", desc=True).limit(limit).offset(offset).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Erro ao buscar geo logs: {e}")
            return []

    # --- Métodos para Refresh Tokens ---
    async def store_refresh_token(self, user_id: uuid.UUID, token_str: str, expires_at: datetime, parent_token_str: Optional[str] = None) -> Optional[Dict]:
        if not self.client: return None
        token_hashed = hash_token(token_str)
        parent_hash = hash_token(parent_token_str) if parent_token_str else None
        
        data_to_insert = {
            "user_id": str(user_id),
            "token_hash": token_hashed,
            "expires_at": expires_at.isoformat(), # Supabase espera string ISO
            "issued_at": datetime.now(timezone.utc).isoformat()
        }
        if parent_hash:
            data_to_insert["parent_token_hash"] = parent_hash
            
        try:
            # print(f"Debug: Storing refresh token for user {user_id}, hash: {token_hashed[:10]}...")
            response = self.client.table("refresh_tokens").insert(data_to_insert).execute()
            # print(f"Debug: Store refresh token response: {response}")
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Erro ao armazenar refresh token (hash: {token_hashed[:10]}...): {e}")
            return None

    async def get_refresh_token_data_by_hash(self, token_str: str) -> Optional[Dict]:
        if not self.client: return None
        token_hashed = hash_token(token_str)
        try:
            # print(f"Debug: Getting refresh token by hash: {token_hashed[:10]}...")
            response = self.client.table("refresh_tokens").select("*").eq("token_hash", token_hashed).maybe_single().execute()
            # print(f"Debug: Get refresh token by hash response: {response}")
            return response.data if response.data else None
        except Exception as e:
            print(f"Erro ao buscar refresh token por hash (hash: {token_hashed[:10]}...): {e}")
            return None

    async def revoke_refresh_token(self, token_db_id: uuid.UUID) -> bool:
        """Marca um refresh token como revogado pelo seu ID de banco de dados."""
        if not self.client: return False
        try:
            # print(f"Debug: Revoking refresh token by DB ID: {token_db_id}")
            response = self.client.table("refresh_tokens").update({"revoked": True}).eq("id", str(token_db_id)).execute()
            # print(f"Debug: Revoke refresh token by ID response: {response}")
            # O Supabase Python client pode retornar um objeto de resposta mesmo que nada seja atualizado.
            # Para ter certeza, você pode verificar response.count se disponível, ou assumir sucesso se não houver erro.
            return True # Assumindo sucesso se não houver erro.
        except Exception as e:
            print(f"Erro ao revogar refresh token ID {token_db_id}: {e}")
            return False

    async def revoke_refresh_token_by_hash(self, token_str: str) -> bool:
        """Marca um refresh token como revogado pelo seu hash."""
        if not self.client: return False
        token_hashed = hash_token(token_str)
        try:
            # print(f"Debug: Revoking refresh token by hash: {token_hashed[:10]}...")
            response = self.client.table("refresh_tokens").update({"revoked": True}).eq("token_hash", token_hashed).eq("revoked", False).execute()
            # print(f"Debug: Revoke refresh token by hash response: {response}")
            return True
        except Exception as e:
            print(f"Erro ao revogar refresh token (hash: {token_hashed[:10]}...): {e}")
            return False

    async def revoke_all_user_refresh_tokens(self, user_id: uuid.UUID) -> bool:
        """Revoga todos os refresh tokens ativos de um usuário."""
        if not self.client: return False
        try:
            # print(f"Debug: Revoking all refresh tokens for user ID: {user_id}")
            response = self.client.table("refresh_tokens").update({"revoked": True}).eq("user_id", str(user_id)).eq("revoked", False).execute()
            # print(f"Debug: Revoke all user refresh tokens response: {response}")
            return True
        except Exception as e:
            print(f"Erro ao revogar todos os refresh tokens para o usuário {user_id}: {e}")
            return False

# Instância do serviço para ser usada nos routers
supabase_service = SupabaseService()
