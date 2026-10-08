"""Only the fixed 22 prepared RAG documents; no authoring, stories or evaluation."""
import json
from pathlib import Path
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.fixture_loader import FIXTURE_ROOT
from globalmail_agent.adapters.knowledge_schema import documents, uploads
from globalmail_agent.application.idempotency import prior, remember
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.base import KnowledgeFiles, scope, sha, canonical, ensure_slot, version, document
from globalmail_agent.knowledge.commands import CreateDocument
from globalmail_agent.knowledge.documents import DocumentService
from globalmail_agent.knowledge.queue import KnowledgeQueue
from globalmail_agent.knowledge.validation import inspect_content, catalog

FAMILIES = ("OUTON-01", "OUTON-02", "OUTON-03", "OUTONLIFE-01", "OUTONLIFE-02", "BELEEV-01", "BELEEV-02", "BELEEV-03")
ALLOW = {**{f"MAN-{f}": "../../../output/pdf/product-manuals-v1.pdf" for f in FAMILIES},
    **{f"SOP-{f}": f"sop/{f}.md" for f in FAMILIES},
    **{f"CASE-{n:03}": f"cases/CASE-{n:03}.md" for n in range(1, 6)}, "POL-SIM-V1": "policies/policy-profile.md"}


def package():
    rows = json.loads((FIXTURE_ROOT / "documents.json").read_text(encoding="utf-8"))
    binding_rows = json.loads((FIXTURE_ROOT / "knowledge-bindings.json").read_text(encoding="utf-8"))
    if len(rows) != 22 or {r["document_id"] for r in rows} != set(ALLOW):
        raise ServiceError("prepared_manifest_invalid", 503)
    output = []
    for row in rows:
        identity = row["document_id"]
        if row["path"] != ALLOW[identity] or row["usage_split"] != "rag" or row["allowed_modes"] != ["simulation"]:
            raise ServiceError("prepared_manifest_invalid", 503)
        source = (FIXTURE_ROOT / ALLOW[identity]).resolve().read_bytes()
        if sha(source) != row["source_hash"]:
            raise ServiceError("prepared_source_mismatch", 503)
        fmt, pages = inspect_content(Path(row["path"]).name, source)
        document_type = row["document_type"]
        if identity == "POL-SIM-V1":
            source = (FIXTURE_ROOT / "policies/policy-profile.json").read_bytes()
            fmt, pages = inspect_content("policy.json", source)
            document_type = "policy_json"
        applicable = []
        for binding in binding_rows:
            if binding["document_id"] != identity:
                continue
            if binding["allowed_modes"] != ["simulation"]:
                raise ServiceError("prepared_binding_invalid", 503)
            skus = binding.get("skus")
            if identity == "POL-SIM-V1":
                skus = [p["sku"] for p in catalog() if p["brand"] in binding["brands"]]
            if not skus:
                raise ServiceError("prepared_binding_invalid", 503)
            for sku in skus:
                applicable.append({"section_id": "document" if binding["section_id"] == "all" else binding["section_id"],
                    "sku": sku, "page_start": row.get("page_range", [None, None])[0],
                    "page_end": row.get("page_range", [None, None])[1], "basis": binding["basis"]})
        output.append((row, document_type, source, fmt, pages, applicable))
    return output


class PreparedImport(DocumentService):
    def importing(self, command, key):
        self.available()
        if command.expected_version != 0:
            raise ServiceError("stale_version")
        with KnowledgeFiles(self.store, self.workspace_id) as files, self.engine.begin() as conn:
            previous, digest = prior(conn, self.workspace_id, key, "knowledge-prepared-import", command.model_dump(mode="json"))
            if previous is not None:
                return previous
            ensure_slot(conn, self.workspace_id)
            if conn.execute(sa.select(documents.c.id).where(documents.c.workspace_id == self.workspace_id,
                    documents.c.prepared_id.is_not(None))).first():
                raise ServiceError("prepared_already_imported")
            ids, versions, task_ids, objects_by_hash = [], [], [], {}
            for original, kind, content, fmt, pages, bindings in package():
                content_hash = sha(content)
                if content_hash not in objects_by_hash:
                    oid = files.put(conn, content, original["source_kind"], original["document_id"])
                    objects_by_hash[content_hash] = oid
                    conn.execute(sa.insert(uploads).values(id=uuid4(), **scope(self.workspace_id), object_id=oid,
                        filename="source." + fmt, format=fmt, page_count=pages))
                did = uuid4()
                row = {"id": did, **scope(self.workspace_id), "title": original["title"], "document_type": kind,
                    "brand": original["brand"], "source_kind": original["source_kind"], "source_reference": original["document_id"],
                    "allowed_modes": ["simulation"], "usage_split": "rag", "prepared_id": original["document_id"],
                    "row_version": 1, "document_fence": 1}
                conn.execute(sa.insert(documents).values(**row))
                create = CreateDocument(expected_version=0, title=row["title"], document_type=kind, brand=row["brand"],
                    source_reference=row["source_reference"], available_at=original["available_at"],
                    object_id=objects_by_hash[content_hash], applicabilities=bindings)
                vid = self._version(conn, files, row, create, create.available_at, page_range=original.get("page_range"), manifest_sha=original["source_hash"])
                v = version(conn, self.workspace_id, vid)
                jid = KnowledgeQueue(self.engine, self.workspace_id)._insert(conn, v, row, generation=1)
                from globalmail_agent.adapters.knowledge_schema import document_versions
                conn.execute(document_versions.update().where(document_versions.c.id == vid)
                    .values(status="parsing", parse_generation=1, row_version=2))
                ids.append(str(did))
                versions.append(str(vid))
                task_ids.append(str(jid))
            result = {"document_ids": ids, "version_ids": versions, "job_ids": task_ids, "version": 1}
            remember(conn, self.workspace_id, key, "knowledge-prepared-import", digest, result)
            return result
