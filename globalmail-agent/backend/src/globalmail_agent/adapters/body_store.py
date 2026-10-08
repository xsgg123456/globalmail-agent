"""Filesystem staging and registry writes on the caller's business transaction."""
import hashlib
import os
import tempfile
from pathlib import Path
from uuid import uuid4
from sqlalchemy import insert, select
from globalmail_agent.adapters.schema import objects, SCOPE_KEYS
from globalmail_agent.application.content_dependencies import register_dependencies


class BodyWriter:
    def __init__(self, store):
        self.store, self.files = store, []

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        if kind is not None:
            for path in self.files:
                path.unlink(missing_ok=True)

    def put(self, conn, conversation, body, source, derived_from=()):
        content, object_id = body.encode("utf-8"), uuid4()
        path = self.store._path(object_id)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.store.root, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            self.files.append(path)
            scope = {k: conversation[k] for k in SCOPE_KEYS}
            conn.execute(insert(objects).values(id=object_id, **scope,
                sha256=hashlib.sha256(content).hexdigest(), size_bytes=len(content),
                source_kind=source, source_ref=str(conversation["id"])))
            register_dependencies(conn, scope, object_id, tuple(derived_from))
            return object_id
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def read_body(conn, store, conversation, object_id):
    if object_id is None:
        return ""
    row = conn.execute(select(objects).where(objects.c.id == object_id,
        *[objects.c[k] == conversation[k] for k in SCOPE_KEYS])).mappings().first()
    if row is None:
        raise LookupError("body_not_found")
    content = store._path(object_id).read_bytes()
    if len(content) != row["size_bytes"] or hashlib.sha256(content).hexdigest() != row["sha256"]:
        raise ValueError("object_integrity_error")
    return content.decode("utf-8")
