from fastapi import APIRouter, Request

from globalmail_agent.api.envelope import response
from globalmail_agent.adapters.database import database_status


def system_router(settings, database, store):
    router = APIRouter(prefix="/api/v1")

    @router.get("/health/live")
    def live(request: Request):
        return response(request.state.request_id, {"status": "ok"})

    @router.get("/health/ready")
    def ready(request: Request):
        db_status, schema_status = database_status(database)
        object_status = "ready" if store.ready() else "unavailable"
        healthy = db_status == schema_status == object_status == "ready"
        return response(request.state.request_id, {
            "status": "ready" if healthy else "degraded", "database": db_status,
            "schema": schema_status, "object_store": object_status,
        }, status=200 if healthy else 503, msg="ok" if healthy else "dependencies_unavailable")

    @router.get("/runtime-config")
    def runtime_config(request: Request):
        return response(request.state.request_id, {
            "mode": "local_single_user", "phase": 6,
            "features": {"conversations": True, "business_queries": True,
                         "knowledge": True, "agent": False},
            "model_configured": bool(settings.model_api_key.get_secret_value()
                                     and settings.model_name and settings.model_base_url),
        })

    return router
