"""One durable knowledge slot, with each parser isolated in a bounded child."""
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread
from uuid import uuid4

from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.jobs import KnowledgeJobService
from globalmail_agent.knowledge.parser_process import parse_bytes, ParserFailure, ParserStopped
from globalmail_agent.knowledge.parser_profiles import fingerprint

logger = logging.getLogger(__name__)


class KnowledgeRunner:
    def __init__(self, engine, store, workspace_id):
        self.store = store
        self.jobs = KnowledgeJobService(engine, store, workspace_id)
        self.owner = uuid4().hex
        self.stopping = Event()
        self.thread = Thread(target=self.run, name="globalmail-knowledge", daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        self.stopping.set()
        # The child observes this flag during its bounded polling loop.
        self.thread.join(timeout=20)

    def execute(self, job):
        if job["parser_fingerprint"] != fingerprint(job["parser_profile_id"]):
            raise ParserFailure("parser_configuration_changed")
        def current():
            return not self.stopping.is_set() and self.jobs.heartbeat(job, self.owner, job["slot_fence"])
        source = self.jobs.source(job)
        cached = self.jobs.cached_result(job)
        if cached:
            if current():
                self.jobs.complete(job, cached)
            return
        # Private temporary originals and logs disappear on success, error and cancellation.
        with TemporaryDirectory(prefix="globalmail_parser_") as temporary:
            result = parse_bytes(source, job["format"], job["parser_profile_id"], Path(temporary),
                                 current, stopped=self.stopping.is_set)
            if result.parser_versions.get("adapter_fingerprint") != job["parser_fingerprint"]:
                raise ParserFailure("parser_configuration_changed")
            self.jobs.complete(job, result.model_dump(mode="json"), Path(temporary))

    def run(self):
        restarting, degraded = True, False
        while not self.stopping.is_set():
            job = None
            try:
                self.jobs.recover_expired(restart=restarting)
                restarting, degraded = False, False
                job = self.jobs.claim(self.owner)
                if job:
                    self.execute(job)
            except ParserStopped:
                if job:
                    self.safe_fail(job, "worker_interrupted", True)
            except ParserFailure as error:
                if job:
                    self.safe_fail(job, error.code, error.retryable)
            except ServiceError as error:
                if job:
                    self.safe_fail(job, error.code, error.status == 503)
            except Exception:
                if not degraded:
                    logger.warning("knowledge_worker_dependency_unavailable")
                    degraded = True
                if job:
                    self.safe_fail(job, "parser_dependency_unavailable", True)
            self.stopping.wait(0.25)

    def safe_fail(self, job, code, retryable):
        try:
            self.jobs.fail(job, code, retryable)
        except Exception:
            logger.warning("knowledge_worker_recovery_deferred")
