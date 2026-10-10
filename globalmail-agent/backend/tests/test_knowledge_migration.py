"""Upgrade existing Phase 4 rows under a second disposable schema, never production."""
from pathlib import Path
from datetime import datetime, timezone
from uuid import UUID, uuid4
from alembic import command
from alembic.config import Config
import sqlalchemy as sa
from globalmail_agent.adapters.object_store import ObjectStore
from globalmail_agent.application.conversations import ConversationService
from globalmail_agent.adapters.body_store import BodyWriter
from globalmail_agent.application.event_store import record_event
from globalmail_agent.application.task_queue import enqueue
from globalmail_agent.knowledge.documents import DocumentService
from globalmail_agent.knowledge.commands import CreateDocument
from globalmail_agent.adapters.conversation_schema import jobs
from test_protocol import ProtocolFixture
from legacy_migration_fixture import LegacyConversations, legacy_enqueue


class KnowledgeMigrationTests(ProtocolFixture):
    def test_upgrade_keeps_existing_real_agent_jobs_and_accepts_knowledge_without_conversation(self):
        temporary_schema = "test_knowledge_upgrade_" + uuid4().hex
        with self.admin.begin() as conn:
            conn.execute(sa.text(f'CREATE SCHEMA "{temporary_schema}"'))
        def cleanup():
            with self.admin.begin() as conn:
                conn.execute(sa.text(f'DROP SCHEMA "{temporary_schema}" CASCADE'))
        self.addCleanup(cleanup)
        engine = sa.create_engine(self.admin.url, hide_parameters=True,
            connect_args={"options": f"-csearch_path={temporary_schema}"})
        self.addCleanup(engine.dispose)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "0003_business_catalog")
        store = ObjectStore(Path(self.temp.name), engine)
        conversations = LegacyConversations(engine, store)
        # Seed the old schema with its message/event/job contract, before current services require head.
        with BodyWriter(store) as writer, engine.begin() as conn:
            conv = conversations.new_conversation(conn, "upgrade@example.test", "simulation", "", True, "manual")
            message = conversations.add_message(conn, writer, conv, "Existing user test message", "",
                "customer", "manual", uuid4().hex, datetime.now(timezone.utc))
            conversations.update(conn, conv, visible_message_seq=message["seq"],
                received_seq=message["received_seq"], input_revision=1)
            event = record_event(conn, conv, "message", str(message["id"]),
                "customer_message.accepted", {"message_id": str(message["id"])})
            original = {"conversation_id": str(conv["id"]), **legacy_enqueue(conn, conv, event)}
        with engine.connect() as conn:
            existing = conn.execute(sa.select(jobs.c.id, jobs.c.run_id, jobs.c.cycle_id, jobs.c.conversation_id)).one()
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
        with engine.connect() as conn:
            preserved = conn.execute(sa.select(jobs)).mappings().one()
            self.assertEqual((preserved["id"], preserved["run_id"], preserved["cycle_id"], preserved["conversation_id"]), tuple(existing))
            self.assertIsNone(preserved["knowledge_version_id"])
        docs = DocumentService(engine, store)
        result = docs.create(CreateDocument(expected_version=0, title="升级后知识", document_type="case_md", brand="OUTON",
            source_reference="合成升级验证", available_at="2026-10-08T00:00:00Z", content="原资料不可变。",
            applicabilities=[{"section_id": "document", "sku": "H-CTD16-US-BK", "basis": "隔离测试"}]), uuid4().hex)
        self.assertTrue(result["version_id"])
        self.assertEqual(len(conversations.detail(UUID(original["conversation_id"]))["messages"]), 1)
