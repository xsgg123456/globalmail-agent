"""Read-only production capture. Private text/key stay under ignored .local-data."""
import hashlib
import hmac
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'data/knowledge/v1'
PRIVATE = ROOT / '.local-data/knowledge-v1'
CAT = ROOT / 'data/preparation/2026-10-07'

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def query(sql):
    cmd = ['ssh', '-i', str(Path.home()/'.ssh/hengxin_smartmail_uat'), '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', '-o', 'StrictHostKeyChecking=yes', 'root@192.168.1.247', 'docker exec -i hengxin-smartmail-uat-postgres-1 psql -X -v ON_ERROR_STOP=1 -qAt -U smartmail -d smartmail']
    result = subprocess.run(cmd, input=sql, text=True, encoding='utf-8', capture_output=True, timeout=90)
    if result.returncode:
        (PRIVATE/'query-error.txt').write_text(result.stderr, encoding='utf-8')
        raise RuntimeError('Production read-only query failed; inspect stderr locally. No data printed.')
    return json.loads(result.stdout)

def main():
    PRIVATE.mkdir(parents=True, exist_ok=True)
    keyfile = PRIVATE/'pseudonym.key'
    if not keyfile.exists():
        keyfile.write_bytes(os.urandom(32))
    key = keyfile.read_bytes()
    def token(kind, value):
        return kind + '-' + hmac.new(key, str(value).strip().lower().encode(), hashlib.sha256).hexdigest()[:20]
    catalog = query((CAT/'catalog-query.sql').read_text(encoding='utf-8'))
    write(PRIVATE/'live-catalog.json', catalog)
    queue = json.loads((CAT/'case-review-queue.json').read_text(encoding='utf-8'))
    wanted = [x for x in queue if x['scope_status']=='target_product_candidate']
    ids = ','.join("'"+x['conversation_id']+"'::uuid" for x in wanted)
    sql = f"""BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout='20s'; SET LOCAL lock_timeout='1s';
SELECT jsonb_build_object('captured_at',current_timestamp,'read_only',current_setting('transaction_read_only'),
'cases',coalesce(jsonb_agg(jsonb_build_object(
'id',c.id,'customer_email',c.customer_email,'customer_name',c.customer_name,'first_status',c.first_status,
'workflow_status',c.workflow_status,
'orders',(SELECT coalesce(jsonb_agg(DISTINCT r.order_number),'[]'::jsonb) FROM after_sales_registrations r WHERE r.conversation_id=c.id),
'messages',(SELECT coalesce(jsonb_agg(jsonb_build_object('id',m.id,'direction',m.direction,
'at',coalesce(m.sent_at,m.received_at,m.created_at),'attachments_unread',m.has_non_inline_attachment,
'text',coalesce(nullif(trim(ec.current_reply_plain_text),''),nullif(trim(ec.full_plain_text),''),ec.ai_plain_text,''),
'text_source',CASE WHEN nullif(trim(ec.current_reply_plain_text),'') IS NOT NULL THEN 'current_reply_plain_text' WHEN nullif(trim(ec.full_plain_text),'') IS NOT NULL THEN 'full_plain_text' ELSE 'ai_plain_text' END
) ORDER BY coalesce(m.sent_at,m.received_at,m.created_at),m.id),'[]'::jsonb)
FROM email_messages m LEFT JOIN email_contents ec ON ec.message_id=m.id
WHERE m.conversation_id=c.id AND NOT m.is_auto_reply AND m.sensitive_data_deleted_at IS NULL)
) ORDER BY c.id),'[]'::jsonb))
FROM mail_conversations c WHERE c.id IN ({ids}) AND c.lifecycle_status::text='ACTIVE' AND NOT c.is_irrelevant AND c.sensitive_data_deleted_at IS NULL;
ROLLBACK;"""
    capture = query(sql)
    write(PRIVATE/'case-source.json', capture)
    cases = capture['cases']
    parents = {c['id']:c['id'] for c in cases}
    def root(x):
        while parents[x] != x:
            parents[x] = parents[parents[x]]; x=parents[x]
        return x
    def join(a,b):
        a,b=root(a),root(b)
        if a!=b: parents[max(a,b)]=min(a,b)
    identity_owner = {}
    signatures = {}
    for c in cases:
        identities = [token('customer', c['customer_email'] or c['id'])] + [token('order',o) for o in c['orders'] if o]
        for identity in identities:
            if identity in identity_owner: join(c['id'],identity_owner[identity])
            else: identity_owner[identity]=c['id']
        first = next((m['text'] for m in c['messages'] if m['direction']=='INBOUND'),'')
        first = re.split(r'(?im)^\s*(?:from:|sent:|on .+ wrote:|发件人[:：]|寄件者[:：])',first)[0]
        words = re.findall(r'[a-z]{3,}',first.lower())
        signatures[c['id']] = {tuple(words[i:i+5]) for i in range(max(0,len(words)-4))}
    for a in cases:
        for b in cases:
            if a['id']>=b['id']: continue
            sa,sb=signatures[a['id']],signatures[b['id']]
            if min(len(sa),len(sb))>=30 and len(sa & sb)/len(sa | sb)>=0.85: join(a['id'],b['id'])
    meta = {x['conversation_id']:x for x in wanted}
    manifest=[]
    for c in cases:
        group = token('group',root(c['id']))
        bucket = int(hashlib.sha256(group.encode()).hexdigest()[:8],16)%10
        split = 'rag_candidate' if bucket<6 else 'dev_candidate' if bucket<8 else 'eval_holdout'
        row = {k:meta[c['id']][k] for k in ['brand','selected_family_ids','registration_skus','complete_history_candidate']}
        row.update(case_id=token('case',c['id']),source_conversation_id=c['id'],customer_key=token('customer',c['customer_email'] or c['id']),group_id=group,usage_split=split,message_count=len(c['messages']),captured_at=capture['captured_at'],privacy_review='pending',indexable=False,source_read_only=capture['read_only'])
        manifest.append(row)
    write(OUT/'sources/case-manifest.json',manifest)
    families=json.loads((CAT/'selected-product-families.json').read_text(encoding='utf-8'))
    # Keep the full current catalog in controlled storage; publish selected product metadata only.
    write(OUT/'sources/capture.json',{'captured_at':capture['captured_at'],'read_only':capture['read_only'],'case_count':len(cases),'message_count':sum(len(c['messages']) for c in cases),'raw_sha256':hashlib.sha256((PRIVATE/'case-source.json').read_bytes()).hexdigest(),'catalog_keys':list(catalog),'grouping':'customer + registered order + first-inbound 5-word shingle Jaccard >=0.85; remaining near-duplicate review pending','raw_storage':'.local-data/knowledge-v1 (gitignored)','available_for_historical_eval':False})
    print(json.dumps({'read_only':capture['read_only'],'cases':len(cases),'messages':sum(len(c['messages']) for c in cases),'splits':{s:sum(m['usage_split']==s for m in manifest) for s in ['rag_candidate','dev_candidate','eval_holdout']},'catalog_keys':list(catalog)},ensure_ascii=False))

if __name__=='__main__': main()
