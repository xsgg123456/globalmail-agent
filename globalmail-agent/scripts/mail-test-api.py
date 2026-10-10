"""Thin test API client; accepts only a live isolated-server session manifest."""
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4


def session_urls(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not re.fullmatch(r"phase(?:[3-9]|10|11|16)_browser_[0-9a-f]{32}", value["schema"]):
        raise ValueError("isolated_session_required")
    urls = [urlsplit(value[key]) for key in ("api", "web")]
    if any(url.scheme != "http" or url.hostname != "127.0.0.1" or not url.port
           or url.username or url.password or url.query for url in urls):
        raise ValueError("local_session_required")
    return value["api"].rstrip("/"), f"http://127.0.0.1:{urls[1].port}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("scenarios")
    for name in ("create", "show", "incoming", "replay-next", "facts"):
        command = commands.add_parser(name)
        command.add_argument("id")
        if name != "show":
            command.add_argument("--key", default=None)
        if name == "incoming":
            command.add_argument("--body-file", type=Path, required=True)
            command.add_argument("--subject", default="")
        if name in ("incoming", "replay-next"):
            command.add_argument("--expected-version", type=int)
        if name == "facts":
            command.add_argument("--json-file", type=Path, required=True)
    args = parser.parse_args()
    base, origin = session_urls(args.session)

    def call(path, body=None):
        headers = {"Origin": origin}
        if body is not None:
            headers.update({"Content-Type": "application/json", "Idempotency-Key": args.key or str(uuid4())})
        request = Request(base + "/api/v1" + path, headers=headers,
                          data=None if body is None else json.dumps(body).encode("utf-8"))
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        return result["data"]

    if args.command == "scenarios":
        result = call("/business/scenarios")
    else:
        identifier = quote(args.id, safe="")
        if args.command == "create":
            result = call(f"/business/scenarios/{identifier}/conversations", {"expected_version": 0})
        elif args.command == "facts":
            result = call(f"/testing/branches/{identifier}/facts", json.loads(args.json_file.read_text(encoding="utf-8-sig")))
        else:
            current = call(f"/conversations/{identifier}")
            if args.command == "show":
                conversation = current["conversation"]
                fields = ("id", "mode", "branch_id", "row_version", "input_revision", "lifecycle",
                          "processing_owner", "auto_run_gate", "scheduling_state", "persistent_human", "human_claimed")
                result = {"conversation": {key: conversation[key] for key in fields},
                          "messages": [{"id": item["id"], "sender": item["sender"]} for item in current["messages"]],
                          "runs": [{"id": item["id"], "status": item["status"]} for item in current["runs"]]}
            else:
                version = args.expected_version if args.expected_version is not None else current["conversation"]["row_version"]
                body = {"expected_version": version}
                suffix = "replay/next"
                if args.command == "incoming":
                    suffix = "messages"
                    body.update(subject=args.subject, body=args.body_file.read_text(encoding="utf-8-sig"))
                result = call(f"/conversations/{identifier}/{suffix}", body)
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        main()
    except HTTPError as error:
        print(json.dumps({"status": "error", "http_status": error.code}), file=sys.stderr)
        sys.exit(1)
    except (OSError, URLError, ValueError, KeyError) as error:
        print(json.dumps({"status": "error", "reason": type(error).__name__}), file=sys.stderr)
        sys.exit(1)
