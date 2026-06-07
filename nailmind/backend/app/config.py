"""Backend configuration management."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "NailMind Backend"
    DEBUG: bool = True
    CORS_ORIGINS: str = ""  # Comma-separated browser origins. Required when DEBUG=false.

    # Database (using SQLite for local dev, switch to PostgreSQL for production)
    DATABASE_URL: str = "sqlite:///./nailmind.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Service
    AI_SERVICE_URL: str = "http://localhost:8003"
    AI_WEBHOOK_SECRET: str = ""

    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    OPERATOR_PHONES: str = ""  # Comma-separated phones allowed to login as merchant/admin.
    SMS_PROVIDER: str = "debug"  # debug, none, webhook, or future provider adapter name.
    SMS_WEBHOOK_URL: str = ""  # HTTP endpoint used when SMS_PROVIDER=webhook.

    # Operations Agent channels
    OPERATIONS_AGENT_EXTERNAL_ENABLED: bool = True
    FEISHU_BOT_WEBHOOK_URL: str = ""
    OPERATIONS_AGENT_EXTERNAL_TOKEN: str = ""
    OPERATIONS_AGENT_SCHEDULER_INTERVAL_SECONDS: int = 30

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    PUBLIC_ASSET_BASE_URL: str = ""  # Optional CDN/API origin used for returned upload URLs.
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
