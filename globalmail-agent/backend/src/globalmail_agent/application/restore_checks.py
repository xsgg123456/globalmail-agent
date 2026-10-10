"""Production restore gates; freeze inherited work and validate usable knowledge."""
import sqlalchemy as sa
from globalmail_agent.adapters.object_store import ObjectStore
from globalmail_agent.adapters.conversation_schema import jobs, agent_runs, agent_slots, conversations, processing_cycles
from globalmail_agent.adapters.knowledge_index_schema import (
    index_builds, knowledge_release_heads, knowledge_release_items,
)
from globalmail_agent.knowledge.build_checks import eligible
from globalmail_agent.adapters.lifecycle_schema import deletion_requests
from globalmail_agent.application.deletion import verify_local


def freeze_inherited_work(engine):
    with engine.begin() as connection:
        connection.execute(jobs.update().where(jobs.c.status.not_in(("completed", "failed", "cancelled"))).values(
            status="cancelled", stage="cancelled", lease_owner=None, lease_expires_at=None,
            row_version=jobs.c.row_version + 1, error_code="restored_requires_explicit_retry"))
        connection.execute(agent_runs.update().values(stop_requested=True, checkpoint_writable=False))
        connection.execute(agent_runs.update().where(agent_runs.c.status.in_(("queued", "running"))).values(
            status="stopped", error_code="restored_requires_explicit_retry", finished_at=sa.func.now()))
        connection.execute(processing_cycles.update().where(processing_cycles.c.state != "completed").values(state="stopped"))
        connection.execute(conversations.update().where(conversations.c.lifecycle == "open").values(
            auto_run_gate=sa.case((conversations.c.persistent_human, "disabled"), else_="manual_retry_required"),
            scheduling_state="stopped", authority_epoch=conversations.c.authority_epoch + 1,
            row_version=conversations.c.row_version + 1))
        connection.execute(agent_slots.update().values(fence=agent_slots.c.fence + 1,
            lease_owner=None, lease_expires_at=None, job_id=None))


def verify_restored_database(engine, object_root):
    store = ObjectStore(object_root, engine)
    with engine.connect() as connection:
        for request in connection.execute(sa.select(deletion_requests)).mappings().all():
            if request["status"] != "completed":
                raise ValueError("restore_deletion_incomplete")
            verify_local(connection, store, dict(request))
        if connection.execute(sa.select(sa.func.count()).select_from(jobs).where(
                jobs.c.status.not_in(("completed", "failed", "cancelled")))).scalar_one():
            raise ValueError("restore_unfenced_jobs")
        if connection.execute(sa.select(sa.func.count()).select_from(agent_runs).where(
                sa.or_(agent_runs.c.checkpoint_writable, ~agent_runs.c.stop_requested))).scalar_one():
            raise ValueError("restore_unfenced_runs")
        if connection.execute(sa.select(sa.func.count()).select_from(agent_slots).where(
                agent_slots.c.lease_owner.is_not(None))).scalar_one():
            raise ValueError("restore_unfenced_slots")
        builds = connection.execute(sa.select(index_builds).join(knowledge_release_items,
            knowledge_release_items.c.build_id == index_builds.c.id).join(knowledge_release_heads,
            knowledge_release_heads.c.release_id == knowledge_release_items.c.release_id)).mappings().all()
        for build in builds:
            document, _, _ = eligible(connection, store, build["workspace_id"], dict(build), verify_source=True)
            if document["withdrawn"] or document["lifecycle"] != "active":
                raise ValueError("restore_revoked_index")
        # PostgreSQL physically rebuilds its indexes during pg_restore. Business index
        # manifests and all original/parse/vector bytes are validated by eligible().
        if connection.execute(sa.text("SELECT count(*) FROM pg_index WHERE NOT indisvalid")).scalar_one():
            raise ValueError("restore_invalid_postgres_index")
    return {"objects": True, "indexes": True, "task_fences": True}
