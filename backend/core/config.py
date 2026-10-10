from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trading System API"
    database_url: str = "postgresql+asyncpg://quant_user:change-me@postgres:5432/trading_system"
    redis_url: str = "redis://redis:6379/0"
    mt5_bridge_url: str = "http://mt5-bridge:5001"
    cors_origins: list[str] = ["http://localhost:3000"]
    fair_economy_calendar_url: str = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    kitco_news_rss_url: str = "https://news.kitco.com/rss/kitconewsfeed.xml"
    fxstreet_news_rss_url: str = "https://www.fxstreet.com/rss/news"
    finnhub_api_key: str | None = None
    finnhub_economic_calendar_enabled: bool = False
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()