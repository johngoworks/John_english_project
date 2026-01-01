from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "English Learning App"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./english_learning.db"

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Groq AI
    GROQ_API_KEY: str
    GROQ_MODEL: str = "qwen/qwen3-32b"

    # Redis (optional for caching)
    REDIS_URL: str = "redis://localhost:6379"
    USE_REDIS: bool = False

    # Progress thresholds
    GRAMMAR_COMPLETION_THRESHOLD: int = 80  # %
    VOCAB_COMPLETION_THRESHOLD: int = 80  # %
    REQUIRED_CORRECT_ATTEMPTS: int = 3  # To mark grammar as completed

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
