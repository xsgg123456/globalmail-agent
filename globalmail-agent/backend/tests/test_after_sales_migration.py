"""Frozen additive upgrade and actual composite constraints preserve preexisting records."""
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from legacy_migration_fixture import LegacyScenarios, legacy_enqueue
from alembic import command
from alembic.config import Config
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from after_sales_fixture import AfterSalesFixture
from test_protocol import ProtocolFixture
from globalmail_agent.adapters import after_sales_schema as a, business_schema as b
from globalmail_agent.adapters.object_store import ObjectStore
from globalmail_agent.application.fixture_conversations import FixtureConversations
from globalmail_agent.domain.conversation import Command


class AfterSalesMigrationTests(ProtocolFixture):
    def test_0007_existing_business_rows_and_sources_survive_additive_0008(self):
        self.preserve_upgrade("0007_visual_evidence", "0008_after_sales_ledger")

    def test_0008_existing_rows_and_sources_survive_repeat_additive_0009(self):
        self.preserve_upgrade("0008_after_sales_ledger", "0009_business_waits")

    def preserve_upgrade(self, start, end):
        namespace = "test_after_sales_upgrade_" + uuid4().hex
        with self.admin.begin() as conn:
            conn.execute(sa.text(f'CREATE SCHEMA "{namespace}"'))
        def cleanup():
            with self.admin.begin() as conn:
                conn.execute(sa.text(f'DROP SCHEMA "{namespace}" CASCADE'))
        self.addCleanup(cleanup)
        engine = sa.create_engine(self.admin.url, hide_parameters=True, connect_args={"options": f"-csearch_path={namespace}"})
        self.addCleanup(engine.dispose)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, start)
        service = LegacyScenarios(engine, ObjectStore(Path(self.temp.name), engine))
        with patch("globalmail_agent.application.conversation_base.enqueue", legacy_enqueue):
            service.create("BASE-OUTON-04", Command(expected_version=0), uuid4().hex)
        with engine.begin() as conn:
            old = sa.MetaData()
            old.reflect(conn)
            before = {name: [dict(r) for r in conn.execute(sa.select(table)).mappings()]
                for name, table in old.tables.items() if name != "alembic_version"}
            config.attributes["connection"] = conn
            command.upgrade(config, end)
            command.upgrade(config, end)
            current = sa.MetaData()
            current.reflect(conn)
            for name, rows in before.items():
                keys = [column.name for column in old.tables[name].primary_key]
                identity = lambda row: tuple(row[key] for key in keys)
                now = {identity(r): r for r in conn.execute(sa.select(current.tables[name])).mappings()}
                self.assertEqual([{k: now[identity(r)][k] for k in r} for r in rows], rows, name)
            self.assertEqual(conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one(), end)
        source = Path(__file__).resolve().parents[1] / ("migrations/versions/" + end + ".py")
        self.assertNotIn("from globalmail_agent", source.read_text(encoding="utf-8"))


class AfterSalesConstraintTests(AfterSalesFixture):
    def test_reservation_scope_and_operation_line_cannot_be_forged(self):
        self.publish_policy()
        cid, context, request = self.prepared()
        self.create_operation(cid, context, request)
        other, _, _ = self.prepared()
        with self.engine.connect() as conn:
            old = dict(conn.execute(sa.select(a.compensation_reservations)).mappings().one())
            foreign = conn.execute(sa.select(b.branch_order_lines).where(b.branch_order_lines.c.branch_id != old["branch_id"])).mappings().one()
        values = {k: v for k, v in old.items() if k not in {"created_at", "updated_at"}}
        values.update(id=uuid4(), unit_id="forged", order_line_id=foreign["id"])
        with self.assertRaises(IntegrityError), self.engine.begin() as conn:
            conn.execute(sa.insert(a.compensation_reservations).values(**values))
