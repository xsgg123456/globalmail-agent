"""Verify the locked local weights before invoking an SDK that can download models."""
import hashlib
import json
import os
from pathlib import Path

MANIFEST = Path(__file__).parent / "model-assets.json"


def manifest_digest():
    return hashlib.sha256(json.dumps(json.loads(MANIFEST.read_text(encoding="utf-8")),
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_models(profile):
    root = (Path(os.environ["MINERU_HOME"]) / "models").resolve()
    for entry in json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]:
        if profile == "mineru_basic" and "GGUF" in entry["path"]:
            continue
        target = (root / entry["path"]).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError("local_model_missing")
        if target.stat().st_size != entry["bytes"]:
            raise ValueError("local_model_mismatch")
        with target.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != entry["sha256"]:
            raise ValueError("local_model_mismatch")
