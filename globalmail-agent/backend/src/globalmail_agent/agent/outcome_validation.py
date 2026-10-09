"""Coverage is deterministic; natural-language grounding also receives a budgeted review."""
from pydantic import Field
from globalmail_agent.agent.understanding import StrictModel
from globalmail_agent.agent.review_audit import RequestCheck, SourceCheck
from globalmail_agent.agent.tool_schemas import Draft
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.base import canonical, sha


class OutcomeReview(StrictModel):
    source_checks: list[SourceCheck] = Field(max_length=30)
    request_checks: list[RequestCheck]
    reason: str = Field(max_length=1500)
    unsupported_claims: list[str] = Field(max_length=20)
    supported: bool
    language_correct: bool


def draft_hash(value):
    return sha(canonical(Draft.model_validate(value).model_dump(mode="json")))


def check_coverage(draft):
    value = draft if isinstance(draft, Draft) else Draft.model_validate(draft)
    if not value.body.strip():
        if not value.waiting_operation_id or value.waiting_for in {"customer_information", "customer_feedback"}:
            raise ServiceError("reply_body_required", 422)
        return
    covered = [False] * len(value.body)
    for claim in value.claims:
        start = value.body.find(claim.text)
        if start < 0:
            raise ServiceError("reply_source_invalid", 422)
        while start >= 0:
            covered[start:start + len(claim.text)] = [True] * len(claim.text)
            start = value.body.find(claim.text, start + len(claim.text))
    if any(not covered[i] and not ch.isspace() for i, ch in enumerate(value.body)):
        raise ServiceError("reply_claims_incomplete", 422)
