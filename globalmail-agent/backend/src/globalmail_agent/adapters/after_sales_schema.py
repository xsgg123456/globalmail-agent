"""Scoped reservations and command receipts extend the existing business ledger."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from globalmail_agent.adapters.schema import metadata, common, scope_columns, SCOPE_KEYS
from globalmail_agent.adapters.business_schema import fk, operations, executions, policy_decisions
from globalmail_agent.adapters.knowledge_index_schema import knowledge_releases

knowledge_releases.append_constraint(sa.UniqueConstraint("id", "workspace_id", name="release_workspace_identity"))
operations.append_constraint(sa.UniqueConstraint("id", "order_line_id", *SCOPE_KEYS, name="operation_line_identity"))
executions.append_constraint(sa.UniqueConstraint("id", "operation_id", *SCOPE_KEYS, name="execution_operation_identity"))


def child(name, *columns):
    return sa.Table(name, metadata, *common(), *scope_columns(), *columns,
        sa.UniqueConstraint("id", *SCOPE_KEYS),
        sa.ForeignKeyConstraint(list(SCOPE_KEYS), [f"simulation_branches.{k}" for k in SCOPE_KEYS]))


compensation_reservations = child("compensation_reservations",
    sa.Column("operation_id", sa.Uuid, nullable=False), sa.Column("order_line_id", sa.Uuid, nullable=False),
    sa.Column("unit_id", sa.String(160), nullable=False), sa.Column("amount_minor", sa.BigInteger),
    sa.Column("currency", sa.String(3)), sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.ForeignKeyConstraint(["operation_id", "order_line_id", *SCOPE_KEYS],
        ["operations.id", "operations.order_line_id", *[f"operations.{k}" for k in SCOPE_KEYS]]),
    fk("branch_order_lines", "order_line_id"),
    sa.UniqueConstraint("operation_id", "unit_id"),
    sa.CheckConstraint("amount_minor IS NULL OR amount_minor >= 0"))
sa.Index("compensation_unit_active", *[compensation_reservations.c[k] for k in SCOPE_KEYS],
    compensation_reservations.c.order_line_id, compensation_reservations.c.unit_id, unique=True,
    postgresql_where=compensation_reservations.c.active.is_(True))

inventory_reservations = child("inventory_reservations",
    sa.Column("operation_id", sa.Uuid, nullable=False), sa.Column("execution_id", sa.Uuid, nullable=False),
    sa.Column("inventory_id", sa.Uuid, nullable=False), sa.Column("quantity", sa.Integer, nullable=False),
    sa.Column("state", sa.String(24), nullable=False),
    fk("operations", "operation_id"),
    sa.ForeignKeyConstraint(["execution_id", "operation_id", *SCOPE_KEYS],
        ["executions.id", "executions.operation_id", *[f"executions.{k}" for k in SCOPE_KEYS]]), fk("inventory", "inventory_id"),
    sa.UniqueConstraint("execution_id"), sa.CheckConstraint("quantity > 0"),
    sa.CheckConstraint("state IN ('reserved','consumed','released')"))

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

sa.Index("executions_one_uncertain_managed", executions.c.operation_id, unique=True,
    postgresql_where=sa.and_(executions.c.managed.is_(True), executions.c.confirmed_not_executed.is_(False),
        executions.c.status.in_(["accepted", "processing", "unknown", "failed"])))
operations.append_constraint(sa.ForeignKeyConstraint(["decision_id", *SCOPE_KEYS],
    ["policy_decisions.id", *[f"policy_decisions.{k}" for k in SCOPE_KEYS]], name="operations_decision_scope"))
operations.append_constraint(sa.ForeignKeyConstraint(["policy_release_id", "workspace_id"],
    ["knowledge_releases.id", "knowledge_releases.workspace_id"], name="operations_release_workspace"))
policy_decisions.append_constraint(fk("agent_runs", "run_id"))
policy_decisions.append_constraint(sa.ForeignKeyConstraint(["release_id", "workspace_id"],
    ["knowledge_releases.id", "knowledge_releases.workspace_id"], name="policy_decisions_release_workspace"))
AFTER_SALES_TABLES = [compensation_reservations, inventory_reservations, operation_commands, simulation_events]
