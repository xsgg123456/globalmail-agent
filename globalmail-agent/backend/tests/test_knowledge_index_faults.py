"""Real durable failures/leases/cancellation; provider output is explicit synthetic data."""
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_index_schema import index_builds, embedding_cache
from globalmail_agent.adapters.conversation_schema import jobs, agent_slots
from globalmail_agent.knowledge.commands import Command, VersionCommand, ReviewCommand
from globalmail_agent.application.conversation_lock import ServiceError
from index_helpers import IndexFixture


class IndexFaultTests(IndexFixture):
    def test_partial_batch_failure_keeps_old_publication_review_and_reuses_partial_cache(self):
        did, vid, _ = self.reviewed_markdown()
        old = self.publish([self.build(vid)])
        text = "# 长排障\n\n" + "\n\n".join(f"步骤{i}：" + "a" * 400 for i in range(36))
        revised = self.docs.revise(did, VersionCommand(expected_version=1, content=text, applicabilities=[
            {"section_id": "document", "sku": "H-CTD16-US-BK", "basis": "完整长文模拟步骤"}]), uuid4().hex)
        next_vid = UUID(revised["version_id"])
        parse_job = self.start_parse(next_vid)
        self.runner.owner = parse_job["lease_owner"]
        self.runner.execute(parse_job)
        self.reviews.review(next_vid, ReviewCommand.model_validate(self.review_payload(next_vid)), uuid4().hex)
        result = self.build(next_vid, execute=False)
        job = self.runner.jobs.claim(self.runner.owner)
        self.gateway.failure_at = len(self.gateway.calls) + 2
        with self.assertRaises(ServiceError) as error:
            self.runner.execute(job)
        self.assertEqual(error.exception.code, "embedding_provider_error")
        self.runner.jobs.fail(job, error.exception.code, True)
        state = self.builds.status(next_vid)["builds"][0]
        self.assertEqual(state["stage"], "retry_wait")
        self.assertGreater(state["embedded_count"], 0)
        self.assertLess(state["embedded_count"], state["chunk_count"])
        self.assertEqual(self.queries.version_detail(next_vid)["version"]["status"], "reviewed")
        self.assertIsNotNone(self.queries.version_detail(next_vid)["version"]["parse_sha256"])
        self.assertEqual(self.preview()["evidence"][0]["version_id"], str(vid))
        self.assertEqual(self.releases.listing()["head"], old["head"])
        with self.engine.begin() as conn:
            conn.execute(jobs.update().where(jobs.c.id == job["id"]).values(not_before=sa.func.now()))
        self.gateway.failure_at = None
        retry = self.runner.jobs.claim(self.runner.owner)
        self.runner.execute(retry)
        self.assertEqual(self.builds.status(next_vid)["builds"][0]["status"], "ready")
        self.assertEqual(self.preview()["evidence"][0]["version_id"], str(vid))

    def test_cancel_inflight_result_and_retry_preserve_reviewed_parse(self):
        _, vid, _ = self.reviewed_markdown()
        result = self.build(vid, execute=False)
        job = self.runner.jobs.claim(self.runner.owner)
        def cancel():
            self.gateway.hook = None
            state = self.runner.jobs.get(job["id"])["job"]
            self.runner.jobs.control(job["id"], "cancel", Command(expected_version=state["row_version"]), uuid4().hex)
        self.gateway.hook = cancel
        with self.assertRaises(ServiceError):
            self.runner.execute(job)
        self.assertEqual(self.count(embedding_cache), 0)
        self.assertEqual(self.builds.status(vid)["builds"][0]["status"], "cancelled")
        v = self.queries.version_detail(vid)["version"]
        self.assertEqual(v["status"], "reviewed")
        self.assertIsNotNone(v["parse_sha256"])
        state = self.runner.jobs.get(job["id"])["job"]
        self.runner.jobs.control(job["id"], "retry", Command(expected_version=state["row_version"]), uuid4().hex)
        new = self.runner.jobs.claim(self.runner.owner)
        self.runner.execute(new)
        self.assertEqual(self.builds.status(vid)["builds"][0]["status"], "ready")
        with self.assertRaises(ServiceError):
            self.runner.execute(job)

    def test_expired_lease_rolls_back_late_vectors_and_bad_source_releases_slot(self):
        _, vid, _ = self.reviewed_markdown()
        self.build(vid, execute=False)
        job = self.runner.jobs.claim(self.runner.owner)
        def expire():
            self.gateway.hook = None
            with self.engine.begin() as conn:
                conn.execute(agent_slots.update().where(agent_slots.c.job_id == job["id"])
                    .values(lease_expires_at=sa.func.now() - sa.text("interval '1 second'")))
        self.gateway.hook = expire
        with self.assertRaises(ServiceError):
            self.runner.execute(job)
        self.assertEqual(self.count(embedding_cache), 0)
        self.runner.jobs.recover_expired()
        self.assertEqual(self.builds.status(vid)["builds"][0]["stage"], "retry_wait")
        # Damaged original is discovered after a durable claim and does not poison the queue.
        with self.engine.begin() as conn:
            conn.execute(jobs.update().where(jobs.c.id == job["id"]).values(not_before=sa.func.now()))
        next_job = self.runner.jobs.claim(self.runner.owner)
        v = self.queries.version_detail(vid)["version"]
        self.store._path(v["object_id"]).write_bytes(b"broken")
        with self.assertRaises(ServiceError) as error:
            self.runner.execute(next_job)
        self.assertEqual(error.exception.code, "object_integrity_error")
        self.runner.jobs.fail(next_job, error.exception.code, True)
        with self.engine.connect() as conn:
            self.assertIsNone(conn.execute(sa.select(agent_slots.c.job_id).where(agent_slots.c.slot_key == "knowledge")).scalar_one())
        _, good, _ = self.reviewed_markdown("# 新健康资料\n正常队列能继续处理。")
        self.build(good)

    def test_provider_failure_is_distinct_from_no_evidence_and_no_fallback_model(self):
        _, vid, _ = self.reviewed_markdown()
        self.publish([self.build(vid)])
        self.gateway.failure_at = len(self.gateway.calls) + 1
        result = self.preview()
        self.assertEqual(result["reason"], "provider_error")
        self.assertEqual(result["evidence"], [])
        self.assertEqual(result["diagnostics"][0]["code"], "embedding_provider_error")
        self.assertEqual(self.gateway.calls[-1][0], "qwen3.7-text-embedding")
