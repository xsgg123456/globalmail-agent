"""Disposable PG/HTTP knowledge fixtures; parser contract tests use explicit synthetic blocks."""
import io
from pathlib import Path
from uuid import UUID, uuid4
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from globalmail_agent.adapters.object_store import ObjectStore
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
from globalmail_agent.knowledge.documents import DocumentService
from globalmail_agent.knowledge.jobs import KnowledgeJobService
from globalmail_agent.knowledge.queries import KnowledgeQueries
from globalmail_agent.knowledge.review import ReviewService
from globalmail_agent.knowledge.commands import CreateDocument, ParseCommand
from globalmail_agent.main import create_app
from globalmail_agent.settings import Settings
from test_protocol import ProtocolFixture


def pdf_bytes(pages=2, encrypted=False):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    if encrypted:
        writer.encrypt("test-only")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def parsed(job, count=0, diagnostics=None):
    pages = list(range(1, count + 1)) if count else [None]
    return {"schema_version": "globalmail.parser/1", "source_sha256": job["source_sha256"],
        "full_document": True, "raw_document": {"contract_test": "explicit_synthetic"}, "page_count": count,
        "blocks": [{"id": f"b{page or 0}", "page": page, "section_id": "document", "type": "paragraph",
            "text": f"测试规范正文 {page or 0}", "bbox": None, "figure_id": None, "table_rows": [], "asset_ids": []} for page in pages],
        "assets": [], "diagnostics": diagnostics or [], "parser_versions": {"contract-test": "1"}, "model_versions": {}}


class KnowledgeFixture(ProtocolFixture):
    def setUp(self):
        super().setUp()
        self.store = ObjectStore(Path(self.temp.name), self.engine)
        self.docs = DocumentService(self.engine, self.store)
        self.knowledge = KnowledgeJobService(self.engine, self.store)
        self.queries = KnowledgeQueries(self.engine, self.store)
        self.reviews = ReviewService(self.engine, self.store)
        self.client = TestClient(create_app(Settings(object_root=Path(self.temp.name)), engine=self.engine, start_worker=False),
            base_url="http://127.0.0.1:18080")
        self.addCleanup(self.client.close)
        self.headers = {"Origin": "http://127.0.0.1:15173"}

    def post(self, path, payload, key=None):
        return self.client.post("/api/v1" + path, json=payload, headers={**self.headers, "Idempotency-Key": key or uuid4().hex})

    def markdown(self, content="# 排障\n先断电，保留完整步骤。", key=None):
        payload = {"expected_version": 0, "title": "排障草稿", "document_type": "troubleshooting_md", "brand": "OUTON",
            "source_reference": "人工整理的本地模拟资料", "available_at": "2026-10-08T00:00:00Z", "content": content,
            "applicabilities": [{"section_id": "document", "sku": "H-CTD16-US-BK", "basis": "明确模拟适配"}]}
        result = self.docs.create(CreateDocument.model_validate(payload), key or uuid4().hex)
        return UUID(result["document_id"]), UUID(result["version_id"]), payload

    def start_parse(self, vid, profile="markdown"):
        v = self.queries.version_detail(vid)["version"]
        self.knowledge.enqueue(vid, ParseCommand(expected_version=v["row_version"], parser_profile_id=profile), uuid4().hex)
        job = self.knowledge.claim("knowledge_test_worker")
        self.assertIsNotNone(job)
        return job

    def review_payload(self, vid, **updates):
        v = self.queries.version_detail(vid)["version"]
        return {"expected_version": v["row_version"], **{k: v[k] for k in ("source_sha256", "parse_sha256", "applicability_sha256")},
            "note": "已逐块核对正文和适用范围。", **updates}
