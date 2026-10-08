"""Explicit human review of current source, parse and applicability digests."""
import sqlalchemy as sa
from uuid import uuid4
from globalmail_agent.adapters.knowledge_schema import document_versions, applicabilities, blocks, knowledge_reviews
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.application.idempotency import prior, remember
from globalmail_agent.knowledge.base import scope, scoped_where, document, version, audit, KnowledgeFiles
from globalmail_agent.worker.leases import slot_for_update


class ReviewService:
    def __init__(self, engine, store, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.workspace_id = engine, store, workspace_id

    def review(self, identity, command, key):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)
        operation = "knowledge-review:" + str(identity)
        with self.engine.begin() as conn:
            previous, digest = prior(conn, self.workspace_id, key, operation, command.model_dump(mode="json"))
            if previous is not None:
                return previous
            slot_for_update(conn, self.workspace_id, "knowledge")
            v = version(conn, self.workspace_id, identity)
            doc = document(conn, self.workspace_id, v["document_id"], lock=True)
            v = version(conn, self.workspace_id, identity, command.expected_version, True)
            if doc["current_version_id"] != identity:
                raise ServiceError("version_superseded")
            if v["status"] != "needs_review" or not v["parse_sha256"]:
                raise ServiceError("parse_not_completed")
            if any(getattr(command, k) != v[k] for k in ("source_sha256", "parse_sha256", "applicability_sha256")):
                raise ServiceError("review_digest_mismatch")
            KnowledgeFiles(self.store, self.workspace_id).read(conn, v["object_id"])
            bindings = conn.execute(sa.select(applicabilities).where(applicabilities.c.version_id == identity,
                *scoped_where(applicabilities, self.workspace_id))).mappings().all()
            parsed = conn.execute(sa.select(blocks).where(blocks.c.version_id == identity,
                blocks.c.parse_generation == v["parse_generation"], *scoped_where(blocks, self.workspace_id))).mappings().all()
            if not bindings or not parsed:
                raise ServiceError("incomplete_applicability")
            excluded = set(command.excluded_block_ids)
            if len(excluded) != len(command.excluded_block_ids) or not excluded <= {b["block_key"] for b in parsed}:
                raise ServiceError("invalid_exclusion", 422)
            if excluded and (not command.exclusion_reason or not command.exclusion_reason.strip()):
                raise ServiceError("exclusion_reason_required", 422)
            for diagnostic in v["diagnostics"]:
                if diagnostic.get("blocks_review") or diagnostic.get("severity") == "error":
                    affected = set(diagnostic.get("block_ids", []))
                    if not affected or not affected <= excluded:
                        raise ServiceError("incomplete_parse")
            retained = [b for b in parsed if b["block_key"] not in excluded]
            if not retained:
                raise ServiceError("empty_reviewed_content")
            for block in retained:
                matched = [a for a in bindings if a["section_id"] in {"document", block["section_id"]}
                    and (block["page"] is None or a["page_start"] <= block["page"] <= a["page_end"])]
                if not matched:
                    raise ServiceError("unbound_section")
            conn.execute(sa.insert(knowledge_reviews).values(id=uuid4(), **scope(self.workspace_id), version_id=identity,
                parse_generation=v["parse_generation"], source_sha256=v["source_sha256"], parse_sha256=v["parse_sha256"],
                applicability_sha256=v["applicability_sha256"], actor="local_operator", note=command.note,
                excluded_block_ids=command.excluded_block_ids, exclusion_reason=command.exclusion_reason))
            revision = v["row_version"] + 1
            conn.execute(document_versions.update().where(document_versions.c.id == identity).values(status="reviewed", row_version=revision))
            audit(conn, self.workspace_id, doc["id"], identity, "version.reviewed", {"excluded_block_ids": sorted(excluded),
                "exclusion_reason": command.exclusion_reason, "parse_sha256": v["parse_sha256"]})
            result = {"document_id": str(doc["id"]), "version_id": str(identity), "version": revision, "status": "reviewed", "published": False}
            remember(conn, self.workspace_id, key, operation, digest, result)
            return result
