"""Actual PDF actions and explicit JSON/JSONL schemas at the HTTP upload boundary."""
import io
import json
from uuid import uuid4
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, ArrayObject, TextStringObject
from globalmail_agent.adapters.schema import objects
from globalmail_agent.knowledge.json_structure import validate_knowledge_structure
from knowledge_helpers import KnowledgeFixture, parsed


def active_pdf(kind):
    writer = PdfWriter()
    page = writer.add_blank_page(width=100, height=100)
    if kind == "EmbeddedFiles":
        writer.add_attachment("test.txt", b"embedded test-only")
    elif kind == "RichMedia":
        page[NameObject("/Annots")] = ArrayObject([DictionaryObject({NameObject("/Subtype"): NameObject("/RichMedia"),
            NameObject("/RichMediaContent"): DictionaryObject()})])
    else:
        action = DictionaryObject({NameObject("/S"): NameObject("/JavaScript" if kind == "AdditionalActions" else "/" + kind)})
        if kind in {"JavaScript", "AdditionalActions"}:
            action[NameObject("/JS")] = TextStringObject("alert('test-only')")
        else:
            action[NameObject("/F")] = TextStringObject("do-not-open-test-only")
        if kind == "AdditionalActions":
            page[NameObject("/AA")] = DictionaryObject({NameObject("/O"): action})
        else:
            page[NameObject("/Annots")] = ArrayObject([DictionaryObject({NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Link"), NameObject("/A"): action})])
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class KnowledgeInputTests(KnowledgeFixture):
    def test_page_annotation_actions_rich_media_and_embedded_files_are_rejected(self):
        for kind in ("AdditionalActions", "JavaScript", "Launch", "RichMedia", "EmbeddedFiles"):
            result = self.client.post("/api/v1/knowledge/uploads?filename=active.pdf", content=active_pdf(kind),
                headers={**self.headers, "Idempotency-Key": uuid4().hex, "Content-Type": "application/octet-stream"})
            self.assertEqual(result.status_code, 422, result.text)
            self.assertEqual(result.json()["msg"], "active_pdf_content")
        self.assertEqual(self.count(objects), 0)

    def test_json_jsonl_structure_is_accepted_full_and_scope_fields_are_rejected(self):
        base = {"schema_version": "globalmail.knowledge/1", "document_type": "case_md", "section_id": "document",
            "type": "paragraph", "text": "这是受控案例，承诺不等于已发货。"}
        for fmt in ("json", "jsonl"):
            body = {"schema_version": base["schema_version"], "document_type": base["document_type"],
                "blocks": [{k: v for k, v in base.items() if k not in {"schema_version", "document_type"}}]} if fmt == "json" else base
            content = json.dumps(body, ensure_ascii=False).encode()
            if fmt == "jsonl":
                content += b"\n" + json.dumps({**base, "text": "第二块完整保留。"}, ensure_ascii=False).encode()
            result = self.client.post(f"/api/v1/knowledge/uploads?filename=case.{fmt}", content=content,
                headers={**self.headers, "Idempotency-Key": uuid4().hex, "Content-Type": "application/octet-stream"})
            self.assertEqual(result.status_code, 202, result.text)
            did, vid, payload = self.markdown()
            payload.update(document_type="case_md", content=None, object_id=result.json()["data"]["object_id"])
            created = self.post("/knowledge/documents", payload)
            self.assertEqual(created.status_code, 202, created.text)
            from uuid import UUID
            created_vid = UUID(created.json()["data"]["version_id"])
            job = self.start_parse(created_vid)
            normalized = validate_knowledge_structure(content, fmt)
            output = parsed(job)
            output["blocks"] = normalized["blocks"]
            output["raw_document"] = {"original_text": content.decode(), "normalized": normalized}
            self.assertTrue(self.knowledge.complete(job, output))
            detail = self.queries.version_detail(created_vid)
            self.assertEqual(len(detail["blocks"]), 1 if fmt == "json" else 2)
            self.assertEqual(detail["source_text"].encode(), content)
            self.assertTrue(all(b["id"].startswith("json-") for b in detail["blocks"]))
        for update in ({"source_kind": "official"}, {"url": "https://example.test"}, {"page": 1},
                {"asset_ids": ["escape"]}, {"reference_reply": "answer"}, {"initial_state": {}}):
            content = json.dumps({**base, **update}).encode()
            result = self.client.post("/api/v1/knowledge/uploads?filename=bad.jsonl", content=content,
                headers={**self.headers, "Idempotency-Key": uuid4().hex, "Content-Type": "application/octet-stream"})
            self.assertEqual(result.status_code, 422, result.text)
        invalid = b'{"schema_version":"controller/1","events":[]}'
        result = self.client.post("/api/v1/knowledge/uploads?filename=controller.jsonl", content=invalid,
            headers={**self.headers, "Idempotency-Key": uuid4().hex, "Content-Type": "application/octet-stream"})
        self.assertEqual(result.status_code, 422)
