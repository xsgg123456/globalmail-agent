"""One scoped business ledger; immutable source bytes remain separate from live state."""
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


def source():
    return [sa.Column("source_kind", sa.String(80), nullable=False),
            sa.Column("source_ref", sa.String(240), nullable=False),
            sa.Column("source_hash", sa.String(64), nullable=False),
            sa.Column("source_snapshot", JSONB, nullable=False)]


def fk(table, *columns):
    return sa.ForeignKeyConstraint([*columns, *SCOPE_KEYS],
        [f"{table}.id", *[f"{table}.{k}" for k in SCOPE_KEYS]])


def scoped(name, *columns):
    return sa.Table(name, metadata, *common(), *scope_columns(), *source(), *columns,
                    sa.UniqueConstraint("id", *SCOPE_KEYS))


products = sa.Table("products", metadata, *common(), *source(),
    sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
    sa.Column("item_id", sa.String(160), nullable=False), sa.Column("sku", sa.String(160), nullable=False),
    sa.Column("brand", sa.String(40), nullable=False), sa.Column("kind", sa.String(24), nullable=False),
    sa.Column("version", sa.String(40), nullable=False),
    sa.UniqueConstraint("workspace_id", "item_id", "version"),
    sa.UniqueConstraint("id", "workspace_id", "sku", "brand"),
    sa.CheckConstraint("kind IN ('product','part')"))

policy_profiles = sa.Table("policy_profiles", metadata, *common(), *source(),
    sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
    sa.Column("policy_id", sa.String(160), nullable=False), sa.Column("version", sa.String(40), nullable=False),
    sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("publication_status", sa.String(24), nullable=False, server_default="unpublished"),
    sa.Column("description", sa.Text, nullable=False),
    sa.UniqueConstraint("workspace_id", "policy_id", "version"),
    sa.UniqueConstraint("id", "workspace_id"))

simulation_branches = scoped("simulation_branches",
    sa.Column("conversation_id", sa.Uuid, nullable=False), sa.Column("dataset_id", sa.Uuid, nullable=False),
    sa.Column("scenario_id", sa.String(160), nullable=False),
    sa.Column("clock", sa.DateTime(timezone=True), nullable=False),
    sa.Column("generation", sa.BigInteger, nullable=False, server_default="1"),
    sa.Column("policy_profile_id", sa.Uuid), sa.Column("state", JSONB, nullable=False),
    sa.Column("tool_overrides", JSONB, nullable=False), fk("conversations", "conversation_id"),
    sa.ForeignKeyConstraint(["policy_profile_id", "workspace_id"], ["policy_profiles.id", "policy_profiles.workspace_id"]),
    sa.UniqueConstraint(*SCOPE_KEYS), sa.UniqueConstraint("conversation_id"),
    sa.CheckConstraint("id = branch_id"), sa.CheckConstraint("generation > 0"))

branch_orders = scoped("branch_orders",
    sa.Column("conversation_id", sa.Uuid, nullable=False), sa.Column("external_id", sa.String(160), nullable=False),
    sa.Column("display_order_number", sa.String(160), nullable=False),
    sa.Column("brand", sa.String(40), nullable=False), sa.Column("currency", sa.String(3)),
    sa.Column("paid_minor", sa.BigInteger), sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
    fk("conversations", "conversation_id"),
    sa.ForeignKeyConstraint(list(SCOPE_KEYS), [f"simulation_branches.{k}" for k in SCOPE_KEYS]),
    sa.UniqueConstraint("id", *SCOPE_KEYS, "brand"),
    sa.UniqueConstraint(*SCOPE_KEYS, "external_id"), sa.UniqueConstraint(*SCOPE_KEYS, "display_order_number"),
    sa.CheckConstraint("paid_minor IS NULL OR paid_minor >= 0"))

