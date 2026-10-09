"""Independent actual PG/Graph/HTTP risk replacement and human resolution probe."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from uuid import UUID, uuid4

root = Path(__file__).resolve().parents[1]
backend = root / "globalmail-agent/backend"
sys.path[:0] = [str(backend / "src"), str(backend / "tests"), str(root / "globalmail-agent/agent-eval")]
from bootstrap import isolated_database_environment
isolated_database_environment()
import sqlalchemy as sa
from vision_fixture import VisionFixture, VisionModel, image_output
from agent_fixture import understanding, terminal
from globalmail_agent.adapters.agent_schema import agent_risks
from globalmail_agent.adapters.conversation_schema import conversations
from globalmail_agent.adapters.body_store import read_bytes
from globalmail_agent.attachments.corrections import EvidenceService, EvidenceCommand
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.domain.conversation import AppendMessage, HumanReply

def snapshot():
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ("src", "tests", "migrations") for p in (backend / folder).rglob("*")
        if p.is_file() and p.suffix in (".py", ".md")}

class RiskProbe(VisionFixture):
    def reply(self, cid, decision="keep_active", note="Human review remains open."):
        state = self.conversation(cid)
        return self.service.human_reply(cid, HumanReply(expected_version=state["row_version"],
            expected_input_revision=state["input_revision"], body="Human reply.",
            risk_decision=decision, note=note), uuid4().hex)

    def test_replacement_and_explicit_human_resolution_keep_old_source_unreadable(self):
        def fire(messages):
            value = image_output(messages)
            value["images"][0]["risk_flags"] = ["fire"]
            return value
        cid, images = self.image_mail()
        first, _ = self.execute(VisionModel(fire))
        self.assertEqual(first["outcome"], "handoff")
        old_id = self.service.detail(cid)["active_risks"][0]["id"]
        state = self.conversation(cid)
        EvidenceService(self.engine, self.store).mutate(UUID(images[0]["attachment_id"]), EvidenceCommand(
            expected_version=state["row_version"], expected_input_revision=state["input_revision"],
            evidence_revision=0), uuid4().hex, revoke=True)
        self.assertEqual(self.service.detail(cid)["active_risks"], [])
        self.reply(cid)
        b = self.stage(cid)
        self.service.append(cid, AppendMessage(expected_version=self.conversation(cid)["row_version"], body="",
            attachments=[{"attachment_id": b["attachment_id"]}]), uuid4().hex)
        second_model = VisionModel(fire)
        second, _ = self.execute(second_model)
        self.assertEqual(second["outcome"], "handoff")
        active = self.service.detail(cid)["active_risks"]
        self.assertEqual(len(active), 1)
        self.assertNotEqual(active[0]["id"], old_id)
        self.assertEqual(active[0]["sources"][0]["message_id"], "image:" + b["attachment_id"])
        self.reply(cid)
        self.assertIsNone(self.leases.claim("review6-human-wait"))
        self.append_mail(cid, "Routine delivery question.")
        blocked = VisionModel()
        blocked.configured = False
        third, job = self.execute(blocked)
        self.assertEqual(third["outcome"], "handoff")
        self.assertEqual(self.budget_row(job)["model_requests"], 0)
        self.assertEqual(blocked.requests, [])
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.conversation(cid)["processing_owner"], "human_review")
        # Human resolution is explicit, evidenced and still waits for new input.
        self.reply(cid, "resolved_by_human", "Human inspected and isolated the affected device; no active danger remains.")
        self.assertEqual(self.service.detail(cid)["active_risks"], [])
        self.assertIsNone(self.leases.claim("review6-resolution-does-not-run"))
        old_preview = self.client.get(f"/api/v1/attachments/{images[0]['attachment_id']}/preview",
            params={"conversation_id": str(cid), "thumbnail": "false"})
        self.assertEqual(old_preview.status_code, 410)
        with self.engine.connect() as conn:
            old_row = conn.execute(sa.select(agent_risks).where(agent_risks.c.id == UUID(old_id))).mappings().one()
            conv = conn.execute(sa.select(conversations).where(conversations.c.id == cid)).mappings().one()
            with self.assertRaises(ServiceError) as revoked:
                read_bytes(conn, self.store, conv, old_row["body_object_id"])
            self.assertEqual(revoked.exception.status, 410)
            self.assertEqual(revoked.exception.code, "image_content_revoked")
        self.append_mail(cid, "Please continue the delivery question after the human inspection.")
        normal_model = VisionModel(image_output, terminal())
        fourth, _ = self.execute(normal_model)
        self.assertEqual(fourth["outcome"], "reply_and_wait")
        self.assertEqual(len(normal_model.requests), 3)
        self.assertEqual(len(self.outbound(cid)), 1)
        self.assertEqual(self.service.detail(cid)["active_risks"], [])
        print("REVIEW6_RISK " + json.dumps({"new_risk_id_distinct": True,
            "new_source_b": True, "keep_active_models": 0, "keep_active_outbound": 0,
            "keep_active_owner": "human_review", "resolution_auto_run": False,
            "after_new_input_models": 3, "after_new_input_outbound": 1,
            "old_preview": old_preview.status_code, "old_risk_bytes": 410}))

before = snapshot()
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RiskProbe))
after = snapshot()
summary = {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
    "skipped": len(result.skipped), "source_changed": before != after, "before": before, "after": after}
(root / "tmp/phase8-review6-risk-probe.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("REVIEW6_PROBE_RESULT " + json.dumps({k: v for k, v in summary.items() if k not in ("before", "after")}))
raise SystemExit(not result.wasSuccessful() or bool(result.skipped) or before != after)
