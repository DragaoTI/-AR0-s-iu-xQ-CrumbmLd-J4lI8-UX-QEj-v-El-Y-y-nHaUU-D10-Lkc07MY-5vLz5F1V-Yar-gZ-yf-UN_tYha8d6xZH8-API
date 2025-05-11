from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid # Para o ID do usuário do Supabase

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    # Adicione outros campos que você tem no Supabase 'users' ou 'profiles'
    # Ex: full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    # Opcional: Adicionar metadata no momento da criação
    # user_metadata: Optional[dict] = {"role": "user"} # Default role

class UserResponse(UserBase):
    id: uuid.UUID # Supabase user ID é UUID
    role: Optional[str] = None # Para mostrar a role do usuário

    class Config:
        from_attributes = True # Necessário para Pydantic V2 (orm_mode no V1)
