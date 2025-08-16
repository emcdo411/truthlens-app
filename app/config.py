from pydantic import BaseSettings, AnyHttpUrl
from typing import Optional

class Settings(BaseSettings):
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None

    # Search providers (choose one you have a key for)
    TAVILY_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None

    # YouTube
    YT_API_KEY: Optional[str] = None  # if using official Data API

    # App
    MAX_CLAIMS: int = 10
    MAX_SOURCES_PER_CLAIM: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
