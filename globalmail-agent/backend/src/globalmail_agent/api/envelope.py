from fastapi.responses import JSONResponse


def response(request_id: str, data=None, *, status: int = 200, msg: str = "ok"):
    return JSONResponse(
        {"code": status, "msg": msg, "data": data,
         "request_id": request_id}, status_code=status,
        headers={"X-Request-ID": request_id, "Cache-Control": "no-store"},
    )

