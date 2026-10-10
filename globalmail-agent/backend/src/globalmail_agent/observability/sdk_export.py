"""Official Langfuse wrappers + OTLP exporter, with acknowledged bounded exports.

The small collector preserves receipt timestamps and exposes OTLP's real return
value; Langfuse.flush() alone does not prove server acknowledgement. Its SDK
processor is disabled, so there is only one network exporter and no auto capture.
"""
import base64
from datetime import datetime, timezone
from time import monotonic, sleep
from uuid import UUID, uuid5
import httpx
from langfuse import Langfuse, LangfuseSpan, LangfuseGeneration, LangfuseTool, LangfuseRetriever
from langfuse import LangfuseOtelSpanAttributes as Attr
from opentelemetry.context import Context
from opentelemetry.trace import set_span_in_context
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.sdk.trace.id_generator import IdGenerator
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from globalmail_agent.observability.media_filter import safe_payload
from globalmail_agent.observability.transport import AcknowledgedSession


class ReceiptIds(IdGenerator):
    trace_id, span_id = 1, 1

    def generate_trace_id(self):
        return self.trace_id

    def generate_span_id(self):
        return self.span_id


class ReceiptCollector(SpanProcessor):
    def __init__(self):
        self.spans = []

    def on_start(self, span, parent_context=None):
        pass

    def on_end(self, span):
        if span.instrumentation_scope.name != "globalmail.observability" or len(self.spans) >= 129:
            raise ValueError("sanitization_failed")
        self.spans.append(span)

    def shutdown(self):
        self.spans.clear()

    def force_flush(self, timeout_millis=3000):
        return True


class NoopExporter(SpanExporter):
    def export(self, spans):
        return SpanExportResult.FAILURE  # This path is intentionally never an export acknowledgement.


