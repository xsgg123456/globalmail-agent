"""Only file bytes; no production connection is created."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[4]
baseline = json.loads((root / 'docs/verification/artifacts/phase6/formal-before.json').read_text(encoding='utf-8'))
results = {}
for relative, digest in baseline['source_files'].items():
    path = root / relative
    results[relative] = path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest
settings = root / '.local-data/runtime/settings.json'
value = {'source_count': len(results), 'all_source_bytes_preserved': all(results.values()),
         'settings_bytes_preserved': hashlib.sha256(settings.read_bytes()).hexdigest() == baseline['settings_sha256'],
         'matches': results, 'production_database_accessed': False}
print(json.dumps(value, ensure_ascii=False, indent=2))
assert all(results.values()) and value['settings_bytes_preserved']
