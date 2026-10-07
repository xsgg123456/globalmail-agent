"""Real Qwen JSON-schema requests. Runtime never reads evaluation labels."""
import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGSMITH_TRACING'] = 'false'

from openai import OpenAI
from prepare_views import CONFIG, DATA, ROOT, prepare
from vision_contract import Analysis, PROMPT


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def config():
    values = {}
    for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('\"').strip("'")
    if values.get('LLM_BASE_URL', '').rstrip('/') != 'https://dashscope.aliyuncs.com/compatible-mode/v1':
        raise ValueError('unapproved_endpoint')
    if values.get('LLM_MODEL') != 'qwen3.7-plus':
        raise ValueError('unapproved_model')
    return values


class Budget:
    def __init__(self):
        self.started = time.monotonic()
        self.calls = 0
        self.views = 0
        self.tokens = 0
        self.unknown_usage = False

    def reserve(self, input_upper, views):
        if (self.calls >= 6 or self.views + views > 6 or input_upper > 16000
                or self.tokens + input_upper + 2000 > 80000
                or time.monotonic() - self.started >= 120):
            raise ValueError('budget_exhausted')
        self.calls += 1
        self.views += views
        self.tokens += input_upper + 2000
        return input_upper + 2000

    def settle(self, reservation, usage):
        if usage is None:
            self.unknown_usage = True
            return
        self.tokens += usage['total_tokens'] - reservation
        if (usage['prompt_tokens'] > 16000 or usage['completion_tokens'] > 2000
                or self.tokens > 80000):
            raise ValueError('actual_budget_exceeded')


def request_payload(row, views, coverage):
    # Explicit allowlist; id/branch/file name/labels/fault parameters are not model context.
    text = canonical({'customer_body': row['body'], 'trusted_current_state': row['trusted'],
                      'attachments': coverage})
    content = [{'type': 'text', 'text': text}]
    for view in views:
        content.extend([{'type': 'text', 'text': canonical({'attachment_id': view['attachment_id'],
            'source_box': view['source_box'], 'source_size': view['source_size'],
            'low_detail_warning': view['low_detail_warning']})},
            {'type': 'image_url', 'image_url': {'url': view['data_url'],
                                             'max_pixels': CONFIG['max_pixels']}}])
    return [{'role': 'system', 'content': PROMPT}, {'role': 'user', 'content': content}]


def validate_sources(parsed, coverage):
    statuses = {item['attachment_id']: item['status'] for item in coverage}
    if len(parsed.coverage) != len(statuses) or {c.attachment_id for c in parsed.coverage} != set(statuses):
        raise ValueError('coverage_mismatch')
    for evidence in [*parsed.field_candidates, *parsed.observations]:
        if statuses.get(evidence.attachment_id) != 'ready':
            raise ValueError('unread_or_unknown_evidence_source')
    for item in parsed.coverage:
        expected = statuses[item.attachment_id]
        if expected != 'ready' and item.status != expected:
            raise ValueError('unread_status_changed')
        if expected == 'ready' and item.status not in ('understood', 'partial', 'unreadable'):
            raise ValueError('ready_status_fabricated')


