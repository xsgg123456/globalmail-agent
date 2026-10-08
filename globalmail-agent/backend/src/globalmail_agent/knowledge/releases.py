"""CAS publication, full-space switches, fresh rollback events and immediate revocation."""
from uuid import uuid4, UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from globalmail_agent.adapters.knowledge_index_schema import knowledge_release_heads, knowledge_releases, knowledge_release_items
from globalmail_agent.adapters.knowledge_schema import documents
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.application.idempotency import prior, remember
from globalmail_agent.knowledge.base import scope, scoped_where, document, audit, canonical, sha, ensure_slot
from globalmail_agent.knowledge.build_checks import build_row, eligible
from globalmail_agent.knowledge.release_queries import head, head_view, release_row, release_view
from globalmail_agent.knowledge.queue import invalidate_document_jobs
from globalmail_agent.worker.leases import slot_for_update, db_now


class ReleaseService:
    def __init__(self, engine, store, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.workspace_id = engine, store, workspace_id

    def _available(self):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)

    def listing(self):
        self._available()
        with self.engine.connect() as conn:
            rows = conn.execute(sa.select(knowledge_releases).where(*scoped_where(knowledge_releases, self.workspace_id))
                .order_by(knowledge_releases.c.epoch.desc())).mappings().all()
            return {"head": head_view(head(conn, self.workspace_id)), "items": [release_view(conn, self.workspace_id, r) for r in rows]}

    def _head(self, conn, expected):
        conn.execute(pg_insert(knowledge_release_heads).values(id=uuid4(), **scope(self.workspace_id)).on_conflict_do_nothing())
        row = head(conn, self.workspace_id, True)
        if row["epoch"] != expected:
            raise ServiceError("stale_release")
        return row

    def _current(self, conn, row):
        if not row["release_id"]:
            return {}
        release = release_row(conn, self.workspace_id, row["release_id"])
        if sha(canonical(release["manifest"])) != release["manifest_sha256"]:
            raise ServiceError("manifest_integrity_error", 503)
        return {e["document_id"]: UUID(e["build_id"]) for e in release["manifest"]["entries"]}

    def _entries(self, conn, candidates, rollback=False, verify_source=True):
        entries, profiles = [], set()
        builds = [build_row(conn, self.workspace_id, identity) for identity in candidates]
        if len({b["document_id"] for b in builds}) != len(builds):
            raise ServiceError("duplicate_document_build", 422)
        for build in sorted(builds, key=lambda b: str(b["document_id"])):
            document(conn, self.workspace_id, build["document_id"], lock=True)
            doc, v, policy = eligible(conn, self.store, self.workspace_id, build, verify_source=verify_source)
            if rollback and doc["withdrawn"]:
                raise ServiceError("document_withdrawn")
            profiles.add(build["profile_id"])
            entries.append({"document_id": str(doc["id"]), "version_id": str(v["id"]), "build_id": str(build["id"]),
                "title": v["title"], "version_number": v["number"], "document_type": doc["document_type"], "brand": doc["brand"],
                "profile_id": str(build["profile_id"]), "applicability_revision": v["applicability_sha256"],
                "source_sha256": v["source_sha256"], "parse_sha256": v["parse_sha256"], "index_manifest_sha256": build["manifest_sha256"],
                "revocation_epoch": doc["revocation_epoch"], "available_at": v["available_at"].isoformat(),
                "source_kind": doc["source_kind"], "allowed_modes": doc["allowed_modes"], "usage_split": doc["usage_split"],
                "policy_bundle": {k: policy[k] for k in ("rules", "rule_schema", "description", "rules_sha256", "schema_sha256", "description_sha256", "generator_version")} if policy else None})
        if len(profiles) > 1:
            raise ServiceError("embedding_space_mismatch")
        return entries, next(iter(profiles), None)

    def _write(self, conn, old_head, entries, profile, operation):
        identity, epoch, now = uuid4(), old_head["epoch"] + 1, db_now(conn)
        manifest = {"schema_version": "knowledge-release/1", "scope": {k: str(v) for k, v in scope(self.workspace_id).items()},
            "profile_id": str(profile) if profile else None, "entries": entries, "effective_at": now.isoformat()}
        values = {"id": identity, **scope(self.workspace_id), "profile_id": profile, "epoch": epoch, "operation": operation,
            "manifest": manifest, "manifest_sha256": sha(canonical(manifest)), "actor": "local_operator", "effective_at": now}
        conn.execute(sa.insert(knowledge_releases).values(**values))
        for entry in entries:
            conn.execute(sa.insert(knowledge_release_items).values(id=uuid4(), **scope(self.workspace_id), release_id=identity,
                document_id=UUID(entry["document_id"]), build_id=UUID(entry["build_id"]), revocation_epoch=entry["revocation_epoch"]))
            conn.execute(documents.update().where(documents.c.id == UUID(entry["document_id"]), documents.c.withdrawn.is_(True))
                .values(withdrawn=False, row_version=documents.c.row_version + 1, updated_at=sa.func.now()))
        conn.execute(knowledge_release_heads.update().where(knowledge_release_heads.c.id == old_head["id"])
            .values(release_id=identity, profile_id=profile, epoch=epoch, updated_at=sa.func.now()))
        row = release_row(conn, self.workspace_id, identity)
        return {"head": head_view({"release_id": identity, "epoch": epoch, "profile_id": profile}),
            "release": release_view(conn, self.workspace_id, row)}

    def publish(self, command, key):
        self._available()
        with self.engine.begin() as conn:
            previous, digest = prior(conn, self.workspace_id, key, "knowledge-release", command.model_dump(mode="json"))
            if previous is not None:
                return previous
            current = self._head(conn, command.expected_release_epoch)
            old = self._current(conn, current)
            selected = [build_row(conn, self.workspace_id, identity) for identity in command.build_ids]
            mapping = {str(b["document_id"]): b["id"] for b in selected}
            if len(mapping) != len(selected):
                raise ServiceError("duplicate_document_build", 422)
            if command.replace_all:
                if not set(old) <= set(mapping):
                    raise ServiceError("incomplete_space_switch")
            else:
                mapping = {**old, **mapping}
            entries, profile = self._entries(conn, list(mapping.values()))
            if current["profile_id"] and profile != current["profile_id"] and not command.replace_all:
                raise ServiceError("embedding_space_mismatch")
            result = self._write(conn, current, entries, profile, "publish")
            for entry in entries:
                audit(conn, self.workspace_id, UUID(entry["document_id"]), UUID(entry["version_id"]), "release.publish", {"release_id": result["head"]["release_id"]})
            remember(conn, self.workspace_id, key, "knowledge-release", digest, result)
            return result

    def rollback(self, identity, command, key):
        self._available()
        operation = "knowledge-rollback:" + str(identity)
        with self.engine.begin() as conn:
            previous, digest = prior(conn, self.workspace_id, key, operation, command.model_dump(mode="json"))
            if previous is not None:
                return previous
            current = self._head(conn, command.expected_release_epoch)
            old = release_row(conn, self.workspace_id, identity)
            if sha(canonical(old["manifest"])) != old["manifest_sha256"]:
                raise ServiceError("manifest_integrity_error", 503)
            entries, profile = self._entries(conn, [UUID(e["build_id"]) for e in old["manifest"]["entries"]], rollback=True)
            result = self._write(conn, current, entries, profile, "rollback")
            for entry in entries:
                audit(conn, self.workspace_id, UUID(entry["document_id"]), UUID(entry["version_id"]), "release.rollback", {"release_id": result["head"]["release_id"]})
            remember(conn, self.workspace_id, key, operation, digest, result)
            return result

    def withdraw(self, identity, command, key):
        self._available()
        operation = "knowledge-withdraw:" + str(identity)
        with self.engine.begin() as conn:
            previous, digest = prior(conn, self.workspace_id, key, operation, command.model_dump(mode="json"))
            if previous is not None:
                return previous
            ensure_slot(conn, self.workspace_id)
            slot_for_update(conn, self.workspace_id, "knowledge")
            current = self._head(conn, command.expected_release_epoch)
            doc = document(conn, self.workspace_id, identity, command.expected_version, True)
            invalidate_document_jobs(conn, self.workspace_id, doc)
            epoch = doc["revocation_epoch"] + 1
            conn.execute(documents.update().where(documents.c.id == identity).values(withdrawn=True, revocation_epoch=epoch,
                document_fence=doc["document_fence"] + 1, row_version=doc["row_version"] + 1, updated_at=sa.func.now()))
            remaining = {k: v for k, v in self._current(conn, current).items() if k != str(identity)}
            entries, profile = self._entries(conn, list(remaining.values()), verify_source=False)
            result = self._write(conn, current, entries, profile, "withdraw")
            audit(conn, self.workspace_id, identity, doc["current_version_id"], "document.withdraw", {"revocation_epoch": epoch})
            result = {"head": result["head"], "document_id": str(identity), "document_row_version": doc["row_version"] + 1,
                "revocation_epoch": epoch, "withdrawn": True}
            remember(conn, self.workspace_id, key, operation, digest, result)
            return result
