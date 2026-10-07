"""Structure-first developer chunker with explicit inherited applicability."""
import re
import hashlib
from datetime import datetime
from functools import lru_cache

from tokenizers import Tokenizer
from common import DATA, ROOT, WORK, read, write, fingerprint

SKU_BRANDS = {p['sku']: p['brand'] for p in read(DATA/'products.json')}


@lru_cache(maxsize=1)
def shared_tokenizer():
    return Tokenizer.from_file(str(WORK/'qwen3-tokenizer.json'))


class Budget:
    def __init__(self):
        self.tokenizer = shared_tokenizer()

    def count(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=False).ids)


def load_documents():
    bindings = {b['document_id']: b for b in read(DATA/'knowledge-bindings.json')}
    parsed = read(WORK/'product-manuals-v1-mineru-basic.json')
    assert parsed['page_count'] == 17 and parsed['full_document']
    if parsed['source_sha256'] != hashlib.sha256((ROOT/'output/pdf/product-manuals-v1.pdf').read_bytes()).hexdigest():
        raise ValueError('Parsed PDF is stale; rerun parsing')
    documents = []
    for original in read(DATA/'documents.json'):
        d = dict(original)
        binding = bindings[d['document_id']]
        assert binding['document_version'] == d['version']
        d['brands'] = binding.get('brands', [d.get('brand')])
        if 'skus' in binding:
            d['skus'] = binding['skus']
        elif binding.get('sku_scope') == 'all_products_within_explicit_policy_scope':
            d['skus'] = [sku for sku, brand in SKU_BRANDS.items() if brand in d['brands']]
        else:
            raise ValueError('No explicit applicability')
        d['allowed_modes'] = sorted(set(d['allowed_modes']) & set(binding['allowed_modes']))
        d['available_at'] = max(d['available_at'], binding['available_at'], key=datetime.fromisoformat)
        if d['document_type'] == 'manual_pdf':
            lo, hi = d['page_range']
            sections = []
            for page in parsed['pages']:
                if not lo <= page['page'] <= hi:
                    continue
                heading, pieces = f'第 {page["page"]} 页', []
                for block in page['blocks']:
                    if block['type'] in {'header', 'footer', 'page_number'}:
                        continue
                    text = block['text'].strip()
                    if not text:
                        continue
                    if block['type'] == 'paragraph_title' and pieces:
                        sections.append({'heading': heading, 'text': '\n'.join(pieces), 'page': page['page']})
                        heading, pieces = text, []
                    else:
                        pieces.append(text)
                if pieces:
                    sections.append({'heading': heading, 'text': '\n'.join(pieces), 'page': page['page']})
            d['sections'] = sections
            d['text'] = '\n\n'.join(s['heading']+'\n'+s['text'] for s in sections)
        else:
            text = (DATA/d['path']).read_text(encoding='utf-8-sig')
            d['text'] = text
            sections, heading, lines = [], d['title'], []
            for line in text.splitlines():
                if line.startswith('#'):
                    if any(x.strip() for x in lines):
                        sections.append({'heading': heading, 'text': '\n'.join(lines).strip(), 'page': None})
                    heading, lines = line.lstrip('#').strip(), []
                else:
                    lines.append(line)
            if any(x.strip() for x in lines):
                sections.append({'heading': heading, 'text': '\n'.join(lines).strip(), 'page': None})
            d['sections'] = sections
        d['parent_id'] = f'{d["document_id"]}@{d["version"]}'
        documents.append(d)
    return documents


def split_units(text, budget, limit):
    """Respect paragraphs, list items and then sentences; reject oversized atomic units."""
    units = [x.strip() for x in re.split(r'\n\s*\n|\n(?=\d+\.|[-*] )', text) if x.strip()]
    refined = []
    for unit in units:
        if budget.count(unit) <= limit:
            refined.append(unit)
        else:
            refined.extend(x for x in re.split(r'(?<=[。！？.!?])\s*', unit) if x.strip())
    groups, current = [], []
    for unit in refined:
        if budget.count(unit) > limit:
            raise ValueError('Atomic unit exceeds budget; manual split required')
        if current and budget.count('\n'.join(current+[unit])) > limit:
            groups.append('\n'.join(current))
            current = []
        current.append(unit)
    if current:
        groups.append('\n'.join(current))
    return groups


