"""Real isolated PostgreSQL barriers exercise the SDK, not a fake checkpointer."""
import asyncio
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version
from threading import Event
from time import monotonic, sleep
from typing import TypedDict
from unittest.mock import patch
from uuid import uuid4

import sqlalchemy as sa
from langgraph.checkpoint.base import empty_checkpoint
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph

from globalmail_agent.adapters.checkpoint_repository import (
    CheckpointRepository, JsonStateSerializer, setup_checkpoint,
)
from globalmail_agent.adapters.conversation_schema import agent_runs, agent_slots, conversations, jobs
from globalmail_agent.adapters.knowledge_index_schema import knowledge_release_heads
from globalmail_agent.agent.context import load_context
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.domain.conversation import AppendMessage, Command, Takeover
from test_protocol import ProtocolFixture


def public_knowledge_snapshot():
    engine = sa.create_engine(os.environ["GLOBALMAIL_TEST_DATABASE_URL"], hide_parameters=True)
    try:
        with engine.connect() as connection:
            tables = connection.execute(sa.text("SELECT relname FROM pg_class JOIN pg_namespace ON pg_namespace.oid=relnamespace "
                "WHERE nspname='public' AND relkind='r' AND (relname LIKE 'knowledge_%' OR relname LIKE 'index_%' "
                "OR relname LIKE 'embedding_%' OR relname='evidence_refs') ORDER BY relname")).scalars().all()
            return {table: connection.execute(sa.text(f'SELECT count(*), md5(string_agg(row_to_json(t)::text, \'\' ORDER BY id)) '
                f'FROM public.{connection.dialect.identifier_preparer.quote(table)} t')).one() for table in tables}
    finally:
        engine.dispose()


class SerializerTests(unittest.TestCase):
    def test_exact_sdk_versions_and_json_roundtrip(self):
        self.assertEqual(version("langgraph"), "1.2.14")
        self.assertEqual(version("langgraph-checkpoint-postgres"), "3.1.2")
        serde = JsonStateSerializer()
        value = {"text": "完整德文 Grüße", "values": [1, False, None, {"reference_id": "safe"}]}
        self.assertEqual(serde.loads_typed(serde.dumps_typed(value)), value)

    def test_pickle_object_binary_and_nonfinite_data_are_rejected(self):
        serde = JsonStateSerializer()
        for value in (object(), b"image bytes", {1: "nonstring key"}, float("nan"), float("inf")):
            with self.subTest(value_type=type(value).__name__), self.assertRaises(TypeError):
                serde.dumps_typed(value)
        for kind in ("pickle", "msgpack", "constructor"):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                serde.loads_typed((kind, b"arbitrary content"))
        with self.assertRaises(TypeError):
            serde.loads_typed(("json", b'{"value": NaN}'))


