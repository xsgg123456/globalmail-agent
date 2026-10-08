"""Source/review/manifest integrity checks shared by worker, release and retrieval."""
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_schema import knowledge_reviews, blocks, applicabilities, parse_caches, policy_bundles
from globalmail_agent.adapters.knowledge_index_schema import index_builds, index_parents, index_chunks, embedding_cache
from globalmail_agent.knowledge.base import scoped_where, canonical, sha, KnowledgeFiles, version, document
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.chunking import chunks


def reviewed(conn, workspace, v):
    review = conn.execute(sa.select(knowledge_reviews).where(knowledge_reviews.c.version_id == v["id"],
        knowledge_reviews.c.parse_generation == v["parse_generation"], *scoped_where(knowledge_reviews, workspace))).mappings().first()
    if (v["status"] != "reviewed" or not review or
            any(review[k] != v[k] for k in ("source_sha256", "parse_sha256", "applicability_sha256"))):
        raise ServiceError("review_required")
    return review


def original(conn, store, workspace, v):
    files = KnowledgeFiles(store, workspace)
    raw, obj = files.read(conn, v["object_id"])
    if sha(raw) != v["source_sha256"]:
        raise ServiceError("source_integrity_error", 503)
    cache = conn.execute(sa.select(parse_caches).where(parse_caches.c.id == v["cache_id"],
        *scoped_where(parse_caches, workspace))).mappings().first()
    if not cache or cache["source_sha256"] != v["source_sha256"]:
        raise ServiceError("cache_integrity_error", 503)
    raw, _ = files.read(conn, cache["result_object_id"])
    if sha(raw) != cache["parse_sha256"]:
        raise ServiceError("cache_integrity_error", 503)


def plan(conn, store, workspace, v, chunker):
    review = reviewed(conn, workspace, v)
    original(conn, store, workspace, v)
    parsed = conn.execute(sa.select(blocks).where(blocks.c.version_id == v["id"],
        blocks.c.parse_generation == v["parse_generation"], *scoped_where(blocks, workspace)).order_by(blocks.c.position)).mappings().all()
    bindings = conn.execute(sa.select(applicabilities).where(applicabilities.c.version_id == v["id"],
        *scoped_where(applicabilities, workspace))).mappings().all()
    doc = document(conn, workspace, v["document_id"])
    if doc["document_type"] == "policy_json":
        policy_for_index(conn, store, workspace, v)
    return chunks(v["title"], parsed, bindings, set(review["excluded_block_ids"]), chunker,
                  safety_context=doc["document_type"] != "policy_json")


def policy_for_index(conn, store, workspace, v, verify_source=True):
    from globalmail_agent.knowledge.policy_bundle import parse_policy, bundle, GENERATOR_VERSION
    policy = conn.execute(sa.select(policy_bundles).where(policy_bundles.c.version_id == v["id"],
        *scoped_where(policy_bundles, workspace))).mappings().first()
    if not policy:
        raise ServiceError("policy_bundle_mismatch")
    generator = policy["generator_version"]
    expected = (parse_policy(KnowledgeFiles(store, workspace).read(conn, v["object_id"])[0], generator_version=generator)
                if verify_source else bundle(policy["rules"], generator_version=generator))
    keys = ("rules", "rule_schema", "rules_sha256", "schema_sha256", "generator_version", "description", "description_sha256")
    if any(policy[k] != expected[k] for k in keys):
        raise ServiceError("policy_bundle_mismatch")
    if generator != GENERATOR_VERSION:
        raise ServiceError("policy_description_requires_revision")
    return policy


def build_row(conn, workspace, identity, lock=False):
    query = sa.select(index_builds).where(index_builds.c.id == identity, *scoped_where(index_builds, workspace))
    row = conn.execute(query.with_for_update() if lock else query).mappings().first()
    if row is None:
        raise ServiceError("build_not_found", 404)
    return dict(row)


def manifest(conn, workspace, build):
    parents = conn.execute(sa.select(index_parents).where(index_parents.c.build_id == build["id"],
        *scoped_where(index_parents, workspace)).order_by(index_parents.c.position)).mappings().all()
    child_rows = conn.execute(sa.select(index_chunks).where(index_chunks.c.build_id == build["id"],
        *scoped_where(index_chunks, workspace)).order_by(index_chunks.c.position)).mappings().all()
    if not parents or len(child_rows) != build["chunk_count"] or any(c["cache_id"] is None for c in child_rows):
        raise ServiceError("incomplete_index")
    for parent in parents:
        if sha(parent["text"].encode()) != parent["content_sha256"]:
            raise ServiceError("index_integrity_error", 503)
    for child in child_rows:
        cached = conn.execute(sa.select(embedding_cache).where(embedding_cache.c.id == child["cache_id"],
            *scoped_where(embedding_cache, workspace))).mappings().one()
        if (cached["profile_id"] != build["profile_id"] or cached["input_text"] != child["input_text"]
                or cached["input_sha256"] != child["input_sha256"] or sha(child["input_text"].encode()) != child["input_sha256"]):
            raise ServiceError("index_integrity_error", 503)
    return {"build_id": str(build["id"]), "version_id": str(build["version_id"]), "profile_id": str(build["profile_id"]),
        "input_sha256": build["input_sha256"], "parents": [{"id": str(p["id"]), "content_sha256": p["content_sha256"],
            "applicability": p["applicability"], "locations": p["locations"]} for p in parents],
        "chunks": [{"id": str(c["id"]), "parent_id": str(c["parent_id"]), "input_sha256": c["input_sha256"],
            "cache_id": str(c["cache_id"])} for c in child_rows]}


def eligible(conn, store, workspace, build, verify_source=True):
    doc = document(conn, workspace, build["document_id"])
    v = version(conn, workspace, build["version_id"])
    reviewed(conn, workspace, v)
    if build["status"] != "ready" or build["revocation_epoch"] != doc["revocation_epoch"]:
        raise ServiceError("build_not_eligible")
    if any(build[k] != v[k] for k in ("source_sha256", "parse_sha256", "applicability_sha256", "parse_generation")):
        raise ServiceError("build_not_eligible")
    if verify_source:
        original(conn, store, workspace, v)
    digest = sha(canonical(manifest(conn, workspace, build)))
    if digest != build["manifest_sha256"]:
        raise ServiceError("manifest_integrity_error", 503)
    policy = policy_for_index(conn, store, workspace, v, verify_source) if doc["document_type"] == "policy_json" else None
    return doc, v, policy
