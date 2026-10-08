"""Real PDF replacement and logical-range regression, through PG and HTTP."""
from uuid import UUID
from knowledge_helpers import KnowledgeFixture, pdf_bytes, parsed


class ReplacementTests(KnowledgeFixture):
    def test_expiry_during_artifact_save_rolls_back_files_cache_and_projection(self):
        from unittest.mock import patch
        import sqlalchemy as sa
        from globalmail_agent.knowledge import jobs as knowledge_jobs
        from globalmail_agent.adapters.conversation_schema import agent_slots
        from globalmail_agent.adapters.knowledge_schema import parse_caches
        from globalmail_agent.application.conversation_lock import ServiceError
        did, vid, _ = self.markdown()
        job = self.start_parse(vid)
        project = knowledge_jobs.project
        def expire(conn, *args):
            digest = project(conn, *args)
            conn.execute(agent_slots.update().where(agent_slots.c.slot_key == "knowledge")
                .values(lease_expires_at=sa.func.clock_timestamp() - sa.text("interval '1 second'")))
            return digest
        with patch.object(knowledge_jobs, "project", side_effect=expire):
            with self.assertRaises(ServiceError): self.knowledge.complete(job, parsed(job))
        self.assertEqual(self.count(parse_caches), 0)
        self.assertEqual(len(list(self.store.root.iterdir())), 1)
        self.assertEqual(self.queries.version_detail(vid)["version"]["status"], "parsing")

    def upload_pdf(self, pages):
        from uuid import uuid4
        result = self.client.post("/api/v1/knowledge/uploads?filename=new.pdf", content=pdf_bytes(pages),
            headers={"Origin": "http://127.0.0.1:15173", "Content-Type": "application/octet-stream", "Idempotency-Key": uuid4().hex})
        self.assertEqual(result.status_code, 202, result.text)
        return result.json()["data"]["object_id"]

    def create_pdf(self, count):
        did, vid, payload = self.markdown()
        payload.update(title="替换测试原件", document_type="manual_pdf", object_id=self.upload_pdf(count),
            applicabilities=[{"section_id": "document", "sku": "H-CTD16-US-BK", "page_start": 1, "page_end": count, "basis": "测试原件明确适用"}])
        payload.pop("content")
        result = self.post("/knowledge/documents", payload)
        self.assertEqual(result.status_code, 202, result.text)
        return result.json()["data"], payload

    def test_pdf_growth_and_shrinkage_use_new_source_pages_and_keep_old_bytes(self):
        for old_count, new_count in ((1, 2), (2, 1)):
            created, payload = self.create_pdf(old_count)
            did, old = created["document_id"], created["version_id"]
            prior = self.queries.version_detail(UUID(old))
            body = {"expected_version": 1, "object_id": self.upload_pdf(new_count),
                "applicabilities": [{**payload["applicabilities"][0], "page_end": new_count}]}
            result = self.post(f"/knowledge/documents/{did}/versions", body)
            self.assertEqual(result.status_code, 202, result.text)
            identity = UUID(result.json()["data"]["version_id"])
            current = self.queries.version_detail(identity)
            self.assertEqual(current["version"]["page_range"], [1, new_count])
            self.assertEqual(self.queries.version_detail(UUID(old))["version"]["page_range"], prior["version"]["page_range"])
            job = self.start_parse(identity, "mineru_basic")
            self.assertTrue(self.knowledge.complete(job, parsed(job, new_count)))
            projected = self.queries.version_detail(identity)
            self.assertEqual({block["page"] for block in projected["blocks"]}, set(range(1, new_count + 1)))

    def test_explicit_logical_range_is_bounded_and_changes_applicability_digest(self):
        created, payload = self.create_pdf(3)
        body = {"expected_version": 1, "page_range": [2, 3],
                "applicabilities": [{**payload["applicabilities"][0], "page_start": 2}]}
        path = f"/knowledge/documents/{created['document_id']}/versions"
        self.assertEqual(self.post(path, {**body, "page_range": [2, 4]}).status_code, 422)
        self.assertEqual(self.post(path, {**body, "page_range": [True, 3]}).status_code, 422)
        result = self.post(path, body)
        self.assertEqual(result.status_code, 202, result.text)
        current = self.queries.version_detail(UUID(result.json()["data"]["version_id"]))
        self.assertEqual(current["version"]["page_range"], [2, 3])
        self.assertTrue(current["diff"]["applicability_changed"])

    def test_prepared_shared_pdf_can_be_replaced_without_old_physical_page_numbers(self):
        import sqlalchemy as sa
        from globalmail_agent.adapters.knowledge_schema import documents
        self.post("/knowledge/prepared-import", {"expected_version": 0})
        with self.engine.connect() as conn:
            row = conn.execute(sa.select(documents).where(documents.c.prepared_id == "MAN-OUTON-01")).mappings().one()
        old = self.queries.version_detail(row["current_version_id"])
        self.assertGreater(old["version"]["page_range"][0], 1)
        invalid = {"expected_version": 1, "page_range": [1, 17], "applicabilities": old["applicabilities"]}
        self.assertEqual(self.post(f"/knowledge/documents/{row['id']}/versions", invalid).status_code, 422)
        body = {"expected_version": 1, "object_id": self.upload_pdf(2), "page_range": [1, 2],
            "applicabilities": [{**binding, "page_start": 1, "page_end": 2} for binding in old["applicabilities"]]}
        result = self.post(f"/knowledge/documents/{row['id']}/versions", body)
        self.assertEqual(result.status_code, 202, result.text)
        current = self.queries.version_detail(UUID(result.json()["data"]["version_id"]))
        self.assertEqual(current["version"]["page_range"], [1, 2])
