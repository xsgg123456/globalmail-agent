"""A restored snapshot is never exposed before replay and verification finish."""
from globalmail_agent.api.envelope import response
from globalmail_agent.application.restore import assert_restore_open
from sqlalchemy.exc import SQLAlchemyError


class RestoreGateMiddleware:
    def __init__(self, app, engine, store):
        self.app, self.engine, self.store = app, engine, store

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] != "/api/v1/health/live":
            try:
                assert_restore_open(self.store.root)
                from globalmail_agent.application.journal_gate import assert_journal_current
                assert_journal_current(self.engine, self.store)
            except SQLAlchemyError:
                # Diagnostics remain available, but a failed journal check never reports ready.
                if scope["path"] == "/api/v1/health/ready":
                    from globalmail_agent.adapters.database import database_status
                    database, schema = database_status(self.engine)
                    return await response(scope.get("state", {}).get("request_id", "restore"), {
                        "status": "degraded", "database": database, "schema": schema,
                        "object_store": "ready" if self.store.ready() else "unavailable",
                        "journal": "unavailable",
                    }, status=503, msg="dependencies_unavailable")(scope, receive, send)
                return await response(scope.get("state", {}).get("request_id", "restore"),
                    status=503, msg="restore_closed")(scope, receive, send)
            except RuntimeError:
                return await response(scope.get("state", {}).get("request_id", "restore"),
                    status=503, msg="restore_closed")(scope, receive, send)
        await self.app(scope, receive, send)
