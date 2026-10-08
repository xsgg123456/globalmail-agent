"""Explicit build, publish, rollback and withdrawal commands with CAS/idempotency."""
from uuid import UUID
from fastapi import APIRouter, Request, Header
from globalmail_agent.api.conversations import safe_call
from globalmail_agent.knowledge.index_commands import BuildCommand, ReleaseCommand, RollbackCommand, WithdrawCommand
from globalmail_agent.knowledge.index_profiles import CHUNKERS
from globalmail_agent.knowledge.builds import BuildService
from globalmail_agent.knowledge.releases import ReleaseService


def knowledge_releases_router(database, store, gateway):
    router = APIRouter(prefix="/api/v1")
    builds = BuildService(database, store, gateway)
    releases = ReleaseService(database, store)

    @router.get("/knowledge/index-profiles")
    def profiles(request: Request):
        return safe_call(request, lambda: {"items": gateway.profiles() if gateway else [], "chunkers": CHUNKERS})

    @router.post("/knowledge/versions/{identity}/build")
    def build(request: Request, identity: UUID, command: BuildCommand, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: builds.enqueue_build(identity, command, idempotency_key), 202)

    @router.get("/knowledge/versions/{identity}/index")
    def index(request: Request, identity: UUID):
        return safe_call(request, lambda: builds.status(identity))

    @router.get("/knowledge/releases")
    def listing(request: Request):
        return safe_call(request, releases.listing)

    @router.post("/knowledge/releases")
    def publish(request: Request, command: ReleaseCommand, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: releases.publish(command, idempotency_key))

    @router.post("/knowledge/releases/{identity}/rollback")
    def rollback(request: Request, identity: UUID, command: RollbackCommand, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: releases.rollback(identity, command, idempotency_key))

    @router.post("/knowledge/documents/{identity}/withdraw")
    def withdraw(request: Request, identity: UUID, command: WithdrawCommand, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: releases.withdraw(identity, command, idempotency_key))

    return router
