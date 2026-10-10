"""Cross-process drain includes model calls and temporary parser files, not just commits."""
from contextlib import contextmanager
from functools import wraps
import hashlib
import sqlalchemy as sa
from globalmail_agent.application.conversation_lock import ServiceError


@contextmanager
def writer_barrier(engine, workspace, *, cleaning=False):
    with engine.connect() as conn:
        namespace = conn.execute(sa.text("SELECT current_database() || ':' || current_schema()")).scalar_one()
        key = int.from_bytes(hashlib.sha256(f'lifecycle:{namespace}:{workspace}'.encode()).digest()[:8], 'big', signed=True)
        lock = 'pg_try_advisory_lock' if cleaning else 'pg_try_advisory_lock_shared'
        acquired = conn.execute(sa.text(f'SELECT {lock}(:key)'), {'key':key}).scalar_one()
        conn.commit()
        if not acquired:
            raise ServiceError('writer_inflight' if cleaning else 'cleanup_in_progress', 503)
        try:
            yield
        finally:
            unlock = 'pg_advisory_unlock' if cleaning else 'pg_advisory_unlock_shared'
            conn.execute(sa.text(f'SELECT {unlock}(:key)'), {'key':key})
            conn.commit()


def guarded_writer(method):
    @wraps(method)
    def execute(self, *args, **kwargs):
        owner = self if hasattr(self, 'engine') else self.jobs
        with writer_barrier(owner.engine, owner.workspace_id):
            return method(self, *args, **kwargs)
    return execute
