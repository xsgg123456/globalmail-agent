"""Read-only diff inventory, line counts, risky pattern locations and hashes."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(["git", "diff", "--name-only", "09a818f"], cwd=root, text=True).splitlines()
paths += subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, text=True).splitlines()
paths = sorted({p for p in paths if p.startswith("globalmail-agent/")
    and any(part in p for part in ("/src/", "/tests/", "/migrations/", "/scripts/"))
    and Path(p).suffix in (".py", ".ts", ".vue", ".md") and not p.endswith("components.d.ts")})
patterns = {
    "dangerous_execution": r"\beval\s*\(|\bexec\s*\(|shell\s*=\s*True|\bpickle\.loads\s*\(",
    "raw_html": r"dangerouslySetInnerHTML|\binnerHTML\s*=|v-html\s*=",
    "frontend_secret": r"VITE_[A-Z_]*(?:KEY|SECRET|TOKEN)",
    "credential_literal": r"(?:password|api_key|secret)\s*=\s*['\"][^'\"]{12,}|sk-(?:ant|proj)-[A-Za-z0-9_-]+",
    "absolute_user_path": r"/Users/|[CD]:[\\/](?:Users|Work_Project)",
    "sql_interpolation": r"(?:text|execute)\s*\(\s*f['\"]",
}
rows, hits = [], []
for path in paths:
    data = (root / path).read_bytes()
    lines = data.decode("utf-8-sig").splitlines()
    rows.append({"file": path, "lines": len(lines), "sha256": hashlib.sha256(data).hexdigest()})
    for line_no, line in enumerate(lines, 1):
        for name, pattern in patterns.items():
            if re.search(pattern, line):
                hits.append({"file": path, "line": line_no, "category": name})
        if Path(path).suffix in (".ts", ".vue") and re.search(r"\bany\b", line):
            hits.append({"file": path, "line": line_no, "category": "ts_any"})
summary = {"base": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
    "files": len(rows), "max_lines": max(r["lines"] for r in rows),
    "over_300": [r for r in rows if r["lines"] > 300], "hits": hits, "inventory": rows}
(root / "tmp/phase8-review6-audit.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in summary.items() if k != "inventory"}))
