"""Versioned explicit controls; GET never creates or resumes a task."""
from uuid import uuid4

import sqlalchemy as sa

from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.adapters.conversation_schema import (
    agent_runs, conversations, jobs, processing_cycles,
)
from globalmail_agent.application.conversation_lock import (
    DEFAULT_WORKSPACE_ID, ServiceError, lock_conversation,
)
from globalmail_agent.application.event_store import append_ui_event
from globalmail_agent.application.idempotency import prior, remember
from globalmail_agent.worker.leases import db_now, release_slot, slot_for_update


class JobService:
    def __init__(self, engine, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.workspace_id = engine, workspace_id

    def _run(self, connection, run_id):
        run = connection.execute(sa.select(agent_runs).where(
            agent_runs.c.id == run_id, agent_runs.c.workspace_id == self.workspace_id,
        )).mappings().first()
        if run is None:
            raise ServiceError("run_not_found", 404)
        return run

    def get(self, run_id):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)
        with self.engine.connect() as connection:
            run = self._run(connection, run_id)
            job = connection.execute(sa.select(jobs).where(jobs.c.run_id == run_id)).mappings().one()
            return {"run": dict(run), "job": dict(job)}

    def control(self, run_id, action, command, key):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)
        payload, operation = command.model_dump(mode="json"), f"run:{run_id}:{action}"
        with self.engine.begin() as connection:
            previous, digest = prior(connection, self.workspace_id, key, operation, payload)
            if previous is not None:
                return previous
            run = self._run(connection, run_id)
            conversation = lock_conversation(connection, run["conversation_id"], self.workspace_id,
                                             expected_version=command.expected_version)
            # Re-read after locks so concurrent completion cannot be stopped or retried twice.
            run = self._run(connection, run_id)
            if action == "stop":
                result = self._stop(connection, conversation, run)
            else:
                result = self._retry(connection, conversation, run)
            remember(connection, self.workspace_id, key, operation, digest, result)
            return result

    def _stop(self, connection, conversation, run):
        if run["status"] not in {"queued", "running"}:
            raise ServiceError("run_not_active")
        from globalmail_agent.attachments.lifecycle import interrupt_images
        interrupt_images(connection, [run["id"]])
        now = db_now(connection)
        connection.execute(agent_runs.update().where(agent_runs.c.id == run["id"])
            .values(status="stopped", stop_requested=True, checkpoint_writable=False,
                    error_code="user_stopped", finished_at=now))
        job = connection.execute(sa.select(jobs).where(jobs.c.run_id == run["id"])).mappings().one()
        connection.execute(jobs.update().where(jobs.c.id == job["id"])
            .values(status="stopped", lease_expires_at=None))
        slot = slot_for_update(connection, self.workspace_id, job["kind"])
        if slot and slot["job_id"] == job["id"]:
            release_slot(connection, slot)
        connection.execute(processing_cycles.update().where(
            processing_cycles.c.id == run["processing_cycle_id"]).values(state="stopped"))
        version = conversation["row_version"] + 1
        connection.execute(conversations.update().where(conversations.c.id == conversation["id"])
            .values(authority_epoch=conversation["authority_epoch"] + 1,
                    auto_run_gate="disabled" if conversation["persistent_human"] else "manual_retry_required",
                    scheduling_state="stopped", row_version=version))
        append_ui_event(connection, conversation["id"], "run.stopped", {"run_id": str(run["id"])})
        return {"conversation_id": str(conversation["id"]), "run_id": str(run["id"]), "version": version}

    def _retry(self, connection, conversation, run):
        internal = conversation["persistent_human"] and conversation["processing_owner"] in {"human_review", "human_wait_customer"}
        if (run["status"] not in {"failed", "interrupted", "stopped"}
                or conversation["lifecycle"] != "open" or (conversation["processing_owner"] != "agent" and not internal)
                or conversation["auto_run_gate"] != ("disabled" if internal else "manual_retry_required")
                or conversation["input_revision"] != run["input_revision"]
                or conversation["branch_generation"] != run["branch_generation"]):
            raise ServiceError("retry_not_allowed")
        cycle = connection.execute(sa.select(processing_cycles).where(
            processing_cycles.c.id == run["processing_cycle_id"])).mappings().one()
        latest = connection.execute(sa.select(sa.func.max(agent_runs.c.attempt_no)).where(
            agent_runs.c.processing_cycle_id == cycle["id"])).scalar_one()
        if latest != run["attempt_no"] or cycle["final_message_id"] or cycle["state"] == "completed":
            raise ServiceError("cycle_already_completed")
        new_run, new_job = uuid4(), uuid4()
        scope = {key: conversation[key] for key in SCOPE_KEYS}
        versions = {key: conversation[key] for key in ("input_revision", "authority_epoch", "branch_generation")}
        connection.execute(sa.insert(agent_runs).values(id=new_run, **scope, **versions,
            conversation_id=conversation["id"], processing_cycle_id=cycle["id"],
            execution_mode="human_assist" if internal else "autonomous",
            attempt_no=latest + 1, status="queued", trigger_id=run["trigger_id"]))
        connection.execute(sa.insert(jobs).values(id=new_job, **scope, conversation_id=conversation["id"],
            run_id=new_run, cycle_id=cycle["id"], kind="agent", status="queued", attempt_no=latest + 1))
        connection.execute(processing_cycles.update().where(processing_cycles.c.id == cycle["id"])
            .values(state="queued", completed_at=None))
        version = conversation["row_version"] + 1
        connection.execute(conversations.update().where(conversations.c.id == conversation["id"])
            .values(auto_run_gate="disabled" if internal else "open", scheduling_state="queued", row_version=version))
        append_ui_event(connection, conversation["id"], "run.retried", {"run_id": str(new_run)})
        return {"conversation_id": str(conversation["id"]), "run_id": str(new_run),
                "job_id": str(new_job), "processing_cycle_id": str(cycle["id"]), "version": version}
