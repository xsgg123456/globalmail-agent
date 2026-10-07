"""Structural and evidence checks. Does not claim Agent/RAG/runtime correctness."""
import hashlib
import json
import re
from pathlib import Path
from pypdf import PdfReader
from PIL import Image, ImageOps, ImageDraw
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'data/knowledge/v1'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
checks=[]
def check(name,condition,detail=''):
    checks.append({'name':name,'passed':bool(condition),'detail':detail})
    if not condition:print('FAIL:',name,detail)
products=read(OUT/'products.json');families=read(OUT/'families.json');docs=read(OUT/'documents.json');bindings=read(OUT/'knowledge-bindings.json')
parts=read(OUT/'parts.json');compat=read(OUT/'compatibility.json');inventory=read(OUT/'inventory.json')
skus={p['sku'] for p in products};pids={p['part_id'] for p in parts};dids={d['document_id'] for d in docs};docby={d['document_id']:d for d in docs};pby={p['sku']:p for p in products}
check('34 unique production SKUs / 8 families',len(products)==len(skus)==34 and len(families)==8)
check('three brands',set(p['brand'] for p in products)=={'OUTON','OUTONLIFE','BELEEV'})
check('manufacturer parameters left unknown',all(p['manufacturer_hardware_revision'] is None and all(v is None for v in p['unverified_parameters'].values()) for p in products))
check('source transaction read only',str(read(OUT/'sources/product-snapshot.json')['transaction_read_only']).lower() in ['on','true'])
check('unique document ids',len(dids)==len(docs))
check('document paths and hashes',all((OUT/d['path']).resolve().is_file() and hashlib.sha256((OUT/d['path']).resolve().read_bytes()).hexdigest()==d['source_hash'] for d in docs))
check('all docs bound',dids=={b['document_id'] for b in bindings})
check('binding versions and scopes',all(b['document_version']==docby[b['document_id']]['version'] and (b.get('sku_scope') or (b.get('skus') and set(b['skus'])<=skus)) for b in bindings))
check('no cross-brand product binding',all(all(pby[s]['brand']==docby[b['document_id']]['brand'] for s in b.get('skus',[])) for b in bindings))
check('no synthetic knowledge in historical modes',all(d['allowed_modes']==['simulation'] for d in docs))
check('all parts explicit SIM identifiers',len(pids)==len(parts) and all(p.startswith('SIM-') for p in pids))
check('compatibility points to real selected SKU and synthetic part',all(c['sku'] in skus and c['part_id'] in pids and c['allowed_modes']==['simulation'] and c['hardware_revision']=='SIM-V1' for c in compat))
check('inventory balances and all product/part stock rows valid',len(inventory)==len(pids|skus) and {i['item_id'] for i in inventory}==pids|skus and all(0<=i['reserved']<=i['on_hand'] for i in inventory))
check('policy generated from one canonical file',read(OUT/'authoring/policy-profile.json')==read(OUT/'policies/policy-profile.json'))
pol=read(OUT/'policies/policy-profile.json');polmd=(OUT/'policies/policy-profile.md').read_text('utf-8')
policy_render=read(OUT/'sources/policy-render.json')
check('readable policy generated from current canonical rules',policy_render['canonical_sha256']==hashlib.sha256((OUT/'authoring/policy-profile.json').read_bytes()).hexdigest() and policy_render['readable_sha256']==hashlib.sha256((OUT/'policies/policy-profile.md').read_bytes()).hexdigest() and f"{pol['return']['window_days_after_delivery']} 天" in polmd and f"{pol['refund']['partial_offer_max_basis_points']/100:g}%" in polmd)
check('videos not promoted to verified knowledge',all(not v['content_reviewed'] and not v['indexable'] and not v['approved_skus'] for v in read(OUT/'video-directory.json')))
manifest=read(OUT/'sources/case-manifest.json');bycase={m['source_conversation_id']:m for m in manifest};cases=jl(OUT/'cases/reviewed-summaries.jsonl')
group_splits={}
for m in manifest:group_splits.setdefault(m['group_id'],set()).add(m['usage_split'])
check('identity groups do not cross splits',all(len(v)==1 for v in group_splits.values()))
check('reviewed cases use only RAG candidate sources',len(cases)==5 and all(bycase[c['source_conversation_id']]['usage_split']=='rag_candidate' and c['skus'] and set(c['skus'])<=skus for c in cases))
raw=read(ROOT/'.local-data/knowledge-v1/case-source.json');rawby={c['id']:{m['id']:m for m in c['messages']} for c in raw['cases']}
check('case evidence message IDs and times resolve',all(t['message_id'] in rawby[c['source_conversation_id']] and rawby[c['source_conversation_id']][t['message_id']]['at']==t['source_at'] for c in cases for t in c['timeline']))
check('unknown outcomes preserved',sum(c['outcome']=='customer_reported_resolved' for c in cases)==1 and all(c['limitations'] for c in cases))
inputs=jl(OUT/'scenarios/inputs.jsonl');expected=jl(OUT/'evaluation/scenario-assertions.jsonl');events=jl(OUT/'scenarios/controller-events.jsonl');q=jl(OUT/'evaluation/retrieval-queries.jsonl')
ids={s['scenario_id'] for s in inputs};iby={s['scenario_id']:s for s in inputs}
check('51 unique scenarios',len(inputs)==len(ids)==51)
check('SCN-001 through SCN-030 complete',{f'SCN-{i:03d}' for i in range(1,31)}<=ids)
check('three brands times seven baseline scenarios',{f'BASE-{b}-{i:02d}' for b in ['OUTON','OUTONLIFE','BELEEV'] for i in range(1,8)}<=ids)
check('assertions isolated and complete',{a['scenario_id'] for a in expected}==ids and all('expected_actions' not in s and 'forbidden_actions' not in s for s in inputs))
check('future events are controller only',all(e['scenario_id'] in ids and not e['agent_can_create'] and e['actor'].startswith('scenario_console') for e in events))
seen={};valid=True
for e in events:
    if e['event_id'] in seen:
        valid &= e.get('replay_same_event') is True and {k:v for k,v in e.items() if k!='replay_same_event'}==seen[e['event_id']]
    else:
        valid &= e['requires_event_id'] is None or (e['requires_event_id'] in seen and seen[e['requires_event_id']]['scenario_id']==e['scenario_id'])
        seen[e['event_id']]=e
