from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str
    app_version: str
    app_description: str
    app_docs_url: str
    app_redoc_url: str

    # security
    secret_key: str
    algorithm: str

    # token
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    # DB
    database_url: str

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env"
    )


@lru_cache()
def get_settings():
    return Settings() 