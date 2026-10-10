"""Phase 7 preservation, frozen visual DDL and real scoped FK enforcement."""
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime, timezone
from alembic import command
from alembic.config import Config
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from globalmail_agent.adapters.object_store import ObjectStore
from globalmail_agent.adapters.body_store import BodyWriter
from globalmail_agent.adapters.attachment_schema import message_attachments, visual_evidence
from globalmail_agent.adapters.conversation_schema import messages
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.conversations import ConversationService
from test_attachment_intake import AttachmentFixture
from legacy_migration_fixture import LegacyConversations


class AttachmentMigrationTests(AttachmentFixture):
    def test_phase7_rows_preserved_and_budget_counter_defaults_to_zero(self):
        namespace = "test_visual_upgrade_" + uuid4().hex
        with self.admin.begin() as conn:
            conn.execute(sa.text(f'CREATE SCHEMA "{namespace}"'))
        def cleanup():
            with self.admin.begin() as conn:
                conn.execute(sa.text(f'DROP SCHEMA "{namespace}" CASCADE'))
        self.addCleanup(cleanup)
        engine = sa.create_engine(self.admin.url, hide_parameters=True,
            connect_args={"options": f"-csearch_path={namespace}"})
        self.addCleanup(engine.dispose)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "0006_agent_results")
        service = LegacyConversations(engine, ObjectStore(Path(self.temp.name), engine))
        # Seed Phase 7's exact shape without running Phase 8 acceptance/read guards
        # against a database which intentionally has not acquired the visual tables.
        with BodyWriter(service.store) as writer, engine.begin() as conn:
            conversation = service.new_conversation(conn, "old@example.test", "simulation", "Existing", True, "manual")
            message = service.add_message(conn, writer, conversation, "原有邮件正文", "Existing", "customer",
                "manual", uuid4().hex, datetime.now(timezone.utc))
            service.update(conn, conversation, visible_message_seq=1, received_seq=1, input_revision=1)
            old = sa.MetaData()
            old.reflect(conn)
            cid, run_id, trigger_id = uuid4(), uuid4(), uuid4()
            scope = {k: conversation[k] for k in SCOPE_KEYS}
            fences = {"input_revision": 1, "authority_epoch": 0, "branch_generation": 1}
            conn.execute(old.tables["processing_cycles"].insert().values(id=cid, **scope, **fences,
                conversation_id=conversation["id"], trigger_id=trigger_id, trigger_message_id=message["id"], state="queued"))
            conn.execute(old.tables["agent_runs"].insert().values(id=run_id, **scope, **fences,
                conversation_id=conversation["id"], processing_cycle_id=cid, trigger_id=trigger_id, attempt_no=1, status="queued"))
            cycle = conn.execute(sa.select(old.tables["processing_cycles"])).mappings().one()
            conn.execute(old.tables["cycle_budgets"].insert().values(id=uuid4(),
                **{k: cycle[k] for k in SCOPE_KEYS}, conversation_id=cycle["conversation_id"], cycle_id=cycle["id"],
                model_requests=2, tool_calls=3, reserved_tokens=1000, input_tokens=600, output_tokens=200,
                unknown_requests=1, active_ms=1234))
            before = {name: [dict(r) for r in conn.execute(sa.select(old.tables[name])).mappings()] for name in
                ("objects", "messages", "conversations", "agent_runs", "processing_cycles", "cycle_budgets")}
            config.attributes["connection"] = conn
            command.upgrade(config, "0009_business_waits")
            current = sa.MetaData()
            current.reflect(conn)
            for name, rows in before.items():
                new = {r["id"]: r for r in conn.execute(sa.select(current.tables[name])).mappings()}
                self.assertEqual([{key: new[row["id"]][key] for key in row} for row in rows], rows, name)
            budget = conn.execute(sa.select(current.tables["cycle_budgets"])).mappings().one()
            self.assertEqual(budget["image_views"], 0)
            self.assertTrue({"message_attachments", "visual_analyses", "visual_evidence"} <= set(current.tables))
        with self.assertRaises(IntegrityError), engine.begin() as conn:
            conn.execute(sa.text("UPDATE cycle_budgets SET image_views = 7"))
        snapshot = Path(__file__).resolve().parents[1] / "migrations/versions/0007_visual_evidence.py"
        self.assertNotIn("from globalmail_agent", snapshot.read_text(encoding="utf-8"))

    def test_attachment_scope_and_evidence_conversation_composite_fks_reject_forgery(self):
        cid, _ = self.create()
        other, _ = self.create("foreign@example.test")
        source = self.stage(cid)
        aid = UUID(source["attachment_id"])
        with self.engine.connect() as conn:
            row = dict(conn.execute(sa.select(message_attachments).where(message_attachments.c.id == aid)).mappings().one())
        values = {key: value for key, value in row.items() if key not in {"created_at", "updated_at"}}
        values.update(id=uuid4(), conversation_id=other)
        with self.assertRaises(IntegrityError), self.engine.begin() as conn:
            conn.execute(message_attachments.insert().values(**values))
        values.update(id=uuid4(), conversation_id=cid, purpose="knowledge")
        with self.assertRaises(IntegrityError), self.engine.begin() as conn:
            conn.execute(message_attachments.insert().values(**values))
        with self.engine.begin() as conn:
            other_row = self.service.lock(conn, other)
            other_message = conn.execute(sa.select(messages).where(messages.c.conversation_id == other)).mappings().one()
        with self.assertRaises(IntegrityError), self.engine.begin() as conn:
            conn.execute(visual_evidence.insert().values(id=uuid4(), **{k: other_row[k] for k in SCOPE_KEYS},
                conversation_id=other, attachment_id=aid, message_id=other_message["id"], revision=0, evidence_epoch=0,
                kind="manual_correction", manual=True, body_object_id=other_message["body_object_id"],
                source_sha256=row["source_sha256"]))
