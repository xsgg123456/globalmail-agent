"""Register body dependencies on the caller's object-registration transaction."""
from uuid import UUID, uuid4
from sqlalchemy import insert

from globalmail_agent.adapters.schema import content_dependencies


def register_dependencies(connection, scope: dict, object_id: UUID, source_ids: tuple[UUID, ...]):
    for source_id in set(source_ids):
        connection.execute(insert(content_dependencies).values(
            id=uuid4(), **scope, source_object_id=source_id, dependent_object_id=object_id,
        ))
