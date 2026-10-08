"""Immutable safe embedding configuration and explicit proxy-token chunkers."""
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_index_schema import embedding_profiles, embedding_probes
from globalmail_agent.knowledge.base import canonical, sha, scope, scoped_where
from globalmail_agent.application.conversation_lock import ServiceError

CHUNKERS = [{"key": f"structure_v1_{target}", "label": f"结构切分 {target} 代理tokens",
    "target_tokens": target, "max_tokens": 1000, "parent_tokens": 2000, "short_input_max_tokens": 2500,
    "estimator": "ascii1_nonascii2/1", "revision": "structure/4"} for target in (500, 300)]


def chunker(key):
    match = next((p for p in CHUNKERS if p["key"] == key), None)
    if match is None:
        raise ServiceError("invalid_chunking_profile", 422)
    return match


def configuration(profile):
    return {k: v for k, v in profile.items() if k not in {"available", "probe_vector", "id", "profile_sha256"}}


def save_profile(conn, workspace, gateway, key):
    match = next((p for p in gateway.profiles() if p["key"] == key), None) if gateway else None
    if match is None or not match["available"]:
        raise ServiceError("embedding_unavailable", 503)
    config = configuration(match)
    if config["dimensions"] != 1024:
        raise ServiceError("invalid_embedding_profile", 422)
    digest = sha(canonical(config))
    row = conn.execute(sa.select(embedding_profiles).where(*scoped_where(embedding_profiles, workspace),
        embedding_profiles.c.profile_sha256 == digest)).mappings().first()
    if row:
        return dict(row)
    values = {"id": uuid4(), **scope(workspace), "profile_key": key, "profile_sha256": digest,
        "configuration": config, "dimensions": config["dimensions"]}
    conn.execute(sa.insert(embedding_profiles).values(**values))
    return values


def load_profile(conn, workspace, identity):
    row = conn.execute(sa.select(embedding_profiles).where(embedding_profiles.c.id == identity,
        *scoped_where(embedding_profiles, workspace))).mappings().first()
    if not row or sha(canonical(row["configuration"])) != row["profile_sha256"]:
        raise ServiceError("profile_integrity_error", 503)
    probe = conn.execute(sa.select(embedding_probes.c.probe_vector).where(embedding_probes.c.profile_id == identity,
        *scoped_where(embedding_probes, workspace))).scalar_one_or_none()
    return {**row["configuration"], "id": row["id"], "profile_sha256": row["profile_sha256"],
        **({"probe_vector": list(probe)} if probe is not None else {})}


def verify_gateway(gateway, profile):
    match = next((p for p in gateway.profiles() if p["key"] == profile["key"]), None) if gateway else None
    if not match or not match["available"] or sha(canonical(configuration(match))) != profile["profile_sha256"]:
        raise ServiceError("embedding_configuration_changed", 503)
