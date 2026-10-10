"""Record actual node boundaries, never their arguments, returns or exceptions."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from hashlib import sha256
from time import time_ns
from uuid import uuid4
from globalmail_agent.observability.media_filter import safe_fields, ENUMS

ACTIVE = ContextVar("globalmail_safe_trace", default=None)


def digest(value):
    return sha256(value.encode()).hexdigest()


class Recorder:
    def __init__(self, service, job):
        self.service, self.job = service, job
        self.rows, self.stack, self.degraded = [], [], False
        self.started = time_ns()
        self.token = ACTIVE.set(self)

    def add(self, values):
        try:
            if len(self.rows) >= 127:
                raise ValueError("observation_limit")
            self.rows.append(safe_fields(values))
        except Exception:
            self.degraded = True

    def close(self):
        ACTIVE.reset(self.token)
        self.add({"node": "outcome", "status": "completed", "started_ns": time_ns(), "ended_ns": time_ns()})
        self.service.persist(self.job, self.rows, self.started, self.degraded)


@contextmanager
def observation(node, **metadata):
    recorder = ACTIVE.get()
    row = {"node": node, "status": "completed", "started_ns": time_ns(),
        "observation_id": str(uuid4()), **metadata}
    if recorder:
        if recorder.stack:
            row["parent_observation_id"] = recorder.stack[-1]
        recorder.stack.append(row["observation_id"])
    try:
        yield row
    except BaseException as error:
        row["status"] = "failed"
        code = getattr(error, "code", None)
        row["reason_code"] = code if code in ENUMS["reason_code"] else "dependency_error"
        raise
    finally:
        if recorder:
            recorder.stack.pop()
            row["ended_ns"] = time_ns()
            row["duration_ms"] = max(0, (row["ended_ns"] - row["started_ns"]) // 1000000)
            recorder.add(row)


def observed(node):
    def decorate(function):
        @wraps(function)
        def execute(*args, **kwargs):
            with observation(node):
                return function(*args, **kwargs)
        return execute
    return decorate
