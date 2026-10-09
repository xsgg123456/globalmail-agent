"""Frozen additive upgrade and actual composite constraints preserve preexisting records."""
from pathlib import Path
from uuid import uuid4
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
            command.upgrade(config, "0007_visual_evidence")
        service = FixtureConversations(engine, ObjectStore(Path(self.temp.name), engine))
        service.create("BASE-OUTON-04", Command(expected_version=0), uuid4().hex)
        with engine.begin() as conn:
            old = sa.MetaData()
            old.reflect(conn)
            before = {name: [dict(r) for r in conn.execute(sa.select(table)).mappings()]
                for name, table in old.tables.items() if name != "alembic_version"}
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            current = sa.MetaData()
            current.reflect(conn)
            for name, rows in before.items():
                keys = [column.name for column in old.tables[name].primary_key]
                identity = lambda row: tuple(row[key] for key in keys)
                now = {identity(r): r for r in conn.execute(sa.select(current.tables[name])).mappings()}
                self.assertEqual([{k: now[identity(r)][k] for k in r} for r in rows], rows, name)
            self.assertEqual(conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one(), "0008_after_sales_ledger")
        source = Path(__file__).resolve().parents[1] / "migrations/versions/0008_after_sales_ledger.py"
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
