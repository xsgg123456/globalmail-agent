"""Produce a private review copy; NOT an export or a privacy approval."""
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'data/knowledge/v1'
PRIVATE=ROOT/'.local-data/knowledge-v1'

def scrub(text, name):
    if name:
        for token in [name]+name.split():
            if len(token)>2: text=re.sub(re.escape(token),'[PERSON]',text,flags=re.I)
    text=re.split(r'(?im)^\s*(?:from:|sent:|on .+ wrote:|发件人[:：]|寄件者[:：]|-----Original)',text)[0]
    text=re.sub(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}','[EMAIL]',text,flags=re.I)
    text=re.sub(r'https?://\S+','[URL]',text)
    text=re.sub(r'\b\d{3}-\d{7}-\d{7}\b','[ORDER]',text)
    text=re.sub(r'(?:\+?\d[\d() .-]{7,}\d)','[NUMBER]',text)
    text=re.sub(r'(?im)^.*(?:address:|phone:|telephone:|street|postcode|postal code|zip code|shipping address|delivery address).*$','[CONTACT_LINE]',text)
    text=re.split(r'(?im)^\s*(?:best regards|kind regards|sincerely|regards)[,!]?\s*$',text)[0]
    return text

manifest=json.loads((OUT/'sources/case-manifest.json').read_text('utf-8'))
raw=json.loads((PRIVATE/'case-source.json').read_text('utf-8'))
cases={x['id']:x for x in raw['cases']}
selected=[]
for brand in ['OUTON','OUTONLIFE','BELEEV']:
    rows=[x for x in manifest if x['brand']==brand and x['usage_split']=='rag_candidate']
    rows.sort(key=lambda x:(not x['complete_history_candidate'],not bool(x['selected_family_ids']),-x['message_count']))
    selected.extend(rows[:2])
review=[]
for row in selected:
    c=cases[row['source_conversation_id']]
    review.append({**row,'messages':[{'id':m['id'],'direction':m['direction'],'at':m['at'],'attachments_unread':m['attachments_unread'],'text_source':m['text_source'],'text':scrub(m['text'],c['customer_name'])} for m in c['messages']]})
(PRIVATE/'review-six.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
for r in review:
    print(json.dumps({k:r[k] for k in ['case_id','brand','registration_skus','selected_family_ids','source_conversation_id']},ensure_ascii=False))
    for m in r['messages']:
        print(json.dumps({**m,'text':m['text'][:1800]},ensure_ascii=False))

