# app/auth/admin_jwt_handler.py
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from app.core.config import settings # Usaremos as mesmas chaves RSA, mas poderíamos ter chaves dedicadas
from app.schemas.admin_schemas import AdminTokenData # Schema específico para payload do admin token

# Usar as mesmas chaves do JWT principal, mas com um "tipo" diferente no payload
# Ou, se você quiser chaves diferentes para admins, defina-as em config.py
# e use aqui (ex: settings.ADMIN_JWT_PRIVATE_KEY_CONTENT)

ADMIN_JWT_ALGORITHM = settings.JWT_ALGORITHM
ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8 # 8 horas, por exemplo

def create_admin_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "admin_access" # Tipo específico para token de admin
    })
    # Usando as mesmas chaves RSA do sistema principal de usuários
    encoded_jwt = jwt.encode(to_encode, settings.JWT_PRIVATE_KEY_CONTENT, algorithm=ADMIN_JWT_ALGORITHM)
    return encoded_jwt

def verify_admin_token(token: str, credentials_exception: Exception) -> Optional[AdminTokenData]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY_CONTENT, # Usando as mesmas chaves RSA
            algorithms=[ADMIN_JWT_ALGORITHM]
        )
        admin_id_str: Optional[str] = payload.get("sub") # admin_id como 'subject'
        token_type: Optional[str] = payload.get("type")
        
        if admin_id_str is None or token_type != "admin_access":
            raise credentials_exception
        
        return AdminTokenData(admin_id=admin_id_str)
    except JWTError:
        raise credentials_exception
    except Exception:
        raise credentials_exception
