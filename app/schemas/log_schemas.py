# app/schemas/log_schemas.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

class ApiLogResponseSchema(BaseModel):
    id: int
    timestamp: datetime
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    client_host: Optional[str] = None
    user_agent: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    admin_id: Optional[uuid.UUID] = None
    request_body: Optional[Dict[str, Any]] = None # Se decidir logar e expor
    response_body: Optional[Dict[str, Any]] = None# Se decidir logar e expor
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    tags: Optional[List[str]] = None

    class Config:
        from_attributes = True # Para Pydantic v2 (era orm_mode)
