"""Prepared whitelist, shared physical cache and safe registered derived assets."""
import tempfile
from pathlib import Path
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_schema import document_versions, documents, parse_caches, knowledge_assets
from globalmail_agent.adapters.conversation_schema import jobs
from globalmail_agent.adapters.schema import objects, content_dependencies
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.commands import Command
from globalmail_agent.knowledge.prepared import PreparedImport
from knowledge_helpers import KnowledgeFixture, parsed


class PreparedTests(KnowledgeFixture):
    def test_prepared_22_documents_8_pdf_ranges_one_original_and_one_cache(self):
        key = uuid4().hex
        result = self.post("/knowledge/prepared-import", {"expected_version": 0}, key)
        self.assertEqual(result.status_code, 202, result.text)
        retry = self.post("/knowledge/prepared-import", {"expected_version": 0}, key)
        self.assertEqual(result.json()["data"], retry.json()["data"])
        self.assertEqual(self.count(documents), 22)
        self.assertEqual(self.count(objects), 15)
        self.assertEqual(self.count(jobs), 22)
        duplicate = self.post("/knowledge/prepared-import", {"expected_version": 0})
        self.assertEqual(duplicate.status_code, 409)
        with self.engine.begin() as conn:
            versions = conn.execute(sa.select(document_versions).where(document_versions.c.format == "pdf")).mappings().all()
            self.assertEqual(len(versions), 8)
            self.assertEqual(len({v["object_id"] for v in versions}), 1)
            self.assertEqual({tuple(v["page_range"]) for v in versions}, {(n, n + 1) for n in range(2, 18, 2)})
            # Process only the physical PDF jobs; markdown/policy work is independently tested.
            conn.execute(jobs.update().where(jobs.c.knowledge_version_id.not_in([v["id"] for v in versions])).values(not_before=sa.func.now() + sa.text("interval '1 day'")))
        real_parses = 0
        for _ in range(8):
            job = self.knowledge.claim("physical_pdf_test_worker")
            cache = self.knowledge.cached_result(job)
            if cache:
                self.assertTrue(self.knowledge.complete(job, cache))
            else:
                real_parses += 1
                self.assertTrue(self.knowledge.complete(job, parsed(job, 17)))
            detail = self.queries.version_detail(job["version_id"])
            self.assertEqual({b["page"] for b in detail["blocks"]}, set(range(detail["version"]["page_range"][0], detail["version"]["page_range"][1] + 1)))
            self.assertTrue(all(b["section_id"] == detail["applicabilities"][0]["section_id"] for b in detail["blocks"]))
            self.assertFalse(detail["version"]["published"])
            self.assertIsNone(detail["review"])
        self.assertEqual(real_parses, 1)
        self.assertEqual(self.count(parse_caches), 1)
        self.assertEqual(self.count(objects), 16)

    def test_assets_dependencies_scope_and_raw_data_never_reach_http(self):
        did, vid, payload = self.markdown()
        job = self.start_parse(vid)
        result = parsed(job)
        with tempfile.TemporaryDirectory(prefix="knowledge_assets_") as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            content = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000b49444154789c636000020000050001a5f645400000000049454e44ae426082")
            (root / "assets/pixel.png").write_bytes(content)
            (root / "raw.json").write_text('{"internal":"full raw only"}', encoding="utf-8")
            result["assets"] = [
                {"id": "image", "relative_path": "assets/pixel.png", "media_type": "image/png", "kind": "figure", "page": None, "sha256": None},
                {"id": "raw", "relative_path": "raw.json", "media_type": "application/json", "kind": "raw", "page": None, "sha256": None}]
            result["blocks"][0]["asset_ids"] = ["image"]
            result["raw_document"] = {"never_http": "raw sensitive placeholder"}
            self.assertTrue(self.knowledge.complete(job, result, root))
        self.assertEqual(self.count(objects), 4)
        self.assertEqual(self.count(content_dependencies), 5)
        detail = self.client.get(f"/api/v1/knowledge/versions/{vid}")
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertNotIn("never_http", detail.text)
        self.assertNotIn("relative_path", detail.text)
        self.assertNotIn("raw.json", detail.text)
        self.assertNotIn(self.temp.name, detail.text)
        asset = detail.json()["data"]["assets"][0]
        response = self.client.get(asset["url"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, content)
        self.assertEqual(response.headers["cache-control"], "no-store")
        with self.engine.connect() as conn:
            raw = conn.execute(sa.select(knowledge_assets.c.object_id).where(knowledge_assets.c.kind == "raw")).scalar_one()
        self.assertEqual(self.client.get(f"/api/v1/knowledge/assets/{raw}").status_code, 404)

    def test_missing_page_and_asset_path_traversal_cannot_be_reviewed(self):
        did, vid, payload = self.markdown()
        job = self.start_parse(vid)
        result = parsed(job)
        result["assets"] = [{"id": "unsafe", "relative_path": "../outside.png", "media_type": "image/png", "kind": "figure", "page": None, "sha256": None}]
        with tempfile.TemporaryDirectory(prefix="knowledge_asset_guard_") as directory:
            with self.assertRaises(ServiceError):
                self.knowledge.complete(job, result, Path(directory))
        self.assertEqual(self.count(parse_caches), 0)
        self.assertEqual(self.count(objects), 1)
        result = parsed(job)
        result["full_document"] = False
        self.assertTrue(self.knowledge.complete(job, result))
        refused = self.post(f"/knowledge/versions/{vid}/review", self.review_payload(vid))
        self.assertEqual(refused.status_code, 409)
        self.assertEqual(refused.json()["msg"], "incomplete_parse")
