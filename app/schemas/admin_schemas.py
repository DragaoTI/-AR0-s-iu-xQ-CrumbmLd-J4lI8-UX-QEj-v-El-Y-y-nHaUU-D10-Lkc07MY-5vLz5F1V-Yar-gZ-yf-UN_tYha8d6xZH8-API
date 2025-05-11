# app/schemas/admin_schemas.py
from pydantic import BaseModel, constr
from typing import Optional
import uuid
from datetime import datetime

class AdminBase(BaseModel):
    username: constr(min_length=3, max_length=50)

class AdminCreateSchema(AdminBase):
    password: constr(min_length=8)
    client_hwid_identifier: Optional[str] = None # HWID enviado pelo cliente no registro

class AdminLoginSchema(AdminBase):
    password: str
    client_hwid_identifier: str # HWID deve ser enviado no login para verificação

class AdminUpdateSchema(BaseModel):
    username: Optional[constr(min_length=3, max_length=50)] = None
    password: Optional[constr(min_length=8)] = None
    client_hwid_identifier: Optional[str] = None
    status: Optional[str] = None # 'active' ou 'inactive'

class AdminResponseSchema(AdminBase):
    id: uuid.UUID
    status: str
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Para Pydantic V2 (orm_mode no V1)

class AdminToken(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AdminTokenData(BaseModel):
    admin_id: Optional[str] = None
    # Você pode adicionar 'scopes' ou 'role' se tiver diferentes tipos de admins
