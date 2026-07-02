from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_timeout_seconds: float = Field(default=30.0, alias="OPENAI_TIMEOUT_SECONDS")

    tavily_api_key: str = Field(..., alias="TAVILY_API_KEY")
    tavily_max_results: int = Field(default=5, alias="TAVILY_MAX_RESULTS")
    tavily_search_depth: str = Field(default="basic", alias="TAVILY_SEARCH_DEPTH")


@lru_cache
def get_settings() -> Settings:
    return Settings()
