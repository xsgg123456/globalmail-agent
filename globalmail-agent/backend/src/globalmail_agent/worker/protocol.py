"""Phase 3 terminal commit exercises authority/lease guards without a model."""
import sqlalchemy as sa

from globalmail_agent.adapters.conversation_schema import (
    agent_runs, conversations, domain_events, jobs, processing_cycles,
)
from globalmail_agent.application.event_store import append_ui_event
from globalmail_agent.worker.leases import (
    db_now, qualified, release_slot, slot_for_update, valid_lease,
)


def complete_protocol(engine, workspace_id, job):
    with engine.begin() as connection:
        slot = slot_for_update(connection, workspace_id, job["kind"])
        now = db_now(connection)
        if not valid_lease(slot, job["id"], job["lease_owner"], job["slot_fence"], now):
            return False
        conversation = connection.execute(sa.select(conversations).where(
            conversations.c.id == job["conversation_id"],
            conversations.c.workspace_id == workspace_id,
        ).with_for_update()).mappings().one()
        run = connection.execute(sa.select(agent_runs).where(
            agent_runs.c.id == job["run_id"]).with_for_update()).mappings().one()
        current_job = connection.execute(sa.select(jobs).where(jobs.c.id == job["id"]))
        if current_job.mappings().one()["status"] != "running" or not qualified(conversation, run):
            release_slot(connection, slot)
            return False
        connection.execute(agent_runs.update().where(agent_runs.c.id == run["id"])
            .values(status="completed", outcome="protocol_verified_model_not_connected",
                    finished_at=now, checkpoint_writable=False))
        connection.execute(jobs.update().where(jobs.c.id == job["id"])
            .values(status="completed", lease_expires_at=None))
        connection.execute(processing_cycles.update().where(processing_cycles.c.id == job["cycle_id"])
            .values(state="completed", completed_at=now))
        connection.execute(conversations.update().where(conversations.c.id == conversation["id"])
            .values(scheduling_state="idle", row_version=conversations.c.row_version + 1))
        connection.execute(domain_events.update().where(
            domain_events.c.conversation_id == conversation["id"],
            domain_events.c.status == "pending").values(status="processed"))
        append_ui_event(connection, conversation["id"], "run.completed",
                        {"run_id": str(run["id"]), "outcome": "protocol_verified_model_not_connected"})
        release_slot(connection, slot)
        return True
