"""Bounded run-ID queue and finite retries, completely outside business execution."""
from queue import Queue, Empty, Full
from threading import Event, Lock, Thread
from time import monotonic
import logging
from globalmail_agent.application.conversation_lock import ServiceError


class TraceExporter:
    def __init__(self, records, transport=None):
        self.records, self.settings = records, records.settings
        self.transport = transport
        self.queue = Queue(maxsize=self.settings.langfuse_queue_size)
        self.lock, self.stopping = Lock(), Event()
        self.identities = set()
        self.thread = Thread(target=self.run, name="globalmail-observability", daemon=True)
        records.exporter = self

    def start(self):
        if self.settings.langfuse_enabled:
            self.thread.start()

    def submit(self, run_id):
        with self.lock:
            if run_id in self.identities:
                return
            try:
                if self.stopping.is_set():
                    return  # Persisted pending buffers can resume in a later process.
                self.queue.put_nowait(run_id)
                self.identities.add(run_id)
            except Full:
                self.records.mark(run_id, "degraded", "observability_queue_full")

    def export_one(self, run_id, *, recovering=False):
        snapshot = None
        try:
            snapshot = self.records.payload(run_id)
            if snapshot is None:
                return
            trace, value = snapshot
            if not self.settings.langfuse_public_key.get_secret_value() or not self.settings.langfuse_secret_key.get_secret_value():
                self.records.mark(run_id, "degraded", "observability_not_configured", generation=trace["generation"])
                return
            if self.transport is None:
                from globalmail_agent.observability.sdk_export import SdkExport
                self.transport = SdkExport(self.settings)
            if trace["reason_code"] == "observability_ack_unknown":
                if recovering:
                    self._reconcile(run_id, trace, value)
                return
            for attempt in range(trace["attempts"], self.settings.langfuse_max_attempts):
                if self.stopping.is_set():
                    return
                # Revalidate every retry; reading a safe buffer never reexecutes a graph.
                latest = self.records.payload(run_id)
                if latest is None or latest[0]["generation"] != trace["generation"]:
                    return
                if not self.records.claim(run_id, trace["generation"], attempt):
                    return
                try:
                    success = self.transport.send(trace["trace_id"], value)
                except Exception:
                    success = False
                    self._reconcile(run_id, trace, value)
                    return
                if not success and getattr(self.transport, "ack_unknown", False):
                    self._reconcile(run_id, trace, value)
                    return
                # A revocation during HTTP wins over the local acknowledgement.
                latest = self.records.payload(run_id)
                if latest is None or latest[0]["generation"] != trace["generation"]:
                    return
                self.records.mark(run_id, "exported" if success else "pending", None if success else "observability_http_failed",
                    generation=trace["generation"], attempts=attempt + 1)
                if success:
                    return
                if not getattr(self.transport, "retryable", True):
                    break
                if self.stopping.wait(0.1 * (attempt + 1)):
                    return
            self.records.mark(run_id, "degraded", "observability_http_failed", generation=trace["generation"])
        except ServiceError as error:
            self.records.mark(run_id, "revoked" if error.status in {404, 410} else "degraded", "trace_revoked")
        except Exception:
            self.records.mark(run_id, "degraded", "observability_export_failed")

    def _reconcile(self, run_id, trace, value):
        confirmed = False
        try:
            confirmed = self.transport.reconcile(trace["trace_id"], value)
        except Exception:
            pass
        latest = self.records.payload(run_id)
        if latest is not None and latest[0]["generation"] == trace["generation"]:
            self.records.mark(run_id, "exported" if confirmed else "degraded",
                None if confirmed else "observability_ack_unknown", generation=trace["generation"])

    def run(self):
        try:
            try:
                for run_id in self.records.pending(self.settings.langfuse_queue_size + 1):
                    self.export_one(run_id, recovering=True)
            except Exception:
                logging.getLogger(__name__).warning("observability_recovery_unavailable")
            while not self.stopping.is_set():
                try:
                    run_id = self.queue.get(timeout=0.2)
                except Empty:
                    continue
                try:
                    self.export_one(run_id)
                finally:
                    with self.lock:
                        self.identities.discard(run_id)
                    self.queue.task_done()
        finally:
            if self.transport:
                try:
                    self.transport.close()
                except Exception:
                    logging.getLogger(__name__).warning("observability_shutdown_unavailable")

    def flush(self, timeout=None):
        deadline = monotonic() + (self.settings.langfuse_flush_timeout if timeout is None else min(timeout, 5))
        while self.queue.unfinished_tasks and monotonic() < deadline:
            self.stopping.wait(min(0.02, max(0, deadline - monotonic())))
        return self.queue.unfinished_tasks == 0

    def close(self):
        if self.thread.ident is None:
            self.stopping.set()
            if self.transport:
                self.transport.close()
            return
        self.flush()
        self.stopping.set()
        if self.thread.is_alive():
            self.thread.join(timeout=self.settings.langfuse_http_timeout + 0.5)