branch_order_lines = scoped("branch_order_lines",
    sa.Column("order_id", sa.Uuid, nullable=False), sa.Column("external_id", sa.String(160), nullable=False),
    sa.Column("product_id", sa.Uuid, nullable=False), sa.Column("sku", sa.String(160), nullable=False),
    sa.Column("brand", sa.String(40), nullable=False), sa.Column("hardware_revision", sa.String(80)),
    sa.Column("quantity", sa.Integer, nullable=False), sa.Column("paid_minor", sa.BigInteger),
    sa.ForeignKeyConstraint(["order_id", *SCOPE_KEYS, "brand"],
        ["branch_orders.id", *[f"branch_orders.{k}" for k in SCOPE_KEYS], "branch_orders.brand"]),
    sa.ForeignKeyConstraint(["product_id", "workspace_id", "sku", "brand"],
        ["products.id", "products.workspace_id", "products.sku", "products.brand"]),
    sa.UniqueConstraint("id", "order_id", *SCOPE_KEYS), sa.UniqueConstraint(*SCOPE_KEYS, "external_id"),
    sa.CheckConstraint("quantity > 0"), sa.CheckConstraint("paid_minor IS NULL OR paid_minor >= 0"))

compatibility = sa.Table("compatibility", metadata, *common(), *source(),
    sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
    sa.Column("sku", sa.String(160), nullable=False), sa.Column("item_id", sa.String(160), nullable=False),
    sa.Column("hardware_revision", sa.String(80), nullable=False), sa.Column("version", sa.String(40), nullable=False),
    sa.UniqueConstraint("workspace_id", "sku", "item_id", "hardware_revision", "version"))

inventory = scoped("inventory", sa.Column("item_id", sa.String(160), nullable=False),
    sa.Column("region_spec", sa.String(40)), sa.Column("hardware_revision", sa.String(80)),
    sa.Column("on_hand", sa.Integer, nullable=False), sa.Column("reserved", sa.Integer, nullable=False),
    sa.Column("snapshot_at", sa.DateTime(timezone=True)),
    sa.ForeignKeyConstraint(list(SCOPE_KEYS), [f"simulation_branches.{k}" for k in SCOPE_KEYS]),
    sa.UniqueConstraint(*SCOPE_KEYS, "item_id", "region_spec", "hardware_revision"),
    sa.CheckConstraint("on_hand >= 0 AND reserved >= 0 AND reserved <= on_hand"))


def ledger(name, *columns):
    return scoped(name, sa.Column("order_id", sa.Uuid, nullable=False),
        sa.Column("order_line_id", sa.Uuid, nullable=False),
        sa.Column("external_id", sa.String(160), nullable=False),
        sa.Column("status", sa.String(80)), sa.Column("snapshot_at", sa.DateTime(timezone=True)),
        fk("branch_orders", "order_id"),
        sa.ForeignKeyConstraint(["order_line_id", "order_id", *SCOPE_KEYS],
            ["branch_order_lines.id", "branch_order_lines.order_id", *[f"branch_order_lines.{k}" for k in SCOPE_KEYS]]),
        sa.UniqueConstraint("id", "order_id", "order_line_id", *SCOPE_KEYS),
        sa.UniqueConstraint(*SCOPE_KEYS, "external_id"), *columns)


operations = ledger("operations", sa.Column("kind", sa.String(40), nullable=False),
    sa.Column("quantity", sa.Integer, nullable=False), sa.Column("amount_minor", sa.BigInteger),
    sa.Column("currency", sa.String(3)), sa.Column("issue_id", sa.String(160)),
    sa.CheckConstraint("quantity > 0"), sa.CheckConstraint("amount_minor IS NULL OR amount_minor >= 0"))


def operation_fk():
    return sa.ForeignKeyConstraint(["operation_id", "order_id", "order_line_id", *SCOPE_KEYS],
        ["operations.id", "operations.order_id", "operations.order_line_id", *[f"operations.{k}" for k in SCOPE_KEYS]])


executions = ledger("executions", sa.Column("operation_id", sa.Uuid, nullable=False),
    sa.Column("amount_minor", sa.BigInteger), sa.Column("currency", sa.String(3)), operation_fk(),
    sa.UniqueConstraint("id", "operation_id", "order_id", "order_line_id", *SCOPE_KEYS),
    sa.CheckConstraint("amount_minor IS NULL OR amount_minor >= 0"))


