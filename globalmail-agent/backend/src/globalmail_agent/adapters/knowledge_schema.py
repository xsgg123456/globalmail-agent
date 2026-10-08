"""Knowledge originals, immutable versions and rebuildable parsing artifacts."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from globalmail_agent.adapters.schema import metadata, common, scope_columns, SCOPE_KEYS


def scoped(name, *columns):
    return sa.Table(name, metadata, *common(), *scope_columns(), *columns,
                    sa.UniqueConstraint("id", *SCOPE_KEYS))


def fk(table, column):
    return sa.ForeignKeyConstraint([column, *SCOPE_KEYS],
        [f"{table}.id", *[f"{table}.{k}" for k in SCOPE_KEYS]])


documents = scoped("documents",
    sa.Column("title", sa.String(500), nullable=False),
    sa.Column("document_type", sa.String(40), nullable=False),
    sa.Column("brand", sa.String(24)),
    sa.Column("source_kind", sa.String(80), nullable=False),
    sa.Column("source_reference", sa.String(240), nullable=False),
    sa.Column("allowed_modes", JSONB, nullable=False),
    sa.Column("usage_split", sa.String(40), nullable=False),
    sa.Column("prepared_id", sa.String(160)),
    sa.Column("row_version", sa.BigInteger, nullable=False, server_default="1"),
    sa.Column("document_fence", sa.BigInteger, nullable=False, server_default="1"),
    sa.Column("revocation_epoch", sa.BigInteger, nullable=False, server_default="0"),
    sa.Column("withdrawn", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("current_version_id", sa.Uuid),
    sa.Column("lifecycle", sa.String(24), nullable=False, server_default="active"),
    sa.UniqueConstraint("workspace_id", "prepared_id"),
    sa.CheckConstraint("document_type IN ('manual_pdf','troubleshooting_md','case_md','policy_json')"),
    sa.CheckConstraint("brand IS NULL OR brand IN ('OUTON','OUTONLIFE','BELEEV')"),
    sa.CheckConstraint("mode = 'simulation' AND purpose = 'knowledge' AND usage_split = 'rag'"))

document_versions = scoped("document_versions",
    sa.Column("document_id", sa.Uuid, nullable=False),
    sa.Column("number", sa.Integer, nullable=False), sa.Column("title", sa.String(500), nullable=False),
    sa.Column("object_id", sa.Uuid, nullable=False), sa.Column("format", sa.String(12), nullable=False),
    sa.Column("source_sha256", sa.String(64), nullable=False),
    sa.Column("source_manifest_sha256", sa.String(64)),
    sa.Column("page_count", sa.Integer), sa.Column("page_range", JSONB),
    sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("applicability_sha256", sa.String(64), nullable=False),
    sa.Column("parser_profile_id", sa.String(40), nullable=False),
    sa.Column("parser_fingerprint", sa.String(64), nullable=False),
    sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
    sa.Column("row_version", sa.BigInteger, nullable=False, server_default="1"),
    sa.Column("parse_generation", sa.BigInteger, nullable=False, server_default="0"),
    sa.Column("parse_sha256", sa.String(64)), sa.Column("cache_id", sa.Uuid),
    sa.Column("diagnostics", JSONB, nullable=False, server_default="[]"),
    fk("documents", "document_id"), fk("objects", "object_id"), fk("knowledge_parse_caches", "cache_id"),
    sa.UniqueConstraint("id", "document_id", *SCOPE_KEYS),
    sa.UniqueConstraint("document_id", "number"),
    sa.CheckConstraint("number > 0 AND row_version > 0 AND parse_generation >= 0"),
    sa.CheckConstraint("status IN ('draft','parsing','needs_review','reviewed','failed','cancelled')"))

applicabilities = scoped("applicabilities", sa.Column("version_id", sa.Uuid, nullable=False),
    sa.Column("section_id", sa.String(160), nullable=False), sa.Column("sku", sa.String(160), nullable=False),
    sa.Column("page_start", sa.Integer), sa.Column("page_end", sa.Integer),
    sa.Column("basis", sa.String(2000), nullable=False), fk("document_versions", "version_id"),
    sa.UniqueConstraint("version_id", "section_id", "sku"),
    sa.CheckConstraint("length(trim(section_id)) > 0 AND length(trim(sku)) > 0 AND length(trim(basis)) > 0"),
    sa.CheckConstraint("(page_start IS NULL AND page_end IS NULL) OR (page_start > 0 AND page_end >= page_start)"))

parse_caches = scoped("knowledge_parse_caches",
    sa.Column("source_sha256", sa.String(64), nullable=False),
    sa.Column("parser_profile_id", sa.String(40), nullable=False),
    sa.Column("parser_fingerprint", sa.String(64), nullable=False),
    sa.Column("result_object_id", sa.Uuid, nullable=False),
    sa.Column("parse_sha256", sa.String(64), nullable=False),
    sa.Column("asset_map", JSONB, nullable=False), fk("objects", "result_object_id"),
    sa.UniqueConstraint("workspace_id", "source_sha256", "parser_profile_id", "parser_fingerprint"))

blocks = scoped("blocks", sa.Column("version_id", sa.Uuid, nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("parse_generation", sa.BigInteger, nullable=False),
    sa.Column("block_key", sa.String(240), nullable=False),
    sa.Column("page", sa.Integer), sa.Column("section_id", sa.String(160), nullable=False),
    sa.Column("type", sa.String(40), nullable=False), sa.Column("text", sa.Text, nullable=False),
    sa.Column("structure", JSONB, nullable=False), fk("document_versions", "version_id"),
    sa.UniqueConstraint("version_id", "parse_generation", "block_key"))

knowledge_assets = scoped("knowledge_assets", sa.Column("cache_id", sa.Uuid, nullable=False),
    sa.Column("asset_key", sa.String(240), nullable=False), sa.Column("object_id", sa.Uuid, nullable=False),
    sa.Column("media_type", sa.String(80), nullable=False), sa.Column("kind", sa.String(40), nullable=False),
    sa.Column("page", sa.Integer), fk("knowledge_parse_caches", "cache_id"), fk("objects", "object_id"),
    sa.UniqueConstraint("cache_id", "asset_key"))

knowledge_reviews = scoped("knowledge_reviews", sa.Column("version_id", sa.Uuid, nullable=False),
    sa.Column("parse_generation", sa.BigInteger, nullable=False),
    sa.Column("source_sha256", sa.String(64), nullable=False),
    sa.Column("parse_sha256", sa.String(64), nullable=False),
    sa.Column("applicability_sha256", sa.String(64), nullable=False),
    sa.Column("actor", sa.String(160), nullable=False), sa.Column("note", sa.String(5000), nullable=False),
    sa.Column("excluded_block_ids", JSONB, nullable=False), sa.Column("exclusion_reason", sa.String(5000)),
    fk("document_versions", "version_id"), sa.UniqueConstraint("version_id", "parse_generation"))

knowledge_audits = scoped("knowledge_audits", sa.Column("document_id", sa.Uuid, nullable=False),
    sa.Column("version_id", sa.Uuid), sa.Column("action", sa.String(80), nullable=False),
    sa.Column("actor", sa.String(160), nullable=False), sa.Column("details", JSONB, nullable=False),
    fk("documents", "document_id"), fk("document_versions", "version_id"))

policy_bundles = scoped("policy_bundles", sa.Column("version_id", sa.Uuid, nullable=False),
    sa.Column("rules", JSONB, nullable=False), sa.Column("rule_schema", JSONB, nullable=False),
    sa.Column("rules_sha256", sa.String(64), nullable=False), sa.Column("schema_sha256", sa.String(64), nullable=False),
    sa.Column("description", sa.Text, nullable=False), sa.Column("description_sha256", sa.String(64), nullable=False),
    sa.Column("generator_version", sa.String(80), nullable=False), fk("document_versions", "version_id"),
    sa.UniqueConstraint("version_id"))

uploads = scoped("knowledge_uploads", sa.Column("object_id", sa.Uuid, nullable=False),
    sa.Column("filename", sa.String(240), nullable=False), sa.Column("format", sa.String(12), nullable=False),
    sa.Column("page_count", sa.Integer), fk("objects", "object_id"), sa.UniqueConstraint("object_id"))

documents.append_constraint(sa.ForeignKeyConstraint(["current_version_id", "id", *SCOPE_KEYS],
    ["document_versions.id", "document_versions.document_id", *[f"document_versions.{k}" for k in SCOPE_KEYS]],
    name="documents_current_scope", use_alter=True))
