"""Run-scoped synchronous LangGraph persistence inside the business write fence."""
import json
import math
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

import psycopg
import sqlalchemy as sa
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver, ChannelVersions, Checkpoint, CheckpointMetadata, CheckpointTuple,
)
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.engine import Connection, Engine

from globalmail_agent.adapters.business_schema import simulation_branches
from globalmail_agent.adapters.conversation_schema import agent_runs, conversations, jobs
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.conversation_lock import ServiceError


def _validate_json(value):
    """Allow data containers only; no object reconstruction or binary image state."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) in (list, tuple):
        for item in value:
            _validate_json(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _validate_json(item)
        return
    raise TypeError("Checkpoint values must be finite JSON data")


class JsonStateSerializer:
    """Strict SerializerProtocol: JSON data never invokes a Python constructor."""
    def dumps_typed(self, value: Any) -> tuple[str, bytes]:
        _validate_json(value)
        return "json", json.dumps(value, ensure_ascii=False, allow_nan=False,
                                  separators=(",", ":")).encode("utf-8")

    def loads_typed(self, value: tuple[str, bytes]) -> Any:
        kind, payload = value
        if kind != "json":
            raise ValueError("Unsupported checkpoint serialization type")
        result = json.loads(payload)
        _validate_json(result)
        return result


def _driver_connection(connection: Connection) -> psycopg.Connection:
    raw = connection.connection.driver_connection
    if not isinstance(raw, psycopg.Connection) or raw.autocommit or not connection.in_transaction():
        raise RuntimeError("Checkpoint persistence requires an active psycopg SQLAlchemy transaction")
    return raw


class _TransactionalSetupSaver(PostgresSaver):
    # SDK 3.1.2 migrations 6–8 create exactly the same indexes, without the
    # CONCURRENTLY scheduling option forbidden inside Alembic's transaction.
    # SDK setup still owns all schema definitions and migration version records.
    MIGRATIONS = [migration.replace("CREATE INDEX CONCURRENTLY", "CREATE INDEX")
                  for migration in PostgresSaver.MIGRATIONS]


def setup_checkpoint(connection: Connection) -> None:
    """Initialize the SDK's tables in the caller's current schema and transaction."""
    _TransactionalSetupSaver(_driver_connection(connection), serde=JsonStateSerializer()).setup()


class CheckpointRepository(BaseCheckpointSaver[str]):
    """Only sync graphs are supported. Each instance is bound to one claimed run.

    SDK cursors use dict_row locally, leaving SQLAlchemy's connection row factory
    intact. SDK pipeline exit flushes writes; SQLAlchemy alone commits/rolls back.
    No connection pool or connection-string saver is permitted behind the fence.
    """
    def __init__(self, engine: Engine, workspace_id, job: Mapping, store=None):
        super().__init__(serde=JsonStateSerializer())
        self.engine, self.workspace_id, self.job = engine, workspace_id, dict(job)
        self.store = store
        self.thread_id = str(self.job["run_id"])

    def _config(self, config: RunnableConfig | None, *, default=False) -> RunnableConfig:
        if config is None and default:
            config = {"configurable": {"thread_id": self.thread_id}}
        configurable = (config or {}).get("configurable", {})
        if configurable.get("thread_id") != self.thread_id:
            raise ServiceError("checkpoint_thread_forbidden", 404)
        return {**config, "configurable": {"checkpoint_ns": "", **configurable}}

    def _read_scope(self, connection):
        query = sa.select(agent_runs.c.id).join(jobs, jobs.c.run_id == agent_runs.c.id).join(
            conversations, conversations.c.id == agent_runs.c.conversation_id).outerjoin(
            simulation_branches, simulation_branches.c.id == agent_runs.c.branch_id).where(
                agent_runs.c.id == self.job["run_id"], jobs.c.id == self.job["id"],
                agent_runs.c.workspace_id == self.workspace_id,
                conversations.c.lifecycle.not_in(("deleting", "deleted")),
                conversations.c.branch_generation == agent_runs.c.branch_generation,
                sa.or_(simulation_branches.c.id.is_(None),
                       simulation_branches.c.generation == agent_runs.c.branch_generation),
                *[agent_runs.c[key] == conversations.c[key] for key in SCOPE_KEYS],
                *[agent_runs.c[key] == jobs.c[key] for key in SCOPE_KEYS])
        if connection.execute(query).first() is None:
            raise ServiceError("run_not_found", 404)
        from globalmail_agent.adapters.agent_schema import agent_run_contexts
        from globalmail_agent.attachments.revocation import check_content_access
        source = connection.execute(sa.select(agent_run_contexts.c.context_object_id).where(
            agent_run_contexts.c.run_id == self.job["run_id"])).scalar_one_or_none()
        if source:
            conv = connection.execute(sa.select(conversations).where(
                conversations.c.id == self.job["conversation_id"])).mappings().one()
            check_content_access(connection, conv, source)

    def _saver(self, connection):
        return PostgresSaver(_driver_connection(connection), serde=self.serde)

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        config = self._config(config)
        with self.engine.begin() as connection:
            self._read_scope(connection)
            return self._saver(connection).get_tuple(config)

    def list(self, config: RunnableConfig | None, *, filter: dict[str, Any] | None = None,
             before: RunnableConfig | None = None, limit: int | None = None) -> Iterator[CheckpointTuple]:
        config = self._config(config, default=True)
        if before is not None:
            before = self._config(before)
        with self.engine.begin() as connection:
            self._read_scope(connection)
            # Consume the SDK cursor before returning; no open transaction escapes.
            rows = list(self._saver(connection).list(config, filter=filter, before=before, limit=limit))
        return iter(rows)

    def put(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata,
            new_versions: ChannelVersions) -> RunnableConfig:
        from globalmail_agent.agent.guard import guarded
        config = self._config(config)
        _validate_json(checkpoint)
        _validate_json(metadata)
        with guarded(self.engine, self.workspace_id, self.job, checkpoint=True) as guarded_rows:
            connection, _, _, _ = guarded_rows
            return self._saver(connection).put(config, checkpoint, metadata, new_versions)

    def put_writes(self, config: RunnableConfig, writes: Sequence[tuple[str, Any]],
                   task_id: str, task_path: str = "") -> None:
        from globalmail_agent.agent.guard import guarded
        config = self._config(config)
        # LangGraph writes node exceptions to its reserved error channel. Save
        # only a diagnostic code, never exception objects, args or provider text.
        writes = [(channel, {"error_type": type(value).__name__,
                  "code": value.code if isinstance(value, ServiceError) else "graph_node_failed"})
                  if channel == "__error__" and isinstance(value, BaseException) else (channel, value)
                  for channel, value in writes]
        for _, value in writes:
            _validate_json(value)
        with guarded(self.engine, self.workspace_id, self.job, checkpoint=True) as guarded_rows:
            connection, _, _, _ = guarded_rows
            self._saver(connection).put_writes(config, writes, task_id, task_path)

    def get_next_version(self, current: str | None, channel: None) -> str:
        return PostgresSaver.get_next_version(self, current, channel)

    async def aget_tuple(self, config):
        raise NotImplementedError("CheckpointRepository supports synchronous graphs only")

    async def aput(self, config, checkpoint, metadata, new_versions):
        raise NotImplementedError("CheckpointRepository supports synchronous graphs only")

    async def aput_writes(self, config, writes, task_id, task_path=""):
        raise NotImplementedError("CheckpointRepository supports synchronous graphs only")

    async def alist(self, config, *, filter=None, before=None, limit=None):
        raise NotImplementedError("CheckpointRepository supports synchronous graphs only")
        yield  # Preserve the SDK async-iterator protocol.
