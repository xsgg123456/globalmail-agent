"""Persist analysis and provenance in the same guarded transaction as understanding/HITL."""
import json
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.attachment_schema import message_attachments, visual_analyses, visual_evidence
from globalmail_agent.adapters.body_store import read_bytes
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.attachments.queries import authorize_attachment
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.base import canonical, sha


def scoped(table, conv):
    return [table.c.conversation_id == conv["id"], *[table.c[k] == conv[k] for k in SCOPE_KEYS]]


def context_images(conn, store, conv):
    from globalmail_agent.adapters.conversation_schema import messages
    rows = list(conn.execute(sa.select(message_attachments).join(messages,
        message_attachments.c.message_id == messages.c.id).where(*scoped(message_attachments, conv),
        messages.c.seq <= conv["visible_message_seq"]).order_by(messages.c.seq, message_attachments.c.position)).mappings())
    manifest = [{"attachment_id": str(r["id"]), "message_id": str(r["message_id"]),
        "revision": r["revision"], "evidence_epoch": r["evidence_epoch"], "status": r["status"],
        "source_sha256": r["source_sha256"], "source_available_at": r["created_at"].isoformat(),
        "filename": r["filename"]} for r in rows]
    notes, sources = [], {}
    for row in conn.execute(sa.select(visual_evidence).where(*scoped(visual_evidence, conv),
            visual_evidence.c.manual.is_(True)).order_by(visual_evidence.c.created_at)).mappings():
        attachment = next((r for r in rows if r["id"] == row["attachment_id"]), None)
        if not attachment or attachment["status"] == "revoked" or row["evidence_epoch"] != attachment["evidence_epoch"]:
            continue
        value = json.loads(read_bytes(conn, store, conv, row["body_object_id"]))
        identity = "visual:" + str(row["id"])
        source = {"message_id": identity, "sender": "human_note", "body": value["value"] + "\n核对依据：" + value["reason"],
            "attachment_id": str(row["attachment_id"]), "kind": "manual_image_correction",
            "correction": value, "evidence_kind": row["kind"]}
        sources[identity] = source
        notes.append(source)
    return manifest, notes, sources, tuple(r["source_object_id"] for r in rows if r["source_object_id"] and r["status"] != "revoked")


def store_visual_analysis(conn, writer, conv, run, value):
    images = value.pop("_visual_raw_images", value.get("images", []))
    if not images:
        return
    old = conn.execute(sa.select(visual_analyses.c.id).where(visual_analyses.c.run_id == run["id"])).scalar_one_or_none()
    if old:
        return
    refs = value.get("image_views", [])
    if {r["attachment_id"] for r in refs} != {r["attachment_id"] for r in images}:
        raise ServiceError("visual_coverage_invalid", 422)
    scope = {k: conv[k] for k in SCOPE_KEYS}
    sources = []
    rows = {}
    for ref in refs:
        row = authorize_attachment(conn, conv, UUID(ref["attachment_id"]), lock=True)
        if row["evidence_epoch"] != ref["evidence_epoch"] or row["revision"] != ref["revision"]:
            raise ServiceError("image_evidence_stale")
        rows[ref["attachment_id"]] = row
        sources.extend([row["source_object_id"], UUID(ref["view_object_id"])])
    body = writer.put(conn, conv, canonical(images).decode(), "visual_analysis", tuple(sources))
    analysis = uuid4()
    conn.execute(sa.insert(visual_analyses).values(id=analysis, **scope, conversation_id=conv["id"], run_id=run["id"],
        body_object_id=body, context_hash=value["visual_context_hash"], model="qwen3.7-plus",
        prompt_version="visual/1", preprocess_version=refs[0]["preprocess_version"], attachment_manifest=refs))
    for image in images:
        row = rows[image["attachment_id"]]
        ref = next(r for r in refs if r["attachment_id"] == image["attachment_id"])
        manual = [(r["kind"], json.loads(read_bytes(conn, writer.store, conv, r["body_object_id"]))) for r in
            conn.execute(sa.select(visual_evidence).where(*scoped(visual_evidence, conv),
                visual_evidence.c.attachment_id == row["id"], visual_evidence.c.evidence_epoch == row["evidence_epoch"],
                visual_evidence.c.manual.is_(True))).mappings()]
        entries = [("field_candidate", field) for field in image["field_candidates"]]
        entries += [(kind, {"value": text}) for key, kind in (("observations", "observation"),
            ("hypotheses", "hypothesis"), ("uncertainties", "uncertainty"), ("risk_flags", "risk_flag")) for text in image[key]]
        for kind, content in entries:
            if any(k == kind and (kind != "field_candidate" or c.get("key") == content.get("key")) for k, c in manual):
                continue
            content = {**content, "coverage": image["coverage"], "quality": image["quality"]}
            object_id = writer.put(conn, conv, canonical(content).decode(), "visual_evidence", (body,))
            conn.execute(sa.insert(visual_evidence).values(id=uuid4(), **scope, conversation_id=conv["id"],
                analysis_id=analysis, attachment_id=row["id"], message_id=row["message_id"],
                revision=row["evidence_epoch"], evidence_epoch=row["evidence_epoch"], kind=kind,
                body_object_id=object_id, source_sha256=row["source_sha256"],
                derived_view_hash=ref["derived_view_hash"], location=ref["location"], manual=False))
        conn.execute(message_attachments.update().where(message_attachments.c.id == row["id"])
            .values(status=image["status"], failure_reason=None))


def evidence_listing(conn, store, conv, attachment_id):
    attachment = authorize_attachment(conn, conv, attachment_id)
    items = []
    for row in conn.execute(sa.select(visual_evidence).where(*scoped(visual_evidence, conv),
            visual_evidence.c.attachment_id == attachment_id,
            visual_evidence.c.evidence_epoch == attachment["evidence_epoch"])
            .order_by(visual_evidence.c.created_at)).mappings():
        content = json.loads(read_bytes(conn, store, conv, row["body_object_id"]))
        items.append({"evidence_id": str(row["id"]), "attachment_id": str(row["attachment_id"]),
            "message_id": str(row["message_id"]), "revision": row["revision"], "evidence_epoch": row["evidence_epoch"],
            "kind": row["kind"], "manual": row["manual"], "source_sha256": row["source_sha256"],
            "derived_view_hash": row["derived_view_hash"], "location": row["location"],
            "created_at": row["created_at"], **content})
    latest = conn.execute(sa.select(visual_analyses).where(*scoped(visual_analyses, conv),
        visual_analyses.c.attachment_manifest.contains([{"attachment_id": str(attachment_id),
            "evidence_epoch": attachment["evidence_epoch"]}])).order_by(visual_analyses.c.created_at.desc()).limit(1)).mappings().first()
    coverage = next((r for r in json.loads(read_bytes(conn, store, conv, latest["body_object_id"]))
        if r["attachment_id"] == str(attachment_id)), {}) if latest else {}
    return {"items": items, "evidence_revision": attachment["evidence_epoch"],
        "coverage": coverage.get("coverage"), "quality": coverage.get("quality")}
