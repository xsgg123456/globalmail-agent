"""Seed frozen pre-0010 shapes without invoking current head-only permission columns."""
from uuid import UUID, uuid4
from unittest.mock import patch
import sqlalchemy as sa
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.application.conversations import ConversationService
from globalmail_agent.application.fixture_conversations import FixtureConversations


class LegacyLock:
    def lock(self, conn, conversation_id, expected_version=None):
        table = sa.Table("conversations", sa.MetaData(), autoload_with=conn)
        row = conn.execute(sa.select(table).where(table.c.id == conversation_id,
            table.c.workspace_id == self.workspace_id).with_for_update()).mappings().one()
        if expected_version is not None and row["row_version"] != expected_version:
            raise ServiceError("stale_version")
        return dict(row)


class LegacyConversations(LegacyLock, ConversationService):
    pass


class LegacyScenarios(LegacyLock, FixtureConversations):
    def accept(self, conn, *args, **kwargs):
        table = sa.Table("conversations", sa.MetaData(), autoload_with=conn)
        with patch("globalmail_agent.application.event_store.conversations", table):
            return super().accept(conn, *args, **kwargs)


def legacy_enqueue(conn, conv, event):
    metadata = sa.MetaData()
    tables = {name: sa.Table(name, metadata, autoload_with=conn) for name in
        ("processing_cycles", "agent_runs", "jobs", "conversations")}
    cycle, run, job = uuid4(), uuid4(), uuid4()
    scope = {k: conv[k] for k in SCOPE_KEYS}
    versions = {k: conv[k] for k in ("input_revision", "authority_epoch", "branch_generation")}
    conn.execute(tables["processing_cycles"].insert().values(id=cycle, **scope, **versions,
        conversation_id=conv["id"], trigger_id=event["id"],
        trigger_message_id=UUID(event["payload"]["message_id"]), state="queued"))
    conn.execute(tables["agent_runs"].insert().values(id=run, **scope, **versions,
        conversation_id=conv["id"], processing_cycle_id=cycle, trigger_id=event["id"], attempt_no=1, status="queued"))
    values = dict(id=job, **scope, conversation_id=conv["id"], run_id=run, cycle_id=cycle,
        kind="agent", status="queued", attempt_no=1)
    conn.execute(tables["jobs"].insert().values(**{k:v for k,v in values.items() if k in tables["jobs"].c}))
    conn.execute(tables["conversations"].update().where(tables["conversations"].c.id == conv["id"])
        .values(scheduling_state="queued"))
    return {"run_id":str(run),"job_id":str(job),"processing_cycle_id":str(cycle)}
