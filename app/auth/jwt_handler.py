from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from app.core.config import settings # Importar APENAS 'settings'
from app.auth.schemas import TokenData

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    # Usar a chave do objeto settings
    encoded_jwt = jwt.encode(to_encode, settings.JWT_PRIVATE_KEY_CONTENT, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    # Usar a chave do objeto settings
    encoded_jwt = jwt.encode(to_encode, settings.JWT_PRIVATE_KEY_CONTENT, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str, credentials_exception: Exception) -> Optional[TokenData]:
    try:
        # Usar a chave do objeto settings
        payload = jwt.decode(token, settings.JWT_PUBLIC_KEY_CONTENT, algorithms=[settings.JWT_ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        token_type: Optional[str] = payload.get("type")
        
        if user_id is None or token_type is None:
            raise credentials_exception
        
        role: Optional[str] = payload.get("role")
        return TokenData(user_id=user_id, token_type=token_type, role=role)
    
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise credentials_exception
