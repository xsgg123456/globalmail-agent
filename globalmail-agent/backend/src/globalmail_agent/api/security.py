from urllib.parse import urlsplit
from uuid import uuid4

from starlette.datastructures import Headers

from globalmail_agent.api.envelope import response


class LocalAccessMiddleware:
    """Reject rebinding and foreign browser origins before routing, including GET."""

    def __init__(self, app, allowed_origins: tuple[str, ...]):
        self.app, self.allowed_origins = app, allowed_origins

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        headers = Headers(scope=scope)
        hosts = headers.getlist("host")
        origins = headers.getlist("origin")
        try:
            host = urlsplit("//" + hosts[0]) if len(hosts) == 1 else None
            valid_host = bool(host and host.hostname in {"127.0.0.1", "localhost"}
                              and not host.username and not host.password and not host.path
                              and not host.query and not host.fragment)
            if host:
                _ = host.port
        except ValueError:
            valid_host = False
        status, message = 0, ""
        if not valid_host:
            status, message = 400, "invalid_host"
        elif origins and (len(origins) != 1 or origins[0] not in self.allowed_origins):
            status, message = 403, "origin_forbidden"
        elif scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
            if not origins:
                status, message = 403, "origin_required"
            elif headers.get("content-type", "").split(";")[0].strip() != (
                    "application/octet-stream" if scope["path"] == "/api/v1/knowledge/uploads" else "application/json"):
                status, message = 415, "json_required"
        if status:
            return await response(request_id, status=status, msg=message)(scope, receive, send)
        async def safe_send(message):
            if message["type"] == "http.response.start" and origins:
                message["headers"].extend([
                    (b"access-control-allow-origin", origins[0].encode("ascii")),
                    (b"vary", b"Origin"),
                ])
            await send(message)

        if scope["method"] == "OPTIONS":
            result = response(request_id)
            result.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS, POST, PATCH"
            result.headers["Access-Control-Allow-Headers"] = "Content-Type, Idempotency-Key, Last-Event-ID"
            return await result(scope, receive, safe_send)
        try:
            await self.app(scope, receive, safe_send)
        except Exception:
            # Swallow raw exception before Uvicorn can log a credential-bearing traceback.
            await response(request_id, status=500, msg="internal_error")(scope, receive, safe_send)

