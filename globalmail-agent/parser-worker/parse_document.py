"""Local-only parser entry. All paths are allocated by the parent worker."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "globalmail-agent/backend/src"))
from globalmail_agent.knowledge.parser_contract import ParserAsset, ParserResult
from globalmail_agent.knowledge.parser_profiles import fingerprint
from markdown_structure import markdown_blocks, missing_images


def parse_document(source, directory, profile):
    content = source.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    adapter_fingerprint = fingerprint(profile)
    directory.mkdir(parents=True, exist_ok=True)
    if profile in {"markdown", "policy"}:
        text = content.decode("utf-8-sig")
        raw = {"format": "markdown", "content": text}
        if profile == "policy":
            from globalmail_agent.knowledge.policy_bundle import parse_policy
            raw = parse_policy(content)
            text = raw["description"]
        if profile == "markdown" and source.suffix in {".json", ".jsonl"}:
            from globalmail_agent.knowledge.json_structure import validate_knowledge_structure
            from globalmail_agent.knowledge.parser_contract import ParserBlock
            structured = validate_knowledge_structure(content, source.suffix[1:])
            raw = {"format": source.suffix[1:], "content": text, "structure": structured}
            blocks = [ParserBlock(**block) for block in structured["blocks"]]
            diagnostics = missing_images(blocks)
        else:
            blocks, diagnostics = markdown_blocks(text)
        result = ParserResult(source_sha256=digest, full_document=True, page_count=0,
            raw_document=raw, blocks=blocks, diagnostics=diagnostics,
            parser_versions={"markdown_structure": "1.0.0", **(
                {"policy_generator": raw["generator_version"]} if profile == "policy" else {})})
    else:
        from pypdf import PdfReader
        reader = PdfReader(source)
        if reader.is_encrypted or not 0 < len(reader.pages) <= 300:
            raise ValueError("invalid_pdf_pages")
        from mineru.parser import parse
        from mineru_structure import project
        from pdf_assets import render_assets
        from model_integrity import verify_models, manifest_digest
        if importlib.metadata.version("mineru") != "4.0.10":
            raise ValueError("unsupported_mineru_version")
        verify_models(profile)
        raw = parse(str(source), tier=profile.split("_", 1)[1], ocr_mode="auto").to_dict()
        blocks, diagnostics, full = project(raw, len(reader.pages))
        assets, image_diagnostics = render_assets(source, directory, blocks)
        result = ParserResult(source_sha256=digest, full_document=full, page_count=len(reader.pages),
            raw_document=raw, blocks=blocks, assets=assets, diagnostics=diagnostics + image_diagnostics,
            parser_versions={name: importlib.metadata.version(name)
                             for name in ("mineru", "docvortex", "pypdf", "pypdfium2")},
            model_versions={"manifest_sha256": manifest_digest()})
    raw_path = directory / "raw.json"
    if fingerprint(profile) != adapter_fingerprint:
        raise ValueError("parser_configuration_changed")
    result.parser_versions["adapter_fingerprint"] = adapter_fingerprint
    raw_path.write_text(json.dumps(result.raw_document, ensure_ascii=False), encoding="utf-8")
    result.assets.append(ParserAsset(id="raw", relative_path="raw.json", media_type="application/json",
                                    kind="raw", sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest()))
    (directory / "result.json").write_text(result.model_dump_json(), encoding="utf-8")
    print(json.dumps({"status": "parsed", "pages": result.page_count, "blocks": len(result.blocks)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=("markdown", "policy", "mineru_basic", "mineru_standard"), required=True)
    arguments = parser.parse_args()
    try:
        parse_document(arguments.input, arguments.output, arguments.profile)
    except Exception as error:
        code = getattr(error, "code", str(error))
        if code in {"local_model_missing", "local_model_mismatch", "unsupported_mineru_version", "invalid_knowledge_schema", "invalid_pdf_pages", "parser_configuration_changed"}:
            (arguments.output / "error.json").write_text(json.dumps({"code": code}), encoding="utf-8")
        raise
