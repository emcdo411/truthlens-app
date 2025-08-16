# app/config.py
from typing import Optional
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None

    # Search providers
    TAVILY_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None

    # YouTube
    YT_API_KEY: Optional[str] = None  # if using official Data API

    # App
    MAX_CLAIMS: int = 10
    MAX_SOURCES_PER_CLAIM: int = 5

    # pydantic v2 settings config
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()


