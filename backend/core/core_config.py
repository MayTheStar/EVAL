from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "RFP Analysis System"
    DEBUG: bool = True
    DATABASE_URL: str
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: Optional[str] = None  # ← اجعلها اختياري

    # هذه المتغيرات الجديدة
    MIN_TOKENS: int = 512
    MAX_TOKENS: int = 1024
    TOP_K_CHUNKS: int = 5
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    CHAT_MODEL: str = "gpt-4o-mini"

    class Config:
        env_file = str(Path(__file__).resolve().parents[2] / ".env")
        env_file_encoding = "utf-8"

settings = Settings()

