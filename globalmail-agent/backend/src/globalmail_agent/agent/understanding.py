"""Schema checks preserve source-backed candidates, not model-authorized business facts."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from globalmail_agent.application.conversation_lock import ServiceError


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRef(StrictModel):
    message_id: str = Field(min_length=1, max_length=100)
    quote: str = Field(min_length=1, max_length=1000)


class Intent(StrictModel):
    business_type: Literal["product_inquiry", "troubleshooting", "shipment", "refund", "return", "replacement", "parts", "other"] = Field(
        description="Request category: parcel tracking/non-arrival is shipment; product malfunction is troubleshooting.")
    order_number: str | None = Field(description="Non-null needs this intent.sources exact quote containing this number.")
    target_item: str | None
    condition: str | None = Field(description="Condition on this requested future outcome; preserve even when not requested now.")
    requested_solution: str | None
    consent: Literal["none", "conditional", "explicit", "declined"]
    sources: list[SourceRef] = Field(min_length=1, max_length=8,
        description="Exact current/historical request quotes AND this intent's non-null order_number quote.")


class Candidate(StrictModel):
    value: str = Field(min_length=1, max_length=100)
    sources: list[SourceRef] = Field(min_length=1, max_length=8)


class Fact(StrictModel):
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=2000)
    kind: Literal["customer_report", "historical_claim", "human_decision", "model_inference"]
    sources: list[SourceRef] = Field(min_length=1, max_length=8)


class Risk(StrictModel):
    kind: Literal["fire", "electric_shock", "injury", "battery_danger", "other_safety"]
    sources: list[SourceRef] = Field(min_length=1, max_length=8)


class Understanding(StrictModel):
    language: str = Field(min_length=2, max_length=32)
    intents: list[Intent] = Field(max_length=12,
        description="Separate every active request and conditional future preference; retain its conditions and refusal of current execution.")
    order_candidates: list[Candidate] = Field(max_length=12)
    facts: list[Fact] = Field(max_length=30)
    risk_flags: list[Risk] = Field(max_length=8)
    missing_information: list[str] = Field(max_length=20)


def validate_sources(value, payload, *, tool_sources=None):
    sources = {row["message_id"]: row for row in [*payload["messages"], *payload["human_notes"]]}
    sources.update(tool_sources or {})
    for item in [*value.intents, *value.order_candidates, *value.facts, *value.risk_flags]:
        for ref in item.sources:
            if ref.message_id not in sources or ref.quote not in sources[ref.message_id]["body"]:
                raise ServiceError("understanding_source_invalid", 422)
    for item in value.order_candidates:
        if not any(item.value in ref.quote for ref in item.sources):
            raise ServiceError("order_candidate_not_in_source", 422)
    for intent in value.intents:
        if intent.order_number and not any(intent.order_number in ref.quote for ref in intent.sources):
            raise ServiceError("order_candidate_not_in_source", 422)
    for fact in value.facts:
        if fact.kind == "human_decision" and not all(sources[ref.message_id]["sender"] in
                {"simulated_human", "human_note"} for ref in fact.sources):
            raise ServiceError("human_source_invalid", 422)
    result = value.model_dump(mode="json")
    resolved = [row for row in payload.get("risk_history", [])
        if row["status"] in {"resolved_by_human", "corrected_by_human"}]
    result["risk_flags"] = [risk for risk in result["risk_flags"] if not any(
        row["kind"] == risk["kind"] and all(ref["message_id"] in
            {source["message_id"] for source in row["sources"]} for ref in risk["sources"])
        for row in resolved)]
    return result
