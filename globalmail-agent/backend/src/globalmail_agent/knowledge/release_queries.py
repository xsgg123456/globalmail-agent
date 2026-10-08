"""Read-only projections of publication heads and complete immutable manifests."""
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_index_schema import knowledge_release_heads, knowledge_releases, knowledge_release_items, index_builds, embedding_profiles
from globalmail_agent.adapters.knowledge_schema import documents
from globalmail_agent.knowledge.base import scoped_where
from globalmail_agent.application.conversation_lock import ServiceError


def head(conn, workspace, lock=False):
    query = sa.select(knowledge_release_heads).where(*scoped_where(knowledge_release_heads, workspace))
    row = conn.execute(query.with_for_update() if lock else query).mappings().first()
    return dict(row) if row else {"release_id": None, "epoch": 0, "profile_id": None}


def head_view(row):
    return {"release_id": str(row["release_id"]) if row["release_id"] else None, "epoch": row["epoch"],
        "embedding_profile_id": str(row["profile_id"]) if row["profile_id"] else None}


def published_condition(workspace):
    return sa.exists(sa.select(knowledge_release_items.c.id)
        .join(knowledge_release_heads, knowledge_release_heads.c.release_id == knowledge_release_items.c.release_id)
        .join(index_builds, index_builds.c.id == knowledge_release_items.c.build_id)
        .where(knowledge_release_items.c.document_id == documents.c.id,
            documents.c.withdrawn.is_(False), index_builds.c.status == "ready",
            knowledge_release_items.c.revocation_epoch == documents.c.revocation_epoch,
            *scoped_where(knowledge_release_items, workspace), *scoped_where(knowledge_release_heads, workspace),
            *scoped_where(index_builds, workspace)))


def release_row(conn, workspace, identity):
    row = conn.execute(sa.select(knowledge_releases).where(knowledge_releases.c.id == identity,
        *scoped_where(knowledge_releases, workspace))).mappings().first()
    if row is None:
        raise ServiceError("release_not_found", 404)
    return dict(row)


def release_view(conn, workspace, row):
    profile = conn.execute(sa.select(embedding_profiles.c.configuration).where(embedding_profiles.c.id == row["profile_id"],
        *scoped_where(embedding_profiles, workspace))).scalar_one_or_none() if row["profile_id"] else None
    return {"id": str(row["id"]), "epoch": row["epoch"], "operation": row["operation"], "profile": profile,
        "embedding_profile_id": str(row["profile_id"]) if row["profile_id"] else None, "entries": row["manifest"]["entries"], "manifest_sha256": row["manifest_sha256"],
        "effective_at": row["effective_at"].isoformat(), "created_at": row["created_at"].isoformat(), "actor": row["actor"]}


def publication(conn, workspace, document_id):
    current = head(conn, workspace)
    if current["release_id"] is None:
        return None
    row = conn.execute(sa.select(knowledge_release_items, index_builds.c.version_id, index_builds.c.profile_id)
        .join(index_builds, index_builds.c.id == knowledge_release_items.c.build_id)
        .join(documents, documents.c.id == knowledge_release_items.c.document_id)
        .where(knowledge_release_items.c.release_id == current["release_id"], knowledge_release_items.c.document_id == document_id,
            documents.c.withdrawn.is_(False), documents.c.lifecycle == "active", index_builds.c.status == "ready",
            knowledge_release_items.c.revocation_epoch == documents.c.revocation_epoch,
            *scoped_where(knowledge_release_items, workspace))).mappings().first()
    return {"release_id": current["release_id"], "release_epoch": current["epoch"], "build_id": row["build_id"],
        "version_id": row["version_id"], "embedding_profile_id": row["profile_id"]} if row else None
