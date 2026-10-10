"""Idempotent local body purge; identifiers and business deduplication survive."""
import hashlib
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.schema import metadata, objects, deletion_journal
from globalmail_agent.adapters import conversation_schema as c, knowledge_schema as k
from globalmail_agent.adapters import knowledge_index_schema as ix
from globalmail_agent.application.lifecycle_inventory import ids
from globalmail_agent.knowledge.base import canonical, sha

SCRUB = {
    "messages": {"subject": ""}, "human_reviews": {"reason": "", "status": "closed"},
    "domain_events": {"payload": {}, "status": "cancelled"}, "ui_events": {"payload": {}},
    "tool_commands": {"arguments": {}}, "understanding_revisions": {"change_reason": "", "source_ids": []},
    "reply_artifacts": {"claims": [], "citation_ids": []},
    "visual_analyses": {"attachment_manifest": []}, "visual_evidence": {"location": {}},
    "message_attachments": {"filename": "", "manifest": {}, "cid": None},
    "agent_run_contexts": {"observed_wakes": [], "observed_event_ids": [], "validated_draft_hash": None},
    "agent_run_dependencies": {"active": False},
    "case_issues": {"order_number": None},
}


def checkpoints(conn, run_ids, verify=False):
    existing = set(sa.inspect(conn).get_table_names())
    for name in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
        if name not in existing:
            continue
        table = sa.Table(name, sa.MetaData(), autoload_with=conn)
        predicate = table.c.thread_id.in_([str(v) for v in run_ids])
        if verify:
            if conn.execute(sa.select(sa.func.count()).select_from(table).where(predicate)).scalar_one():
                raise RuntimeError("checkpoint_residue")
        else:
            conn.execute(table.delete().where(predicate))


def scrub_receipts(conn, workspace, manifest, target_id):
    tokens = {str(target_id), *manifest["object_ids"], *manifest["run_ids"], *manifest["conversation_ids"],
        *manifest["version_ids"], *manifest["build_ids"]}
    # Receipts have no conversation FK; both operation and recursive result IDs identify holders.
    for row in conn.execute(sa.select(c.request_receipts).where(c.request_receipts.c.workspace_id == workspace)).mappings():
        body = str(row["result"])
        if any(token in row["operation"] or token in body for token in tokens):
            conn.execute(c.request_receipts.update().where(c.request_receipts.c.id == row["id"])
                .values(result={"deleted": True}))


def scrub_business(conn, manifest):
    conv_ids = ids(manifest, "conversation_ids")
    scopes = conn.execute(sa.select(c.conversations).where(c.conversations.c.id.in_(conv_ids))).mappings().all()
    for table in list(metadata.tables.values()):
        if "branch_id" not in table.c or table.name in {"objects", "deletion_requests", "deletion_journal"}:
            continue
        values = {key: {} for key in ("source_snapshot", "details", "decision_data", "result") if key in table.c}
        if "source_snapshot" in table.c and "source_ref" in table.c:
            values["source_ref"] = "deleted"
        if table.name == "simulation_events":
            values["payload"] = {}
        if table.name == "simulation_branches":
            values.update(state={}, tool_overrides={})
        if not values:
            continue
        for scope in scopes:
            conn.execute(table.update().where(table.c.workspace_id == scope["workspace_id"],
                table.c.branch_id == scope["branch_id"], table.c.mode == scope["mode"]).values(**values))


