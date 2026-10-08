"""Strict knowledge writes; scope and publication are never caller-selected."""
from datetime import datetime
from typing import Literal, Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0, strict=True)


class Applicability(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_id: str = Field(min_length=1, max_length=160, pattern=r"\S")
    sku: str = Field(min_length=1, max_length=160, pattern=r"\S")
    page_start: int | None = Field(default=None, ge=1, le=300, strict=True)
    page_end: int | None = Field(default=None, ge=1, le=300, strict=True)
    basis: str = Field(min_length=1, max_length=2000, pattern=r"\S")

    @model_validator(mode="after")
    def pages(self):
        if ((self.page_start is None) != (self.page_end is None)
                or self.page_start is not None and self.page_end < self.page_start):
            raise ValueError("invalid_page_range")
        return self


class VersionCommand(Command):
    title: str | None = Field(default=None, min_length=1, max_length=500, pattern=r"\S")
    object_id: UUID | None = None
    content: str | dict | None = None
    parser_profile_id: Literal["markdown", "policy", "mineru_basic", "mineru_standard"] | None = None
    applicabilities: list[Applicability] = Field(max_length=1000)
    page_range: list[Annotated[int, Field(ge=1, le=300, strict=True)]] | None = Field(default=None, min_length=2, max_length=2)

    @model_validator(mode="after")
    def source(self):
        if self.object_id is not None and self.content is not None:
            raise ValueError("one_source_required")
        if self.page_range and self.page_range[1] < self.page_range[0]:
            raise ValueError("invalid_page_range")
        return self


class CreateDocument(VersionCommand):
    title: str = Field(min_length=1, max_length=500, pattern=r"\S")
    document_type: Literal["manual_pdf", "troubleshooting_md", "case_md", "policy_json"]
    brand: Literal["OUTON", "OUTONLIFE", "BELEEV"] | None = None
    source_reference: str = Field(min_length=1, max_length=240, pattern=r"\S")
    available_at: datetime

    @field_validator("available_at")
    @classmethod
    def time(cls, value):
        if value.tzinfo is None:
            raise ValueError("timezone_required")
        return value


class ParseCommand(Command):
    parser_profile_id: Literal["markdown", "policy", "mineru_basic", "mineru_standard"]


class ReviewCommand(Command):
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parse_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    applicability_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    note: str = Field(min_length=1, max_length=5000, pattern=r"\S")
    excluded_block_ids: list[str] = Field(default_factory=list, max_length=10000)
    exclusion_reason: str | None = Field(default=None, max_length=5000)
