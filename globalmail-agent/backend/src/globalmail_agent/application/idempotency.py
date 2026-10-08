from uuid import uuid4
from sqlalchemy import insert, select, text
from globalmail_agent.adapters.conversation_schema import request_receipts
from globalmail_agent.adapters.import_loader import payload_hash
from globalmail_agent.application.conversation_lock import ServiceError


def prior(conn, workspace, key, operation, payload):
    if not key or len(key) > 160 or not key.strip():
        raise ServiceError("idempotency_key_required", 422)
    # Advisory lock serializes even the first insertion, before a receipt row exists.
    conn.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                 {"key": str(workspace) + ":" + key})
    digest = payload_hash(payload)
    row = conn.execute(select(request_receipts).where(request_receipts.c.workspace_id == workspace,
        request_receipts.c.request_key == key)).mappings().first()
    if row and (row["payload_hash"] != digest or row["operation"] != operation):
        raise ServiceError("idempotency_conflict")
    return (row["result"] if row else None), digest


def remember(conn, workspace, key, operation, digest, result):
    conn.execute(insert(request_receipts).values(id=uuid4(), workspace_id=workspace,
        request_key=key, operation=operation, payload_hash=digest, result=result))
