"""Conversation-only image sources, immutable bindings and versioned visual evidence."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from globalmail_agent.adapters.conversation_schema import child, object_fk
from globalmail_agent.adapters.agent_schema import fk, run_child
from globalmail_agent.adapters.schema import SCOPE_KEYS


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
