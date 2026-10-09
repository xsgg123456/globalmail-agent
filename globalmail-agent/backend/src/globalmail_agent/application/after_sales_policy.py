"""Only a currently published, reviewed, applicable policy bundle can authorize writes."""
from uuid import UUID
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_index_schema import knowledge_releases, knowledge_release_items
from globalmail_agent.adapters.knowledge_schema import applicabilities
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.base import canonical, sha, scoped_where
from globalmail_agent.knowledge.release_queries import head, release_row
from globalmail_agent.knowledge.build_checks import build_row, eligible
from globalmail_agent.knowledge.policy_bundle import bundle
from globalmail_agent.domain.orders import timestamp


def published_policy(conn, store, workspace, context, model, selected):
    current = head(conn, workspace)
    if (not context.release_id or current["release_id"] != context.release_id
            or current["epoch"] != context.release_epoch):
        raise ServiceError("published_policy_required", 422)
    release = release_row(conn, workspace, context.release_id)
    if sha(canonical(release["manifest"])) != release["manifest_sha256"]:
        raise ServiceError("policy_manifest_invalid", 503)
    policy_profile = model["policy"]
    if not policy_profile:
        raise ServiceError("branch_policy_required", 422)
    matches = []
    for entry in release["manifest"]["entries"]:
        data = entry.get("policy_bundle")
        if not data or data["rules"]["policy_id"] != policy_profile["policy_id"] or data["rules"]["version"] != policy_profile["version"]:
            continue
        build = build_row(conn, workspace, UUID(entry["build_id"]))
        doc, version, actual = eligible(conn, store, workspace, build)
        if any(entry.get(key) != expected for key, expected in {
                "source_sha256": version["source_sha256"], "parse_sha256": version["parse_sha256"],
                "index_manifest_sha256": build["manifest_sha256"],
                "applicability_revision": version["applicability_sha256"],
                "brand": doc["brand"], "usage_split": doc["usage_split"], "allowed_modes": doc["allowed_modes"],
                "available_at": version["available_at"].isoformat()}.items()):
            raise ServiceError("policy_manifest_invalid", 422)
        linked = conn.execute(sa.select(knowledge_release_items.c.id).where(
            knowledge_release_items.c.release_id == context.release_id,
            knowledge_release_items.c.document_id == doc["id"], knowledge_release_items.c.build_id == UUID(entry["build_id"]),
            knowledge_release_items.c.revocation_epoch == doc["revocation_epoch"],
            *scoped_where(knowledge_release_items, workspace))).scalar_one_or_none()
        if not linked or doc["withdrawn"] or doc["lifecycle"] != "active" or doc["revocation_epoch"] != entry["revocation_epoch"]:
            raise ServiceError("policy_revoked", 422)
        line, order = selected[1:]
        if (doc["usage_split"] != "rag" or context.mode not in doc["allowed_modes"]
                or entry["usage_split"] != "rag" or context.mode not in entry["allowed_modes"]
                or doc["brand"] not in {None, order["brand"]} or version["available_at"] > context.as_of):
            raise ServiceError("policy_out_of_scope", 422)
        binding = conn.execute(sa.select(applicabilities.c.id).where(applicabilities.c.version_id == version["id"],
            applicabilities.c.sku == line["sku"], *scoped_where(applicabilities, workspace))).first()
        if not binding:
            raise ServiceError("policy_sku_not_covered", 422)
        expected = bundle(data["rules"], generator_version=data["generator_version"])
        if any(expected[k] != data[k] or actual[k] != data[k] for k in expected):
            raise ServiceError("policy_bundle_mismatch", 422)
        if any(entry[k] != str(value) for k, value in (("document_id", doc["id"]), ("version_id", version["id"]))):
            raise ServiceError("policy_manifest_invalid", 422)
        matches.append(data)
    if len(matches) != 1:
        raise ServiceError("published_policy_ambiguous" if matches else "published_policy_required", 422)
    return matches[0]
