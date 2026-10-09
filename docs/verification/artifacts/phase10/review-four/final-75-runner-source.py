import hashlib
import json
from pathlib import Path
import sys
import time
import unittest

root = Path(__file__).resolve().parents[1]
backend = root / 'globalmail-agent/backend'
sys.path[:0] = [str(backend / 'src'), str(backend / 'tests'), str(root / 'globalmail-agent/agent-eval')]
from bootstrap import isolated_database_environment

def snapshot():
    paths = [backend / 'pyproject.toml', backend / 'uv.lock']
    for folder in ('src', 'tests', 'migrations'):
        paths.extend(p for p in (backend / folder).rglob('*') if p.is_file() and p.suffix in ('.py', '.md'))
    return {str(p.relative_to(root)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

before = snapshot()
isolated_database_environment()
suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:]) if sys.argv[1:] else unittest.defaultTestLoader.discover(str(backend / 'tests'))
start = time.monotonic()
result = unittest.TextTestRunner(verbosity=2).run(suite)
after = snapshot()
report = {'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'skipped': len(result.skipped), 'successful': result.wasSuccessful(), 'duration_seconds': time.monotonic() - start,
    'source_changed': before != after, 'before': before, 'after': after}
output = root / 'docs/verification/artifacts/phase10/review-four'
output.mkdir(parents=True, exist_ok=True)
name = 'independent-tests-final-75.json' if sys.argv[1:] else 'backend-tests.json'
(output / name).write_text(json.dumps(report, indent=2), encoding='utf-8')
raise SystemExit(not result.wasSuccessful() or bool(result.skipped) or (not sys.argv[1:] and before != after))





