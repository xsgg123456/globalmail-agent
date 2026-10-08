"""Knowledge lease/fence, bounded retries and cached physical parser completion."""
from datetime import timedelta
from uuid import UUID
import sqlalchemy as sa
from globalmail_agent.adapters.conversation_schema import jobs, agent_slots
from globalmail_agent.adapters.knowledge_schema import document_versions, documents
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.knowledge.base import scoped_where, document, version, KnowledgeFiles, ensure_slot, audit
from globalmail_agent.knowledge.queue import KnowledgeQueue
from globalmail_agent.knowledge.cache import find_cache, save_cache, project
from globalmail_agent.worker.leases import slot_for_update, valid_lease, release_slot, db_now


class KnowledgeJobService(KnowledgeQueue):
    def __init__(self, engine, store, workspace_id=DEFAULT_WORKSPACE_ID):
        super().__init__(engine, workspace_id)
        self.store = store

    def _current(self, conn, job):
        v = conn.execute(sa.select(document_versions).where(document_versions.c.id == job["knowledge_version_id"],
            *scoped_where(document_versions, self.workspace_id))).mappings().first()
        if v is None:
            return False, None, None
        doc = conn.execute(sa.select(documents).where(documents.c.id == v["document_id"],
            *scoped_where(documents, self.workspace_id)).with_for_update()).mappings().first()
        v = conn.execute(sa.select(document_versions).where(document_versions.c.id == v["id"],
            *scoped_where(document_versions, self.workspace_id)).with_for_update()).mappings().one()
        valid = (doc is not None and doc["lifecycle"] == "active" and doc["current_version_id"] == v["id"] and doc["document_fence"] == job["document_fence"]
            and v["parse_generation"] == job["parse_generation"] and v["parser_profile_id"] == job["parser_profile_id"])
        return valid, v, doc

    def claim(self, owner):
        self._available()
        with self.engine.begin() as conn:
            ensure_slot(conn, self.workspace_id)
            slot = slot_for_update(conn, self.workspace_id, "knowledge", skip_locked=True)
            if not slot:
                return None
            now = db_now(conn)
            if slot["job_id"]:
                if slot["lease_expires_at"] and slot["lease_expires_at"] > now:
                    return None
                legacy = conn.execute(sa.select(jobs.c.knowledge_version_id).where(jobs.c.id == slot["job_id"])).scalar_one_or_none()
                if legacy is None:
                    return None
                old = self._job(conn, slot["job_id"])
                self._failed(conn, slot, old, "worker_interrupted", True, now)
                slot = slot_for_update(conn, self.workspace_id, "knowledge")
            candidate = conn.execute(sa.select(jobs).where(jobs.c.kind == "knowledge", jobs.c.knowledge_version_id.is_not(None),
                jobs.c.status == "queued", sa.or_(jobs.c.not_before.is_(None), jobs.c.not_before <= now),
                *scoped_where(jobs, self.workspace_id)).order_by(jobs.c.created_at, jobs.c.id).limit(1)).mappings().first()
            if not candidate:
                return None
            valid, v, doc = self._current(conn, candidate)
            job = self._job(conn, candidate["id"], True)
            if not valid or job["status"] != "queued":
                conn.execute(jobs.update().where(jobs.c.id == job["id"]).values(status="cancelled", stage="superseded", retryable=False,
                    error_code="version_superseded", row_version=job["row_version"] + 1))
                return None
            fence, expiry = slot["fence"] + 1, now + timedelta(seconds=90)
            conn.execute(agent_slots.update().where(agent_slots.c.id == slot["id"]).values(job_id=job["id"], lease_owner=owner,
                lease_expires_at=expiry, fence=fence))
            changes = {"status": "running", "stage": "parsing", "lease_owner": owner, "lease_expires_at": expiry,
                "slot_fence": fence, "row_version": job["row_version"] + 1}
            conn.execute(jobs.update().where(jobs.c.id == job["id"]).values(**changes))
            return {**job, **changes, "version_id": v["id"], "source_sha256": v["source_sha256"], "object_id": v["object_id"],
                "format": v["format"], "parser_fingerprint": v["parser_fingerprint"]}

    def source(self, job):
        # Claim has committed, so an I/O fault can be persisted and release the slot.
        with self.engine.connect() as conn:
            return KnowledgeFiles(self.store, self.workspace_id).read(conn, job["object_id"])[0]

    def heartbeat(self, job, owner, fence):
        identity = job["id"] if isinstance(job, dict) else job
        with self.engine.begin() as conn:
            slot = slot_for_update(conn, self.workspace_id, "knowledge")
            now = db_now(conn)
            if not valid_lease(slot, identity, owner, fence, now):
                return False
            row = self._job(conn, identity)
            valid, v, doc = self._current(conn, row)
            if row["status"] != "running" or not valid:
                return False
            expiry = now + timedelta(seconds=90)
            conn.execute(agent_slots.update().where(agent_slots.c.id == slot["id"]).values(lease_expires_at=expiry))
            conn.execute(jobs.update().where(jobs.c.id == identity).values(lease_expires_at=expiry))
            return True

    def recover_expired(self, *, restart=False):
        with self.engine.begin() as conn:
            ensure_slot(conn, self.workspace_id)
            slot = slot_for_update(conn, self.workspace_id, "knowledge")
            now = db_now(conn)
            if not slot or not slot["job_id"] or not restart and slot["lease_expires_at"] and slot["lease_expires_at"] > now:
                return []
            legacy = conn.execute(sa.select(jobs.c.knowledge_version_id).where(jobs.c.id == slot["job_id"])).scalar_one_or_none()
            if legacy is None:
                return []
            job = self._job(conn, slot["job_id"])
            if job["status"] == "running":
                self._failed(conn, slot, job, "worker_interrupted", True, now)
            else:
                release_slot(conn, slot)
            return [job["id"]]

    def _guard(self, conn, job):
        slot = slot_for_update(conn, self.workspace_id, "knowledge")
        if not valid_lease(slot, job["id"], job["lease_owner"], job["slot_fence"], db_now(conn)):
            return None
        current = self._job(conn, job["id"])
        valid, v, doc = self._current(conn, current)
        if not valid or current["status"] != "running" or v["source_sha256"] != job["source_sha256"]:
            return None
        return slot, current, v, doc

    def complete(self, job, result, artifact_dir=None):
        with KnowledgeFiles(self.store, self.workspace_id) as files, self.engine.begin() as conn:
            guard = self._guard(conn, job)
            if not guard:
                return False
            slot, current, v, doc = guard
            cache = find_cache(conn, self.workspace_id, v)
            if isinstance(result, dict) and "_cache_id" in result:
                if not cache or str(cache["id"]) != result["_cache_id"]:
                    raise ServiceError("cache_integrity_error", 503)
            else:
                result = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
                cache = save_cache(conn, files, self.workspace_id, v, result, artifact_dir)
            digest = project(conn, files, self.workspace_id, v, cache)
            if not self._guard(conn, job):
                raise ServiceError("lease_expired")
            conn.execute(jobs.update().where(jobs.c.id == job["id"]).values(status="completed", stage="needs_review",
                row_version=current["row_version"] + 1, error_code=None, retryable=False, lease_expires_at=None))
            audit(conn, self.workspace_id, doc["id"], v["id"], "parse.completed", {"job_id": str(job["id"]), "parse_sha256": digest})
            release_slot(conn, slot)
            return True

    def cached_result(self, job):
        with self.engine.connect() as conn:
            v = version(conn, self.workspace_id, job["knowledge_version_id"])
            cache = find_cache(conn, self.workspace_id, v)
            return {"_cache_id": str(cache["id"])} if cache else None

    def _failed(self, conn, slot, job, error_code, retryable, now):
        valid, v, doc = self._current(conn, job)
        auto = valid and retryable and job["attempt_no"] <= 3
        status = "queued" if auto else "failed" if valid else "cancelled"
        changes = {"status": status, "stage": "retry_wait" if auto else "failed", "error_code": error_code,
            "retryable": bool(retryable and valid), "row_version": job["row_version"] + 1,
            "lease_owner": None, "lease_expires_at": None}
        if auto:
            changes.update(attempt_no=job["attempt_no"] + 1,
                not_before=now + timedelta(seconds=(2, 10, 30)[job["attempt_no"] - 1]))
        conn.execute(jobs.update().where(jobs.c.id == job["id"]).values(**changes))
        if valid:
            conn.execute(document_versions.update().where(document_versions.c.id == v["id"])
                .values(status="parsing" if auto else "failed", row_version=v["row_version"] + 1))
            audit(conn, self.workspace_id, doc["id"], v["id"], "parse.failed", {"job_id": str(job["id"]), "error_code": error_code})
        release_slot(conn, slot)
        return auto

    def fail(self, job, error_code, retryable):
        safe_code = error_code if isinstance(error_code, str) and error_code.replace("_", "").isalnum() and len(error_code) <= 80 else "parser_failed"
        with self.engine.begin() as conn:
            guard = self._guard(conn, job)
            if not guard:
                return False
            slot, current, v, doc = guard
            self._failed(conn, slot, current, safe_code, retryable, db_now(conn))
            return True
