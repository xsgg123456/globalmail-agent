"""Build inputs only from the authorized visible prefix. Model parameters never set scope."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4
import json
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import messages, human_reviews, replay_cursors, case_facts, case_issues
from globalmail_agent.adapters.body_store import BodyWriter, read_body, read_bytes
from globalmail_agent.adapters.schema import SCOPE_KEYS, objects
from globalmail_agent.agent.guard import guarded
from globalmail_agent.knowledge.base import canonical
from globalmail_agent.knowledge.release_queries import head
from globalmail_agent.worker.leases import db_now

PROMPT_VERSION = "text/5"
GRAPH_VERSION = "text-graph/2"


@dataclass(frozen=True)
class RunContext:
    workspace_id: UUID
    conversation_id: UUID
    run_id: UUID
    cycle_id: UUID
    mode: str
    as_of: datetime
    release_id: UUID | None
    release_epoch: int
    profile_id: UUID | None
    payload: dict


def load_context(engine, store, workspace, job, *, rebuild=False):
    with BodyWriter(store) as writer, guarded(engine, workspace, job, check_knowledge=False) as (conn, conv, run, cycle):
        rows = list(conn.execute(sa.select(messages).where(messages.c.conversation_id == conv["id"],
            messages.c.seq <= conv["visible_message_seq"]).order_by(messages.c.seq)).mappings())
        mail = [{"message_id": str(row["id"]), "seq": row["seq"], "sender": row["sender"],
            "subject": row["subject"], "body": read_body(conn, store, conv, row["body_object_id"])} for row in rows]
        from globalmail_agent.adapters.business_schema import simulation_branches
        branch_source = conn.execute(sa.select(simulation_branches).where(
            simulation_branches.c.conversation_id == conv["id"])).mappings().first()
        if branch_source:
            for row, item in zip(rows, mail):
                if row["source_ref"] == branch_source["source_ref"] and item["subject"] == branch_source["scenario_id"]:
                    # The fixture loader uses its scenario key as a UI title; it is not customer evidence.
                    item["subject"] = ""
        notes = []
        if conv["mode"] == "simulation":
            for review in conn.execute(sa.select(human_reviews).where(human_reviews.c.conversation_id == conv["id"],
                    human_reviews.c.status == "completed").order_by(human_reviews.c.created_at)).mappings():
                if review["note_object_id"]:
                    notes.append({"message_id": "human_note:" + str(review["id"]), "sender": "human_note",
                        "body": read_body(conn, store, conv, review["note_object_id"])})
        if conv["mode"] == "historical_replay":
            when = conn.execute(sa.select(replay_cursors.c.as_of).where(replay_cursors.c.conversation_id == conv["id"])).scalar_one()
            # Actual historical messages only; no old candidate state or human comparison.
            facts = []
        else:
            when = conn.execute(sa.select(simulation_branches.c.clock).where(
                simulation_branches.c.conversation_id == conv["id"])).scalar_one_or_none() or db_now(conn)
            facts = [{"kind": row["kind"], "source_message_id": str(row["source_message_id"]),
                "value": read_body(conn, store, conv, row["value_object_id"])} for row in conn.execute(sa.select(case_facts).where(
                    case_facts.c.conversation_id == conv["id"], case_facts.c.visible_seq <= conv["visible_message_seq"],
                    case_facts.c.value_object_id.in_(sa.select(objects.c.id).where(
                        objects.c.source_kind == "candidate_case_facts")))).mappings()]
        current = head(conn, workspace)
        if conv["mode"] == "historical_replay":
            current = {"release_id": None, "epoch": 0, "profile_id": None}
        wakes = [{"condition_key": r["condition_key"], "business_version": r["business_version"], "status": r["status"]}
            for r in conn.execute(sa.select(a.wake_pending).where(a.wake_pending.c.conversation_id == conv["id"],
                a.wake_pending.c.status.in_(["pending", "suppressed_by_human"]))).mappings()]
        from globalmail_agent.application.risk_records import active_risks
        from globalmail_agent.attachments.evidence import context_images
        image_manifest, image_notes, image_sources, image_objects = context_images(conn, store, conv)
        notes.extend(image_notes)
        risks = active_risks(conn, store, conv) if conv["mode"] == "simulation" else []
        payload = {"mode": conv["mode"], "simulation": conv["mode"] == "simulation", "as_of": when.isoformat(),
            "messages": mail, "human_notes": notes, "case_facts": facts, "case_revision": conv["case_revision"],
            "trigger_message_id": str(cycle["trigger_message_id"]), "unread_attachments": image_manifest, "wake_pending": wakes,
            "attachments": image_manifest, "visual_sources": image_sources,
            "active_risks": risks,
            "risk_history": active_risks(conn, store, conv, status=None) if conv["mode"] == "simulation" else [],
            "limitations": ["Image metadata is not content. Only authorized views in this request are read; unread coverage stays explicit.",
                "After-sales write tools are not available in this phase. Never claim a new request or fulfillment succeeded."]}
        if rebuild:
            from globalmail_agent.application.understanding_revisions import current_understanding, tool_sources
            known = current_understanding(conn, store, conv, run["id"])
            if known and not image_manifest:
                payload["reused_understanding"] = known
                payload["verified_tool_sources"] = {identity: {"sender": row["sender"], "body": row["body"]}
                    for identity, row in tool_sources(conn, store, conv, run["id"]).items()}
            names = {"get_order_snapshot", "get_shipment_status", "get_after_sales_context",
                "get_item_availability", "get_operation_status"}
            payload["verified_business_observations"] = [{"command_source_id": "command:" + str(row["id"]),
                "tool_name": row["name"], "result": json.loads(read_bytes(conn, store, conv, row["result_object_id"]))}
                for row in conn.execute(sa.select(a.tool_commands).where(a.tool_commands.c.run_id == run["id"],
                    a.tool_commands.c.name.in_(names), a.tool_commands.c.status.in_(["ok", "needs_input"]),
                    a.tool_commands.c.result_object_id.is_not(None))).mappings()]
        old = conn.execute(sa.select(a.agent_run_contexts).where(a.agent_run_contexts.c.run_id == run["id"])).mappings().first()
        if rebuild and old and old["rebuild_count"] >= 1:
            from globalmail_agent.application.conversation_lock import ServiceError
            raise ServiceError("knowledge_rebuild_exhausted")
        object_id = writer.put(conn, conv, canonical(payload).decode(), "agent_context",
            (*tuple(row["body_object_id"] for row in rows), *image_objects))
        values = dict(release_id=current["release_id"], release_epoch=current["epoch"], profile_id=current["profile_id"],
            as_of=when, visible_message_seq=conv["visible_message_seq"], context_object_id=object_id,
            observed_wakes=wakes,
            validated_draft_hash=None,
            prompt_version=PROMPT_VERSION, graph_version=GRAPH_VERSION)
        if old:
            conn.execute(a.agent_run_contexts.update().where(a.agent_run_contexts.c.id == old["id"])
                .values(**values, rebuild_count=old["rebuild_count"] + int(rebuild)))
        else:
            conn.execute(sa.insert(a.agent_run_contexts).values(id=uuid4(), **{k: conv[k] for k in SCOPE_KEYS},
                conversation_id=conv["id"], run_id=run["id"], **values))
        if rebuild:
            conn.execute(a.agent_run_dependencies.update().where(a.agent_run_dependencies.c.run_id == run["id"]).values(active=False))
        return RunContext(workspace, conv["id"], run["id"], cycle["id"], conv["mode"], when,
            current["release_id"], current["epoch"], current["profile_id"], payload)
