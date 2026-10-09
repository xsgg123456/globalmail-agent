"""Fixed backend runtime imports; provider settings remain server-side and private."""
import hashlib
import ast
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BACKEND = HERE.parent / "backend"
for path in (BACKEND / "src", BACKEND / "tests", HERE.parent / "knowledge-eval"):
    sys.path.insert(0, str(path))
from provider_config import configured_settings, isolated_database_environment


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def provider_sampling():
    """Inspect only literal sampling options; never load or export provider credentials."""
    path = BACKEND / "src/globalmail_agent/adapters/model_provider.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    validation = next(ast.literal_eval(node.value) for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
            and target.id == "VALIDATION_OPTIONS" for target in node.targets))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "options" for target in node.targets):
            if not isinstance(node.value, ast.Dict):
                break
            entries = {key.value: value for key, value in zip(node.value.keys, node.value.values)
                if isinstance(key, ast.Constant) and isinstance(key.value, str)}
            try:
                extra = ast.literal_eval(entries["extra_body"])
                return {"temperature": ast.literal_eval(entries["temperature"]),
                    "enable_thinking": extra["enable_thinking"],
                    "top_p": ast.literal_eval(entries["top_p"]) if "top_p" in entries else "server_default",
                    "validation_profile": {"temperature": ast.literal_eval(entries["temperature"]),
                        **validation["extra_body"], "max_completion_tokens": validation["max_completion_tokens"],
                        "top_p": "server_default"}}
            except (ValueError, KeyError):
                break
    raise RuntimeError("provider_sampling_not_literal_no_paid_calls")


def provider_tool_choice_strategy():
    """Read only the local choice expression, never client/configuration values."""
    path = BACKEND / "src/globalmail_agent/adapters/model_provider.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.IfExp) and any(
                isinstance(target, ast.Name) and target.id == "choice" for target in node.targets):
            expression = ast.unparse(node.value)
            if isinstance(node.value.orelse, ast.Constant) and node.value.orelse.value == "auto" and (
                    "len(tools) == 1" in expression and "'function'" in expression):
                return {"single_tool": "named_declared_function", "multiple_tools": "auto",
                    "basis": "local_provider_source_expression_and_separate_actual_SDK_payload_capture",
                    "source_expression": expression}
    raise RuntimeError("provider_tool_choice_strategy_unrecognized_no_paid_calls")


def cleanup_verified(fixture):
    import sqlalchemy as sa
    checks = {"callbacks_passed": fixture.doCleanups(), "schema_removed": False,
        "temporary_objects_removed": not hasattr(fixture, "temp") or not Path(fixture.temp.name).exists()}
    if hasattr(fixture, "schema") and hasattr(fixture, "admin"):
        try:
            with fixture.admin.connect() as conn:
                checks["schema_removed"] = not conn.execute(sa.text(
                    "SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = :owned_schema)"),
                    {"owned_schema": fixture.schema}).scalar_one()
        except Exception as error:
            checks["verification_error_type"] = type(error).__name__
        finally:
            fixture.admin.dispose()
    return checks


def frozen_inputs():
    frozen = json.loads((HERE / "freeze.json").read_text(encoding="utf-8"))
    for relative, expected in frozen["files"].items():
        actual = digest((ROOT / relative).read_bytes())
        if expected != actual:
            raise RuntimeError("frozen_input_changed:" + relative)
    return json.loads((HERE / "cases.json").read_text(encoding="utf-8")), frozen


def prepare(fixture, settings, cases):
    """Use real upload/parse/review/build/publish on one unchanged approved text SOP."""
    from uuid import UUID, uuid4
    from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
    from globalmail_agent.knowledge.commands import CreateDocument, ParseCommand, ReviewCommand
    from globalmail_agent.knowledge.index_commands import BuildCommand, ReleaseCommand
    from globalmail_agent.knowledge.builds import BuildService
    from globalmail_agent.knowledge.releases import ReleaseService
    from globalmail_agent.knowledge.embedding import EmbeddingGateway
    from globalmail_agent.worker.knowledge_runner import KnowledgeRunner
    source_root = ROOT / "data/knowledge/v1"
    docs = json.loads((source_root / "documents.json").read_text(encoding="utf-8"))
    bindings = json.loads((source_root / "knowledge-bindings.json").read_text(encoding="utf-8"))
    embedding = EmbeddingGateway(settings)
    runner = KnowledgeRunner(fixture.engine, fixture.store, DEFAULT_WORKSPACE_ID, embedding)
    builds = BuildService(fixture.engine, fixture.store, embedding)
    build_ids, audit = [], []
    for identity in cases["knowledge"]:
        row = next(d for d in docs if d["document_id"] == identity)
        raw = (source_root / row["path"]).read_bytes()
        if digest(raw) != row["source_hash"]:
            raise RuntimeError("sop_source_mismatch")
        uploaded = fixture.docs.upload(Path(row["path"]).name, raw, uuid4().hex)
        applicable = [{"section_id": "document" if b["section_id"] == "all" else b["section_id"],
            "sku": sku, "basis": b["basis"]} for b in bindings if b["document_id"] == identity for sku in b["skus"]]
        created = fixture.docs.create(CreateDocument(expected_version=0, title=row["title"],
            document_type=row["document_type"], brand=row["brand"], source_reference=identity,
            available_at=row["available_at"], object_id=UUID(uploaded["object_id"]), applicabilities=applicable), uuid4().hex)
        vid = UUID(created["version_id"])
        v = fixture.queries.version_detail(vid)["version"]
        fixture.knowledge.enqueue(vid, ParseCommand(expected_version=v["row_version"], parser_profile_id="markdown"), uuid4().hex)
        job = runner.jobs.claim(runner.owner)
        if not job:
            raise RuntimeError("knowledge_parse_not_claimed")
        runner.execute(job)
        v = fixture.queries.version_detail(vid)["version"]
        if v["status"] != "needs_review":
            raise RuntimeError("knowledge_parse_failed")
        fixture.reviews.review(vid, ReviewCommand.model_validate({**fixture.review_payload(vid),
            "note": "隔离Phase7文本验收初始化：沿用Phase5/6固定SOP原文和原模拟适用范围，逐块核对；非正式知识发布批准。"}), uuid4().hex)
        v = fixture.queries.version_detail(vid)["version"]
        build = builds.enqueue_build(vid, BuildCommand(expected_version=v["row_version"],
            embedding_profile_key="qwen3.7-text-embedding", chunking_profile_key="structure_v1_500"), uuid4().hex)
        job = runner.jobs.claim(runner.owner)
        if not job:
            raise RuntimeError("knowledge_build_not_claimed")
        runner.execute(job)
        state = builds.status(vid)["builds"][0]
        if state["status"] != "ready" or not state["eligible"]:
            raise RuntimeError("knowledge_build_failed")
        build_ids.append(UUID(build["build_id"]))
        audit.append({"prepared_id": identity, "source_sha256": digest(raw), "available_at": row["available_at"],
            "actual_source_kind": "user_provided_simulation_knowledge", "applicable_skus": sorted({a["sku"] for a in applicable}),
            "build": state})
    release = ReleaseService(fixture.engine, fixture.store).publish(
        ReleaseCommand(expected_release_epoch=0, build_ids=build_ids), uuid4().hex)
    return embedding, {"documents": audit, "release": release["head"]}
