"""Run one local parser; source/derived files stay in the ignored workspace."""
import argparse
import hashlib
import importlib.metadata
import os
import time

from common import WORK, read, write


def content_text(node):
    if isinstance(node, list):
        return '\n'.join(filter(None, (content_text(x) for x in node)))
    if not isinstance(node, dict):
        return ''
    if node.get('type') in {'image_body', 'image', 'chart_body', 'equation_body'}:
        # Captions remain in nested content; never embed binary or base64 assets.
        value = node.get('content', [])
        return content_text(value) if isinstance(value, list) else ''
    value = node.get('content', '')
    if isinstance(value, str):
        if value.startswith('data:'):
            return ''
        if '<table' in value.lower():
            from bs4 import BeautifulSoup
            return BeautifulSoup(value, 'html.parser').get_text(' ', strip=True)
        return value
    return content_text(value)


def table_rows(node):
    rows = []
    if isinstance(node, list):
        for child in node:
            rows.extend(table_rows(child))
    elif isinstance(node, dict):
        value = node.get('content', '')
        if isinstance(value, str) and '<table' in value.lower():
            from bs4 import BeautifulSoup
            rows.extend([[c.get_text(' ', strip=True) for c in row.find_all(['td', 'th'])]
                         for row in BeautifulSoup(value, 'html.parser').find_all('tr')])
        elif isinstance(value, list):
            rows.extend(table_rows(value))
    return rows


def parse_file(source, parser, output):
    start = time.monotonic()
    if parser == 'pypdf':
        from pypdf import PdfReader
        pdf = PdfReader(source)
        pages = [{'page': i+1, 'text': p.extract_text() or '', 'blocks': [],
                  'image_count': len(p.images), 'table_rows': []} for i, p in enumerate(pdf.pages)]
        version = importlib.metadata.version('pypdf')
        full_document = True
        diagnostics = ['no_layout_semantics_no_ocr']
    else:
        os.environ['MINERU_HOME'] = str(WORK/'mineru-home')
        os.environ['MINERU_MODEL_SOURCE'] = 'modelscope'
        from mineru.parser import parse
        tier = parser.split('-', 1)[1]
        result = parse(str(source), tier=tier, ocr_mode='txt' if tier == 'flash' else 'auto')
        raw = result.to_dict()
        write(output.with_suffix('.raw.json'), raw)
        pages = []
        for page in raw['pages']:
            blocks = [{'id': b.get('index'), 'type': b.get('type'), 'bbox': b.get('bbox'),
                       'text': content_text(b)} for b in page.get('blocks', [])]
            pages.append({'page': page['page_idx']+1, 'blocks': blocks,
                          'text': '\n'.join(b['text'] for b in blocks if b['text']),
                          'image_count': sum(b['type'] == 'image' for b in blocks),
                          'table_rows': table_rows(page.get('blocks', []))})
        version = importlib.metadata.version('mineru')
        full_document = raw.get('is_full_document', False)
        diagnostics = raw.get('diagnostics', [])
    result = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'parser': parser,
              'parser_version': version, 'elapsed_seconds': round(time.monotonic()-start, 3),
              'full_document': full_document, 'page_count': len(pages), 'pages': pages,
              'diagnostics': diagnostics}
    write(output, result)
    print({'parser': parser, 'pages': len(pages), 'seconds': result['elapsed_seconds']}, flush=True)


if __name__ == '__main__':
    from pathlib import Path
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=Path)
    ap.add_argument('parser', choices=['pypdf', 'mineru-flash', 'mineru-basic', 'mineru-standard'])
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    parse_file(args.source, args.parser, args.output)