check('events ordered with explicit intentional duplicate',valid)
valid=True
for sc in inputs:
    s=sc['initial_state'];orders={o['order_id']:o for o in s['orders']}
    valid &= set(orders)==set(sc['access_scope']['allowed_order_ids'])
    for o in orders.values():
        valid &= o['customer_id']==sc['access_scope']['customer_id'] and o['paid_minor']==sum(l['paid_minor'] for l in o['lines']) and 0<=o['refunded_minor']+o['pending_refund_minor']<=o['paid_minor'] and all(l['sku'] in skus for l in o['lines'])
    for op in s['operations']:valid &= op['order_id'] in orders and op['order_line_id'] in {l['line_id'] for l in orders[op['order_id']]['lines']}
    for sh in s['shipments']:valid &= sh['order_id'] in orders and sh['order_line_id'] in {l['line_id'] for l in orders[sh['order_id']]['lines']}
check('scenario customer order line and amount consistency',valid)
check('negative scenarios contain relevant missing/conflict data',not iby['SCN-002']['initial_state']['orders'] and not iby['SCN-017']['initial_state']['address_confirmation']['confirmed'] and iby['SCN-018']['initial_state']['inventory'][0]['on_hand']==0 and iby['SCN-020']['initial_state']['confirmed_missing_part_id'] is None and iby['SCN-028']['initial_state']['conversation']['processing_owner']=='human')
check('replay fixture has no synthetic policy',iby['SCN-029']['mode']=='historical_replay' and iby['SCN-029']['policy_profile_id'] is None and not [e for e in events if e['scenario_id']=='SCN-029'])
check('24 developer retrieval queries, targets exist',len(q)==24 and all(set(r['expected_document_ids'])<=dids and r['execution_status']=='not_run' for r in q))
pdf=PdfReader(ROOT/'output/pdf/product-manuals-v1.pdf');texts=[p.extract_text() or '' for p in pdf.pages]
check('17 PDF pages',len(pdf.pages)==17)
check('internal reference notice on every PDF page',all('客服内部整理' in t and '非厂家原版说明书' in t for t in texts))
check('all SKU tokens extract from PDF',' '.join(texts).count('H-CTD16-US-BK')>0 and all(s in '\n'.join(texts) for s in skus))
check('8 genuine embedded raster figures',sum(len(p.images) for p in pdf.pages)==8)
fby={f['family_id']:f for f in families}
check('PDF chapter page mapping',all(fby[d['family_id']]['name'] in texts[d['page_range'][0]-1] for d in docs if d['document_type']=='manual_pdf'))
check('no test terminology in business PDF',not any(word in '\n'.join(texts) for word in ['SIM-V1','RAG','pgvector','knowledge-bindings','hardware_revision']))
photos=read(OUT/'sources/product-photo-manifest.json')
check('eight production-backed photos with exact SKU evidence',len(photos)==8 and all(p['matched_sku'] in skus and p['source_kind']=='production_order_product_photo' and hashlib.sha256((OUT/p['path']).read_bytes()).hexdigest()==p['sha256'] for p in photos))
check('no internal codes in customer mail',all(not re.search(r'SIM-|BIZ-|SCN-|HITL|fixture|inspection passed',m['body']) for sc in inputs for m in sc['initial_messages']))
for ext in ['*.json','*.jsonl']:
    for path in OUT.rglob(ext):
        if path.name=='validation-report.json':continue
        read(path) if ext=='*.json' else jl(path)
