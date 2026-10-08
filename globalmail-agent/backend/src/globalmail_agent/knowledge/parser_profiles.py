"""Fixed local parser profiles; configuration paths never enter public output."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
PARSER_ROOT = ROOT / "globalmail-agent/parser-worker"
PROFILE_IDS = ("markdown", "policy", "mineru_basic", "mineru_standard")


def parser_python():
    default = PARSER_ROOT / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
    return Path(os.environ.get("GLOBALMAIL_PARSER_PYTHON", str(default)))


def model_home():
    existing = ROOT / "tmp/knowledge-spike/mineru-home"
    default = existing if existing.is_dir() else ROOT / ".local-data/parser-models"
    return Path(os.environ.get("GLOBALMAIL_PARSER_HOME", str(default)))


def fingerprint(profile_id):
    if profile_id not in PROFILE_IDS:
        raise ValueError("unsupported_parser_profile")
    manifest = PARSER_ROOT / "model-assets.json"
    sources = [*sorted(PARSER_ROOT.glob("*.py")), Path(__file__).parent / "parser_contract.py",
               Path(__file__).parent / "policy_bundle.py", Path(__file__).parent / "json_structure.py"]
    content = {"id": profile_id, "contract": "globalmail.parser/1", "adapter": "1.0.0",
               "code": {path.name: hashlib.sha256(path.read_text(encoding="utf-8").replace("\r\n", "\n").encode()).hexdigest()
                        for path in sources if path.is_file()}}
    if profile_id.startswith("mineru_"):
        content.update(mineru="4.0.10", docvortex="0.5.9",
                       models=hashlib.sha256(json.dumps(json.loads(manifest.read_text(encoding="utf-8")),
                           sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                       if manifest.exists() else "missing")
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def profiles():
    labels = ("Markdown结构读取", "政策规则生成说明", "MinerU Basic", "MinerU Standard")
    manifest = json.loads((PARSER_ROOT / "model-assets.json").read_text(encoding="utf-8"))
    def available(name):
        if not name.startswith("mineru_"):
            return True
        files = [entry for entry in manifest["files"]
                 if name != "mineru_basic" or "GGUF" not in entry["path"]]
        return parser_python().is_file() and all(
            (model_home() / "models" / entry["path"]).is_file()
            and (model_home() / "models" / entry["path"]).stat().st_size == entry["bytes"] for entry in files)
    return [{"id": name, "label": label, "available": available(name),
             "config_sha256": fingerprint(name)} for name, label in zip(PROFILE_IDS, labels)]
