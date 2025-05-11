from pydantic_settings import BaseSettings, SettingsConfigDict # Importar SettingsConfigDict
# from pathlib import Path # Não é mais necessário para as chaves aqui

class Settings(BaseSettings):
    APP_NAME: str = "CrosshairLab API"
    API_V1_STR: str = "/api/v1"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str # Use a service_role key se for criar usuários/manipular dados restritos

    # JWT
    # Estes campos serão preenchidos automaticamente pelo Pydantic-Settings
    # a partir dos Secret Files do Render (se os nomes coincidirem e secrets_dir estiver configurado)
    # ou de variáveis de ambiente.
    JWT_PRIVATE_KEY_CONTENT: str
    JWT_PUBLIC_KEY_CONTENT: str
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # GeoIP
    IPAPI_URL: str = "https://ipapi.co"

    # Rate Limiting (exemplo, pode ser ajustado)
    RATE_LIMIT_LOGIN_ATTEMPTS: str = "5/minute"

    # Configuração do modelo Pydantic
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        secrets_dir='/opt/render/project/src/', # ESSENCIAL: Diz ao Pydantic para procurar arquivos
                                                # com os nomes dos campos (ex: JWT_PRIVATE_KEY_CONTENT)
                                                # neste diretório. O Render coloca os Secret Files aqui.
        extra='ignore',                         # Ignora variáveis extras no .env que não estão no modelo.
        case_sensitive=False                    # Boa prática para variáveis de ambiente e nomes de arquivos.
    )

settings = Settings()

# REMOVA COMPLETAMENTE a seção abaixo que tentava ler as chaves de 'settings.JWT_PRIVATE_KEY_PATH'.
# A Pydantic-Settings com a configuração 'secrets_dir' acima já cuida disso.
# try:
#     JWT_PRIVATE_KEY_CONTENT = settings.JWT_PRIVATE_KEY_PATH.read_text()
#     JWT_PUBLIC_KEY_CONTENT = settings.JWT_PUBLIC_KEY_PATH.read_text()
# except FileNotFoundError:
#     # ...
#     exit(1)
