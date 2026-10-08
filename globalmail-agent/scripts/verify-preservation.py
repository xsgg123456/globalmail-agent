"""Read-only before/after checks of formal rows/settings/original source bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlalchemy as sa

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / 'docs/verification/artifacts/phase6'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def file_hashes():
    files = {}
    for directory in (ROOT / 'data', ROOT / 'output/pdf'):
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                files[str(path.relative_to(ROOT)).replace('\\', '/')] = digest(path.read_bytes())
    return files


def capture(before=None):
    settings_path = ROOT / '.local-data/runtime/settings.json'
    private = json.loads(settings_path.read_text(encoding='utf-8-sig'))
    engine = sa.create_engine(private['database_url'], hide_parameters=True)
    try:
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            names = inspector.get_table_names(schema='public')
            tables = {}
            for name in sorted(names if before is None else before['tables']):
                table = sa.Table(name, sa.MetaData(), schema='public', autoload_with=conn)
                columns = list(table.c.keys()) if before is None else before['tables'][name]['columns']
                # Compare the same old columns; newly added default fields do not rewrite old facts.
                values = [dict(row) for row in conn.execute(sa.select(*[table.c[k] for k in columns])).mappings()]
                rows = sorted([canonical(row).decode() for row in values])
                tables[name] = {'columns': columns, 'rows': len(rows), 'sha256': digest(canonical(rows))}
            revision = conn.execute(sa.text('SELECT version_num FROM public.alembic_version')).scalar_one()
            knowledge = {name: conn.execute(sa.select(sa.func.count()).select_from(
                sa.Table(name, sa.MetaData(), schema='public', autoload_with=conn))).scalar_one()
                for name in ('documents', 'document_versions', 'index_builds', 'knowledge_releases', 'embedding_cache') if name in names}
    finally: engine.dispose()
    return {'revision': revision, 'table_count': len(names), 'tables': tables,
        'settings_sha256': digest(settings_path.read_bytes()), 'source_files': file_hashes(), 'knowledge_counts': knowledge}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('before', 'after'))
    args = parser.parse_args()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    if args.action == 'before':
        value = capture()
        (ARTIFACTS / 'formal-before.json').write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps({'status': 'captured_read_only', 'revision': value['revision'], 'tables': value['table_count'],
                          'knowledge_counts': value['knowledge_counts']}))
        return
    before = json.loads((ARTIFACTS / 'formal-before.json').read_text(encoding='utf-8'))
    after = capture(before)
    preserved = {name: data == after['tables'].get(name) for name, data in before['tables'].items() if name != 'alembic_version'}
    value = {'before_revision': before['revision'], 'after_revision': after['revision'],
        'before_table_count': before['table_count'], 'after_table_count': after['table_count'],
        'old_tables_preserved': preserved, 'settings_preserved': before['settings_sha256'] == after['settings_sha256'],
        'source_bytes_preserved': before['source_files'] == after['source_files'],
        'knowledge_counts': after['knowledge_counts']}
    (ARTIFACTS / 'formal-preservation.json').write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(value))
    if not all(preserved.values()) or not value['settings_preserved'] or not value['source_bytes_preserved']:
        raise SystemExit(1)


if __name__ == '__main__': main()
