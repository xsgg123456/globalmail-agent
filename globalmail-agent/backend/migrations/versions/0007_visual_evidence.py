"""Frozen Phase 8 DDL snapshot; does not import mutable runtime metadata."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

metadata = sa.MetaData()
SCOPE_KEYS = ("workspace_id", "mode", "branch_id", "customer_id", "purpose")


def common():
    return [sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())]


def child(name, *columns):
    return sa.Table(name, metadata, *common(),
        sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("mode", sa.String(24), nullable=False), sa.Column("branch_id", sa.Uuid, nullable=False),
        sa.Column("customer_id", sa.Uuid, nullable=False), sa.Column("purpose", sa.String(80), nullable=False),
        sa.Column("conversation_id", sa.Uuid, nullable=False), *columns,
        sa.ForeignKeyConstraint(["conversation_id", *SCOPE_KEYS],
            ["conversations.id", *[f"conversations.{k}" for k in SCOPE_KEYS]]),
        sa.UniqueConstraint("id", *SCOPE_KEYS))


def fk(table, column):
    return sa.ForeignKeyConstraint([column, *SCOPE_KEYS],
        [f"{table}.id", *[f"{table}.{key}" for key in SCOPE_KEYS]])


def object_fk(column):
    return fk("objects", column)


def run_child(name, *columns):
    return child(name, sa.Column("run_id", sa.Uuid, nullable=False), *columns, fk("agent_runs", "run_id"))


message_attachments = child("message_attachments",
    sa.Column("message_id", sa.Uuid), sa.Column("position", sa.Integer),
    sa.Column("cid", sa.String(240)), sa.Column("filename", sa.String(240), nullable=False),
    sa.Column("mime_type", sa.String(80), nullable=False),
    sa.Column("size_bytes", sa.BigInteger, nullable=False),
    sa.Column("width", sa.Integer), sa.Column("height", sa.Integer),
    sa.Column("source_sha256", sa.String(64)), sa.Column("source_object_id", sa.Uuid),
    sa.Column("thumbnail_object_id", sa.Uuid),
    sa.Column("revision", sa.BigInteger, nullable=False, server_default="1"),
    sa.Column("evidence_epoch", sa.BigInteger, nullable=False, server_default="0"),
    sa.Column("status", sa.String(24), nullable=False, server_default="ready"),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("processing_run_id", sa.Uuid),
    sa.Column("failure_reason", sa.String(80)),
    sa.Column("manifest", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    object_fk("source_object_id"), object_fk("thumbnail_object_id"),
    fk("messages", "message_id"), fk("agent_runs", "processing_run_id"),
    sa.UniqueConstraint("message_id", "position"), sa.UniqueConstraint("message_id", "cid"),
    sa.UniqueConstraint("id", "conversation_id", *SCOPE_KEYS),
    sa.CheckConstraint("revision > 0 AND evidence_epoch >= 0"),
    sa.CheckConstraint("size_bytes BETWEEN 0 AND 10485760"),
    sa.CheckConstraint("(width IS NULL AND height IS NULL) OR (width > 0 AND height > 0 AND width::bigint * height <= 20000000)"),
    sa.CheckConstraint("(message_id IS NULL AND position IS NULL AND cid IS NULL) OR (message_id IS NOT NULL AND position BETWEEN 0 AND 3)"),
    sa.CheckConstraint("status IN ('ready','processing','understood','partial','unreadable','failed','missing','unsupported','revoked','cancelled')"))

visual_analyses = run_child("visual_analyses",
    sa.Column("body_object_id", sa.Uuid, nullable=False), object_fk("body_object_id"),
    sa.Column("context_hash", sa.String(64), nullable=False),
    sa.Column("model", sa.String(160), nullable=False),
    sa.Column("prompt_version", sa.String(80), nullable=False),
    sa.Column("preprocess_version", sa.String(80), nullable=False),
    sa.Column("attachment_manifest", JSONB, nullable=False),
    sa.UniqueConstraint("run_id"))

visual_evidence = child("visual_evidence",
    sa.Column("analysis_id", sa.Uuid), sa.Column("attachment_id", sa.Uuid, nullable=False),
    sa.Column("message_id", sa.Uuid, nullable=False),
    sa.Column("revision", sa.BigInteger, nullable=False),
    sa.Column("evidence_epoch", sa.BigInteger, nullable=False),
    sa.Column("kind", sa.String(40), nullable=False),
    sa.Column("body_object_id", sa.Uuid, nullable=False), object_fk("body_object_id"),
    sa.Column("source_sha256", sa.String(64), nullable=False),
    sa.Column("derived_view_hash", sa.String(64)),
    sa.Column("location", JSONB, nullable=False, server_default=sa.text("'{\"type\":\"full_image\"}'::jsonb")),
    sa.Column("supersedes_id", sa.Uuid),
    sa.Column("manual", sa.Boolean, nullable=False, server_default=sa.false()),
    fk("visual_analyses", "analysis_id"), fk("messages", "message_id"),
    fk("visual_evidence", "supersedes_id"),
    sa.ForeignKeyConstraint(["attachment_id", "conversation_id", *SCOPE_KEYS],
        ["message_attachments.id", "message_attachments.conversation_id", *[f"message_attachments.{k}" for k in SCOPE_KEYS]]),
    sa.CheckConstraint("revision >= 0 AND evidence_epoch >= 0"),
    sa.CheckConstraint("manual OR analysis_id IS NOT NULL"),
    sa.CheckConstraint("kind IN ('field_candidate','observation','hypothesis','uncertainty','risk_flag','manual_correction')"))

ATTACHMENT_TABLES = [message_attachments, visual_analyses, visual_evidence]


revision = "0007_visual_evidence"
down_revision = "0006_agent_results"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    metadata.reflect(conn, only=["workspaces", "objects", "conversations", "messages", "agent_runs"], extend_existing=True)
    target = conn.execute(sa.text("SELECT current_schema()")).scalar_one()
    existing = set(sa.inspect(conn).get_table_names(schema=target))
    for table in sa.sql.ddl.sort_tables(ATTACHMENT_TABLES):
        if table.name not in existing:
            table.create(conn, checkfirst=False)
    image_columns = {c["name"] for c in sa.inspect(conn).get_columns("message_attachments", schema=target)}
    if "failure_reason" not in image_columns:
        op.add_column("message_attachments", sa.Column("failure_reason", sa.String(80)))
    columns = {c["name"] for c in sa.inspect(conn).get_columns("cycle_budgets", schema=target)}
    if "image_views" not in columns:
        op.add_column("cycle_budgets", sa.Column("image_views", sa.BigInteger, nullable=False, server_default="0"))
    checks = {c["name"] for c in sa.inspect(conn).get_check_constraints("cycle_budgets", schema=target)}
    if "cycle_image_views_limit" not in checks:
        op.create_check_constraint("cycle_image_views_limit", "cycle_budgets", "image_views BETWEEN 0 AND 6")


def downgrade():
    raise RuntimeError("Image evidence downgrade requires an explicit preservation plan")
