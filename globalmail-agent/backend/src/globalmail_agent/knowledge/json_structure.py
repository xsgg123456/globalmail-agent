"""Explicit content-only knowledge JSON/JSONL; no arbitrary runtime or fixture envelopes."""
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from globalmail_agent.application.conversation_lock import ServiceError


class ContentBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_id: str = Field(min_length=1, max_length=160, pattern=r"\S")
    type: Literal["heading", "paragraph", "list", "table"]
    text: str
    table_rows: list[list[str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def content(self):
        if not self.text.strip() and not any(cell.strip() for row in self.table_rows for cell in row):
            raise ValueError("empty_knowledge_content")
        if self.table_rows and self.type != "table":
            raise ValueError("table_structure_requires_table")
        return self


class KnowledgeContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["globalmail.knowledge/1"]
    document_type: Literal["troubleshooting_md", "case_md"]
    blocks: list[ContentBlock] = Field(min_length=1, max_length=10000)


class KnowledgeLine(ContentBlock):
    schema_version: Literal["globalmail.knowledge/1"]
    document_type: Literal["troubleshooting_md", "case_md"]


def validate_knowledge_structure(content: bytes, fmt: str):
    if fmt not in {"json", "jsonl"}:
        raise ServiceError("unsupported_format", 422)
    try:
        if fmt == "json":
            value = KnowledgeContent.model_validate_json(content)
            normalized = value.model_dump(mode="json")
            normalized.pop("schema_version")
            normalized["blocks"] = [{"id": f"json-{i + 1:04d}", **b} for i, b in enumerate(normalized["blocks"])]
            return normalized
        rows = [KnowledgeLine.model_validate_json(line) for line in content.decode("utf-8").splitlines() if line.strip()]
        if not rows or len(rows) > 10000 or len({r.document_type for r in rows}) != 1:
            raise ValueError()
        return {"document_type": rows[0].document_type,
            "blocks": [{"id": f"json-{i + 1:04d}", **{k: v for k, v in row.model_dump(mode="json").items() if k not in {"schema_version", "document_type"}}} for i, row in enumerate(rows)]}
    except (ValueError, UnicodeError, TypeError):
        raise ServiceError("invalid_knowledge_schema", 422) from None
