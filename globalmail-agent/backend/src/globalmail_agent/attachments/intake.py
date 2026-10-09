"""Image staging is independent from mail acceptance and never enqueues model work."""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from sqlalchemy import select, insert, update, delete, func, or_
from globalmail_agent.adapters.body_store import BodyWriter
from globalmail_agent.adapters.attachment_schema import message_attachments
from globalmail_agent.adapters.conversation_schema import agent_slots, conversations, identities
from globalmail_agent.adapters.schema import objects, content_dependencies, metadata, SCOPE_KEYS
from globalmail_agent.application.conversation_base import ServiceBase
from globalmail_agent.application.conversation_lock import DEFAULT_DATASET_ID, ServiceError
from globalmail_agent.application.idempotency import prior, remember
from globalmail_agent.domain.conversation import CreateConversation
from globalmail_agent.attachments.queries import attachment_metadata, authorize_attachment, scoped_where
from globalmail_agent.attachments.validation import inspect_image


class AttachmentService(ServiceBase):
    def available(self):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)

    def stage(self, filename, content, key, *, conversation_id=None, sender_email=None):
        self.available()
        if (conversation_id is None) == (sender_email is None):
            raise ServiceError("attachment_target_required", 422)
        if sender_email is not None:
            try:
                sender_email = CreateConversation.email(sender_email)
            except (ValueError, TypeError, AttributeError):
                raise ServiceError("invalid_email", 422) from None
        inspected = inspect_image(filename, content)
        payload = {"filename": filename, "sha256": inspected["source_sha256"],
            "conversation_id": str(conversation_id) if conversation_id else None, "sender_email": sender_email}
        with BodyWriter(self.store) as writer, self.engine.begin() as conn:
            previous, digest = prior(conn, self.workspace_id, key, "attachment-upload", payload)
            if previous is not None:
                conversation = self.lock(conn, UUID(previous["conversation_id"]))
                authorize_attachment(conn, conversation, UUID(previous["attachment_id"]), lock=True, allow_staged=True)
                return previous
            conversation = self._target(conn, conversation_id, sender_email)
            if conversation["mode"] != "simulation":
                raise ServiceError("historical_messages_read_only")
            source_id = writer.put_bytes(conn, conversation, content, "customer_image")
            thumbnail_id = writer.put_bytes(conn, conversation, inspected.pop("thumbnail"),
                "customer_image_thumbnail", derived_from=(source_id,))
            row = {"id": uuid4(), **{k: conversation[k] for k in SCOPE_KEYS},
                "conversation_id": conversation["id"], "message_id": None, "position": None, "cid": None,
                "filename": filename, **inspected, "source_object_id": source_id,
                "thumbnail_object_id": thumbnail_id, "revision": 1, "evidence_epoch": 0,
                "status": "ready", "expires_at": datetime.now(timezone.utc) + timedelta(hours=24)}
            conn.execute(insert(message_attachments).values(**row))
            result = attachment_metadata(row)
            remember(conn, self.workspace_id, key, "attachment-upload", digest, result)
            return result

    def _target(self, conn, conversation_id, sender_email):
        if conversation_id is not None:
            return self.lock(conn, conversation_id)
        conn.execute(select(agent_slots).where(agent_slots.c.workspace_id == self.workspace_id,
            agent_slots.c.slot_key == "agent").with_for_update()).first()
        existing = conn.execute(select(conversations).join(identities, conversations.c.identity_id == identities.c.id)
            .where(identities.c.workspace_id == self.workspace_id, identities.c.dataset_id == DEFAULT_DATASET_ID,
                identities.c.mode == "simulation", identities.c.sender_key == sender_email)).mappings().first()
        return self.lock(conn, existing["id"]) if existing else self.new_conversation(
            conn, sender_email, "simulation", "", True, "manual")

    def cancel(self, attachment_id, expected_version=0):
        self.available()
        if expected_version != 0:
            raise ServiceError("initial_version_required", 422)
        with self.engine.begin() as conn:
            anchor = conn.execute(select(message_attachments.c.conversation_id).where(
                message_attachments.c.id == attachment_id, message_attachments.c.workspace_id == self.workspace_id)).first()
            if anchor is None:
                raise ServiceError("attachment_not_found", 404)
            conversation = self.lock(conn, anchor.conversation_id)
            row = conn.execute(select(message_attachments).where(message_attachments.c.id == attachment_id,
                message_attachments.c.conversation_id == conversation["id"], *scoped_where(message_attachments, conversation))
                .with_for_update()).mappings().first()
            if row is None:
                raise ServiceError("attachment_not_found", 404)
            if row["message_id"] is not None:
                raise ServiceError("attachment_already_bound")
            if row["status"] not in {"ready", "cancelled"}:
                raise ServiceError("attachment_not_ready")
            conn.execute(update(message_attachments).where(message_attachments.c.id == attachment_id)
                .values(status="cancelled", updated_at=func.now()))
            return {"attachment_id": str(attachment_id), "status": "cancelled"}

    def cleanup_expired(self, now=None, limit=100):
        self.available()
        now = now or datetime.now(timezone.utc)
        removed = []
        with self.engine.connect() as conn:
            candidates = conn.execute(select(message_attachments.c.id, message_attachments.c.conversation_id).where(
                message_attachments.c.workspace_id == self.workspace_id, message_attachments.c.message_id.is_(None),
                or_(message_attachments.c.expires_at <= now, message_attachments.c.status == "cancelled"))
                .order_by(message_attachments.c.id).limit(limit)).all()
        for aid, cid in candidates:
            with self.engine.begin() as conn:
                conversation = self.lock(conn, cid)
                row = conn.execute(select(message_attachments).where(message_attachments.c.id == aid,
                    *scoped_where(message_attachments, conversation)).with_for_update()).mappings().first()
                if row is None or row["message_id"] is not None or not (row["expires_at"] <= now or row["status"] == "cancelled"):
                    continue
                object_ids = {row[k] for k in ("source_object_id", "thumbnail_object_id") if row[k] is not None}
                if self._other_references(conn, aid, object_ids):
                    continue
                paths = [self.store._path(oid) for oid in object_ids]
                # These objects are already expired/cancelled. Keep their denied registry
                # rows if unlink or the transaction fails, so the next cleanup can retry.
                for path in paths:
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        raise ServiceError("attachment_cleanup_failed", 503) from None
                conn.execute(delete(message_attachments).where(message_attachments.c.id == aid))
                if object_ids:
                    conn.execute(delete(content_dependencies).where(
                        content_dependencies.c.source_object_id.in_(object_ids),
                        content_dependencies.c.dependent_object_id.in_(object_ids)))
                    conn.execute(delete(objects).where(objects.c.id.in_(object_ids), *scoped_where(objects, conversation)))
            removed.append(str(aid))
        return {"removed": removed}

    def _other_references(self, conn, attachment_id, object_ids):
        if not object_ids:
            return False
        edges = conn.execute(select(content_dependencies).where(or_(
            content_dependencies.c.source_object_id.in_(object_ids),
            content_dependencies.c.dependent_object_id.in_(object_ids)))).mappings()
        if any(edge["source_object_id"] not in object_ids or edge["dependent_object_id"] not in object_ids for edge in edges):
            return True
        # Enumerate registered FKs so cleanup cannot delete an object reused by another child.
        for table in metadata.tables.values():
            for column in table.columns:
                if table is content_dependencies or not any(fk.target_fullname == "objects.id" for fk in column.foreign_keys):
                    continue
                query = select(table.c.id).where(column.in_(object_ids))
                if table is message_attachments:
                    query = query.where(table.c.id != attachment_id)
                if conn.execute(query.limit(1)).first() is not None:
                    return True
        return False
