"""Disposable real API + Vite for browser QA; isolated schema and object root."""
import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "globalmail-agent/backend"
FRONTEND = ROOT / "globalmail-agent/frontend"
sys.path.insert(0, str(BACKEND / "src"))


def ready(url):
    try:
        with urlopen(url, timeout=2) as result:
            return result.status == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-port", type=int, default=18181)
    parser.add_argument("--web-port", type=int, default=15174)
    args = parser.parse_args()
    stop_file = ROOT / "tmp/phase3-browser.stop"
    stop_file.unlink(missing_ok=True)
    for port in (args.api_port, args.web_port):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", port))
    url = os.environ.get("GLOBALMAIL_TEST_DATABASE_URL")
    if not url:
        raise RuntimeError("requires GLOBALMAIL_TEST_DATABASE_URL")
    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config
    schema = "phase3_browser_" + uuid4().hex
    admin = sa.create_engine(url, hide_parameters=True)
    processes, outputs = [], []
    temporary_directory = tempfile.TemporaryDirectory(prefix="globalmail_phase3_browser_")
    with admin.begin() as connection:
        connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    try:
        with nullcontext(temporary_directory.name) as temporary:
            engine = sa.create_engine(url, hide_parameters=True,
                                     connect_args={"options": f"-csearch_path={schema}"})
            try:
                config = Config(str(BACKEND / "alembic.ini"))
                with engine.begin() as connection:
                    config.attributes["connection"] = connection
                    command.upgrade(config, "head")
            finally:
                engine.dispose()
            # The URL carries only the schema option to its private child environment.
            test_url = sa.engine.make_url(url).update_query_dict({"options": f"-csearch_path={schema}"})
            environment = dict(os.environ)
            environment.update(GLOBALMAIL_DATABASE_URL=test_url.render_as_string(hide_password=False),
                GLOBALMAIL_OBJECT_ROOT=str(Path(temporary) / "objects"),
                GLOBALMAIL_ALLOWED_ORIGINS=f"http://127.0.0.1:{args.web_port}",
                PYTHONPATH=str(BACKEND / "src"))
            api_log = open(Path(temporary) / "api.log", "wb")
            outputs.append(api_log)
            processes.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "--app-dir", "src",
                "globalmail_agent.main:app", "--host", "127.0.0.1", "--port", str(args.api_port),
                "--no-access-log"], cwd=BACKEND, env=environment, stdout=api_log, stderr=api_log,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW))
            for name in list(environment):
                if name.startswith(("GLOBALMAIL_", "LLM_")):
                    environment.pop(name)
            environment.update(VITE_PORT=str(args.web_port),
                               VITE_API_PROXY_URL=f"http://127.0.0.1:{args.api_port}")
            web_log = open(Path(temporary) / "web.log", "wb")
            outputs.append(web_log)
            processes.append(subprocess.Popen([shutil.which("node"),
                str(FRONTEND / "node_modules/vite/bin/vite.js"), "--host", "127.0.0.1",
                "--port", str(args.web_port), "--strictPort"], cwd=FRONTEND, env=environment,
                stdout=web_log, stderr=web_log,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW))
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if any(process.poll() is not None for process in processes):
                    raise RuntimeError("isolated_test_server_failed; private log retained only during run")
                if (ready(f"http://127.0.0.1:{args.api_port}/api/v1/health/ready")
                        and ready(f"http://127.0.0.1:{args.web_port}")):
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError("isolated_test_server_not_ready")
            print(json.dumps({"status": "ready", "web": f"http://127.0.0.1:{args.web_port}/#/workbench",
                              "api": f"http://127.0.0.1:{args.api_port}", "schema": schema}), flush=True)
            try:
                print("Stop by creating tmp/phase3-browser.stop.", flush=True)
                while not stop_file.exists():
                    time.sleep(0.2)
            except (KeyboardInterrupt, EOFError):
                pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for output in outputs:
            output.close()
        with admin.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
        temporary_directory.cleanup()
        stop_file.unlink(missing_ok=True)
        print("Isolated processes/schema/object directory cleaned.", flush=True)


if __name__ == "__main__":
    main()
