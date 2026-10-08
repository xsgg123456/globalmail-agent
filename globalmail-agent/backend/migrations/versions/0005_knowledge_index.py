"""Scoped immutable vector inputs, build manifests and publication snapshots."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from alembic import op
metadata = sa.MetaData()
SCOPE_KEYS = ("workspace_id", "mode", "branch_id", "customer_id", "purpose")
def scoped(name, *columns):
    return sa.Table(name, metadata,
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("mode", sa.String(24), nullable=False), sa.Column("branch_id", sa.Uuid, nullable=False),
        sa.Column("customer_id", sa.Uuid, nullable=False), sa.Column("purpose", sa.String(80), nullable=False),
        *columns, sa.UniqueConstraint("id", *SCOPE_KEYS))
def fk(table, column):
    return sa.ForeignKeyConstraint([column, *SCOPE_KEYS], [f"{table}.id", *[f"{table}.{k}" for k in SCOPE_KEYS]])


embedding_profiles = scoped("embedding_profiles",
    sa.Column("profile_key", sa.String(80), nullable=False),
    sa.Column("profile_sha256", sa.String(64), nullable=False),
    sa.Column("configuration", JSONB, nullable=False),
    sa.Column("dimensions", sa.Integer, nullable=False),
    sa.UniqueConstraint(*SCOPE_KEYS, "profile_sha256"), sa.CheckConstraint("dimensions = 1024"))
embedding_probes = scoped("embedding_probes",
    sa.Column("profile_id", sa.Uuid, nullable=False), sa.Column("probe_vector", Vector(1024), nullable=False),
    fk("embedding_profiles", "profile_id"), sa.UniqueConstraint("profile_id"))
index_builds = scoped("index_builds",
    sa.Column("document_id", sa.Uuid, nullable=False), sa.Column("version_id", sa.Uuid, nullable=False),
    sa.Column("profile_id", sa.Uuid, nullable=False), sa.Column("chunker_key", sa.String(80), nullable=False),
    sa.Column("chunker_configuration", JSONB, nullable=False), sa.Column("input_sha256", sa.String(64), nullable=False),
    sa.Column("source_sha256", sa.String(64), nullable=False), sa.Column("parse_sha256", sa.String(64), nullable=False),
    sa.Column("applicability_sha256", sa.String(64), nullable=False),
    *[sa.Column(k, sa.BigInteger, nullable=False) for k in ("document_fence", "revocation_epoch", "parse_generation")],
    sa.Column("status", sa.String(24), nullable=False), sa.Column("stage", sa.String(40), nullable=False),
    sa.Column("row_version", sa.BigInteger, nullable=False, server_default="1"),
    sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
    sa.Column("embedded_count", sa.Integer, nullable=False, server_default="0"),
    sa.Column("cache_hits", sa.Integer, nullable=False, server_default="0"),
    sa.Column("usage", JSONB, nullable=False, server_default="[]"), sa.Column("error_code", sa.String(80)),
    sa.Column("retryable", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("manifest_sha256", sa.String(64)), fk("documents", "document_id"), fk("embedding_profiles", "profile_id"),
    sa.ForeignKeyConstraint(["version_id", "document_id", *SCOPE_KEYS],
        ["document_versions.id", "document_versions.document_id", *[f"document_versions.{k}" for k in SCOPE_KEYS]]),
    sa.UniqueConstraint("id", "document_id", *SCOPE_KEYS),
    sa.CheckConstraint("status IN ('queued','indexing','ready','failed','cancelled')"),
    sa.CheckConstraint("chunk_count >= 0 AND embedded_count >= 0 AND cache_hits >= 0"))
index_parents = scoped("index_parents",
    sa.Column("build_id", sa.Uuid, nullable=False), sa.Column("position", sa.Integer, nullable=False),
    sa.Column("section_id", sa.String(160), nullable=False), sa.Column("text", sa.Text, nullable=False),
    sa.Column("content_sha256", sa.String(64), nullable=False), sa.Column("applicability", JSONB, nullable=False),
    sa.Column("locations", JSONB, nullable=False), sa.Column("proxy_tokens", sa.Integer, nullable=False),
    fk("index_builds", "build_id"), sa.UniqueConstraint("id", "build_id", *SCOPE_KEYS),
    sa.UniqueConstraint("build_id", "position"))
embedding_cache = scoped("embedding_cache",
    sa.Column("profile_id", sa.Uuid, nullable=False), sa.Column("input_sha256", sa.String(64), nullable=False),
    sa.Column("input_text", sa.Text, nullable=False), sa.Column("vector", Vector(1024), nullable=False),
    fk("embedding_profiles", "profile_id"), sa.UniqueConstraint(*SCOPE_KEYS, "profile_id", "input_sha256"))
index_chunks = scoped("index_chunks",
    sa.Column("build_id", sa.Uuid, nullable=False), sa.Column("parent_id", sa.Uuid, nullable=False),
    sa.Column("position", sa.Integer, nullable=False), sa.Column("input_text", sa.Text, nullable=False),
    sa.Column("input_sha256", sa.String(64), nullable=False), sa.Column("cache_id", sa.Uuid),
    fk("index_builds", "build_id"), fk("embedding_cache", "cache_id"),
    sa.ForeignKeyConstraint(["parent_id", "build_id", *SCOPE_KEYS],
        ["index_parents.id", "index_parents.build_id", *[f"index_parents.{k}" for k in SCOPE_KEYS]]),
    sa.UniqueConstraint("build_id", "position"))
knowledge_releases = scoped("knowledge_releases",
    sa.Column("profile_id", sa.Uuid), sa.Column("epoch", sa.BigInteger, nullable=False),
    sa.Column("operation", sa.String(24), nullable=False), sa.Column("manifest", JSONB, nullable=False),
    sa.Column("manifest_sha256", sa.String(64), nullable=False), sa.Column("actor", sa.String(160), nullable=False),
    sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False), fk("embedding_profiles", "profile_id"),
    sa.UniqueConstraint(*SCOPE_KEYS, "epoch"))
knowledge_release_items = scoped("knowledge_release_items",
    sa.Column("release_id", sa.Uuid, nullable=False), sa.Column("document_id", sa.Uuid, nullable=False),
    sa.Column("build_id", sa.Uuid, nullable=False), sa.Column("revocation_epoch", sa.BigInteger, nullable=False),
    fk("knowledge_releases", "release_id"), fk("documents", "document_id"),
    sa.ForeignKeyConstraint(["build_id", "document_id", *SCOPE_KEYS],
        ["index_builds.id", "index_builds.document_id", *[f"index_builds.{k}" for k in SCOPE_KEYS]]),
    sa.UniqueConstraint("release_id", "document_id"))
knowledge_release_heads = scoped("knowledge_release_heads",
    sa.Column("release_id", sa.Uuid), sa.Column("epoch", sa.BigInteger, nullable=False, server_default="0"),
    sa.Column("profile_id", sa.Uuid), fk("knowledge_releases", "release_id"), fk("embedding_profiles", "profile_id"),
    sa.UniqueConstraint(*SCOPE_KEYS), sa.UniqueConstraint("workspace_id", "purpose"))
evidence_refs = scoped("evidence_refs", sa.Column("release_id", sa.Uuid, nullable=False),
    sa.Column("build_id", sa.Uuid, nullable=False), sa.Column("document_id", sa.Uuid, nullable=False),
    sa.Column("revocation_epoch", sa.BigInteger, nullable=False), sa.Column("content_object_id", sa.Uuid, nullable=False),
    sa.Column("reference", JSONB, nullable=False), fk("knowledge_releases", "release_id"),
    fk("index_builds", "build_id"), fk("documents", "document_id"), fk("objects", "content_object_id"))
knowledge_dependencies = scoped("knowledge_dependencies",
    sa.Column("reference_id", sa.Uuid, nullable=False), sa.Column("source_object_id", sa.Uuid, nullable=False),
    sa.Column("content_object_id", sa.Uuid, nullable=False), sa.Column("holder_kind", sa.String(80), nullable=False),
    fk("evidence_refs", "reference_id"), fk("objects", "source_object_id"), fk("objects", "content_object_id"),
    sa.UniqueConstraint("reference_id", "source_object_id", "holder_kind"))

revision = "0005_knowledge_index"
down_revision = "0004_knowledge_content"
branch_labels = None
depends_on = None
TABLE_NAMES = tuple(metadata.tables)


def upgrade():
    conn = op.get_bind()
    # Reuse an installed extension read-only; new test installations stay in their private schema.
    extension = conn.execute(sa.text("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'")).scalar_one_or_none()
    if extension is None:
        conn.execute(sa.text("CREATE EXTENSION vector"))
        extension = conn.execute(sa.text("SELECT current_schema()")).scalar_one()
    conn.execute(sa.text("SELECT set_config('search_path', current_setting('search_path') || ',' || quote_ident(:namespace), true)"), {"namespace": extension})
    metadata.reflect(conn, only=["workspaces", "objects", "documents", "document_versions"], extend_existing=True)
    metadata.create_all(conn, tables=[metadata.tables[n] for n in TABLE_NAMES], checkfirst=True)
    additions = {"documents": [sa.Column("revocation_epoch", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("withdrawn", sa.Boolean, nullable=False, server_default=sa.false())],
        "jobs": [sa.Column("knowledge_operation", sa.String(24), nullable=False, server_default="parse"),
            sa.Column("index_build_id", sa.Uuid)]}
    for table, columns in additions.items():
        existing = {c["name"] for c in sa.inspect(conn).get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)
    if "jobs_index_build_scope" not in {c["name"] for c in sa.inspect(conn).get_foreign_keys("jobs")}:
        op.create_foreign_key("jobs_index_build_scope", "jobs", "index_builds", ["index_build_id", *SCOPE_KEYS], ["id", *SCOPE_KEYS])
    if "jobs_knowledge_operation" not in {c["name"] for c in sa.inspect(conn).get_check_constraints("jobs")}:
        op.create_check_constraint("jobs_knowledge_operation", "jobs", "knowledge_operation IN ('parse','index') AND (knowledge_operation = 'parse' AND index_build_id IS NULL OR knowledge_operation = 'index' AND index_build_id IS NOT NULL AND knowledge_version_id IS NOT NULL)")
    conn.execute(sa.text("""CREATE OR REPLACE FUNCTION immutable_knowledge_index() RETURNS trigger AS $$
      BEGIN
        IF NEW IS DISTINCT FROM OLD THEN RAISE EXCEPTION 'immutable_knowledge_index'; END IF;
        RETURN NEW;
      END; $$ LANGUAGE plpgsql"""))
    for name in ("embedding_profiles", "embedding_probes", "index_parents", "embedding_cache", "knowledge_releases", "knowledge_release_items", "evidence_refs", "knowledge_dependencies"):
        conn.execute(sa.text(f'DROP TRIGGER IF EXISTS immutable_index ON "{name}"'))
        conn.execute(sa.text(f'CREATE TRIGGER immutable_index BEFORE UPDATE ON "{name}" FOR EACH ROW EXECUTE FUNCTION immutable_knowledge_index()'))
    conn.execute(sa.text("""CREATE OR REPLACE FUNCTION guard_knowledge_index_state() RETURNS trigger AS $$
      BEGIN
        IF TG_TABLE_NAME = 'index_builds' AND
          (to_jsonb(NEW) - ARRAY['status','stage','row_version','chunk_count','embedded_count','cache_hits','usage','error_code','retryable','manifest_sha256','updated_at'])
          IS DISTINCT FROM
          (to_jsonb(OLD) - ARRAY['status','stage','row_version','chunk_count','embedded_count','cache_hits','usage','error_code','retryable','manifest_sha256','updated_at'])
          THEN RAISE EXCEPTION 'immutable_build_input'; END IF;
        IF TG_TABLE_NAME = 'index_chunks' THEN
          IF (to_jsonb(NEW) - ARRAY['cache_id','updated_at']) IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['cache_id','updated_at'])
            OR OLD.cache_id IS NOT NULL AND NEW.cache_id IS DISTINCT FROM OLD.cache_id
            THEN RAISE EXCEPTION 'immutable_chunk_input'; END IF;
        END IF;
        IF TG_TABLE_NAME = 'knowledge_release_heads' AND
          (to_jsonb(NEW) - ARRAY['release_id','epoch','profile_id','updated_at']) IS DISTINCT FROM
          (to_jsonb(OLD) - ARRAY['release_id','epoch','profile_id','updated_at'])
          THEN RAISE EXCEPTION 'immutable_release_scope'; END IF;
        RETURN NEW;
      END; $$ LANGUAGE plpgsql"""))
    for name in ('index_builds', 'index_chunks', 'knowledge_release_heads'):
        conn.execute(sa.text(f'DROP TRIGGER IF EXISTS guarded_index ON "{name}"'))
        conn.execute(sa.text(f'CREATE TRIGGER guarded_index BEFORE UPDATE ON "{name}" FOR EACH ROW EXECUTE FUNCTION guard_knowledge_index_state()'))


def downgrade():
    raise RuntimeError("Knowledge index downgrade requires an explicit preservation plan")
