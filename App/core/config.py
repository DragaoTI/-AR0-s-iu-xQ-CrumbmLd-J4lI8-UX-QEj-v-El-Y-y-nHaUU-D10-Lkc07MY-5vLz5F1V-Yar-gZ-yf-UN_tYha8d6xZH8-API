from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    APP_NAME: str = "CrosshairLab API"
    API_V1_STR: str = "/api/v1"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str # Use a service_role key se for criar usuários/manipular dados restritos

    # JWT
    JWT_PRIVATE_KEY_PATH: Path = Path("rsa_private_key.pem")
    JWT_PUBLIC_KEY_PATH: Path = Path("rsa_public_key.pem")
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # GeoIP
    IPAPI_URL: str = "https://ipapi.co"

    # Rate Limiting (exemplo, pode ser ajustado)
    RATE_LIMIT_LOGIN_ATTEMPTS: str = "5/minute"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        # Para ler as chaves diretamente do conteúdo do .env, se não forem paths
        # JWT_PRIVATE_KEY: str
        # JWT_PUBLIC_KEY: str

settings = Settings()

# Carregar o conteúdo das chaves dos arquivos
try:
    JWT_PRIVATE_KEY_CONTENT = settings.JWT_PRIVATE_KEY_PATH.read_text()
    JWT_PUBLIC_KEY_CONTENT = settings.JWT_PUBLIC_KEY_PATH.read_text()
except FileNotFoundError:
    print(f"ERRO FATAL: Arquivos de chave JWT não encontrados em {settings.JWT_PRIVATE_KEY_PATH} ou {settings.JWT_PUBLIC_KEY_PATH}")
    print("Certifique-se de que os arquivos rsa_private_key.pem e rsa_public_key.pem existem.")
    print("Você pode gerá-los com OpenSSL.")
    exit(1) # Ou raise uma exceção mais específica
