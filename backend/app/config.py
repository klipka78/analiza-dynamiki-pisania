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

    # Protokół badania
    min_sessions_per_user: int = 3
    min_users_for_model: int = 2
    min_events: int = 40
    min_duration_ms: float = 15000.0  # 15 s aktywnego pisania
    confidence_threshold: float = 0.45  # poniżej → niezidentyfikowano / odrzuć weryfikację
    protocol_task_id: str = "A"  # zalecany tekst do enrollu


@lru_cache
def get_settings() -> Settings:
    return Settings()
