"""Recover durable pending deletions without busy retrying failed requests."""
from threading import Event, Thread
import logging
import sqlalchemy as sa


class CleanupRunner:
    def __init__(self, service):
        self.service = service
        self.stopping = Event()
        self.thread = Thread(target=self.run, name="globalmail-cleanup", daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=15)

    def run(self):
        from globalmail_agent.adapters.lifecycle_schema import deletion_requests as requests
        while not self.stopping.is_set():
            try:
                with self.service.engine.connect() as conn:
                    identity = conn.execute(sa.select(requests.c.id).where(
                        requests.c.workspace_id == self.service.workspace,
                        requests.c.status.in_(["revoked", "purging", "verifying"])).order_by(
                        requests.c.created_at).limit(1)).scalar_one_or_none()
                if identity:
                    self.service.process(identity)
            except Exception:
                logging.getLogger(__name__).warning("cleanup_iteration_failed")
            self.stopping.wait(1)
