"""Authorize images against full scope and the visible prefix before reading bytes."""
from datetime import datetime, timezone
import hashlib
from sqlalchemy import select
from globalmail_agent.adapters.attachment_schema import message_attachments
from globalmail_agent.adapters.conversation_schema import messages
from globalmail_agent.adapters.schema import objects, deletion_journal, SCOPE_KEYS
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError, lock_conversation


def scoped_where(table, conversation):
    return [table.c[k] == conversation[k] for k in SCOPE_KEYS]


def attachment_metadata(row):
    fields = ("conversation_id", "message_id", "position", "cid", "filename", "mime_type",
        "size_bytes", "width", "height", "revision", "evidence_epoch", "status")
    return {"attachment_id": str(row["id"]), "failure_reason": row.get("failure_reason"), **{k: str(row[k]) if k in
        {"conversation_id", "message_id"} and row[k] is not None else row[k] for k in fields}}


def authorize_attachment(conn, conversation, attachment_id, *, lock=False, allow_staged=False):
    query = select(message_attachments).where(message_attachments.c.id == attachment_id,
        message_attachments.c.conversation_id == conversation["id"], *scoped_where(message_attachments, conversation))
    row = conn.execute(query.with_for_update() if lock else query).mappings().first()
    if row is None:
        raise ServiceError("attachment_not_found", 404)
    if row["status"] in {"revoked", "cancelled"}:
        raise ServiceError("attachment_revoked", 410)
    if row["message_id"] is None:
        if not allow_staged:
            raise ServiceError("attachment_not_bound", 409)
        if row["expires_at"] <= datetime.now(timezone.utc):
            raise ServiceError("attachment_expired", 410)
    else:
        message = conn.execute(select(messages.c.id).where(messages.c.id == row["message_id"],
            messages.c.conversation_id == conversation["id"], messages.c.seq <= conversation["visible_message_seq"],
            *scoped_where(messages, conversation))).first()
        if message is None:
            raise ServiceError("attachment_not_visible", 404)
    return dict(row)


def read_attachment_bytes(conn, store, conversation, row, *, thumbnail=False):
    # Recheck source revocation even when reading its derived thumbnail.
    object_id = row["thumbnail_object_id"] if thumbnail else row["source_object_id"]
    if object_id is None or row["source_object_id"] is None:
        raise ServiceError("attachment_bytes_unavailable", 503)
    if row["status"] in {"revoked", "cancelled"}:
        raise ServiceError("attachment_revoked", 410)
    forbidden = conn.execute(select(deletion_journal.c.id).where(
        deletion_journal.c.target_object_id.in_([row["source_object_id"], object_id]),
        *scoped_where(deletion_journal, conversation))).first()
    if forbidden is not None:
        raise ServiceError("attachment_revoked", 410)
    obj = conn.execute(select(objects).where(objects.c.id == object_id,
        *scoped_where(objects, conversation))).mappings().first()
    if obj is None:
        raise ServiceError("attachment_bytes_unavailable", 503)
    try:
        content = store._path(object_id).read_bytes()
    except (OSError, ValueError):
        raise ServiceError("attachment_bytes_unavailable", 503) from None
    digest = hashlib.sha256(content).hexdigest()
    if (len(content) != obj["size_bytes"] or digest != obj["sha256"]
            or not thumbnail and (digest != row["source_sha256"] or len(content) != row["size_bytes"])):
        raise ServiceError("attachment_integrity_error", 503)
    return content, "image/jpeg" if thumbnail else row["mime_type"]


def list_message_attachments(conn, conversation, message_id):
    visible = conn.execute(select(messages.c.id).where(messages.c.id == message_id,
        messages.c.conversation_id == conversation["id"], messages.c.seq <= conversation["visible_message_seq"],
        *scoped_where(messages, conversation))).first()
    if visible is None:
        return []
    rows = conn.execute(select(message_attachments).where(message_attachments.c.message_id == message_id,
        message_attachments.c.conversation_id == conversation["id"], *scoped_where(message_attachments, conversation))
        .order_by(message_attachments.c.position)).mappings()
    return [attachment_metadata(row) for row in rows]


class AttachmentQueries:
    def __init__(self, engine, store, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.workspace_id = engine, store, workspace_id

    def available(self):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)

    def preview(self, attachment_id, conversation_id, thumbnail=True):
        self.available()
        with self.engine.begin() as conn:
            conversation = lock_conversation(conn, conversation_id, self.workspace_id)
            row = authorize_attachment(conn, conversation, attachment_id, lock=True, allow_staged=True)
            return read_attachment_bytes(conn, self.store, conversation, row, thumbnail=thumbnail)

    def listing(self, conversation_id):
        self.available()
        with self.engine.begin() as conn:
            conversation = lock_conversation(conn, conversation_id, self.workspace_id)
            rows = conn.execute(select(message_attachments).join(messages,
                message_attachments.c.message_id == messages.c.id).where(
                message_attachments.c.conversation_id == conversation_id,
                *scoped_where(message_attachments, conversation), *scoped_where(messages, conversation),
                messages.c.conversation_id == conversation_id, messages.c.seq <= conversation["visible_message_seq"])
                .order_by(messages.c.seq, message_attachments.c.position)).mappings()
            return {"items": [attachment_metadata(row) for row in rows]}
