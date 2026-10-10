"""Durable revoke/purge/verify orchestration with an independent deletion journal."""
from pathlib import Path
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.lifecycle_schema import deletion_requests as requests, journal_receipts
from sqlalchemy.dialects.postgresql import insert as pg_insert
from globalmail_agent.adapters.schema import SCOPE_KEYS, deletion_journal
from globalmail_agent.adapters.deletion_journal import DeletionJournal
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.application.lifecycle_inventory import target, enumerate_holders, impact, ids
from globalmail_agent.application.lifecycle_revoke import lock_writers, revoke
from globalmail_agent.application.deletion import purge_local, verify_local


class LifecycleService:
    def __init__(self, engine, store, settings, workspace=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.settings, self.workspace = engine, store, settings, workspace
        root = getattr(settings, "lifecycle_journal_root", None)
        self.journal = DeletionJournal(Path(root) if root else store.root.parent / (store.root.name + "-lifecycle"))
        store.lifecycle_journal_root = self.journal.root

    def _available(self):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)

    @staticmethod
    def _view(row):
        return {"id": str(row["id"]), "request_id": str(row["id"]), "status": row["status"],
            "target_type": row["target_type"], "target_id": str(row["target_id"]), "action": row["action"],
            "new_conversation_id": str(row["replacement_conversation_id"]) if row.get("replacement_conversation_id") else None,
            "impact": impact(row["manifest"]), "error_code": row["error_code"], "journal_seq": row["journal_seq"]}

    def preview(self, kind, target_id):
        self._available()
        with self.engine.connect() as conn:
            row = target(conn, self.workspace, kind, UUID(str(target_id)))
            manifest = enumerate_holders(conn, self.workspace, kind, row)
            return {"target_type": kind, "target_id": str(target_id),
                "expected_version": row.get("row_version", row.get("revision")), "impact": impact(manifest)}

    def _row(self, conn, request_id):
        row = conn.execute(sa.select(requests).where(requests.c.id == UUID(str(request_id)),
            requests.c.workspace_id == self.workspace)).mappings().first()
        if not row:
            raise ServiceError("deletion_request_not_found", 404)
        return dict(row)

    def get(self, request_id):
        self._available()
        with self.engine.connect() as conn:
            return self._view(self._row(conn, request_id))

    def request(self, kind, target_id, expected_version, action="delete"):
        self._available()
        if action not in {"delete", "reset"} or (action == "reset" and kind != "conversation"):
            raise ServiceError("invalid_deletion_action", 422)
        identity = UUID(str(target_id))
        with self.engine.begin() as conn:
            lock_writers(conn, self.workspace)
            existing = conn.execute(sa.select(requests).where(requests.c.workspace_id == self.workspace,
                requests.c.target_type == kind, requests.c.target_id == identity)).mappings().first()
            if existing:
                return self._view(existing)
            row = self._target_locked(conn, kind, identity)
            if row.get("row_version", row.get("revision")) != expected_version:
                raise ServiceError("stale_version")
            if action == "reset" and row["mode"] != "simulation":
                raise ServiceError("reset_requires_simulation", 422)
            request_id = uuid4()
            record = {"request_id": str(request_id), "workspace_id": str(self.workspace),
                "target_type": kind, "target_id": str(identity), "action": action, "expected_version": expected_version}
            # Existing DB tombstones mean a missing independent journal must fail closed.
            any_deletion = conn.execute(sa.select(deletion_journal.c.id).limit(1)).first()
            any_request = conn.execute(sa.select(requests.c.id).limit(1)).first()
            any_receipt = conn.execute(sa.select(journal_receipts.c.request_id).limit(1)).first()
            if any_deletion or any_request or any_receipt:
                self.journal.read_verified()
            else:
                self.journal.initialize()
            saved = self.journal.append(record)
            self._revoke(conn, row, record, saved["seq"])
        return self.get(request_id)

    def _revoke(self, conn, row, record, sequence):
        kind = record["target_type"]
        manifest = enumerate_holders(conn, self.workspace, kind, row)
        revoke(conn, self.workspace, kind, row, manifest)
        from globalmail_agent.application.event_store import append_ui_event
        for cid in ids(manifest, "conversation_ids"):
            append_ui_event(conn, cid, "content.revoked", {})
        # Root locks now fence object-registration; include children committed while waiting.
        refreshed = enumerate_holders(conn, self.workspace, kind, row)
        if set(refreshed["object_ids"]) - set(manifest["object_ids"]):
            from globalmail_agent.application.lifecycle_revoke import revoke_objects
            revoke_objects(conn, refreshed)
        conn.execute(requests.insert().values(id=UUID(record["request_id"]),
            **{key: row[key] for key in SCOPE_KEYS}, target_type=kind, target_id=row["id"],
            action=record["action"], expected_version=int(record.get("expected_version", 0)),
            status="revoked", manifest=refreshed, journal_seq=sequence))
        self._receipt(conn, record, sequence)

    def _receipt(self, conn, record, sequence):
        conn.execute(pg_insert(journal_receipts).values(request_id=UUID(record["request_id"]),
            workspace_id=self.workspace, seq=int(sequence)).on_conflict_do_nothing())

    def _target_locked(self, conn, kind, identity):
        row = target(conn, self.workspace, kind, identity)
        if kind in {"conversation", "attachment"}:
            from globalmail_agent.adapters.conversation_schema import conversations
            from globalmail_agent.adapters.business_schema import simulation_branches
            cid = row["id"] if kind == "conversation" else row["conversation_id"]
            conn.execute(sa.select(simulation_branches).where(simulation_branches.c.conversation_id == cid)
                .with_for_update()).all()
            conn.execute(sa.select(conversations).where(conversations.c.id == cid).with_for_update()).all()
        return target(conn, self.workspace, kind, identity, lock=True)

    def replay(self, record):
        if record["workspace_id"] != str(self.workspace):
            raise ServiceError("journal_workspace_mismatch")
        from globalmail_agent.application.lifecycle_inventory import TARGETS
        table = TARGETS.get(record['target_type'])
        allowed = {('conversation', 'delete'), ('conversation', 'reset'), ('document', 'delete'),
            ('document', 'withdraw'), ('attachment', 'delete'), ('attachment', 'revoke')}
        if table is None or (record['target_type'], record['action']) not in allowed:
            raise ServiceError('invalid_journal_action', 422)
        with self.engine.begin() as conn:
            present = conn.execute(sa.select(table.c.id).where(table.c.id == UUID(record['target_id']),
                table.c.workspace_id == self.workspace)).first()
            if not present:
                self._receipt(conn, record, record['seq'])
                return {'status':'completed', 'target_id':record['target_id'], 'already_absent':True}
        if record["action"] in {"withdraw", "revoke"}:
            from globalmail_agent.application.lifecycle_replay import replay_revocation
            return replay_revocation(self, record)
        with self.engine.begin() as conn:
            lock_writers(conn, self.workspace)
            old = conn.execute(sa.select(requests.c.id).where(requests.c.id == UUID(record["request_id"]))).first()
            if not old:
                row = self._target_locked(conn, record["target_type"], UUID(record["target_id"]))
                self._revoke(conn, row, record, record["seq"])
            else:
                self._receipt(conn, record, record["seq"])
        result = self.process(record["request_id"])
        if result["status"] != "completed":
            raise ServiceError("restore_deletion_incomplete", 503)
        return result

    def process(self, request_id):
        self._available()
        # Session advisory lock spans remote deletion, transactions and filesystem IO.
        with self.engine.connect() as guard:
            key = int.from_bytes(UUID(str(request_id)).bytes[:8], "big", signed=True)
            guard.execute(sa.text("SELECT pg_advisory_lock(:key)"), {"key": key})
            guard.commit()
            try:
                return self._process(request_id)
            finally:
                guard.execute(sa.text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                guard.commit()

    def _status(self, request_id, status, error=None):
        with self.engine.begin() as conn:
            conn.execute(requests.update().where(requests.c.id == UUID(str(request_id)),
                requests.c.workspace_id == self.workspace).values(status=status, error_code=error, updated_at=sa.func.now()))

    def _process(self, request_id):
        from globalmail_agent.application.writer_barrier import writer_barrier
        try:
            with writer_barrier(self.engine, self.workspace, cleaning=True):
                return self._process_drained(request_id)
        except ServiceError as error:
            self._status(request_id, 'cleanup_failed', error.code)
            return self.get(request_id)

    def _process_drained(self, request_id):
        with self.engine.connect() as conn:
            row = self._row(conn, request_id)
        if row["status"] == "completed":
            return self._view(row)
        if row["manifest"]["blocked_document_ids"]:
            with self.engine.begin() as conn:
                current = target(conn, self.workspace, row["target_type"], row["target_id"])
                fresh = enumerate_holders(conn, self.workspace, row["target_type"], current)
                row["manifest"]["blocked_document_ids"] = fresh["blocked_document_ids"]
                conn.execute(requests.update().where(requests.c.id == row["id"]).values(manifest=row["manifest"]))
            if row["manifest"]["blocked_document_ids"]:
                self._status(request_id, "blocked_dependencies", "shared_source_requires_separation")
                return self.get(request_id)
        self._status(request_id, "purging")
        try:
            from globalmail_agent.observability.purge import PurgeService
            if PurgeService(self.engine, self.store, self.settings, self.workspace).purge_runs(ids(row["manifest"], "run_ids")) is not True:
                raise ServiceError("observability_purge_unconfirmed", 503)
            with self.engine.begin() as conn:
                lock_writers(conn, self.workspace)
                purge_local(conn, self.store, row)
            self._status(request_id, "verifying")
            with self.engine.begin() as conn:
                verify_local(conn, self.store, row)
                current = target(conn, self.workspace, row["target_type"], row["target_id"])
                latest = enumerate_holders(conn, self.workspace, row["target_type"], current)
                if set(latest["object_ids"]) - set(row["manifest"]["object_ids"]):
                    raise ServiceError("unregistered_deletion_holder", 503)
            self._status(request_id, "completed")
        except Exception as error:
            code = error.code if isinstance(error, ServiceError) else "local_cleanup_failed"
            self._status(request_id, "cleanup_failed", code)
        return self.get(request_id)
