# app/models/admin.py
from pydantic import BaseModel, Field
import uuid
from typing import Optional
from datetime import datetime

class Administrator(BaseModel):
    id: uuid.UUID
    username: str
    password_hash: str # Armazena o hash da senha
    client_hwid_identifier_hash: Optional[str] = None # Hash do HWID do cliente
    status: str = "active"
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Se você precisar de um método para verificar a senha no modelo (opcional)
    # from app.utils.security import verify_password
    # def check_password(self, plain_password: str) -> bool:
    #     return verify_password(plain_password, self.password_hash)
