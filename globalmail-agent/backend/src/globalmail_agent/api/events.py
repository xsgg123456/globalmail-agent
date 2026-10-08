import asyncio
import json
import time
from uuid import UUID
from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from globalmail_agent.adapters.conversation_schema import conversations
from globalmail_agent.application.event_store import read_events
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
from globalmail_agent.api.envelope import response


def sse_event(row):
    value = {key: str(row[key]) for key in ("conversation_id", "workspace_id", "branch_id")}
    value.update(mode="interactive_simulation" if row["mode"] == "simulation" else row["mode"],
                 seq=row["seq"], kind=row["kind"], payload=row["payload"])
    return f"id: {row['seq']}\nevent: update\ndata: {json.dumps(value, ensure_ascii=False)}\n\n"


def events_router(database):
    router = APIRouter(prefix="/api/v1")

    @router.get("/conversations/{conversation_id}/events")
    async def events(request: Request, conversation_id: UUID, after_seq: int = Query(0, ge=0),
                     last_event_id: str | None = Header(default=None)):
        if database is None:
            return response(request.state.request_id, status=503, msg="database_unavailable")
        try:
            if last_event_id is not None:
                previous = int(last_event_id)
                if previous < 0:
                    raise ValueError()
                after_seq = max(after_seq, previous)
            if after_seq < 0:
                raise ValueError()
        except ValueError:
            return response(request.state.request_id, status=422, msg="invalid_event_cursor")
        def snapshot():
            with database.connect() as conn:
                row = conn.execute(select(conversations).where(conversations.c.id == conversation_id,
                    conversations.c.workspace_id == DEFAULT_WORKSPACE_ID,
                    conversations.c.lifecycle.not_in(["deleting", "deleted"]))).mappings().first()
                return dict(row) if row else None
        try:
            current = await asyncio.to_thread(snapshot)
        except SQLAlchemyError:
            return response(request.state.request_id, status=503, msg="database_unavailable")
        if current is None:
            return response(request.state.request_id, status=404, msg="conversation_not_found")
        if after_seq > current["next_seq"]:
            return response(request.state.request_id, status=409, msg="event_cursor_invalidated")

        async def stream():
            cursor, heartbeat = after_seq, time.monotonic()
            yield ": connected\n\n"
            while not await request.is_disconnected():
                def batch():
                    with database.connect() as conn:
                        return read_events(conn, conversation_id, DEFAULT_WORKSPACE_ID, cursor)
                try:
                    rows = await asyncio.to_thread(batch)
                except SQLAlchemyError:
                    yield "event: unavailable\ndata: {\"reason_code\":\"database_unavailable\"}\n\n"
                    return
                for row in rows:
                    yield sse_event(row)
                    cursor = row["seq"]
                if time.monotonic() - heartbeat >= 15:
                    yield ": heartbeat\n\n"
                    heartbeat = time.monotonic()
                await asyncio.sleep(0.25)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={
            "Cache-Control": "no-store", "X-Accel-Buffering": "no", "X-Request-ID": request.state.request_id})

    return router
