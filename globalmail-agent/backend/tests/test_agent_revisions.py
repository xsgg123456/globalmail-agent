"""Real scoped PG revisions with frozen protocol outputs; no semantic-quality claims."""
import json
import unittest
from uuid import uuid4
from unittest.mock import patch
import sqlalchemy as sa
from agent_fixture import AgentFixture, ScriptedModel, understanding, terminal, call, draft
from globalmail_agent.adapters import agent_schema as a, business_schema as b
from globalmail_agent.agent.context import load_context
from globalmail_agent.agent.understanding import Understanding, validate_sources
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.application.commit_outcome import commit_outcome
from globalmail_agent.application.run_records import RunRecords
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.domain.conversation import Command, HumanReply
from globalmail_agent.observability.local_records import save_understanding


def intent(source, business_type="troubleshooting", **changes):
    return {"business_type": business_type, "order_number": None, "target_item": None,
        "condition": None, "requested_solution": None, "consent": "none", "sources": [source], **changes}


def revision(source, case_revision, **changes):
    return {"intents": [intent(source)], "missing_information": ["symptom"], "sources": [source],
        "change_reason": "Frozen test corrects the candidate using the cited receipt.",
        "expected_case_revision": case_revision, **changes}


class AgentRevisionTests(AgentFixture):
    def initial(self, context, job, **changes):
        value = understanding([], **changes)
        save_understanding(self.engine, self.store, context.workspace_id, job, value)
        return value

    def test_tool_revision_updates_next_decision_validation_and_ui_keeps_initial(self):
        cid, _ = self.scene()
        number = BusinessQueries(self.engine).detail(cid)["data"]["orders"][0]["display_order_number"]
        self.append_mail(cid, "My order is " + number + ". I need help with this lamp.")
        def initial(messages):
            payload = json.loads(messages[-1]["content"])
            source = {"message_id": payload["messages"][-1]["message_id"], "quote": number}
            return understanding([], intents=[intent(source, "shipment", order_number=number)],
                order_candidates=[{"value": number, "sources": [source]}])
        def revise(messages):
            observed = json.loads(next(message["content"] for message in reversed(messages) if message["role"] == "tool"))
            self.assertEqual(observed["status"], "ok")
            source = {"message_id": observed["command_source_id"], "quote": number}
            state = json.loads(messages[1]["content"])
            return {"calls": [call("revise_understanding", revision(source, state["context"]["case_revision"],
                intents=[intent(source, order_number=number)]), "correct-intent")]}
        def next_decision(messages):
            current = json.loads(messages[1]["content"])["understanding"]
            self.assertEqual(current["intents"][0]["business_type"], "troubleshooting")
            return terminal("What symptom does the lamp show?")
        def review(messages):
            state = json.loads(next(message["content"] for message in messages if message["role"] == "user"))
            self.assertEqual(state["understanding"]["intents"][0]["business_type"], "troubleshooting")
            return {"supported": True, "language_correct": True, "unsupported_claims": [],
                "reason": "Frozen protocol approval; semantic accuracy not evaluated."}
        model = ScriptedModel(initial, {"calls": [call("get_order_snapshot", {
            "display_order_number": number}, "verified-order")]}, revise, next_decision, reviews=[review])
        output, job = self.execute(model)
        self.assertEqual(output.get("outcome"), "reply_and_wait", output)
        self.assertEqual(len(model.requests), 5)
        self.assertEqual(len(self.outbound(cid)), 1)
        detail = RunRecords(self.engine, self.store).get(job["run_id"])["understanding"]
        self.assertEqual(detail["intents"][0]["business_type"], "troubleshooting")
        self.assertEqual(detail["initial_understanding"]["intents"][0]["business_type"], "shipment")
        self.assertEqual(len(detail["revisions"]), 1)
        self.assertTrue(detail["revisions"][0]["source_ids"][0].startswith("command:"))
        for table in (b.operations, b.executions):
            self.assertEqual(self.count(table), 0)

    def test_revision_cas_duplicate_receipt_and_risk_authority_invariants(self):
        cid, _ = self.create_mail("The plug sparked. Please check the lamp.")
        job, context, _, gateway = self.components()
        source = {"message_id": context.payload["messages"][0]["message_id"], "quote": "The plug sparked."}
        initial = self.initial(context, job, risk_flags=[{"kind": "electric_shock", "sources": [source]}])
        before = self.conversation(cid)
        args = revision(source, before["case_revision"])
        _, stale = gateway.call(call("revise_understanding", {**args, "expected_case_revision": before["case_revision"] + 1}))
        self.assertEqual(stale["reason_code"], "stale_case_revision")
        request = call("revise_understanding", args, "stable-revision")
        first = gateway.call(request)
        calls = self.budget_row(job)["tool_calls"]
        self.assertEqual(gateway.call(request), first)
        self.assertEqual(self.budget_row(job)["tool_calls"], calls)
        self.assertEqual(self.count(a.understanding_revisions), 1)
        self.assertEqual(first[1]["data"]["understanding"]["risk_flags"], initial["risk_flags"])
        current = self.conversation(cid)
        self.assertEqual(current["case_revision"], before["case_revision"] + 1)
        for field in ("input_revision", "authority_epoch", "processing_owner", "auto_run_gate"):
            self.assertEqual(current[field], before[field])
        self.assert_error("tool_command_conflict", lambda: gateway.call(call("revise_understanding",
            {**args, "change_reason": "different payload"}, "stable-revision")))

    def test_revision_effect_and_receipt_survive_lost_gateway_response(self):
        cid, _ = self.create_mail("Please check the lamp.")
        job, context, _, gateway = self.components()
        self.initial(context, job)
        source = {"message_id": context.payload["messages"][0]["message_id"], "quote": "lamp"}
        request = call("revise_understanding", revision(source, self.conversation(cid)["case_revision"]), "lost-revision")
        execute = gateway.execute
        def lost_response(name, args, command_id):
            execute(name, args, command_id)
            raise ConnectionError("Frozen lost response after guarded revision commit")
        with patch.object(gateway, "execute", side_effect=lost_response):
            with self.assertRaises(ConnectionError):
                gateway.call(request)
        self.assertEqual(self.count(a.understanding_revisions), 1)
        before = self.conversation(cid)["case_revision"]
        _, replay = gateway.call(request)
        self.assertEqual(replay["status"], "ok")
        self.assertEqual(self.conversation(cid)["case_revision"], before)
        self.assertEqual(self.count(a.understanding_revisions), 1)
        self.assertEqual(self.budget_row(job)["tool_calls"], 1)

    def test_revision_rejects_scope_risk_ledger_and_unverified_tool_sources(self):
        cid, _ = self.create_mail("Please check the lamp.")
        job, context, _, gateway = self.components()
        self.initial(context, job)
        source = {"message_id": context.payload["messages"][0]["message_id"], "quote": "lamp"}
        args = revision(source, self.conversation(cid)["case_revision"])
        for field in ("customer_id", "mode", "as_of", "release_id", "risk_flags", "facts", "processing_owner"):
            self.assert_error("tool_parameters_invalid", lambda: gateway.call(call("revise_understanding", {**args, field: []})))
        identity, _ = gateway.call(call("get_case_context", {}))
        denied_id, _ = gateway.call(call("get_order_snapshot", {"display_order_number": "UNKNOWN"}))
        for invalid in ({"message_id": "command:" + str(identity), "quote": "lamp"},
                {"message_id": "command:" + str(denied_id), "quote": "denied"},
                {"message_id": "command:" + str(uuid4()), "quote": "lamp"},
                {**source, "quote": "invented quote"}):
            self.assert_error("understanding_source_invalid", lambda: gateway.call(call("revise_understanding",
                revision(invalid, args["expected_case_revision"]))))
        self.assertEqual(self.count(a.understanding_revisions), 0)

    def test_successful_tool_quote_is_exact_and_cannot_promote_customer_choice(self):
        cid, _ = self.scene()
        number = BusinessQueries(self.engine).detail(cid)["data"]["orders"][0]["display_order_number"]
        self.append_mail(cid, "My order is " + number)
        job, context, _, gateway = self.components()
        self.initial(context, job)
        identity, found = gateway.call(call("get_order_snapshot", {"display_order_number": number}))
        self.assertEqual(found["status"], "ok")
        source = {"message_id": "command:" + str(identity), "quote": number}
        args = revision(source, self.conversation(cid)["case_revision"])
        self.assert_error("understanding_source_invalid", lambda: gateway.call(call("revise_understanding",
            revision({**source, "quote": number + " not in receipt"}, args["expected_case_revision"]))))
        self.assert_error("candidate_choice_requires_message", lambda: gateway.call(call("revise_understanding",
            {**args, "intents": [intent(source, "refund", consent="explicit")]})))
        _, revised = gateway.call(call("revise_understanding", args))
        self.assertEqual(revised["status"], "ok")
        self.assertTrue(revised["data"]["candidate_only"])
        rebuilt = load_context(self.engine, self.store, context.workspace_id, job, rebuild=True)
        self.assertEqual(rebuilt.payload["reused_understanding"]["intents"][0]["sources"], [source])

    def test_cross_run_tool_receipt_cannot_revise_new_run(self):
        cid, _ = self.scene()
        number = BusinessQueries(self.engine).detail(cid)["data"]["orders"][0]["display_order_number"]
        self.append_mail(cid, "My order is " + number)
        job, context, _, gateway = self.components()
        old_id, _ = gateway.call(call("get_order_snapshot", {"display_order_number": number}))
        self.approve_fixture_draft(context, job, draft())
        commit_outcome(self.engine, self.store, context, job, understanding([]), {"kind": "reply", "data": draft()})
        self.append_mail(cid, "Please check again.")
        job, context, _, gateway = self.components()
        self.initial(context, job)
        source = {"message_id": "command:" + str(old_id), "quote": number}
        self.assert_error("understanding_source_invalid", lambda: gateway.call(call("revise_understanding",
            revision(source, self.conversation(cid)["case_revision"]))))
        self.assertEqual(self.count(a.understanding_revisions), 0)

    def test_visible_human_note_revises_candidate_after_new_customer_input(self):
        cid, _ = self.create_mail()
        handoff = {"calls": [call("request_human_review", {"reason": "cannot_decide", "summary": "Need inspection",
            "gaps": ["Need human assessment"], "draft": ""})]}
        output, _ = self.execute(ScriptedModel(understanding, handoff))
        self.assertEqual(output.get("outcome"), "handoff", output)
        state = self.conversation(cid)
        self.service.human_reply(cid, HumanReply(expected_version=state["row_version"],
            expected_input_revision=state["input_revision"], body="We reviewed the issue.",
            note="Customer selected replacement; it remains an unexecuted proposal."), uuid4().hex)
        self.append_mail(cid, "Any next step?")
        job, context, _, gateway = self.components()
        self.initial(context, job)
        note = context.payload["human_notes"][0]
        source = {"message_id": note["message_id"], "quote": note["body"]}
        _, revised = gateway.call(call("revise_understanding", revision(source, self.conversation(cid)["case_revision"],
            intents=[intent(source, "replacement", consent="explicit", requested_solution="replacement")])) )
        self.assertEqual(revised["status"], "ok")
        self.assertEqual(self.count(b.operations), 0)
        self.assertEqual(self.count(b.executions), 0)

    def test_stopped_or_superseded_run_cannot_apply_late_revision(self):
        for action in ("stop", "new_input"):
            cid, rid = self.create_mail(email=action + "@example.test")
            job, context, _, gateway = self.components()
            self.initial(context, job)
            source = {"message_id": context.payload["messages"][0]["message_id"], "quote": "lamp"}
            args = revision(source, self.conversation(cid)["case_revision"])
            if action == "stop":
                self.controls.control(rid, "stop", Command(expected_version=self.conversation(cid)["row_version"]), uuid4().hex)
            else:
                self.append_mail(cid, "New input replaces the running revision.")
            with self.assertRaises(ServiceError) as refused:
                gateway.call(call("revise_understanding", args))
            self.assertIn(refused.exception.code, {"lease_expired", "run_superseded"})
            self.assertEqual(self.count(a.understanding_revisions), 0)


class ResolvedRiskSourceTests(unittest.TestCase):
    def test_old_resolved_sources_are_ignored_but_new_or_mixed_sources_are_kept(self):
        old = {"message_id": "old", "quote": "spark"}
        new = {"message_id": "new", "quote": "spark"}
        payload = {"messages": [{"message_id": ref["message_id"], "body": ref["quote"], "sender": "customer"}
            for ref in (old, new)], "human_notes": [], "risk_history": [{"kind": "electric_shock",
                "status": "corrected_by_human", "sources": [old]}]}
        for sources, expected in (([old], []), ([new], [new]), ([old, new], [old, new])):
            value = Understanding.model_validate(understanding([], risk_flags=[{"kind": "electric_shock", "sources": sources}]))
            checked = validate_sources(value, payload)
            self.assertEqual(checked["risk_flags"][0]["sources"] if checked["risk_flags"] else [], expected)
        payload["risk_history"][0]["status"] = "active"
        self.assertTrue(validate_sources(Understanding.model_validate(understanding([],
            risk_flags=[{"kind": "electric_shock", "sources": [old]}])), payload)["risk_flags"])
