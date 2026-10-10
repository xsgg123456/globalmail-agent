"""Add human-assist permissions and call records; retain existing ledgers and objects."""
import sqlalchemy as sa
from alembic import op

revision = "0010_human_assistance"
down_revision = "0009_business_waits"
branch_labels = depends_on = None
SCOPE = ["workspace_id", "mode", "branch_id", "customer_id", "purpose"]


def upgrade():
    conn = op.get_bind()
    target = conn.execute(sa.text("SELECT current_schema()")).scalar_one()
    first_application = "persistent_human" not in {
        c["name"] for c in sa.inspect(conn).get_columns("conversations", schema=target)}
    additions = {
        "conversations": [sa.Column("persistent_human", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("human_claimed", sa.Boolean, nullable=False, server_default=sa.false())],
        "agent_runs": [sa.Column("execution_mode", sa.String(24), nullable=False, server_default="autonomous")],
        "reply_artifacts": [sa.Column("advice_object_id", sa.Uuid)],
        "usage_records": [sa.Column("request_object_id", sa.Uuid), sa.Column("response_object_id", sa.Uuid),
            sa.Column("request_state", sa.String(24), nullable=False, server_default="not_recorded"),
            sa.Column("error_code", sa.String(80)), sa.Column("finished_at", sa.DateTime(timezone=True))]}
    for table, columns in additions.items():
        existing = {c["name"] for c in sa.inspect(conn).get_columns(table, schema=target)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)
    for table, field in [("reply_artifacts", "advice_object_id"),
            ("usage_records", "request_object_id"), ("usage_records", "response_object_id")]:
        name = table + "_" + field + "_scope"
        if name not in {f["name"] for f in sa.inspect(conn).get_foreign_keys(table, schema=target)}:
            op.create_foreign_key(name, table, "objects", [field, *SCOPE], ["id", *SCOPE])
    for constraint in sa.inspect(conn).get_check_constraints("reply_artifacts", schema=target):
        if "outcome" in constraint["sqltext"] and "human_advice" not in constraint["sqltext"]:
            op.drop_constraint(constraint["name"], "reply_artifacts", type_="check")
    if not any("human_advice" in c["sqltext"] for c in sa.inspect(conn).get_check_constraints("reply_artifacts", schema=target)):
        op.create_check_constraint("reply_artifacts_outcome", "reply_artifacts",
            "outcome IN ('reply_and_wait','historical_comparison','handoff','human_advice','wait_business','no_material_update')")
    if not any("execution_mode" in c["sqltext"] for c in sa.inspect(conn).get_check_constraints("agent_runs", schema=target)):
        op.create_check_constraint("agent_runs_execution_mode", "agent_runs",
            "execution_mode IN ('autonomous','human_assist')")
    if not first_application:
        return
    # Existing source-backed commercial issues stay human-owned after the upgrade.
    conn.execute(sa.text("UPDATE conversations c SET persistent_human=true, "
        "human_claimed=(processing_owner <> 'agent'), processing_owner=CASE "
        "WHEN processing_owner='human_wait_customer' THEN 'human_wait_customer' ELSE 'human_review' END, auto_run_gate='disabled' "
        "WHERE lifecycle='open' AND (EXISTS (SELECT 1 FROM case_issues i WHERE i.conversation_id=c.id "
        "AND i.business_type IN ('refund','return','replacement','parts','spare_part')) "
        "OR EXISTS (SELECT 1 FROM operations o WHERE o.workspace_id=c.workspace_id AND o.branch_id=c.branch_id "
        "AND o.customer_id=c.customer_id AND o.mode=c.mode AND o.purpose=c.purpose AND o.kind IN "
        "('refund','return','replacement','parts','spare_part')))"))
    # Never resume a checkpoint with the superseded commercial tool menu.
    conn.execute(sa.text("UPDATE message_attachments m SET status='failed', processing_run_id=NULL, "
        "failure_reason='analysis_interrupted' FROM agent_runs r WHERE m.processing_run_id=r.id "
        "AND m.status='processing' AND r.status IN ('queued','running')"))
    conn.execute(sa.text("UPDATE conversations c SET scheduling_state='failed', auto_run_gate=CASE "
        "WHEN persistent_human THEN 'disabled' ELSE 'manual_retry_required' END, "
        "row_version=row_version+1 WHERE c.lifecycle='open' AND EXISTS (SELECT 1 FROM agent_runs r "
        "WHERE r.conversation_id=c.id AND r.status IN ('queued','running'))"))
    conn.execute(sa.text("UPDATE agent_runs SET status='interrupted', checkpoint_writable=false, "
        "error_code='runtime_policy_changed', finished_at=now() WHERE status IN ('queued','running')"))
    conn.execute(sa.text("UPDATE jobs SET status='interrupted', lease_expires_at=NULL, "
        "error_code='runtime_policy_changed' WHERE kind='agent' AND status IN ('queued','running')"))
    conn.execute(sa.text("UPDATE processing_cycles SET state='interrupted' WHERE state IN ('queued','running')"))
    conn.execute(sa.text("UPDATE agent_slots SET job_id=NULL, lease_owner=NULL, lease_expires_at=NULL, "
        "fence=fence+1 WHERE slot_key='agent'"))


def downgrade():
    raise RuntimeError("Human-assist downgrade requires a preservation plan")
