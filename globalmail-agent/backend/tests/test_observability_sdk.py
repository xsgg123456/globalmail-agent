"""Official SDK/media and protobuf HTTP boundaries, without external services."""
from copy import deepcopy
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from time import time_ns, monotonic, sleep
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
from pydantic import ValidationError
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest, ExportTraceServiceResponse
from globalmail_agent.settings import Settings
from globalmail_agent.observability.sdk_export import SdkExport
from langfuse import propagate_attributes


class Receiver(BaseHTTPRequestHandler):
    def do_POST(self):
        self.server.payloads.append(self.rfile.read(int(self.headers["Content-Length"])))
        sleep(self.server.delay)
        self.send_response(self.server.status)
        self.send_header("Content-Type", self.server.content_type)
        self.end_headers()
        try:
            self.wfile.write(self.server.reply)
        except OSError:
            pass

    def do_GET(self):
        rows = []
        for payload in self.server.payloads:
            wire = ExportTraceServiceRequest.FromString(payload)
            rows.extend({"id": span.span_id.hex(), "traceId": span.trace_id.hex()} for resource in
                wire.resource_spans for scope in resource.scope_spans for span in scope.spans)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"data": rows, "meta": {}}).encode())

    def log_message(self, *args):
        pass


class SdkBoundaryTests(TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
        self.server.status, self.server.reply, self.server.payloads = 200, b"", []
        self.server.content_type = "application/x-protobuf"
        self.server.delay = 0
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.transport = SdkExport(Settings(langfuse_enabled=True, langfuse_http_timeout=0.2,
            langfuse_base_url=f"http://127.0.0.1:{self.server.server_port}",
            langfuse_public_key="pk-lf-" + uuid4().hex, langfuse_secret_key="local-test-only"))
        self.addCleanup(self.transport.close)
        now = time_ns()
        self.trace_id = uuid4().hex
        parent, child = str(uuid4()), str(uuid4())
        self.value = {"metadata": {"run_id": str(uuid4()), "workspace_id": str(uuid4()),
            "mode": "simulation", "branch_id": str(uuid4()), "conversation_id": str(uuid4()),
            "started_ns": now, "ended_ns": now + 5000000}, "observations": [
                {"node": "model", "observation_id": child, "parent_observation_id": parent,
                    "status": "completed", "started_ns": now + 1000000, "ended_ns": now + 2000000,
                    "model": "qwen3.7-plus", "input_tokens": 20, "output_tokens": 10},
                {"node": "understanding", "observation_id": parent,
                    "status": "completed", "started_ns": now, "ended_ns": now + 3000000}]}

    def test_original_times_parent_tree_and_single_generation_usage_in_actual_http(self):
        self.assertTrue(self.transport.send(self.trace_id, self.value))
        wire = ExportTraceServiceRequest.FromString(self.server.payloads[0])
        spans = [span for resource in wire.resource_spans for scope in resource.scope_spans for span in scope.spans]
        self.assertEqual(len(spans), 3)
        model = next(span for span in spans if span.name == "model")
        parent = next(span for span in spans if span.name == "understanding")
        root = next(span for span in spans if span.name == "run")
        self.assertEqual(model.parent_span_id, parent.span_id)
        self.assertEqual(parent.parent_span_id, root.span_id)
        self.assertEqual(model.start_time_unix_nano, self.value["observations"][0]["started_ns"])
        self.assertEqual(model.end_time_unix_nano, self.value["observations"][0]["ended_ns"])
        self.assertTrue(all(span.trace_id.hex() == self.trace_id for span in spans))
        usage = [attribute for span in spans for attribute in span.attributes if attribute.key == "langfuse.observation.usage_details"]
        self.assertEqual(len(usage), 1)
        self.assertIn('"input": 20', usage[0].value.string_value)

    def test_equal_start_child_completed_first_keeps_actual_parent_dependency(self):
        self.value["observations"][0]["started_ns"] = self.value["observations"][1]["started_ns"]
        self.assertTrue(self.transport.send(self.trace_id, self.value))
        wire = ExportTraceServiceRequest.FromString(self.server.payloads[0])
        spans = [span for resource in wire.resource_spans for scope in resource.scope_spans for span in scope.spans]
        model = next(span for span in spans if span.name == "model")
        parent = next(span for span in spans if span.name == "understanding")
        root = next(span for span in spans if span.name == "run")
        self.assertEqual(model.parent_span_id, parent.span_id)
        self.assertEqual(parent.parent_span_id, root.span_id)
        self.assertEqual(model.start_time_unix_nano, parent.start_time_unix_nano)

    def test_missing_or_cyclic_parent_fails_before_sdk_media_or_http(self):
        media = self.transport.client._resources._media_manager
        for missing in (True, False):
            value = deepcopy(self.value)
            if missing:
                value["observations"][0]["parent_observation_id"] = str(uuid4())
            else:
                value["observations"][1]["parent_observation_id"] = value["observations"][0]["observation_id"]
            with patch.object(media, "_find_and_process_media", wraps=media._find_and_process_media) as traversal:
                with self.assertRaises(ValueError):
                    self.transport.send(self.trace_id, value)
                traversal.assert_not_called()
        self.assertEqual(self.server.payloads, [])

    def test_raw_media_url_and_exception_rejected_before_sdk_media_traversal(self):
        media = self.transport.client._resources._media_manager
        for key, value in (("body", "customer@example.test SECRET_SENTINEL"),
                ("input", b"RAW_IMAGE_SENTINEL"), ("output", "data:image/png;base64,SECRET_SENTINEL"),
                ("error", "https://reachable.invalid/private-image.png"),
                ("run_id", "CUSTOMER_SECRET_SENTINEL"), ("reason_code", "SECRET_SENTINEL")):
            invalid = deepcopy(self.value)
            invalid["observations"][0][key] = value
            with patch.object(media, "_find_and_process_media", wraps=media._find_and_process_media) as traversal:
                with self.assertRaises(ValueError):
                    self.transport.send(self.trace_id, invalid)
                traversal.assert_not_called()
        self.assertEqual(self.server.payloads, [])

    def test_http_rejection_and_partial_rejection_are_real_failure(self):
        self.server.status = 401
        self.assertFalse(self.transport.send(self.trace_id, self.value))
        self.server.status = 200
        response = ExportTraceServiceResponse()
        response.partial_success.rejected_spans = 1
        self.server.reply = response.SerializeToString()
        self.assertFalse(self.transport.send(self.trace_id, self.value))
        self.server.reply = b""
        self.assertTrue(self.transport.send(self.trace_id, self.value))
        self.assertEqual(len(self.server.payloads), 3)

    def test_third_party_propagated_metadata_cannot_join_safe_spans(self):
        with propagate_attributes(session_id="SECRET_SENTINEL@example.test",
                metadata={"raw_payload": "SECRET_SENTINEL"}, tags=["SECRET_SENTINEL"]):
            self.assertTrue(self.transport.send(self.trace_id, self.value))
        self.assertNotIn(b"SECRET_SENTINEL", self.server.payloads[0])

    def test_official_v4_events_only_json_queue_receipt_is_acknowledged(self):
        self.server.content_type = "application/json; charset=utf-8"
        for response in ({}, {"name": "otel", "id": "queue-test", "stacktrace": []}):
            self.server.reply = json.dumps(response).encode()
            self.assertTrue(self.transport.send(self.trace_id, self.value))
        for response in ({"error": "failed"}, {"partialSuccess": {"rejectedSpans": "1"}}):
            self.server.reply = json.dumps(response).encode()
            self.assertFalse(self.transport.send(self.trace_id, self.value))

    def test_network_timeout_is_bounded_and_cannot_mark_success(self):
        self.server.shutdown()
        started = monotonic()
        self.assertFalse(self.transport.send(self.trace_id, self.value))
        self.assertLess(monotonic() - started, 1)

    def test_sdk_internal_status_and_connection_retries_are_disabled(self):
        import requests
        for status in (429, 503):
            self.server.status = status
            before = len(self.server.payloads)
            self.assertFalse(self.transport.send(self.trace_id, self.value))
            self.assertEqual(len(self.server.payloads), before + 1)
            self.assertEqual(self.transport.retryable, status == 429)
            self.assertEqual(self.transport.ack_unknown, status == 503)
        for error, retryable in ((requests.ConnectTimeout("SECRET_SENTINEL"), True),
                (requests.ReadTimeout("SECRET_SENTINEL"), False)):
            with patch("requests.Session.request", side_effect=error) as network, self.assertLogs(
                    "opentelemetry.exporter.otlp.proto.http.trace_exporter", level="ERROR") as logs:
                self.assertFalse(self.transport.send(self.trace_id, self.value))
            self.assertEqual(network.call_count, 1)
            self.assertEqual(self.transport.retryable, retryable)
            self.assertNotIn("SECRET_SENTINEL", str(logs.output))

    def test_raw_exception_context_and_remote_payload_never_enter_sdk_transport(self):
        import requests
        with patch("requests.Session.request", side_effect=requests.ReadTimeout("RAW_SECRET_SENTINEL")):
            receipt = self.transport.session.request("POST", "http://127.0.0.1:1")
        self.assertEqual((receipt.status_code, receipt.reason, receipt.content),
            (400, "observability_transport_failed", b""))
        self.assertNotIn("RAW_SECRET_SENTINEL", repr(vars(receipt)))
        self.server.content_type = "application/json"
        self.server.reply = b'{"error":"RAW_SECRET_SENTINEL","stacktrace":["RAW_SECRET_SENTINEL"]}'
        receipt = self.transport.session.request("POST", f"http://127.0.0.1:{self.server.server_port}", data=b"safe")
        self.assertEqual((receipt.status_code, receipt.content), (200, b""))
        self.assertTrue(self.transport.ack_unknown)
        self.assertNotIn("RAW_SECRET_SENTINEL", repr(vars(receipt)))

    def test_response_lost_after_acceptance_reconciles_without_resending(self):
        self.server.delay = 0.3
        self.assertFalse(self.transport.send(self.trace_id, self.value))
        self.assertTrue(self.transport.ack_unknown)
        self.assertFalse(self.transport.retryable)
        self.assertTrue(self.transport.reconcile(self.trace_id, self.value))
        self.assertEqual(len(self.server.payloads), 1)

    def test_reconciliation_rejects_duplicate_and_incomplete_remote_receipts(self):
        self.assertTrue(self.transport.send(self.trace_id, self.value))
        self.assertTrue(self.transport.reconcile(self.trace_id, self.value))
        self.server.payloads.append(self.server.payloads[0])
        self.assertFalse(self.transport.reconcile(self.trace_id, self.value))
        self.server.payloads.clear()
        self.assertFalse(self.transport.reconcile(self.trace_id, self.value))

    def test_non_loopback_config_and_embedded_credentials_are_rejected(self):
        for url in ("https://cloud.langfuse.com", "http://127.0.0.1@evil.test", "http://localhost/private",
                "http://127.0.0.1:3001?secret=value"):
            with self.assertRaises(ValidationError):
                Settings(langfuse_base_url=url)
