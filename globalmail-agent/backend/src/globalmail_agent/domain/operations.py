"""Agent commands contain a proposal and visible source, never execution authority."""
from pydantic import BaseModel, ConfigDict, Field
from globalmail_agent.domain.policy import EligibilityRequest


class SelectionRef(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    message_id: str = Field(min_length=1, max_length=160)
    quote: str = Field(min_length=1, max_length=1000)


class CheckOperation(EligibilityRequest):
    issue_id: str = Field(min_length=1, max_length=160)
    selection_ref: SelectionRef
    address_ref: SelectionRef | None = None
    address_version: int | None = Field(default=None, ge=1)
    affected_unit_ids: list[str] | None = Field(default=None, min_length=1, max_length=100)


class CreateOperation(CheckOperation):
    decision_id: str = Field(min_length=1, max_length=160)


class CancelOperation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation_id: str = Field(min_length=1, max_length=160)
    expected_operation_version: int = Field(ge=1)
    selection_ref: SelectionRef


OCCUPYING = {"accepted", "waiting_condition", "awaiting_execution", "processing", "unknown", "failed", "succeeded"}
COMPENSATING = {"refund", "replacement", "spare_part"}


def plan(command):
    fields = command.model_dump(mode="json", exclude={"decision_id", "selection_ref", "address_ref", "issue_id"})
    if fields.get("affected_unit_ids"):
        fields["affected_unit_ids"] = sorted(fields["affected_unit_ids"])
    return fields