class CheckpointTests(ProtocolFixture):
    def setUp(self):
        self.public_before = public_knowledge_snapshot()
        super().setUp()
        self.cid, self.rid = self.create()
        self.job = self.leases.claim("checkpoint_real_sdk_test")
        load_context(self.engine, self.service.store, DEFAULT_WORKSPACE_ID, self.job)
        self.repo = CheckpointRepository(self.engine, DEFAULT_WORKSPACE_ID, self.job)
        self.config = {"configurable": {"thread_id": str(self.rid), "checkpoint_ns": ""}}

    def checkpoint(self, value="controlled text"):
        result = empty_checkpoint()
        result["channel_values"] = {"state": {"body": value, "reference_ids": []}}
        result["channel_versions"] = {"state": self.repo.get_next_version(None, None)}
        return result

    def save(self):
        checkpoint = self.checkpoint()
        return self.repo.put(self.config, checkpoint, {"source": "input", "step": 0},
                             checkpoint["channel_versions"])

    def counts(self):
        with self.engine.connect() as connection:
            return tuple(connection.execute(sa.text(f"SELECT count(*) FROM {table} WHERE thread_id=:run"),
                {"run": str(self.rid)}).scalar_one() for table in ("checkpoints", "checkpoint_blobs", "checkpoint_writes"))

    def both_rejected(self, config):
        with self.assertRaises(ServiceError):
            self.repo.put(config, self.checkpoint(), {}, {"state": "new-version"})
        with self.assertRaises(ServiceError):
            self.repo.put_writes(config, [("state", {"body": "late"})], "late-task")

    def test_sdk_setup_is_idempotent_transactional_and_schema_scoped(self):
        with self.engine.begin() as connection:
            setup_checkpoint(connection)
            setup_checkpoint(connection)
            versions = connection.execute(sa.text("SELECT v FROM checkpoint_migrations ORDER BY v")).scalars().all()
            self.assertEqual(versions, list(range(len(PostgresSaver.MIGRATIONS))))
            indexes = connection.execute(sa.text("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() "
                "AND indexname LIKE 'checkpoint%thread_id_idx'")).scalars().all()
            self.assertEqual(set(indexes), {"checkpoints_thread_id_idx", "checkpoint_blobs_thread_id_idx", "checkpoint_writes_thread_id_idx"})
        rollback_schema = self.schema + "_rollback"
        with self.assertRaisesRegex(RuntimeError, "setup rollback"):
            with self.admin.begin() as connection:
                connection.execute(sa.text(f'CREATE SCHEMA "{rollback_schema}"'))
                connection.execute(sa.text(f'SET LOCAL search_path TO "{rollback_schema}"'))
                setup_checkpoint(connection)
                raise RuntimeError("setup rollback")
        with self.admin.connect() as connection:
            self.assertFalse(connection.execute(sa.text("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=:name)"),
                {"name": rollback_schema}).scalar_one())

    def test_migrations_create_local_knowledge_tables_without_changing_existing_public(self):
        with self.engine.connect() as connection:
            self.assertIn("knowledge_release_heads", sa.inspect(connection).get_table_names(schema=self.schema))
            self.assertIn("agent_run_contexts", sa.inspect(connection).get_table_names(schema=self.schema))
        self.assertEqual(public_knowledge_snapshot(), self.public_before)

    def test_sync_graph_persists_full_state_and_pending_writes_on_one_run(self):
        class State(TypedDict):
            text: str
            facts: list[dict]
        graph = StateGraph(State)
        graph.add_node("reply", lambda state: {"text": state["text"] + " Danke", "facts": [{"source": "customer"}]})
        graph.add_edge(START, "reply")
        graph.add_edge("reply", END)
        compiled = graph.compile(checkpointer=self.repo)
        result = compiled.invoke({"text": "Hello", "facts": []}, self.config, durability="sync")
        self.assertEqual(result, {"text": "Hello Danke", "facts": [{"source": "customer"}]})
        recreated = graph.compile(checkpointer=CheckpointRepository(self.engine, DEFAULT_WORKSPACE_ID, self.job))
        self.assertEqual(recreated.get_state(self.config).values, result)
        self.assertEqual(recreated.get_state(self.config).next, ())
        self.assertGreaterEqual(self.counts()[0], 3)
        self.assertGreater(self.counts()[2], 0)

    def test_graph_node_exception_keeps_original_failure_and_json_diagnostic(self):
        def fail(state):
            raise ValueError("explicit checkpoint node failure")
        graph = StateGraph(dict)
        graph.add_node("fail", fail)
        graph.add_edge(START, "fail")
        graph.add_edge("fail", END)
        with self.assertRaisesRegex(ValueError, "explicit checkpoint node failure"):
            graph.compile(checkpointer=self.repo).invoke({}, self.config, durability="sync")
        diagnostic = self.repo.get_tuple(self.config).pending_writes[0]
        self.assertEqual(diagnostic[1], "__error__")
        self.assertEqual(diagnostic[2], {"error_type": "ValueError", "code": "graph_node_failed"})

    def test_reads_writes_and_listing_cannot_cross_run_or_workspace(self):
        saved = self.save()
        foreign = {"configurable": {"thread_id": str(uuid4()), "checkpoint_ns": "", "checkpoint_id": "foreign"}}
        self.both_rejected(foreign)
        for method in (self.repo.get, self.repo.get_tuple, self.repo.list):
            with self.assertRaises(ServiceError):
                method(foreign)
        with self.assertRaises(ServiceError):
            self.repo.list(self.config, before=foreign)
        self.assertEqual(len(list(self.repo.list(None))), 1)
        for job, workspace in ((self.job, uuid4()), ({**self.job, "id": uuid4()}, DEFAULT_WORKSPACE_ID)):
            with self.assertRaises(ServiceError):
                CheckpointRepository(self.engine, workspace, job).get_tuple(saved)

    def test_both_sdk_writes_roll_back_when_failure_occurs_after_persistence(self):
        saved = self.save()
        for method in ("put", "put_writes"):
            baseline = self.counts()
            original = getattr(PostgresSaver, method)
            def fail(saver, *args, **kwargs):
                original(saver, *args, **kwargs)
                saver.conn.execute("UPDATE agent_runs SET outcome='must_rollback' WHERE id=%s", (self.rid,))
                raise RuntimeError("injected SDK crash after write")
            with self.subTest(method=method), patch.object(PostgresSaver, method, fail):
                with self.assertRaisesRegex(RuntimeError, "injected SDK crash"):
                    if method == "put":
                        self.save()
                    else:
                        self.repo.put_writes(saved, [("state", {"body": "pending"})], "must_rollback")
            self.assertEqual(self.counts(), baseline)
            self.assertIsNone(self.controls.get(self.rid)["run"]["outcome"])

    def test_put_and_pending_writes_hold_stop_lock_until_the_sdk_transaction_commits(self):
        for method in ("put", "put_writes"):
            if method == "put_writes":
                self.cid, self.rid = self.create("pending@example.test")
                self.job = self.leases.claim("pending_sdk_barrier")
                load_context(self.engine, self.service.store, DEFAULT_WORKSPACE_ID, self.job)
                self.repo = CheckpointRepository(self.engine, DEFAULT_WORKSPACE_ID, self.job)
                self.config = {"configurable": {"thread_id": str(self.rid), "checkpoint_ns": ""}}
            saved = self.save()
            baseline = self.counts()
            entered, resume, backend_pid = Event(), Event(), []
            original = getattr(PostgresSaver, method)
            def hold(saver, *args, **kwargs):
                result = original(saver, *args, **kwargs)
                backend_pid.append(saver.conn.info.backend_pid)
                entered.set()
                if not resume.wait(5):
                    raise AssertionError("Checkpoint barrier was not released")
                return result
            state = self.conversation(self.cid)
            with self.subTest(method=method), patch.object(PostgresSaver, method, hold), ThreadPoolExecutor(max_workers=2) as pool:
                writer = pool.submit(self.save if method == "put" else self.repo.put_writes,
                    *(() if method == "put" else (saved, [("state", {"body": "pending"})], "concurrent-task")))
                self.assertTrue(entered.wait(5))
                stop = pool.submit(self.controls.control, self.rid, "stop", Command(expected_version=state["row_version"]), uuid4().hex)
                try:
                    deadline, blocked = monotonic() + 3, False
                    while monotonic() < deadline:
                        with self.engine.connect() as connection:
                            blocked = connection.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                                "WHERE :pid=ANY(pg_blocking_pids(pid)))"), {"pid": backend_pid[0]}).scalar_one()
                        if blocked:
                            break
                        sleep(0.01)
                    self.assertTrue(blocked, "Stop must wait on the checkpoint's actual backend connection")
                    self.assertEqual(self.counts(), baseline, "SDK must not commit or use a second connection")
                    with self.engine.begin() as connection:
                        with self.assertRaises(sa.exc.OperationalError):
                            connection.execute(sa.select(agent_slots).where(agent_slots.c.workspace_id == DEFAULT_WORKSPACE_ID,
                                agent_slots.c.slot_key == "agent").with_for_update(nowait=True)).first()
                finally:
                    resume.set()
                writer.result(timeout=5)
                stop.result(timeout=5)
            committed = self.counts()
            self.both_rejected(saved)
            self.assertEqual(self.counts(), committed)

    def test_stop_first_and_new_input_reject_both_late_entrypoints(self):
        saved = self.save()
        state = self.conversation(self.cid)
        self.service.append(self.cid, AppendMessage(expected_version=state["row_version"], body="A newer input supersedes the graph."), uuid4().hex)
        self.both_rejected(saved)
        self.assertEqual(self.counts(), (1, 1, 0))

    def test_takeover_revokes_both_checkpoint_entrypoints(self):
        saved = self.save()
        state = self.conversation(self.cid)
        self.service.takeover(self.cid, Takeover(expected_version=state["row_version"]), uuid4().hex)
        self.both_rejected(saved)
        self.assertEqual(self.counts(), (1, 1, 0))

    def test_run_state_checkpoint_gate_and_lease_expiry_reject_both_writes(self):
        saved = self.save()
        for values in ({"status": "failed"}, {"status": "handed_off"}, {"stop_requested": True}, {"checkpoint_writable": False}):
            with self.subTest(values=values), self.engine.begin() as connection:
                connection.execute(agent_runs.update().where(agent_runs.c.id == self.rid).values(**values))
            self.both_rejected(saved)
            with self.engine.begin() as connection:
                connection.execute(agent_runs.update().where(agent_runs.c.id == self.rid)
                    .values(status="running", stop_requested=False, checkpoint_writable=True))
        with self.engine.begin() as connection:
            connection.execute(agent_slots.update().where(agent_slots.c.job_id == self.job["id"])
                .values(lease_expires_at=sa.func.now() - sa.text("interval '1 second'")))
        self.both_rejected(saved)
        self.assertEqual(self.counts(), (1, 1, 0))

    def test_knowledge_head_change_rejects_both_writes_with_pinned_context(self):
        saved = self.save()
        with self.engine.begin() as connection:
            connection.execute(knowledge_release_heads.update().values(epoch=knowledge_release_heads.c.epoch + 1))
        self.both_rejected(saved)
        self.assertEqual(self.counts(), (1, 1, 0))

    def test_completed_run_has_one_final_write_window_and_terminal_diagnostics(self):
        saved = self.save()
        with self.engine.begin() as connection:
            connection.execute(agent_runs.update().where(agent_runs.c.id == self.rid).values(status="completed"))
            connection.execute(jobs.update().where(jobs.c.id == self.job["id"]).values(status="completed"))
        final = self.save()
        self.repo.put_writes(final, [("state", {"body": "terminal"})], "terminal-task")
        with self.engine.begin() as connection:
            connection.execute(agent_runs.update().where(agent_runs.c.id == self.rid).values(checkpoint_writable=False))
        self.both_rejected(saved)
        self.assertEqual(self.repo.get_tuple(final).pending_writes, [("terminal-task", "state", {"body": "terminal"})])

    def test_old_branch_and_deleted_conversation_cannot_read_checkpoint_content(self):
        self.save()
        for values in ({"branch_generation": 2}, {"lifecycle": "deleting"}):
            with self.engine.begin() as connection:
                connection.execute(conversations.update().where(conversations.c.id == self.cid).values(**values))
            with self.assertRaises(ServiceError):
                self.repo.get_tuple(self.config)
            with self.assertRaises(ServiceError):
                self.repo.list(None)
            self.both_rejected(self.config)
            with self.engine.begin() as connection:
                connection.execute(conversations.update().where(conversations.c.id == self.cid).values(branch_generation=1, lifecycle="open"))

    def test_async_graph_is_explicitly_unsupported(self):
        with self.assertRaisesRegex(NotImplementedError, "synchronous graphs only"):
            asyncio.run(self.repo.aget_tuple(self.config))
