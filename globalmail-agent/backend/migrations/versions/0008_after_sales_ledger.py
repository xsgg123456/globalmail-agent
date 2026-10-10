"""Frozen Phase 9 additive DDL; existing source snapshots remain intact."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision = "0008_after_sales_ledger"
down_revision = "0007_visual_evidence"
branch_labels = depends_on = None
SCOPE_KEYS = ("workspace_id", "mode", "branch_id", "customer_id", "purpose")
metadata = sa.MetaData()


def fk(table, column):
    return sa.ForeignKeyConstraint([column, *SCOPE_KEYS], [f"{table}.id", *[f"{table}.{k}" for k in SCOPE_KEYS]])


def child(name, *columns):
    return sa.Table(name, metadata, sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("mode", sa.String(24), nullable=False), sa.Column("branch_id", sa.Uuid, nullable=False),
        sa.Column("customer_id", sa.Uuid, nullable=False), sa.Column("purpose", sa.String(80), nullable=False),
        *columns, sa.UniqueConstraint("id", *SCOPE_KEYS),
        sa.ForeignKeyConstraint(list(SCOPE_KEYS), [f"simulation_branches.{k}" for k in SCOPE_KEYS]))


compensation_reservations = child("compensation_reservations",
    sa.Column("operation_id", sa.Uuid, nullable=False), sa.Column("order_line_id", sa.Uuid, nullable=False),
    sa.Column("unit_id", sa.String(160), nullable=False), sa.Column("amount_minor", sa.BigInteger),
    sa.Column("currency", sa.String(3)), sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.ForeignKeyConstraint(["operation_id", "order_line_id", *SCOPE_KEYS],
        ["operations.id", "operations.order_line_id", *[f"operations.{k}" for k in SCOPE_KEYS]]),
    fk("branch_order_lines", "order_line_id"),
    sa.UniqueConstraint("operation_id", "unit_id"), sa.CheckConstraint("amount_minor IS NULL OR amount_minor >= 0"))
sa.Index("compensation_unit_active", *[compensation_reservations.c[k] for k in SCOPE_KEYS],
    compensation_reservations.c.order_line_id, compensation_reservations.c.unit_id, unique=True,
    postgresql_where=compensation_reservations.c.active.is_(True))
inventory_reservations = child("inventory_reservations",
    sa.Column("operation_id", sa.Uuid, nullable=False), sa.Column("execution_id", sa.Uuid, nullable=False),
    sa.Column("inventory_id", sa.Uuid, nullable=False), sa.Column("quantity", sa.Integer, nullable=False),
    sa.Column("state", sa.String(24), nullable=False), fk("operations", "operation_id"),
    sa.ForeignKeyConstraint(["execution_id", "operation_id", *SCOPE_KEYS],
        ["executions.id", "executions.operation_id", *[f"executions.{k}" for k in SCOPE_KEYS]]),
    fk("inventory", "inventory_id"), sa.UniqueConstraint("execution_id"),
    sa.CheckConstraint("quantity > 0"), sa.CheckConstraint("state IN ('reserved','consumed','released')"))
operation_commands = child("operation_commands",
    sa.Column("command_id", sa.Uuid, nullable=False), sa.Column("operation_id", sa.Uuid, nullable=False),
    sa.Column("action", sa.String(24), nullable=False), sa.Column("payload_hash", sa.String(64), nullable=False),
    sa.Column("result", JSONB, nullable=False), fk("operations", "operation_id"), fk("tool_commands", "command_id"),
    sa.UniqueConstraint("command_id"))
simulation_events = child("simulation_events",
    sa.Column("conversation_id", sa.Uuid, nullable=False), sa.Column("operation_id", sa.Uuid, nullable=False),
    sa.Column("execution_id", sa.Uuid), sa.Column("event", sa.String(40), nullable=False),
    sa.Column("sequence", sa.BigInteger, nullable=False), sa.Column("payload", JSONB, nullable=False),
    sa.Column("source_kind", sa.String(40), nullable=False, server_default="scenario_console_manual"),
    fk("conversations", "conversation_id"), fk("operations", "operation_id"),
    sa.ForeignKeyConstraint(["execution_id", "operation_id", *SCOPE_KEYS],
        ["executions.id", "executions.operation_id", *[f"executions.{k}" for k in SCOPE_KEYS]]),
    sa.UniqueConstraint("operation_id", "sequence"), sa.CheckConstraint("sequence > 0"))


def upgrade():
    conn = op.get_bind()
    additions = {
        "operations": [sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
            sa.Column("plan_digest", sa.String(64)), sa.Column("decision_id", sa.Uuid),
            sa.Column("policy_release_id", sa.Uuid),
            sa.Column("confirmed_not_executed", sa.Boolean, nullable=False, server_default=sa.false())],
        "executions": [sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
            sa.Column("attempt_no", sa.Integer, nullable=False, server_default="0"),
            sa.Column("managed", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("confirmed_not_executed", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("receipt_ref", sa.String(240))],
        "shipments": [sa.Column("version", sa.BigInteger, nullable=False, server_default="1")],
        "return_receipts": [sa.Column("version", sa.BigInteger, nullable=False, server_default="1")],
        "policy_decisions": [sa.Column("decision_data", JSONB), sa.Column("plan_digest", sa.String(64)),
            sa.Column("release_id", sa.Uuid), sa.Column("run_id", sa.Uuid)]}
    for table, columns in additions.items():
        if table in {"operations", "executions", "shipments", "return_receipts"}:
            columns.append(sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")))
        current = {c["name"] for c in sa.inspect(conn).get_columns(table)}
        for column in columns:
            if column.name not in current:
                op.add_column(table, column)
    unique = {c["name"] for c in sa.inspect(conn).get_unique_constraints("knowledge_releases")}
    if "release_workspace_identity" not in unique:
        op.create_unique_constraint("release_workspace_identity", "knowledge_releases", ["id", "workspace_id"])
    for table, name, columns in [("operations", "operation_line_identity", ["id", "order_line_id", *SCOPE_KEYS]),
            ("executions", "execution_operation_identity", ["id", "operation_id", *SCOPE_KEYS])]:
        if name not in {c["name"] for c in sa.inspect(conn).get_unique_constraints(table)}:
            op.create_unique_constraint(name, table, columns)
    for table, name, columns, target, remote in [
        ("operations", "operations_decision_scope", ["decision_id", *SCOPE_KEYS], "policy_decisions", ["id", *SCOPE_KEYS]),
        ("operations", "operations_release_workspace", ["policy_release_id", "workspace_id"], "knowledge_releases", ["id", "workspace_id"]),
        ("policy_decisions", "policy_decisions_release_workspace", ["release_id", "workspace_id"], "knowledge_releases", ["id", "workspace_id"]),
        ("policy_decisions", "policy_decisions_run_scope", ["run_id", *SCOPE_KEYS], "agent_runs", ["id", *SCOPE_KEYS])]:
        existing = {f["name"] for f in sa.inspect(conn).get_foreign_keys(table)}
        if name not in existing:
            op.create_foreign_key(name, table, target, columns, remote)
    for table, name, check in [
        ("operations", "operations_version_positive", "version > 0"),
        ("executions", "executions_version_attempt_positive", "version > 0 AND attempt_no >= 0")]:
        if name not in {c["name"] for c in sa.inspect(conn).get_check_constraints(table)}:
            op.create_check_constraint(name, table, check)
    metadata.reflect(conn, only=["workspaces", "simulation_branches", "operations", "executions", "inventory",
        "branch_order_lines", "tool_commands", "conversations"], extend_existing=True)
    target = conn.execute(sa.text("SELECT current_schema()")).scalar_one()
    existing = set(sa.inspect(conn).get_table_names(schema=target))
    for table in sa.sql.ddl.sort_tables([compensation_reservations, inventory_reservations, operation_commands, simulation_events]):
        if table.name not in existing:
            table.create(conn, checkfirst=False)
    if "executions_one_uncertain_managed" not in {i["name"] for i in sa.inspect(conn).get_indexes("executions")}:
        op.create_index("executions_one_uncertain_managed", "executions", ["operation_id"], unique=True,
            postgresql_where=sa.text("managed AND NOT confirmed_not_executed AND status IN ('accepted','processing','unknown','failed')"))


def downgrade():
    raise RuntimeError("After-sales ledger downgrade requires an explicit preservation plan")
