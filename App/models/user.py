from pydantic import BaseModel, EmailStr, Field
import uuid
from typing import Optional, Dict, Any

class User(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool = True
    role: Optional[str] = "user" # Default role
    user_metadata: Optional[Dict[str, Any]] = Field(default_factory=lambda: {"role": "user"})
    # Outros campos que você espera do Supabase user object
    # app_metadata: Optional[Dict[str, Any]] = None
    # created_at: Optional[datetime] = None
    # ...
