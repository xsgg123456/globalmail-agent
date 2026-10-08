"""Upgrade existing Phase 4 rows under a second disposable schema, never production."""
from pathlib import Path
from uuid import UUID, uuid4
from alembic import command
from alembic.config import Config
import sqlalchemy as sa
from globalmail_agent.adapters.object_store import ObjectStore
from globalmail_agent.application.conversations import ConversationService
from globalmail_agent.domain.conversation import CreateConversation
from globalmail_agent.knowledge.documents import DocumentService
from globalmail_agent.knowledge.commands import CreateDocument
from globalmail_agent.adapters.conversation_schema import jobs
from test_protocol import ProtocolFixture


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
        conversations = ConversationService(engine, store)
        original = conversations.create(CreateConversation(expected_version=0, sender_email="upgrade@example.test", body="Existing user test message"), uuid4().hex)
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
