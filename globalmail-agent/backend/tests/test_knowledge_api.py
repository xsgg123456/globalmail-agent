"""Real PG to production HTTP routes, upload/CAS/scope/policy and immutable history."""
import json
import unittest
from pathlib import Path
from uuid import UUID, uuid4
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, DBAPIError
from globalmail_agent.adapters.schema import objects
from globalmail_agent.adapters.knowledge_schema import documents, document_versions, applicabilities, policy_bundles
from globalmail_agent.adapters.conversation_schema import jobs
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.adapters.fixture_loader import FIXTURE_ROOT
from globalmail_agent.knowledge.commands import CreateDocument, VersionCommand
from globalmail_agent.knowledge.base import scope
from globalmail_agent.knowledge.policy_bundle import parse_policy
from knowledge_helpers import KnowledgeFixture, pdf_bytes, parsed


class KnowledgeApiTests(KnowledgeFixture):
    def test_upload_actual_bytes_limits_and_idempotency(self):
        data = pdf_bytes()
        key = uuid4().hex
        headers = {**self.headers, "Idempotency-Key": key, "Content-Type": "application/octet-stream"}
        url = "/api/v1/knowledge/uploads?filename=manual.pdf"
        first = self.client.post(url, content=data, headers=headers)
        self.assertEqual(first.status_code, 202, first.text)
        second = self.client.post(url, content=data, headers=headers)
        self.assertEqual(first.json()["data"], second.json()["data"])
        self.assertEqual(first.json()["data"]["page_count"], 2)
        self.assertEqual(self.count(objects), 1)
        conflict = self.client.post(url, content=pdf_bytes(3), headers=headers)
        self.assertEqual(conflict.status_code, 409)
        cases = [("../bad.pdf", data, "invalid_filename"), ("https://bad.test/x.pdf", data, "invalid_filename"),
            ("bad.pdf", b"%PDF-corrupt", "invalid_pdf"), ("bad.pdf", b"not-a-pdf", "invalid_pdf"),
            ("secure.pdf", pdf_bytes(encrypted=True), "encrypted_pdf"), ("large.pdf", pdf_bytes(301), "pdf_page_limit"),
            ("fake.md", data, "unsupported_format"), ("bad.md", b"MZprogram", "unsupported_format"),
            ("story.json", b'{"schema_version":"scene/1","initial_state":{}}', "unsupported_policy_schema")]
        for filename, body, error in cases:
            result = self.client.post("/api/v1/knowledge/uploads", params={"filename": filename}, content=body,
                headers={**headers, "Idempotency-Key": uuid4().hex})
            self.assertEqual(result.status_code, 422, result.text)
            self.assertEqual(result.json()["msg"], error)
        huge = self.client.post(url, content=b"x" * (50 * 1024 * 1024 + 1), headers={**headers, "Idempotency-Key": uuid4().hex})
        self.assertEqual(huge.status_code, 422)
        self.assertEqual(self.count(objects), 1)

    def test_create_unknown_retry_and_schema_rejects_scope_publication(self):
        did, vid, payload = self.markdown(key="stable-create")
        result = self.post("/knowledge/documents", payload, "stable-create")
        self.assertEqual(result.status_code, 202, result.text)
        self.assertEqual(result.json()["data"]["document_id"], str(did))
        self.assertEqual(self.count(documents), 1)
        for update in ({"allowed_modes": ["historical_replay"]}, {"published": True}, {"source_kind": "manufacturer"}, {"workspace_id": str(uuid4())}):
            bad = self.post("/knowledge/documents", {**payload, **update})
            self.assertEqual(bad.status_code, 422, bad.text)
        invalid = self.post("/knowledge/documents", {**payload, "applicabilities": [{"section_id": "document", "sku": "SP-XLLHBC02-P", "basis": "wrong brand"}]})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(self.count(objects), 1)
        detail = self.client.get(f"/api/v1/knowledge/documents/{did}").json()["data"]
        self.assertFalse(detail["document"]["published"])
        self.assertEqual(detail["document"]["allowed_modes"], ["simulation"])
        self.assertEqual(len(detail["audits"]), 1)
        listing = self.client.get("/api/v1/knowledge/documents?sku=H-CTD16-US-BK").json()["data"]
        self.assertEqual(len(listing["items"]), 1)
        self.assertEqual(self.client.get("/api/v1/knowledge/documents?sku=unknown").json()["data"]["items"], [])
        source = self.client.get(f"/api/v1/knowledge/versions/{vid}/source")
        self.assertEqual(source.status_code, 200)
        self.assertTrue(source.headers["content-type"].startswith("text/plain"))
        self.assertEqual(source.headers["cache-control"], "no-store")
        self.assertEqual(source.content.decode(), payload["content"])

    def test_revision_keeps_original_and_real_diff_conflicts_preserve_input(self):
        did, vid, payload = self.markdown()
        revise = {"expected_version": 1, "content": "# 第二版\n先拔掉电源，后续人工核验。", "applicabilities": payload["applicabilities"]}
        key = uuid4().hex
        first = self.post(f"/knowledge/documents/{did}/versions", revise, key)
        self.assertEqual(first.status_code, 202, first.text)
        retry = self.post(f"/knowledge/documents/{did}/versions", revise, key)
        self.assertEqual(first.json()["data"], retry.json()["data"])
        stale = self.post(f"/knowledge/documents/{did}/versions", revise)
        self.assertEqual(stale.status_code, 409)
        current = self.client.get("/api/v1/knowledge/versions/" + first.json()["data"]["version_id"]).json()["data"]
        self.assertIn("+先拔掉电源", current["diff"]["text_diff"])
        self.assertEqual(self.queries.version_detail(vid)["source_text"], payload["content"])
        self.assertEqual(self.count(document_versions), 2)
        with self.assertRaises(DBAPIError):
            with self.engine.begin() as conn:
                conn.execute(document_versions.update().where(document_versions.c.id == vid).values(title="rewrite old"))
        with self.assertRaises(DBAPIError):
            with self.engine.begin() as conn:
                conn.execute(documents.update().where(documents.c.id == did).values(allowed_modes=["historical_replay"]))

    def test_missing_cross_scope_source_and_job_targets_fail_closed(self):
        did, vid, payload = self.markdown()
        for path in (f"/knowledge/documents/{uuid4()}", f"/knowledge/versions/{uuid4()}", f"/knowledge/assets/{uuid4()}", f"/jobs/{uuid4()}"):
            self.assertEqual(self.client.get("/api/v1" + path).status_code, 404)
        other = uuid4()
        from globalmail_agent.adapters.schema import workspaces
        from globalmail_agent.knowledge.queries import KnowledgeQueries
        with self.engine.begin() as conn:
            conn.execute(sa.insert(workspaces).values(id=other, name="isolated-other"))
        with self.assertRaises(ServiceError) as error:
            KnowledgeQueries(self.engine, self.store, other).version_detail(vid)
        self.assertEqual(error.exception.status, 404)
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as conn:
                conn.execute(sa.insert(jobs).values(id=uuid4(), **scope(other), knowledge_version_id=vid,
                    kind="knowledge", status="queued", stage="queued", attempt_no=1, parse_generation=1,
                    parser_profile_id="markdown", document_fence=1))
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as conn:
                conn.execute(sa.insert(jobs).values(id=uuid4(), **scope(other), kind="agent", status="queued", attempt_no=1))

    def test_policy_edit_is_validated_and_generation_remains_same_version(self):
        rules = json.loads((FIXTURE_ROOT.parent / "v2/policies/policy-profile.json").read_text(encoding="utf-8"))
        original = (FIXTURE_ROOT.parent / "v2/policies/policy-profile.json").read_bytes()
        rules["return"]["window_days_after_delivery"] = 45
        rules["refund"]["partial_offer_max_basis_points"] = 1250
        did, vid, payload = self.markdown()
        policy_payload = {**payload, "title": "政策草稿", "document_type": "policy_json", "brand": None, "content": rules}
        result = self.post("/knowledge/documents", policy_payload)
        self.assertEqual(result.status_code, 202, result.text)
        detail = self.client.get("/api/v1/knowledge/versions/" + result.json()["data"]["version_id"]).json()["data"]
        self.assertEqual(detail["policy"]["rules"]["return"]["window_days_after_delivery"], 45)
        self.assertIn("45 天", detail["policy"]["description"])
        self.assertIn("1250 基点", detail["policy"]["description"])
        self.assertEqual((FIXTURE_ROOT.parent / "v2/policies/policy-profile.json").read_bytes(), original)
        for path, bad_value in ((["return", "window_days_after_delivery"], True), (["refund", "partial_offer_max_basis_points"], 10001),
                (["return", "receipt_required_for_refund"], False), (["allowed_modes"], ["historical_replay"]),
                (["evidence_requirements", "warehouse_receipt", "allowed_kinds"], ["visual_observation"])):
            bad = json.loads(json.dumps(rules))
            node = bad
            for name in path[:-1]:
                node = node[name]
            node[path[-1]] = bad_value
            response = self.post("/knowledge/documents", {**policy_payload, "content": bad})
            self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
