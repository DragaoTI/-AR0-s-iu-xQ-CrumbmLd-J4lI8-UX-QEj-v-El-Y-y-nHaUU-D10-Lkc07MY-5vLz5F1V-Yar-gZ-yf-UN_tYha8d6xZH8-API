from supabase import create_client, Client
from app.core.config import settings
from app.schemas.user_schemas import UserCreate
from app.models.user import User
from app.schemas.geo_log_schemas import GeoLogCreate
from typing import Optional, Dict, Any
import uuid

class SupabaseService:
    def __init__(self):
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        try:
            # Supabase não tem um "get user by id" direto no client.auth se não for o usuário atual
            # Usaremos admin para buscar, assumindo que SUPABASE_KEY é service_role
            # response = self.client.auth.admin.get_user_by_id(user_id) # Descontinuado/Alterado
            
            # Alternativa: buscar na tabela 'auth.users' via PostgREST
            # Ou, se você tem uma tabela 'profiles' sincronizada:
            # response = self.client.table("profiles").select("*").eq("id", str(user_id)).single().execute()
            
            # Para este exemplo, vamos assumir que a informação do usuário (incluindo role)
            # está no token ou será buscada de uma tabela `profiles` ou `user_metadata`.
            # Se estiver usando `user_metadata` para role:
            user_data_res = self.client.auth.admin.get_user_by_id(str(user_id)) # Precisa de service_role key
            if user_data_res:
                supabase_user = user_data_res.user
                # print(f"Supabase User Data for {user_id}: {supabase_user}") # Debug
                role = supabase_user.user_metadata.get("role", "user") if supabase_user.user_metadata else "user"
                return User(
                    id=supabase_user.id,
                    email=supabase_user.email,
                    is_active=True, # Supabase não tem is_active direto, assumimos true se existe
                    role=role,
                    user_metadata=supabase_user.user_metadata
                )
            return None
        except Exception as e:
            print(f"Erro ao buscar usuário {user_id} no Supabase: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        # Este método é mais para verificar se o email existe antes de tentar login
        # O login real é feito com sign_in_with_password
        try:
            # Para verificar se um usuário existe com este email e pegar seus metadados (como role)
            # response = self.client.from_("users").select("id, email, raw_user_meta_data").eq("email", email).single().execute() # Se acesso direto à tabela auth.users
            # A maneira mais segura com a service_role key é listar usuários com filtro, o que não é ideal para um único.
            # Para este exemplo, o login irá validar, e o get_user_by_id será usado após o login bem-sucedido
            # ou na decodificação do token.
            # Se precisar verificar a existência ANTES de chamar sign_in_with_password:
            # users_res = self.client.auth.admin.list_users(filters={"email": email})
            # if users_res and users_res.users:
            #     sb_user = users_res.users[0]
            #     role = sb_user.user_metadata.get("role", "user") if sb_user.user_metadata else "user"
            #     return User(id=sb_user.id, email=sb_user.email, role=role, user_metadata=sb_user.user_metadata)
            return None # Deixe o sign_in_with_password tratar a existência
        except Exception as e:
            print(f"Erro ao buscar usuário por email {email} no Supabase: {e}")
            return None


    async def create_user(self, user_create: UserCreate) -> Optional[User]:
        try:
            # Adiciona 'role' ao user_metadata se não estiver presente
            user_metadata_with_role = user_create.model_dump().get("user_metadata", {})
            if "role" not in user_metadata_with_role:
                user_metadata_with_role["role"] = "user"

            response = self.client.auth.admin.create_user( # Use create_user com admin para definir metadata
                email=user_create.email,
                password=user_create.password,
                email_confirm=True, # Ou False se você não quer confirmação de email inicialmente
                user_metadata=user_metadata_with_role
            )
            # print(f"Create user response: {response}") # Debug
            if response and response.user:
                created_user = response.user
                return User(
                    id=created_user.id,
                    email=created_user.email,
                    is_active=True, # Assumindo ativo após criação
                    role=created_user.user_metadata.get("role", "user"),
                    user_metadata=created_user.user_metadata
                )
            # print(f"Falha ao criar usuário no Supabase. Resposta: {response}") # Debug
            return None
        except Exception as e:
            print(f"Erro ao criar usuário no Supabase: {e}") # Log detalhado do erro
            # from supabase.lib.client_async_gotrue import APIError as GoTrueAPIError
            # if isinstance(e, GoTrueAPIError):
            #     print(f"GoTrue API Error: {e.message}, Status: {e.status}")
            return None

    async def login_user(self, email: str, password: str) -> Optional[User]:
        try:
            response = self.client.auth.sign_in_with_password({"email": email, "password": password})
            if response and response.user:
                # Após o login, precisamos pegar os metadados do usuário, incluindo a role.
                # A resposta de sign_in_with_password pode não ter tudo.
                # Usaremos get_user_by_id que definimos para pegar a role do user_metadata.
                return await self.get_user_by_id(response.user.id)
            return None
        except Exception as e:
            print(f"Erro ao logar usuário no Supabase: {e}")
            return None

    async def add_geo_log(self, log_data: GeoLogCreate) -> bool:
        try:
            # print(f"Tentando adicionar geo log: {log_data.model_dump()}") # Debug
            response = self.client.table("geo_login_logs").insert(log_data.model_dump()).execute()
            # print(f"Resposta do add_geo_log: {response}") # Debug
            return len(response.data) > 0 if response.data is not None else False
        except Exception as e:
            print(f"Erro ao adicionar geo log no Supabase: {e}")
            return False

    async def get_all_geo_logs(self, limit: int = 100, offset: int = 0) -> list:
        try:
            response = self.client.table("geo_login_logs").select("*").order("timestamp", desc=True).limit(limit).offset(offset).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Erro ao buscar geo logs: {e}")
            return []

# Instância do serviço para ser usada nos routers
supabase_service = SupabaseService()
