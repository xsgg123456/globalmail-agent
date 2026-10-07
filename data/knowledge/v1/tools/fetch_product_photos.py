"""Read production product image metadata and download exact-SKU public photos."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from extract_sources import query,write,PRIVATE,OUT,ROOT

families=json.loads((OUT/'families.json').read_text('utf-8'))
skus=[s for f in families for s in f['skus']]
quoted=','.join("'"+s.replace("'","''")+"'" for s in skus)
sql=f"""BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout='15s'; SET LOCAL lock_timeout='1s';
SELECT jsonb_build_object('observed_at',current_timestamp,'read_only',current_setting('transaction_read_only'),
'items',coalesce(jsonb_agg(DISTINCT jsonb_build_object('sku',x->>'sku','title',x->>'title','product_name',x->>'product_name','image_url',x->>'image_url','asin',x->>'asin','asin_url',x->>'asin_url','unit_price',x->>'unit_price','currency',o.order_summary_json::jsonb->'details'->>'currency','country',o.order_summary_json::jsonb->'details'->>'country')),'[]'::jsonb))
FROM order_bindings o CROSS JOIN LATERAL jsonb_array_elements(coalesce(o.order_summary_json::jsonb->'details'->'items','[]'::jsonb)) x
WHERE x->>'sku' IN ({quoted});
ROLLBACK;"""
capture=query(sql);write(OUT/'sources/production-product-images.json',capture)
manifest=[]
for f in families:
    items=[x for x in capture['items'] if x['sku'] in f['skus'] and x.get('image_url')]
    items.sort(key=lambda x:f['skus'].index(x['sku']))
    success=False
    for item in items:
        try:
            url=item['image_url'];u=urlparse(url)
            if u.scheme!='https' or not u.hostname:continue
            req=Request(url,headers={'User-Agent':'Mozilla/5.0'})
            with urlopen(req,timeout=20) as r:
                data=r.read(10*1024*1024+1)
                if len(data)>10*1024*1024:raise ValueError('oversize')
            from PIL import Image
            import io
            image=Image.open(io.BytesIO(data));image.verify()
            ext='png' if data.startswith(b'\x89PNG') else 'jpg' if data.startswith(b'\xff\xd8') else 'webp'
            p=OUT/'assets/photos'/f"{f['family_id']}.{ext}";p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            manifest.append({'family_id':f['family_id'],'brand':f['brand'],'matched_sku':item['sku'],'source_kind':'production_order_product_photo','source_image_url':url,'source_asin_url':item['asin_url'],'source_asin':item['asin'],'source_title':item['title'],'path':str(p.relative_to(OUT)).replace('\\','/'),'sha256':hashlib.sha256(data).hexdigest(),'observed_at':capture['observed_at'],'match_basis':'exact SKU in production order snapshot','other_skus_in_family':'appearance_reference_only_not_exact_variant','visual_review':'pending'})
            success=True;break
        except Exception as e:
            print(json.dumps({'family':f['family_id'],'download_error':type(e).__name__}))
    if not success:manifest.append({'family_id':f['family_id'],'status':'missing_production_photo','candidates':len(items)})
write(OUT/'sources/product-photo-manifest.json',manifest)
print(json.dumps({'production_item_rows':len(capture['items']),'photos':sum('path' in x for x in manifest),'families':[{'family':x['family_id'],'sku':x.get('matched_sku'),'path':x.get('path')} for x in manifest]},ensure_ascii=False))
