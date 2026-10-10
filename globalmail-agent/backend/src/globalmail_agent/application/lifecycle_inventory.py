"""Enumerate persisted holders before revocation and again before completion."""
from uuid import UUID
import sqlalchemy as sa
from globalmail_agent.adapters.schema import metadata, objects, content_dependencies
from globalmail_agent.adapters import conversation_schema as c, knowledge_schema as k
from globalmail_agent.adapters import knowledge_index_schema as ix, agent_schema as a
from globalmail_agent.adapters import attachment_schema as image
from globalmail_agent.adapters import business_schema, after_sales_schema  # noqa: F401
from globalmail_agent.application.conversation_lock import ServiceError

TARGETS = {"conversation": c.conversations, "document": k.documents, "attachment": image.message_attachments}


def target(conn, workspace, kind, identity, lock=False):
    if kind not in TARGETS:
        raise ServiceError("invalid_deletion_target", 422)
    table = TARGETS[kind]
    query = sa.select(table).where(table.c.id == identity, table.c.workspace_id == workspace)
    row = conn.execute(query.with_for_update() if lock else query).mappings().first()
    if not row:
        raise ServiceError("deletion_target_not_found", 404)
    return dict(row)


def descendants(conn, roots):
    found = set(roots)
    while found:
        more = set(conn.execute(sa.select(content_dependencies.c.dependent_object_id).where(
            content_dependencies.c.source_object_id.in_(found))).scalars()) - found
        if not more:
            break
        found.update(more)
    return found


def enumerate_holders(conn, workspace, kind, row):
    roots, convs, versions, builds, caches, blocked = set(), set(), set(), set(), set(), []
    if kind == "conversation":
        convs.add(row["id"])
    elif kind == "attachment":
        convs.add(row["conversation_id"])
        roots.update(row[key] for key in ("source_object_id", "thumbnail_object_id") if row[key])
    else:
        version_rows = conn.execute(sa.select(k.document_versions).where(
            k.document_versions.c.document_id == row["id"])).mappings().all()
        versions.update(v["id"] for v in version_rows)
        roots.update(v["object_id"] for v in version_rows)
        caches.update(v["cache_id"] for v in version_rows if v["cache_id"])
        others = conn.execute(sa.select(k.document_versions.c.document_id).join(k.documents,
            k.documents.c.id == k.document_versions.c.document_id).where(k.documents.c.lifecycle != "deleted",
            k.document_versions.c.document_id != row["id"], sa.or_(
                k.document_versions.c.object_id.in_(roots), k.document_versions.c.cache_id.in_(caches)))).scalars()
        blocked = sorted({str(v) for v in others})
        roots.update(conn.execute(sa.select(k.parse_caches.c.result_object_id).where(k.parse_caches.c.id.in_(caches))).scalars())
        roots.update(conn.execute(sa.select(k.knowledge_assets.c.object_id).where(k.knowledge_assets.c.cache_id.in_(caches))).scalars())
        builds.update(conn.execute(sa.select(ix.index_builds.c.id).where(ix.index_builds.c.document_id == row["id"])).scalars())
        refs = conn.execute(sa.select(ix.evidence_refs).where(ix.evidence_refs.c.document_id == row["id"])).mappings().all()
        roots.update(r["content_object_id"] for r in refs)
        convs.update(conn.execute(sa.select(a.agent_run_dependencies.c.conversation_id).where(
            a.agent_run_dependencies.c.document_id == row["id"])).scalars())
    runs = set(conn.execute(sa.select(c.agent_runs.c.id).where(c.agent_runs.c.conversation_id.in_(convs))).scalars())
    holders = {}
    # A dependency run may have copied a fact into any later summary in its case.
    # Scrub that case's derived holders conservatively, preserving its source mail.
    for table in list(metadata.tables.values()):
        if "conversation_id" not in table.c or table.name == "deletion_requests":
            continue
        query = sa.select(table).where(table.c.conversation_id.in_(convs))
        if kind != "conversation" and table.name == "messages":
            query = query.where(table.c.sender.in_(["simulated_agent", "simulated_human"]))
        if kind != "conversation" and table.name == "message_attachments":
            query = query.where(table.c.id == row["id"] if kind == "attachment" else sa.false())
        rows = conn.execute(query).mappings().all()
        holders[table.name] = [str(r["id"]) for r in rows]
        for holder in rows:
            for column in table.c:
                # Cross-scope input links are not owned outputs of this conversation.
                if table.name == 'agent_run_dependencies' and column.name == 'source_object_id':
                    continue
                if column.name.endswith("object_id") and holder[column.name]:
                    roots.add(holder[column.name])
    roots = descendants(conn, roots)
    if kind == "conversation":
        # Include registered but not yet attached uploads and abandoned task output.
        roots.update(conn.execute(sa.select(objects.c.id).where(*[
            objects.c[key] == row[key] for key in ("workspace_id", "mode", "branch_id", "customer_id", "purpose")])).scalars())
        roots = descendants(conn, roots)
    return {"object_ids": sorted(map(str, roots)), "conversation_ids": sorted(map(str, convs)),
        "run_ids": sorted(map(str, runs)), "version_ids": sorted(map(str, versions)),
        "build_ids": sorted(map(str, builds)), "cache_ids": sorted(map(str, caches)),
        "holders": holders, "blocked_document_ids": blocked,
        "branch_reset": kind == "conversation" and row["mode"] == "simulation"}


def ids(manifest, name):
    return [UUID(value) for value in manifest.get(name, [])]


def impact(manifest):
    return {"objects": len(manifest["object_ids"]), "runs": len(manifest["run_ids"]),
        "conversations": len(manifest["conversation_ids"]), "versions": len(manifest["version_ids"]),
        "conversation_ids": manifest["conversation_ids"],
        "blocked_document_ids": manifest["blocked_document_ids"],
        "external_copies_included": False, "business_ledger_retained": True,
        "branch_reservations_released": manifest.get("branch_reset", False)}
