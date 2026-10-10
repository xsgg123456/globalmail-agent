"""Observation lifecycle shared by the application and direct worker integrations."""
from globalmail_agent.observability.records import TraceRecords
from globalmail_agent.observability.exporter import TraceExporter
from globalmail_agent.observability.tracing import Recorder
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID


class ObservabilityService:
    def __init__(self, engine, store, settings, workspace=DEFAULT_WORKSPACE_ID, transport=None):
        self.records = TraceRecords(engine, store, settings, workspace)
        self.exporter = TraceExporter(self.records, transport)

    def begin(self, job):
        return Recorder(self.records, job)

    def start(self):
        self.exporter.start()

    def flush(self, timeout=None):
        return self.exporter.flush(timeout)

    def close(self):
        self.exporter.close()
