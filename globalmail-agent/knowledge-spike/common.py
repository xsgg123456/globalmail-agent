"""Shared paths and safe reporting for isolated knowledge experiments."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WORK = ROOT/'tmp/knowledge-spike'
DATA = ROOT/'data/knowledge/v1'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    os.replace(temporary, path)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def execute_report(filename, main):
    path = HERE/filename
    write(path, {'status': 'running', 'scope': 'developer_spike_not_product_acceptance'})
    try:
        result = main()
        result.setdefault('status', 'completed')
        write(path, result)
        return result
    except Exception as exc:
        write(path, {'status': 'failed', 'error_type': type(exc).__name__,
                     'http_status': getattr(exc, 'status_code', None)})
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__}), flush=True)
        raise SystemExit(1) from None


def normalized(text):
    return ''.join(text.split()).lower()
