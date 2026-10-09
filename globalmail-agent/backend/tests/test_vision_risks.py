"""Revoked old evidence cannot suppress a newly validated risk or its later safety gate."""
from uuid import UUID, uuid4
from vision_fixture import VisionFixture, VisionModel, image_output
from globalmail_agent.attachments.corrections import EvidenceService, EvidenceCommand
from globalmail_agent.domain.conversation import AppendMessage, HumanReply


class VisionRiskTests(VisionFixture):
    def test_new_same_kind_risk_after_revoked_image_persists_and_blocks_later_automatic_reply(self):
        def fire(messages):
            value = image_output(messages)
            value["images"][0]["risk_flags"] = ["fire"]
            return value
        cid, images = self.image_mail()
        first, _ = self.execute(VisionModel(fire))
        self.assertEqual(first["outcome"], "handoff")
        old = self.service.detail(cid)["active_risks"][0]["id"]
        state = self.conversation(cid)
        EvidenceService(self.engine, self.store).mutate(UUID(images[0]["attachment_id"]), EvidenceCommand(
            expected_version=state["row_version"], expected_input_revision=state["input_revision"],
            evidence_revision=0), uuid4().hex, revoke=True)
        self.assertEqual(self.service.detail(cid)["active_risks"], [])
        self.human_reply(cid)
        second = self.stage(cid)
        self.service.append(cid, AppendMessage(expected_version=self.conversation(cid)["row_version"], body="",
            attachments=[{"attachment_id": second["attachment_id"]}]), uuid4().hex)
        new_model = VisionModel(fire)
        output, _ = self.execute(new_model)
        self.assertEqual(output["outcome"], "handoff")
        self.assertEqual(len(new_model.requests), 1)
        active = self.service.detail(cid)["active_risks"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["kind"], "fire")
        self.assertNotEqual(active[0]["id"], old)
        self.assertEqual(active[0]["sources"][0]["message_id"], "image:" + second["attachment_id"])
        self.human_reply(cid)
        self.append_mail(cid, "Please check the delivery status.")
        no_model = VisionModel()
        no_model.configured = False
        third, job = self.execute(no_model)
        self.assertEqual(third["outcome"], "handoff")
        self.assertEqual(no_model.requests, [])
        self.assertEqual(self.budget_row(job)["model_requests"], 0)
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.conversation(cid)["processing_owner"], "human_review")
        self.assertEqual(self.service.detail(cid)["active_risks"][0]["id"], active[0]["id"])

    def human_reply(self, cid):
        state = self.conversation(cid)
        self.service.human_reply(cid, HumanReply(expected_version=state["row_version"],
            expected_input_revision=state["input_revision"], body="We are reviewing the reported issue.",
            note="No resolution or correction has been confirmed.", risk_decision="keep_active"), uuid4().hex)
