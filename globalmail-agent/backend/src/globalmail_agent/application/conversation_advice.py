"""Read latest internal advice with current validity; GET never starts a run."""
import json
import sqlalchemy as sa
from globalmail_agent.adapters.agent_schema import reply_artifacts
from globalmail_agent.adapters.conversation_schema import conversations, agent_runs
from globalmail_agent.adapters.body_store import read_bytes
from globalmail_agent.application.conversation_lock import ServiceError, DEFAULT_WORKSPACE_ID
from globalmail_agent.application.run_records import RunRecords


class ConversationAdvice:
    def __init__(self, engine, store, workspace=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.workspace = engine, store, workspace

    def get(self, conversation_id):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)
        with self.engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn, conn.begin():
            conv = conn.execute(sa.select(conversations).where(conversations.c.id == conversation_id,
                conversations.c.workspace_id == self.workspace,
                conversations.c.lifecycle.not_in(["deleting", "deleted"]))).mappings().first()
            if conv is None:
                raise ServiceError("conversation_not_found", 404)
            latest = conn.execute(sa.select(agent_runs).where(agent_runs.c.conversation_id == conversation_id)
                .order_by(agent_runs.c.created_at.desc(), agent_runs.c.id.desc()).limit(1)).mappings().first()
            row = conn.execute(sa.select(reply_artifacts).where(reply_artifacts.c.conversation_id == conversation_id,
                reply_artifacts.c.advice_object_id.is_not(None)).order_by(reply_artifacts.c.created_at.desc(),
                reply_artifacts.c.id.desc()).limit(1)).mappings().first()
            if row is None:
                return {"advice": None, "run_id": str(latest["id"]) if latest else None,
                    "stale": False, "input_revision": conv["input_revision"], "observations": []}
            value = json.loads(read_bytes(conn, self.store, conv, row["advice_object_id"]))
            stale = conv["lifecycle"] != "open" or value["input_revision"] != conv["input_revision"] or (
                latest is None or latest["id"] != row["run_id"])
        record = RunRecords(self.engine, self.store, self.workspace).get(row["run_id"])
        return {"advice": value, "run_id": str(row["run_id"]), "stale": stale,
            "input_revision": conv["input_revision"], "observations": record["tools"]}
