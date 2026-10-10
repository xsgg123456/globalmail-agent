"""Explicit impact, confirmation, status and retry; reset remains script/API only."""
from typing import Literal
from uuid import UUID
import sqlalchemy as sa
from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field
from globalmail_agent.api.conversations import safe_call
from globalmail_agent.application.lifecycle import LifecycleService
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID


class DeletionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)
    action: Literal["delete", "reset"] = "delete"


def lifecycle_router(engine, store, settings):
    router = APIRouter(prefix="/api/v1/lifecycle")
    service = LifecycleService(engine, store, settings)

    @router.get("/requests")
    def listing(request: Request):
        def action():
            from globalmail_agent.adapters.lifecycle_schema import deletion_requests
            with engine.connect() as conn:
                ids = conn.execute(sa.select(deletion_requests.c.id).where(
                    deletion_requests.c.workspace_id == DEFAULT_WORKSPACE_ID).order_by(
                    deletion_requests.c.created_at.desc()).limit(50)).scalars().all()
            return {"items": [service.get(identity) for identity in ids]}
        return safe_call(request, action)

    @router.get("/{kind}/{identity}/impact")
    def impact(request: Request, kind: Literal["conversation", "document", "attachment"], identity: UUID):
        return safe_call(request, lambda: service.preview(kind, identity))

    @router.post("/{kind}/{identity}")
    def create(request: Request, kind: Literal["conversation", "document", "attachment"],
               identity: UUID, command: DeletionCommand):
        return safe_call(request, lambda: service.request(kind, identity,
            command.expected_version, action=command.action), 202)

    @router.get("/requests/{identity}")
    def status(request: Request, identity: UUID):
        return safe_call(request, lambda: service.get(identity))

    @router.post("/requests/{identity}/retry")
    def retry(request: Request, identity: UUID):
        return safe_call(request, lambda: service.process(identity), 202)

    return router
