"""Real private PG -> HTTP -> durable worker protocol; synthetic vectors are explicit."""
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_index_schema import embedding_cache, evidence_refs, knowledge_dependencies, knowledge_release_heads
from globalmail_agent.adapters.conversation_schema import jobs
from globalmail_agent.adapters.knowledge_schema import document_versions
from globalmail_agent.knowledge.commands import VersionCommand, ReviewCommand
from globalmail_agent.application.conversation_lock import ServiceError
from index_helpers import IndexFixture


class IndexApiTests(IndexFixture):
    def test_publication_filters_are_distinct_and_keep_old_publication_after_draft_revision(self):
        did, vid, payload = self.reviewed_markdown()
        _, draft, _ = self.markdown("# 还未发布\n待核对正文。")
        self.publish([self.build(vid)])
        self.docs.revise(did, VersionCommand(expected_version=1, title="新草稿", applicabilities=payload["applicabilities"]), uuid4().hex)
        def listing(value):
            result = self.client.get("/api/v1/knowledge/documents", params={"publication": value})
            self.assertEqual(result.status_code, 200, result.text)
            return result.json()["data"]["items"]
        self.assertEqual([r["id"] for r in listing("published")], [str(did)])
        self.assertEqual(len(listing("unpublished")), 1)
        self.assertEqual(listing("withdrawn"), [])
        self.assertEqual(self.client.get("/api/v1/knowledge/documents", params={"publication": "invalid"}).status_code, 422)
        head = self.releases.listing()["head"]
        self.post(f"/knowledge/documents/{did}/withdraw", {"expected_version": 2, "expected_release_epoch": head["epoch"]})
        self.assertEqual(listing("published"), [])
        self.assertEqual([r["id"] for r in listing("withdrawn")], [str(did)])
        self.assertEqual(len(listing("unpublished")), 1)

    def test_review_build_publish_preview_and_reference_are_real(self):
        did, vid, _ = self.reviewed_markdown()
        result = self.build(vid)
        state = self.client.get(f"/api/v1/knowledge/versions/{vid}/index").json()["data"]
        self.assertEqual(state["builds"][0]["status"], "ready")
        self.assertTrue(state["builds"][0]["eligible"])
        self.assertIsNone(state["publication"])
        self.assertEqual(self.preview()["reason"], "scope_unavailable")
        published = self.publish([result])
        hits = self.preview()
        self.assertEqual(hits["reason"], "ok")
        self.assertEqual(len(hits["evidence"]), 1)
        ref = hits["evidence"][0]
        self.assertEqual(ref["version_id"], str(vid))
        self.assertEqual(ref["source_kind"], "user_provided_simulation_knowledge")
        self.assertIn("先断电", ref["text"])
        self.assertEqual(ref["release_epoch"], published["head"]["epoch"])
        self.assertTrue(self.client.get(f"/api/v1/knowledge/references/{ref['evidence_id']}").json()["data"]["eligible"])
        self.assertTrue(self.queries.version_detail(vid)["version"]["published"])
        self.assertEqual(self.count(evidence_refs), 1)
        self.assertEqual(self.count(knowledge_dependencies), 1)
        self.preview()  # deterministic references/dependencies do not grow.
        self.assertEqual(self.count(evidence_refs), 1)

    def test_gets_do_not_create_head_jobs_or_vectors_and_unreviewed_cannot_build(self):
        did, vid, _ = self.markdown()
        count_jobs = self.count(jobs)
        for _ in range(3):
            for path in ("/knowledge/releases", "/knowledge/index-profiles", f"/knowledge/versions/{vid}/index", f"/knowledge/versions/{vid}"):
                self.assertEqual(self.client.get("/api/v1" + path).status_code, 200)
        self.assertEqual(self.count(knowledge_release_heads), 0)
        self.assertEqual(self.count(jobs), count_jobs)
        self.assertEqual(self.count(embedding_cache), 0)
        response = self.post(f"/knowledge/versions/{vid}/build", {"expected_version": 1,
            "embedding_profile_key": "qwen3.7-text-embedding", "chunking_profile_key": "structure_v1_500"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["msg"], "review_required")
        self.assertEqual(self.gateway.calls, [])

    def test_exact_sku_brand_type_mode_time_and_stale_filter_before_provider(self):
        did, vid, _ = self.reviewed_markdown()
        self.publish([self.build(vid)])
        before = len(self.gateway.calls)
        for updates, reason in (({"sku": "H-GMD19-US-BK"}, "empty"), ({"brand": "BELEEV"}, "empty"),
                ({"types": ["manual_pdf"]}, "empty"), ({"mode": "history_replay", "as_of": "2026-10-08T12:00:00Z"}, "scope_unavailable"),
                ({"as_of": "2020-01-01T00:00:00Z"}, "empty"), ({"expected_release_epoch": 0}, "stale_release")):
            self.assertEqual(self.preview(**updates)["reason"], reason)
        self.assertEqual(len(self.gateway.calls), before)
        self.assertEqual(self.post("/knowledge/search", {"query": "x", "sku": "H-CTD16-US-BK", "mode": "history_replay"}).status_code, 422)

    def test_reparse_published_version_requires_new_revision_and_preserves_serving_manifest(self):
        _, vid, _ = self.reviewed_markdown()
        published = self.publish([self.build(vid)])
        before = self.queries.version_detail(vid)["version"]
        response = self.post(f"/knowledge/versions/{vid}/parse", {"expected_version": before["row_version"], "parser_profile_id": "markdown"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["msg"], "published_version_requires_revision")
        self.assertEqual(self.queries.version_detail(vid)["version"], before)
        self.assertEqual(self.preview()["evidence"][0]["version_id"], str(vid))
        self.assertEqual(self.releases.listing()["head"], published["head"])

    def test_metadata_only_revision_reuses_vectors_title_change_reembeds_and_old_stays_published(self):
        did, vid, payload = self.reviewed_markdown()
        self.publish([self.build(vid)])
        vector_count = self.count(embedding_cache)
        revised = self.docs.revise(did, VersionCommand(expected_version=1, applicabilities=[
            {"section_id": "document", "sku": "H-CTD16-US-BK", "basis": "重新核对适用，不变正文"}]), uuid4().hex)
        new_vid = UUID(revised["version_id"])
        self.assertTrue(self.queries.version_detail(vid)["version"]["published"])
        self.assertEqual(self.preview()["evidence"][0]["version_id"], str(vid))
        parsed_job = self.start_parse(new_vid)
        self.runner.owner = parsed_job["lease_owner"]
        self.runner.execute(parsed_job)
        self.reviews.review(new_vid, ReviewCommand.model_validate(self.review_payload(new_vid)), uuid4().hex)
        new_build = self.build(new_vid)
        self.assertEqual(self.count(embedding_cache), vector_count)
        self.assertGreater(self.builds.status(new_vid)["builds"][0]["cache_hits"], 0)
        self.publish([new_build])
        titled = self.docs.revise(did, VersionCommand(expected_version=2, title="新的嵌入标题", applicabilities=payload["applicabilities"]), uuid4().hex)
        title_vid = UUID(titled["version_id"])
        job = self.start_parse(title_vid)
        self.runner.execute(job)
        self.reviews.review(title_vid, ReviewCommand.model_validate(self.review_payload(title_vid)), uuid4().hex)
        self.build(title_vid)
        self.assertGreater(self.count(embedding_cache), vector_count)
        self.assertEqual(self.preview()["evidence"][0]["version_id"], str(new_vid))
