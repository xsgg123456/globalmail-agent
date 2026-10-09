from uuid import UUID
from sqlalchemy import select
from globalmail_agent.adapters.conversation_schema import agent_slots, conversations

DEFAULT_WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_DATASET_ID = UUID("00000000-0000-0000-0000-000000000002")


class ServiceError(Exception):
    def __init__(self, code, status=409):
        self.code, self.status = code, status


def lock_conversation(conn, conversation_id, workspace_id=DEFAULT_WORKSPACE_ID, expected_version=None):
    # Invalidation can revoke either task kind; lock both before the conversation.
    conn.execute(select(agent_slots).where(agent_slots.c.workspace_id == workspace_id)
        .order_by(agent_slots.c.slot_key).with_for_update()).mappings().all()
    from globalmail_agent.adapters.business_schema import simulation_branches
    conn.execute(select(simulation_branches).where(simulation_branches.c.conversation_id == conversation_id,
        simulation_branches.c.workspace_id == workspace_id).with_for_update()).mappings().first()
    row = conn.execute(select(conversations).where(conversations.c.id == conversation_id,
        conversations.c.workspace_id == workspace_id).with_for_update()).mappings().first()
    if row is None or row["lifecycle"] in {"deleting", "deleted"}:
        raise ServiceError("conversation_not_found", 404)
    if expected_version is not None and row["row_version"] != expected_version:
        raise ServiceError("stale_version")
    return dict(row)