def purge_knowledge(conn, target_id, manifest):
    versions, builds, caches = (ids(manifest, name) for name in ("version_ids", "build_ids", "cache_ids"))
    cache_ids = list(conn.execute(sa.select(ix.index_chunks.c.cache_id).where(ix.index_chunks.c.build_id.in_(builds))).scalars())
    conn.execute(ix.index_chunks.delete().where(ix.index_chunks.c.build_id.in_(builds)))
    conn.execute(ix.index_parents.delete().where(ix.index_parents.c.build_id.in_(builds)))
    for cache_id in set(cache_ids) - {None}:
        used = conn.execute(sa.select(ix.index_chunks.c.id).where(ix.index_chunks.c.cache_id == cache_id)).first()
        if not used:
            conn.execute(ix.embedding_cache.delete().where(ix.embedding_cache.c.id == cache_id))
    for table, values in [(k.blocks, {"text": "", "structure": {}}),
            (k.applicabilities, {"basis": "deleted"}),
            (k.knowledge_reviews, {"note": "", "exclusion_reason": None, "excluded_block_ids": []}),
            (k.policy_bundles, {"rules": {}, "rule_schema": {}, "description": ""})]:
        conn.execute(table.update().where(table.c.version_id.in_(versions)).values(**values))
    conn.execute(k.parse_caches.update().where(k.parse_caches.c.id.in_(caches)).values(asset_map={}))
    conn.execute(k.knowledge_audits.update().where(k.knowledge_audits.c.document_id == target_id).values(details={}))
    conn.execute(k.document_versions.update().where(k.document_versions.c.id.in_(versions))
        .values(title="deleted", diagnostics=[], status="cancelled"))
    conn.execute(k.documents.update().where(k.documents.c.id == target_id)
        .values(title="deleted", source_reference="deleted", lifecycle="deleted"))
    conn.execute(k.uploads.update().where(k.uploads.c.object_id.in_(ids(manifest, "object_ids"))).values(filename="deleted"))
    conn.execute(k.knowledge_assets.update().where(k.knowledge_assets.c.cache_id.in_(caches))
        .values(asset_key=sa.literal("deleted:") + sa.cast(k.knowledge_assets.c.id, sa.String)))
    conn.execute(ix.evidence_refs.update().where(ix.evidence_refs.c.document_id == target_id)
        .values(reference={"status": "deleted"}))
    for release in conn.execute(sa.select(ix.knowledge_releases)).mappings():
        old = release["manifest"]
        entries = [entry for entry in old.get("entries", []) if entry.get("document_id") != str(target_id)]
        if len(entries) != len(old.get("entries", [])):
            revised = {**old, "entries": entries}
            conn.execute(ix.knowledge_releases.update().where(ix.knowledge_releases.c.id == release["id"])
                .values(manifest=revised, manifest_sha256=sha(canonical(revised))))


def purge_local(conn, store, request):
    conn.execute(sa.text("SELECT set_config('globalmail.deletion_request', :id, true)"), {"id": str(request["id"])})
    manifest = request["manifest"]
    for name, values in SCRUB.items():
        table = metadata.tables[name]
        holder_ids = [UUID(value) for value in manifest["holders"].get(name, [])]
        conn.execute(table.update().where(table.c.id.in_(holder_ids)).values(**values))
    scrub_business(conn, manifest)
    scrub_receipts(conn, request["workspace_id"], manifest, request["target_id"])
    checkpoints(conn, ids(manifest, "run_ids"))
    if request["target_type"] == "document":
        purge_knowledge(conn, request["target_id"], manifest)
    if request["target_type"] == "conversation":
        reset_branch(conn, request)
        conn.execute(c.identities.update().where(c.identities.c.id == request["customer_id"])
            .values(sender_key="deleted:" + str(request["customer_id"]), source_ref="deleted"))
        conn.execute(c.messages.update().where(c.messages.c.conversation_id == request["target_id"])
            .values(source_ref="deleted", source_message_id=sa.cast(c.messages.c.id, sa.String)))
        conn.execute(c.conversations.update().where(c.conversations.c.id == request["target_id"])
            .values(subject="", lifecycle="deleted"))
    for identity in ids(manifest, "object_ids"):
        store._path(identity).unlink(missing_ok=True)
    conn.execute(objects.update().where(objects.c.id.in_(ids(manifest, "object_ids")))
        .values(size_bytes=0, sha256=hashlib.sha256(b"").hexdigest(), source_ref="deleted"))


