"""Live Phase 2 acceptance; optional isolated PG/object persistence across restart."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / 'globalmail-agent/backend'
sys.path.insert(0, str(BACKEND / 'src'))


def request(url, headers=None):
    try:
        result = urlopen(Request(url, headers=headers or {}), timeout=10)
    except HTTPError as error:
        result = error
    with result:
        return result.status, result.read().decode()


def persistence(settings):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, insert, text
    from globalmail_agent.adapters.object_store import ObjectStore, Scope, Source
    from globalmail_agent.adapters.schema import workspaces
    schema = 'phase2_restart_' + uuid4().hex
    admin = create_engine(settings['database_url'], hide_parameters=True)
    engine = create_engine(settings['database_url'], hide_parameters=True, pool_pre_ping=True,
                           connect_args={'options': f'-csearch_path={schema}'})
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with tempfile.TemporaryDirectory(prefix='phase2_restart_') as temporary:
            config = Config(str(BACKEND / 'alembic.ini'))
            with engine.begin() as connection:
                config.attributes['connection'] = connection
                command.upgrade(config, 'head')
                workspace = uuid4()
                connection.execute(insert(workspaces).values(id=workspace, name='restart acceptance'))
            scope = Scope(workspace_id=workspace, mode='simulation', branch_id=uuid4(),
                          customer_id=uuid4(), purpose='isolated_acceptance')
            store = ObjectStore(Path(temporary), engine)
            object_id = store.put(b'phase2 persistent body', scope, Source(kind='test', reference='synthetic'))
            engine.dispose()
            admin.dispose()
            compose = ['docker', 'compose', '--project-name', 'globalmail-agent', '--env-file',
                       str(ROOT / '.local-data/runtime/compose.env'), '-f',
                       str(ROOT / 'globalmail-agent/infra/compose.yaml')]
            subprocess.run(compose + ['restart', 'postgres'], check=True, capture_output=True)
            subprocess.run(compose + ['up', '-d', '--wait'], check=True, capture_output=True)
            assert store.get(object_id, scope) == b'phase2 persistent body'
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--restart-database', action='store_true')
    args = parser.parse_args()
    settings = json.loads((ROOT / '.local-data/runtime/settings.json').read_text(encoding='utf-8-sig'))
    api = f'http://127.0.0.1:{settings["api_port"]}'
    web = f'http://127.0.0.1:{settings["frontend_port"]}'
    checks = []
    for base in (api, web):
        for endpoint in ('health/live', 'health/ready', 'runtime-config'):
            status, body = request(base + '/api/v1/' + endpoint)
            parsed = json.loads(body)
            assert status == parsed['code'] == 200 and parsed['request_id']
            assert settings['database_url'] not in body and 'postgresql' not in body
            checks.append({'target': 'api' if base == api else 'frontend_proxy', 'endpoint': endpoint, 'status': status})
        for headers, expected in (({'Host': 'evil.example'}, 400 if base == api else 403),
                                  ({'Origin': 'https://evil.example'}, 403)):
            assert request(base + '/api/v1/health/live', headers)[0] == expected
    if args.restart_database:
        persistence(settings)
        assert request(api + '/api/v1/health/ready')[0] == 200
    report = {'status': 'passed', 'http_checks': checks, 'invalid_host_origin': 'rejected',
              'database_restart_persistence': 'passed' if args.restart_database else 'not_run',
              'test_data': 'isolated schema and temporary objects cleaned'}
    filename = 'phase2-runtime-restart-check.json' if args.restart_database else 'phase2-runtime-check.json'
    output = ROOT / 'tmp' / filename
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
