from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trading System API"
    database_url: str = "postgresql+asyncpg://quant_user:change-me@postgres:5432/trading_system"
    redis_url: str = "redis://redis:6379/0"
    mt5_bridge_url: str = "http://mt5-bridge:5001"
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()