from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class GeoLogBase(BaseModel):
    ip_address: str
    user_agent: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class GeoLogCreate(GeoLogBase):
    user_id: uuid.UUID # Para associar ao usuário que logou

class GeoLogResponse(GeoLogBase):
    id: uuid.UUID
    user_id: uuid.UUID
    timestamp: datetime

    class Config:
        from_attributes = True
