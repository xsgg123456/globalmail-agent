"""Real worker and PG/HTTP: broken originals never block the next queued document."""
from pathlib import Path
from time import monotonic, sleep
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.conversation_schema import jobs
from globalmail_agent.adapters.knowledge_schema import document_versions
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
from globalmail_agent.worker.knowledge_runner import KnowledgeRunner
from knowledge_helpers import KnowledgeFixture, parsed


class SourceFaultTests(KnowledgeFixture):
    def enqueue_http(self, vid):
        version = self.queries.version_detail(vid)["version"]
        response = self.post(f"/knowledge/versions/{vid}/parse", {
            "expected_version": version["row_version"], "parser_profile_id": "markdown"})
        self.assertEqual(response.status_code, 202, response.text)
        return UUID(response.json()["data"]["job_id"])

    def wait_job(self, identity, predicate):
        deadline = monotonic() + 8
        while monotonic() < deadline:
            response = self.client.get(f"/api/v1/jobs/{identity}")
            self.assertEqual(response.status_code, 200)
            job = response.json()["data"]["job"]
            if predicate(job):
                return job
            sleep(0.05)
        self.fail("worker did not reach the asserted state")

    def exercise_fault(self, corrupt=False, cached=False):
        did, vid, payload = self.markdown("# 损坏原件测试\n先断电。")
        if cached:
            first = self.start_parse(vid)
            self.assertTrue(self.knowledge.complete(first, parsed(first)))
        broken = self.enqueue_http(vid)
        with self.engine.connect() as connection:
            oid = connection.execute(sa.select(document_versions.c.object_id)
                .where(document_versions.c.id == vid)).scalar_one()
        path = self.store._path(oid)
        # This path belongs only to ProtocolFixture's disposable object directory.
        self.assertEqual(path.resolve().parent, Path(self.temp.name).resolve())
        if corrupt:
            path.write_bytes(b"changed private test bytes")
        else:
            path.unlink()
        _, healthy_vid, _ = self.markdown("# 正常原件测试\n24 V，保留单位。")
        healthy = self.enqueue_http(healthy_vid)
        runner = KnowledgeRunner(self.engine, self.store, DEFAULT_WORKSPACE_ID)
        runner.start()
        self.addCleanup(runner.close)
        self.assertEqual(self.wait_job(healthy, lambda j: j["status"] == "completed")["stage"], "needs_review")
        expected = "object_integrity_error" if corrupt else "source_unavailable"
        for attempt in (2, 3, 4):
            fault = self.wait_job(broken, lambda j: j["attempt_no"] >= attempt)
            self.assertEqual(fault["error_code"], expected)
            self.assertTrue(fault["retryable"])
            self.assertEqual(fault["stage"], "retry_wait")
            with self.engine.begin() as connection:
                connection.execute(jobs.update().where(jobs.c.id == broken)
                    .values(not_before=sa.func.now() - sa.text("interval '1 second'")))
        failed = self.wait_job(broken, lambda j: j["status"] == "failed")
        self.assertEqual(failed["attempt_no"], 4)
        self.assertEqual(self.queries.version_detail(vid)["version"]["status"], "failed")
        detail = self.client.get(f"/api/v1/knowledge/versions/{vid}")
        self.assertEqual(detail.status_code, 200)
        self.assertFalse(detail.json()["data"]["source_available"])
        self.assertIsNone(detail.json()["data"]["source_text"])
        self.assertEqual(detail.json()["data"]["jobs"][0]["error_code"], expected)
        self.assertTrue(detail.json()["data"]["diagnostics"][-1]["blocks_review"])
        # Restore exactly the registered original; explicit HTTP retry is now useful.
        path.write_bytes(payload["content"].encode())
        response = self.post(f"/jobs/{broken}/retry", {"expected_version": failed["row_version"]})
        self.assertEqual(response.status_code, 202, response.text)
        self.wait_job(broken, lambda j: j["status"] == "completed")
        runner.close()
        self.assertEqual(self.queries.version_detail(healthy_vid)["version"]["status"], "needs_review")
        self.assertEqual(self.queries.version_detail(vid)["version"]["status"], "needs_review")
        self.assertIsNone(self.queries.version_detail(vid)["review"])

    def test_missing_original_persists_failure_and_next_document_completes(self):
        self.exercise_fault()

    def test_corrupted_original_persists_failure_and_next_document_completes(self):
        self.exercise_fault(corrupt=True)

    def test_cached_result_never_bypasses_missing_original(self):
        self.exercise_fault(cached=True)

    def test_review_rechecks_original_and_old_source_fault_does_not_hide_new_version(self):
        from globalmail_agent.knowledge.commands import VersionCommand
        did, vid, payload = self.markdown()
        job = self.start_parse(vid)
        self.assertTrue(self.knowledge.complete(job, parsed(job)))
        command = self.review_payload(vid)
        path = self.store._path(job["object_id"])
        path.unlink()
        rejected = self.post(f"/knowledge/versions/{vid}/review", command)
        self.assertEqual(rejected.status_code, 503)
        self.assertEqual(rejected.json()["msg"], "source_unavailable")
        detail = self.client.get(f"/api/v1/knowledge/versions/{vid}").json()["data"]
        self.assertIsNone(detail["review"])
        self.assertFalse(detail["source_available"])
        newer = self.docs.revise(did, VersionCommand(expected_version=1,
            content="# 新版完整原件\n先断电。", applicabilities=payload["applicabilities"]), uuid4().hex)
        detail = self.client.get(f"/api/v1/knowledge/versions/{newer['version_id']}")
        self.assertEqual(detail.status_code, 200)
        current = detail.json()["data"]
        self.assertTrue(current["source_available"])
        self.assertIn("新版完整原件", current["source_text"])
        self.assertIsNone(current["diff"]["text_diff"])
        self.assertEqual(current["diagnostics"][-1]["code"], "prior_source_unavailable")
