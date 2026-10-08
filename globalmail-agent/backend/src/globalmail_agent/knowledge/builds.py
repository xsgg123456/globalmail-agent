"""Explicit immutable index attempts; content review remains independent."""
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_index_schema import index_builds, index_parents, index_chunks, embedding_profiles
from globalmail_agent.adapters.conversation_schema import jobs
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.application.idempotency import prior, remember
from globalmail_agent.knowledge.base import scope, scoped_where, version, document, audit, canonical, sha, ensure_slot
from globalmail_agent.knowledge.index_profiles import chunker, save_profile
from globalmail_agent.knowledge.build_checks import plan, eligible
from globalmail_agent.knowledge.queue import KnowledgeQueue
from globalmail_agent.worker.leases import slot_for_update


class BuildService(KnowledgeQueue):
    def __init__(self, engine, store, gateway, workspace_id=DEFAULT_WORKSPACE_ID):
        super().__init__(engine, workspace_id)
        self.store, self.gateway = store, gateway

    def enqueue_build(self, identity, command, key):
        self._available()
        with self.engine.begin() as conn:
            previous, digest = prior(conn, self.workspace_id, key, "knowledge-build:" + str(identity), command.model_dump(mode="json"))
            if previous is not None:
                return previous
            ensure_slot(conn, self.workspace_id)
            slot_for_update(conn, self.workspace_id, "knowledge")
            v = version(conn, self.workspace_id, identity)
            doc = document(conn, self.workspace_id, v["document_id"], lock=True)
            v = version(conn, self.workspace_id, identity, command.expected_version, True)
            if doc["current_version_id"] != v["id"]:
                raise ServiceError("version_superseded")
            config = chunker(command.chunking_profile_key)
            parents = plan(conn, self.store, self.workspace_id, v, config)
            profile = save_profile(conn, self.workspace_id, self.gateway, command.embedding_profile_key)
            existing = conn.execute(sa.select(jobs.c.id).where(jobs.c.knowledge_version_id == identity,
                jobs.c.knowledge_operation == "index", jobs.c.status.in_(["queued", "running"]), *scoped_where(jobs, self.workspace_id))).first()
            if existing:
                raise ServiceError("build_already_active")
            identity_build = uuid4()
            conn.execute(sa.insert(index_builds).values(id=identity_build, **scope(self.workspace_id), document_id=doc["id"], version_id=v["id"],
                profile_id=profile["id"], chunker_key=config["key"], chunker_configuration=config,
                input_sha256=sha(canonical(parents)), **{k: v[k] for k in ("source_sha256", "parse_sha256", "applicability_sha256", "parse_generation")},
                document_fence=doc["document_fence"], revocation_epoch=doc["revocation_epoch"], status="queued", stage="queued",
                chunk_count=sum(len(p["children"]) for p in parents)))
            position = 0
            for parent_position, parent in enumerate(parents):
                pid = uuid4()
                conn.execute(sa.insert(index_parents).values(id=pid, **scope(self.workspace_id), build_id=identity_build,
                    position=parent_position, **{k: value for k, value in parent.items() if k != "children"}))
                for child in parent["children"]:
                    conn.execute(sa.insert(index_chunks).values(id=uuid4(), **scope(self.workspace_id), build_id=identity_build,
                        parent_id=pid, position=position, **child))
                    position += 1
            jid = self._insert(conn, v, doc)
            conn.execute(jobs.update().where(jobs.c.id == jid).values(knowledge_operation="index", index_build_id=identity_build))
            audit(conn, self.workspace_id, doc["id"], v["id"], "index.queued", {"build_id": str(identity_build), "job_id": str(jid)})
            result = {"document_id": str(doc["id"]), "version_id": str(v["id"]), "build_id": str(identity_build), "job_id": str(jid), "version": v["row_version"]}
            remember(conn, self.workspace_id, key, "knowledge-build:" + str(identity), digest, result)
            return result

    def status(self, identity):
        self._available()
        from globalmail_agent.knowledge.release_queries import publication
        with self.engine.connect() as conn:
            v = version(conn, self.workspace_id, identity)
            doc = document(conn, self.workspace_id, v["document_id"])
            rows = conn.execute(sa.select(index_builds, embedding_profiles.c.profile_key).join(embedding_profiles,
                embedding_profiles.c.id == index_builds.c.profile_id).where(index_builds.c.version_id == identity,
                *scoped_where(index_builds, self.workspace_id)).order_by(index_builds.c.created_at.desc())).mappings().all()
            items = []
            for row in rows:
                job = conn.execute(sa.select(jobs.c.id).where(jobs.c.index_build_id == row["id"], *scoped_where(jobs, self.workspace_id))).scalar_one_or_none()
                try:
                    eligible(conn, self.store, self.workspace_id, row)
                    qualified = True
                except ServiceError:
                    qualified = False
                items.append({**{k: row[k] for k in ("id", "version_id", "status", "stage", "row_version", "profile_id", "profile_key", "chunker_key",
                    "chunk_count", "embedded_count", "cache_hits", "usage", "error_code", "retryable", "manifest_sha256")}, "job_id": job, "eligible": qualified})
            return {"builds": items, "publication": publication(conn, self.workspace_id, doc["id"]),
                "document_row_version": doc["row_version"], "revocation_epoch": doc["revocation_epoch"], "withdrawn": doc["withdrawn"]}
