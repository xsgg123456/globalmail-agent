"""Only provider credentials reach the bounded, owned Embedding child."""
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.parser_process import stop_tree

CHILD = Path(__file__).with_name("embedding_child.py")
SAFE_ERRORS = {"embedding_provider_error", "embedding_output_invalid", "embedding_unavailable"}


def child_environment(base_url, api_key):
    keys = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA")
    environment = {key: os.environ[key] for key in keys if key in os.environ}
    environment.update(PYTHONUTF8="1", GLOBALMAIL_EMBEDDING_BASE_URL=base_url,
                       GLOBALMAIL_EMBEDDING_API_KEY=api_key)
    return environment


def run_embedding_child(command, directory, environment, current, stopped, *, timeout=45, heartbeat_interval=15):
    if stopped() or not current():
        raise ServiceError("embedding_cancelled", 409)
    options = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
               if os.name == "nt" else {"start_new_session": True})
    started = checked = time.monotonic()
    process = subprocess.Popen(command, cwd=directory, env=environment,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
    try:
        while process.poll() is None:
            if stopped():
                raise ServiceError("embedding_cancelled", 409)
            now = time.monotonic()
            if now - started >= timeout:
                raise ServiceError("embedding_timeout", 503)
            if now - checked >= heartbeat_interval:
                if not current():
                    raise ServiceError("embedding_cancelled", 409)
                checked = now
            time.sleep(0.05)
        if stopped() or not current():
            raise ServiceError("embedding_cancelled", 409)
        result_path = directory / "result.json"
        if not result_path.is_file() or result_path.stat().st_size > 4 * 1024 * 1024:
            raise ServiceError("embedding_output_invalid", 503)
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ServiceError("embedding_output_invalid", 503) from None
        if not isinstance(result, dict):
            raise ServiceError("embedding_output_invalid", 503)
        if process.returncode or result.get("error"):
            code = result.get("error")
            raise ServiceError(code if code in SAFE_ERRORS else "embedding_provider_error", 503)
        return result
    finally:
        stop_tree(process)


def embed_child(base_url, api_key, model, texts, current, stopped):
    with TemporaryDirectory(prefix="globalmail_embedding_") as temporary:
        directory = Path(temporary)
        request = directory / "request.json"
        request.write_text(json.dumps({"model": model, "texts": texts, "dimensions": 1024}, ensure_ascii=False),
                           encoding="utf-8")
        return run_embedding_child([sys.executable, str(CHILD), str(request)], directory,
            child_environment(base_url, api_key), current, stopped)
