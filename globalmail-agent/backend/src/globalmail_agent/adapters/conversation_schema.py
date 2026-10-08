"""Scoped Phase 3 tables; every child relationship carries all scope dimensions."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from globalmail_agent.adapters.schema import metadata, common, scope_columns, SCOPE_KEYS


def scoped(name, *columns, **kwargs):
    return sa.Table(name, metadata, *common(), *scope_columns(), *columns, **kwargs)


def conv_fk():
    return sa.ForeignKeyConstraint(["conversation_id", *SCOPE_KEYS],
        ["conversations.id", *[f"conversations.{k}" for k in SCOPE_KEYS]])


def object_fk(column):
    return sa.ForeignKeyConstraint([column, *SCOPE_KEYS],
        ["objects.id", *[f"objects.{k}" for k in SCOPE_KEYS]])


def child(name, *columns):
    return scoped(name, sa.Column("conversation_id", sa.Uuid, nullable=False), *columns,
                  conv_fk(), sa.UniqueConstraint("id", *SCOPE_KEYS))


identities = sa.Table("identities", metadata, *common(),
    sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
    sa.Column("dataset_id", sa.Uuid, nullable=False), sa.Column("mode", sa.String(24), nullable=False),
    sa.Column("sender_key", sa.String(320), nullable=False),
    sa.Column("verified", sa.Boolean, nullable=False), sa.Column("source_ref", sa.String(240), nullable=False),
    sa.UniqueConstraint("workspace_id", "dataset_id", "mode", "sender_key"),
    sa.UniqueConstraint("id", "workspace_id", "dataset_id", "mode"))

conversations = scoped("conversations",
    sa.Column("dataset_id", sa.Uuid, nullable=False), sa.Column("identity_id", sa.Uuid, nullable=False),
    sa.Column("subject", sa.String(500), nullable=False, server_default=""),
    *[sa.Column(k, sa.BigInteger, nullable=False, server_default=str(v)) for k, v in (
        ("row_version", 1), ("input_revision", 0), ("authority_epoch", 0), ("branch_generation", 1),
        ("case_revision", 0), ("visible_message_seq", 0), ("next_seq", 0), ("received_seq", 0))],
    sa.Column("human_reply_after_seq", sa.BigInteger),
    sa.Column("lifecycle", sa.String(24), nullable=False, server_default="open"),
    sa.Column("processing_owner", sa.String(24), nullable=False, server_default="agent"),
    sa.Column("auto_run_gate", sa.String(24), nullable=False, server_default="open"),
    sa.Column("scheduling_state", sa.String(24), nullable=False, server_default="idle"),
    sa.ForeignKeyConstraint(["identity_id", "workspace_id", "dataset_id", "mode"],
        ["identities.id", "identities.workspace_id", "identities.dataset_id", "identities.mode"]),
    sa.UniqueConstraint("identity_id"), sa.UniqueConstraint("id", *SCOPE_KEYS),
    sa.UniqueConstraint("id", "workspace_id"),
    sa.CheckConstraint("mode IN ('simulation','historical_replay')"),
    sa.CheckConstraint("lifecycle IN ('open','resolved','deleting','deleted')"),
    sa.CheckConstraint("processing_owner IN ('agent','human_review','human_wait_customer')"),
    sa.CheckConstraint("auto_run_gate IN ('open','manual_retry_required','disabled')"))

messages = child("messages", sa.Column("seq", sa.BigInteger, nullable=False),
    sa.Column("received_seq", sa.BigInteger, nullable=False),
    sa.Column("source_ref", sa.String(240), nullable=False),
    sa.Column("source_message_id", sa.String(160), nullable=False),
    sa.Column("sender", sa.String(24), nullable=False),
    sa.Column("subject", sa.String(500), nullable=False, server_default=""),
    sa.Column("body_object_id", sa.Uuid, nullable=False),
    sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False), object_fk("body_object_id"),
    sa.UniqueConstraint("conversation_id", "seq"),
    sa.UniqueConstraint("conversation_id", "source_ref", "source_message_id"),
    sa.CheckConstraint("sender IN ('customer','historical_staff','simulated_human','simulated_agent')"))

replay_cursors = child("replay_cursors", sa.Column("position", sa.Integer, nullable=False),
    sa.Column("total_customer_messages", sa.Integer, nullable=False),
    sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
    sa.Column("finished", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.UniqueConstraint("conversation_id"))

processing_cycles = child("processing_cycles", sa.Column("trigger_id", sa.Uuid, nullable=False),
    sa.Column("trigger_message_id", sa.Uuid, nullable=False),
    *[sa.Column(k, sa.BigInteger, nullable=False) for k in
      ("input_revision", "authority_epoch", "branch_generation")],
    sa.Column("state", sa.String(24), nullable=False, server_default="queued"),
    sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("final_message_id", sa.Uuid),
    sa.UniqueConstraint("conversation_id", "trigger_id"),
    sa.ForeignKeyConstraint(["trigger_message_id", *SCOPE_KEYS],
        ["messages.id", *[f"messages.{k}" for k in SCOPE_KEYS]]),
    sa.ForeignKeyConstraint(["final_message_id", *SCOPE_KEYS],
        ["messages.id", *[f"messages.{k}" for k in SCOPE_KEYS]]),
    sa.CheckConstraint("input_revision > 0"))

agent_runs = child("agent_runs", sa.Column("processing_cycle_id", sa.Uuid, nullable=False),
    sa.Column("attempt_no", sa.Integer, nullable=False), sa.Column("status", sa.String(24), nullable=False),
    *[sa.Column(k, sa.BigInteger, nullable=False) for k in
      ("input_revision", "authority_epoch", "branch_generation")],
    sa.Column("trigger_id", sa.Uuid, nullable=False),
    sa.Column("stop_requested", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("checkpoint_writable", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.Column("error_code", sa.String(80)), sa.Column("outcome", sa.String(80)),
    sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("finished_at", sa.DateTime(timezone=True)),
    sa.ForeignKeyConstraint(["processing_cycle_id", *SCOPE_KEYS],
        ["processing_cycles.id", *[f"processing_cycles.{k}" for k in SCOPE_KEYS]]),
    sa.UniqueConstraint("processing_cycle_id", "attempt_no"))

jobs = scoped("jobs", sa.Column("conversation_id", sa.Uuid), sa.Column("run_id", sa.Uuid),
    sa.Column("cycle_id", sa.Uuid), sa.Column("kind", sa.String(24), nullable=False),
    sa.Column("status", sa.String(24), nullable=False), sa.Column("lease_owner", sa.String(160)),
    sa.Column("lease_expires_at", sa.DateTime(timezone=True)), sa.Column("slot_fence", sa.BigInteger),
    sa.Column("attempt_no", sa.Integer, nullable=False),
    sa.Column("knowledge_version_id", sa.Uuid), sa.Column("parse_generation", sa.BigInteger),
    sa.Column("knowledge_operation", sa.String(24), nullable=False, server_default="parse"),
    sa.Column("index_build_id", sa.Uuid),
    sa.Column("parser_profile_id", sa.String(40)), sa.Column("document_fence", sa.BigInteger),
    sa.Column("row_version", sa.BigInteger, nullable=False, server_default="1"),
    sa.Column("stage", sa.String(40), nullable=False, server_default="queued"),
    sa.Column("error_code", sa.String(80)),
    sa.Column("retryable", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("not_before", sa.DateTime(timezone=True)), conv_fk(),
    sa.UniqueConstraint("id", *SCOPE_KEYS),
    sa.ForeignKeyConstraint(["knowledge_version_id", *SCOPE_KEYS],
        ["document_versions.id", *[f"document_versions.{k}" for k in SCOPE_KEYS]]),
    sa.CheckConstraint("(knowledge_version_id IS NULL AND conversation_id IS NOT NULL AND run_id IS NOT NULL AND cycle_id IS NOT NULL) OR "
        "(kind = 'knowledge' AND knowledge_version_id IS NOT NULL AND conversation_id IS NULL AND run_id IS NULL AND cycle_id IS NULL "
        "AND parse_generation IS NOT NULL AND parse_generation > 0 AND parser_profile_id IS NOT NULL "
        "AND document_fence IS NOT NULL AND document_fence > 0)", name="jobs_target"),
    sa.ForeignKeyConstraint(["run_id", *SCOPE_KEYS],
        ["agent_runs.id", *[f"agent_runs.{k}" for k in SCOPE_KEYS]]),
    sa.ForeignKeyConstraint(["cycle_id", *SCOPE_KEYS],
        ["processing_cycles.id", *[f"processing_cycles.{k}" for k in SCOPE_KEYS]]),
    sa.UniqueConstraint("run_id"), sa.CheckConstraint("kind IN ('agent','knowledge')"))

agent_slots = sa.Table("agent_slots", metadata, *common(),
    sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
    sa.Column("slot_key", sa.String(24), nullable=False), sa.Column("lease_owner", sa.String(160)),
    sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
    sa.Column("fence", sa.BigInteger, nullable=False, server_default="0"), sa.Column("job_id", sa.Uuid),
    sa.UniqueConstraint("workspace_id", "slot_key"),
    sa.CheckConstraint("slot_key IN ('agent','knowledge')"))

domain_events = child("domain_events", sa.Column("source", sa.String(80), nullable=False),
    sa.Column("source_event_id", sa.String(160), nullable=False),
    sa.Column("kind", sa.String(80), nullable=False), sa.Column("payload", JSONB, nullable=False),
    sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
    sa.UniqueConstraint("conversation_id", "source", "source_event_id"))

ui_events = child("ui_events", sa.Column("seq", sa.BigInteger, nullable=False),
    sa.Column("kind", sa.String(80), nullable=False), sa.Column("payload", JSONB, nullable=False),
    sa.UniqueConstraint("conversation_id", "seq"))

human_reviews = child("human_reviews", sa.Column("status", sa.String(24), nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
    sa.Column("input_revision", sa.BigInteger, nullable=False), sa.Column("reason", sa.String(500), nullable=False),
    sa.Column("visible_message_seq", sa.BigInteger, nullable=False, server_default="0"),
    sa.Column("as_of", sa.DateTime(timezone=True)),
    *[sa.Column(k, sa.Uuid) for k in ("draft_object_id", "note_object_id", "reply_object_id")],
    *[object_fk(k) for k in ("draft_object_id", "note_object_id", "reply_object_id")])
sa.Index("one_open_human_review", human_reviews.c.conversation_id, unique=True,
         postgresql_where=human_reviews.c.status == "open")

case_issues = child("case_issues", sa.Column("issue_key", sa.String(160), nullable=False),
    sa.Column("status", sa.String(24), nullable=False), sa.Column("version", sa.BigInteger, nullable=False),
    sa.UniqueConstraint("conversation_id", "issue_key"))

case_facts = child("case_facts", sa.Column("issue_id", sa.Uuid, nullable=False),
    sa.Column("source_message_id", sa.Uuid, nullable=False), sa.Column("kind", sa.String(40), nullable=False),
    sa.Column("value_object_id", sa.Uuid, nullable=False), sa.Column("revision", sa.BigInteger, nullable=False),
    sa.Column("visible_seq", sa.BigInteger, nullable=False), object_fk("value_object_id"),
    sa.ForeignKeyConstraint(["issue_id", *SCOPE_KEYS],
        ["case_issues.id", *[f"case_issues.{k}" for k in SCOPE_KEYS]]),
    sa.ForeignKeyConstraint(["source_message_id", *SCOPE_KEYS],
        ["messages.id", *[f"messages.{k}" for k in SCOPE_KEYS]]),
    sa.CheckConstraint("kind IN ('customer_report','historical_claim','visual_observation','tool_fact','human_decision','model_inference')"),
    sa.UniqueConstraint("conversation_id", "source_message_id", "kind"))

case_revisions = child("case_revisions", sa.Column("revision", sa.BigInteger, nullable=False),
    sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
    sa.Column("visible_message_seq", sa.BigInteger, nullable=False),
    sa.Column("source", sa.String(80), nullable=False), sa.UniqueConstraint("conversation_id", "revision"))

data_imports = sa.Table("data_imports", metadata, *common(),
    sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
    sa.Column("source_ref", sa.String(240), nullable=False),
    sa.Column("source_conversation_id", sa.String(160), nullable=False),
    sa.Column("split", sa.String(80), nullable=False), sa.Column("group_id", sa.String(160)),
    sa.Column("payload_hash", sa.String(64), nullable=False),
    sa.Column("conversation_id", sa.Uuid, nullable=False),
    sa.ForeignKeyConstraint(["conversation_id", "workspace_id"], ["conversations.id", "conversations.workspace_id"]),
    sa.UniqueConstraint("workspace_id", "source_ref", "source_conversation_id"))

request_receipts = sa.Table("request_receipts", metadata, *common(),
    sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
    sa.Column("request_key", sa.String(160), nullable=False),
    sa.Column("operation", sa.String(240), nullable=False), sa.Column("payload_hash", sa.String(64), nullable=False),
    sa.Column("result", JSONB, nullable=False), sa.UniqueConstraint("workspace_id", "request_key"))
