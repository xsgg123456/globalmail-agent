"""Initial runtime and controlled content registry."""
from alembic import op
"""Phase 2 metadata; scope columns are non-null to make composite FKs effective."""
import sqlalchemy as sa

metadata = sa.MetaData()
SCOPE_KEYS = ("workspace_id", "mode", "branch_id", "customer_id", "purpose")


def common():
    return [sa.Column("id", sa.Uuid, primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]


def scope_columns():
    return [sa.Column("workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column("mode", sa.String(24), nullable=False),
            sa.Column("branch_id", sa.Uuid, nullable=False),
            sa.Column("customer_id", sa.Uuid, nullable=False),
            sa.Column("purpose", sa.String(80), nullable=False)]


workspaces = sa.Table("workspaces", metadata, *common(),
                      sa.Column("name", sa.String(120), nullable=False))
objects = sa.Table(
    "objects", metadata, *common(), *scope_columns(),
    sa.Column("sha256", sa.String(64), nullable=False),
    sa.Column("size_bytes", sa.BigInteger, nullable=False),
    sa.Column("source_kind", sa.String(80), nullable=False),
    sa.Column("source_ref", sa.String(240), nullable=False),
    sa.CheckConstraint("mode IN ('historical_replay', 'simulation')", name="objects_mode"),
    sa.CheckConstraint("size_bytes >= 0", name="objects_size"),
    sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="objects_digest"),
    sa.CheckConstraint("length(trim(purpose)) > 0 AND length(trim(source_kind)) > 0 "
                       "AND length(trim(source_ref)) > 0", name="objects_source"),
    sa.UniqueConstraint("id", *SCOPE_KEYS, name="objects_id_scope"),
)
content_dependencies = sa.Table(
    "content_dependencies", metadata, *common(), *scope_columns(),
    sa.Column("source_object_id", sa.Uuid, nullable=False),
    sa.Column("dependent_object_id", sa.Uuid, nullable=False),
    sa.ForeignKeyConstraint(["source_object_id", *SCOPE_KEYS],
                            ["objects.id", *[f"objects.{key}" for key in SCOPE_KEYS]],
                            name="dependencies_source_scope"),
    sa.ForeignKeyConstraint(["dependent_object_id", *SCOPE_KEYS],
                            ["objects.id", *[f"objects.{key}" for key in SCOPE_KEYS]],
                            name="dependencies_target_scope"),
    sa.UniqueConstraint("source_object_id", "dependent_object_id", name="dependencies_edge"),
    sa.CheckConstraint("source_object_id <> dependent_object_id", name="dependencies_not_self"),
)
deletion_journal = sa.Table(
    "deletion_journal", metadata, *common(), *scope_columns(),
    sa.Column("target_object_id", sa.Uuid, nullable=False),
    sa.Column("generation", sa.BigInteger, nullable=False),
    sa.Column("state", sa.String(24), nullable=False),
    sa.CheckConstraint("generation > 0", name="journal_generation"),
    sa.CheckConstraint("mode IN ('historical_replay', 'simulation')", name="journal_mode"),
    sa.CheckConstraint("length(trim(purpose)) > 0", name="journal_purpose"),
    sa.CheckConstraint("state IN ('revoked', 'cleaning', 'failed', 'verified')", name="journal_state"),
    sa.UniqueConstraint(*SCOPE_KEYS, "target_object_id", "generation", name="journal_target_generation"),
)


revision = "0001_runtime_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    metadata.create_all(op.get_bind(), checkfirst=True)


def downgrade():
    metadata.drop_all(op.get_bind(), checkfirst=True)


