"""Register complete physical parser artifacts and project immutable logical page ranges."""
import json
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_schema import parse_caches, knowledge_assets, blocks, document_versions, documents, applicabilities
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.base import canonical, sha, scope, scoped_where
from globalmail_agent.knowledge.parser_contract import ParserResult


def find_cache(conn, workspace, v):
    return conn.execute(sa.select(parse_caches).where(*scoped_where(parse_caches, workspace),
        parse_caches.c.source_sha256 == v["source_sha256"], parse_caches.c.parser_profile_id == v["parser_profile_id"],
        parse_caches.c.parser_fingerprint == v["parser_fingerprint"])).mappings().first()


def asset_bytes(root, asset):
    relative = PurePosixPath(asset["relative_path"])
    if (root is None or relative.is_absolute() or ".." in relative.parts or not relative.parts
            or "\\" in asset["relative_path"] or ":" in asset["relative_path"]):
        raise ServiceError("invalid_parser_asset", 422)
    base = Path(root).resolve()
    path = base.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(base) or any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(base)):
        raise ServiceError("invalid_parser_asset", 422)
    try:
        content = path.read_bytes()
    except OSError:
        raise ServiceError("missing_parser_asset", 422) from None
    if not content or len(content) > 50 * 1024 * 1024 or asset["sha256"] and sha(content) != asset["sha256"]:
        raise ServiceError("invalid_parser_asset", 422)
    media = asset["media_type"]
    valid = (media == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n")
        or media == "image/jpeg" and content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9")
        or media == "image/webp" and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
        or media == "application/pdf" and content.startswith(b"%PDF-")
        or media == "application/json" and asset["kind"] == "raw")
    if not valid or asset["kind"] != "raw" and not media.startswith("image/"):
        raise ServiceError("invalid_parser_asset", 422)
    if media == "application/json":
        try:
            json.loads(content)
        except (ValueError, UnicodeError):
            raise ServiceError("invalid_parser_asset", 422) from None
    return content


def save_cache(conn, files, workspace, v, result, artifact_dir):
    existing = find_cache(conn, workspace, v)
    if existing:
        return dict(existing)
    normalized = ParserResult.model_validate(result).model_dump(mode="json")
    if normalized["source_sha256"] != v["source_sha256"]:
        raise ServiceError("parser_source_mismatch", 422)
    if v["format"] == "pdf" and normalized["page_count"] != v["page_count"]:
        raise ServiceError("parser_page_mismatch", 422)
    identity, asset_map = uuid4(), {}
    entries = []
    for asset in normalized["assets"]:
        content = asset_bytes(artifact_dir, asset)
        object_id = files.put(conn, content, "knowledge_parser_asset", str(identity), (v["object_id"],))
        asset_map[asset["id"]] = str(object_id)
        entries.append({"id": uuid4(), **scope(workspace), "cache_id": identity, "asset_key": asset["id"],
            "object_id": object_id, "media_type": asset["media_type"], "kind": asset["kind"], "page": asset["page"]})
    raw = canonical(normalized)
    result_object = files.put(conn, raw, "knowledge_full_parser_result", str(identity),
        (v["object_id"], *[UUID(value) for value in asset_map.values()]))
    values = {"id": identity, **scope(workspace), "source_sha256": v["source_sha256"],
        "parser_profile_id": v["parser_profile_id"], "parser_fingerprint": v["parser_fingerprint"],
        "result_object_id": result_object, "parse_sha256": sha(raw), "asset_map": asset_map}
    conn.execute(sa.insert(parse_caches).values(**values))
    for entry in entries:
        conn.execute(sa.insert(knowledge_assets).values(**entry))
    return values


def project(conn, files, workspace, v, cache):
    raw, registry = files.read(conn, cache["result_object_id"])
    if sha(raw) != cache["parse_sha256"]:
        raise ServiceError("cache_integrity_error", 503)
    result = ParserResult.model_validate_json(raw).model_dump(mode="json")
    if result["source_sha256"] != v["source_sha256"]:
        raise ServiceError("cache_integrity_error", 503)
    page_range = v["page_range"]
    selected = [b for b in result["blocks"] if not page_range or b["page"] is not None and page_range[0] <= b["page"] <= page_range[1]]
    doc = conn.execute(sa.select(documents).where(documents.c.id == v["document_id"], *scoped_where(documents, workspace))).mappings().one()
    if doc["prepared_id"] and v["format"] == "pdf":
        sections = conn.execute(sa.select(applicabilities.c.section_id).where(applicabilities.c.version_id == v["id"],
            *scoped_where(applicabilities, workspace)).distinct()).scalars().all()
        if len(sections) == 1:
            selected = [{**b, "source_section_id": b["section_id"], "section_id": sections[0]} for b in selected]
    diagnostics = [d for d in result["diagnostics"] if not page_range or d["page"] is None or page_range[0] <= d["page"] <= page_range[1]]
    by_id = {b["id"]: b for b in selected}
    for diagnostic in diagnostics:
        if diagnostic.get("blocks_review") and any(term in diagnostic["code"] for term in ("asset", "image", "figure")):
            sections = {by_id[key]["section_id"] for key in diagnostic["block_ids"] if key in by_id}
            if sections:
                diagnostic["block_ids"] = [b["id"] for b in selected if b["section_id"] in sections]
    if not result["full_document"]:
        diagnostics.append({"code": "incomplete_document", "severity": "error", "page": None,
            "block_ids": [], "asset_ids": [], "message": "原件存在未覆盖内容，需重新解析。", "blocks_review": True})
    if page_range:
        pages = {b["page"] for b in selected}
        for page in range(page_range[0], page_range[1] + 1):
            if page not in pages:
                diagnostics.append({"code": "missing_page", "severity": "error", "page": page,
                    "block_ids": [], "asset_ids": [], "message": "此页没有可核对的规范内容。", "blocks_review": True})
    for position, block in enumerate(selected):
        structure = {k: block[k] for k in ("bbox", "figure_id", "table_rows")}
        if "source_section_id" in block:
            structure["source_section_id"] = block["source_section_id"]
        structure["asset_ids"] = [cache["asset_map"][key] for key in block["asset_ids"]]
        conn.execute(sa.insert(blocks).values(id=uuid4(), **scope(workspace), version_id=v["id"], position=position,
            parse_generation=v["parse_generation"], block_key=block["id"], page=block["page"],
            section_id=block["section_id"], type=block["type"], text=block["text"], structure=structure))
    # Bind review to actual projected content plus physical parser digest and applicability.
    projected_digest = sha(canonical({"physical": cache["parse_sha256"], "page_range": page_range,
        "blocks": selected, "diagnostics": diagnostics}))
    conn.execute(document_versions.update().where(document_versions.c.id == v["id"]).values(cache_id=cache["id"],
        parse_sha256=projected_digest, status="needs_review", diagnostics=diagnostics, row_version=v["row_version"] + 1))
    return projected_digest
