"""Read server settings privately; never print or persist the credential values."""
import json
import os
from pathlib import Path
from globalmail_agent.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


def configured_settings():
    values = {}
    for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            if key.strip() in {'LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL',
                              'GLOBALMAIL_EMBEDDING_API_KEY', 'GLOBALMAIL_EMBEDDING_BASE_URL'}:
                values[key.strip()] = value.strip().strip('"').strip("'")
    return Settings(model_api_key=values.get('LLM_API_KEY', ''),
        model_base_url=values.get('LLM_BASE_URL', ''), model_name=values.get('LLM_MODEL', ''),
        embedding_api_key=values.get('GLOBALMAIL_EMBEDDING_API_KEY', ''),
        embedding_base_url=values.get('GLOBALMAIL_EMBEDDING_BASE_URL', ''))


def isolated_database_environment():
    if not os.getenv('GLOBALMAIL_TEST_DATABASE_URL'):
        private = json.loads((ROOT / '.local-data/runtime/settings.json').read_text(encoding='utf-8-sig'))
        os.environ['GLOBALMAIL_TEST_DATABASE_URL'] = private['database_url']


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
