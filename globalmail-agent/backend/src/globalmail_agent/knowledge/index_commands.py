"""Strict build, release and read-only preview inputs."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from globalmail_agent.knowledge.commands import Command


class BuildCommand(Command):
    embedding_profile_key: Literal["qwen3.7-text-embedding", "text-embedding-v4"]
    chunking_profile_key: Literal["structure_v1_500", "structure_v1_300"]


class ReleaseCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_release_epoch: int = Field(ge=0, strict=True)
    build_ids: list[UUID] = Field(min_length=1, max_length=1000)
    replace_all: bool = False

    @field_validator("build_ids")
    @classmethod
    def unique(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("duplicate_build")
        return values


class RollbackCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_release_epoch: int = Field(ge=0, strict=True)


class WithdrawCommand(Command):
    expected_release_epoch: int = Field(ge=0, strict=True)


class SearchCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=4000, pattern=r"\S")
    sku: str = Field(min_length=1, max_length=160, pattern=r"\S")
    brand: Literal["OUTON", "OUTONLIFE", "BELEEV"] | None = None
    types: list[Literal["manual_pdf", "troubleshooting_md", "case_md", "policy_json"]] = Field(default_factory=list, max_length=4)
    mode: Literal["simulation", "history_replay"] = "simulation"
    as_of: datetime | None = None
    expected_release_epoch: int | None = Field(default=None, ge=0, strict=True)
    release_id: UUID | None = None

    @model_validator(mode="after")
    def time(self):
        if self.as_of is not None and self.as_of.tzinfo is None:
            raise ValueError("timezone_required")
        if self.mode == "history_replay" and self.as_of is None:
            raise ValueError("as_of_required")
        return self
