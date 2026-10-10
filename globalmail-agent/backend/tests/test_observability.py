"""Real PostgreSQL observations; scripted outputs prove engineering, not model quality."""
import json
from pathlib import Path
from threading import Event
from time import monotonic
from unittest.mock import patch
from uuid import UUID, uuid4
import sqlalchemy as sa
from fastapi.testclient import TestClient
from agent_fixture import AgentFixture, ScriptedModel, understanding, terminal, call
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.schema import content_dependencies, deletion_journal, SCOPE_KEYS
from globalmail_agent.adapters.conversation_schema import conversations
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.observability.service import ObservabilityService
from globalmail_agent.observability.records import TraceRecords
from globalmail_agent.observability.tracing import observation
from globalmail_agent.worker.agent_runner import AgentRunner
from globalmail_agent.main import create_app
from globalmail_agent.settings import Settings

SENTINEL = "customer-secret@example.test 123 Sensitive Lane sk-SECRET-SENTINEL"


class FakeTransport:
    def __init__(self, answers=(True,)):
        self.answers, self.payloads = list(answers), []

    def send(self, trace_id, value):
        self.payloads.append((trace_id, value))
        return self.answers.pop(0) if self.answers else False

    def close(self):
        pass


class ObservabilityTests(AgentFixture):
    def settings(self, **changes):
        return Settings(object_root=Path(self.temp.name), langfuse_enabled=True,
            langfuse_public_key="pk-lf-" + uuid4().hex, langfuse_secret_key="test-only", **changes)

    def observer(self, transport=None, **changes):
        observer = ObservabilityService(self.engine, self.store, self.settings(**changes), transport=transport or FakeTransport())
        self.addCleanup(observer.close)
        return observer

    def run_mail(self, observer, *, model=None, email=None):
        cid, rid = self.create_mail(SENTINEL, email=email or uuid4().hex + "@example.test")
        model = model or ScriptedModel(understanding, {"calls": [call("get_case_context", {})]},
            {**terminal(), "reasoning_content": SENTINEL})
        job = self.claimed()
        output = AgentRunner(self.engine, self.store, DEFAULT_WORKSPACE_ID, model, None,
            observability=observer).execute(job)
        return cid, rid, job, output, model

    def test_actual_node_receipts_safe_dependencies_and_single_usage(self):
        transport = FakeTransport()
        observer = self.observer(transport)
        cid, rid, job, output, model = self.run_mail(observer)
        self.assertEqual(output["outcome"], "reply_and_wait")
        self.assertEqual(observer.records.get(rid)["export_status"], "pending")
        with self.engine.connect() as conn:
            before = list(conn.execute(sa.select(a.usage_records).where(a.usage_records.c.run_id == rid)).mappings())
        observer.exporter.export_one(rid)
        summary = observer.records.get(rid)
        self.assertEqual(summary["export_status"], "exported")
        self.assertTrue(summary["trace_url"].endswith(summary["trace_id"]))
        value = transport.payloads[0][1]
        nodes = {row["node"] for row in value["observations"]}
        self.assertTrue({"context", "attachment_prepare", "understanding", "model", "tool", "policy", "response", "commit", "outcome"} <= nodes)
        self.assertNotIn(SENTINEL, json.dumps(value))
        generations = [row for row in value["observations"] if row["node"] == "model"]
        self.assertEqual(len(generations), len(model.requests))
        self.assertEqual(sum(row["input_tokens"] for row in generations), self.budget_row(job)["input_tokens"])
        self.assertTrue(all(row["ended_ns"] >= row["started_ns"] for row in generations))
        with self.engine.connect() as conn:
            after = list(conn.execute(sa.select(a.usage_records).where(a.usage_records.c.run_id == rid)).mappings())
            self.assertEqual(before, after)
            correlation = conn.execute(sa.select(a.trace_correlations).where(a.trace_correlations.c.run_id == rid)).mappings().one()
            dependencies = list(conn.execute(sa.select(content_dependencies).where(
                content_dependencies.c.dependent_object_id == correlation["export_object_id"])).mappings())
            self.assertGreaterEqual(len(dependencies), len(generations) * 2)
            self.assertTrue(all(row["customer_id"] == self.conversation(cid)["customer_id"] for row in dependencies))
        self.assertEqual(len(self.outbound(cid)), 1)

    def test_http_failure_retry_does_not_execute_or_double_bill(self):
        transport = FakeTransport((False, True))
        observer = self.observer(transport)
        cid, rid, job, output, model = self.run_mail(observer)
        requests = len(model.requests)
        observer.exporter.export_one(rid)
        self.assertEqual(observer.records.get(rid)["export_status"], "exported")
        self.assertEqual(len(transport.payloads), 2)
        self.assertEqual(transport.payloads[0], transport.payloads[1])
        self.assertEqual(len(model.requests), requests)
        self.assertEqual(self.count(a.usage_records), requests)
        self.assertEqual(len(self.outbound(cid)), 1)

    def test_failed_export_is_degraded_but_business_is_committed(self):
        transport = FakeTransport((False, False, False))
        observer = self.observer(transport)
        cid, rid, job, output, model = self.run_mail(observer)
        observer.exporter.export_one(rid)
        summary = observer.records.get(rid)
        self.assertEqual((summary["export_status"], summary["reason_code"]), ("degraded", "observability_http_failed"))
        self.assertIsNone(summary["trace_url"])
        self.assertEqual(len(transport.payloads), 3)
        self.assertEqual(len(self.outbound(cid)), 1)
        self.assertEqual(self.controls.get(rid)["run"]["status"], "completed")

    def test_failure_exception_content_never_enters_trace(self):
        transport = FakeTransport()
        observer = self.observer(transport)
        cid, rid, job, output, model = self.run_mail(observer, model=ScriptedModel(RuntimeError(SENTINEL)))
        self.assertEqual(output["error_code"], "agent_dependency_error")
        observer.exporter.export_one(rid)
        encoded = json.dumps(transport.payloads)
        self.assertNotIn(SENTINEL, encoded)
        self.assertIn("dependency_error", encoded)
        self.assertEqual(self.count(a.usage_records), 1)
        self.assertEqual(self.outbound(cid), [])

    def test_actual_human_handoff_outcome_keeps_terminal_run_status(self):
        transport = FakeTransport()
        observer = self.observer(transport)
        handoff = {"reason": "no_applicable_evidence", "summary": "Need applicable evidence.",
            "gaps": ["Applicable reference missing."], "draft": "Unsent draft."}
        cid, rid, _, output, model = self.run_mail(observer, model=ScriptedModel(
            understanding, {"calls": [call("request_human_review", handoff)]}))
        self.assertEqual(output["outcome"], "handoff")
        observer.exporter.export_one(rid)
        outcome = next(row for row in transport.payloads[0][1]["observations"] if row["node"] == "outcome")
        self.assertEqual((outcome["status"], outcome["outcome"]), ("handed_off", "handoff"))
        self.assertEqual(self.controls.get(rid)["run"]["status"], outcome["status"])
        self.assertEqual(self.count(a.usage_records), len(model.requests))
        self.assertEqual(self.outbound(cid), [])

    def test_sanitization_failure_drops_before_transport_and_keeps_outcome(self):
        observer = self.observer()
        original = ScriptedModel(understanding, terminal())
        real = original.request
        def malformed(*args, **kwargs):
            with observation("model", body=SENTINEL):
                pass
            return real(*args, **kwargs)
        original.request = malformed
        cid, rid, job, output, _ = self.run_mail(observer, model=original)
        self.assertEqual(output["outcome"], "reply_and_wait")
        self.assertEqual(observer.records.get(rid)["reason_code"], "sanitization_failed")
        observer.exporter.export_one(rid)
        self.assertEqual(observer.exporter.transport.payloads, [])
        self.assertEqual(len(self.outbound(cid)), 1)

    def test_bounded_queue_overflow_and_flush_deadline(self):
        observer = self.observer(langfuse_queue_size=1, langfuse_flush_timeout=0)
        _, first, _, _, _ = self.run_mail(observer)
        cid, second, _, output, _ = self.run_mail(observer)
        self.assertEqual(observer.records.get(first)["export_status"], "pending")
        self.assertEqual(observer.records.get(second)["reason_code"], "observability_queue_full")
        self.assertEqual(observer.exporter.queue.qsize(), 1)
        started = monotonic()
        self.assertFalse(observer.flush(timeout=0.05))
        self.assertLess(monotonic() - started, 0.3)
        self.assertEqual(len(self.outbound(cid)), 1)

    def test_scope_deletion_fences_and_private_api_do_not_rerun(self):
        observer = self.observer()
        cid, rid, job, output, model = self.run_mail(observer)
        outsider = TraceRecords(self.engine, self.store, observer.records.settings, uuid4())
        self.assert_error("run_not_found", lambda: outsider.get(rid))
        with TestClient(create_app(observer.records.settings, engine=self.engine, start_worker=False,
                observability_transport=FakeTransport()), base_url="http://localhost") as client:
            result = client.get(f"/api/v1/observability/runs/{rid}")
            self.assertEqual(result.status_code, 200)
            self.assertNotIn("test-only", result.text)
            self.assertEqual(client.get("/api/v1/observability/runs/not-a-uuid").status_code, 422)
            self.assertEqual(len(model.requests), 4)
        with self.engine.begin() as conn:
            conv = self.row(conversations, conversations.c.id == cid)
            context = conn.execute(sa.select(a.agent_run_contexts.c.context_object_id).where(a.agent_run_contexts.c.run_id == rid)).scalar_one()
            conn.execute(deletion_journal.insert().values(id=uuid4(), **{k: conv[k] for k in SCOPE_KEYS},
                target_object_id=context, generation=1, state="revoked"))
        self.assertEqual(observer.records.get(rid)["export_status"], "revoked")
        observer.exporter.export_one(rid)
        self.assertEqual(observer.exporter.transport.payloads, [])
        self.assertEqual(len(self.outbound(cid)), 1)

    def test_retry_new_trace_has_same_scoped_session_and_parent_run(self):
        observer = self.observer()
        cid, old, job, output, model = self.run_mail(observer, model=ScriptedModel(ServiceError("model_unavailable", 503),
            ServiceError("model_unavailable", 503)))
        from globalmail_agent.domain.conversation import Command
        result = self.controls.control(old, "retry", Command(expected_version=self.conversation(cid)["row_version"]), uuid4().hex)
        current = UUID(result["run_id"])
        next_job = self.claimed()
        AgentRunner(self.engine, self.store, DEFAULT_WORKSPACE_ID, ScriptedModel(understanding, terminal()), None,
            observability=observer).execute(next_job)
        first, second = observer.records.payload(old), observer.records.payload(current)
        self.assertNotEqual(first[0]["trace_id"], second[0]["trace_id"])
        self.assertEqual(first[1]["metadata"]["conversation_id"], second[1]["metadata"]["conversation_id"])
        self.assertEqual(second[1]["metadata"]["parent_run_id"], str(old))
