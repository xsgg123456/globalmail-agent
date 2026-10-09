"""Frozen image outputs prove integration, never model recognition quality."""
import json
from uuid import UUID, uuid4
from agent_fixture import AgentSupport, ScriptedModel, understanding, call
from test_attachment_intake import AttachmentFixture
from globalmail_agent.domain.conversation import CreateConversation


class VisionModel(ScriptedModel):
    def __init__(self, *steps, **options):
        super().__init__(*steps, **options)
        self.image_requests = []

    def request(self, messages, *, schema=None, tools=None, timeout=30, image_views=(), image_loader=None):
        if image_views:
            self.image_requests.append({"refs": image_views, "bytes": [image_loader(r) for r in image_views]})
        return super().request(messages, schema=schema, tools=tools, timeout=timeout)


def image_output(messages, **changes):
    payload = json.loads(next(m["content"] for m in messages if m["role"] == "user"))
    images = [{"attachment_id": r["attachment_id"], "status": "understood", "coverage": "整图",
        "quality": "工程固定样本", "field_candidates": [], "observations": ["visible mark"],
        "hypotheses": [], "uncertainties": ["原因待核对"], "risk_flags": []} for r in payload["image_views"]]
    return understanding(messages, images=images, **changes)


def handoff():
    return {"calls": [call("request_human_review", {"reason": "cannot_decide", "summary": "人工核对图片",
        "gaps": ["原因待核对"], "draft": ""})]}


class VisionFixture(AgentSupport, AttachmentFixture):
    def image_mail(self, number=1):
        email = "vision-" + uuid4().hex + "@example.test"
        rows = [self.stage(email=email) for _ in range(number)]
        result = self.service.create(CreateConversation(expected_version=0, sender_email=email,
            body="", attachments=[{"attachment_id": r["attachment_id"]} for r in rows]), uuid4().hex)
        return UUID(result["conversation_id"]), rows
