"""Cycle reservations survive attempts; SDK retries cannot bypass the ledger."""
import time
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.agent.guard import guarded
from globalmail_agent.adapters.body_store import BodyWriter
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.chunking import proxy_tokens

LIMITS = {"model_requests": 6, "tool_calls": 12, "tokens": 80000, "active_ms": 120000}


def output_limit(stage):
    return 4000 if stage == "validation" else 2000


def network_timeout(stage):
    return 60 if stage == "validation" else 30


def input_estimate(messages, tools=None):
    from globalmail_agent.knowledge.base import canonical
    return proxy_tokens(canonical({"messages": messages, "tools": tools or []}).decode())


class Budget:
    def __init__(self, engine, workspace, job):
        self.engine, self.workspace, self.job = engine, workspace, job
        self.started, self.base_ms = time.monotonic(), 0
        with guarded(engine, workspace, job, check_knowledge=False) as (conn, conv, run, cycle):
            row = conn.execute(sa.select(a.cycle_budgets).where(a.cycle_budgets.c.cycle_id == cycle["id"])).mappings().first()
            if row is None:
                conn.execute(sa.insert(a.cycle_budgets).values(id=uuid4(), **{k: conv[k] for k in SCOPE_KEYS},
                    conversation_id=conv["id"], cycle_id=cycle["id"]))
            else:
                self.base_ms = row["active_ms"]

    def _row(self, conn):
        return dict(conn.execute(sa.select(a.cycle_budgets).where(
            a.cycle_budgets.c.cycle_id == self.job["cycle_id"]).with_for_update()).mappings().one())

    def active_ms(self):
        return self.base_ms + int((time.monotonic() - self.started) * 1000)

    def reserve(self, messages, stage, model, tools=None, image_views=(), *, schema=None, options=None, store=None, request_tools=None):
        estimate = input_estimate(messages, tools) + sum(r["visual_token_upper"] for r in image_views)
        reservation = estimate + output_limit(stage)
        if estimate > 16000:
            raise ServiceError("input_budget_exceeded")
        key = uuid4().hex
        from contextlib import nullcontext
        with (BodyWriter(store) if store else nullcontext()) as writer, guarded(self.engine, self.workspace, self.job) as (conn, conv, run, cycle):
            row = self._row(conn)
            if row["image_views"] + len(image_views) > 6:
                raise ServiceError("image_view_budget_exceeded")
            if (row["model_requests"] >= 6 or row["reserved_tokens"] + reservation > 80000
                    or self.active_ms() >= 120000):
                raise ServiceError("budget_exhausted")
            conn.execute(a.cycle_budgets.update().where(a.cycle_budgets.c.id == row["id"]).values(
                model_requests=row["model_requests"] + 1, reserved_tokens=row["reserved_tokens"] + reservation,
                image_views=row["image_views"] + len(image_views),
                unknown_requests=row["unknown_requests"] + 1, active_ms=self.active_ms()))
            conn.execute(sa.insert(a.usage_records).values(id=uuid4(), **{k: conv[k] for k in SCOPE_KEYS},
                conversation_id=conv["id"], run_id=run["id"], request_key=key, stage=stage, status="reserved",
                estimated_input=estimate, reserved_tokens=reservation, model=model,
                request_object_id=self._request_record(conn, writer, conv, run, messages, stage, model,
                    schema, request_tools, options, image_views) if writer else None,
                request_state="running" if writer else "not_recorded"))
        return key

    @staticmethod
    def _request_record(conn, writer, conv, run, messages, stage, model, schema, tools, options, image_views):
        from globalmail_agent.observability.model_records import request_record
        return request_record(conn, writer, conv, run, messages, stage, model, schema, tools, options, image_views)

    def remaining_requests(self):
        with guarded(self.engine, self.workspace, self.job) as (conn, conv, run, cycle):
            return max(0, LIMITS["model_requests"] - self._row(conn)["model_requests"])

    def settle(self, key, usage, provider_id=None):
        # Usage is diagnostic even after stop; never creates a business effect.
        with self.engine.begin() as conn:
            row = self._row(conn)
            record = conn.execute(sa.select(a.usage_records).where(a.usage_records.c.run_id == self.job["run_id"],
                a.usage_records.c.request_key == key).with_for_update()).mappings().one()
            if record["status"] != "reserved":
                return
            valid = usage and all(type(usage.get(k)) is int and usage[k] >= 0 for k in ("prompt_tokens", "completion_tokens"))
            values = {"status": "known" if valid else "unknown", "provider_request_id": provider_id}
            accounting = {"active_ms": max(row["active_ms"], self.active_ms())}
            if valid:
                incoming, outgoing = usage["prompt_tokens"], usage["completion_tokens"]
                values.update(input_tokens=incoming, output_tokens=outgoing)
                accounting.update(input_tokens=row["input_tokens"] + incoming, output_tokens=row["output_tokens"] + outgoing,
                    reserved_tokens=row["reserved_tokens"] - record["reserved_tokens"] + incoming + outgoing,
                    unknown_requests=row["unknown_requests"] - 1)
            conn.execute(a.usage_records.update().where(a.usage_records.c.id == record["id"]).values(**values))
            conn.execute(a.cycle_budgets.update().where(a.cycle_budgets.c.id == row["id"]).values(**accounting))
            if valid and (incoming > 16000 or outgoing > output_limit(record["stage"]) or accounting["reserved_tokens"] > 80000):
                raise_after = True
            else:
                raise_after = False
        if raise_after:
            raise ServiceError("provider_usage_exceeded")

    def tool(self):
        with guarded(self.engine, self.workspace, self.job) as (conn, conv, run, cycle):
            row = self._row(conn)
            if row["tool_calls"] >= 12 or self.active_ms() >= 120000:
                raise ServiceError("budget_exhausted")
            conn.execute(a.cycle_budgets.update().where(a.cycle_budgets.c.id == row["id"]).values(
                tool_calls=row["tool_calls"] + 1, active_ms=self.active_ms()))

    def finish(self):
        with self.engine.begin() as conn:
            row = self._row(conn)
            conn.execute(a.cycle_budgets.update().where(a.cycle_budgets.c.id == row["id"]).values(
                active_ms=max(row["active_ms"], self.active_ms())))
