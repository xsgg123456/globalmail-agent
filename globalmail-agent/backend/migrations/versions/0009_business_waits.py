"""Frozen additive business wait correlation; old facts and outcomes remain intact."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision = "0009_business_waits"
down_revision = "0008_after_sales_ledger"
branch_labels = depends_on = None
SCOPE = ["workspace_id", "mode", "branch_id", "customer_id", "purpose"]


def upgrade():
    conn = op.get_bind()
    additions = {
        "inventory": [sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))],
        "case_issues": [sa.Column("order_line_id", sa.Uuid), sa.Column("order_number", sa.String(160)),
            sa.Column("business_type", sa.String(40)), sa.Column("source_message_id", sa.Uuid),
            sa.Column("plan_status", sa.String(40)), sa.Column("current_operation_id", sa.String(160))],
        "wait_conditions": [sa.Column("owner", sa.String(24), nullable=False, server_default="agent")],
        "wake_pending": [sa.Column("issue_id", sa.Uuid), sa.Column("operation_id", sa.String(160))],
        "agent_run_contexts": [sa.Column("observed_event_ids", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))],
        "domain_events": [sa.Column("issue_id", sa.Uuid), sa.Column("operation_id", sa.String(160)),
            sa.Column("condition_type", sa.String(40)), sa.Column("business_version", sa.BigInteger),
            sa.Column("observed_run_id", sa.Uuid)]}
    for table, columns in additions.items():
        current = {c["name"] for c in sa.inspect(conn).get_columns(table)}
        for column in columns:
            if column.name not in current:
                op.add_column(table, column)
    for table, field, target in [("case_issues", "order_line_id", "branch_order_lines"),
            ("case_issues", "source_message_id", "messages"), ("wake_pending", "issue_id", "case_issues"),
            ("domain_events", "issue_id", "case_issues"), ("domain_events", "observed_run_id", "agent_runs"),
            ("wake_pending", "observed_run_id", "agent_runs")]:
        name = table + "_" + field + "_scope"
        if name not in {f["name"] for f in sa.inspect(conn).get_foreign_keys(table)}:
            op.create_foreign_key(name, table, target, [field, *SCOPE], ["id", *SCOPE])
    for table, name, columns in [
            ("case_issues", "issue_order_line", ["conversation_id", "order_line_id", "business_type"]),
            ("domain_events", "business_event_consumption", ["conversation_id", "status", "operation_id", "business_version"]),
            ("wait_conditions", "active_business_wait", ["conversation_id", "operation_id", "status"]),
            ("wake_pending", "issue_pending_wake", ["conversation_id", "issue_id", "status"])]:
        if name not in {i["name"] for i in sa.inspect(conn).get_indexes(table)}:
            op.create_index(name, table, columns)


def downgrade():
    raise RuntimeError("Business waits downgrade requires a preservation plan")
