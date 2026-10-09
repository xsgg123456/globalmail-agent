"""Bind one immutable ordered attachment/CID manifest on the message transaction."""
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, update, func
from globalmail_agent.adapters.attachment_schema import message_attachments
from globalmail_agent.adapters.conversation_schema import messages
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.attachments.queries import scoped_where, attachment_metadata, list_message_attachments
from globalmail_agent.attachments.validation import MAX_IMAGES, MAX_TOTAL_BYTES


def references(attachments):
    if len(attachments) > MAX_IMAGES:
        raise ServiceError("attachment_count_limit", 422)
    normalized, ids, cids = [], set(), set()
    for item in attachments:
        value = item.model_dump() if hasattr(item, "model_dump") else item
        if not isinstance(value, dict) or set(value) - {"attachment_id", "cid"}:
            raise ServiceError("invalid_attachment_reference", 422)
        try:
            aid = UUID(str(value["attachment_id"]))
        except (KeyError, ValueError, TypeError):
            raise ServiceError("invalid_attachment_reference", 422) from None
        cid = value.get("cid")
        if cid is not None and (not isinstance(cid, str) or not cid.strip() or len(cid) > 240
                or any(ord(c) < 33 for c in cid) or any(c in cid for c in "<>\\\"")):
            raise ServiceError("invalid_attachment_cid", 422)
        if aid in ids or cid is not None and cid in cids:
            raise ServiceError("duplicate_attachment_reference", 422)
        ids.add(aid)
        if cid is not None:
            cids.add(cid)
        normalized.append({"attachment_id": aid, "cid": cid})
    return normalized


def assert_same_manifest(conn, conversation, message, attachments):
    expected = references(attachments)
    rows = conn.execute(select(message_attachments).where(
        message_attachments.c.conversation_id == conversation["id"],
        message_attachments.c.message_id == message["id"], *scoped_where(message_attachments, conversation))
        .where(message_attachments.c.source_object_id.is_not(None))
        .order_by(message_attachments.c.position)).mappings().all()
    actual = [{"attachment_id": row["id"], "cid": row["cid"]} for row in rows]
    if actual != expected:
        raise ServiceError("source_message_conflict")


def bind_attachments(conn, conversation, message, attachments):
    refs = references(attachments)
    if not refs:
        return []
    valid_message = conn.execute(select(messages.c.id).where(messages.c.id == message["id"],
        messages.c.conversation_id == conversation["id"], messages.c.sender == "customer",
        *scoped_where(messages, conversation))).first()
    if valid_message is None:
        raise ServiceError("attachment_message_scope", 409)
    rows = conn.execute(select(message_attachments).where(
        message_attachments.c.id.in_([r["attachment_id"] for r in refs]),
        message_attachments.c.conversation_id == conversation["id"],
        *scoped_where(message_attachments, conversation)).order_by(message_attachments.c.id)
        .with_for_update()).mappings().all()
    if len(rows) != len(refs):
        raise ServiceError("attachment_not_found", 404)
    now = datetime.now(timezone.utc)
    for row in rows:
        if row["message_id"] is not None:
            raise ServiceError("attachment_already_bound")
        if row["status"] != "ready":
            raise ServiceError("attachment_not_ready")
        if row["expires_at"] <= now:
            raise ServiceError("attachment_expired", 410)
    if sum(row["size_bytes"] for row in rows) > MAX_TOTAL_BYTES:
        raise ServiceError("attachment_total_size_limit", 422)
    by_id, result = {row["id"]: dict(row) for row in rows}, []
    for position, ref in enumerate(refs):
        row = by_id[ref["attachment_id"]]
        manifest = {"attachment_id": str(row["id"]), "message_id": str(message["id"]),
            "position": position, "cid": ref["cid"], "revision": row["revision"],
            "source_sha256": row["source_sha256"], "mime_type": row["mime_type"], "size_bytes": row["size_bytes"]}
        values = {"message_id": message["id"], "position": position, "cid": ref["cid"], "manifest": manifest}
        conn.execute(update(message_attachments).where(message_attachments.c.id == row["id"])
            .values(**values, updated_at=func.now()))
        row.update(values)
        result.append(attachment_metadata(row))
    return result
