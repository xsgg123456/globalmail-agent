"""Complete parser output; pixel preservation never proves image interpretation."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class ParserBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)
    section_id: str = "document"
    type: Literal["heading", "paragraph", "list", "table", "figure"]
    text: str = ""
    bbox: list[float] | None = None
    figure_id: str | None = None
    table_rows: list[list[str]] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)


class ParserAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    media_type: Literal["image/png", "image/jpeg", "image/webp", "application/json", "application/pdf"]
    kind: Literal["page_preview", "figure", "raw"]
    page: int | None = Field(default=None, ge=1)
    sha256: str | None = Field(default=None, pattern="^[a-f0-9]{64}$")


class ParserDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1)
    severity: Literal["warning", "error"]
    page: int | None = Field(default=None, ge=1)
    block_ids: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)
    message: str
    blocks_review: bool = False


class ParserResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["globalmail.parser/1"] = "globalmail.parser/1"
    source_sha256: str = Field(pattern="^[a-f0-9]{64}$")
    full_document: bool
    raw_document: dict[str, JsonValue] = Field(default_factory=dict)
    page_count: int = Field(ge=0, le=300)
    blocks: list[ParserBlock]
    assets: list[ParserAsset] = Field(default_factory=list)
    diagnostics: list[ParserDiagnostic] = Field(default_factory=list)
    parser_versions: dict[str, str]
    model_versions: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def consistent_references(self):
        block_ids = [block.id for block in self.blocks]
        asset_ids = [asset.id for asset in self.assets]
        if len(set(block_ids)) != len(block_ids) or len(set(asset_ids)) != len(asset_ids):
            raise ValueError("duplicate_parser_identifier")
        if any(block.page and block.page > self.page_count for block in self.blocks):
            raise ValueError("invalid_parser_page")
        if any(asset.page and asset.page > self.page_count for asset in self.assets):
            raise ValueError("invalid_asset_page")
        if any(not set(block.asset_ids) <= set(asset_ids) for block in self.blocks):
            raise ValueError("missing_parser_asset")
        return self
