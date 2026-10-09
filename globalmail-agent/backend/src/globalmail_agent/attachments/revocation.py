"""Immediate read fence for all objects derived from a revoked image, across old runs."""
import sqlalchemy as sa
from globalmail_agent.adapters.attachment_schema import message_attachments
from globalmail_agent.adapters.schema import content_dependencies, SCOPE_KEYS
from globalmail_agent.application.conversation_lock import ServiceError

REDACTED = "（图片证据已撤销，相关派生内容不可读取）"


def check_content_access(conn, conv, object_id):
    ancestors = sa.select(sa.literal(object_id, type_=sa.Uuid).label("id")).cte("image_ancestors", recursive=True)
    ancestors = ancestors.union(sa.select(content_dependencies.c.source_object_id).join(ancestors,
        content_dependencies.c.dependent_object_id == ancestors.c.id).where(
        *[content_dependencies.c[k] == conv[k] for k in SCOPE_KEYS]))
    forbidden = conn.execute(sa.select(message_attachments.c.id).where(
        message_attachments.c.conversation_id == conv["id"],
        *[message_attachments.c[k] == conv[k] for k in SCOPE_KEYS],
        message_attachments.c.status.in_(["revoked", "cancelled"]),
        message_attachments.c.source_object_id.in_(sa.select(ancestors.c.id)))).first()
    if forbidden:
        raise ServiceError("image_content_revoked", 410)
