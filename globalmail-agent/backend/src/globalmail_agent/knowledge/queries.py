"""Safe management projections; raw parser structures never enter HTTP responses."""
import difflib
from uuid import UUID
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_schema import documents, document_versions, applicabilities, blocks, knowledge_assets, knowledge_reviews, knowledge_audits, policy_bundles
from globalmail_agent.adapters.conversation_schema import jobs
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.knowledge.base import KnowledgeFiles, document, version, scoped_where
from globalmail_agent.knowledge.queue import job_view
from globalmail_agent.knowledge.release_queries import publication, published_condition


def version_view(row, published=False):
    keys = ("id", "document_id", "number", "title", "object_id", "format", "page_count", "row_version", "status", "source_sha256", "source_manifest_sha256",
        "parser_profile_id", "parser_fingerprint", "parse_generation", "parse_sha256", "applicability_sha256", "page_range", "available_at")
    return {**{k: row[k] for k in keys}, "published": published}


def binding_view(row):
    return {k: row[k] for k in ("section_id", "sku", "page_start", "page_end", "basis")}


class KnowledgeQueries:
    def __init__(self, engine, store, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.workspace_id = engine, store, workspace_id

    def _available(self):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)

    def _document_view(self, conn, doc):
        current = version(conn, self.workspace_id, doc["current_version_id"])
        active = publication(conn, self.workspace_id, doc["id"])
        return {**{k: doc[k] for k in ("id", "title", "document_type", "brand", "source_kind", "source_reference",
            "allowed_modes", "usage_split", "row_version", "current_version_id")}, "current_version_number": current["number"],
            "status": current["status"], "published": active is not None, "publication": active,
            "withdrawn": doc["withdrawn"], "revocation_epoch": doc["revocation_epoch"]}

    def listing(self, document_type=None, brand=None, sku=None, status=None, cursor=None, limit=50, publication_filter=None):
        self._available()
        with self.engine.connect() as conn:
            query = sa.select(documents).where(*scoped_where(documents, self.workspace_id), documents.c.lifecycle == "active")
            for col, value in ((documents.c.document_type, document_type), (documents.c.brand, brand)):
                if value:
                    query = query.where(col == value)
            if status:
                query = query.where(documents.c.current_version_id.in_(sa.select(document_versions.c.id).where(document_versions.c.status == status)))
            if publication_filter == "published":
                query = query.where(published_condition(self.workspace_id))
            elif publication_filter == "unpublished":
                query = query.where(documents.c.withdrawn.is_(False), ~published_condition(self.workspace_id))
            elif publication_filter == "withdrawn":
                query = query.where(documents.c.withdrawn.is_(True))
            elif publication_filter:
                raise ServiceError("invalid_publication_filter", 422)
            if sku:
                query = query.where(documents.c.current_version_id.in_(sa.select(applicabilities.c.version_id).where(applicabilities.c.sku == sku)))
            if cursor:
                query = query.where(documents.c.id > cursor)
            rows = conn.execute(query.order_by(documents.c.id).limit(limit + 1)).mappings().all()
            return {"items": [self._document_view(conn, row) for row in rows[:limit]],
                "next_cursor": str(rows[limit - 1]["id"]) if len(rows) > limit else None}

    def detail(self, identity):
        self._available()
        with self.engine.connect() as conn:
            doc = document(conn, self.workspace_id, identity)
            versions = conn.execute(sa.select(document_versions).where(document_versions.c.document_id == identity,
                *scoped_where(document_versions, self.workspace_id)).order_by(document_versions.c.number.desc())).mappings().all()
            audits = conn.execute(sa.select(knowledge_audits).where(knowledge_audits.c.document_id == identity,
                *scoped_where(knowledge_audits, self.workspace_id)).order_by(knowledge_audits.c.created_at)).mappings().all()
            active = publication(conn, self.workspace_id, doc["id"])
            return {"document": self._document_view(conn, doc), "versions": [version_view(v, bool(active and active["version_id"] == v["id"])) for v in versions],
                "audits": [{k: row[k] for k in ("id", "version_id", "action", "actor", "details", "created_at")} for row in audits]}

    def _blocks(self, conn, v):
        rows = conn.execute(sa.select(blocks).where(blocks.c.version_id == v["id"], blocks.c.parse_generation == v["parse_generation"],
            *scoped_where(blocks, self.workspace_id)).order_by(blocks.c.position)).mappings().all()
        return [{**row["structure"], "id": row["block_key"], "page": row["page"], "section_id": row["section_id"],
            "type": row["type"], "text": row["text"]} for row in rows]

    def _bindings(self, conn, v):
        return [binding_view(r) for r in conn.execute(sa.select(applicabilities).where(applicabilities.c.version_id == v["id"],
            *scoped_where(applicabilities, self.workspace_id)).order_by(applicabilities.c.section_id, applicabilities.c.sku)).mappings()]

    def _readable(self, conn, v):
        if v["format"] == "pdf":
            return "\n".join(b["text"] for b in self._blocks(conn, v))
        policy = conn.execute(sa.select(policy_bundles.c.description).where(policy_bundles.c.version_id == v["id"],
            *scoped_where(policy_bundles, self.workspace_id))).scalar_one_or_none()
        if policy is not None:
            return policy
        raw = KnowledgeFiles(self.store, self.workspace_id).read(conn, v["object_id"])[0]
        if v["format"] in {"json", "jsonl"}:
            from globalmail_agent.knowledge.json_structure import validate_knowledge_structure
            normalized = validate_knowledge_structure(raw, v["format"])
            return "\n".join(b["text"] + ("\n" + "\n".join(" | ".join(row) for row in b["table_rows"]) if b["table_rows"] else "")
                for b in normalized["blocks"])
        return raw.decode("utf-8")

    def _original(self, conn, v):
        try:
            return KnowledgeFiles(self.store, self.workspace_id).read(conn, v["object_id"])[0], None
        except ServiceError as error:
            if error.code not in {"source_unavailable", "object_integrity_error", "object_not_found"}:
                raise
            return None, {"code": error.code, "severity": "error", "page": None, "block_ids": [],
                "asset_ids": [], "message": "原件缺失或损坏，请恢复完整原件或替换新文件后再核对。", "blocks_review": True}

    def version_detail(self, identity):
        self._available()
        with self.engine.connect() as conn:
            v = version(conn, self.workspace_id, identity)
            parsed = self._blocks(conn, v)
            assets = conn.execute(sa.select(knowledge_assets).where(knowledge_assets.c.cache_id == v["cache_id"],
                *scoped_where(knowledge_assets, self.workspace_id))).mappings().all() if v["cache_id"] else []
            if v["page_range"]:
                assets = [a for a in assets if a["page"] and v["page_range"][0] <= a["page"] <= v["page_range"][1]]
            assets = [a for a in assets if a["kind"] != "raw"]
            review = conn.execute(sa.select(knowledge_reviews).where(knowledge_reviews.c.version_id == identity,
                knowledge_reviews.c.parse_generation == v["parse_generation"], *scoped_where(knowledge_reviews, self.workspace_id))).mappings().first()
            task_rows = conn.execute(sa.select(jobs).where(jobs.c.knowledge_version_id == identity,
                *scoped_where(jobs, self.workspace_id)).order_by(jobs.c.created_at.desc())).mappings().all()
            policy = conn.execute(sa.select(policy_bundles).where(policy_bundles.c.version_id == identity,
                *scoped_where(policy_bundles, self.workspace_id))).mappings().first()
            raw, source_error = self._original(conn, v)
            diagnostics = [*v["diagnostics"], *([source_error] if source_error else [])]
            text = raw.decode("utf-8") if raw is not None and v["format"] != "pdf" else None
            prior = conn.execute(sa.select(document_versions).where(document_versions.c.document_id == v["document_id"],
                document_versions.c.number == v["number"] - 1, *scoped_where(document_versions, self.workspace_id))).mappings().first()
            diff = None
            if prior:
                _, prior_error = self._original(conn, prior)
                before = self._readable(conn, prior) if not prior_error else ""
                after = self._readable(conn, v) if not source_error else ""
                if prior_error:
                    diagnostics.append({"code": "prior_source_unavailable", "severity": "warning", "page": None,
                        "block_ids": [], "asset_ids": [], "message": "上一版原件暂不可用，无法显示正文差异；当前原件可独立维护。", "blocks_review": False})
                diff = {"source_changed": prior["source_sha256"] != v["source_sha256"],
                    "applicability_changed": prior["applicability_sha256"] != v["applicability_sha256"],
                    "before_applicabilities": self._bindings(conn, prior), "after_applicabilities": self._bindings(conn, v),
                    "text_diff": "\n".join(difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="")) if not prior_error and not source_error and (text is not None or before and after) else None}
            active = publication(conn, self.workspace_id, v["document_id"])
            return {"version": version_view(v, bool(active and active["version_id"] == v["id"])), "blocks": parsed, "diagnostics": diagnostics,
                "assets": [{"id": str(a["object_id"]), "asset_key": a["asset_key"], "media_type": a["media_type"],
                    "kind": a["kind"], "page": a["page"], "url": f"/api/v1/knowledge/assets/{a['object_id']}"} for a in assets],
                "applicabilities": self._bindings(conn, v),
                "review": {k: review[k] for k in ("actor", "note", "excluded_block_ids", "exclusion_reason", "created_at")} if review else None,
                "jobs": [job_view(j) for j in task_rows], "source_url": f"/api/v1/knowledge/versions/{identity}/source",
                "source_available": source_error is None, "source_text": text, "policy": {k: policy[k] for k in ("rules", "description", "rules_sha256", "schema_sha256", "description_sha256", "generator_version")} if policy else None,
                "diff": diff}

    def source(self, identity):
        self._available()
        with self.engine.connect() as conn:
            v = version(conn, self.workspace_id, identity)
            content, obj = KnowledgeFiles(self.store, self.workspace_id).read(conn, v["object_id"])
            return content, {"pdf": "application/pdf", "md": "text/plain; charset=utf-8", "json": "application/json", "jsonl": "text/plain; charset=utf-8"}[v["format"]], v["format"]

    def asset(self, identity):
        self._available()
        with self.engine.connect() as conn:
            row = conn.execute(sa.select(knowledge_assets).where(knowledge_assets.c.object_id == identity,
                knowledge_assets.c.kind != "raw", *scoped_where(knowledge_assets, self.workspace_id))).mappings().first()
            if row is None:
                raise ServiceError("asset_not_found", 404)
            # An asset must still be referenced by an active knowledge version/document in this workspace.
            refs = conn.execute(sa.select(document_versions).join(documents, documents.c.id == document_versions.c.document_id)
                .where(document_versions.c.cache_id == row["cache_id"], documents.c.lifecycle == "active",
                    *scoped_where(document_versions, self.workspace_id))).mappings().all()
            if not any(not v["page_range"] or row["page"] and v["page_range"][0] <= row["page"] <= v["page_range"][1] for v in refs):
                raise ServiceError("asset_not_found", 404)
            return KnowledgeFiles(self.store, self.workspace_id).read(conn, identity)[0], row["media_type"]
