"""Scope, safe object I/O and short-transaction helpers."""
import hashlib
import json
import os
import tempfile
from uuid import uuid4, uuid5, UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from globalmail_agent.adapters.schema import objects, SCOPE_KEYS
from globalmail_agent.adapters.conversation_schema import agent_slots
from globalmail_agent.adapters.knowledge_schema import documents, document_versions, knowledge_audits
from globalmail_agent.application.content_dependencies import register_dependencies
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(content):
    return hashlib.sha256(content).hexdigest()


def scope(workspace):
    return {"workspace_id": workspace, "mode": "simulation", "purpose": "knowledge",
        "branch_id": uuid5(workspace, "shared-knowledge"), "customer_id": uuid5(workspace, "knowledge-owner")}


def scoped_where(table, workspace):
    return [table.c[k] == v for k, v in scope(workspace).items()]


def ensure_slot(conn, workspace):
    conn.execute(pg_insert(agent_slots).values(id=uuid4(), workspace_id=workspace, slot_key="knowledge")
        .on_conflict_do_nothing(index_elements=["workspace_id", "slot_key"]))


def audit(conn, workspace, document_id, version_id, action, details=None):
    conn.execute(sa.insert(knowledge_audits).values(id=uuid4(), **scope(workspace),
        document_id=document_id, version_id=version_id, action=action, actor="local_operator", details=details or {}))


def document(conn, workspace, identity, expected=None, lock=False):
    query = sa.select(documents).where(documents.c.id == identity, *scoped_where(documents, workspace))
    row = conn.execute(query.with_for_update() if lock else query).mappings().first()
    if row is None or row["lifecycle"] != "active":
        raise ServiceError("document_not_found", 404)
    if expected is not None and row["row_version"] != expected:
        raise ServiceError("stale_version")
    return dict(row)


def version(conn, workspace, identity, expected=None, lock=False):
    query = sa.select(document_versions).where(document_versions.c.id == identity,
        *scoped_where(document_versions, workspace))
    row = conn.execute(query.with_for_update() if lock else query).mappings().first()
    if row is None:
        raise ServiceError("version_not_found", 404)
    document(conn, workspace, row["document_id"])
    if expected is not None and row["row_version"] != expected:
        raise ServiceError("stale_version")
    return dict(row)


class KnowledgeFiles:
    def __init__(self, store, workspace=DEFAULT_WORKSPACE_ID):
        self.store, self.workspace, self.files = store, workspace, []

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        if kind:
            for path in self.files:
                path.unlink(missing_ok=True)

    def put(self, conn, content, source, reference, derived_from=()):
        if not isinstance(content, bytes) or len(content) > 50 * 1024 * 1024:
            raise ServiceError("file_too_large", 422)
        identity = uuid4()
        path = self.store._path(identity)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.store.root, delete=False) as output:
                temporary = output.name
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
            self.files.append(path)
            conn.execute(sa.insert(objects).values(id=identity, **scope(self.workspace), sha256=sha(content),
                size_bytes=len(content), source_kind=source, source_ref=reference))
            register_dependencies(conn, scope(self.workspace), identity, tuple(derived_from))
            return identity
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def read(self, conn, identity):
        row = conn.execute(sa.select(objects).where(objects.c.id == identity,
            *scoped_where(objects, self.workspace))).mappings().first()
        if row is None:
            raise ServiceError("object_not_found", 404)
        try:
            content = self.store._path(identity).read_bytes()
        except OSError:
            raise ServiceError("source_unavailable", 503) from None
        if len(content) != row["size_bytes"] or sha(content) != row["sha256"]:
            raise ServiceError("object_integrity_error", 503)
        return content, dict(row)
