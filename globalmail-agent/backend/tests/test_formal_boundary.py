"""Independent Stage 1 probes. Synthetic fixtures, isolated PG schemas only."""
import json
from uuid import uuid4
from pathlib import Path
from datetime import datetime, timedelta, timezone
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from alembic import command as migrations
from alembic.config import Config
from agent_fixture import AgentFixture, ScriptedModel, call, understanding
from test_human_assistance import handoff
from globalmail_agent.domain.conversation import HumanReply, ReviewDraft, Close, Command
from globalmail_agent.application.run_records import RunRecords
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.application.branch_facts import BranchFactsService
from globalmail_agent.application.conversation_advice import ConversationAdvice
from globalmail_agent.domain.business_events import BranchFact
from vision_fixture import VisionFixture, VisionModel, image_output, handoff as image_handoff
from globalmail_agent.attachments.corrections import EvidenceService, EvidenceCommand
from globalmail_agent.adapters.body_store import BodyWriter
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID


class FormalBoundaryProbes(AgentFixture):
    def test_model_and_advice_records_preserve_all_scope_guards(self):
        cid, rid = self.commercial()
        self.assert_error("run_not_found", lambda: RunRecords(self.engine, self.store, uuid4()).get(rid))
        self.assert_error("conversation_not_found", lambda: ConversationAdvice(self.engine, self.store, uuid4()).get(cid))
        other, _ = self.create_mail(email="other-review@example.test")
        foreign = self.service.detail(other)["messages"][0]["body_object_id"]
        from globalmail_agent.adapters import agent_schema as records
        with self.engine.connect() as conn:
            usage = conn.execute(sa.select(records.usage_records).where(records.usage_records.c.run_id == rid)).mappings().first()
            artifact = conn.execute(sa.select(records.reply_artifacts).where(records.reply_artifacts.c.run_id == rid)).mappings().one()
        for table, identity, field in ((records.usage_records, usage["id"], "request_object_id"),
                (records.usage_records, usage["id"], "response_object_id"),
                (records.reply_artifacts, artifact["id"], "advice_object_id")):
            with self.assertRaises(IntegrityError), self.engine.begin() as conn:
                conn.execute(table.update().where(table.c.id == identity).values(**{field: foreign}))
        print("PROBE scopes", {"foreign_workspace_read": "404", "foreign_object_updates": "3 FK rejections"})

    def test_closed_conversation_cannot_retry_an_old_stopped_run(self):
        cid, rid = self.create_mail()
        self.controls.control(rid, "stop", Command(expected_version=self.conversation(cid)["row_version"]), uuid4().hex)
        self.service.close(cid, Close(expected_version=self.conversation(cid)["row_version"]), uuid4().hex)
        self.assert_error("retry_not_allowed", lambda: self.controls.control(rid, "retry",
            Command(expected_version=self.conversation(cid)["row_version"]), uuid4().hex))
        self.assertEqual(self.outbound(cid), [])

    def test_closed_incoming_preserves_resolved_issue_states(self):
        cid, _ = self.commercial()
        self.service.close(cid, Close(expected_version=self.conversation(cid)["row_version"]), uuid4().hex)
        self.append_mail(cid, "Another message after closure")
        detail = self.service.detail(cid)
        states = {r["issue_key"]: r["status"] for r in detail["issues"]}
        print("PROBE closed_issues", {"lifecycle": detail["conversation"]["lifecycle"], "issue_states": states})
        self.assertTrue(all(state == "resolved" for state in states.values()), states)

    def commercial(self):
        cid, rid = self.create_mail("I want a refund for my order.")
        def source(m):
            payload = json.loads(m[1]["content"])
            row = payload["messages"][-1]
            return understanding(payload["messages"], intents=[{
                "business_type": "refund", "order_number": None, "target_item": None,
                "condition": None, "requested_solution": None, "consent": "none",
                "sources": [{"message_id": row["message_id"], "quote": row["body"]}]}])
        result, _ = self.execute(ScriptedModel(source, handoff()))
        self.assertEqual(result.get("outcome"), "handoff", result)
        return cid, rid

    def test_agent_suggestions_do_not_become_staff_drafts(self):
        cid, _ = self.commercial()
        review = self.service.detail(cid)["review"]
        self.assertIsNone(review["draft_object_id"])
        self.assertEqual(review["staff_draft"], "")
        self.append_mail(cid, "Please update me.")
        review = self.service.detail(cid)["review"]
        self.service.save_review(review["id"], ReviewDraft(expected_version=review["version"],
            expected_input_revision=self.conversation(cid)["input_revision"], draft="Staff personal wording",
            note="Staff verified note"), uuid4().hex)
        self.execute(ScriptedModel(understanding([]), handoff()))
        review = self.service.detail(cid)["review"]
        self.assertEqual(review["staff_draft"], "Staff personal wording")
        self.assertEqual(review["staff_note"], "Staff verified note")
        print("PROBE staff_draft", {"draft": review["staff_draft"], "note": review["staff_note"]})

    def test_late_model_response_after_staff_reply_is_diagnostic_only(self):
        cid, _ = self.commercial()
        incoming = self.append_mail(cid, "Any progress?")
        def late(m):
            conv = self.conversation(cid)
            self.service.human_reply(cid, HumanReply(expected_version=conv["row_version"],
                expected_input_revision=conv["input_revision"], body="Staff reply before model finishes."), uuid4().hex)
            return understanding([])
        result, _ = self.execute(ScriptedModel(late))
        run = RunRecords(self.engine, self.store).get(__import__("uuid").UUID(incoming["run_id"]))
        self.assertEqual(run["run"]["status"], "superseded")
        self.assertEqual(len(run["model_calls"]), 1)
        self.assertEqual(run["model_calls"][0]["status"], "completed")
        self.assertIsNotNone(run["model_calls"][0]["response"])
        self.assertEqual(run["artifacts"], [])
        self.assertEqual(self.outbound(cid), [])
        print("PROBE late_response", {"result": result, "run_status": run["run"]["status"],
            "call_status": run["model_calls"][0]["status"], "artifacts": len(run["artifacts"])})

    def test_revised_commercial_intent_changes_authority_before_next_decision(self):
        cid, rid = self.create_mail("I want a refund for this order.")
        def revision(m):
            payload = json.loads(m[1]["content"])
            context = payload["context"]
            row = context["messages"][-1]
            refs = [{"message_id": row["message_id"], "quote": row["body"]}]
            return {"calls": [call("revise_understanding", {
                "expected_case_revision": context["case_revision"], "sources": refs,
                "change_reason": "The explicit refund request was missed initially.",
                "missing_information": ["order_number"], "intents": [{
                    "business_type": "refund", "order_number": None, "target_item": None,
                    "condition": None, "requested_solution": None, "consent": "none", "sources": refs}]})]}
        model = ScriptedModel(understanding([]), revision, handoff())
        result, _ = self.execute(model)
        self.assertEqual(result.get("outcome"), "handoff", result)
        conv = self.conversation(cid)
        self.assertTrue(conv["persistent_human"])
        run = RunRecords(self.engine, self.store).get(rid)
        self.assertEqual(run["run"]["execution_mode"], "human_assist")
        self.assertNotIn("create_reply_draft", [t["function"]["name"] for t in model.requests[-1]["tools"]])
        self.assertEqual(self.outbound(cid), [])
        print("PROBE revised_intent", {"persistent_human": conv["persistent_human"],
            "execution_mode": run["run"]["execution_mode"], "outcome": result["outcome"]})

    def test_queried_inventory_change_expires_refund_advice(self):
        cid, _ = self.scene("BASE-OUTON-01")
        self.append_mail(cid, "I want a refund for my order. Please check stock before recommending an alternative.")
        data = BusinessQueries(self.engine).detail(cid)["data"]
        order = data["orders"][0]
        line = order["lines"][0]
        def refund(m):
            payload = json.loads(m[1]["content"])
            row = payload["messages"][-1]
            # Intent is explicitly stated by the newly stored customer message.
            return understanding(payload["messages"], intents=[{
                "business_type": "refund", "order_number": None,
                "target_item": None, "condition": None,
                "requested_solution": None, "consent": "none",
                "sources": [{"message_id": row["message_id"], "quote": row["body"]}]}],
                order_candidates=[{"value": order["display_order_number"], "sources": [{
                    "message_id": payload["messages"][0]["message_id"],
                    "quote": order["display_order_number"]}]}])
        model = ScriptedModel(refund,
            {"calls": [call("get_item_availability", {"order_line_id": line["line_id"], "item_id": line["sku"]})]},
            {"calls": [call("request_human_review", {"reason": "commercial_after_sales",
                "summary": "Review the existing stock before deciding the refund.",
                "gaps": ["Staff must verify latest inventory evidence"],
                "recommendations": ["Check stock"], "draft": "We are checking available alternatives."})]})
        result, _ = self.execute(model)
        self.assertEqual(result.get("outcome"), "handoff", result)
        before = self.conversation(cid)
        self.assertFalse(ConversationAdvice(self.engine, self.store).get(cid)["stale"])
        with self.engine.connect() as conn:
            branch = conn.execute(sa.select(b.simulation_branches).where(
                b.simulation_branches.c.id == before["branch_id"])).mappings().one()
        command = BranchFact(conversation_id=cid, expected_version=before["row_version"],
            source_event_id=uuid4().hex, order_line_id=line["line_id"], event="inventory_snapshot",
            expected_business_version=0, business_version=1, staff_id="isolated-reviewer",
            receipt_ref="isolated-stock-proof", reason="Warehouse confirmed new stock",
            item_id=line["sku"], region_spec="US", hardware_revision=line["hardware_revision"],
            snapshot_at=branch["clock"], on_hand=7)
        changed = BranchFactsService(self.engine, self.store).event(before["branch_id"], command, uuid4().hex)
        after = self.conversation(cid)
        advice = ConversationAdvice(self.engine, self.store).get(cid)
        print("PROBE inventory_change", {"event_status": changed["status"],
            "before_revision": before["input_revision"], "after_revision": after["input_revision"],
            "advice_stale": advice["stale"], "new_on_hand": 7})
        self.assertTrue(advice["stale"], "Changed queried inventory still leaves advice usable")


class FormalImageRecordProbes(VisionFixture):
    def test_actual_image_call_records_use_refs_and_revoke_with_the_original(self):
        cid, images = self.image_mail()
        result, job = self.execute(VisionModel(image_output, image_handoff()))
        self.assertNotIn("error_code", result, result)
        records = RunRecords(self.engine, self.store).get(job["run_id"])["model_calls"]
        serialized = json.dumps(records, default=str)
        self.assertNotIn("base64,", serialized)
        self.assertEqual(records[0]["request"]["image_transport"], "authorized_reference")
        self.assertEqual(len(records[0]["request"]["image_views"]), 1)
        conv = self.conversation(cid)
        EvidenceService(self.engine, self.store).mutate(__import__("uuid").UUID(images[0]["attachment_id"]),
            EvidenceCommand(expected_version=conv["row_version"], expected_input_revision=conv["input_revision"],
                evidence_revision=0), uuid4().hex, revoke=True)
        self.assert_error("image_content_revoked", lambda: RunRecords(self.engine, self.store).get(job["run_id"]))
        print("PROBE image_records", {"image_transport": "authorized_reference", "revoked_read": "image_content_revoked"})
