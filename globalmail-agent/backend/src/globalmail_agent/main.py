from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from globalmail_agent.adapters.object_store import ObjectStore
from globalmail_agent.api.envelope import response
from globalmail_agent.api.security import LocalAccessMiddleware
from globalmail_agent.adapters.database import make_engine
from globalmail_agent.settings import Settings
from globalmail_agent.api.system import system_router
from globalmail_agent.api.conversations import conversation_router
from globalmail_agent.api.events import events_router
from globalmail_agent.api.runs import runs_router
from globalmail_agent.api.business import business_router
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
from globalmail_agent.worker.runner import ProtocolRunner
from globalmail_agent.worker.knowledge_runner import KnowledgeRunner
from globalmail_agent.api.knowledge_documents import knowledge_router
from globalmail_agent.api.knowledge_releases import knowledge_releases_router
from globalmail_agent.api.knowledge_search import knowledge_search_router
from globalmail_agent.knowledge.embedding import EmbeddingGateway


def create_app(settings: Settings | None = None, *, engine=None, start_worker=True,
               embedding_gateway=None) -> FastAPI:
    settings = settings or Settings.from_env()
    database = engine if engine is not None else make_engine(settings)
    store = ObjectStore(settings.object_root, database)
    gateway = embedding_gateway if embedding_gateway is not None else EmbeddingGateway(settings)

    @asynccontextmanager
    async def lifespan(app):
        runner = knowledge = None
        if start_worker and database is not None:
            runner = ProtocolRunner(database, DEFAULT_WORKSPACE_ID)
            runner.start()
            knowledge = KnowledgeRunner(database, store, DEFAULT_WORKSPACE_ID, gateway)
            knowledge.start()
        try:
            yield
        finally:
            if runner is not None:
                runner.close()
            if knowledge is not None:
                knowledge.close()
            if database is not None:
                database.dispose()

    app = FastAPI(title="GlobalMail Agent", version="0.1.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(LocalAccessMiddleware, allowed_origins=settings.allowed_origins)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error):
        return response(request.state.request_id, status=422, msg="validation_error")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error):
        return response(request.state.request_id, status=error.status_code,
                        msg={404: "not_found", 405: "method_not_allowed"}.get(error.status_code, "request_error"))

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error):
        return response(getattr(request.state, "request_id", "unavailable"),
                        status=500, msg="internal_error")

    app.include_router(system_router(settings, database, store))
    app.include_router(conversation_router(database, store))
    app.include_router(events_router(database))
    app.include_router(runs_router(database))
    app.include_router(business_router(database, store))
    app.include_router(knowledge_router(database, store))
    app.include_router(knowledge_releases_router(database, store, gateway))
    app.include_router(knowledge_search_router(database, store, gateway))

    return app


app = create_app()


