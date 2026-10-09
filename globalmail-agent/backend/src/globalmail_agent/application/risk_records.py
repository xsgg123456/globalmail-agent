"""Validated risks stay active until a scoped, version-checked human decision resolves them."""
import json
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.agent_schema import agent_risks
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.adapters.body_store import read_body
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.base import canonical


def active_risks(conn, store, conv, status="active"):
    result = []
    query = sa.select(agent_risks).where(agent_risks.c.conversation_id == conv["id"],
        *[agent_risks.c[k] == conv[k] for k in SCOPE_KEYS])
    if status:
        query = query.where(agent_risks.c.status == status)
    for row in conn.execute(query).mappings():
        value = json.loads(read_body(conn, store, conv, row["body_object_id"]))
        result.append({"id": str(row["id"]), "kind": row["kind"], "status": row["status"], **value})
    return result


def store_risks(conn, writer, conv, run, understanding, source_object):
    for kind in {r["kind"] for r in understanding["risk_flags"]}:
        existing = conn.execute(sa.select(agent_risks.c.id).where(agent_risks.c.conversation_id == conv["id"],
            agent_risks.c.kind == kind, agent_risks.c.status == "active")).scalar_one_or_none()
        if existing:
            continue
        sources = [source for risk in understanding["risk_flags"] if risk["kind"] == kind for source in risk["sources"]]
        body = writer.put(conn, conv, canonical({"sources": sources, "language": understanding["language"]}).decode(),
            "validated_risk", (source_object,))
        conn.execute(sa.insert(agent_risks).values(id=uuid4(), **{k: conv[k] for k in SCOPE_KEYS},
            conversation_id=conv["id"], run_id=run["id"], kind=kind, status="active", body_object_id=body))


def resolve_risks(conn, conv, review, decision, note_object):
    if decision == "keep_active":
        return
    active = conn.execute(sa.select(agent_risks.c.id).where(agent_risks.c.conversation_id == conv["id"],
        agent_risks.c.status == "active").with_for_update()).scalars().all()
    if conv["mode"] != "simulation" or not active or note_object is None:
        raise ServiceError("risk_decision_requires_evidence", 422)
    conn.execute(agent_risks.update().where(agent_risks.c.id.in_(active)).values(status=decision,
        resolution_review_id=review["id"], resolution_object_id=note_object))
