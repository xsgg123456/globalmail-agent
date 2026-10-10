"""Use the same slot/head/conversation/object locks as ordinary writers."""
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.schema import objects, deletion_journal, SCOPE_KEYS
from globalmail_agent.adapters import conversation_schema as c, knowledge_schema as k
from globalmail_agent.adapters import knowledge_index_schema as ix, attachment_schema as image
from globalmail_agent.application.task_queue import invalidate
from globalmail_agent.application.lifecycle_inventory import ids
from globalmail_agent.knowledge.queue import invalidate_document_jobs


def lock_writers(conn, workspace):
    conn.execute(sa.select(c.agent_slots).where(c.agent_slots.c.workspace_id == workspace)
        .order_by(c.agent_slots.c.slot_key).with_for_update()).all()
    conn.execute(sa.select(ix.knowledge_release_heads).where(ix.knowledge_release_heads.c.workspace_id == workspace)
        .order_by(ix.knowledge_release_heads.c.id).with_for_update()).all()


def revoke(conn, workspace, kind, row, manifest):
    conv_ids = ids(manifest, "conversation_ids")
    from globalmail_agent.adapters.business_schema import simulation_branches
    conn.execute(sa.select(simulation_branches).where(simulation_branches.c.conversation_id.in_(conv_ids))
        .order_by(simulation_branches.c.id).with_for_update()).all()
    conn.execute(sa.select(c.conversations).where(c.conversations.c.id.in_(conv_ids))
        .order_by(c.conversations.c.id).with_for_update()).all()
    for cid in conv_ids:
        invalidate(conn, cid)
    conn.execute(c.agent_runs.update().where(c.agent_runs.c.id.in_(ids(manifest, "run_ids")))
        .values(checkpoint_writable=False, stop_requested=True))
    if conv_ids:
        values = {"input_revision": c.conversations.c.input_revision + 1,
            "row_version": c.conversations.c.row_version + 1,
            "authority_epoch": c.conversations.c.authority_epoch + 1,
            "auto_run_gate": "disabled", "scheduling_state": "idle"}
        if kind == "conversation":
            values.update(lifecycle="deleting", branch_generation=c.conversations.c.branch_generation + 1)
        conn.execute(c.conversations.update().where(c.conversations.c.id.in_(conv_ids)).values(**values))
    if kind == "document":
        invalidate_document_jobs(conn, workspace, row)
        conn.execute(k.documents.update().where(k.documents.c.id == row["id"]).values(
            withdrawn=True, lifecycle="deleting", document_fence=k.documents.c.document_fence + 1,
            revocation_epoch=k.documents.c.revocation_epoch + 1, row_version=k.documents.c.row_version + 1))
        # Publish a new legal snapshot; stale release_items must not remain at the head.
        from globalmail_agent.knowledge.releases import ReleaseService
        from globalmail_agent.knowledge.release_queries import head
        current = head(conn, workspace)
        if current.get('id'):
            releases = ReleaseService(conn.engine, None, workspace)
            remaining = {key:value for key,value in releases._current(conn, current).items() if key != str(row['id'])}
            entries, profile = releases._entries(conn, list(remaining.values()), verify_source=False)
            releases._write(conn, current, entries, profile, 'withdraw')
    if kind in {"attachment", "conversation"}:
        clause = image.message_attachments.c.id == row["id"] if kind == "attachment" else image.message_attachments.c.conversation_id == row["id"]
        conn.execute(image.message_attachments.update().where(clause).values(status="revoked",
            evidence_epoch=image.message_attachments.c.evidence_epoch + 1,
            revision=image.message_attachments.c.revision + 1))
    revoke_objects(conn, manifest)


def revoke_objects(conn, manifest):
    object_rows = conn.execute(sa.select(objects).where(objects.c.id.in_(ids(manifest, "object_ids")))
        .order_by(objects.c.id).with_for_update()).mappings().all()
    for obj in object_rows:
        exists = conn.execute(sa.select(deletion_journal.c.id).where(deletion_journal.c.target_object_id == obj["id"])).first()
        if not exists:
            conn.execute(deletion_journal.insert().values(id=uuid4(), **{key: obj[key] for key in SCOPE_KEYS},
                target_object_id=obj["id"], generation=1, state="revoked"))