check('all JSON and JSONL parse',True)
bad=[]
synthetic_order_numbers={o['display_order_number'] for sc in inputs for o in sc['initial_state']['orders'] if o.get('display_order_number_source')=='synthetic_not_a_real_customer_order'}
journey_inputs=OUT/'scenarios/journeys/inputs.jsonl'
if journey_inputs.exists():
    synthetic_order_numbers.update(o['display_order_number'] for sc in jl(journey_inputs) for o in sc['initial_state']['orders'] if o.get('display_order_number_source')=='synthetic_not_a_real_customer_order')
for path in OUT.rglob('*'):
    if path.suffix not in ['.json','.jsonl','.md']:continue
    if path.name=='validation-report.json':continue
    text=path.read_text('utf-8')
    numbers=set(re.findall(r'\b\d{3}-\d{7}-\d{7}\b',text))
    if numbers-synthetic_order_numbers or re.search(r'\bsk-[A-Za-z0-9]{16,}',text):bad.append(str(path.relative_to(OUT)))
    emails=re.findall(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',text)
    if any(not e.endswith('.invalid') for e in emails):bad.append(str(path.relative_to(OUT)))
check('no raw order number email or API key in published text',not bad,str(bad))
visual_path=OUT/'sources/pdf-visual-review.json'
visual=read(visual_path) if visual_path.exists() else {'status':'pending'}
if visual.get('pdf_sha256')!=hashlib.sha256((ROOT/'output/pdf/product-manuals-v1.pdf').read_bytes()).hexdigest():visual={'status':'pending_or_stale'}
report={'validation_kind':'offline_data_consistency_not_agent_or_rag_test','passed':all(c['passed'] for c in checks),'checks':checks,'counts':{'products':len(products),'families':len(families),'knowledge_documents':len(docs),'pdf_pages':len(pdf.pages),'case_cards':len(cases),'scenarios':len(inputs),'controller_event_rows':len(events),'retrieval_queries':len(q)},'not_run':['PDF image OCR / multimodal extraction','embeddings and pgvector retrieval','scenario execution by Agent','independent historical evaluation','real system actions'],'visual_review':visual}
(OUT/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Review sheets preserve page order. Final visual signoff is recorded separately.
pages=sorted((ROOT/'tmp/pdfs/knowledge-v1').glob('page-*.png'))
for batch in range(0,len(pages),6):
    selected=pages[batch:batch+6];sheet=Image.new('RGB',(1324,3*956),'#c9cfd8');d=ImageDraw.Draw(sheet)
    for k,path in enumerate(selected):
        im=Image.open(path).convert('RGB');im.thumbnail((652,926));x=(k%2)*662;y=(k//2)*956;sheet.paste(im,(x+5,y+23));d.text((x+8,y+5),path.name,fill='black')
    sheet.save(ROOT/f'tmp/pdfs/knowledge-v1/review-{batch//6+1}.png')
print(json.dumps({'passed':report['passed'],'checks':len(checks),'counts':report['counts']},ensure_ascii=False))
if not report['passed']:raise SystemExit(1)
