"""Configuração centralizada via pydantic-settings.

Lê variáveis de ambiente do arquivo `.env` (raiz do projeto) ou do shell.
Todas as configs do app passam por aqui — nada de `os.getenv` espalhado.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_env: str = "dev"
    log_level: str = "INFO"
    encryption_key: SecretStr = Field(..., description="Fernet key p/ criptografar tokens")

    # --- iFood ---
    ifood_client_id: SecretStr
    ifood_client_secret: SecretStr
    ifood_api_base_url: str = "https://merchant-api.ifood.com.br"
    ifood_auth_url: str = "https://merchant-api.ifood.com.br/authentication/v1.0/oauth/token"

    # --- Supabase ---
    supabase_url: str
    supabase_anon_key: SecretStr
    supabase_service_role_key: SecretStr
    supabase_jwt_secret: SecretStr | None = None  # pega em Settings → API → JWT Settings
    database_url: SecretStr

    # --- FastAPI ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Dashboard ---
    dashboard_port: int = 8501
    api_base_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
