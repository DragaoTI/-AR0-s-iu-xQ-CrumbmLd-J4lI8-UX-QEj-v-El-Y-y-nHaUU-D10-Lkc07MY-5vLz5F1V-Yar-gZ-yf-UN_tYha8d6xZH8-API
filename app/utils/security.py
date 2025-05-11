# app/utils/security.py
import hashlib

def hash_token(token: str) -> str:
    """Gera um hash SHA256 para o token."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()