class SdkExport:
    def __init__(self, settings):
        self.settings = settings
        self.ids, self.collector = ReceiptIds(), ReceiptCollector()
        self.provider = TracerProvider(resource=Resource({"service.name": "globalmail-agent"}),
            id_generator=self.ids, shutdown_on_exit=False)
        self.provider.add_span_processor(self.collector)
        self.http = httpx.Client(timeout=settings.langfuse_http_timeout, trust_env=False)
        self.client = Langfuse(public_key=settings.langfuse_public_key.get_secret_value(),
            secret_key=settings.langfuse_secret_key.get_secret_value(), base_url=settings.langfuse_base_url,
            httpx_client=self.http, timeout=settings.langfuse_http_timeout, debug=False,
            environment="local", release="phase11", tracer_provider=self.provider,
            should_export_span=lambda span: False, span_exporter=NoopExporter(),
            mask=lambda **kwargs: kwargs.get("data"), flush_at=1, flush_interval=0.2)
        self.tracer = self.provider.get_tracer("globalmail.observability")
        credentials = base64.b64encode((settings.langfuse_public_key.get_secret_value() + ":" +
            settings.langfuse_secret_key.get_secret_value()).encode()).decode()
        self.session = AcknowledgedSession()
        self.session.trust_env = False
        self.exporter = OTLPSpanExporter(endpoint=settings.langfuse_base_url + "/api/public/otel/v1/traces",
            headers={"Authorization": "Basic " + credentials, "x-langfuse-ingestion-version": "4"},
            timeout=settings.langfuse_http_timeout, session=self.session, max_request_size=512 * 1024)

    def build(self, trace_id, value):
        # This validation precedes every Langfuse wrapper constructor/media traversal.
        value = safe_payload(value)
        meta, rows = value["metadata"], value["observations"]
        ordered = self.ordered(value)
        self.collector.spans.clear()
        self.ids.trace_id = int(trace_id, 16)
        run_id = UUID(meta["run_id"])
        self.ids.span_id = self._span_id(uuid5(run_id, "run"))
        # Nonempty isolated context also prevents SDK's `parent_context or current`
        # fallback from importing third-party propagated metadata into the root.
        root = self.tracer.start_span("run", context=Context({"globalmail.safe": True}), start_time=meta["started_ns"])
        root.set_attribute(Attr.TRACE_NAME, "agent.run")
        # Session is scoped to workspace/mode/branch/conversation, never a mailbox address.
        session = uuid5(UUID(meta["workspace_id"]), meta["mode"] + meta["branch_id"] + meta["conversation_id"])
        root.set_attribute(Attr.TRACE_SESSION_ID, str(session))
        root.set_attribute(Attr.TRACE_PUBLIC, False)
        LangfuseSpan(otel_span=root, langfuse_client=self.client, metadata=meta, environment="local")
        spans = {}
        for identity, row in ordered:
            self.ids.span_id = self._span_id(identity)
            parent = spans[row["parent_observation_id"]] if row.get("parent_observation_id") else root
            span = self.tracer.start_span(row["node"], context=set_span_in_context(parent, Context()),
                start_time=row["started_ns"])
            span.set_attribute(Attr.TRACE_SESSION_ID, str(session))
            options = {"otel_span": span, "langfuse_client": self.client, "metadata": row,
                "level": "ERROR" if row["status"] == "failed" else "DEFAULT",
                "status_message": row.get("reason_code"), "environment": "local"}
            if row["node"] == "model":
                usage = {key: row[field] for key, field in (("input", "input_tokens"), ("output", "output_tokens")) if field in row}
                wrapper = LangfuseGeneration(**options, model=row.get("model"), usage_details=usage or None)
            else:
                wrapper_type = LangfuseTool if row["node"] == "tool" else LangfuseRetriever if row["node"] == "retrieval" else LangfuseSpan
                wrapper = wrapper_type(**options)
            wrapper.end(end_time=row["ended_ns"])
            spans[str(identity)] = span
        root.end(end_time=meta["ended_ns"])
        if len(self.collector.spans) != len(rows) + 1:
            raise ValueError("sdk_receipt_incomplete")
        return tuple(self.collector.spans)

    @classmethod
    def ordered(cls, value):
        """Parent dependency is authoritative; timestamps only sort ready siblings."""
        run_id = UUID(value["metadata"]["run_id"])
        pending = [(UUID(row["observation_id"]) if row.get("observation_id") else uuid5(run_id, "node:" + str(index)), row)
            for index, row in enumerate(sorted(value["observations"], key=lambda row: row["started_ns"]))]
        identities = {str(identity) for identity, _ in pending}
        span_ids = [cls._span_id(uuid5(run_id, "run")), *[cls._span_id(identity) for identity, _ in pending]]
        if len(identities) != len(pending) or len(set(span_ids)) != len(span_ids):
            raise ValueError("sdk_receipt_identity_conflict")
        if any(row.get("parent_observation_id") and row["parent_observation_id"] not in identities for _, row in pending):
            raise ValueError("sdk_receipt_parent_missing")
        result, emitted = [], set()
        while pending:
            ready = next(((identity, row) for identity, row in pending
                if not row.get("parent_observation_id") or row["parent_observation_id"] in emitted), None)
            if ready is None:
                raise ValueError("sdk_receipt_parent_cycle")
            pending.remove(ready)
            result.append(ready)
            emitted.add(str(ready[0]))
        return result

    @staticmethod
    def _span_id(identity):
        return (identity.int & ((1 << 64) - 1)) or 1

    def send(self, trace_id, value):
        self.session.reset()
        spans = self.build(trace_id, value)
        return self.exporter.export(spans) == SpanExportResult.SUCCESS and self.session.acknowledged

    @property
    def retryable(self):
        return self.session.retryable

    @property
    def ack_unknown(self):
        return self.session.ack_unknown

    def reconcile(self, trace_id, value):
        """Bounded v2 read confirms the entire immutable receipt, without sending."""
        value = safe_payload(value)
        meta, rows = value["metadata"], value["observations"]
        run_id = UUID(meta["run_id"])
        identities = [uuid5(run_id, "run")] + [identity for identity, _ in self.ordered(value)]
        expected = {f"{self._span_id(identity):016x}" for identity in identities}
        if len(expected) != len(identities):
            return False
        timestamp = lambda ns: datetime.fromtimestamp(ns / 1e9, timezone.utc).isoformat()
        params = {"traceId": trace_id, "fields": "core", "limit": 129,
            "fromStartTime": timestamp(meta["started_ns"] - 1000000000),
            "toStartTime": timestamp(meta["ended_ns"] + 1000000000)}
        auth = (self.settings.langfuse_public_key.get_secret_value(), self.settings.langfuse_secret_key.get_secret_value())
        deadline = monotonic() + min(self.settings.langfuse_flush_timeout, 3)
        for _ in range(3):
            if monotonic() >= deadline:
                break
            try:
                response = self.http.get(self.settings.langfuse_base_url + "/api/public/v2/observations",
                    params=params, auth=auth, timeout=min(self.settings.langfuse_http_timeout, deadline - monotonic()))
                result = response.json() if response.status_code == 200 else {}
                data = result.get("data", [])
                ids = [row["id"] for row in data if row.get("traceId") == trace_id]
                if len(ids) == len(data) == len(expected) and set(ids) == expected and not result.get("meta", {}).get("cursor"):
                    return True
            except Exception:
                pass
            sleep(min(0.1, max(0, deadline - monotonic())))
        return False

    def close(self):
        self.exporter.shutdown()
        self.provider.shutdown()
        self.client.shutdown()
        self.http.close()
        self.session.close()
