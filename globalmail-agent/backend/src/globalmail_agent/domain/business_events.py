"""Manual continuous facts have explicit source/version authority, never model tool authority."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from globalmail_agent.domain.operations import SelectionRef


class BranchFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: UUID
    expected_version: int = Field(ge=1, strict=True)
    source_event_id: str = Field(min_length=1, max_length=100)
    order_line_id: str = Field(min_length=1, max_length=160)
    event: Literal["inventory_snapshot", "address_confirmation", "original_shipment", "inspection_correction",
        "return_documents", "service_note"]
    expected_business_version: int = Field(ge=0, strict=True)
    business_version: int = Field(ge=1, strict=True)
    staff_id: str = Field(min_length=1, max_length=160)
    receipt_ref: str = Field(min_length=1, max_length=240)
    reason: str = Field(min_length=1, max_length=1000)
    resource_id: str | None = Field(default=None, max_length=160)
    expected_resource_version: int | None = Field(default=None, ge=1, strict=True)
    selection_ref: SelectionRef | None = None
    item_id: str | None = Field(default=None, max_length=160)
    region_spec: str | None = Field(default=None, max_length=40)
    hardware_revision: str | None = Field(default=None, max_length=80)
    snapshot_at: datetime | None = None
    on_hand: int | None = Field(default=None, ge=0, strict=True)
    confirmed: bool | None = Field(default=None, strict=True)
    status: Literal["label_created", "shipped", "delivered"] | None = None
    carrier: str | None = Field(default=None, max_length=80)
    tracking_number: str | None = Field(default=None, max_length=160)
    quantity: int | None = Field(default=None, ge=1, strict=True)
    inspection: Literal["passed", "failed", "disputed"] | None = None
    return_address: str | None = Field(default=None, max_length=1000)
    packing_instructions: str | None = Field(default=None, max_length=2000)
    postage_responsibility: Literal["customer", "merchant"] | None = None
    prepaid_label_ref: str | None = Field(default=None, max_length=240)

    @field_validator("staff_id", "receipt_ref", "reason", "source_event_id", "order_line_id",
        "resource_id", "item_id", "region_spec", "hardware_revision", "carrier", "tracking_number",
        "return_address", "packing_instructions", "prepaid_label_ref")
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("source_required")
        return value

    @field_validator("snapshot_at")
    @classmethod
    def timezone(cls, value):
        if value is not None and value.utcoffset() is None:
            raise ValueError("timezone_required")
        return value
