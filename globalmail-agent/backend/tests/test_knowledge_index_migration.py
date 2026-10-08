"""Phase 5 preservation and new scoped FK/immutability checks in disposable PostgreSQL."""
from pathlib import Path
from uuid import UUID, uuid4
from alembic import command
from alembic.config import Config
import sqlalchemy as sa
from globalmail_agent.knowledge.base import scope, sha
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
from globalmail_agent.adapters.knowledge_index_schema import index_builds, index_parents, index_chunks
from sqlalchemy.exc import IntegrityError
from test_protocol import ProtocolFixture


class IndexMigrationTests(ProtocolFixture):
    def test_phase5_original_reviewed_version_and_existing_parse_job_are_preserved(self):
        namespace = "test_index_upgrade_" + uuid4().hex
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
            command.upgrade(config, "0004_knowledge_content")
            reflected = sa.MetaData()
            reflected.reflect(conn)
            did, vid, oid, jid = uuid4(), uuid4(), uuid4(), uuid4()
            scoped = scope(DEFAULT_WORKSPACE_ID)
            digest = sha("现有用户原件字节".encode())
            conn.execute(reflected.tables["objects"].insert().values(id=oid, **scoped, sha256=digest, size_bytes=24,
                source_kind="user_provided_simulation_knowledge", source_ref="existing_private_test_original"))
            conn.execute(reflected.tables["documents"].insert().values(id=did, **scoped, title="既有核对资料", document_type="case_md", brand="OUTON",
                source_kind="user_provided_simulation_knowledge", source_reference="existing_test", allowed_modes=["simulation"], usage_split="rag"))
            conn.execute(reflected.tables["document_versions"].insert().values(id=vid, **scoped, document_id=did, number=1, title="既有核对资料",
                object_id=oid, format="md", source_sha256=digest, available_at="2026-10-08T00:00:00Z", applicability_sha256="a" * 64,
                parser_profile_id="markdown", parser_fingerprint="b" * 64, status="reviewed", parse_generation=1, parse_sha256="c" * 64))
            conn.execute(reflected.tables["documents"].update().where(reflected.tables["documents"].c.id == did).values(current_version_id=vid))
            conn.execute(reflected.tables["jobs"].insert().values(id=jid, **scoped, kind="knowledge", status="completed", attempt_no=1,
                knowledge_version_id=vid, parser_profile_id="markdown", parse_generation=1, document_fence=1, stage="needs_review"))
            before = {name: dict(conn.execute(sa.select(reflected.tables[name])).mappings().one()) for name in ("objects", "documents", "document_versions", "jobs")}
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            after_meta = sa.MetaData()
            after_meta.reflect(conn)
            for name, row in before.items():
                after = conn.execute(sa.select(after_meta.tables[name])).mappings().one()
                self.assertEqual({k: after[k] for k in row}, row, name)
            doc = conn.execute(sa.select(after_meta.tables["documents"])).mappings().one()
            job = conn.execute(sa.select(after_meta.tables["jobs"])).mappings().one()
            self.assertEqual(doc["revocation_epoch"], 0)
            self.assertFalse(doc["withdrawn"])
            self.assertEqual(job["knowledge_operation"], "parse")
            self.assertIsNone(job["index_build_id"])
