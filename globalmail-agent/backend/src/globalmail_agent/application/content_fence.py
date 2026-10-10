"""Persistent tombstones protect every object reader and derived writer."""
import sqlalchemy as sa
from globalmail_agent.adapters.schema import objects, deletion_journal, content_dependencies, SCOPE_KEYS
from globalmail_agent.application.conversation_lock import ServiceError


def check_objects(conn, scope, identities, *, writing=False):
    identities = set(identities)
    if not identities:
        return
    ancestors = sa.select(objects.c.id).where(objects.c.id.in_(identities),
        *[objects.c[k] == scope[k] for k in SCOPE_KEYS]).cte("content_fence_sources", recursive=True)
    ancestors = ancestors.union(sa.select(content_dependencies.c.source_object_id).join(ancestors,
        content_dependencies.c.dependent_object_id == ancestors.c.id).where(
            *[content_dependencies.c[k] == scope[k] for k in SCOPE_KEYS]))
    query = sa.select(objects.c.id).where(objects.c.id.in_(sa.select(ancestors.c.id))).order_by(objects.c.id)
    if writing:
        query = query.with_for_update()
    found = set(conn.execute(query).scalars())
    if writing and not identities.issubset(found):
        raise ServiceError("object_not_found", 404)
    if conn.execute(sa.select(deletion_journal.c.id).where(
            *[deletion_journal.c[k] == scope[k] for k in SCOPE_KEYS],
            deletion_journal.c.target_object_id.in_(found)).limit(1)).first():
        raise ServiceError("content_deleted", 410)


def check_conversation_write(conn, scope):
    if scope.get("purpose") != "conversation":
        return
    from globalmail_agent.adapters.conversation_schema import conversations
    row = conn.execute(sa.select(conversations.c.id, conversations.c.lifecycle).where(
        *[conversations.c[k] == scope[k] for k in SCOPE_KEYS]).with_for_update()).first()
    if row is None or row.lifecycle in {"deleting", "deleted"}:
        raise ServiceError("conversation_not_found", 404)
    from globalmail_agent.adapters.lifecycle_schema import deletion_requests
    if conn.execute(sa.select(deletion_requests.c.id).where(
        deletion_requests.c.workspace_id == scope['workspace_id'],
        deletion_requests.c.status != 'completed',
        deletion_requests.c.manifest['conversation_ids'].contains([str(row.id)])).limit(1)).first():
        raise ServiceError('cleanup_in_progress', 409)


def readable_objects(conn, scope, identities):
    from globalmail_agent.attachments.revocation import check_content_access
    result = []
    for identity in identities:
        try:
            check_content_access(conn, scope, identity)
        except ServiceError as error:
            if error.code not in {'content_deleted', 'image_content_revoked'}:
                raise
        else:
            result.append(identity)
    return tuple(result)
