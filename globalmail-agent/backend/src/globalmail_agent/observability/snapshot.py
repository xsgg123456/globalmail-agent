"""Project existing receipts/usage into ID, enum, version hash and count fields."""
from time import time_ns
from pathlib import Path
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import agent_runs
from globalmail_agent.observability.tracing import digest
from globalmail_agent.observability.media_filter import ENUMS


def snapshot(conn, conv, run, observations, started):
    context = conn.execute(sa.select(a.agent_run_contexts).where(
        a.agent_run_contexts.c.run_id == run["id"])).mappings().first()
    parent = conn.execute(sa.select(agent_runs.c.id).where(
        agent_runs.c.conversation_id == conv["id"], agent_runs.c.created_at < run["created_at"])
        .order_by(agent_runs.c.created_at.desc()).limit(1)).scalar_one_or_none()
    meta = {"run_id": str(run["id"]), "conversation_id": str(conv["id"]),
        "workspace_id": str(conv["workspace_id"]), "branch_id": str(conv["branch_id"]),
        "customer_id": str(conv["customer_id"]), "cycle_id": str(run["processing_cycle_id"]),
        "mode": conv["mode"], "execution_mode": run["execution_mode"], "attempt_no": run["attempt_no"],
        "generation": run["branch_generation"], "input_revision": run["input_revision"],
        "authority_epoch": run["authority_epoch"], "started_ns": started, "ended_ns": time_ns()}
    if parent:
        meta["parent_run_id"] = str(parent)
    sources = set()
    if context:
        meta.update(context_object_id=str(context["context_object_id"]), release_epoch=context["release_epoch"],
            prompt_hash=digest(context["prompt_version"] + "\n" + "\n".join(p.read_text(encoding="utf-8")
                for p in sorted((Path(__file__).parents[1] / "agent" / "prompts").glob("*.md")))),
            graph_hash=digest(context["graph_version"] + "\n" + (Path(__file__).parents[1] / "agent" / "graph.py").read_text(encoding="utf-8")),
            policy_hash=digest((Path(__file__).parents[1] / "application" / "draft_validation.py").read_text(encoding="utf-8")))
        for key in ("release_id", "profile_id"):
            if context[key]:
                meta[key] = str(context[key])
        sources.add(context["context_object_id"])
    rows = [dict(row) for row in observations]
    ledger = list(conn.execute(sa.select(a.usage_records).where(a.usage_records.c.run_id == run["id"])).mappings())
    requests = {digest(row["request_key"]): row for row in ledger}
    for row in rows:
        usage = requests.get(row.get("request_hash"))
        if usage:
            row.update(usage_id=str(usage["id"]), stage=usage["stage"], usage_status=usage["status"], model_hash=digest(usage["model"]))
            if usage["model"] in ENUMS["model"]:
                row["model"] = usage["model"]
            for key in ("input_tokens", "output_tokens"):
                if usage[key] is not None:
                    row[key] = usage[key]
        if row["node"] == "outcome":
            row["status"] = run["status"] if run["status"] in ENUMS["status"] else "unknown"
            if run["outcome"] in ENUMS["outcome"]:
                row["outcome"] = run["outcome"]
            if run["error_code"]:
                row["reason_code"] = run["error_code"] if run["error_code"] in ENUMS["reason_code"] else "business_failure"
    for row in ledger:
        sources.update(row[k] for k in ("request_object_id", "response_object_id") if row[k])
    for table, keys in ((a.tool_commands, ("result_object_id",)), (a.understanding_results, ("body_object_id",)),
            (a.reply_artifacts, ("body_object_id", "advice_object_id"))):
        for row in conn.execute(sa.select(table).where(table.c.run_id == run["id"])).mappings():
            sources.update(row[k] for k in keys if row[k])
    return {"metadata": meta, "observations": rows}, tuple(sources)
