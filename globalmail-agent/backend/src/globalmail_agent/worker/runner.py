"""One local API worker; no provider calls or fabricated email effects."""
import logging
from threading import Event, Thread
from uuid import uuid4

from globalmail_agent.worker.leases import LeaseService
from globalmail_agent.worker.protocol import complete_protocol

logger = logging.getLogger(__name__)


class ProtocolRunner:
    def __init__(self, engine, workspace_id):
        self.engine, self.workspace_id = engine, workspace_id
        self.owner = uuid4().hex
        self.leases = LeaseService(engine, workspace_id)
        self.stopping = Event()
        self.thread = Thread(target=self.run, name="globalmail-protocol", daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=5)

    def run(self):
        needs_restart, degraded = True, False
        while not self.stopping.is_set():
            try:
                self.leases.recover_expired(restart=needs_restart)
                needs_restart, degraded = False, False
                job = self.leases.claim(self.owner)
                if job:
                    complete_protocol(self.engine, self.workspace_id, job)
            except Exception:
                # Credentials and SQL payloads never reach logs; lease recovery is durable.
                if not degraded:
                    logger.warning("protocol_worker_dependency_unavailable")
                    degraded = True
            self.stopping.wait(0.25)
