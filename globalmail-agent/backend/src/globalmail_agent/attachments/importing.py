"""Metadata stays unread; controlled package bytes are decoded and scoped on ingestion."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.attachment_schema import message_attachments
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.attachments.validation import inspect_image, MAX_BYTES, MAX_TOTAL_BYTES

SUPPORTED = {"image/jpeg", "image/png", "image/webp"}


def assert_metadata(conn, conv, message, items):
    expected = [item.model_dump() for item in items]
    rows = conn.execute(sa.select(message_attachments).where(message_attachments.c.message_id == message["id"],
        message_attachments.c.conversation_id == conv["id"], message_attachments.c.source_object_id.is_(None),
        *[message_attachments.c[k] == conv[k] for k in SCOPE_KEYS]).order_by(message_attachments.c.position)).mappings()
    actual = [{k: row[k] for k in ("filename", "mime_type", "cid")} for row in rows]
    if actual != expected:
        raise ServiceError("source_message_conflict")


def save_metadata(conn, conv, message, items, *, writer=None, package=None):
    if not items:
        return
    position = conn.execute(sa.select(sa.func.count()).select_from(message_attachments).where(
        message_attachments.c.message_id == message["id"])).scalar_one()
    if position + len(items) > 4:
        raise ServiceError("attachment_count_limit", 422)
    for item in items:
        item = item.model_dump() if hasattr(item, "model_dump") else item
        filename = item.get("filename", item.get("name", "附件"))
        mime = item.get("mime_type", "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else
            "image/png" if filename.lower().endswith(".png") else "image/webp" if filename.lower().endswith(".webp") else "application/octet-stream")
        if not isinstance(filename, str) or len(filename) > 240 or any(c in filename for c in "/\\\x00"):
            raise ServiceError("invalid_image_filename", 422)
        row = {"id": uuid4(), **{k: conv[k] for k in SCOPE_KEYS}, "conversation_id": conv["id"],
            "message_id": message["id"], "position": position, "filename": filename,
            "cid": item.get("cid"), "mime_type": mime, "size_bytes": 0, "revision": 1, "evidence_epoch": 0,
            "status": "missing" if mime in SUPPORTED else "unsupported", "expires_at": datetime.now(timezone.utc)}
        if item.get("content_id"):
            if package is None or writer is None:
                raise ServiceError("controlled_attachment_package_required", 422)
            content = package_bytes(package, item["content_id"])
            inspected = inspect_image(filename, content)
            original = writer.put_bytes(conn, conv, content, "customer_image")
            thumbnail = writer.put_bytes(conn, conv, inspected.pop("thumbnail"), "customer_image_thumbnail", (original,))
            row.update(**inspected, status="ready", source_object_id=original, thumbnail_object_id=thumbnail)
        row["manifest"] = {k: str(v) if k in {"id", "message_id"} else v for k, v in row.items()
            if k in {"id", "message_id", "position", "filename", "cid", "mime_type", "source_sha256", "status"}}
        conn.execute(sa.insert(message_attachments).values(**row))
        position += 1
    total = conn.execute(sa.select(sa.func.sum(message_attachments.c.size_bytes)).where(
        message_attachments.c.message_id == message["id"])).scalar_one() or 0
    if total > MAX_TOTAL_BYTES:
        raise ServiceError("attachment_total_size_limit", 422)


def package_bytes(package, content_id):
    root = Path(package.root).resolve()
    directory = (root / "attachments").resolve()
    if not directory.is_relative_to(root):
        raise ServiceError("fixture_attachment_path_denied", 422)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    entry = manifest.get(content_id)
    if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
        raise ServiceError("fixture_attachment_not_allowed", 422)
    path = (directory / entry["path"]).resolve()
    if not path.is_relative_to(directory) or not path.is_file():
        raise ServiceError("fixture_attachment_path_denied", 422)
    with path.open("rb") as stream:
        content = stream.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ServiceError("image_too_large", 422)
    if hashlib.sha256(content).hexdigest() != entry["sha256"]:
        raise ServiceError("fixture_attachment_integrity_error", 422)
    return content