def reset_branch(conn, request):
    if request["mode"] != "simulation":
        return
    # The branch is terminal. Keep IDs/status/amounts for deduplication, release its occupancy.
    for name, values in (("compensation_reservations", {"active": False}),
            ("inventory_reservations", {"state": "released"}), ("inventory", {"reserved": 0})):
        table = metadata.tables[name]
        predicate = [table.c.workspace_id == request["workspace_id"],
            table.c.branch_id == request["branch_id"], table.c.mode == "simulation"]
        if name == "inventory_reservations":
            predicate.append(table.c.state == "reserved")
        conn.execute(table.update().where(*predicate).values(**values))
    if request["action"] == "reset" and not request.get("replacement_conversation_id"):
        from globalmail_agent.application.conversation_base import ServiceBase
        from globalmail_agent.adapters.lifecycle_schema import deletion_requests
        identity = conn.execute(sa.select(c.identities).where(c.identities.c.id == request["customer_id"])).mappings().one()
        fresh = ServiceBase(conn.engine, None, request["workspace_id"]).new_conversation(conn,
            identity["sender_key"], "simulation", "", identity["verified"], "lifecycle-reset", dataset=uuid4())
        conn.execute(deletion_requests.update().where(deletion_requests.c.id == request["id"])
            .values(replacement_conversation_id=fresh["id"]))


def verify_local(conn, store, request):
    manifest = request["manifest"]
    for identity in ids(manifest, "object_ids"):
        if store._path(identity).exists():
            raise RuntimeError("object_residue")
    checkpoints(conn, ids(manifest, "run_ids"), verify=True)
    for name, values in SCRUB.items():
        table = metadata.tables[name]
        holder_ids = [UUID(value) for value in manifest["holders"].get(name, [])]
        for row in conn.execute(sa.select(table).where(table.c.id.in_(holder_ids))).mappings():
            if any(row[key] != value for key, value in values.items()):
                raise RuntimeError("inline_content_residue")
    writable = conn.execute(sa.select(c.agent_runs.c.id).where(c.agent_runs.c.id.in_(ids(manifest, "run_ids")),
        c.agent_runs.c.checkpoint_writable.is_(True))).first()
    if writable:
        raise RuntimeError("writer_still_active")
    for name in ("jobs",):
        table = metadata.tables[name]
        active = conn.execute(sa.select(table.c.id).where(table.c.run_id.in_(ids(manifest, "run_ids")),
            table.c.status.in_(["queued", "running"]))).first()
        if active:
            raise RuntimeError("job_still_active")
    if request["target_type"] == "document":
        verify_knowledge(conn, manifest)
    verify_business(conn, manifest)
    conn.execute(deletion_journal.update().where(deletion_journal.c.target_object_id.in_(ids(manifest, "object_ids")))
        .values(state="verified"))


def verify_knowledge(conn, manifest):
    versions, builds = ids(manifest, "version_ids"), ids(manifest, "build_ids")
    for table, predicate in ((ix.index_chunks, ix.index_chunks.c.build_id.in_(builds)),
            (ix.index_parents, ix.index_parents.c.build_id.in_(builds))):
        if conn.execute(sa.select(table.c.id).where(predicate)).first():
            raise RuntimeError("knowledge_index_residue")
    for table, values in ((k.blocks, {"text": "", "structure": {}}),
            (k.policy_bundles, {"rules": {}, "rule_schema": {}, "description": ""}),
            (k.knowledge_reviews, {"note": "", "exclusion_reason": None}),
            (k.applicabilities, {"basis": "deleted"})):
        for row in conn.execute(sa.select(table).where(table.c.version_id.in_(versions))).mappings():
            if any(row[key] != value for key, value in values.items()):
                raise RuntimeError("knowledge_inline_residue")


def verify_business(conn, manifest):
    scopes = conn.execute(sa.select(c.conversations).where(c.conversations.c.id.in_(ids(manifest, "conversation_ids")))).mappings()
    for scope in scopes:
        for table in list(metadata.tables.values()):
            keys = [key for key in ("source_snapshot", "details", "decision_data", "result") if key in table.c]
            if "branch_id" not in table.c or not keys:
                continue
            for row in conn.execute(sa.select(table).where(table.c.workspace_id == scope["workspace_id"],
                    table.c.branch_id == scope["branch_id"], table.c.mode == scope["mode"])).mappings():
                if any(row[key] != {} for key in keys):
                    raise RuntimeError("business_inline_residue")
