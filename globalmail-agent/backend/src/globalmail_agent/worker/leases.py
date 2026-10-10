"""Short PostgreSQL lease transactions; effects always fence the slot first."""
from datetime import timedelta
from uuid import UUID

import sqlalchemy as sa

from globalmail_agent.adapters.conversation_schema import (
    agent_slots, agent_runs, conversations, jobs, processing_cycles,
)
from globalmail_agent.application.event_store import append_ui_event


def db_now(connection):
    return connection.execute(sa.select(sa.func.clock_timestamp())).scalar_one()


def slot_for_update(connection, workspace_id, slot_key="agent", *, skip_locked=False):
    return connection.execute(sa.select(agent_slots).where(
        agent_slots.c.workspace_id == workspace_id, agent_slots.c.slot_key == slot_key,
    ).with_for_update(skip_locked=skip_locked)).mappings().first()


def qualified(conversation, run):
    internal = run.get("execution_mode") == "human_assist"
    authority = (conversation.get("persistent_human") and conversation["processing_owner"] in
        {"human_review", "human_wait_customer"} and conversation["auto_run_gate"] == "disabled") if internal else (
        conversation["processing_owner"] == "agent" and conversation["auto_run_gate"] == "open"
        and not conversation.get("persistent_human"))
    return (conversation["lifecycle"] == "open"
            and authority
            and not run["stop_requested"]
            and all(conversation[key] == run[key] for key in (
                "input_revision", "authority_epoch", "branch_generation")))


class LeaseService:
    def __init__(self, engine, workspace_id: UUID):
        self.engine, self.workspace_id = engine, workspace_id

    def claim(self, owner: str, slot_key="agent"):
        with self.engine.begin() as connection:
            slot = slot_for_update(connection, self.workspace_id, slot_key, skip_locked=True)
            if not slot or slot["job_id"] is not None:
                return None
            candidate = connection.execute(sa.select(jobs).where(
                jobs.c.workspace_id == self.workspace_id, jobs.c.kind == slot_key,
                jobs.c.status == "queued", jobs.c.conversation_id.is_not(None),
            ).order_by(jobs.c.created_at, jobs.c.id).limit(1)).mappings().first()
            if candidate is None:
                return None
            conversation = connection.execute(sa.select(conversations).where(
                conversations.c.id == candidate["conversation_id"],
                conversations.c.workspace_id == self.workspace_id,
            ).with_for_update()).mappings().one()
            job = connection.execute(sa.select(jobs).where(jobs.c.id == candidate["id"])
                .with_for_update(skip_locked=True)).mappings().first()
            if not job or job["status"] != "queued":
                return None
            run = connection.execute(sa.select(agent_runs).where(
                agent_runs.c.id == job["run_id"])).mappings().one()
            if not qualified(conversation, run):
                connection.execute(jobs.update().where(jobs.c.id == job["id"])
                                   .values(status="cancelled"))
                connection.execute(agent_runs.update().where(agent_runs.c.id == run["id"])
                                   .values(status="cancelled", checkpoint_writable=False))
                return None
            now, fence = db_now(connection), slot["fence"] + 1
            expiry = now + timedelta(seconds=60 if slot_key == "agent" else 90)
            connection.execute(agent_slots.update().where(agent_slots.c.id == slot["id"])
                .values(job_id=job["id"], lease_owner=owner, lease_expires_at=expiry, fence=fence))
            connection.execute(jobs.update().where(jobs.c.id == job["id"])
                .values(status="running", lease_owner=owner, lease_expires_at=expiry, slot_fence=fence))
            connection.execute(agent_runs.update().where(agent_runs.c.id == run["id"])
                .values(status="running", started_at=now))
            connection.execute(processing_cycles.update().where(processing_cycles.c.id == job["cycle_id"])
                .values(state="running"))
            connection.execute(conversations.update().where(conversations.c.id == conversation["id"])
                .values(scheduling_state="running", row_version=conversations.c.row_version + 1))
            append_ui_event(connection, conversation["id"], "run.running", {"run_id": str(run["id"])})
            return {**dict(job), "status": "running", "lease_owner": owner,
                    "lease_expires_at": expiry, "slot_fence": fence}

    def heartbeat(self, job_id, owner, fence, slot_key="agent"):
        with self.engine.begin() as connection:
            slot = slot_for_update(connection, self.workspace_id, slot_key)
            now = db_now(connection)
            if not valid_lease(slot, job_id, owner, fence, now):
                return False
            job = connection.execute(sa.select(jobs).where(jobs.c.id == job_id)
                .with_for_update()).mappings().one()
            if job["status"] != "running":
                return False
            expiry = now + timedelta(seconds=60 if slot_key == "agent" else 90)
            connection.execute(agent_slots.update().where(agent_slots.c.id == slot["id"])
                               .values(lease_expires_at=expiry))
            connection.execute(jobs.update().where(jobs.c.id == job_id)
                               .values(lease_expires_at=expiry))
            return True

    def recover_expired(self, *, restart=False):
        """Restart is reserved for the single local API startup, never a GET."""
        recovered = []
        for slot_key in ("agent", "knowledge"):
            with self.engine.begin() as connection:
                slot = slot_for_update(connection, self.workspace_id, slot_key)
                if not slot or slot["job_id"] is None:
                    continue
                now = db_now(connection)
                if not restart and slot["lease_expires_at"] and slot["lease_expires_at"] > now:
                    continue
                job = connection.execute(sa.select(jobs).where(jobs.c.id == slot["job_id"]))
                job = job.mappings().one()
                # Knowledge versions use their own worker and recovery contract.
                if job["conversation_id"] is None:
                    continue
                conversation = connection.execute(sa.select(conversations).where(
                    conversations.c.id == job["conversation_id"]
                ).with_for_update()).mappings().one()
                if job["status"] == "running":
                    connection.execute(jobs.update().where(jobs.c.id == job["id"])
                        .values(status="interrupted", lease_expires_at=None))
                    connection.execute(agent_runs.update().where(agent_runs.c.id == job["run_id"])
                        .values(status="interrupted", error_code="worker_interrupted",
                                checkpoint_writable=False, finished_at=now))
                    connection.execute(processing_cycles.update().where(
                        processing_cycles.c.id == job["cycle_id"]).values(state="interrupted"))
                    run = connection.execute(sa.select(agent_runs).where(
                        agent_runs.c.id == job["run_id"])).mappings().one()
                    if qualified(conversation, run):
                        connection.execute(conversations.update().where(
                            conversations.c.id == conversation["id"])
                            .values(auto_run_gate="disabled" if conversation["persistent_human"] else "manual_retry_required", scheduling_state="failed",
                                    row_version=conversations.c.row_version + 1))
                    append_ui_event(connection, conversation["id"], "run.interrupted",
                                    {"run_id": str(job["run_id"])})
                    recovered.append(job["run_id"])
                    from globalmail_agent.attachments.lifecycle import interrupt_images
                    interrupt_images(connection, [job["run_id"]])
                release_slot(connection, slot)
        return recovered


def valid_lease(slot, job_id, owner, fence, now):
    return bool(slot and slot["job_id"] == job_id and slot["lease_owner"] == owner
                and slot["fence"] == fence and slot["lease_expires_at"]
                and slot["lease_expires_at"] > now)


def release_slot(connection, slot):
    connection.execute(agent_slots.update().where(agent_slots.c.id == slot["id"])
        .values(job_id=None, lease_owner=None, lease_expires_at=None, fence=slot["fence"] + 1))
