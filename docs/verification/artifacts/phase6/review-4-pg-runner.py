"""Load only isolated PG protocol tests; no formal app or provider call."""
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'globalmail-agent/backend/tests'))
private = json.loads((ROOT / '.local-data/runtime/settings.json').read_text(encoding='utf-8-sig'))
os.environ['GLOBALMAIL_TEST_DATABASE_URL'] = private['database_url']
del private
loader = unittest.TestLoader()
modules = ('test_knowledge_index_api', 'test_knowledge_index_structure', 'test_knowledge_index_faults',
           'test_knowledge_releases', 'test_knowledge_index_migration', 'test_knowledge_index_prepared',
           'test_policy_generation')
names = sys.argv[1:] or modules
suite = loader.loadTestsFromNames(names)
result = unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps({'tests_run': result.testsRun, 'errors': len(result.errors), 'failures': len(result.failures),
                  'skipped': len(result.skipped), 'actual_provider_calls': False,
                  'isolation': 'each fixture creates random owned schema and temporary object directory'}))
sys.exit(0 if result.wasSuccessful() and not result.skipped else 1)
