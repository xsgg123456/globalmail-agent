"""Small, explicit provider probes. Uses curated knowledge, never raw customer mail."""
import base64
import hashlib
import json
import math
import os
import time
from pathlib import Path
from urllib.parse import urlparse

os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGSMITH_TRACING'] = 'false'

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader
import pypdfium2
from probe_support import run_reported

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/knowledge/v1'
WORK = ROOT / 'tmp/tech-selection'
REPORT = Path(__file__).with_name('provider-results.json')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def config():
    values = {}
    for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('\"').strip("'")
    if urlparse(values['LLM_BASE_URL']).hostname != 'dashscope.aliyuncs.com':
        raise ValueError('This probe only targets the approved Beijing provider')
    return values


class Understanding(BaseModel):
    model_config = ConfigDict(extra='forbid')
    order_number: str
    ask_shipment_status: bool
    conditional_refund: bool
    authorize_refund_now: bool


@tool
def get_order_snapshot(order_number: str) -> dict:
    """Read the SKU and shipment for a fictional test order."""
    if order_number != '999-1000001-2000001':
        return {'found': False}
    return {'found': True, 'sku': 'H-CTD16-US-BK', 'shipment_status': 'label_created'}


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    cfg = config()
    llm = ChatOpenAI(model=cfg['LLM_MODEL'], base_url=cfg['LLM_BASE_URL'], api_key=cfg['LLM_API_KEY'],
                     temperature=0, max_tokens=700, timeout=40, max_retries=0,
                     use_responses_api=False, stream_usage=True, extra_body={'enable_thinking': False})
    client = OpenAI(base_url=cfg['LLM_BASE_URL'], api_key=cfg['LLM_API_KEY'], timeout=40, max_retries=0)
    results = {'scope': 'component_probes_not_agent_acceptance', 'model': cfg['LLM_MODEL'],
               'beijing_date': '2026-10-07', 'checks': [], 'usage': []}

    def check(name, fn):
        start = time.monotonic()
        try:
            detail = fn()
            results['checks'].append({'name': name, 'passed': True, 'detail': detail,
                                      'elapsed_seconds': round(time.monotonic()-start, 2)})
        except Exception as exc:
            # No raw provider response, headers, request body or credentials in reports.
            results['checks'].append({'name': name, 'passed': False, 'error_type': type(exc).__name__,
                                      'http_status': getattr(exc, 'status_code', None)})
        REPORT.write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(results['checks'][-1], ensure_ascii=False), flush=True)

    def structured():
        response = llm.with_structured_output(Understanding, method='json_schema', strict=True, include_raw=True).invoke([
            SystemMessage(content='Extract the customer intent. A conditional refund is not permission to refund now.'),
            HumanMessage(content='Order 999-1000001-2000001: my replacement remote has not arrived. Please check tracking. If it still does not arrive, I would like a refund.')])
        parsed = response['parsed']
        assert parsed is not None and parsed.ask_shipment_status and parsed.conditional_refund
        assert not parsed.authorize_refund_now and parsed.order_number == '999-1000001-2000001'
        results['usage'].append(response['raw'].usage_metadata)
        return {'method': 'json_schema', 'validated': parsed.model_dump()}

    def streamed_tool():
        bound = llm.bind_tools([get_order_snapshot])
        messages = [SystemMessage(content='Use the order tool to find the exact SKU and shipment status. Do not invent values.'),
                    HumanMessage(content='Please look up order 999-1000001-2000001. What is the SKU and has it shipped?')]
        chunks = list(bound.stream(messages))
        merged = chunks[0]
        for chunk in chunks[1:]:
            merged += chunk
        assert len(merged.tool_calls) == 1
        call = merged.tool_calls[0]
        assert call['name'] == 'get_order_snapshot' and call['args']['order_number'] == '999-1000001-2000001'
        tool_result = get_order_snapshot.invoke(call['args'])
        reply = llm.invoke(messages + [merged, ToolMessage(content=json.dumps(tool_result), tool_call_id=call['id'])])
        assert 'H-CTD16-US-BK' in reply.content and 'label' in reply.content.lower()
        assert merged.usage_metadata and reply.usage_metadata
        results['usage'].extend([merged.usage_metadata, reply.usage_metadata])
        return {'stream_chunks': len(chunks), 'tool_name': call['name'], 'final_reply': reply.content,
                'stream_usage_present': True}

    pdf_path = ROOT / 'output/pdf/product-manuals-v1.pdf'
    pages = []

    def pdf_extract():
        reader = PdfReader(pdf_path)
        pages.extend(page.extract_text() or '' for page in reader.pages)
        products = read(DATA/'products.json')
        missing = [p['sku'] for p in products if p['sku'] not in '\n'.join(pages)]
        assert len(pages) == 17 and not missing
        raster_images = sum(len(page.images) for page in reader.pages)
        assert raster_images == 8
        pdf = pypdfium2.PdfDocument(str(pdf_path))
        page = pdf[1]
        bitmap = page.render(scale=1.5)
        pil = bitmap.to_pil()
        pil.save(WORK/'manual-page-2.png')
        pil.close(); bitmap.close(); page.close(); pdf.close()
        return {'pages': len(pages), 'sku_tokens_found': len(products), 'embedded_images': raster_images,
                'characters': sum(len(p) for p in pages), 'pdf_sha256': hashlib.sha256(pdf_path.read_bytes()).hexdigest()}

    def vision():
        data = base64.b64encode((WORK/'manual-page-2.png').read_bytes()).decode('ascii')
        response = llm.invoke([HumanMessage(content=[
            {'type':'text','text':'Read this product reference page. In English give: the visible product type, the figure label, and one visible SKU. Only report what is visible; do not infer electrical ratings or compatibility.'},
            {'type':'image_url','image_url':{'url':'data:image/png;base64,'+data}}])])
        assert response.content and ('lamp' in response.content.lower() or 'light' in response.content.lower())
        assert 'H-CTD16' in response.content
        results['usage'].append(response.usage_metadata)
        return {'page': 2, 'output': response.content, 'scope': 'one_page_image_input_smoke_not_full_visual_ingestion'}

    def embeddings():
        assert pages
        docs = read(DATA/'documents.json')
        bindings = read(DATA/'knowledge-bindings.json')
        bydoc = {b['document_id']: b for b in bindings}
        corpus = []
        for d in docs:
            if d['document_type'] == 'manual_pdf':
                lo, hi = d['page_range']
                text = '\n'.join(pages[lo-1:hi])
            else:
                text = (DATA/d['path']).read_text(encoding='utf-8')
            # Whole-document baseline; production chunking is a separate implementation task.
            corpus.append({'id':d['document_id'], 'text':text, 'skus':bydoc[d['document_id']].get('skus',[])})
        queries = [json.loads(s) for s in (DATA/'evaluation/retrieval-queries.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
        texts = [d['text'] for d in corpus] + [q['query'] for q in queries]
        fingerprint = hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest()
        cache = WORK/'embedding-v4-1024.json'
        cached = read(cache) if cache.exists() else None
        if cached and cached['fingerprint'] == fingerprint:
            vectors = cached['vectors']
            usage = cached['usage']
        else:
            vectors, usage = [], []
            for offset in range(0,len(texts),10):
                response = client.embeddings.create(model='text-embedding-v4',input=texts[offset:offset+10],dimensions=1024,encoding_format='float')
                vectors.extend(d.embedding for d in sorted(response.data,key=lambda d:d.index))
                usage.append(response.usage.model_dump())
            cache.write_text(json.dumps({'fingerprint':fingerprint,'vectors':vectors,'usage':usage}),encoding='utf-8')
        assert len(vectors)==len(texts) and all(len(v)==1024 and all(math.isfinite(x) for x in v) for v in vectors)
        def cosine(a,b): return sum(x*y for x,y in zip(a,b))/(math.sqrt(sum(x*x for x in a))*math.sqrt(sum(x*x for x in b)))
        observations=[]
        for n,q in enumerate(queries):
            ranked=sorted(range(len(corpus)),key=lambda i:cosine(vectors[i],vectors[len(corpus)+n]),reverse=True)
            global_ids=[corpus[i]['id'] for i in ranked[:5]]
            scoped=[corpus[i]['id'] for i in ranked if q['sku'] in corpus[i]['skus']][:5]
            expected=set(q['expected_document_ids'])
            observations.append({'query_id':q['query_id'],'expected':sorted(expected),'global_top5':global_ids,
                'global_top1_hit':bool(expected and global_ids[0] in expected),
                'scoped_top5':scoped,'scoped_hit':bool(expected.intersection(scoped)) if expected else not scoped,
                'wrong_sku_excluded':not set(scoped).intersection(q['must_exclude'])})
        assert all(q['scoped_hit'] and q['wrong_sku_excluded'] for q in observations)
        # Keep text/vector cache local; report only document IDs and aggregate evidence.
        (WORK/'retrieval-corpus.json').write_text(json.dumps(corpus,ensure_ascii=False),encoding='utf-8')
        return {'embedding_model':'text-embedding-v4','dimensions':1024,'documents':len(corpus),'queries':len(queries),
                'positive_queries':16,'negative_queries':8,'global_top1_hits':sum(q['global_top1_hit'] for q in observations),
                'scoped_passed':len(observations),'embedding_usage':usage,'observations':observations,
                'limitations':'Small developer set; whole-document ranking and explicit SKU filtering, not independent RAG quality evaluation.'}

    check('native_json_schema', structured)
    check('streamed_tool_roundtrip_and_usage', streamed_tool)
    check('pdf_text_images_and_page_render', pdf_extract)
    check('qwen_page_vision', vision)
    check('cross_language_embedding_baseline', embeddings)
    client.close()
    results['passed'] = all(c['passed'] for c in results['checks'])
    results['provider_total_tokens'] = sum((u or {}).get('total_tokens', 0) for u in results['usage'])
    REPORT.write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if not results['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    run_reported(REPORT,main)
