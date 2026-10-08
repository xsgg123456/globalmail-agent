"""Real PG fence/lease/cancel/retry/review behavior with synthetic parser contract results."""
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.conversation_schema import jobs, agent_slots, conversations
from globalmail_agent.adapters.knowledge_schema import blocks, parse_caches, knowledge_reviews, document_versions, documents
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.commands import Command, VersionCommand, ReviewCommand
from knowledge_helpers import KnowledgeFixture, parsed


class KnowledgeJobTests(KnowledgeFixture):
    def test_knowledge_has_no_fake_conversation_and_agent_slot_remains_independent(self):
        cid, run = self.create()
        did, vid, payload = self.markdown()
        job = self.start_parse(vid)
        self.assertIsNone(job["conversation_id"])
        self.assertIsNone(job["run_id"])
        self.assertIsNone(job["cycle_id"])
        self.assertEqual(self.count(conversations), 1)
        agent = self.leases.claim("agent_worker")
        self.assertIsNotNone(agent)
        self.assertTrue(self.knowledge.heartbeat(job, job["lease_owner"], job["slot_fence"]))
        self.assertTrue(self.knowledge.complete(job, parsed(job)))
        for _ in range(3):
            self.client.get(f"/api/v1/knowledge/versions/{vid}")
            self.client.get(f"/api/v1/jobs/{job['id']}")
        self.assertEqual(self.count(jobs), 2)
        with self.engine.connect() as conn:
            slot = conn.execute(sa.select(agent_slots).where(agent_slots.c.slot_key == "agent")).mappings().one()
            self.assertEqual(slot["job_id"], agent["id"])

    def test_two_concurrent_claims_are_single_slot(self):
        first, vid, payload = self.markdown()
        from globalmail_agent.knowledge.commands import ParseCommand
        self.knowledge.enqueue(vid, ParseCommand(expected_version=1, parser_profile_id="markdown"), uuid4().hex)
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(self.knowledge.claim, ["worker_a", "worker_b"]))
        self.assertEqual(sum(job is not None for job in claims), 1)

    def test_document_deletion_fence_blocks_late_effects_and_recovery(self):
        did, vid, payload = self.markdown()
        job = self.start_parse(vid)
        with self.engine.begin() as conn:
            conn.execute(documents.update().where(documents.c.id == did).values(lifecycle="deleting", document_fence=2))
        self.assertFalse(self.knowledge.complete(job, parsed(job)))
        self.assertFalse(self.knowledge.heartbeat(job, job["lease_owner"], job["slot_fence"]))
        self.assertEqual(self.knowledge.recover_expired(restart=True), [job["id"]])
        self.assertEqual(self.count(parse_caches), 0)
        self.assertEqual(self.count(blocks), 0)
        with self.engine.connect() as conn:
            self.assertEqual(self.knowledge._job(conn, job["id"])["status"], "cancelled")

    def test_cancel_unknown_retry_and_late_completion_are_fenced(self):
        did, vid, payload = self.markdown()
        job = self.start_parse(vid)
        current = self.client.get(f"/api/v1/jobs/{job['id']}").json()["data"]["job"]
        key = uuid4().hex
        cancel = {"expected_version": current["row_version"]}
        first = self.post(f"/jobs/{job['id']}/cancel", cancel, key)
        self.assertEqual(first.status_code, 202, first.text)
        again = self.post(f"/jobs/{job['id']}/cancel", cancel, key)
        self.assertEqual(first.json()["data"], again.json()["data"])
        self.assertFalse(self.knowledge.complete(job, parsed(job)))
        self.assertFalse(self.knowledge.heartbeat(job, job["lease_owner"], job["slot_fence"]))
        self.assertEqual(self.count(blocks), 0)
        row = first.json()["data"]["job"]
        retry = self.post(f"/jobs/{job['id']}/retry", {"expected_version": row["row_version"]})
        self.assertEqual(retry.status_code, 202, retry.text)
        next_job = self.knowledge.claim("new_worker")
        self.assertGreater(next_job["slot_fence"], job["slot_fence"])
        self.assertTrue(self.knowledge.complete(next_job, parsed(next_job)))

    def test_new_version_cancels_old_parser_and_old_tasks_cannot_write(self):
        did, vid, payload = self.markdown()
        job = self.start_parse(vid)
        changed = self.docs.revise(did, VersionCommand(expected_version=1, content="新版内容", applicabilities=payload["applicabilities"]), uuid4().hex)
        self.assertFalse(self.knowledge.complete(job, parsed(job)))
        self.assertFalse(self.knowledge.fail(job, "late_provider_error", True))
        self.assertEqual(self.count(parse_caches), 0)
        self.assertEqual(self.queries.version_detail(vid)["version"]["status"], "cancelled")
        self.assertEqual(self.queries.detail(did)["document"]["current_version_id"], UUID(changed["version_id"]))
        stale = self.post(f"/jobs/{job['id']}/retry", {"expected_version": self.knowledge.get(job["id"])["job"]["row_version"]})
        self.assertEqual(stale.status_code, 409)

    def test_expired_lease_recovery_and_bounded_three_automatic_retries(self):
        did, vid, payload = self.markdown()
        original = self.start_parse(vid)
        with self.engine.begin() as conn:
            conn.execute(agent_slots.update().where(agent_slots.c.job_id == original["id"])
                .values(lease_expires_at=sa.func.now() - sa.text("interval '1 second'")))
        self.assertFalse(self.knowledge.complete(original, parsed(original)))
        self.assertEqual(self.knowledge.recover_expired(), [original["id"]])
        for attempt in (2, 3, 4):
            with self.engine.begin() as conn:
                conn.execute(jobs.update().where(jobs.c.id == original["id"]).values(not_before=sa.func.now() - sa.text("interval '1 second'")))
            job = self.knowledge.claim("retry_worker")
            self.assertEqual(job["attempt_no"], attempt)
            self.assertTrue(self.knowledge.fail(job, "provider_timeout", True))
        result = self.knowledge.get(original["id"])["job"]
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["attempt_no"], 4)
        self.assertTrue(result["retryable"])
        self.assertIsNone(self.knowledge.claim("finished_retry_worker"))
        self.assertEqual(self.queries.version_detail(vid)["version"]["status"], "failed")

    def test_review_requires_all_digests_and_reparse_invalidates_previous_review(self):
        did, vid, payload = self.markdown()
        job = self.start_parse(vid)
        premature = self.post(f"/knowledge/versions/{vid}/review", {"expected_version": 2,
            "source_sha256": job["source_sha256"], "parse_sha256": "0" * 64, "applicability_sha256": "0" * 64, "note": "premature"})
        self.assertEqual(premature.status_code, 409)
        self.assertTrue(self.knowledge.complete(job, parsed(job)))
        wrong = self.post(f"/knowledge/versions/{vid}/review", self.review_payload(vid, source_sha256="0" * 64))
        self.assertEqual(wrong.status_code, 409)
        reviewed = self.post(f"/knowledge/versions/{vid}/review", self.review_payload(vid))
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(reviewed.json()["data"]["status"], "reviewed")
        self.assertFalse(reviewed.json()["data"]["published"])
        replacement = self.start_parse(vid)
        self.assertIsNone(self.queries.version_detail(vid)["review"])
        cache_token = self.knowledge.cached_result(replacement)
        self.assertIsNotNone(cache_token)
        self.assertTrue(self.knowledge.complete(replacement, cache_token))
        self.assertEqual(self.count(parse_caches), 1)
        self.assertEqual(self.count(knowledge_reviews), 1)
        self.assertEqual(self.queries.version_detail(vid)["version"]["status"], "needs_review")
        late_review = self.post(f"/knowledge/versions/{vid}/review", self.review_payload(vid, expected_version=3))
        self.assertEqual(late_review.status_code, 409)

    def test_critical_image_excludes_its_entire_section_and_missing_pages_never_pass(self):
        did, vid, payload = self.markdown()
        job = self.start_parse(vid)
        result = parsed(job, diagnostics=[{"code": "markdown_image_not_loaded", "severity": "error", "page": None,
            "block_ids": ["figure"], "asset_ids": [], "message": "操作图缺失", "blocks_review": True}])
        result["blocks"] = [
            {"id": "figure", "page": None, "section_id": "assembly", "type": "figure", "text": "接线图", "asset_ids": []},
            {"id": "step", "page": None, "section_id": "assembly", "type": "paragraph", "text": "按图接线", "asset_ids": []},
            {"id": "unrelated", "page": None, "section_id": "other", "type": "paragraph", "text": "停止并交人工", "asset_ids": []}]
        self.assertTrue(self.knowledge.complete(job, result))
        reject = self.post(f"/knowledge/versions/{vid}/review", self.review_payload(vid, excluded_block_ids=["figure"], exclusion_reason="原图缺失"))
        self.assertEqual(reject.status_code, 409)
        accepted = self.post(f"/knowledge/versions/{vid}/review", self.review_payload(vid, excluded_block_ids=["figure", "step"], exclusion_reason="此整段接线内容缺操作图，暂不采用"))
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(self.queries.version_detail(vid)["review"]["excluded_block_ids"], ["figure", "step"])
        new_job = self.start_parse(vid)
        # Same physical cache retains errors; a generic checkbox cannot erase them.
        self.assertTrue(self.knowledge.complete(new_job, self.knowledge.cached_result(new_job)))
        reject = self.post(f"/knowledge/versions/{vid}/review", self.review_payload(vid))
        self.assertEqual(reject.status_code, 409)


if __name__ == "__main__":
    import unittest
    unittest.main()
