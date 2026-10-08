"""Create immutable knowledge versions with source, applicability and audit together."""
import json
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_schema import documents, document_versions, applicabilities, uploads, policy_bundles
from globalmail_agent.application.idempotency import prior, remember
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.knowledge.base import KnowledgeFiles, scope, scoped_where, canonical, sha, document, version, audit, ensure_slot
from globalmail_agent.knowledge.validation import inspect_content, validate_bindings
from globalmail_agent.knowledge.parser_profiles import fingerprint
from globalmail_agent.knowledge.policy_bundle import parse_policy


class DocumentService:
    def __init__(self, engine, store, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.workspace_id = engine, store, workspace_id

    def available(self):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)

    def upload(self, filename, content, key, expected_version=0):
        self.available()
        if expected_version != 0:
            raise ServiceError("stale_version")
        fmt, count = inspect_content(filename, content)
        payload = {"filename": filename, "sha256": sha(content), "size_bytes": len(content), "expected_version": 0}
        with KnowledgeFiles(self.store, self.workspace_id) as files, self.engine.begin() as conn:
            previous, digest = prior(conn, self.workspace_id, key, "knowledge-upload", payload)
            if previous is not None:
                return previous
            identity = files.put(conn, content, "user_provided_simulation_knowledge", "local_upload")
            conn.execute(sa.insert(uploads).values(id=uuid4(), **scope(self.workspace_id), object_id=identity,
                filename=filename, format=fmt, page_count=count))
            result = {"object_id": str(identity), "sha256": sha(content), "size_bytes": len(content), "format": fmt, "page_count": count}
            remember(conn, self.workspace_id, key, "knowledge-upload", digest, result)
            return result

    def create(self, command, key):
        self.available()
        if command.expected_version != 0:
            raise ServiceError("stale_version")
        payload = command.model_dump(mode="json")
        with KnowledgeFiles(self.store, self.workspace_id) as files, self.engine.begin() as conn:
            previous, digest = prior(conn, self.workspace_id, key, "knowledge-create", payload)
            if previous is not None:
                return previous
            ensure_slot(conn, self.workspace_id)
            did = uuid4()
            row = {"id": did, **scope(self.workspace_id), "title": command.title,
                "document_type": command.document_type, "brand": command.brand,
                "source_kind": "user_provided_simulation_knowledge", "source_reference": command.source_reference,
                "allowed_modes": ["simulation"], "usage_split": "rag", "row_version": 1, "document_fence": 1}
            conn.execute(sa.insert(documents).values(**row))
            vid = self._version(conn, files, row, command, command.available_at)
            result = {"document_id": str(did), "version_id": str(vid), "version": 1}
            remember(conn, self.workspace_id, key, "knowledge-create", digest, result)
            return result

    def revise(self, did, command, key):
        self.available()
        operation = "knowledge-version:" + str(did)
        with KnowledgeFiles(self.store, self.workspace_id) as files, self.engine.begin() as conn:
            previous, digest = prior(conn, self.workspace_id, key, operation, command.model_dump(mode="json"))
            if previous is not None:
                return previous
            # Knowledge slot is always acquired before document/version to fence a running parser.
            from globalmail_agent.worker.leases import slot_for_update
            slot_for_update(conn, self.workspace_id, "knowledge")
            row = document(conn, self.workspace_id, did, command.expected_version, True)
            old = version(conn, self.workspace_id, row["current_version_id"])
            from globalmail_agent.knowledge.queue import invalidate_document_jobs
            invalidate_document_jobs(conn, self.workspace_id, row)
            row["document_fence"] += 1
            vid = self._version(conn, files, row, command, old["available_at"], old)
            result = {"document_id": str(did), "version_id": str(vid), "version": row["row_version"] + 1}
            remember(conn, self.workspace_id, key, operation, digest, result)
            return result

    def _source(self, conn, files, row, command, old):
        if command.content is None and command.object_id is None:
            if old is None:
                raise ServiceError("source_required", 422)
            content, obj = files.read(conn, old["object_id"])
            return old["object_id"], content, old["format"], old["page_count"]
        expected = "pdf" if row["document_type"] == "manual_pdf" else "json" if row["document_type"] == "policy_json" else "md"
        if command.object_id:
            upload = conn.execute(sa.select(uploads).where(uploads.c.object_id == command.object_id,
                *scoped_where(uploads, self.workspace_id))).mappings().first()
            if not upload or upload["format"] not in ({"md", "json", "jsonl"} if expected == "md" else {expected}):
                raise ServiceError("source_format_mismatch", 422)
            content, obj = files.read(conn, command.object_id)
            fmt, pages = inspect_content("source." + upload["format"], content)
            if expected == "md" and fmt in {"json", "jsonl"}:
                from globalmail_agent.knowledge.json_structure import validate_knowledge_structure
                if validate_knowledge_structure(content, fmt)["document_type"] != row["document_type"]:
                    raise ServiceError("source_format_mismatch", 422)
            return command.object_id, content, fmt, pages
        if expected == "pdf" or expected == "md" and not isinstance(command.content, str):
            raise ServiceError("source_format_mismatch", 422)
        content = canonical(command.content) if isinstance(command.content, dict) else command.content.encode("utf-8")
        fmt, pages = inspect_content("source." + expected, content)
        identity = files.put(conn, content, row["source_kind"], str(row["id"]))
        return identity, content, fmt, pages

    def _version(self, conn, files, row, command, available_at, old=None, page_range=None, manifest_sha=None):
        identity, content, fmt, pages = self._source(conn, files, row, command, old)
        source_changed = old is not None and sha(content) != old["source_sha256"]
        range_value = page_range or command.page_range or (
            old["page_range"] if old and not source_changed else [1, pages] if pages else None)
        if (command.page_range and fmt != "pdf" or range_value and (
                not pages or not 1 <= range_value[0] <= range_value[1] <= pages)):
            raise ServiceError("invalid_page_scope", 422)
        if (old and not source_changed and row.get("prepared_id") and range_value
                and not old["page_range"][0] <= range_value[0] <= range_value[1] <= old["page_range"][1]):
            raise ServiceError("invalid_page_scope", 422)
        bindings = [binding.model_dump() for binding in command.applicabilities]
        validate_bindings(bindings, row["brand"], range_value)
        policy = row["document_type"] == "policy_json"
        profile = command.parser_profile_id or ("mineru_basic" if fmt == "pdf" else "policy" if policy else "markdown")
        if (fmt == "pdf" and not profile.startswith("mineru_") or fmt == "md" and profile != "markdown"
                or policy and profile != "policy" or not policy and fmt != "pdf" and profile != "markdown"):
            raise ServiceError("parser_format_mismatch", 422)
        vid = uuid4()
        number = old["number"] + 1 if old else 1
        title = command.title or row["title"]
        conn.execute(sa.insert(document_versions).values(id=vid, **scope(self.workspace_id), document_id=row["id"],
            number=number, title=title, object_id=identity, format=fmt, source_sha256=sha(content), page_count=pages,
            source_manifest_sha256=manifest_sha or (old["source_manifest_sha256"] if old and not source_changed else None),
            page_range=range_value, available_at=available_at, parser_profile_id=profile, parser_fingerprint=fingerprint(profile),
            applicability_sha256=sha(canonical({"bindings": sorted(bindings, key=lambda b: (b["section_id"], b["sku"])), "page_range": range_value}))))
        for binding in bindings:
            conn.execute(sa.insert(applicabilities).values(id=uuid4(), **scope(self.workspace_id), version_id=vid, **binding))
        if policy:
            values = parse_policy(content)
            conn.execute(sa.insert(policy_bundles).values(id=uuid4(), **scope(self.workspace_id), version_id=vid, **values))
        conn.execute(documents.update().where(documents.c.id == row["id"]).values(current_version_id=vid,
            title=title, row_version=row["row_version"] + (1 if old else 0), document_fence=row["document_fence"], updated_at=sa.func.now()))
        audit(conn, self.workspace_id, row["id"], vid, "version.created", {"number": number, "source_sha256": sha(content)})
        return vid
