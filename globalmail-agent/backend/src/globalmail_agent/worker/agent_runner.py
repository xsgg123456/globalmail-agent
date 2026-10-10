"""One global Agent slot, periodic leases, and explicit failure recovery."""
import logging
import time
from threading import Event, Thread
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.agent_schema import trace_correlations
from globalmail_agent.adapters.conversation_schema import agent_runs, jobs, processing_cycles, conversations
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.adapters.checkpoint_repository import CheckpointRepository
from globalmail_agent.agent.budget import Budget
from globalmail_agent.agent.context import load_context
from globalmail_agent.agent.graph import AgentGraph
from globalmail_agent.agent.guard import guarded
from globalmail_agent.agent.tool_gateway import ToolGateway
from globalmail_agent.application.commit_outcome import commit_outcome, existing_outcome
from globalmail_agent.application.risk_handoff import risk_handoff
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.application.event_store import append_ui_event
from globalmail_agent.worker.leases import LeaseService, db_now, slot_for_update, release_slot

logger = logging.getLogger(__name__)


class AgentRunner:
    def __init__(self, engine, store, workspace_id, model, embedding_gateway, *, observability=None):
        self.engine, self.store, self.workspace_id = engine, store, workspace_id
        self.model, self.embedding = model, embedding_gateway
        from globalmail_agent.observability.service import ObservabilityService
        from globalmail_agent.settings import Settings
        self.observability = observability or ObservabilityService(engine, store, Settings(), workspace_id)
        self.leases = LeaseService(engine, workspace_id)
        self.owner, self.stopping = uuid4().hex, Event()
        self.active = None
        self.last_image_cleanup = 0
        self.thread = Thread(target=self.run, name="globalmail-agent", daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        self.stopping.set()
        if self.active:
            self.fail(self.active, "worker_interrupted")
        self.thread.join(timeout=35)

    def _trace(self, job):
        with guarded(self.engine, self.workspace_id, job, check_knowledge=False) as (conn, conv, run, cycle):
            old = conn.execute(sa.select(trace_correlations.c.id).where(trace_correlations.c.run_id == run["id"])).scalar_one_or_none()
            if old is None:
                conn.execute(sa.insert(trace_correlations).values(id=uuid4(), **{k: conv[k] for k in SCOPE_KEYS},
                    conversation_id=conv["id"], run_id=run["id"], trace_id=uuid4().hex, export_status="local_only"))

    def execute(self, job):
        prior = existing_outcome(self.engine, self.workspace_id, job)
        if prior:
            return prior
        self.active = job
        heartbeat_stop = Event()
        def heartbeat():
            while not heartbeat_stop.wait(10):
                try:
                    if not self.leases.heartbeat(job["id"], job["lease_owner"], job["slot_fence"]):
                        return
                except Exception:
                    self.fail(job, "lease_heartbeat_failed")
                    return
        pulse = Thread(target=heartbeat, name="globalmail-agent-heartbeat", daemon=True)
        budget = context = recorder = None
        pulse.start()
        try:
            budget = Budget(self.engine, self.workspace_id, job)
            try:
                self._trace(job)
                recorder = self.observability.begin(job)
            except Exception:
                logger.warning("observability_record_unavailable")
            for rebuild in (False, True):
                context = load_context(self.engine, self.store, self.workspace_id, job, rebuild=rebuild)
                if context.payload["active_risks"]:
                    risks = context.payload["active_risks"]
                    return risk_handoff(self.engine, self.store, context, job, {
                        "language": risks[0]["language"], "facts": [],
                        "risk_flags": [{"kind": risk["kind"], "sources": risk["sources"]} for risk in risks]})
                if not self.model.configured:
                    raise ServiceError("model_not_configured", 503)
                gateway = ToolGateway(self.engine, self.store, self.embedding, context, job, budget)
                try:
                    output = AgentGraph(context, job, self.model, gateway, budget,
                        CheckpointRepository(self.engine, self.workspace_id, job, self.store)).invoke()
                    if output["understanding"]["risk_flags"]:
                        return risk_handoff(self.engine, self.store, context, job, output["understanding"])
                    if budget.active_ms() >= 120000:
                        raise ServiceError("budget_exhausted")
                    return commit_outcome(self.engine, self.store, context, job, output["understanding"], output["proposal"])
                except ServiceError as error:
                    # Danger was persisted before the next checkpoint: it survives knowledge/network errors.
                    from globalmail_agent.adapters.agent_schema import understanding_results
                    from globalmail_agent.adapters.body_store import read_bytes
                    import json
                    with self.engine.connect() as conn:
                        stored = conn.execute(sa.select(understanding_results.c.body_object_id).where(
                            understanding_results.c.run_id == job["run_id"])).scalar_one_or_none()
                        if stored:
                            conv = conn.execute(sa.select(conversations).where(conversations.c.id == context.conversation_id)).mappings().one()
                            value = json.loads(read_bytes(conn, self.store, conv, stored))
                            if value["risk_flags"]:
                                return risk_handoff(self.engine, self.store, context, job, value)
                    if error.code != "stale_release":
                        raise
                    if rebuild:
                        proposal = {"kind": "handoff", "data": {"reason": "conflicting_evidence",
                            "summary": "本轮知识连续变化，需要人工核对当前资料。", "gaps": ["无法锁定一致有效依据"], "draft": ""}}
                        return commit_outcome(self.engine, self.store, context, job,
                            output["understanding"] if "output" in locals() else {"language": "und", "facts": []}, proposal, safety=True)
        except ServiceError as error:
            self.fail(job, error.code)
            return {"error_code": error.code}
        except Exception:
            if context:
                try:
                    from globalmail_agent.adapters.agent_schema import understanding_results
                    from globalmail_agent.adapters.body_store import read_bytes
                    import json
                    with self.engine.connect() as conn:
                        stored = conn.execute(sa.select(understanding_results.c.body_object_id).where(
                            understanding_results.c.run_id == job["run_id"])).scalar_one_or_none()
                        if stored:
                            conv = conn.execute(sa.select(conversations).where(conversations.c.id == context.conversation_id)).mappings().one()
                            value = json.loads(read_bytes(conn, self.store, conv, stored))
                            if value["risk_flags"]:
                                return risk_handoff(self.engine, self.store, context, job, value)
                except Exception:
                    pass  # Revoked authority cannot be bypassed for a late safety result.
            self.fail(job, "agent_dependency_error")
            logger.warning("agent_dependency_error")
            return {"error_code": "agent_dependency_error"}
        finally:
            heartbeat_stop.set()
            pulse.join(timeout=5)
            if budget:
                budget.finish()
            if recorder:
                recorder.close()
            self.active = None

    def fail(self, job, code):
        try:
            with guarded(self.engine, self.workspace_id, job, check_knowledge=False) as (conn, conv, run, cycle):
                status = "budget_exhausted" if code in {"budget_exhausted", "input_budget_exceeded", "provider_usage_exceeded", "image_view_budget_exceeded"} else (
                    "interrupted" if code == "worker_interrupted" else "failed")
                conn.execute(agent_runs.update().where(agent_runs.c.id == run["id"]).values(status=status,
                    error_code=code, finished_at=db_now(conn), checkpoint_writable=False))
                conn.execute(jobs.update().where(jobs.c.id == job["id"]).values(status=status, error_code=code, lease_expires_at=None))
                conn.execute(processing_cycles.update().where(processing_cycles.c.id == cycle["id"]).values(state=status))
                conn.execute(conversations.update().where(conversations.c.id == conv["id"]).values(scheduling_state="failed",
                    auto_run_gate="disabled" if conv["persistent_human"] else "manual_retry_required",
                    row_version=conv["row_version"] + 1))
                from globalmail_agent.adapters.attachment_schema import message_attachments
                conn.execute(message_attachments.update().where(message_attachments.c.processing_run_id == run["id"],
                    message_attachments.c.status == "processing").values(status="failed", processing_run_id=None, failure_reason=code))
                append_ui_event(conn, conv["id"], "run.failed", {"run_id": str(run["id"]), "reason_code": code})
                release_slot(conn, slot_for_update(conn, self.workspace_id))
        except ServiceError:
            pass  # A newer authority/input already owns the state; never overwrite it.
        except Exception:
            logger.warning("agent_failure_record_unavailable")

    def run(self):
        restart = True
        while not self.stopping.is_set():
            try:
                self.leases.recover_expired(restart=restart)
                restart = False
                if time.monotonic() - self.last_image_cleanup >= 60:
                    from globalmail_agent.attachments.intake import AttachmentService
                    try:
                        AttachmentService(self.engine, self.store, self.workspace_id).cleanup_expired()
                    except Exception:
                        logger.warning("image_staging_cleanup_unavailable")
                    finally:
                        self.last_image_cleanup = time.monotonic()
                job = self.leases.claim(self.owner)
                if job:
                    self.execute(job)
            except Exception:
                logger.warning("agent_worker_dependency_unavailable")
            self.stopping.wait(0.25)
