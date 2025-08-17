import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    TAVILY_API_KEY: str = os.environ.get("TAVILY_API_KEY", "")
    YT_API_KEY: str = os.environ.get("YT_API_KEY", "")
    MAX_CLAIMS: int = 10
    MAX_SOURCES_PER_CLAIM: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()



