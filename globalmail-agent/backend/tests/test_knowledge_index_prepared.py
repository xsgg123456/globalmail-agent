"""Fixed real prepared SOP/case bytes, parsed in actual local children under a private schema."""
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_schema import documents, document_versions
from globalmail_agent.adapters.knowledge_index_schema import index_parents, index_chunks
from globalmail_agent.adapters.conversation_schema import jobs
from globalmail_agent.knowledge.prepared import PreparedImport
from globalmail_agent.knowledge.commands import Command, ReviewCommand
from globalmail_agent.knowledge.chunking import proxy_tokens
from index_helpers import IndexFixture


class PreparedIndexTests(IndexFixture):
    def test_all_eight_fixed_sops_and_five_cases_keep_complete_single_parent_and_child(self):
        PreparedImport(self.engine, self.store).importing(Command(expected_version=0), uuid4().hex)
        with self.engine.begin() as conn:
            rows = conn.execute(sa.select(document_versions.c.id, documents.c.prepared_id)
                .join(documents, documents.c.id == document_versions.c.document_id)
                .where(documents.c.document_type.in_(["troubleshooting_md", "case_md"]))).all()
            allowed = [r[0] for r in rows]
            conn.execute(jobs.update().where(jobs.c.knowledge_version_id.not_in(allowed))
                .values(not_before=sa.func.now() + sa.text("interval '1 day'")))
        self.assertEqual(len(rows), 13)
        for _ in rows:
            job = self.runner.jobs.claim(self.runner.owner)
            self.assertIsNotNone(job)
            self.runner.execute(job)
            self.reviews.review(job["version_id"], ReviewCommand.model_validate(self.review_payload(job["version_id"])), uuid4().hex)
        for vid, prepared_id in rows:
            result = self.build(vid)
            with self.engine.connect() as conn:
                parents = conn.execute(sa.select(index_parents).where(index_parents.c.build_id == UUID(result["build_id"]))).mappings().all()
                children = conn.execute(sa.select(index_chunks).where(index_chunks.c.build_id == UUID(result["build_id"]))).mappings().all()
            self.assertEqual(len(parents), 1, prepared_id)
            self.assertEqual(len(children), 1, prepared_id)
            self.assertLessEqual(parents[0]["proxy_tokens"], 2000, prepared_id)
            self.assertLessEqual(proxy_tokens(children[0]["input_text"]), 2500, prepared_id)
            parsed = self.queries.version_detail(vid)["blocks"]
            self.assertTrue(all(block["text"].strip() in parents[0]["text"] for block in parsed), prepared_id)
