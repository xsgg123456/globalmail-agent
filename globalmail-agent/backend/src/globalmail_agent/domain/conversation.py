"""Validated public commands; callers cannot choose workspace or execution scope."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)


class Body(Command):
    body: str = Field(min_length=1, max_length=20000)
    subject: str = Field(default="", max_length=500)

    @field_validator("body")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("body_required")
        return value


class CreateConversation(Body):
    sender_email: str = Field(max_length=320)

    @field_validator("sender_email")
    @classmethod
    def email(cls, value):
        value = value.strip()
        if value.count("@") != 1:
            raise ValueError("invalid_email")
        local, domain = value.split("@")
        if not local or not domain or "." not in domain or any(c.isspace() for c in value):
            raise ValueError("invalid_email")
        return local + "@" + domain.lower()


class AppendMessage(Body):
    source_message_id: str | None = Field(default=None, min_length=1, max_length=160)


class Takeover(Command):
    reason: str = Field(default="人工主动接管", min_length=1, max_length=500)


class ReviewDraft(Command):
    expected_input_revision: int = Field(ge=0)
    draft: str = Field(default="", max_length=20000)
    note: str = Field(default="", max_length=5000)


class HumanReply(Body):
    expected_input_revision: int = Field(ge=0)
    note: str = Field(default="", max_length=5000)
    risk_decision: Literal["keep_active", "resolved_by_human", "corrected_by_human"] = "keep_active"


class Close(Command):
    note: str = Field(default="", max_length=5000)


class ImportMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_message_id: str = Field(min_length=1, max_length=160)
    sender: Literal["customer", "historical_staff"]
    sent_at: datetime
    subject: str = Field(default="", max_length=500)
    body: str = Field(min_length=1, max_length=20000)

    @field_validator("sent_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timezone_required")
        return value

    @field_validator("body")
    @classmethod
    def nonempty(cls, value):
        return Body.nonempty(value)


class ImportCase(Command):
    source_ref: str = Field(min_length=1, max_length=240)
    source_conversation_id: str = Field(min_length=1, max_length=160)
    split: Literal["dev", "eval_holdout"]
    group_id: str | None = Field(default=None, max_length=160)
    sender_key: str | None = Field(default=None, min_length=1, max_length=320)
    identity_verified: Literal[False] = False
    identity_source_ref: str | None = Field(default=None, max_length=240)
    messages: list[ImportMessage] = Field(min_length=1, max_length=500)
