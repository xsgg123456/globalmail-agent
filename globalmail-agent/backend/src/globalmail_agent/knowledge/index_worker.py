"""Build batches stage under lease guards; provider calls hold no DB transaction."""
from uuid import uuid4
import math
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from globalmail_agent.adapters.knowledge_index_schema import index_builds, index_chunks, embedding_cache, embedding_probes
from globalmail_agent.adapters.conversation_schema import jobs
from globalmail_agent.knowledge.base import scope, scoped_where, audit, sha, canonical
from globalmail_agent.knowledge.build_checks import build_row, plan, manifest
from globalmail_agent.knowledge.index_profiles import load_profile, verify_gateway
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.worker.leases import release_slot


def validate_vector(vector):
    if (len(vector) != 1024 or any(not math.isfinite(float(x)) for x in vector)
            or abs(sum(float(x) ** 2 for x in vector) - 1) > 0.002):
        raise ServiceError("invalid_embedding_vector", 503)
    return [float(x) for x in vector]


def check_input(conn, service, job):
    guard = service._guard(conn, job)
    if not guard:
        raise ServiceError("embedding_cancelled")
    _, _, v, _ = guard
    build = build_row(conn, service.workspace_id, job["index_build_id"], True)
    parents = plan(conn, service.store, service.workspace_id, v, build["chunker_configuration"])
    if sha(canonical(parents)) != build["input_sha256"]:
        raise ServiceError("index_input_changed")
    return guard, build


def execute_index(service, gateway, job, current, stopped):
    workspace = service.workspace_id
    # The source read occurs after the durable claim, so faults reach bounded retry.
    service.source(job)
    with service.engine.connect() as conn:
        build = build_row(conn, workspace, job["index_build_id"])
        profile = load_profile(conn, workspace, build["profile_id"])
    verify_gateway(gateway, profile)
    while True:
        if stopped() or not current():
            raise ServiceError("embedding_cancelled")
        with service.engine.begin() as conn:
            _, build = check_input(conn, service, job)
            rows = conn.execute(sa.select(index_chunks).where(index_chunks.c.build_id == build["id"],
                index_chunks.c.cache_id.is_(None), *scoped_where(index_chunks, workspace)).order_by(index_chunks.c.position)).mappings().all()
            missing, hits = [], 0
            for row in rows:
                cache = conn.execute(sa.select(embedding_cache).where(embedding_cache.c.profile_id == build["profile_id"],
                    embedding_cache.c.input_sha256 == row["input_sha256"], *scoped_where(embedding_cache, workspace))).mappings().first()
                if cache:
                    if cache["input_text"] != row["input_text"]:
                        raise ServiceError("cache_integrity_error", 503)
                    conn.execute(index_chunks.update().where(index_chunks.c.id == row["id"]).values(cache_id=cache["id"]))
                    hits += 1
                elif len(missing) < 9:
                    missing.append(dict(row))
            if hits:
                conn.execute(index_builds.update().where(index_builds.c.id == build["id"]).values(cache_hits=index_builds.c.cache_hits + hits))
            if not service._guard(conn, job):
                raise ServiceError("embedding_cancelled")
            profile = load_profile(conn, workspace, build["profile_id"])
        if not missing:
            break
        output = gateway.embed(profile, [row["input_text"] for row in missing], current=current, stopped=stopped)
        if len(output["vectors"]) != len(missing):
            raise ServiceError("invalid_embedding_vector", 503)
        vectors = [validate_vector(v) for v in output["vectors"]]
        probe = validate_vector(output["probe_vector"])
        with service.engine.begin() as conn:
            _, build = check_input(conn, service, job)
            baseline = conn.execute(sa.select(embedding_probes.c.probe_vector).where(embedding_probes.c.profile_id == build["profile_id"],
                *scoped_where(embedding_probes, workspace))).scalar_one_or_none()
            if baseline is not None and sum(float(a) * b for a, b in zip(baseline, probe)) < profile.get("probe_min_cosine", 0.9995):
                raise ServiceError("embedding_model_drift", 503)
            if baseline is None:
                conn.execute(sa.insert(embedding_probes).values(id=uuid4(), **scope(workspace), profile_id=build["profile_id"], probe_vector=probe))
            for row, vector in zip(missing, vectors):
                conn.execute(pg_insert(embedding_cache).values(id=uuid4(), **scope(workspace), profile_id=build["profile_id"],
                    input_sha256=row["input_sha256"], input_text=row["input_text"], vector=vector).on_conflict_do_nothing())
                cached_id = conn.execute(sa.select(embedding_cache.c.id).where(embedding_cache.c.profile_id == build["profile_id"],
                    embedding_cache.c.input_sha256 == row["input_sha256"], *scoped_where(embedding_cache, workspace))).scalar_one()
                conn.execute(index_chunks.update().where(index_chunks.c.id == row["id"]).values(cache_id=cached_id))
            usage = [*build["usage"], {"request_id": output.get("request_id"), "usage": output.get("usage"), "seconds": output.get("seconds")}]
            conn.execute(index_builds.update().where(index_builds.c.id == build["id"]).values(usage=usage,
                embedded_count=index_builds.c.embedded_count + len(missing), row_version=index_builds.c.row_version + 1))
            if not service._guard(conn, job):
                raise ServiceError("embedding_cancelled")
    with service.engine.begin() as conn:
        guard, build = check_input(conn, service, job)
        slot, task, v, doc = guard
        digest = sha(canonical(manifest(conn, workspace, build)))
        conn.execute(index_builds.update().where(index_builds.c.id == build["id"]).values(status="ready", stage="ready",
            manifest_sha256=digest, error_code=None, retryable=False, row_version=index_builds.c.row_version + 1))
        conn.execute(jobs.update().where(jobs.c.id == job["id"]).values(status="completed", stage="ready", row_version=jobs.c.row_version + 1,
            error_code=None, retryable=False, lease_owner=None, lease_expires_at=None))
        # Recheck after all writes; expiry during staging rolls back the whole transaction.
        if not service._guard_ready(conn, job):
            raise ServiceError("embedding_cancelled")
        audit(conn, workspace, doc["id"], v["id"], "index.ready", {"build_id": str(build["id"]), "manifest_sha256": digest})
        release_slot(conn, slot)
