import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

root = Path(__file__).resolve().parents[1]
backend = root / 'globalmail-agent/backend'
out = root / 'docs/verification/artifacts/phase9'
out.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(backend / 'src'), str(backend / 'tests'), str(root / 'globalmail-agent/agent-eval')]
from bootstrap import isolated_database_environment

def snapshot():
    paths = [backend / 'pyproject.toml', backend / 'uv.lock']
    for folder in ('src', 'tests', 'migrations'):
        paths.extend(p for p in (backend / folder).rglob('*') if p.is_file() and p.suffix in ('.py', '.md'))
    return {str(p.relative_to(root)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

if len(sys.argv) > 1:
    group, names = sys.argv[1], sys.argv[2:]
    before = snapshot()
    isolated_database_environment()
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    start = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = snapshot()
    report = {'modules': names, 'tests': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'skipped': len(result.skipped), 'successful': result.wasSuccessful(),
        'duration_seconds': time.monotonic() - start, 'source_changed': before != after,
        'before': before, 'after': after}
    (out / f'backend-group-{group}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    raise SystemExit(not result.wasSuccessful() or bool(result.skipped) or before != after)

before = snapshot()
isolated_database_environment()
modules = [(p.stem, unittest.defaultTestLoader.loadTestsFromName(p.stem).countTestCases())
    for p in sorted((backend / 'tests').glob('test_*.py'))]
groups = [[] for _ in range(4)]
weights = [0] * 4
for name, count in sorted(modules, key=lambda row: -row[1]):
    index = weights.index(min(weights))
    groups[index].append(name)
    weights[index] += count
def execute(index):
    with (out / f'backend-group-{index}.txt').open('w', encoding='utf-8') as log:
        process = subprocess.run([sys.executable, str(Path(__file__)), str(index), *groups[index]],
            stdout=log, stderr=subprocess.STDOUT, cwd=root)
    return process.returncode
start = time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    codes = list(pool.map(execute, range(4)))
reports = [json.loads((out / f'backend-group-{index}.json').read_text()) for index in range(4)]
after = snapshot()
value = {'method': 'all_discovered_modules_in_four_independent_processes_private_PG_schemas',
    'expected_tests': sum(count for _, count in modules), 'modules': dict(modules), 'exit_codes': codes,
    'tests': sum(r['tests'] for r in reports), 'failures': sum(r['failures'] for r in reports),
    'errors': sum(r['errors'] for r in reports), 'skipped': sum(r['skipped'] for r in reports),
    'source_changed': before != after or any(r['source_changed'] for r in reports),
    'duration_seconds': time.monotonic() - start, 'before': before, 'after': after}
value['successful'] = (not any(codes) and value['tests'] == value['expected_tests'] and
    not value['source_changed'] and not value['failures'] and not value['errors'] and not value['skipped'])
(out / 'backend-tests-frozen.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
print(json.dumps({key: data for key, data in value.items() if key not in {'before', 'after', 'modules'}}))
raise SystemExit(not value['successful'])
