"""Read-only search preview, with durable references for every exposed body."""
from uuid import UUID
from fastapi import APIRouter, Request
from globalmail_agent.api.conversations import safe_call
from globalmail_agent.knowledge.index_commands import SearchCommand
from globalmail_agent.knowledge.retrieval import KnowledgeSearch
from globalmail_agent.knowledge.references import ReferenceService


def knowledge_search_router(database, store, gateway):
    router = APIRouter(prefix="/api/v1")
    search = KnowledgeSearch(database, store, gateway)
    references = ReferenceService(database, store)

    @router.post("/knowledge/search")
    def preview(request: Request, command: SearchCommand):
        return safe_call(request, lambda: search.search(command))

    @router.get("/knowledge/references/{identity}")
    def reference(request: Request, identity: UUID):
        return safe_call(request, lambda: references.get(identity))

    return router
