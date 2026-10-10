"""Persistent deletion orchestration; manifests contain identifiers, never body text."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from globalmail_agent.adapters.schema import metadata, common, scope_columns

journal_receipts = sa.Table("journal_receipts", metadata,
    sa.Column("request_id", sa.Uuid, primary_key=True),
    sa.Column("workspace_id", sa.Uuid, nullable=False),
    sa.Column("seq", sa.BigInteger, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

deletion_requests = sa.Table("deletion_requests", metadata, *common(), *scope_columns(),
    sa.Column("target_type", sa.String(24), nullable=False),
    sa.Column("target_id", sa.Uuid, nullable=False),
    sa.Column("action", sa.String(24), nullable=False),
    sa.Column("expected_version", sa.BigInteger, nullable=False),
    sa.Column("status", sa.String(32), nullable=False),
    sa.Column("manifest", JSONB, nullable=False),
    sa.Column("error_code", sa.String(80)),
    sa.Column("journal_seq", sa.BigInteger, nullable=False),
    sa.Column("replacement_conversation_id", sa.Uuid),
    sa.CheckConstraint("target_type IN ('conversation','document','attachment')"),
    sa.CheckConstraint("action IN ('delete','reset')"),
    sa.CheckConstraint("status IN ('revoked','purging','verifying','completed','cleanup_failed','blocked_dependencies')"),
    sa.UniqueConstraint("workspace_id", "target_type", "target_id"))