def execution_fk():
    return sa.ForeignKeyConstraint(["execution_id", "operation_id", "order_id", "order_line_id", *SCOPE_KEYS],
        ["executions.id", "executions.operation_id", "executions.order_id", "executions.order_line_id",
         *[f"executions.{k}" for k in SCOPE_KEYS]])


shipments = ledger("shipments", sa.Column("operation_id", sa.Uuid), sa.Column("execution_id", sa.Uuid),
    sa.Column("parcel_purpose", sa.String(40), nullable=False), operation_fk(), execution_fk(),
    sa.CheckConstraint("execution_id IS NULL OR operation_id IS NOT NULL"))

return_receipts = ledger("return_receipts", sa.Column("operation_id", sa.Uuid), sa.Column("execution_id", sa.Uuid),
    sa.Column("quantity", sa.Integer, nullable=False), sa.Column("received", sa.Boolean),
    sa.Column("inspection", sa.String(80)), operation_fk(), execution_fk(),
    sa.CheckConstraint("quantity > 0"), sa.CheckConstraint("execution_id IS NULL OR operation_id IS NOT NULL"))

policy_decisions = scoped("policy_decisions", sa.Column("order_line_id", sa.Uuid, nullable=False),
    sa.Column("policy_profile_id", sa.Uuid, nullable=False), sa.Column("authorized", sa.Boolean, nullable=False),
    fk("branch_order_lines", "order_line_id"),
    sa.ForeignKeyConstraint(["policy_profile_id", "workspace_id"], ["policy_profiles.id", "policy_profiles.workspace_id"]))


revision = "0003_business_catalog"
down_revision = "0002_conversations_jobs"
branch_labels = None
depends_on = None
PHASE4_TABLE_NAMES = tuple(metadata.tables)


def upgrade():
    conn = op.get_bind()
    metadata.reflect(conn, only=["workspaces", "conversations"], extend_existing=True)
    metadata.create_all(conn, tables=[metadata.tables[n] for n in PHASE4_TABLE_NAMES], checkfirst=True)
    conn.execute(sa.text("""CREATE OR REPLACE FUNCTION immutable_business_source() RETURNS trigger AS $$
    BEGIN
        IF NEW.source_snapshot IS DISTINCT FROM OLD.source_snapshot
            OR NEW.source_hash IS DISTINCT FROM OLD.source_hash
            OR NEW.source_ref IS DISTINCT FROM OLD.source_ref
            OR NEW.source_kind IS DISTINCT FROM OLD.source_kind THEN
            RAISE EXCEPTION 'immutable_business_source';
        END IF;
        IF TG_TABLE_NAME IN ('branch_orders','branch_order_lines','products','compatibility')
            AND NEW IS DISTINCT FROM OLD THEN
            RAISE EXCEPTION 'immutable_business_snapshot';
        END IF;
        IF TG_TABLE_NAME = 'policy_profiles' THEN
            IF NEW.description IS DISTINCT FROM OLD.description OR NEW.version IS DISTINCT FROM OLD.version
                OR NEW.policy_id IS DISTINCT FROM OLD.policy_id OR NEW.available_at IS DISTINCT FROM OLD.available_at THEN
                RAISE EXCEPTION 'immutable_policy_version';
            END IF;
        END IF;
        RETURN NEW;
    END; $$ LANGUAGE plpgsql"""))
    for name in PHASE4_TABLE_NAMES:
        # Identifiers are frozen migration-owned constants, never request values.
        conn.execute(sa.text(f'DROP TRIGGER IF EXISTS immutable_source ON "{name}"'))
        conn.execute(sa.text(f'CREATE TRIGGER immutable_source BEFORE UPDATE ON "{name}" '
            'FOR EACH ROW EXECUTE FUNCTION immutable_business_source()'))


def downgrade():
    conn = op.get_bind()
    metadata.reflect(conn, only=["workspaces", "conversations"], extend_existing=True)
    for table in reversed(metadata.sorted_tables):
        if table.name in PHASE4_TABLE_NAMES:
            table.drop(conn, checkfirst=True)
    conn.execute(sa.text("DROP FUNCTION IF EXISTS immutable_business_source()"))
