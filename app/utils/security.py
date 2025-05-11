# app/utils/security.py
import hashlib
from passlib.context import CryptContext

# Contexto para hashing de senhas
# Escolha os esquemas de hashing. bcrypt é uma boa escolha padrão.
# deprecated="auto" fará com que senhas antigas (se você mudar o esquema) sejam atualizadas no próximo login.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica uma senha plana contra um hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Gera um hash para uma senha."""
    return pwd_context.hash(password)

def hash_identifier(identifier: str) -> str:
    """Gera um hash SHA256 para um identificador (como o HWID do cliente)."""
    if not identifier: # Tratar caso o identificador seja None ou vazio
        return ""
    return hashlib.sha256(identifier.encode('utf-8')).hexdigest()

def hash_token(token: str) -> str:
    """Gera um hash SHA256 para o token."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()
