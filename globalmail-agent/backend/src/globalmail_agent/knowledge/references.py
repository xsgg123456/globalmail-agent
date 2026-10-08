"""Register every exposed body dependency before returning evidence; recheck current eligibility."""
from uuid import UUID, uuid5, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_index_schema import evidence_refs, knowledge_dependencies
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.knowledge.base import scope, scoped_where, KnowledgeFiles, canonical, sha, document
from globalmail_agent.knowledge.build_checks import build_row, eligible
from globalmail_agent.knowledge.release_queries import head, publication


def register_reference(conn, files, workspace, current, build, doc, v, parent, child, score):
    identity = uuid5(current["release_id"], canonical([str(parent["id"]), parent["content_sha256"]]).decode())
    stored = conn.execute(sa.select(evidence_refs).where(evidence_refs.c.id == identity,
        *scoped_where(evidence_refs, workspace))).mappings().first()
    if stored:
        return {**stored["reference"], "score": score}
    locations = parent["locations"]
    reference = {"evidence_id": str(identity), "release_id": str(current["release_id"]), "release_epoch": current["epoch"],
        "document_id": str(doc["id"]), "version_id": str(v["id"]), "version_number": v["number"],
        "applicability_revision": v["applicability_sha256"], "build_id": str(build["id"]),
        "embedding_profile_id": str(build["profile_id"]), "chunk_id": str(child["id"]), "parent_id": str(parent["id"]),
        "source_sha256": v["source_sha256"], "content_hash": parent["content_sha256"],
        "page": sorted({p["page"] for p in locations if p["page"] is not None}), "section": parent["section_id"],
        "figure": sorted({p["figure_id"] for p in locations if p.get("figure_id")}), "locations": locations,
        "source_kind": doc["source_kind"], "allowed_scope": {k: str(value) for k, value in scope(workspace).items()},
        "allowed_modes": doc["allowed_modes"], "available_at": v["available_at"].isoformat(),
        "observed_at": conn.execute(sa.select(sa.func.clock_timestamp())).scalar_one().isoformat(),
        "completeness": "reviewed_complete", "applicability": parent["applicability"], "title": v["title"],
        "text": parent["text"], "score": score, "revocation_epoch": doc["revocation_epoch"]}
    object_id = files.put(conn, canonical(reference), "knowledge_evidence_body", str(identity), (v["object_id"],))
    conn.execute(sa.insert(evidence_refs).values(id=identity, **scope(workspace), release_id=current["release_id"],
        build_id=build["id"], document_id=doc["id"], revocation_epoch=doc["revocation_epoch"], content_object_id=object_id, reference=reference))
    conn.execute(sa.insert(knowledge_dependencies).values(id=uuid4(), **scope(workspace), reference_id=identity,
        source_object_id=v["object_id"], content_object_id=object_id, holder_kind="search_preview"))
    return reference


class ReferenceService:
    def __init__(self, engine, store, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.workspace_id = engine, store, workspace_id

    def get(self, identity):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)
        with self.engine.connect() as conn:
            row = conn.execute(sa.select(evidence_refs).where(evidence_refs.c.id == identity,
                *scoped_where(evidence_refs, self.workspace_id))).mappings().first()
            if not row:
                raise ServiceError("reference_not_found", 404)
            doc = document(conn, self.workspace_id, row["document_id"])
            reason = "ok"
            if doc["withdrawn"] or doc["revocation_epoch"] != row["revocation_epoch"]:
                reason = "document_withdrawn"
            else:
                current = publication(conn, self.workspace_id, doc["id"])
                if not current or current["release_id"] != row["release_id"] or current["build_id"] != row["build_id"]:
                    reason = "stale_release"
                else:
                    try:
                        eligible(conn, self.store, self.workspace_id, build_row(conn, self.workspace_id, row["build_id"]))
                        raw, _ = KnowledgeFiles(self.store, self.workspace_id).read(conn, row["content_object_id"])
                        if sha(raw) != sha(canonical(row["reference"])):
                            raise ServiceError("reference_integrity_error", 503)
                    except ServiceError as error:
                        reason = error.code
            return {"reference": row["reference"], "eligible": reason == "ok", "reason": reason}
