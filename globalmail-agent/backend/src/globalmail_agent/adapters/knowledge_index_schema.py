"""Scoped immutable vector inputs, build manifests and publication snapshots."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from globalmail_agent.adapters.schema import metadata, SCOPE_KEYS
from globalmail_agent.adapters.knowledge_schema import scoped, fk


embedding_profiles = scoped("embedding_profiles",
    sa.Column("profile_key", sa.String(80), nullable=False),
    sa.Column("profile_sha256", sa.String(64), nullable=False),
    sa.Column("configuration", JSONB, nullable=False),
    sa.Column("dimensions", sa.Integer, nullable=False),
    sa.UniqueConstraint(*SCOPE_KEYS, "profile_sha256"), sa.CheckConstraint("dimensions = 1024"))
embedding_probes = scoped("embedding_probes",
    sa.Column("profile_id", sa.Uuid, nullable=False), sa.Column("probe_vector", Vector(1024), nullable=False),
    fk("embedding_profiles", "profile_id"), sa.UniqueConstraint("profile_id"))
index_builds = scoped("index_builds",
    sa.Column("document_id", sa.Uuid, nullable=False), sa.Column("version_id", sa.Uuid, nullable=False),
    sa.Column("profile_id", sa.Uuid, nullable=False), sa.Column("chunker_key", sa.String(80), nullable=False),
    sa.Column("chunker_configuration", JSONB, nullable=False), sa.Column("input_sha256", sa.String(64), nullable=False),
    sa.Column("source_sha256", sa.String(64), nullable=False), sa.Column("parse_sha256", sa.String(64), nullable=False),
    sa.Column("applicability_sha256", sa.String(64), nullable=False),
    *[sa.Column(k, sa.BigInteger, nullable=False) for k in ("document_fence", "revocation_epoch", "parse_generation")],
    sa.Column("status", sa.String(24), nullable=False), sa.Column("stage", sa.String(40), nullable=False),
    sa.Column("row_version", sa.BigInteger, nullable=False, server_default="1"),
    sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
    sa.Column("embedded_count", sa.Integer, nullable=False, server_default="0"),
    sa.Column("cache_hits", sa.Integer, nullable=False, server_default="0"),
    sa.Column("usage", JSONB, nullable=False, server_default="[]"), sa.Column("error_code", sa.String(80)),
    sa.Column("retryable", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("manifest_sha256", sa.String(64)), fk("documents", "document_id"), fk("embedding_profiles", "profile_id"),
    sa.ForeignKeyConstraint(["version_id", "document_id", *SCOPE_KEYS],
        ["document_versions.id", "document_versions.document_id", *[f"document_versions.{k}" for k in SCOPE_KEYS]]),
    sa.UniqueConstraint("id", "document_id", *SCOPE_KEYS),
    sa.CheckConstraint("status IN ('queued','indexing','ready','failed','cancelled')"),
    sa.CheckConstraint("chunk_count >= 0 AND embedded_count >= 0 AND cache_hits >= 0"))
index_parents = scoped("index_parents",
    sa.Column("build_id", sa.Uuid, nullable=False), sa.Column("position", sa.Integer, nullable=False),
    sa.Column("section_id", sa.String(160), nullable=False), sa.Column("text", sa.Text, nullable=False),
    sa.Column("content_sha256", sa.String(64), nullable=False), sa.Column("applicability", JSONB, nullable=False),
    sa.Column("locations", JSONB, nullable=False), sa.Column("proxy_tokens", sa.Integer, nullable=False),
    fk("index_builds", "build_id"), sa.UniqueConstraint("id", "build_id", *SCOPE_KEYS),
    sa.UniqueConstraint("build_id", "position"))
embedding_cache = scoped("embedding_cache",
    sa.Column("profile_id", sa.Uuid, nullable=False), sa.Column("input_sha256", sa.String(64), nullable=False),
    sa.Column("input_text", sa.Text, nullable=False), sa.Column("vector", Vector(1024), nullable=False),
    fk("embedding_profiles", "profile_id"), sa.UniqueConstraint(*SCOPE_KEYS, "profile_id", "input_sha256"))
index_chunks = scoped("index_chunks",
    sa.Column("build_id", sa.Uuid, nullable=False), sa.Column("parent_id", sa.Uuid, nullable=False),
    sa.Column("position", sa.Integer, nullable=False), sa.Column("input_text", sa.Text, nullable=False),
    sa.Column("input_sha256", sa.String(64), nullable=False), sa.Column("cache_id", sa.Uuid),
    fk("index_builds", "build_id"), fk("embedding_cache", "cache_id"),
    sa.ForeignKeyConstraint(["parent_id", "build_id", *SCOPE_KEYS],
        ["index_parents.id", "index_parents.build_id", *[f"index_parents.{k}" for k in SCOPE_KEYS]]),
    sa.UniqueConstraint("build_id", "position"))
knowledge_releases = scoped("knowledge_releases",
    sa.Column("profile_id", sa.Uuid), sa.Column("epoch", sa.BigInteger, nullable=False),
    sa.Column("operation", sa.String(24), nullable=False), sa.Column("manifest", JSONB, nullable=False),
    sa.Column("manifest_sha256", sa.String(64), nullable=False), sa.Column("actor", sa.String(160), nullable=False),
    sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False), fk("embedding_profiles", "profile_id"),
    sa.UniqueConstraint(*SCOPE_KEYS, "epoch"))
knowledge_release_items = scoped("knowledge_release_items",
    sa.Column("release_id", sa.Uuid, nullable=False), sa.Column("document_id", sa.Uuid, nullable=False),
    sa.Column("build_id", sa.Uuid, nullable=False), sa.Column("revocation_epoch", sa.BigInteger, nullable=False),
    fk("knowledge_releases", "release_id"), fk("documents", "document_id"),
    sa.ForeignKeyConstraint(["build_id", "document_id", *SCOPE_KEYS],
        ["index_builds.id", "index_builds.document_id", *[f"index_builds.{k}" for k in SCOPE_KEYS]]),
    sa.UniqueConstraint("release_id", "document_id"))
knowledge_release_heads = scoped("knowledge_release_heads",
    sa.Column("release_id", sa.Uuid), sa.Column("epoch", sa.BigInteger, nullable=False, server_default="0"),
    sa.Column("profile_id", sa.Uuid), fk("knowledge_releases", "release_id"), fk("embedding_profiles", "profile_id"),
    sa.UniqueConstraint(*SCOPE_KEYS), sa.UniqueConstraint("workspace_id", "purpose"))
evidence_refs = scoped("evidence_refs", sa.Column("release_id", sa.Uuid, nullable=False),
    sa.Column("build_id", sa.Uuid, nullable=False), sa.Column("document_id", sa.Uuid, nullable=False),
    sa.Column("revocation_epoch", sa.BigInteger, nullable=False), sa.Column("content_object_id", sa.Uuid, nullable=False),
    sa.Column("reference", JSONB, nullable=False), fk("knowledge_releases", "release_id"),
    fk("index_builds", "build_id"), fk("documents", "document_id"), fk("objects", "content_object_id"))
knowledge_dependencies = scoped("knowledge_dependencies",
    sa.Column("reference_id", sa.Uuid, nullable=False), sa.Column("source_object_id", sa.Uuid, nullable=False),
    sa.Column("content_object_id", sa.Uuid, nullable=False), sa.Column("holder_kind", sa.String(80), nullable=False),
    fk("evidence_refs", "reference_id"), fk("objects", "source_object_id"), fk("objects", "content_object_id"),
    sa.UniqueConstraint("reference_id", "source_object_id", "holder_kind"))

from globalmail_agent.adapters.conversation_schema import jobs
jobs.append_constraint(sa.ForeignKeyConstraint(["index_build_id", *SCOPE_KEYS],
    ["index_builds.id", *[f"index_builds.{k}" for k in SCOPE_KEYS]], name="jobs_index_build_scope"))
jobs.append_constraint(sa.CheckConstraint("knowledge_operation IN ('parse','index') AND "
    "(knowledge_operation = 'parse' AND index_build_id IS NULL OR knowledge_operation = 'index' AND index_build_id IS NOT NULL AND knowledge_version_id IS NOT NULL)",
    name="jobs_knowledge_operation"))
