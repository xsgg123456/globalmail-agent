"""Knowledge enqueue/control transactions; no fake conversation or AgentRun."""
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.conversation_schema import jobs
from globalmail_agent.adapters.knowledge_schema import documents, document_versions
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.application.idempotency import prior, remember
from globalmail_agent.knowledge.base import scope, scoped_where, document, version, audit, ensure_slot
from globalmail_agent.knowledge.parser_profiles import fingerprint, profiles
from globalmail_agent.worker.leases import slot_for_update, release_slot


def job_view(job):
    return {"id": str(job["id"]), "kind": job["kind"], "version_id": str(job["knowledge_version_id"]),
        **{key: job[key] for key in ("status", "stage", "row_version", "attempt_no", "error_code", "retryable", "parser_profile_id")}}


def invalidate_document_jobs(conn, workspace, doc):
    version_ids = sa.select(document_versions.c.id).where(document_versions.c.document_id == doc["id"],
        *scoped_where(document_versions, workspace))
    active = conn.execute(sa.select(jobs).where(jobs.c.knowledge_version_id.in_(version_ids),
        jobs.c.status.in_(["queued", "running"]), *scoped_where(jobs, workspace))).mappings().all()
    slot = slot_for_update(conn, workspace, "knowledge")
    for job in active:
        conn.execute(jobs.update().where(jobs.c.id == job["id"]).values(status="cancelled", stage="superseded",
            retryable=False, error_code="new_version", lease_expires_at=None, row_version=jobs.c.row_version + 1))
        conn.execute(document_versions.update().where(document_versions.c.id == job["knowledge_version_id"])
            .values(status="cancelled", row_version=document_versions.c.row_version + 1))
        if slot and slot["job_id"] == job["id"]:
            release_slot(conn, slot)


class KnowledgeQueue:
    def __init__(self, engine, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.workspace_id = engine, workspace_id

    def _available(self):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)

    def _job(self, conn, identity, lock=False):
        query = sa.select(jobs).where(jobs.c.id == identity, jobs.c.knowledge_version_id.is_not(None),
            *scoped_where(jobs, self.workspace_id))
        row = conn.execute(query.with_for_update() if lock else query).mappings().first()
        if row is None:
            raise ServiceError("job_not_found", 404)
        return dict(row)

    def get(self, identity):
        self._available()
        with self.engine.connect() as conn:
            row = self._job(conn, identity)
            version(conn, self.workspace_id, row["knowledge_version_id"])
            return {"job": job_view(row)}

    def enqueue(self, identity, command, key):
        self._available()
        operation = "knowledge-parse:" + str(identity)
        with self.engine.begin() as conn:
            previous, digest = prior(conn, self.workspace_id, key, operation, command.model_dump(mode="json"))
            if previous is not None:
                return previous
            ensure_slot(conn, self.workspace_id)
            slot = slot_for_update(conn, self.workspace_id, "knowledge")
            v = version(conn, self.workspace_id, identity)
            doc = document(conn, self.workspace_id, v["document_id"], lock=True)
            v = version(conn, self.workspace_id, identity, command.expected_version, True)
            if doc["current_version_id"] != identity:
                raise ServiceError("version_superseded")
            profile = command.parser_profile_id
            match = "mineru_" if v["format"] == "pdf" else "policy" if doc["document_type"] == "policy_json" else "markdown"
            if not (profile.startswith(match) if match == "mineru_" else profile == match):
                raise ServiceError("parser_format_mismatch", 422)
            if not next(p["available"] for p in profiles() if p["id"] == profile):
                raise ServiceError("parser_unavailable", 503)
            invalidate_document_jobs(conn, self.workspace_id, doc)
            generation = v["parse_generation"] + 1
            jid = self._insert(conn, v, doc, profile, generation)
            revision = v["row_version"] + 1
            conn.execute(document_versions.update().where(document_versions.c.id == identity).values(status="parsing",
                row_version=revision, parse_generation=generation, parse_sha256=None, cache_id=None,
                parser_profile_id=profile, parser_fingerprint=fingerprint(profile), diagnostics=[]))
            audit(conn, self.workspace_id, doc["id"], identity, "parse.queued", {"job_id": str(jid), "generation": generation})
            result = {"document_id": str(doc["id"]), "version_id": str(identity), "job_id": str(jid), "version": revision}
            remember(conn, self.workspace_id, key, operation, digest, result)
            return result

    def _insert(self, conn, v, doc, profile=None, generation=None):
        identity = uuid4()
        conn.execute(sa.insert(jobs).values(id=identity, **scope(self.workspace_id), kind="knowledge", status="queued",
            attempt_no=1, knowledge_version_id=v["id"], parser_profile_id=profile or v["parser_profile_id"],
            parse_generation=generation or v["parse_generation"], document_fence=doc["document_fence"], stage="queued"))
        return identity

    def control(self, identity, action, command, key):
        self._available()
        operation = f"knowledge-job:{identity}:{action}"
        with self.engine.begin() as conn:
            previous, digest = prior(conn, self.workspace_id, key, operation, command.model_dump(mode="json"))
            if previous is not None:
                return previous
            slot = slot_for_update(conn, self.workspace_id, "knowledge")
            job = self._job(conn, identity)
            v = version(conn, self.workspace_id, job["knowledge_version_id"])
            doc = document(conn, self.workspace_id, v["document_id"], lock=True)
            v = version(conn, self.workspace_id, v["id"], lock=True)
            job = self._job(conn, identity, True)
            if job["row_version"] != command.expected_version:
                raise ServiceError("stale_version")
            if (doc["current_version_id"] != v["id"] or job["parse_generation"] != v["parse_generation"]
                    or doc["document_fence"] != job["document_fence"]):
                raise ServiceError("version_superseded")
            if action == "cancel":
                if job["status"] not in {"queued", "running"}:
                    raise ServiceError("job_not_active")
                changes = {"status": "cancelled", "stage": "cancelled", "error_code": "user_cancelled", "retryable": True}
                if slot and slot["job_id"] == identity:
                    release_slot(conn, slot)
                state = "cancelled"
            else:
                if job["status"] not in {"failed", "cancelled"} or not job["retryable"]:
                    raise ServiceError("retry_not_allowed")
                changes = {"status": "queued", "stage": "queued", "error_code": None,
                    "attempt_no": job["attempt_no"] + 1, "retryable": False, "not_before": None}
                state = "parsing"
            changes.update(row_version=job["row_version"] + 1, lease_owner=None, lease_expires_at=None)
            conn.execute(jobs.update().where(jobs.c.id == identity).values(**changes))
            conn.execute(document_versions.update().where(document_versions.c.id == v["id"])
                .values(status=state, row_version=v["row_version"] + 1, parse_sha256=None))
            audit(conn, self.workspace_id, doc["id"], v["id"], "job." + action, {"job_id": str(identity)})
            result = {"job": job_view({**job, **changes})}
            remember(conn, self.workspace_id, key, operation, digest, result)
            return result
