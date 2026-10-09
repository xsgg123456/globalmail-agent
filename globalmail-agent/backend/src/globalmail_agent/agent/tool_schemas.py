"""Scoped reads, internal applications and terminal proposals are model-callable."""
from typing import Literal
from pydantic import Field
from globalmail_agent.agent.understanding import StrictModel, Fact, Intent, SourceRef
from globalmail_agent.domain.operations import CheckOperation, CreateOperation, CancelOperation


class Empty(StrictModel):
    pass


class Order(StrictModel):
    display_order_number: str = Field(min_length=1, max_length=100)


class Line(StrictModel):
    order_line_id: str = Field(min_length=1, max_length=160)


class Operation(StrictModel):
    operation_id: str = Field(min_length=1, max_length=160)


class Availability(Line):
    item_id: str = Field(min_length=1, max_length=160)


class Search(Line):
    query: str = Field(min_length=1, max_length=1500)
    types: list[Literal["manual_pdf", "troubleshooting_md", "case_md", "policy_json"]] = Field(max_length=4)


class StateUpdate(StrictModel):
    facts: list[Fact] = Field(max_length=20)
    expected_case_revision: int = Field(ge=0)


class UnderstandingRevision(StrictModel):
    intents: list[Intent] = Field(max_length=12)
    missing_information: list[str] = Field(max_length=20)
    sources: list[SourceRef] = Field(min_length=1, max_length=16)
    change_reason: str = Field(min_length=1, max_length=1000)
    expected_case_revision: int = Field(ge=0)


class Claim(StrictModel):
    kind: Literal["order_fact", "product_step", "customer_fact", "proposal", "clarification", "visual_observation"]
    text: str = Field(min_length=1, max_length=2000,
        description="Complete email paragraph, never source quotes.")
    source_ids: list[str] = Field(max_length=10,
        description="Source IDs only, never quotes.")


class BusinessWait(StrictModel):
    condition_type: Literal["manual_execution", "refund_receipt", "warehouse_receipt", "inventory", "shipment_changed"]
    operation_id: str | None = Field(default=None, min_length=1, max_length=160)
    issue_id: str | None = Field(default=None, min_length=1, max_length=160)
    observed_business_version: int = Field(ge=0)


class ReplyParts(StrictModel):
    language: str = Field(min_length=2, max_length=32)
    claims: list[Claim] = Field(max_length=30,
        description="Entire email in order, including courtesy. Server joins texts with two newlines; do not repeat a body field.")
    citation_ids: list[str] = Field(max_length=10)
    waiting_for: Literal["customer_information", "customer_feedback", "manual_execution", "refund_receipt",
        "warehouse_receipt", "inventory", "shipment_changed"]
    waiting_operation_id: str | None = Field(default=None, max_length=160)
    waiting_issue_id: str | None = Field(default=None, max_length=160)
    observed_business_version: int = Field(default=0, ge=0)
    additional_waits: list[BusinessWait] = Field(default_factory=list, max_length=12)


class Draft(ReplyParts):
    body: str = Field(max_length=8000)


class Handoff(StrictModel):
    reason: Literal["no_applicable_evidence", "conflicting_evidence", "failed_steps", "cannot_decide", "safety_risk", "no_progress"]
    summary: str = Field(min_length=1, max_length=3000)
    gaps: list[str] = Field(min_length=1, max_length=20)
    draft: str = Field(max_length=8000)


TOOLS = {"get_case_context": Empty, "get_order_snapshot": Order, "get_shipment_status": Line,
    "get_after_sales_context": Line, "get_item_availability": Availability, "get_operation_status": Operation,
    "search_reference": Search, "update_case_state": StateUpdate, "revise_understanding": UnderstandingRevision,
    "create_reply_draft": Draft, "request_human_review": Handoff}
TOOLS.update(check_after_sales_eligibility=CheckOperation,
    create_after_sales_operation=CreateOperation, cancel_after_sales_operation=CancelOperation)


def compact_schema(value):
    # Gateway validates the full Pydantic bounds; omit only redundant schema annotations/bounds from prompts.
    if isinstance(value, dict):
        return {key: compact_schema(item) for key, item in value.items() if key not in {
            "title", "default", "minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems"}}
    if isinstance(value, list):
        return [compact_schema(item) for item in value]
    return value


def schemas(allowed=None, *, multiple_waits=True):
    reply_schema = ReplyParts.model_json_schema()
    if not multiple_waits:
        reply_schema["properties"].pop("additional_waits", None)
        reply_schema["properties"].pop("waiting_issue_id", None)
        reply_schema.get("$defs", {}).pop("BusinessWait", None)
    return [{"type": "function", "function": {"name": name, "parameters": compact_schema(
        reply_schema if name == "create_reply_draft" else model.model_json_schema()),
        **({"description": "Revise candidates using exact visible-message/human-note or successful current-run command:<id> quotes; never authorize or clear risks."}
           if name == "revise_understanding" else {})}}
        for name, model in TOOLS.items() if allowed is None or name in allowed]
