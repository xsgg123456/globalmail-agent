"""Server-only configuration. Never serialize this object to a response."""
import os
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)
    database_url: SecretStr = SecretStr("")
    object_root: Path = Path(".local-data/objects")
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:15173", "http://localhost:15173",
    )
    model_api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    model_name: str = ""
    model_base_url: str = ""
    embedding_api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    embedding_base_url: str = ""

    @field_validator("allowed_origins")
    @classmethod
    def local_origins(cls, origins: tuple[str, ...]) -> tuple[str, ...]:
        for origin in origins:
            parsed = urlsplit(origin)
            if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
                    or parsed.username or parsed.password or parsed.path
                    or parsed.query or parsed.fragment):
                raise ValueError("Origin must be a local HTTP origin")
        return origins

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.getenv("GLOBALMAIL_ALLOWED_ORIGINS")
        values = {
            "database_url": os.getenv("GLOBALMAIL_DATABASE_URL", ""),
            "object_root": os.getenv("GLOBALMAIL_OBJECT_ROOT", ".local-data/objects"),
            "model_api_key": os.getenv("LLM_API_KEY", ""),
            "model_name": os.getenv("LLM_MODEL", ""),
            "model_base_url": os.getenv("LLM_BASE_URL", ""),
            "embedding_api_key": os.getenv("GLOBALMAIL_EMBEDDING_API_KEY", ""),
            "embedding_base_url": os.getenv("GLOBALMAIL_EMBEDDING_BASE_URL", ""),
        }
        if origins is not None:
            values["allowed_origins"] = tuple(x.strip() for x in origins.split(",") if x.strip())
        return cls(**values)

