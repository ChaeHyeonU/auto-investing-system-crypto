from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Auto Investing Backend"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/v1"
    environment: str = "dev"
    cors_origins: list[str] = ["http://localhost:3000"]
    database_url: str = "sqlite:///./auto_investing.db"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    stripe_webhook_secret: str = "whsec_test"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
