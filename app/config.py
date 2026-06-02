from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://shipa:shipa@localhost:5432/shipa"
    webhook_secret: str = "dev-webhook-secret-change-me"
    dashboard_api_key: str = "dev-dashboard-key-change-me"
    verification_max_attempts: int = 3


settings = Settings()
