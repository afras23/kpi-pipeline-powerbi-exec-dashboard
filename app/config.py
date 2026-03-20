from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./data/processed/kpi_mart.db"
    raw_data_dir: str = "data/raw"
    env: str = "development"
    run_etl_on_startup: bool = False


settings = Settings()
