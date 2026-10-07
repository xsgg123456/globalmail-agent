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


def create_app(settings: Settings | None = None, *, engine=None) -> FastAPI:
    settings = settings or Settings.from_env()
    database = engine if engine is not None else make_engine(settings)
    store = ObjectStore(settings.object_root, database)

    @asynccontextmanager
    async def lifespan(app):
        yield
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

    return app


app = create_app()


