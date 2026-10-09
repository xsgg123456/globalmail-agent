"""Phase 7 records share existing conversation/run scope; no second business ledger."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
metadata = sa.MetaData()
SCOPE_KEYS = ("workspace_id", "mode", "branch_id", "customer_id", "purpose")
def common():
    return [sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())]
def scoped(name, *columns):
    return sa.Table(name, metadata, *common(),
        sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("mode", sa.String(24), nullable=False), sa.Column("branch_id", sa.Uuid, nullable=False),
        sa.Column("customer_id", sa.Uuid, nullable=False), sa.Column("purpose", sa.String(80), nullable=False),
        *columns, sa.UniqueConstraint("id", *SCOPE_KEYS))
def child(name, *columns):
    return scoped(name, sa.Column("conversation_id", sa.Uuid, nullable=False), *columns,
        sa.ForeignKeyConstraint(["conversation_id", *SCOPE_KEYS], ["conversations.id", *[f"conversations.{k}" for k in SCOPE_KEYS]]))
def object_fk(column):
    return sa.ForeignKeyConstraint([column, *SCOPE_KEYS], ["objects.id", *[f"objects.{k}" for k in SCOPE_KEYS]])


def fk(table, column):
    return sa.ForeignKeyConstraint([column, *SCOPE_KEYS],
        [f"{table}.id", *[f"{table}.{key}" for key in SCOPE_KEYS]])


def run_child(name, *columns):
    return child(name, sa.Column("run_id", sa.Uuid, nullable=False),
        *columns, fk("agent_runs", "run_id"))


cycle_budgets = child("cycle_budgets", sa.Column("cycle_id", sa.Uuid, nullable=False),
    *[sa.Column(k, sa.BigInteger, nullable=False, server_default="0") for k in
      ("model_requests", "tool_calls", "reserved_tokens", "input_tokens", "output_tokens", "unknown_requests", "active_ms")],
    fk("processing_cycles", "cycle_id"), sa.UniqueConstraint("cycle_id"),
    sa.CheckConstraint("model_requests BETWEEN 0 AND 6 AND tool_calls BETWEEN 0 AND 12"),
    sa.CheckConstraint("reserved_tokens >= 0 AND input_tokens >= 0 AND output_tokens >= 0 AND active_ms >= 0"))
agent_run_contexts = run_child("agent_run_contexts",
    sa.Column("release_id", sa.Uuid), sa.Column("release_epoch", sa.BigInteger, nullable=False),
    sa.Column("profile_id", sa.Uuid), sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
    sa.Column("visible_message_seq", sa.BigInteger, nullable=False),
    sa.Column("observed_wakes", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
    sa.Column("validated_draft_hash", sa.String(64)),
    sa.Column("context_object_id", sa.Uuid, nullable=False), object_fk("context_object_id"),
    sa.Column("rebuild_count", sa.Integer, nullable=False, server_default="0"),
    sa.Column("prompt_version", sa.String(80), nullable=False), sa.Column("graph_version", sa.String(80), nullable=False),
    sa.UniqueConstraint("run_id"), sa.CheckConstraint("rebuild_count BETWEEN 0 AND 1"))
understanding_results = run_child("understanding_results",
    sa.Column("body_object_id", sa.Uuid, nullable=False), object_fk("body_object_id"),
    sa.UniqueConstraint("run_id"))
tool_commands = run_child("tool_commands", sa.Column("command_key", sa.String(160), nullable=False),
    sa.Column("name", sa.String(80), nullable=False), sa.Column("payload_hash", sa.String(64), nullable=False),
    sa.Column("arguments", JSONB, nullable=False), sa.Column("status", sa.String(24), nullable=False),
    sa.Column("result_object_id", sa.Uuid), object_fk("result_object_id"),
    sa.UniqueConstraint("run_id", "command_key"))
understanding_revisions = run_child("understanding_revisions",
    sa.Column("revision", sa.BigInteger, nullable=False),
    sa.Column("case_revision", sa.BigInteger, nullable=False),
    sa.Column("command_id", sa.Uuid, nullable=False), fk("tool_commands", "command_id"),
    sa.Column("body_object_id", sa.Uuid, nullable=False), object_fk("body_object_id"),
    sa.Column("source_ids", JSONB, nullable=False), sa.Column("change_reason", sa.String(1000), nullable=False),
    sa.UniqueConstraint("run_id", "revision"), sa.UniqueConstraint("command_id"),
    sa.CheckConstraint("revision > 0 AND case_revision >= 0"))
tool_calls = run_child("tool_calls", sa.Column("command_id", sa.Uuid, nullable=False),
    sa.Column("provider_call_id", sa.String(160), nullable=False),
    sa.Column("position", sa.Integer, nullable=False), fk("tool_commands", "command_id"),
    sa.UniqueConstraint("run_id", "position"))
reply_artifacts = run_child("reply_artifacts", sa.Column("cycle_id", sa.Uuid, nullable=False),
    sa.Column("outcome", sa.String(32), nullable=False), sa.Column("language", sa.String(32), nullable=False),
    sa.Column("body_object_id", sa.Uuid), object_fk("body_object_id"),
    sa.Column("citation_ids", JSONB, nullable=False), sa.Column("claims", JSONB, nullable=False),
    fk("processing_cycles", "cycle_id"), sa.UniqueConstraint("cycle_id"),
    sa.CheckConstraint("outcome IN ('reply_and_wait','historical_comparison','handoff','wait_business','no_material_update')"))
usage_records = run_child("usage_records", sa.Column("request_key", sa.String(160), nullable=False),
    sa.Column("stage", sa.String(40), nullable=False), sa.Column("status", sa.String(24), nullable=False),
    sa.Column("estimated_input", sa.Integer, nullable=False), sa.Column("reserved_tokens", sa.Integer, nullable=False),
    sa.Column("input_tokens", sa.Integer), sa.Column("output_tokens", sa.Integer),
    sa.Column("provider_request_id", sa.String(160)), sa.Column("model", sa.String(160), nullable=False),
    sa.UniqueConstraint("run_id", "request_key"),
    sa.CheckConstraint("estimated_input >= 0 AND reserved_tokens >= 0 AND (input_tokens IS NULL OR input_tokens >= 0) AND (output_tokens IS NULL OR output_tokens >= 0)"))
agent_run_dependencies = run_child("agent_run_dependencies",
    sa.Column("reference_id", sa.Uuid, nullable=False), sa.Column("sku", sa.String(160), nullable=False),
    sa.Column("document_id", sa.Uuid, nullable=False), sa.Column("source_object_id", sa.Uuid, nullable=False),
    sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("revocation_epoch", sa.BigInteger, nullable=False),
    sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
    # Knowledge lives in its shared rag scope. Explicit workspace-aware FKs prevent forged dependencies.
    sa.ForeignKeyConstraint(["reference_id", "workspace_id"], ["evidence_refs.id", "evidence_refs.workspace_id"]),
    sa.UniqueConstraint("run_id", "reference_id"))
wait_conditions = run_child("wait_conditions", sa.Column("issue_id", sa.Uuid, nullable=False),
    sa.Column("operation_id", sa.String(160)), sa.Column("condition_type", sa.String(40), nullable=False),
    sa.Column("last_seen_business_version", sa.BigInteger, nullable=False),
    sa.Column("status", sa.String(24), nullable=False), fk("case_issues", "issue_id"),
    sa.Column("condition_key", sa.String(200), nullable=False), sa.UniqueConstraint("run_id", "condition_key"))
wake_pending = child("wake_pending", sa.Column("condition_key", sa.String(200), nullable=False),
    sa.Column("business_version", sa.BigInteger, nullable=False), sa.Column("status", sa.String(24), nullable=False),
    sa.Column("observed_run_id", sa.Uuid), sa.UniqueConstraint("conversation_id", "condition_key"))
trace_correlations = run_child("trace_correlations", sa.Column("trace_id", sa.String(64), nullable=False),
    sa.Column("export_status", sa.String(24), nullable=False), sa.UniqueConstraint("run_id"))
agent_risks = run_child("agent_risks", sa.Column("kind", sa.String(40), nullable=False),
    sa.Column("status", sa.String(40), nullable=False), sa.Column("body_object_id", sa.Uuid, nullable=False),
    object_fk("body_object_id"), sa.Column("resolution_review_id", sa.Uuid), fk("human_reviews", "resolution_review_id"),
    sa.Column("resolution_object_id", sa.Uuid), object_fk("resolution_object_id"),
    sa.UniqueConstraint("run_id", "kind"),
    sa.CheckConstraint("status IN ('active','resolved_by_human','corrected_by_human')"))

AGENT_TABLES = [cycle_budgets, agent_run_contexts, understanding_results, understanding_revisions, tool_commands, tool_calls,
    reply_artifacts, usage_records, agent_run_dependencies, wait_conditions, wake_pending, trace_correlations, agent_risks]

from alembic import op
revision = "0006_agent_results"
down_revision = "0005_knowledge_index"
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    if "evidence_refs_workspace" not in {c["name"] for c in sa.inspect(conn).get_unique_constraints("evidence_refs")}:
        op.create_unique_constraint("evidence_refs_workspace", "evidence_refs", ["id", "workspace_id"])
    metadata.reflect(conn, only=["workspaces", "objects", "conversations", "agent_runs", "processing_cycles", "case_issues", "evidence_refs", "human_reviews"], extend_existing=True)
    target = conn.execute(sa.text("SELECT current_schema()")).scalar_one()
    existing = set(sa.inspect(conn).get_table_names(schema=target))
    for table in sa.sql.ddl.sort_tables(AGENT_TABLES):
        if table.name not in existing:
            table.create(conn, checkfirst=False)
    from globalmail_agent.adapters.checkpoint_repository import setup_checkpoint
    setup_checkpoint(conn)

def downgrade():
    raise RuntimeError("Agent record downgrade requires an explicit preservation plan")
