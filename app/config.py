from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://shipa:shipa@localhost:5432/shipa"
    webhook_secret: str = "dev-webhook-secret-change-me"
    dashboard_api_key: str = "dev-dashboard-key-change-me"
    verification_max_attempts: int = 3
    frontend_origin: str = "http://localhost:3000"

    @field_validator("database_url")
    @classmethod
    def _force_psycopg_driver(cls, v: str) -> str:
        # Railway (and most managed PG) inject a bare postgresql:// URL, which
        # SQLAlchemy routes to psycopg2 — not installed. Pin the psycopg3 driver.
        if v.startswith("postgresql+"):
            return v
        if v.startswith("postgresql://"):
            return "postgresql+psycopg://" + v[len("postgresql://"):]
        if v.startswith("postgres://"):
            return "postgresql+psycopg://" + v[len("postgres://"):]
        return v


settings = Settings()
