"""Stopped exports, SDK deletion, and bounded v4 observation read-back.

Langfuse v4 represents the trace itself as its root observation. The removed
v3 trace GET endpoint is deliberately not used as a false absence signal.
"""
from datetime import datetime, timezone
import hashlib
import json
from time import monotonic, sleep
from uuid import UUID, uuid5
import httpx
from langfuse.api.client import LangfuseAPI
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.schema import SCOPE_KEYS, objects
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.observability.media_filter import safe_payload
from globalmail_agent.observability.records import TraceRecords
from globalmail_agent.observability.sdk_export import SdkExport


class PurgeService:
    def __init__(self, engine, store, settings, workspace=DEFAULT_WORKSPACE_ID, *, http_transport=None):
        self.engine, self.store, self.settings, self.workspace = engine, store, settings, workspace
        self.records = TraceRecords(engine, store, settings, workspace)
        self.http_transport = http_transport

    def purge_runs(self, run_ids):
        """Return True only after remote absence; failures retain buffers for retry.

        The caller removes local correlation/buffer rows only after this succeeds.
        Revocation is durable even when HTTP or a later run fails.
        """
        ids = sorted(set(run_ids), key=str)
        for run_id in ids:
            self.records.revoke(run_id)
        for run_id in ids:
            with self.records.export_lock(run_id):
                with self.engine.connect() as conn:
                    trace = conn.execute(sa.select(a.trace_correlations).where(
                        a.trace_correlations.c.workspace_id == self.workspace,
                        a.trace_correlations.c.run_id == run_id)).mappings().first()
                if trace is None or trace["reason_code"] == "observability_purged":
                    continue
                # Explicit rejection never entered ingestion. Every other attempted
                # send is conservative, including lost/partial acknowledgements.
                if (trace["attempts"] and trace["reason_code"] != "observability_http_failed"
                        or trace["reason_code"] in {"observability_exported", "observability_purge_pending"}):
                    self._remote(dict(trace))
                self._reason(run_id, "observability_purged")
        return True

    def _reason(self, run_id, reason):
        with self.engine.begin() as conn:
            conn.execute(a.trace_correlations.update().where(
                a.trace_correlations.c.run_id == run_id,
                a.trace_correlations.c.workspace_id == self.workspace,
                a.trace_correlations.c.export_status == "revoked").values(
                reason_code=reason, updated_at=sa.func.now()))

    def _remote(self, trace):
        settings = self.settings
        if not settings.langfuse_public_key.get_secret_value() or not settings.langfuse_secret_key.get_secret_value():
            raise ServiceError("observability_purge_not_configured", 503)
        try:
            # Deletion is an authorized internal reader of a revoked, scoped,
            # integrity-checked safe buffer; it never returns content to callers.
            value = self._buffer(trace)
            run_id = UUID(value["metadata"]["run_id"])
            if run_id != trace["run_id"]:
                raise ServiceError("observability_buffer_integrity_error", 503)
            identities = [uuid5(run_id, "run")] + [identity for identity, _ in SdkExport.ordered(value)]
            expected = {f"{SdkExport._span_id(identity):016x}" for identity in identities}
            meta = value["metadata"]
            window = {"from_start_time": datetime.fromtimestamp(meta["started_ns"] / 1e9 - 1, timezone.utc),
                "to_start_time": datetime.fromtimestamp(meta["ended_ns"] / 1e9 + 1, timezone.utc)}
            deadline = monotonic() + max(1, settings.langfuse_flush_timeout)
            with httpx.Client(timeout=settings.langfuse_http_timeout, trust_env=False,
                    transport=self.http_transport) as http:
                api = LangfuseAPI(base_url=settings.langfuse_base_url,
                    username=settings.langfuse_public_key.get_secret_value(),
                    password=settings.langfuse_secret_key.get_secret_value(), httpx_client=http)

                def options():
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        raise ServiceError("observability_purge_unconfirmed", 503)
                    return {"timeout_in_seconds": min(settings.langfuse_http_timeout, remaining), "max_retries": 0}

                def read():
                    result = api.observations.get_many(trace_id=trace["trace_id"], fields="core",
                        limit=129, **window, request_options=options())
                    if result.meta.cursor or any(row.trace_id != trace["trace_id"] for row in result.data):
                        raise ServiceError("observability_purge_unconfirmed", 503)
                    return [row.id for row in result.data]

                if trace["reason_code"] != "observability_purge_pending":
                    # Empty reads before deletion do not prove the ingestion queue
                    # is drained. Require the complete immutable receipt first.
                    visible = read()
                    if len(visible) != len(expected) or set(visible) != expected:
                        raise ServiceError("observability_ingestion_unconfirmed", 503)
                    # Durable before HTTP: a lost delete response or crash must
                    # not require already-deleted observations to reappear.
                    self._reason(trace["run_id"], "observability_purge_pending")
                elif not read():
                    sleep(min(0.1, max(0, deadline - monotonic())))
                    if not read():
                        return
                api.trace.delete(trace["trace_id"], request_options=options())
                empty_reads = 0
                for _ in range(3):
                    empty_reads = empty_reads + 1 if not read() else 0
                    if empty_reads == 2:
                        return
                    sleep(min(0.1, max(0, deadline - monotonic())))
                raise ServiceError("observability_purge_unconfirmed", 503)
        except ServiceError:
            raise
        except Exception:
            raise ServiceError("observability_purge_unavailable", 503) from None

    def _buffer(self, trace):
        """Private cleanup read after revocation; public reads must stay denied."""
        with self.engine.connect() as conn:
            row = conn.execute(sa.select(objects).where(objects.c.id == trace["export_object_id"],
                *[objects.c[k] == trace[k] for k in SCOPE_KEYS],
                objects.c.source_kind == "observability_buffer")).mappings().one()
        content = self.store._path(trace["export_object_id"]).read_bytes()
        if len(content) != row["size_bytes"] or hashlib.sha256(content).hexdigest() != row["sha256"]:
            raise ServiceError("observability_buffer_integrity_error", 503)
        return safe_payload(json.loads(content))
