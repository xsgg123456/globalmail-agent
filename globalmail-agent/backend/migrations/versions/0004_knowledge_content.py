"""Knowledge originals, immutable versions and rebuildable parsing artifacts."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op
metadata = sa.MetaData()
SCOPE_KEYS = ("workspace_id", "mode", "branch_id", "customer_id", "purpose")
def common():
    return [sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]
def scope_columns():
    return [sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("mode", sa.String(24), nullable=False), sa.Column("branch_id", sa.Uuid, nullable=False),
        sa.Column("customer_id", sa.Uuid, nullable=False), sa.Column("purpose", sa.String(80), nullable=False)]


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

revision = "0004_knowledge_content"
down_revision = "0003_business_catalog"
branch_labels = None
depends_on = None
TABLE_NAMES = tuple(metadata.tables)


def upgrade():
    conn = op.get_bind()
    metadata.reflect(conn, only=["workspaces", "objects"], extend_existing=True)
    metadata.create_all(conn, tables=[metadata.tables[n] for n in TABLE_NAMES], checkfirst=True)
    existing = {c["name"] for c in sa.inspect(conn).get_columns("jobs")}
    added = [sa.Column("knowledge_version_id", sa.Uuid), sa.Column("parse_generation", sa.BigInteger),
        sa.Column("parser_profile_id", sa.String(40)), sa.Column("document_fence", sa.BigInteger),
        sa.Column("row_version", sa.BigInteger, nullable=False, server_default="1"),
        sa.Column("stage", sa.String(40), nullable=False, server_default="queued"),
        sa.Column("error_code", sa.String(80)),
        sa.Column("retryable", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("not_before", sa.DateTime(timezone=True))]
    for column in added:
        if column.name not in existing:
            op.add_column("jobs", column)
    for name in ("conversation_id", "run_id", "cycle_id"):
        op.alter_column("jobs", name, nullable=True)
    checks = {c["name"] for c in sa.inspect(conn).get_check_constraints("jobs")}
    if "jobs_target" not in checks:
        op.create_check_constraint("jobs_target", "jobs",
            "(knowledge_version_id IS NULL AND conversation_id IS NOT NULL AND run_id IS NOT NULL AND cycle_id IS NOT NULL) OR "
            "(kind = 'knowledge' AND knowledge_version_id IS NOT NULL AND conversation_id IS NULL AND run_id IS NULL AND cycle_id IS NULL "
            "AND parse_generation IS NOT NULL AND parse_generation > 0 AND parser_profile_id IS NOT NULL "
            "AND document_fence IS NOT NULL AND document_fence > 0)")
    constraints = {c["name"] for c in sa.inspect(conn).get_foreign_keys("jobs")}
    if "jobs_knowledge_version_scope" not in constraints:
        op.create_foreign_key("jobs_knowledge_version_scope", "jobs", "document_versions",
            ["knowledge_version_id", *SCOPE_KEYS], ["id", *SCOPE_KEYS])
    if "documents_current_scope" not in {c["name"] for c in sa.inspect(conn).get_foreign_keys("documents")}:
        op.create_foreign_key("documents_current_scope", "documents", "document_versions",
            ["current_version_id", "id", *SCOPE_KEYS], ["id", "document_id", *SCOPE_KEYS])
    conn.execute(sa.text("""CREATE OR REPLACE FUNCTION immutable_knowledge() RETURNS trigger AS $$
    BEGIN
      IF TG_TABLE_NAME IN ('applicabilities','knowledge_reviews','policy_bundles','knowledge_parse_caches','knowledge_assets','blocks')
          AND NEW IS DISTINCT FROM OLD THEN RAISE EXCEPTION 'immutable_knowledge'; END IF;
      IF TG_TABLE_NAME = 'document_versions' THEN
        IF (
          NEW.document_id IS DISTINCT FROM OLD.document_id OR NEW.number IS DISTINCT FROM OLD.number OR
          NEW.title IS DISTINCT FROM OLD.title OR NEW.object_id IS DISTINCT FROM OLD.object_id OR
          NEW.source_sha256 IS DISTINCT FROM OLD.source_sha256 OR NEW.available_at IS DISTINCT FROM OLD.available_at OR
          NEW.source_manifest_sha256 IS DISTINCT FROM OLD.source_manifest_sha256 OR
          NEW.page_range IS DISTINCT FROM OLD.page_range OR NEW.page_count IS DISTINCT FROM OLD.page_count OR NEW.format IS DISTINCT FROM OLD.format OR
          NEW.applicability_sha256 IS DISTINCT FROM OLD.applicability_sha256)
          THEN RAISE EXCEPTION 'immutable_knowledge_version'; END IF;
      END IF;
      IF TG_TABLE_NAME IN ('documents','document_versions') AND (
          NEW.workspace_id IS DISTINCT FROM OLD.workspace_id OR NEW.mode IS DISTINCT FROM OLD.mode OR
          NEW.branch_id IS DISTINCT FROM OLD.branch_id OR NEW.customer_id IS DISTINCT FROM OLD.customer_id OR
          NEW.purpose IS DISTINCT FROM OLD.purpose) THEN RAISE EXCEPTION 'immutable_knowledge_scope'; END IF;
      IF TG_TABLE_NAME = 'documents' THEN
        IF (NEW.source_kind IS DISTINCT FROM OLD.source_kind OR
          NEW.source_reference IS DISTINCT FROM OLD.source_reference OR NEW.allowed_modes IS DISTINCT FROM OLD.allowed_modes OR
          NEW.usage_split IS DISTINCT FROM OLD.usage_split OR NEW.brand IS DISTINCT FROM OLD.brand OR
          NEW.document_type IS DISTINCT FROM OLD.document_type)
          THEN RAISE EXCEPTION 'immutable_knowledge_source'; END IF;
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql"""))
    for name in ('documents','document_versions','applicabilities','knowledge_reviews','policy_bundles','knowledge_parse_caches','knowledge_assets','blocks'):
        conn.execute(sa.text(f'DROP TRIGGER IF EXISTS immutable_source ON "{name}"'))
        conn.execute(sa.text(f'CREATE TRIGGER immutable_source BEFORE UPDATE ON "{name}" FOR EACH ROW EXECUTE FUNCTION immutable_knowledge()'))


def downgrade():
    raise RuntimeError("Knowledge downgrade requires an explicit preservation plan")
