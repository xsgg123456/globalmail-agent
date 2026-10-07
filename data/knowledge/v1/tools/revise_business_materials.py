"""Business-facing revision: real product photos, ordinary support language, realistic inputs."""
import copy
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[4];OUT=ROOT/'data/knowledge/v1';PDF=ROOT/'output/pdf/product-manuals-v1.pdf'
def read(p):return json.loads(p.read_text('utf-8'))
def write(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def jl(p):return [json.loads(s) for s in p.read_text('utf-8').splitlines() if s.strip()]
def dump(p,rows):p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
families=read(OUT/'families.json');products=read(OUT/'products.json');copyby=read(OUT/'authoring/business-copy.json')
photos=read(OUT/'sources/product-photo-manifest.json');photoby={p['family_id']:p for p in photos}
imagecapture=read(OUT/'sources/production-product-images.json');items=imagecapture['items'];pby={p['sku']:p for p in products}
for p in products:
    observations=[x for x in items if x['sku']==p['sku']]
    p['listing_observations']=observations
    p['listing_observations_status']='production_order_snapshot_not_current_catalog_or_manufacturer_confirmation'
    p['photo_reference']=photoby[p['family_id']]['path']
    p['photo_match']='exact_sku' if photoby[p['family_id']]['matched_sku']==p['sku'] else 'same_family_appearance_only'
write(OUT/'products.json',products)
# Replace the old authoring prose too, so a later rebuild cannot silently resurrect made-up controls.
authored=read(OUT/'authoring/product-content.json')
for cfg in authored['families']:cfg.update(copyby[cfg['family_id']])
authored['source_kind']='curated_production_support_reference'
authored['notice']='根据生产商品信息与售后往来整理，供客服内部参考，非厂家原版说明书；未核实的操作不作为直接给客户的指导。'
write(OUT/'authoring/product-content.json',authored)

pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/simhei.ttf'))
c=canvas.Canvas(str(PDF),pagesize=(595.28,841.89),invariant=1);c.setTitle('三品牌产品资料与售后参考');c.setAuthor('GlobalMail Agent 项目组')
styles={s:ParagraphStyle(str(s),fontName='CN',fontSize=s,leading=s*1.55,wordWrap='CJK',textColor='#26364a') for s in [9,10,11,13,18,25]}
page=0;y=0
def text(t,size=11,gap=9,x=40,width=515):
    global y
    p=Paragraph(escape(t).replace('\n','<br/>'),styles[size]);w,h=p.wrap(width,730)
    if y-h<62:raise ValueError(f'Overflow page {page}: {t[:30]}')
    p.drawOn(c,x,y-h);y-=h+gap
def start(kicker,title):
    global page,y
    page+=1;c.setFillColorRGB(.06,.16,.25);c.rect(0,760,596,82,fill=1,stroke=0)
    c.setFont('CN',10);c.setFillColorRGB(.65,.78,.97);c.drawString(40,813,kicker)
    c.setFont('CN',18);c.setFillColorRGB(1,1,1);c.drawString(40,781,title);y=735
def finish():
    c.setStrokeColorRGB(.82,.86,.9);c.line(40,50,555,50);c.setFont('CN',9);c.setFillColorRGB(.42,.46,.5)
    c.drawString(40,34,'客服内部整理 | 非厂家原版说明书 | 2026-10-07');c.drawRightString(555,34,str(page).zfill(2));c.showPage()
start('OUTON / OUTONLIFE / BELEEV','产品资料与常见售后问题')
text('以真实商品和客户问题为起点',18,18)
text('本册根据生产订单中的商品信息、实物图片，以及客服和客户的往来整理。用于帮助客服识别产品、理解问题和选择下一步。',11,18)
text('实物图片均来自生产订单关联的商品图。每款图片注明对应商品编码；其他颜色和地区版本只作外观参考，参数与配件仍需按订单核对。',11,18)
text('对尚未拿到有效说明的功能，不编写具体按键顺序、接线方式、紧固参数或拆修步骤。历史个案只说明当时如何处理，不等于整个系列都适用。',11,18)
text('目录',13,10)
for i,f in enumerate(families):text(f"{f['brand']} · {f['name']}  /  {2+i*2}-{3+i*2} 页",11,8)
text('怎样记录处理结果',13,10)
text('客户的问题、已尝试操作、客服建议、补发安排、物流进度和客户确认分别记录。承诺补件不等于已经发货，客户致谢也不一定表示问题已经解决。',11,10)
finish()
for i,f in enumerate(families):
    fid=f['family_id'];b=copyby[fid];photo=photoby[fid]
    start(f['brand']+' / 产品识别',f['name']);text(b['intro'],11,10)
    im=Image.open(OUT/photo['path']);iw,ih=im.size;boxw=330;boxh=285;scale=min(boxw/iw,boxh/ih);w,h=iw*scale,ih*scale
    c.drawImage(str(OUT/photo['path']),40+(515-w)/2,y-h,width=w,height=h,mask='auto');y-=h+10
    text('商品图对应：'+photo['matched_sku']+'。来源：生产订单关联商品图片。',9,4)
    text('同系列其他颜色、地区版本以实际订单为准；图片不能代替装配或维修说明。',9,10)
    text('接到客户问题时先确认',13,8)
    for n,s in enumerate(b['setup'],1):text(f'{n}. {s}',10,6)
    text('本批商品编码',10,5)
    text('、'.join(f['skus']),9,5)
    finish()
    start(f['brand']+' / 售后处理参考',b['symptom'])
    text('处理思路',13,7)
    for n,s in enumerate(b['diagnosis'],1):text(f'{n}. {s}',10,7)
    text('容易弄错的地方',13,7)
    for s in b['operation']:text(s,10,7)
    text('什么时候交给人工',13,7);text(b['stop'],10,10)
    text('英文回复示例',13,7);text(b['reply'],10,12)
    text('资料依据：'+b['basis'],9,5);finish()
    sop=f"# {f['name']}：{b['symptom']}\n\n## 客户问题\n\n{b['intro']}\n\n## 先确认什么\n\n"+'\n'.join(f'{n}. {s}' for n,s in enumerate(b['setup'],1))+"\n\n## 怎么处理\n\n"+'\n'.join(f'{n}. {s}' for n,s in enumerate(b['diagnosis'],1))+"\n\n## 容易弄错的地方\n\n"+'\n'.join('- '+s for s in b['operation'])+f"\n\n## 交给人工的情况\n\n{b['stop']}\n\n## 可以参考的英文回复\n\n{b['reply']}\n\n## 资料依据\n\n{b['basis']}\n\n内部整理，非厂家原版说明。具体商品适用范围由独立资料清单记录；未经确认的维修操作不得直接发送给客户。\n"
    (OUT/'sop'/f'{fid}.md').write_text(sop,encoding='utf-8')
c.save()
for photo in photos:
    photo['visual_review']='reviewed_real_product_appearance_against_production_title'
    photo['reuse_scope']='internal_project_reference; rights remain with source owner'
write(OUT/'sources/product-photo-manifest.json',photos)

# Rewrite customer prose; internal order/part keys stay in server-owned metadata.
scenarios=jl(OUT/'scenarios/inputs.jsonl');events=jl(OUT/'scenarios/controller-events.jsonl');assertions=jl(OUT/'evaluation/scenario-assertions.jsonl')
aby={a['scenario_id']:a for a in assertions};prodbid={p['product_id']:p for p in products}
templates={
1:'Hi, I bought one of your lamps on Amazon and would like to know how to change the brightness. Could you help?',
2:'Hello, the lamp still turns on from the buttons, but the remote has stopped responding. I have already put in fresh batteries. What can I try next?',
3:'Hi, could you check where my parcel is? I have not received it yet and would appreciate an update.',
4:'Hello, I sent the item back and the return tracking says it has arrived. Could you check the refund for me, please?',
5:'Hi, I would like to return this item as it is not suitable for my room. It has not been used and I still have the packaging. What do I need to do?',
6:'Hello, I would prefer a replacement rather than a refund. Please send the same model and colour. My delivery address has not changed.',
7:'Hi, there seems to be a part missing from the box. Could you help arrange a replacement part? I would like to keep the product.'}
custom={
'SCN-002':'Hi, I received one of your lamps as a gift and cannot find the order number. I need help using the controls. What information would help you identify it?',
'SCN-003':'Hello, can I buy a spare handle grip for this scooter? I am not sure which size fits. I am happy to pay for it.',
'SCN-005':'I already changed the batteries and followed the pairing instructions you sent. The remote still does not work. Is there anything else you can do?',
'SCN-006':'The lamp started giving off a burning smell and I noticed some smoke. I have stopped using it. Please let me know what happens next.',
'SCN-008':'Amazon shows two parcels for this order. One has arrived but I am still waiting for the other. Can you check which one the tracking update is for?',
'SCN-009':'The tracking says delivered, but I have checked around the house and with my neighbours and cannot find the parcel. Could you look into this?',
'SCN-011':'You mentioned a partial refund. How much would that be, and would I need to return the lamp? I would like to know before deciding.',
'SCN-012':'I contacted you about a refund before, but I am still not sure what has happened. Could you refund the order, please?',
'SCN-014':'Hi, I need to send something from this order back. Could you tell me how to arrange a return?',
'SCN-015':'I bought the scooter a few months ago and would now like to return it. Is there anything you can do?',
'SCN-017':'Thank you, I would like the replacement. I have moved since I placed the order, so please do not send it to the old address.',
'SCN-018':'I would like the same scooter as a replacement. Please let me know whether it is available before arranging anything else.',
'SCN-019':'The remote control was not in the box when the lamp arrived. Could you send one that works with this lamp? My address is the same as on the order.',
'SCN-020':'There is a small piece missing and I am not sure what it is called. I have attached a photo of where I think it should go. Can you help identify it?',
'SCN-021':'Before you send the replacement, could you check it is the correct version for my lamp? The details in the last message look different from the one I have.',
'SCN-022':'Could you check the parcel for my recent order? I also still need help with the remote on the other lamp I bought earlier.',
'SCN-023':'I have changed my mind about the replacement part. If it has not been sent yet, I would rather return the lamp and get a refund. Please let me know if that is still possible.',
'SCN-024':'I have posted the lamp back. Could you confirm when it arrives and let me know when the refund is being processed?',
'SCN-025':'You arranged a replacement part for me earlier. Has it been sent yet, and is there a tracking number?',
'SCN-026':'I asked for a refund and have not seen a confirmation yet. Could you check whether it has gone through?',
'SCN-027':'Just following up on the part you agreed to send. Do you have any update for me?',
'SCN-028':'I wanted to add some information while your colleague is looking into this. Please keep it with my earlier messages.',
'SCN-029':'Could you check the tracking update for my parcel, please?',
'SCN-030':'I would like a refund for the faulty lamp. Could you also send me a replacement? Please let me know what you can offer.'}
price_sources=[]
for n,sc in enumerate(scenarios,1):
    sid=sc['scenario_id'];p=prodbid[sc['product_id']];s=sc['initial_state'];biz=int(sc['business_categories'][0].split('-')[1]);oldorders=s['orders']
    for j,o in enumerate(oldorders):
        choices=[x for x in items if x['sku']==o['lines'][0]['sku'] and x.get('currency')==o['currency'] and re.fullmatch(r'\d+(?:\.\d+)?',x.get('unit_price') or '')]
        if choices:
            chosen=sorted(choices,key=lambda x:Decimal(x['unit_price']))[len(choices)//2];unit=int(Decimal(chosen['unit_price'])*100);basis='production_observed_unit_price_same_sku_currency'
        else:
            unit=5999 if p['brand']=='BELEEV' else 6999;chosen=None;basis='authored_price_no_matching_snapshot'
        oldpaid=o['paid_minor'];o['display_order_number']=f'999-{7100000+n:07d}-{8100000+j:07d}';o['display_order_number_source']='synthetic_not_a_real_customer_order'
        for line in o['lines']:line['paid_minor']=unit*line['quantity']
        newpaid=sum(l['paid_minor'] for l in o['lines']);o['paid_minor']=newpaid
        if o['refunded_minor']==oldpaid:o['refunded_minor']=newpaid
        o['pricing_source']=basis;o['tax_and_discount_semantics']='fixture amount uses observed item amount as proxy; not a reconstructed real transaction'
        price_sources.append({'scenario_id':sid,'order_id':o['order_id'],'sku':o['lines'][0]['sku'],'currency':o['currency'],'unit_price_minor':unit,'basis':basis,'source_asin':chosen['asin'] if chosen else None})
        def adjust(obj):
            if isinstance(obj,dict):
                for k,v in obj.items():
                    if k in ['amount_minor'] and v==oldpaid:obj[k]=newpaid
                    else:adjust(v)
            elif isinstance(obj,list):
                for v in obj:adjust(v)
        adjust(s['operations']);adjust(s['execution_records']);adjust(s['customer_choices'])
        for e in events:
            if e['scenario_id']==sid:adjust(e['payload'])
        if s.get('refund_proposal'):s['refund_proposal']['amount_minor']=unit*2000//10000
    body=custom.get(sid,templates[biz])
    if p['brand']=='BELEEV' and sid.startswith('BASE'):
        if biz==1:body='Hello, we have just received the scooter. Could you help us find the instructions for adjusting the handlebar height?'
        elif biz==2:body='The wheel and handlebar do not stay aligned. I tried tightening the connection but it keeps coming loose. Could you help?'
        elif biz==5:body='Hi, I would like to return the scooter as it is not suitable for us. It has not been used and the packaging is complete. How do I arrange this?'
        elif biz==7:body='Hi, one of the handle grips was missing when we opened the box. Could you send the correct grip for this scooter?'
    if p['brand']=='OUTONLIFE' and sid.startswith('BASE') and biz==7:body='Hello, one of the fixing pieces for the bookshelf was missing from the box. Could you help us get the correct part?'
    if p['brand']=='OUTON' and sid.startswith('BASE') and biz==7:body='Hi, the lamp arrived without the remote control. Could you arrange to send the correct remote?'
    if oldorders:body+='\n\nAmazon order number: '+oldorders[0]['display_order_number']
    if sid=='SCN-022':body+='\nThe earlier order number is '+oldorders[1]['display_order_number']+'.'
    body+='\n\nThank you.'
    sc['initial_messages'][-1]['body']=body
    if sid=='SCN-020':sc['initial_messages'][-1]['attachment_metadata']=[{'name':'missing-part.jpg','content_available':False}]
    sc['business_text_source']='paraphrased_common_support_language_no_real_identity';sc['internal_keys_must_not_appear_in_customer_reply']=True
    aby[sid]['title']=body.split('\n')[0]
    if sid=='BASE-BELEEV-02':aby[sid]['expected_actions']=['record_failed_tightening','stop_use_guidance','human_review'];aby[sid]['forbidden_actions']=['repeat_tightening','invent_torque','ask_child_to_ride']
    if sid in ['SCN-002','SCN-003','SCN-023']:sc['initial_state']['customer_choices']=[] if sid!='SCN-023' else sc['initial_state']['customer_choices']
    # Controller human language is normal too; fault details remain in the controller file.
dump(OUT/'scenarios/inputs.jsonl',scenarios);dump(OUT/'scenarios/controller-events.jsonl',events);dump(OUT/'evaluation/scenario-assertions.jsonl',assertions)
write(OUT/'sources/scenario-price-basis.json',price_sources)
# Keep technical trace fields in JSON; the readable case cards use service-team language.
outcome_labels={'replacement_promised_delivery_and_resolution_unknown':'客服已答应安排补件；没有证据确认已发货、已收货或问题已解决。','purchase_guidance_given_resolution_unknown':'客服已说明配件购买方式；客户是否下单、是否解决问题仍未知。','order_obtained_accessory_availability_unknown':'客户已补充原订单号；后续是否找到或购买配件仍未知。','customer_reported_resolved':'客户明确表示按指导操作后已经恢复；最终是否关闭会话仍由客服确认。','evidence_requested_resolution_unknown':'客服已请求补充资料；没有后续诊断或修复结果。'}
for case in jl(OUT/'cases/reviewed-summaries.jsonl'):
    card=f"# {case['title']}\n\n## 客户遇到了什么\n\n{case['problem']}\n\n## 往来过程\n\n"+'\n'.join(f"{i}. {'客户' if t['direction']=='INBOUND' else '客服'}：{t['summary']}" for i,t in enumerate(case['timeline'],1))+f"\n\n## 最后看到了什么结果\n\n{outcome_labels[case['outcome']]}\n\n## 处理时可以借鉴什么\n\n{case['lesson']}\n\n## 还不能确定什么\n\n"+'\n'.join('- '+s for s in case['limitations'])+'\n\n根据真实往来重新概括，身份信息已移除。具体消息来源与时间保存在独立记录中；此案例不代替当前订单的政策或执行记录。\n'
    card=card.replace('HITL','人工接管').replace('SKU','商品编码')
    (OUT/'cases'/f"{case['document_id']}.md").write_text(card,encoding='utf-8')
policy=read(OUT/'policies/policy-profile.json')
policytext=f"""# 售后处理规则（内部演练草案）

本稿用于本项目业务演练，尚不是三品牌的正式售后承诺，也不代表销售平台或所在地区的现行要求。规则版本：{policy['version']}。

## 适用范围

适用于 OUTON、OUTONLIFE、BELEEV，在美国、英国、德国、加拿大、澳大利亚的 Amazon 与品牌自营渠道演练订单。只处理订单原币种，不自行换算。其他市场或渠道交客服核实。

## 接到来信后

先查看已有往来，复用订单号、商品信息、客户已经做过的操作和已确认的选择。需要安排退款、退换或补件时，必须明确是哪件商品、数量和客户希望的方案。缺少信息先补问，不直接拒绝申请。

## 退货

签收后 {policy['return']['window_days_after_delivery']} 天内（含第 {policy['return']['window_days_after_delivery']} 天）核对退货原因。非质量问题要求商品未使用且配件完整，由客户安排寄回邮资；质量问题的退货标签费用由商家承担。未取得有效退货资料前，不编造仓库地址或退货标签。

超过窗口、收件或验货有争议时交客服处理。签收时间不清楚时先核实，不拿下单日期直接代替。

## 退款

全额退款默认在退件签收且验货通过后安排。可退金额以商品行实付为基础，减去已成功退款和正在处理的退款金额。不能重复退款，不能把整笔订单金额当作其中一件商品的金额。

部分退款方案最高为对应商品实付的 {policy['refund']['partial_offer_max_basis_points']/100:g}%。先告诉客户具体金额和币种，取得明确同意后再提交；客户询问金额、表达不满或没有回复，都不算接受。

客服在原销售渠道执行退款后，再依据实际回执通知客户。申请已提交不等于款项已退，不承诺未经确认的到账时间。不退货退款等例外由客服处理。

## 换货

质量问题在签收后 {policy['replacement']['defect_window_days_after_delivery']} 天内核对资格。默认更换相同商品编码的产品，确认有库存、收件地址无误，并在退件验货通过后安排换出。缺货时先说明情况，不擅自改颜色、地区版本或型号。

客户改变地址后重新确认；原地址确认不能继续沿用。需要先发后退或替代型号的情况由客服确认。

## 补寄配件

质量问题在签收后 {policy['spare_part']['defect_window_days_after_delivery']} 天内核对资格。先明确缺失或损坏部件、适配商品、库存和收件信息，再安排补寄。购买备用配件不自动成为免费补寄申请。

滑板车锁止、轮轴、刹车和电气拆修等安全相关问题交人工。不能按相似外形认定配件通用。

## 物流与后续跟进

查询本次订单和本次处理事项对应的包裹。连续 {policy['logistics']['stale_tracking_days']} 天未更新时进入查件判断；显示签收但客户未收到时先核对包裹并处理争议，不直接认定客户已经收货。

生成单号或物流标签不等于承运商已收件。不保证未经承运商确认的到货日期。查询失败、还没同步和确实没有记录分别说明。

## 客户改方案或重复催问

先查询原申请和已执行记录。客户从补件改成退款时，检查补件能否取消以及是否已经产生补偿。对同一件商品同时要求退款和换货时先澄清，不同时安排两份补偿。

如果操作结果不确定，查询原申请，不重新创建一笔碰运气。客户催问时沿用已知订单和处理记录。

## 交给人工与结案

资料不足、处理多次无效、政策冲突、安全异常或客户要求例外时交人工。接管期间继续保存新邮件和业务消息，不自动抢答。客服回复后，下一封客户来信再恢复自动处理。

最终是否解决由客服确认。客户说“谢谢”、申请通过或补件单创建，都不能单独作为问题已经解决的依据。
"""
(OUT/'policies/policy-profile.md').write_text(policytext,encoding='utf-8')
write(OUT/'sources/policy-render.json',{'canonical_sha256':hashlib.sha256((OUT/'authoring/policy-profile.json').read_bytes()).hexdigest(),'readable_sha256':hashlib.sha256((OUT/'policies/policy-profile.md').read_bytes()).hexdigest(),'generated_by':'tools/revise_business_materials.py','rule_version':policy['version']})
# Customer-sounding mail examples for direct review, without exposing control metadata.
preview='# 客户来信示例\n\n以下均为基于真实售后表达重新编写的演练来信，订单号为虚构；不是原始客户邮件。\n\n'
for sid in ['SCN-004','SCN-005','SCN-011','SCN-017','SCN-020','SCN-023','SCN-025','SCN-030']:
    sc=next(x for x in scenarios if x['scenario_id']==sid);preview+='## '+sid+'\n\n'+sc['initial_messages'][-1]['body']+'\n\n'
(OUT/'scenarios/customer-mail-examples.md').write_text(preview,encoding='utf-8')
docs=read(OUT/'documents.json')
for d in docs:
    if d['document_type'] in ['manual_pdf','troubleshooting_md']:
        d['source_kind']='curated_production_support_reference';d['title']=d['title'].replace('模拟说明','产品与售后参考');d['content_basis']='production product listing/photo plus curated correspondence; no manufacturer certification'
    d['source_hash']=hashlib.sha256((OUT/d['path']).resolve().read_bytes()).hexdigest()
write(OUT/'documents.json',docs)
manifest=read(OUT/'sources/build-manifest.json');manifest.update(pdf_hash=hashlib.sha256(PDF.read_bytes()).hexdigest(),real_product_photos=8,synthetic_diagrams_used=0,business_revision='realistic_v2');write(OUT/'sources/build-manifest.json',manifest)
write(OUT/'sources/business-review.json',{'status':'rewritten_pending_final_checks','photo_count':8,'photo_basis':'exact SKU in current production order snapshot','customer_text_contains_internal_codes':False,'prices_from_production_observations':sum(x['basis'].startswith('production_') for x in price_sources),'price_rows':len(price_sources),'known_gaps':['No manufacturer approved repair manual','Price proxies not full historical tax/discount reconstruction','Stock and policy values remain authored simulation data','Public product name can refer to a different revision'],'removed':['schematic drawings in delivered manual','invented remote target-switch sequence','SIM-V1 and RAG terminology in business prose']})
print(json.dumps({'pdf_pages':page,'real_photos':len(photos),'realistic_mail_scenarios':len(scenarios),'production_based_prices':sum(x['basis'].startswith('production_') for x in price_sources),'price_rows':len(price_sources)},ensure_ascii=False))