def build_chunks(documents, strategy, budget):
    chunks = []
    for d in documents:
        prefix = d['title']+'\n'
        if strategy == 'whole':
            segments = [('全文', d['text'], None)]
        elif strategy == 'fixed500':
            segments = [('固定字符窗口', d['text'][i:i+500], None) for i in range(0, len(d['text']), 450)]
        else:
            target = int(strategy.removeprefix('structured'))
            if d['document_type'] == 'case_md' and budget.count(prefix+d['text']) <= 800:
                segments = [('完整案例', d['text'], None)]
            else:
                segments = []
                guard = ''
                if d['document_type'] == 'troubleshooting_md':
                    guard = '\n'.join(s['heading']+'\n'+s['text'] for s in d['sections']
                                      if s['heading'] in {'先确认什么', '交给人工的情况'})
                for section in d['sections']:
                    header = prefix+section['heading']+'\n'
                    context = guard if section['heading'] not in {'先确认什么', '交给人工的情况'} else ''
                    # Guard context is counted in the actual embedding input budget.
                    limit = max(100, target-budget.count(header+context))
                    for body in split_units(section['text'], budget, limit):
                        text = body+('\n必要前提与停止条件：\n'+context if context else '')
                        if budget.count(header+text) > 1000:
                            raise ValueError('Context exceeds hard experimental token budget')
                        segments.append((section['heading'], text, section['page']))
        for ordinal, (heading, body, page) in enumerate(segments):
            embedded = prefix+heading+'\n'+body
            row = {k: d[k] for k in ['document_id', 'version', 'brands', 'skus', 'allowed_modes',
                                      'available_at', 'usage_split', 'parent_id']}
            row.update(chunk_id=f'{d["document_id"]}:{strategy}:{ordinal}', strategy=strategy,
                       heading=heading, text=body, embedding_input=embedded, page=page,
                       input_hash=fingerprint(embedded), parent_text_hash=fingerprint(d['text']),
                       token_count=budget.count(embedded))
            chunks.append(row)
    return chunks


def eligible(chunk, query):
    brand = SKU_BRANDS.get(query['sku'])
    return (brand is not None and query.get('brand', brand) == brand and brand in chunk['brands']
            and query['sku'] in chunk['skus'] and query['mode'] in chunk['allowed_modes']
            and chunk['usage_split'] == 'rag'
            and datetime.fromisoformat(chunk['available_at']) <= datetime.fromisoformat(query['as_of']))


def verified_parent(chunk, parents, query):
    parent = parents.get(chunk['parent_id'])
    if (parent is None or not eligible(parent, query)
            or any(parent[k] != chunk[k] for k in ('document_id', 'version', 'parent_id'))
            or parent['parent_id'] != f'{parent["document_id"]}@{parent["version"]}'
            or chunk.get('parent_text_hash') != fingerprint(parent['text'])):
        return None
    # Whole-document expansion is safe only for this experiment's uniform scopes.
    for field in ('brands', 'skus', 'allowed_modes'):
        if set(parent[field]) != set(chunk[field]):
            return None
    if any(parent[k] != chunk[k] for k in ('available_at', 'usage_split')):
        return None
    return parent


def main():
    documents, budget = load_documents(), Budget()
    result = {'documents': len(documents), 'strategies': {},
              'tokenizer': 'Qwen/Qwen3-Embedding-0.6B proxy; hosted v4 tokenizer parity unverified',
              'tokenizer_sha256': fingerprint((WORK/'qwen3-tokenizer.json').read_text(encoding='utf-8'))}
    for strategy in ('whole', 'fixed500', 'structured300', 'structured500'):
        chunks = build_chunks(documents, strategy, budget)
        write(WORK/f'chunks-{strategy}.json', chunks)
        result['strategies'][strategy] = {'chunks': len(chunks),
            'max_tokens': max(c['token_count'] for c in chunks),
            'total_tokens': sum(c['token_count'] for c in chunks), 'fingerprint': fingerprint(chunks)}
    write(WORK/'documents-normalized.json', documents)
    return result


if __name__ == '__main__':
    from common import execute_report
    execute_report('chunking-results.json', main)
