from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple # Importar Tuple
from jose import jwt, JWTError
from app.core.config import settings
from app.auth.schemas import TokenData # Supondo que TokenData está em app.auth.schemas

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Adicionar 'iat' (issued at) é uma boa prática, embora não estritamente necessário por todos
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, settings.JWT_PRIVATE_KEY_CONTENT, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> Tuple[str, datetime]:
    """
    Cria um refresh token JWT.
    Retorna o token string e seu timestamp de expiração.
    """
    to_encode = data.copy()
    current_time_utc = datetime.now(timezone.utc)

    if expires_delta:
        expire_at_utc = current_time_utc + expires_delta
    else:
        expire_at_utc = current_time_utc + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire_at_utc,
        "iat": current_time_utc,
        "type": "refresh"
    })
    # O JTI (JWT ID) pode ser útil para identificar unicamente um token se necessário
    # import uuid
    # to_encode.update({"jti": str(uuid.uuid4())}) 
    
    encoded_jwt = jwt.encode(to_encode, settings.JWT_PRIVATE_KEY_CONTENT, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt, expire_at_utc

def verify_token(token: str, credentials_exception: Exception) -> Optional[TokenData]:
    """
    Verifica um token JWT (access ou refresh).
    Retorna TokenData se válido, caso contrário, levanta a credentials_exception.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY_CONTENT,
            algorithms=[settings.JWT_ALGORITHM],
            # options={"verify_aud": False} # Se você não usar 'aud' (audience)
        )
        user_id: Optional[str] = payload.get("sub") # 'sub' (subject) é o ID do usuário
        token_type: Optional[str] = payload.get("type")
        
        # Validações básicas do payload
        if user_id is None or token_type is None:
            # print("Debug: verify_token - user_id ou token_type ausente no payload.") # Debug
            raise credentials_exception
        
        # Adicionando role ao TokenData se presente no payload
        role: Optional[str] = payload.get("role") # 'role' é específico para seu access token
        
        return TokenData(user_id=user_id, token_type=token_type, role=role)
    
    except JWTError as e:
        # print(f"Debug: verify_token - JWTError: {e}, Token: {token[:20]}...") # Debug
        raise credentials_exception
    except Exception as e: # Captura outras exceções inesperadas durante a decodificação
        # print(f"Debug: verify_token - Erro inesperado: {e}") # Debug
        raise credentials_exception
