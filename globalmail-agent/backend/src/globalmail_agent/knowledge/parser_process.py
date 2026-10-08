"""Own a bounded local parser child; secrets never enter its environment."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from globalmail_agent.knowledge.parser_contract import ParserResult
from globalmail_agent.knowledge.parser_profiles import PARSER_ROOT, model_home, parser_python, profiles


class ParserStopped(Exception):
    pass


class ParserFailure(Exception):
    def __init__(self, code, retryable=False):
        self.code, self.retryable = code, retryable


def child_environment():
    keys = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA")
    environment = {key: os.environ[key] for key in keys if key in os.environ}
    environment.update(PYTHONUTF8="1", MINERU_HOME=str(model_home()), MINERU_MODEL_SOURCE="modelscope",
                       HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1", OMP_NUM_THREADS="2")
    return environment


def stop_tree(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_child(command, directory, should_continue, *, timeout=900, heartbeat_interval=15, stopped=lambda: False):
    options = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
               if os.name == "nt" else {"start_new_session": True})
    started, last_heartbeat = time.monotonic(), time.monotonic()
    with open(directory / "parser.log", "wb") as output:
        process = subprocess.Popen(command, cwd=PARSER_ROOT, env=child_environment(),
                                   stdout=output, stderr=output, **options)
        try:
            while process.poll() is None:
                if stopped():
                    raise ParserStopped()
                elapsed = time.monotonic() - started
                if elapsed >= timeout:
                    raise ParserFailure("parser_timeout", True)
                if time.monotonic() - last_heartbeat >= heartbeat_interval:
                    if not should_continue():
                        raise ParserStopped()
                    last_heartbeat = time.monotonic()
                time.sleep(0.1)
            if not should_continue():
                raise ParserStopped()
            if process.returncode:
                error_file = directory / "error.json"
                if error_file.is_file():
                    try:
                        code = json.loads(error_file.read_text(encoding="utf-8"))["code"]
                        if code in {"local_model_missing", "local_model_mismatch", "unsupported_mineru_version", "invalid_knowledge_schema", "invalid_pdf_pages", "parser_configuration_changed"}:
                            raise ParserFailure(code)
                    except (ValueError, KeyError, TypeError):
                        pass
                raise ParserFailure("parser_failed", True)
        finally:
            stop_tree(process)


def parse_bytes(content, source_format, profile_id, directory, should_continue, *, timeout=900, stopped=lambda: False):
    if profile_id not in {"markdown", "policy", "mineru_basic", "mineru_standard"}:
        raise ParserFailure("unsupported_parser_profile")
    if profile_id.startswith("mineru_") and not next(p["available"] for p in profiles() if p["id"] == profile_id):
        raise ParserFailure("parser_unavailable")
    suffix = {"pdf": "pdf", "md": "md", "markdown": "md", "json": "json", "jsonl": "jsonl"}.get(source_format)
    if suffix is None:
        raise ParserFailure("unsupported_source_format")
    source = directory / ("source." + suffix)
    source.write_bytes(content)
    executable = str(parser_python()) if profile_id.startswith("mineru_") else sys.executable
    command = [executable, str(PARSER_ROOT / "parse_document.py"), "--input", str(source),
               "--output", str(directory), "--profile", profile_id]
    if not should_continue():
        raise ParserStopped()
    run_child(command, directory, should_continue, timeout=timeout, stopped=stopped)
    try:
        result = ParserResult.model_validate(json.loads((directory / "result.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        raise ParserFailure("parser_output_invalid") from None
    import hashlib
    if result.source_sha256 != hashlib.sha256(content).hexdigest():
        raise ParserFailure("parser_source_mismatch")
    return result
