from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    domain: str = "localhost"
    public_url: str = "http://localhost"
    admin_token: str = "changeme"
    app_env: str = "development"
    database_url: str = "sqlite:////data/keystroke.db"
    host_port: int = 80


@lru_cache
def get_settings() -> Settings:
    return Settings()
