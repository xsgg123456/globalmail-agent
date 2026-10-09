"""Explicit console events are not Agent tools."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

EventName = Literal["create_execution", "processing", "succeeded", "failed", "unknown", "reconciled_not_executed",
    "label_created", "shipped", "delivered", "return_in_transit", "received", "inspected", "inventory_changed"]


class SimulationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: UUID
    expected_version: int = Field(ge=1, strict=True)
    operation_id: str = Field(min_length=1, max_length=160)
    expected_operation_version: int = Field(ge=1, strict=True)
    event: EventName
    execution_id: str | None = Field(default=None, min_length=1, max_length=160)
    receipt_ref: str | None = Field(default=None, min_length=1, max_length=240)
    tracking_number: str | None = Field(default=None, min_length=1, max_length=160)
    carrier: str | None = Field(default=None, min_length=1, max_length=80)
    reason: str | None = Field(default=None, min_length=1, max_length=500)
    quantity: int | None = Field(default=None, ge=1, strict=True)
    confirmed_not_executed: bool = Field(default=False, strict=True)
    on_hand: int | None = Field(default=None, ge=0, strict=True)
    return_address: str | None = Field(default=None, min_length=1, max_length=1000)
    packing_instructions: str | None = Field(default=None, min_length=1, max_length=2000)
    postage_responsibility: Literal["customer", "merchant"] | None = None
    prepaid_label_ref: str | None = Field(default=None, min_length=1, max_length=240)


class ExecutionLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: UUID
    expected_version: int = Field(ge=1, strict=True)
    operation_id: str = Field(min_length=1, max_length=160)
    expected_operation_version: int = Field(ge=1, strict=True)
    execution_id: str = Field(min_length=1, max_length=160)


UNDETERMINED = {"accepted", "processing", "unknown", "failed"}


def allowed_events(operation, executions=(), shipments=(), returns=()):
    if operation.get("status") in {"cancelled", "succeeded"}:
        return ["delivered"] if any(s.get("status") == "shipped" for s in shipments) else []
    active = [e for e in executions if not e.get("confirmed_not_executed")]
    events = []
    if not active:
        events.append("create_execution")
    elif active[-1].get("status") in UNDETERMINED:
        status = active[-1]["status"]
        if status == "accepted":
            events.append("processing")
        if status in {"accepted", "processing", "unknown"}:
            events += ["succeeded", "failed", "unknown"]
        if status in {"failed", "unknown"}:
            events.append("reconciled_not_executed")
    kind = operation.get("kind")
    dispatched = any(s.get("status") in {"shipped", "delivered"} for s in shipments)
    warehouse_done = any(r.get("received") and r.get("inspection") == "passed"
        and r.get("quantity") == operation.get("quantity") for r in returns)
    if (kind in {"replacement", "spare_part"} and not dispatched) or (kind == "return" and not warehouse_done):
        events = [event for event in events if event != "succeeded"]
    if dispatched:
        events = [event for event in events if event != "reconciled_not_executed"]
    if kind in {"replacement", "spare_part"}:
        events.append("inventory_changed")
        if active and active[-1].get("status") in {"accepted", "processing", "unknown"}:
            if not shipments:
                events.append("label_created")
            elif shipments[-1].get("status") == "label_created":
                events.append("shipped")
            elif shipments[-1].get("status") == "shipped":
                events.append("delivered")
    if kind in {"return", "replacement", "refund"}:
        if not returns and (kind != "replacement" or not active):
            events.append("label_created")
        elif returns and returns[-1].get("status") == "authorized":
            events += ["return_in_transit", "received"]
        elif returns and returns[-1].get("status") == "in_transit":
            events.append("received")
        elif returns and returns[-1].get("received") and returns[-1].get("inspection") is None:
            events.append("inspected")
    return list(dict.fromkeys(events))
