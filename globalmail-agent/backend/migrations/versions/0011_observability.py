"""Add scoped safe export buffers without changing business records or usage."""
import sqlalchemy as sa
from alembic import op

revision = "0011_observability"
down_revision = "0010_human_assistance"
branch_labels = depends_on = None
SCOPE = ["workspace_id", "mode", "branch_id", "customer_id", "purpose"]


def upgrade():
    conn = op.get_bind()
    target = conn.execute(sa.text("SELECT current_schema()")).scalar_one()
    existing = {c["name"] for c in sa.inspect(conn).get_columns("trace_correlations", schema=target)}
    for column in [sa.Column("reason_code", sa.String(80)), sa.Column("export_object_id", sa.Uuid),
            sa.Column("generation", sa.BigInteger, nullable=False, server_default="1"),
            sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
            sa.Column("pending_count", sa.Integer, nullable=False, server_default="0")]:
        if column.name not in existing:
            op.add_column("trace_correlations", column)
    if "trace_export_object_scope" not in {
            f["name"] for f in sa.inspect(conn).get_foreign_keys("trace_correlations", schema=target)}:
        op.create_foreign_key("trace_export_object_scope", "trace_correlations", "objects",
            ["export_object_id", *SCOPE], ["id", *SCOPE])


def downgrade():
    raise RuntimeError("Observability downgrade requires an export preservation plan")
