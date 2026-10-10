"""Scoped correlations and safe object buffers; this module never schedules a run."""
import json
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import agent_runs, conversations
from globalmail_agent.adapters.schema import SCOPE_KEYS, deletion_journal, content_dependencies
from globalmail_agent.adapters.body_store import BodyWriter, read_bytes
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.attachments.revocation import check_content_access
from globalmail_agent.observability.media_filter import safe_payload


class TraceRecords:
    def __init__(self, engine, store, settings, workspace=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.settings, self.workspace = engine, store, settings, workspace
        self.exporter = None

    def _rows(self, conn, run_id):
        run = conn.execute(sa.select(agent_runs).where(agent_runs.c.id == run_id,
            agent_runs.c.workspace_id == self.workspace)).mappings().first()
        if run is None:
            raise ServiceError("run_not_found", 404)
        conv = conn.execute(sa.select(conversations).where(conversations.c.id == run["conversation_id"],
            *[conversations.c[k] == run[k] for k in SCOPE_KEYS])).mappings().one()
        if conv["lifecycle"] in {"deleting", "deleted"}:
            raise ServiceError("run_not_found", 404)
        trace = conn.execute(sa.select(a.trace_correlations).where(a.trace_correlations.c.run_id == run_id,
            *[a.trace_correlations.c[k] == run[k] for k in SCOPE_KEYS])).mappings().first()
        return conv, run, trace

    def _fence(self, conn, conv, run, trace):
        if conv["branch_generation"] != run["branch_generation"] or trace and trace["export_status"] == "revoked":
            raise ServiceError("trace_revoked", 410)
        context = conn.execute(sa.select(a.agent_run_contexts.c.context_object_id).where(
            a.agent_run_contexts.c.run_id == run["id"])).scalar_one_or_none()
        for object_id in (context, trace["export_object_id"] if trace else None):
            if object_id:
                check_content_access(conn, conv, object_id)
                ancestors = sa.select(sa.literal(object_id, type_=sa.Uuid).label("id")).cte("trace_ancestors", recursive=True)
                ancestors = ancestors.union(sa.select(content_dependencies.c.source_object_id).join(
                    ancestors, content_dependencies.c.dependent_object_id == ancestors.c.id).where(
                    *[content_dependencies.c[k] == conv[k] for k in SCOPE_KEYS]))
                if conn.execute(sa.select(deletion_journal.c.id).where(
                        *[deletion_journal.c[k] == conv[k] for k in SCOPE_KEYS],
                        deletion_journal.c.target_object_id.in_(sa.select(ancestors.c.id))).limit(1)).first():
                    raise ServiceError("trace_revoked", 410)
        from globalmail_agent.adapters.knowledge_schema import documents
        deps = conn.execute(sa.select(a.agent_run_dependencies).where(
            a.agent_run_dependencies.c.run_id == run["id"])).mappings()
        for dep in deps:
            doc = conn.execute(sa.select(documents).where(documents.c.id == dep["document_id"],
                documents.c.workspace_id == self.workspace)).mappings().first()
            if not doc or doc["lifecycle"] != "active" or doc["withdrawn"] or doc["revocation_epoch"] != dep["revocation_epoch"]:
                raise ServiceError("trace_revoked", 410)

    def get(self, run_id):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)
        with self.engine.connect() as conn:
            conv, run, trace = self._rows(conn, run_id)
            reason = trace["reason_code"] if trace else None
            status = trace["export_status"] if trace else "local_only"
            try:
                self._fence(conn, conv, run, trace)
            except ServiceError:
                status, reason = "revoked", "trace_revoked"
            if status != "revoked" and not self.settings.langfuse_enabled:
                status, reason = "disabled", "observability_disabled"
            trace_id = trace["trace_id"] if trace else None
            url = (f"{self.settings.langfuse_base_url}/project/{self.settings.langfuse_project_id}/traces/{trace_id}"
                if trace_id and status == "exported" else None)
            return {"run_id": str(run_id), "trace_id": trace_id, "trace_url": url,
                "export_status": status, "reason_code": reason,
                "pending_count": trace["pending_count"] if trace and status == "pending" else 0}

    def persist(self, job, observations, started, degraded):
        # Called after the business transaction. Its failure cannot change its result.
        try:
            with BodyWriter(self.store) as writer, self.engine.begin() as conn:
                conv, run, trace = self._rows(conn, job["run_id"])
                self._fence(conn, conv, run, trace)
                if trace is None:
                    return
                from globalmail_agent.observability.snapshot import snapshot
                value, sources = snapshot(conn, conv, run, observations, started)
                value = safe_payload(value)
                buffer_id = writer.put(conn, conv, json.dumps(value), "observability_buffer", sources)
                status = "degraded" if degraded else "pending" if self.settings.langfuse_enabled else "local_only"
                conn.execute(a.trace_correlations.update().where(a.trace_correlations.c.id == trace["id"]).values(
                    export_object_id=buffer_id, export_status=status, generation=trace["generation"] + 1,
                    attempts=0, pending_count=len(value["observations"]) if status == "pending" else 0,
                    reason_code="sanitization_failed" if degraded else None, updated_at=sa.func.now()))
            if status == "pending" and self.exporter:
                self.exporter.submit(job["run_id"])
        except ServiceError as error:
            self.mark(job["run_id"], "revoked" if error.status in {404, 410} else "degraded", "trace_revoked")
        except Exception:
            self.mark(job["run_id"], "degraded", "observability_buffer_failed")

    def payload(self, run_id):
        with self.engine.connect() as conn:
            conv, run, trace = self._rows(conn, run_id)
            self._fence(conn, conv, run, trace)
            if not trace or trace["export_status"] != "pending" or not trace["export_object_id"]:
                return None
            value = safe_payload(json.loads(read_bytes(conn, self.store, conv, trace["export_object_id"])))
            return dict(trace), value

    def pending(self, limit):
        with self.engine.connect() as conn:
            return list(conn.execute(sa.select(a.trace_correlations.c.run_id).where(
                a.trace_correlations.c.workspace_id == self.workspace,
                a.trace_correlations.c.export_status == "pending").order_by(
                a.trace_correlations.c.created_at).limit(limit)).scalars())

    def claim(self, run_id, generation, attempts):
        """CAS records the crash window before any byte can reach Langfuse."""
        with self.engine.begin() as conn:
            conv, run, trace = self._rows(conn, run_id)
            self._fence(conn, conv, run, trace)
            return conn.execute(a.trace_correlations.update().where(
                a.trace_correlations.c.run_id == run_id, a.trace_correlations.c.workspace_id == self.workspace,
                a.trace_correlations.c.generation == generation, a.trace_correlations.c.attempts == attempts,
                a.trace_correlations.c.export_status == "pending",
                sa.or_(a.trace_correlations.c.reason_code.is_(None),
                    a.trace_correlations.c.reason_code != "observability_ack_unknown")).values(
                reason_code="observability_ack_unknown", attempts=attempts + 1,
                updated_at=sa.func.now())).rowcount == 1

    def mark(self, run_id, status, reason=None, *, generation=None, attempts=None):
        try:
            with self.engine.begin() as conn:
                where = [a.trace_correlations.c.run_id == run_id, a.trace_correlations.c.workspace_id == self.workspace]
                if generation is not None:
                    where += [a.trace_correlations.c.generation == generation,
                        a.trace_correlations.c.export_status == "pending"]
                values = {"export_status": status, "reason_code": reason, "updated_at": sa.func.now()}
                if status != "pending":
                    values["pending_count"] = 0
                if attempts is not None:
                    values["attempts"] = attempts
                conn.execute(a.trace_correlations.update().where(*where).values(**values))
        except Exception:
            pass

    def revoke(self, run_id):
        """Phase12 stop-write entry; remote deletion remains its separate responsibility."""
        self.mark(run_id, "revoked", "trace_revoked")
