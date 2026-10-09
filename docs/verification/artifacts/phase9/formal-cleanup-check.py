"""Read-only formal preservation and owned Phase 9 server cleanup verification."""
import importlib.util
import json
from pathlib import Path
import socket
import sqlalchemy as sa

root = Path(__file__).resolve().parents[1]
artifacts = root / 'docs/verification/artifacts/phase9'
spec = importlib.util.spec_from_file_location('preservation', root / 'globalmail-agent/scripts/verify-preservation.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
baseline_path = root / 'docs/verification/artifacts/phase7/formal-before.json'
baseline_bytes = baseline_path.read_bytes()
before = json.loads(baseline_bytes)
current = module.capture(before)
checks = {name: value == current['tables'][name] for name, value in before['tables'].items()}
private = json.loads((root / '.local-data/runtime/settings.json').read_text(encoding='utf-8-sig'))
engine = sa.create_engine(private['database_url'], hide_parameters=True)
owned = set()
for path in (root / 'tmp/phase9-browser-server.txt', artifacts / 'browser-server-before-policy-lock.txt'):
    owned.add(json.loads(path.read_text(encoding='utf-8-sig').splitlines()[0])['schema'])
assert all(s.startswith('phase9_browser_') and s.replace('_', '').isalnum() for s in owned)
try:
    with engine.connect() as conn:
        absent = {s: not conn.execute(sa.text('SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=:schema)'),
            {'schema': s}).scalar_one() for s in sorted(owned)}
        remaining = list(conn.execute(sa.text("SELECT nspname FROM pg_namespace WHERE starts_with(nspname, :prefix)"),
            {'prefix': 'phase9_browser_'}).scalars())
finally:
    engine.dispose()

def listening(port):
    with socket.socket() as sock:
        sock.settimeout(.3)
        return sock.connect_ex(('127.0.0.1', port)) == 0

report = {'scope': 'read_only_no_formal_upgrade', 'revision': current['revision'],
    'total_tables': current['table_count'], 'table_row_column_SHA_matches': checks,
    'settings_preserved': before['settings_sha256'] == current['settings_sha256'],
    'source_bytes_preserved': before['source_files'] == current['source_files'],
    'source_file_count': len(current['source_files']), 'knowledge_counts': current['knowledge_counts'],
    'formal_baseline_unchanged': baseline_path.read_bytes() == baseline_bytes,
    'owned_schemas_absent': absent,
    'remaining_phase9_browser_schemas': remaining,
    'owned_object_directories_absent': not list((root / 'tmp').glob('globalmail_phase9_browser_*')),
    'test_ports_closed': {str(p): not listening(p) for p in (15174, 18181)},
    'formal_upgrade_executed': False}
assert current['revision'] == before['revision'] == '0005_knowledge_index'
assert current['table_count'] == before['table_count'] == 54
assert all(checks.values()) and report['settings_preserved'] and report['source_bytes_preserved']
assert report['formal_baseline_unchanged'] and all(absent.values())
assert not remaining
assert report['owned_object_directories_absent'] and all(report['test_ports_closed'].values())
(artifacts / 'formal-readonly-and-cleanup.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'table_row_column_SHA_matches'}))
