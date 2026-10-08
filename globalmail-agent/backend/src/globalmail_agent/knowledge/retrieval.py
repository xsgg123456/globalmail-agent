"""Filter eligibility before provider/PG ranking; one immutable head for the complete request."""
from uuid import UUID
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_index_schema import index_builds, index_chunks, index_parents, embedding_cache, knowledge_release_items
from globalmail_agent.adapters.knowledge_schema import documents, document_versions
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.knowledge.base import scoped_where, KnowledgeFiles, canonical, sha
from globalmail_agent.knowledge.build_checks import build_row, eligible
from globalmail_agent.knowledge.index_profiles import load_profile, verify_gateway
from globalmail_agent.knowledge.index_worker import validate_vector
from globalmail_agent.knowledge.release_queries import head, head_view, release_row
from globalmail_agent.knowledge.references import register_reference
from globalmail_agent.knowledge.validation import catalog
from globalmail_agent.knowledge.chunking import proxy_tokens


class KnowledgeSearch:
    def __init__(self, engine, store, gateway, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.gateway, self.workspace_id = engine, store, gateway, workspace_id

    def _reply(self, reason, current, count=0, evidence=None, usage=None, diagnostics=None):
        return {"reason": reason, "head": head_view(current), "candidate_count": count, "evidence": evidence or [],
            "usage": usage, "diagnostics": diagnostics or []}

    def _same(self, expected):
        with self.engine.connect() as conn:
            current = head(conn, self.workspace_id)
            return head_view(current) == head_view(expected)

    def _candidates(self, conn, current, command):
        if command.mode != "simulation" or current["release_id"] is None:
            return None
        release = release_row(conn, self.workspace_id, current["release_id"])
        if sha(canonical(release["manifest"])) != release["manifest_sha256"]:
            raise ServiceError("manifest_integrity_error", 503)
        product = next((p for p in catalog() if p["sku"] == command.sku), None)
        if not product or command.brand is not None and command.brand != product["brand"]:
            return []
        when = command.as_of or conn.execute(sa.select(sa.func.clock_timestamp())).scalar_one()
        # Every identity/purpose/mode/type/time/revocation filter precedes vector ordering.
        rows = conn.execute(sa.select(index_parents, index_builds.c.document_id, index_builds.c.version_id)
            .join(index_builds, index_builds.c.id == index_parents.c.build_id)
            .join(knowledge_release_items, knowledge_release_items.c.build_id == index_builds.c.id)
            .join(documents, documents.c.id == index_builds.c.document_id)
            .join(document_versions, document_versions.c.id == index_builds.c.version_id)
            .where(knowledge_release_items.c.release_id == current["release_id"], index_builds.c.profile_id == current["profile_id"],
                index_builds.c.status == "ready", documents.c.lifecycle == "active", documents.c.withdrawn.is_(False),
                documents.c.usage_split == "rag", documents.c.allowed_modes.contains(["simulation"]),
                knowledge_release_items.c.revocation_epoch == documents.c.revocation_epoch,
                index_builds.c.revocation_epoch == documents.c.revocation_epoch, document_versions.c.available_at <= when,
                sa.or_(documents.c.brand.is_(None), documents.c.brand == product["brand"]),
                *scoped_where(index_parents, self.workspace_id), *scoped_where(index_builds, self.workspace_id),
                *scoped_where(knowledge_release_items, self.workspace_id), *scoped_where(documents, self.workspace_id),
                *scoped_where(document_versions, self.workspace_id),
                *([documents.c.document_type.in_(command.types)] if command.types else []))).mappings().all()
        retained = []
        for row in rows:
            applies = [a for a in row["applicability"] if a["sku"] == command.sku]
            if not applies or not all(any(a["section_id"] in {"document", p["section"]} and (
                    p["page"] is None or a["page_start"] is not None and a["page_start"] <= p["page"] <= a["page_end"])
                    for a in applies) for p in row["locations"]):
                continue
            retained.append(dict(row))
        return retained

    def search(self, command):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)
        with self.engine.connect() as conn:
            current = head(conn, self.workspace_id)
            if (command.expected_release_epoch is not None and command.expected_release_epoch != current["epoch"]
                    or command.release_id is not None and command.release_id != current["release_id"]):
                return self._reply("stale_release", current)
            rows = self._candidates(conn, current, command)
            if rows is None:
                return self._reply("scope_unavailable", current)
            if not rows:
                return self._reply("empty", current)
            try:
                for identity in {r["build_id"] for r in rows}:
                    eligible(conn, self.store, self.workspace_id, build_row(conn, self.workspace_id, identity))
                profile = load_profile(conn, self.workspace_id, current["profile_id"])
            except ServiceError as error:
                return self._reply("incomplete_source", current, diagnostics=[{"code": error.code}])
        if not self._same(current):
            return self._reply("stale_release", current)
        try:
            verify_gateway(self.gateway, profile)
            output = self.gateway.embed(profile, [command.query], current=lambda: self._same(current))
            vector = validate_vector(output["vectors"][0])
        except ServiceError as error:
            reason = "stale_release" if not self._same(current) else "provider_error"
            return self._reply(reason, current, diagnostics=[{"code": error.code}])
        with KnowledgeFiles(self.store, self.workspace_id) as files, self.engine.begin() as conn:
            latest = head(conn, self.workspace_id, True)
            if head_view(latest) != head_view(current):
                return self._reply("stale_release", latest)
            live = self._candidates(conn, current, command)
            parents = {r["id"]: r for r in live}
            if not parents:
                return self._reply("empty", current)
            namespace = conn.execute(sa.text("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'")).scalar_one()
            conn.execute(sa.text("SELECT set_config('search_path', current_setting('search_path') || ',' || quote_ident(:namespace), true)"), {"namespace": namespace})
            # PostgreSQL exact cosine; the bounded candidate list only sees the prefiltered parents.
            candidates = conn.execute(sa.select(index_chunks, embedding_cache.c.vector.cosine_distance(vector).label("distance"))
                .join(embedding_cache, embedding_cache.c.id == index_chunks.c.cache_id)
                .where(index_chunks.c.parent_id.in_(parents), embedding_cache.c.profile_id == current["profile_id"],
                    *scoped_where(index_chunks, self.workspace_id), *scoped_where(embedding_cache, self.workspace_id))
                .order_by("distance", index_chunks.c.id).limit(20)).mappings().all()
            evidence, seen, tokens = [], set(), 0
            for child in candidates:
                parent = parents[child["parent_id"]]
                if parent["document_id"] in seen or len(evidence) >= 5:
                    continue
                build = build_row(conn, self.workspace_id, child["build_id"])
                try:
                    doc, v, _ = eligible(conn, self.store, self.workspace_id, build)
                except ServiceError as error:
                    return self._reply("incomplete_source", current, diagnostics=[{"code": error.code}])
                if sha(parent["text"].encode()) != parent["content_sha256"]:
                    return self._reply("incomplete_source", current, diagnostics=[{"code": "parent_integrity_error"}])
                count = proxy_tokens(parent["text"])
                if tokens + count > 4500:
                    continue
                evidence.append(register_reference(conn, files, self.workspace_id, current, build, doc, v, parent, child, 1 - float(child["distance"])))
                tokens += count
                seen.add(doc["id"])
            return self._reply("ok" if evidence else "empty", current, len(candidates), evidence,
                {"provider": output.get("usage"), "request_id": output.get("request_id"), "context_proxy_tokens": tokens, "estimator": "ascii1_nonascii2/1"})
