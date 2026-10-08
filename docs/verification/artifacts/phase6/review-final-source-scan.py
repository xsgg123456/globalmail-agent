"""Read-only changed-source audit; matches emit locations/categories, never secret bodies."""
import json
import re
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
changed = subprocess.check_output(['git', 'diff', '--name-only', 'd0833a4'], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).splitlines()
added = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
paths = sorted(set(changed + added))
patterns = {
    'typescript_any': r'\bany\b',
    'html_injection': r'v-html|innerHTML|dangerouslySetInnerHTML',
    'dynamic_eval': r'\beval\s*\(|\bexec\s*\(',
    'key_like_literal': r'sk-(?:ant-|proj-)[A-Za-z0-9_-]{12,}|(?:api_key|password)\s*=\s*[\'\"][^\'\"]{12,}',
    'frontend_secret_env': r'VITE_[A-Z_]*(?:KEY|TOKEN|SECRET)',
    'sql_text_interpolation': r'sa\.text\s*\(\s*f[\'\"]|execute\s*\(\s*f[\'\"]',
    'absolute_user_path': r'(?:/Users/|C:[/\\]Users[/\\])',
}
files, findings = [], []
for value in paths:
    path = ROOT / value
    if not path.is_file() or not value.startswith('globalmail-agent/') or path.suffix not in {'.py', '.ts', '.vue', '.ps1'}:
        continue
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    files.append({'path': value, 'lines': len(lines), 'new': value in added, 'over_300': len(lines) > 300})
    for number, line in enumerate(lines, 1):
        for label, pattern in patterns.items():
            if label == 'typescript_any' and path.suffix not in {'.ts', '.vue'}:
                continue
            if re.search(pattern, line, re.I if label == 'key_like_literal' else 0):
                findings.append({'path': value, 'line': number, 'category': label})
print(json.dumps({'changed_source_count': len(files), 'new_sources_over_300': [f for f in files if f['new'] and f['over_300']],
    'all_changed_sources_over_300': [f for f in files if f['over_300']], 'files': files, 'findings': findings}, ensure_ascii=False, indent=2))