def run_one(client, row, variant, budget, model):
    started = time.monotonic()
    record = {'id': row['id'], 'variant': variant, 'status': 'failed', 'usage': None,
              'analyzed_at': datetime.now(timezone.utc).isoformat()}
    request_started = False
    try:
        views, coverage = prepare(row, variant)
        record['coverage_input'] = coverage
        record['views'] = [{k: v for k, v in view.items() if k != 'data_url'} for view in views]
        if not row['attachments']:
            record['status'] = 'text_path_no_added_vision_request'
            return record
        if not views:
            record['status'] = 'unread_inputs_no_vision_request'
            return record
        messages = request_payload(row, views, coverage)
        schema = Analysis.model_json_schema()
        # UTF-8 byte upper bound for text/schema + default provider cap per image + margin.
        # Never use base64 length as a visual-token estimate.
        text_bytes = len(PROMPT.encode()) + len(canonical(schema).encode())
        text_bytes += sum(len(p['text'].encode()) for p in messages[1]['content'] if p['type'] == 'text')
        upper = text_bytes + len(views) * (CONFIG['max_pixels'] // 1024 + 2) + 512
        reservation = budget.reserve(upper, len(views))
        record.update({'estimated_input_upper': upper, 'reserved_tokens': reservation,
                       'request_sha256': fingerprint({'messages': messages, 'schema': schema})})
        remaining = max(0.001, min(30, 120 - (time.monotonic() - budget.started)))
        request_started = True
        response = client.with_options(timeout=remaining).chat.completions.create(
            model=model, messages=messages, temperature=0, max_tokens=2000,
            extra_body={'enable_thinking': False, 'vl_high_resolution_images': False},
            response_format={'type': 'json_schema', 'json_schema': {
                'name': 'visual_understanding', 'strict': True, 'schema': schema}})
        record['usage'] = response.usage.model_dump() if response.usage else None
        record['provider_response_id'] = response.id
        budget.settle(reservation, record['usage'])
        record['raw_output'] = response.choices[0].message.content
        if time.monotonic() - budget.started > 120:
            raise ValueError('elapsed_budget_exceeded')
        if response.choices[0].finish_reason != 'stop':
            raise ValueError('incomplete_response')
        parsed = Analysis.model_validate_json(record['raw_output'])
        validate_sources(parsed, coverage)
        record['analysis'] = parsed.model_dump()
        record['status'] = 'ok'
    except Exception as exc:
        # Do not log exception text, requests, credentials or provider error bodies.
        record['error_type'] = type(exc).__name__
        record['http_status'] = getattr(exc, 'status_code', None)
        if isinstance(exc, ValueError) and str(exc) in {
            'budget_exhausted', 'actual_budget_exceeded', 'elapsed_budget_exceeded',
            'coverage_mismatch', 'unread_or_unknown_evidence_source', 'unread_status_changed',
            'ready_status_fabricated',
            'incomplete_response', 'source_hash_mismatch', 'scope_denied', 'future_image',
            'revoked', 'byte_limit', 'pixel_limit', 'image_count_limit', 'outside_images'}:
            record['reason'] = str(exc)
    finally:
        if request_started and record['usage'] is None:
            budget.unknown_usage = True
        record['elapsed_seconds'] = round(time.monotonic() - started, 3)
        record['budget'] = {'calls': budget.calls, 'views': budget.views,
                            'tokens_reserved_or_used': budget.tokens,
                            'usage_unknown': budget.unknown_usage}
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--only', default='')
    parser.add_argument('--workers', type=int, choices=[1, 2, 3], default=1)
    args = parser.parse_args()
    if not args.run.replace('-', '').replace('_', '').isalnum() or args.rounds not in (1, 3):
        raise ValueError('invalid_run_arguments')
    output = ROOT / 'tmp/vision-spike' / args.run
    output.mkdir(parents=True, exist_ok=False)  # immutable runs; never reuse stale green results
    summary = {'status': 'running', 'manifest_sha256': hashlib.sha256((DATA / 'manifest.jsonl').read_bytes()).hexdigest(),
        'prompt_sha256': fingerprint(PROMPT), 'schema_sha256': fingerprint(Analysis.model_json_schema()),
        'preprocessing': CONFIG, 'rounds': args.rounds, 'model': 'qwen3.7-plus',
        'experiment_workers': args.workers, 'records': []}
    summary_path = output / 'results.json'
    def save():
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        freeze = json.loads((DATA / 'freeze.json').read_text(encoding='utf-8'))
        if freeze['manifest_sha256'] != summary['manifest_sha256']:
            raise ValueError('freeze_mismatch')
        # The label file is intentionally not loaded by this executable.
        (output / 'manifest.jsonl').write_bytes((DATA / 'manifest.jsonl').read_bytes())
        (output / 'freeze.json').write_text(canonical(freeze), encoding='utf-8')
        (output / 'prompt.txt').write_text(PROMPT, encoding='utf-8')
        summary['source_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in Path(__file__).parent.glob('*.py')}
        rows = [json.loads(line) for line in (DATA / 'manifest.jsonl').read_text(encoding='utf-8').splitlines()]
        selected = [r for r in rows if r['kind'] == 'ai' and (not args.only or r['id'] in args.only.split(','))]
        if not selected:
            raise ValueError('no_selected_cases')
        cfg = config()
        def run_case(row):
            records = []
            with OpenAI(api_key=cfg['LLM_API_KEY'], base_url=cfg['LLM_BASE_URL'], max_retries=0) as client:
                for repeat in range(1, args.rounds + 1):
                    budget = Budget()
                    variants = ['full', 'crop'] if row['options'].get('crop_compare') else ['full']
                    for variant in variants:
                        result = run_one(client, row, variant, budget, cfg['LLM_MODEL'])
                        result['repeat'] = repeat
                        records.append(result)
                        # Per-case journal survives interruption before case completion.
                        journal = output / (row['id'] + '.json')
                        journal.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
                        print(canonical({k: result.get(k) for k in ('id', 'repeat', 'variant', 'status', 'elapsed_seconds', 'reason')}), flush=True)
            return records
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_case, row) for row in selected]
            for future in as_completed(futures):
                summary['records'].extend(future.result())
                save()
        summary['status'] = 'completed' if all(r['status'] == 'ok' for r in summary['records']) else 'completed_with_failures'
    except Exception as exc:
        summary.update({'status': 'failed', 'error_type': type(exc).__name__})
    save()
    if summary['status'] != 'completed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
