"""Opaque UUID object storage; no caller-supplied filenames or external paths."""
import hashlib
import os
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from sqlalchemy import and_, insert, select
from sqlalchemy.engine import Engine

from globalmail_agent.adapters.schema import objects
from globalmail_agent.application.content_dependencies import register_dependencies


class Scope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    workspace_id: UUID
    mode: Literal["historical_replay", "simulation"]
    branch_id: UUID
    customer_id: UUID
    purpose: str = Field(min_length=1, max_length=80, pattern=r"\S")


class Source(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: str = Field(min_length=1, max_length=80, pattern=r"\S")
    reference: str = Field(min_length=1, max_length=240, pattern=r"\S")


class ObjectStore:
    def __init__(self, root: Path, engine: Engine | None):
        self.root, self.engine = root.absolute(), engine

    def _root(self):
        if self.root.is_symlink() or self.root.resolve() != self.root:
            raise ValueError("invalid_object_root")
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, object_id: UUID) -> Path:
        if not isinstance(object_id, UUID):
            raise ValueError("invalid_object_id")
        self._root()
        path = self.root / str(object_id)
        if path.is_symlink() or path.resolve().parent != self.root:
            raise ValueError("invalid_object_path")
        return path

    def ready(self) -> bool:
        try:
            self._root()
            with tempfile.TemporaryFile(dir=self.root) as probe:
                probe.write(b"ready")
                probe.flush()
                os.fsync(probe.fileno())
                probe.seek(0)
                return probe.read() == b"ready"
        except (OSError, ValueError):
            return False

    def put(self, content: bytes, scope: Scope, source: Source,
            *, derived_from: tuple[UUID, ...] = ()) -> UUID:
        if self.engine is None:
            raise RuntimeError("database_unavailable")
        if not isinstance(content, bytes) or len(content) > 50 * 1024 * 1024:
            raise ValueError("invalid_object_content")
        object_id = uuid4()
        path = self._path(object_id)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.root, delete=False) as output:
                temporary = Path(output.name)
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
            with self.engine.begin() as connection:
                connection.execute(insert(objects).values(
                    id=object_id, **scope.model_dump(), sha256=hashlib.sha256(content).hexdigest(),
                    size_bytes=len(content), source_kind=source.kind, source_ref=source.reference,
                ))
                register_dependencies(connection, scope.model_dump(), object_id, derived_from)
            return object_id
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def get(self, object_id: UUID, scope: Scope) -> bytes:
        path = self._path(object_id)
        if self.engine is None:
            raise RuntimeError("database_unavailable")
        with self.engine.connect() as connection:
            row = connection.execute(select(objects).where(and_(
                objects.c.id == object_id,
                *[objects.c[key] == value for key, value in scope.model_dump().items()],
            ))).mappings().first()
        if row is None:
            raise LookupError("object_not_found")
        content = path.read_bytes()
        if len(content) != row["size_bytes"] or hashlib.sha256(content).hexdigest() != row["sha256"]:
            raise ValueError("object_integrity_error")
        return content

