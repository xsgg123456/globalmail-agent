"""Bounded, non-generative full-image views; only scoped refs enter graph state."""
import hashlib
from io import BytesIO
from math import ceil
from uuid import UUID
import sqlalchemy as sa
from PIL import Image, ImageOps
from globalmail_agent.adapters.attachment_schema import message_attachments
from globalmail_agent.adapters.body_store import BodyWriter, read_bytes
from globalmail_agent.agent.guard import guarded
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.attachments.queries import authorize_attachment, read_attachment_bytes

PREPROCESS_VERSION = "full-image/1-exif-1024"


def bounded_view(content):
    with Image.open(BytesIO(content), formats=["JPEG", "PNG", "WEBP"]) as original:
        if original.width * original.height > 20000000 or getattr(original, "n_frames", 1) != 1:
            raise ServiceError("image_limits_invalid", 422)
        image = ImageOps.exif_transpose(original).convert("RGBA")
        background = Image.new("RGBA", image.size, "white")
        background.alpha_composite(image)
        image = background.convert("RGB")
        image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        # Account for provider patch rounding and minimum resolution, not base64 length.
        width, height = max(32, ceil(image.width / 32) * 32), max(32, ceil(image.height / 32) * 32)
        image = image.resize((width, height), Image.Resampling.LANCZOS)
        result = BytesIO()
        image.save(result, format="PNG")
        return result.getvalue(), width, height, 2 * (width * height // 1024 + 2) + 512


def prepare_authorized_image_views(engine, store, context, job):
    refs = []
    selected = [r for r in reversed(context.payload.get("attachments", []))
        if r["status"] not in {"missing", "unsupported", "revoked", "cancelled"}][:6]
    with guarded(engine, context.workspace_id, job) as (conn, conv, run, cycle):
        for item in selected:
            row = authorize_attachment(conn, conv, UUID(item["attachment_id"]), lock=True)
            conn.execute(message_attachments.update().where(message_attachments.c.id == row["id"])
                .values(status="processing", processing_run_id=run["id"], failure_reason=None))
    with BodyWriter(store) as writer, guarded(engine, context.workspace_id, job) as (conn, conv, run, cycle):
        # Cover newest input first; every excluded image remains explicitly unread.
        for item in selected:
            row = authorize_attachment(conn, conv, UUID(item["attachment_id"]), lock=True)
            content, _ = read_attachment_bytes(conn, store, conv, row)
            view, width, height, upper = bounded_view(content)
            object_id = writer.put_bytes(conn, conv, view, "authorized_image_view", (row["source_object_id"],))
            refs.append({"attachment_id": str(row["id"]), "message_id": str(row["message_id"]),
                "revision": row["revision"], "evidence_epoch": row["evidence_epoch"],
                "source_sha256": row["source_sha256"], "derived_view_hash": hashlib.sha256(view).hexdigest(),
                "view_object_id": str(object_id), "width": width, "height": height,
                "visual_token_upper": upper, "preprocess_version": PREPROCESS_VERSION,
                "location": {"type": "full_image", "orientation_corrected": True,
                    "source_width": row["width"], "source_height": row["height"],
                    "view_width": width, "view_height": height}})
            conn.execute(message_attachments.update().where(message_attachments.c.id == row["id"])
                .values(status="processing", processing_run_id=run["id"], failure_reason=None))
    return refs


def load_authorized_view(engine, store, context, job, ref):
    with guarded(engine, context.workspace_id, job) as (conn, conv, run, cycle):
        row = authorize_attachment(conn, conv, UUID(ref["attachment_id"]), lock=True)
        if (row["evidence_epoch"] != ref["evidence_epoch"] or row["revision"] != ref["revision"]
                or row["source_sha256"] != ref["source_sha256"] or row["processing_run_id"] != run["id"]):
            raise ServiceError("image_evidence_stale")
        content = read_bytes(conn, store, conv, UUID(ref["view_object_id"]))
        if hashlib.sha256(content).hexdigest() != ref["derived_view_hash"]:
            raise ServiceError("image_integrity_error", 503)
        return content
