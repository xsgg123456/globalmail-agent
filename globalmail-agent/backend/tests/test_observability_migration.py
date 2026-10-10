"""Incremental schema preservation and composite export-buffer scope, on isolated PG."""
import importlib.util
from pathlib import Path
from uuid import uuid4
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from alembic import command
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from alembic.config import Config
from agent_fixture import AgentFixture, ScriptedModel, understanding, terminal
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import conversations
from globalmail_agent.adapters.body_store import BodyWriter


class ObservationMigrationTests(AgentFixture):
    def test_upgrade_preserves_all_business_records_and_old_trace_ids(self):
        cid, rid = self.create_mail()
        self.execute(ScriptedModel(understanding, terminal()))
        additions = ("reason_code", "export_object_id", "generation", "attempts", "pending_count")
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with self.engine.begin() as conn:
            for name in ("trace_export_object_scope",):
                conn.execute(sa.text(f'ALTER TABLE trace_correlations DROP CONSTRAINT "{name}"'))
            for name in additions:
                conn.execute(sa.text(f'ALTER TABLE trace_correlations DROP COLUMN "{name}"'))
            conn.execute(sa.text("UPDATE alembic_version SET version_num='0010_human_assistance'"))
            legacy = sa.MetaData()
            names = ("conversations", "messages", "agent_runs", "jobs", "usage_records", "reply_artifacts", "objects", "trace_correlations")
            tables = {name: sa.Table(name, legacy, autoload_with=conn) for name in names}
            before = {name: [dict(row) for row in conn.execute(sa.select(table)).mappings()] for name, table in tables.items()}
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.upgrade(config, "head")
            for name, rows in before.items():
                latest = {row["id"]: row for row in conn.execute(sa.select(tables[name])).mappings()}
                self.assertEqual(rows, [{key: latest[row["id"]][key] for key in row} for row in rows], name)
            self.assertEqual(conn.execute(sa.select(a.trace_correlations.c.trace_id).where(a.trace_correlations.c.run_id == rid)).scalar_one(),
                before["trace_correlations"][0]["trace_id"])
            path = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0011_observability.py"
            spec = importlib.util.spec_from_file_location("observation_migration", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with Operations.context(MigrationContext.configure(conn)):
                module.upgrade()  # Explicit idempotent DDL, not only Alembic's revision skip.

    def test_export_object_cannot_be_bound_to_another_customer_scope(self):
        cid, rid = self.create_mail(email="first-buffer@example.test")
        self.execute(ScriptedModel(understanding, terminal()))
        other, _ = self.create_mail(email="second-buffer@example.test")
        with BodyWriter(self.store) as writer, self.engine.begin() as conn:
            conv = conn.execute(sa.select(conversations).where(conversations.c.id == other)).mappings().one()
            outsider = writer.put(conn, conv, "{}", "observability_buffer")
        with self.assertRaises(IntegrityError), self.engine.begin() as conn:
            conn.execute(a.trace_correlations.update().where(a.trace_correlations.c.run_id == rid).values(export_object_id=outsider))
