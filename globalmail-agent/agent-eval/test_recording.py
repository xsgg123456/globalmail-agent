"""Local privacy checks for the export boundary, with no model or database calls."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from recording import safe_arguments, source_scope


class ExportPrivacyTests(unittest.TestCase):
    def test_new_revision_tool_does_not_export_quotes_by_default(self):
        value = safe_arguments("revise_understanding", {"sources": [{"quote": "PRIVATE_SOURCE_QUOTE"}],
            "change_reason": "PRIVATE_MODEL_DESCRIPTION"})
        self.assertNotIn("PRIVATE_", json.dumps(value))
        self.assertEqual(set(value), {"arguments_sha256"})

    def test_terminal_and_handoff_export_no_original_free_text(self):
        draft = safe_arguments("create_reply_draft", {"body": "PRIVATE_DRAFT_BODY", "language": "en",
            "claims": [{"kind": "customer_fact", "text": "PRIVATE_CLAIM_TEXT", "source_ids": ["m1"]}],
            "citation_ids": [], "waiting_for": "customer_information"})
        handoff = safe_arguments("request_human_review", {"reason": "no_evidence",
            "summary": "PRIVATE_HANDOFF_SUMMARY", "gaps": ["PRIVATE_GAP"], "draft": "PRIVATE_UNSENT_BODY"})
        exported = json.dumps({"draft": draft, "handoff": handoff})
        self.assertNotIn("PRIVATE_", exported)
        self.assertEqual(draft["claims"][0]["source_ids"], ["m1"])
        self.assertEqual(handoff["gap_count"], 1)

    def test_source_scope_keeps_ids_and_hashes_without_mail_or_note_body(self):
        payload = {"mode": "simulation", "as_of": "2026-10-08T02:00:00Z", "trigger_message_id": "m1",
            "case_revision": 1, "case_facts": [], "messages": [{"message_id": "m1", "seq": 1,
                "sender": "customer", "body": "PRIVATE_MAIL_BODY"}],
            "human_notes": [{"message_id": "n1", "body": "PRIVATE_HUMAN_NOTE"}]}
        requests = [{"messages": [{"role": "system", "content": "PRIVATE_SYSTEM_PROMPT"},
            {"role": "user", "content": json.dumps(payload)}], "schema": {}, "tools": None,
            "timeout": 30, "seconds": 1, "response": {"request_id": "request1", "usage": None}}]
        exported = source_scope(requests)
        self.assertNotIn("PRIVATE_", json.dumps(exported))
        self.assertEqual(exported["messages"][0]["message_id"], "m1")
        self.assertEqual(exported["human_notes"][0]["message_id"], "n1")
        self.assertIsNone(exported["model_requests"][0]["usage"])

    def test_budget_rejection_captures_full_unsent_request_before_model(self):
        from globalmail_agent.agent.graph import AgentGraph
        from globalmail_agent.application.conversation_lock import ServiceError
        from recording import capture_graph_errors
        messages = [{"role": "user", "content": "COMPLETE_ORIGINAL_DATA"}]
        tools = [{"function": {"name": "request_human_review"}}]
        class RejectBudget:
            def reserve(self, *args):
                raise ServiceError("input_budget_exceeded")
        graph = object.__new__(AgentGraph)
        graph.model, graph.budget = SimpleNamespace(model="qwen3.7-plus"), RejectBudget()
        with TemporaryDirectory() as temporary, patch.object(AgentGraph, "invoke",
                lambda g: g.request(messages, "decision", tools=tools)):
            directory = Path(temporary)
            restore = capture_graph_errors(directory)
            try:
                with self.assertRaises(ServiceError):
                    graph.invoke()
            finally:
                restore()
            captured = json.loads((directory / "blocked-next-request.json").read_text(encoding="utf-8"))
            self.assertEqual(captured["messages"], messages)
            self.assertEqual(captured["tools"], tools)
            self.assertFalse(captured["new_model_http_call"])

    def test_sdk_capture_is_pass_through_and_omits_credential_fields(self):
        from recording import instrument
        class CaptureOnlyProvider:
            def __init__(self):
                self.received = None
                self.client = SimpleNamespace(with_options=lambda **kwargs: SimpleNamespace(
                    chat=SimpleNamespace(completions=SimpleNamespace(create=self.send))))
            def send(self, **payload):
                self.received = payload
                return {"request_id": "local-test", "content": "{}", "calls": [], "finish_reason": "stop", "usage": None}
            def request(self, messages, *, schema=None, tools=None, timeout=30):
                return self.client.with_options(timeout=timeout).chat.completions.create(messages=messages,
                    tool_choice={"type": "function", "function": {"name": "request_human_review"}},
                    temperature=0.7, api_key="PRIVATE_TEST_CREDENTIAL", base_url="PRIVATE_TEST_URL")
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            provider = CaptureOnlyProvider()
            traffic = instrument(provider, directory)
            provider.request([{"role": "user", "content": "full input"}], tools=[])
            captured = json.loads((directory / "provider-payload-01.json").read_text(encoding="utf-8"))
            self.assertNotIn("PRIVATE_", json.dumps(captured))
            self.assertEqual(captured["tool_choice"], provider.received["tool_choice"])
            self.assertEqual(captured["messages"], provider.received["messages"])
            self.assertEqual(traffic[0]["actual_provider_tool_choice"], captured["tool_choice"])


if __name__ == "__main__":
    unittest.main()
