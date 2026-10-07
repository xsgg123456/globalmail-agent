"""Compare real local parsing, preserving failures and source fingerprints."""
import argparse
import json
import os
import subprocess
import time

import psutil
from common import ROOT, HERE, WORK, DATA, read, write, normalized, execute_report


def measure(source, parser):
    output = WORK/f'{source.stem}-{parser}.json'
    output.unlink(missing_ok=True)
    cmd = [str(WORK/'mineru-venv/Scripts/python.exe'), str(HERE/'parse_one.py'),
           str(source), parser, str(output)]
    env = dict(os.environ, PYTHONUTF8='1', MINERU_HOME=str(WORK/'mineru-home'),
               MINERU_MODEL_SOURCE='modelscope')
    log = WORK/f'{source.stem}-{parser}.log'
    start, peak = time.monotonic(), 0
    with log.open('w', encoding='utf-8') as stream:
        child = subprocess.Popen(cmd, stdout=stream, stderr=subprocess.STDOUT, env=env)
        process = psutil.Process(child.pid)
        timed_out = False
        while child.poll() is None:
            try:
                peak = max(peak, sum(p.memory_info().rss for p in [process]+process.children(recursive=True)
                                    if p.is_running()))
            except psutil.Error:
                pass
            if time.monotonic()-start > 900:
                timed_out = True
                for descendant in process.children(recursive=True):
                    try:
                        descendant.kill()
                    except psutil.Error:
                        pass
                child.kill()
                break
            time.sleep(0.2)
        code = child.wait()
    detail = {'source': source.name, 'parser': parser, 'exit_code': code,
              'timeout': timed_out, 'wall_seconds': round(time.monotonic()-start, 2),
              'peak_process_tree_rss_mib': round(peak/1024**2, 1)}
    if code != 0 or not output.exists():
        detail['completed'] = False
        return detail
    result = read(output)
    detail.update(completed=True, parser_version=result['parser_version'],
                  source_sha256=result['source_sha256'], pages=result['page_count'],
                  full_document=result['full_document'], images=sum(p['image_count'] for p in result['pages']))
    if source.name == 'product-manuals-v1.pdf':
        docs = [d for d in read(DATA/'documents.json') if d['document_type'] == 'manual_pdf']
        bindings = {b['document_id']: b for b in read(DATA/'knowledge-bindings.json')}
        checks = []
        for d in docs:
            lo, hi = d['page_range']
            text = normalized('\n'.join(p['text'] for p in result['pages'] if lo <= p['page'] <= hi))
            checks.extend({'sku': sku, 'found_in_expected_pages': normalized(sku) in text}
                          for sku in bindings[d['document_id']]['skus'])
        detail['sku_checks'] = checks
        detail['sku_hits'] = sum(x['found_in_expected_pages'] for x in checks)
        detail['quality_gate'] = (result['page_count'] == 17 and result['full_document']
                                  and all(x['found_in_expected_pages'] for x in checks)
                                  and detail['images'] >= 8)
        detail['quality_scope'] = 'page_sku_image_presence_only_not_visual_factual_review'
    else:
        truth = read(WORK/'fixture-truth.json')
        checks = []
        bypage = {str(p['page']): p for p in result['pages']}
        for page, phrases in truth['page_markers'].items():
            text = normalized(bypage.get(page, {}).get('text', ''))
            checks.extend({'page': int(page), 'phrase': phrase, 'found': normalized(phrase) in text}
                          for phrase in phrases)
        rows = [row for p in result['pages'] for row in p['table_rows']]
        detail['marker_checks'] = checks
        detail['marker_hits'] = sum(x['found'] for x in checks)
        detail['marker_total'] = len(checks)
        detail['structured_table_rows'] = len(rows)
        row_checks = []
        for expected in truth['table_rows']:
            cells = [expected['part'], str(expected['voltage']), str(expected['current']), expected['model']]
            found = any(all(normalized(cell) in [normalized(v) for v in row] for cell in cells) for row in rows)
            row_checks.append({'part': expected['part'], 'structured_cells_correct': found})
        detail['table_checks'] = row_checks
        detail['table_rows_correct'] = sum(r['structured_cells_correct'] for r in row_checks)
        # Token presence is insufficient for table usability; both are recorded.
        detail['quality_gate'] = (result['full_document'] and result['page_count'] == 4
                                  and all(x['found'] for x in checks) and all(r['structured_cells_correct'] for r in row_checks))
    return detail


def main(parsers, names):
    sources = [ROOT/'output/pdf/product-manuals-v1.pdf', WORK/'difficult-native.pdf', WORK/'difficult-scanned.pdf']
    sources = [s for s in sources if s.name in names]
    rows = []
    for parser in parsers:
        for source in sources:
            row = measure(source, parser)
            rows.append(row)
            write(WORK/'parsing-progress.json', {'status': 'running', 'results': rows})
            print(json.dumps({k:v for k,v in row.items() if not k.endswith('checks')}, ensure_ascii=True), flush=True)
    write(WORK/'parsing-progress.json', {'status':'completed', 'results':rows})
    return {'scope': 'developer_parser_comparison_not_product_acceptance', 'results': rows,
            'all_invocations_completed': all(r['completed'] for r in rows),
            'limitations': ['single cold/warm mixed run; resource metric is process-tree RSS, not GPU memory',
                            'fixtures are synthetic; marker checks do not prove reading order or visual meaning']}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--parsers', nargs='+', default=['pypdf', 'mineru-flash', 'mineru-basic'])
    ap.add_argument('--sources', nargs='+', default=['product-manuals-v1.pdf','difficult-native.pdf','difficult-scanned.pdf'],
                    choices=['product-manuals-v1.pdf','difficult-native.pdf','difficult-scanned.pdf'])
    ap.add_argument('--standard-report', action='store_true')
    args = ap.parse_args()
    report = 'parsing-standard-results.json' if args.standard_report else 'parsing-results.json'
    execute_report(report, lambda: main(args.parsers, args.sources))
