"""CAS concurrency, rollback, same-dimensional space switches and withdrawal gates."""
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.knowledge.commands import VersionCommand, ReviewCommand
from globalmail_agent.knowledge.index_commands import ReleaseCommand, RollbackCommand, WithdrawCommand
from globalmail_agent.application.conversation_lock import ServiceError
from index_helpers import IndexFixture


class ReleaseTests(IndexFixture):
    def test_publish_cas_serializes_competing_full_manifests_and_same_key_replays(self):
        _, first, _ = self.reviewed_markdown()
        _, second, _ = self.reviewed_markdown("# 另一资料\n同范围的完整证据。")
        a, b = self.build(first), self.build(second)
        def publish(build):
            try:
                return self.releases.publish(ReleaseCommand(expected_release_epoch=0, build_ids=[build["build_id"]]), uuid4().hex)
            except ServiceError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(publish, (a, b)))
        self.assertEqual(sum(isinstance(r, dict) for r in responses), 1)
        self.assertIn("stale_release", responses)
        state = self.releases.listing()
        self.assertEqual(state["head"]["epoch"], 1)
        other = b if responses[0] != "stale_release" else a
        body = {"expected_release_epoch": 1, "build_ids": [other["build_id"]], "replace_all": False}
        key = uuid4().hex
        first_response = self.post("/knowledge/releases", body, key)
        self.assertEqual(first_response.status_code, 200, first_response.text)
        self.assertEqual(self.post("/knowledge/releases", body, key).json()["data"], first_response.json()["data"])
        self.assertEqual(len(first_response.json()["data"]["release"]["entries"]), 2)
        self.assertEqual(self.post("/knowledge/releases", {**body, "replace_all": True}, key).status_code, 409)

    def test_withdraw_cancels_old_task_reference_and_rollback_only_fresh_build_restores(self):
        did, vid, _ = self.reviewed_markdown()
        published = self.publish([self.build(vid)])
        evidence = self.preview()["evidence"][0]
        old = self.build(vid, execute=False)
        job = self.runner.jobs.claim(self.runner.owner)
        command = {"expected_version": 1, "expected_release_epoch": published["head"]["epoch"]}
        response = self.post(f"/knowledge/documents/{did}/withdraw", command)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["revocation_epoch"], 1)
        self.assertEqual(self.preview()["reason"], "empty")
        reference = self.client.get(f"/api/v1/knowledge/references/{evidence['evidence_id']}").json()["data"]
        self.assertFalse(reference["eligible"])
        self.assertEqual(reference["reason"], "document_withdrawn")
        self.assertEqual(self.queries.version_detail(vid)["version"]["status"], "reviewed")
        self.assertFalse(self.queries.version_detail(vid)["version"]["published"])
        with self.assertRaises(ServiceError):
            self.runner.execute(job)
        current = response.json()["data"]["head"]
        rollback = self.post(f"/knowledge/releases/{published['release']['id']}/rollback", {"expected_release_epoch": current["epoch"]})
        self.assertEqual(rollback.status_code, 409)
        refused = self.post("/knowledge/releases", {"expected_release_epoch": current["epoch"], "build_ids": [old["build_id"]]})
        self.assertEqual(refused.status_code, 409)
        restored = self.build(vid)
        self.assertTrue(self.builds.status(vid)["withdrawn"])
        self.publish([restored])
        self.assertEqual(self.preview()["reason"], "ok")
        self.assertFalse(self.references.get(UUID(evidence["evidence_id"]))["eligible"])
        self.assertFalse(self.builds.status(vid)["withdrawn"])

    def test_same_dimension_other_model_requires_complete_scope_then_can_rollback(self):
        _, first, _ = self.reviewed_markdown()
        _, second, _ = self.reviewed_markdown("# 另一资料\n独立型号证据。")
        old = self.publish([self.build(first), self.build(second)])
        v4a = self.build(first, model="text-embedding-v4")
        epoch = old["head"]["epoch"]
        response = self.post("/knowledge/releases", {"expected_release_epoch": epoch, "build_ids": [v4a["build_id"]]})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["msg"], "embedding_space_mismatch")
        response = self.post("/knowledge/releases", {"expected_release_epoch": epoch, "build_ids": [v4a["build_id"]], "replace_all": True})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["msg"], "incomplete_space_switch")
        v4b = self.build(second, model="text-embedding-v4")
        switched = self.publish([v4a, v4b], replace_all=True)
        self.assertNotEqual(switched["head"]["embedding_profile_id"], old["head"]["embedding_profile_id"])
        self.preview()
        self.assertEqual(self.gateway.calls[-1][0], "text-embedding-v4")
        rolled = self.post(f"/knowledge/releases/{old['release']['id']}/rollback", {"expected_release_epoch": switched["head"]["epoch"]})
        self.assertEqual(rolled.status_code, 200, rolled.text)
        self.assertEqual(rolled.json()["data"]["head"]["epoch"], 3)
        self.preview()
        self.assertEqual(self.gateway.calls[-1][0], "qwen3.7-text-embedding")

    def test_provider_period_head_change_returns_stale_without_exposing_old_evidence(self):
        did, vid, _ = self.reviewed_markdown()
        published = self.publish([self.build(vid)])
        def withdraw_during_call():
            self.gateway.hook = None
            self.releases.withdraw(did, WithdrawCommand(expected_version=1,
                expected_release_epoch=published["head"]["epoch"]), uuid4().hex)
        self.gateway.hook = withdraw_during_call
        before = self.preview()
        self.assertEqual(before["reason"], "stale_release")
        self.assertEqual(before["evidence"], [])
        self.assertEqual(self.preview()["reason"], "empty")

    def test_unrelated_source_fault_cannot_block_immediate_target_withdrawal(self):
        did, vid, _ = self.reviewed_markdown()
        _, other, _ = self.reviewed_markdown("# 另一个发布文档\n此原件随后缺失。")
        release = self.publish([self.build(vid), self.build(other)])
        source = self.queries.version_detail(other)["version"]["object_id"]
        self.store._path(source).write_bytes(b"damaged")
        result = self.post(f"/knowledge/documents/{did}/withdraw", {"expected_version": 1,
            "expected_release_epoch": release["head"]["epoch"]})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertTrue(result.json()["data"]["withdrawn"])
        state = self.releases.listing()
        self.assertEqual(len(state["items"][0]["entries"]), 1)
        self.assertEqual(state["items"][0]["entries"][0]["version_id"], str(other))
