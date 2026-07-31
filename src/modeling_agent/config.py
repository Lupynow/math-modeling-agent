from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Math Modeling Agent"
    app_mode: str = Field(default="fake", pattern="^(fake|production)$")
    log_level: str = "INFO"
    max_upload_bytes: int = 5 * 1024 * 1024
    knowledge_root: Path = Path("/workspace/knowledge/math-modeling-skills/skills")

    database_url: str = "mysql+pymysql://modeling:modeling@mysql:3306/modeling"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "math_modeling_knowledge_v1"

    chat_api_base: str = ""
    chat_api_key: str = ""
    chat_model: str = ""
    embedding_api_base: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""
    request_timeout_seconds: float = 45.0

    schema_version: str = "1.0"
    prompt_version: str = "solver-v2.0"

    @property
    def model_configured(self) -> bool:
        if self.app_mode == "fake":
            return True
        return bool(
            self.chat_api_base
            and self.chat_api_key
            and self.chat_model
            and self.embedding_api_base
            and self.embedding_api_key
            and self.embedding_model
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
