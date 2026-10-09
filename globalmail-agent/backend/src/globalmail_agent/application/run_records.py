"""Read persistent run receipts; GET never schedules or resumes a graph."""
import json
from uuid import UUID
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import conversations, agent_runs
from globalmail_agent.adapters.body_store import read_body
from globalmail_agent.application.conversation_lock import ServiceError, DEFAULT_WORKSPACE_ID
from globalmail_agent.knowledge.references import ReferenceService
from globalmail_agent.observability.usage import usage_view
from globalmail_agent.worker.jobs import JobService


class RunRecords:
    def __init__(self, engine, store, workspace=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.workspace = engine, store, workspace

    def reference(self, run_id, identity):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)
        with self.engine.connect() as conn:
            run = conn.execute(sa.select(agent_runs).where(agent_runs.c.id == run_id,
                agent_runs.c.workspace_id == self.workspace)).mappings().first()
            if run is None:
                raise ServiceError("run_not_found", 404)
            linked = conn.execute(sa.select(a.agent_run_dependencies.c.id).where(
                a.agent_run_dependencies.c.run_id == run_id, a.agent_run_dependencies.c.reference_id == identity,
                a.agent_run_dependencies.c.workspace_id == self.workspace)).scalar_one_or_none()
            if not linked:
                raise ServiceError("reference_not_found", 404)
        return ReferenceService(self.engine, self.store, self.workspace).get(identity)

    def get(self, run_id):
        basic = JobService(self.engine, self.workspace).get(run_id)
        with self.engine.connect() as conn:
            conv = conn.execute(sa.select(conversations).where(conversations.c.id == basic["run"]["conversation_id"],
                conversations.c.workspace_id == self.workspace)).mappings().one()
            if conv["lifecycle"] in {"deleting", "deleted"}:
                raise ServiceError("run_not_found", 404)
            from globalmail_agent.attachments.revocation import check_content_access
            context_id = conn.execute(sa.select(a.agent_run_contexts.c.context_object_id).where(
                a.agent_run_contexts.c.run_id == run_id)).scalar_one_or_none()
            if context_id:
                check_content_access(conn, conv, context_id)
            def body(object_id):
                from globalmail_agent.attachments.revocation import REDACTED
                value = read_body(conn, self.store, conv, object_id)
                if value == REDACTED:
                    raise ServiceError("image_content_revoked", 410)
                return value
            understanding = conn.execute(sa.select(a.understanding_results).where(a.understanding_results.c.run_id == run_id)).mappings().first()
            understanding_value = json.loads(body(understanding["body_object_id"])) if understanding else None
            revisions = []
            for row in conn.execute(sa.select(a.understanding_revisions).where(
                    a.understanding_revisions.c.run_id == run_id,
                    a.understanding_revisions.c.workspace_id == self.workspace)
                    .order_by(a.understanding_revisions.c.revision)).mappings():
                value = json.loads(body(row["body_object_id"]))
                revisions.append({"revision": row["revision"], "case_revision": row["case_revision"],
                    "source_ids": row["source_ids"], "change_reason": row["change_reason"],
                    "created_at": row["created_at"], "sources": value["sources"],
                    "understanding": value["understanding"]})
            if understanding_value is not None:
                initial = understanding_value
                understanding_value = {**(revisions[-1]["understanding"] if revisions else initial),
                    "initial_understanding": initial, "revisions": revisions}
            tools = []
            for row in conn.execute(sa.select(a.tool_commands).where(a.tool_commands.c.run_id == run_id)
                    .order_by(a.tool_commands.c.created_at, a.tool_commands.c.id)).mappings():
                output = json.loads(body(row["result_object_id"])) if row["result_object_id"] else None
                tools.append({"id": str(row["id"]), "name": row["name"], "arguments": row["arguments"],
                    "status": row["status"], "reason_code": output["reason_code"] if output else "awaiting_result",
                    "result": output, "created_at": row["created_at"]})
            artifacts = [{**dict(row), "body": body(row["body_object_id"])} for row in conn.execute(sa.select(a.reply_artifacts)
                .where(a.reply_artifacts.c.run_id == run_id)).mappings()]
            identities = list(conn.execute(sa.select(a.agent_run_dependencies.c.reference_id).where(
                a.agent_run_dependencies.c.run_id == run_id)).scalars())
            waits = [dict(row) for row in conn.execute(sa.select(a.wait_conditions).where(a.wait_conditions.c.run_id == run_id)).mappings()]
            usage = usage_view(conn, basic["run"]["processing_cycle_id"])
            trace = conn.execute(sa.select(a.trace_correlations.c.trace_id).where(a.trace_correlations.c.run_id == run_id)).scalar_one_or_none()
        return {**basic, "understanding": understanding_value,
            "tools": tools, "artifacts": artifacts, "references": [self.reference(run_id, identity) for identity in identities],
            "waits": waits, "usage": usage, "trace_id": trace}
