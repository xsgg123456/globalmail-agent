"""Offline, reproducible material build. No model API, no production writes."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'data/knowledge/v1'
PRIVATE=ROOT/'.local-data/knowledge-v1'
PDF=ROOT/'output/pdf/product-manuals-v1.pdf'
VERSION='1.0.0'
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def md(path,text):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text.rstrip()+'\n',encoding='utf-8')
def jsonl(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def diagram(cfg, path):
    # Schematic authored as diagram primitives; not a photo of the production product.
    im=Image.new('RGB',(1500,670),'#f4f7fb'); d=ImageDraw.Draw(im)
    font=ImageFont.truetype('C:/Windows/Fonts/simhei.ttf',30)
    small=ImageFont.truetype('C:/Windows/Fonts/simhei.ttf',24)
    ink='#233d59'; accent='#2563eb'
    shape=cfg['shape']; cx=610
    if shape.startswith('scooter'):
        d.line([(440,155),(590,155),(535,155),(560,440),(895,440)],fill=ink,width=16)
        d.line([(560,440),(590,490)],fill=ink,width=14)
        for x in [590,880]: d.ellipse((x-42,460,x+42,544),outline=ink,width=12)
        if shape=='scooter3': d.ellipse((620,482,680,542),outline=accent,width=8)
        d.line([(830,435),(864,420),(910,444)],fill=accent,width=8)
        anchors=[(535,155),(550,300),(710,440),(880,505)]
    elif shape=='shelf':
        d.rectangle((565,120,595,535),fill=ink)
        for y in [190,280,370,460]:
            d.line([(420,y-60),(580,y),(760,y-65)],fill=ink,width=14)
        d.rectangle((410,535,760,555),fill=ink);d.ellipse((540,65,625,130),fill='#f0ba48')
        anchors=[(590,90),(760,215),(580,400),(700,545)]
    elif shape=='table':
        d.rectangle((420,305,850,330),fill=ink)
        d.line([(450,330),(450,565)],fill=ink,width=12);d.line([(820,330),(820,565)],fill=ink,width=12)
        d.rectangle((485,385,775,490),outline=accent,width=8)
        d.line([(620,300),(620,190)],fill=ink,width=12)
        d.polygon([(550,100),(690,100),(750,190),(490,190)],outline=ink,width=10)
        anchors=[(620,140),(840,320),(770,430),(820,535)]
    else:
        d.line([(cx,180),(cx,530)],fill=ink,width=13)
        if shape=='tripod':
            for x in [445,620,790]:d.line([(cx,380),(x,565)],fill=ink,width=12)
            d.ellipse((470,340,755,375),outline=accent,width=8)
            d.polygon([(520,80),(700,80),(760,200),(460,200)],outline=ink,width=10)
            anchors=[(610,140),(755,358),(790,550),(620,455)]
        else:
            d.ellipse((490,110,730,175),outline=ink,width=10)
            d.ellipse((465,530,760,560),outline=ink,width=10)
            if shape=='dual':
                d.line([(cx,320),(775,235)],fill=ink,width=12); d.ellipse((755,200,845,240),outline=accent,width=8)
                anchors=[(610,140),(795,220),(610,400),(715,547)]
            else: anchors=[(610,140),(610,310),(720,547),(610,465)]
    for idx,((x,y),label) in enumerate(zip(anchors,cfg['diagram_labels']),1):
        labely=90+(idx-1)*125
        d.line([(x,y),(1010,labely+18)],fill=accent,width=3)
        d.ellipse((990,labely-1,1030,labely+39),fill=accent)
        d.text((1000,labely+1),str(idx),fill='white',font=font)
        d.text((1045,labely+2),label,fill=ink,font=font)
    # Text exists only inside this image, enabling later image-extraction evaluation.
    d.text((35,605),f"图内标记：{cfg['family_id']}-FIG-A；仅作位置示意，不提供尺寸或装配方向。",font=small,fill=ink)
    path.parent.mkdir(parents=True,exist_ok=True);im.save(path)

class Manual:
    def __init__(self):
        PDF.parent.mkdir(parents=True,exist_ok=True)
        pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/simhei.ttf'))
        self.c=canvas.Canvas(str(PDF),pagesize=(595.28,841.89),invariant=1)
        self.c.setTitle('三品牌产品资料册 - 项目模拟资料 v1.0.0')
        self.c.setAuthor('GlobalMail Agent 项目组')
        self.styles={size:ParagraphStyle(str(size),fontName='CN',fontSize=size,leading=size*1.5,textColor='#26364a',wordWrap='CJK') for size in [9,10,11,13,18,25]}
        self.page=0
    def start(self, label, title):
        self.page+=1; c=self.c
        c.setFillColorRGB(.07,.16,.27);c.rect(0,760,596,82,fill=1,stroke=0)
        c.setFillColorRGB(.65,.78,.97);c.setFont('CN',10);c.drawString(40,813,label)
        c.setFillColorRGB(1,1,1);c.setFont('CN',18);c.drawString(40,781,title)
        self.y=735
    def text(self,text,size=11,space=10):
        p=Paragraph(escape(text).replace('\n','<br/>'),self.styles[size]); w,h=p.wrap(515,720)
        if self.y-h<62: raise ValueError(f'PDF overflow page {self.page}: {text[:25]}')
        p.drawOn(self.c,40,self.y-h);self.y-=h+space
    def heading(self,text): self.text(text,13,8)
    def finish(self):
        c=self.c;c.setStrokeColorRGB(.8,.85,.9);c.line(40,50,555,50)
        c.setFont('CN',9);c.setFillColorRGB(.4,.45,.5)
        c.drawString(40,34,'项目模拟资料 | 非厂家说明书 | 仅限隔离测试 | v1.0.0')
        c.drawRightString(555,34,f'{self.page:02d}');c.showPage()
    def save(self): self.c.save()

def build():
    catalog=read(PRIVATE/'live-catalog.json')
    selected=read(ROOT/'data/preparation/2026-10-07/selected-product-families.json')
    authored=read(OUT/'authoring/product-content.json')
    policy=read(OUT/'authoring/policy-profile.json')
    capture=read(OUT/'sources/capture.json')
    available=capture['captured_at']
    bykey={(p['brand'],p['sku']):p for p in catalog['products']}
    cfgs={x['family_id']:x for x in authored['families']}
    products=[];families=[];parts=[];compat=[];stocks=[];docs=[];bindings=[];queries=[]
    def doc(id,title,type,path,brand,family=None,pages=None,source='synthetic_project_knowledge'):
        row={'document_id':id,'version':VERSION,'title':title,'document_type':type,'path':path,'brand':brand,'family_id':family,'source_kind':source,'allowed_modes':['simulation'],'usage_split':'rag','available_at':available,'status':'prepared_not_indexed','language':'zh-CN','source_hash':None}
        if pages:row['page_range']=pages
        docs.append(row);return row
    def bind(docid,skus,section='all',basis='explicit_project_simulation_assignment'):
        bindings.append({'binding_id':f'BIND-{len(bindings)+1:03d}','document_id':docid,'document_version':VERSION,'section_id':section,'skus':skus,'basis':basis,'allowed_modes':['simulation'],'hardware_revision':'SIM-V1' if basis.startswith('explicit_project') else None,'status':'active_simulation_only','available_at':available})
    book=Manual();book.start('GLOBALMAIL / KNOWLEDGE PACK','三品牌产品与排障资料册')
    book.text('生产商品原型 + 项目模拟操作规则',18,18)
    book.text(authored['notice'],11,18)
    book.heading('阅读与引用规则')
    for s in ['每个产品族占两页：商品范围与示意图、操作和排障。实际地区/结构差异始终以精确 SKU 为入口。','图中编号用于识别部位，不代表尺寸、零件兼容或实际装配方向；不得据图指导拆解电气或安全部件。','本册模拟硬件版本为 SIM-V1。生产型号、功率、电压、承重、扭矩和年龄未知时保留未知。','产品族关系只用于组织资料。后续 RAG 以 knowledge-bindings.json 的明确 SKU 列表限定章节，不将整本 PDF 绑定给全部商品。','图片中的“图内标记”仅存在于图片像素，后续 PDF 解析需能定位页码与图号；本次只检查文档生成，不宣称完成多模态入库。']:
        book.text(s,11,12)
    book.heading('产品目录')
    for idx,f in enumerate(selected):book.text(f"{f['brand']} · {f['name']} / 第 {2+idx*2}-{3+idx*2} 页",10,4)
    book.finish()
    for idx,f in enumerate(selected):
        cfg=cfgs[f['family_id']]; fid=f['family_id']; start=2+idx*2
        families.append({'family_id':fid,'brand':f['brand'],'name':f['name'],'category_id':cfg['category_id'],'grouping_basis':'production_names_and_project_selection_not_compatibility','skus':f['skus']})
        for si,sku in enumerate(f['skus'],1):
            src=bykey[(f['brand'],sku)]
            product={'product_id':f'{fid}-SKU-{si:02d}','brand':f['brand'],'sku':sku,'family_id':fid,'category_id':cfg['category_id'],'registered_names':src['product_names'],'observed_sites':src['sites'],'source_registration_ids':src['registration_ids'],'identity_source':'production_registration','identity_observed_at':catalog['observed_at'],'manufacturer_model':None,'manufacturer_hardware_revision':None,'simulation_hardware_revision':'SIM-V1','unverified_parameters':{'voltage':None,'power':None,'load_capacity':None,'torque':None,'age_range':None},'specification_hint':next((t for t in ['US','UK','EU','AU'] if f'-{t}-' in sku),None),'specification_hint_source':'sku_token_only_not_verified_rating'}
            products.append(product)
            stocks.append({'inventory_id':'INV-'+sku,'item_id':sku,'on_hand':5,'reserved':0,'warehouse_id':'SIM-WH-01','source_kind':'synthetic','snapshot_at':'2026-10-08T09:00:00+08:00'})
            for part in cfg['parts']:
                pid=f"SIM-{fid}-{part['code']}-{si:02d}"
                parts.append({'part_id':pid,'name':part['name'],'source_kind':'synthetic_project_part','customer_replaceable':part['customer_replaceable'],'safety_critical':not part['customer_replaceable'],'brand':f['brand']})
                compat.append({'part_id':pid,'sku':sku,'hardware_revision':'SIM-V1','source_kind':'synthetic_project_compatibility','allowed_modes':['simulation'],'status':'compatible_in_simulation','cross_sku_substitution':False})
                stocks.append({'inventory_id':'INV-'+pid,'item_id':pid,'on_hand':8,'reserved':0,'warehouse_id':'SIM-WH-01','source_kind':'synthetic','snapshot_at':'2026-10-08T09:00:00+08:00'})
        photo=next(p for p in read(OUT/'sources/product-photo-manifest.json') if p['family_id']==fid)
        img=OUT/photo['path']
        book.start(f"{f['brand']} / {fid} / SIM-V1",f['name'])
        book.text(cfg['intro'],11,10)
        book.heading('适用范围：仅以下 SKU 的模拟版本')
        for line in [', '.join(f['skus'][i:i+2]) for i in range(0,len(f['skus']),2)]:book.text(line,10,3)
        book.text('真实额定参数及厂家硬件版本：未知。请勿从地区后缀推算电压、功率或配件兼容。',10,12)
        height=230;book.c.drawImage(str(img),40,book.y-height,width=515,height=height,mask='auto');book.y-=height+12
        book.text(f"图 {fid}-FIG-A：结构部位示意，非实物装配图。关键图内标签需在 PDF 图像解析时单独核验。",9,12)
        book.heading('启用前检查')
        for i,s in enumerate(cfg['setup'],1):book.text(f'{i}. {s}',10,6)
        book.finish()
        book.start(f"{f['brand']} / {fid} / 操作与排障",cfg['symptom'])
        book.heading('模拟操作规则')
        for i,s in enumerate(cfg['operation'],1):book.text(f'{i}. {s}',10,7)
        book.heading('排查与下一步')
        for i,s in enumerate(cfg['diagnosis'],1):book.text(f'{i}. {s}',10,7)
        book.heading('停止条件')
        book.text(cfg['stop'],11,15)
        book.heading('结果记录')
        book.text('记录客户已尝试步骤、结果、所用资料版本和未确定信息。申请、建单、发货、收货与客户确认解决分别记录；最终结案由人工完成。',10)
        book.text('视频仍为题名候选。配件的精确 SKU 适配、人工更换要求及库存，分别查询 compatibility.json 与 inventory.json。',10)
        book.finish()
        did=f'MAN-{fid}';doc(did,f['name']+'模拟说明','manual_pdf','../../../output/pdf/product-manuals-v1.pdf',f['brand'],fid,[start,start+1]);bind(did,f['skus'],fid)
        sid=f'SOP-{fid}';sp=OUT/'sop'/f'{fid}.md'
        text=f"# {f['name']}：{cfg['symptom']}\n\n资料 ID：{sid}；版本：{VERSION}；来源：项目模拟；仅限 simulation。\n适用范围以 knowledge-bindings.json 为准，硬件版本 SIM-V1。\n\n## 前提\n\n订单及目标商品行已明确，品牌和 SKU 已核对；未读附件不能作为诊断证据。\n\n## 操作依据\n\n"+'\n'.join(f'{i}. {s}' for i,s in enumerate(cfg['operation'],1))+"\n\n## 决策步骤\n\n"+'\n'.join(f'{i}. {s}' for i,s in enumerate(cfg['diagnosis'],1))+f"\n\n## 停止与人工接管\n\n{cfg['stop']}\n\n## 记录与跟进\n\n保留原始诉求、已尝试步骤、每一步结果、资料版本与待办号。缺少可补信息先补问；无可靠下一步才 HITL。正常人工执行补发后查询本次待办关联记录，HITL 期间事件只记录。\n\n## 非适用情况\n\n其他品牌、未列入绑定的 SKU、真实生产商品未知硬件版本。不得将本资料用于真实客户操作或历史准确率评测。\n"
        md(sp,text);doc(sid,f['name']+'排障 SOP','troubleshooting_md',f'sop/{fid}.md',f['brand'],fid);bind(sid,f['skus'])
        for lang in ['en','de']:
            queries.append({'query_id':f'RQ-{fid}-{lang}','usage_split':'dev','mode':'simulation','brand':f['brand'],'sku':f['skus'][0],'query':cfg['query_'+lang],'expected_document_ids':[sid,did],'must_exclude':[f'SOP-{other["family_id"]}' for other in selected if other['family_id']!=fid],'expected_top_k':5,'execution_status':'not_run'})
        queries.append({'query_id':f'RQ-{fid}-unknown','usage_split':'dev','mode':'simulation','brand':f['brand'],'sku':'UNKNOWN-SKU','query':cfg['query_en'],'expected_document_ids':[],'must_exclude':[sid,did],'expected_behavior':'ask_product_identity_no_cross_sku_fallback','execution_status':'not_run'})
    book.save()
    write(OUT/'products.json',products);write(OUT/'families.json',families);write(OUT/'parts.json',parts);write(OUT/'compatibility.json',compat);write(OUT/'inventory.json',stocks)
    write(OUT/'sources/product-snapshot.json',{'observed_at':catalog['observed_at'],'transaction_read_only':catalog['transaction_read_only'],'products':[bykey[(p['brand'],p['sku'])] for p in products]})
    videos=[]
    for v in catalog['videos']:
        videos.append({**v,'content_reviewed':False,'approved_skus':[],'indexable':False,'status':'directory_only'})
    write(OUT/'video-directory.json',videos)
    write(OUT/'policies/policy-profile.json',policy)
    # Render every canonical rule, so readable policy cannot quietly diverge from JSON.
    poltext=f"# 模拟售后政策 {policy['policy_id']}\n\n版本：{VERSION}。{policy['notice']}\n\n本文件从 authoring/policy-profile.json 生成，不手工维护第二份数值。时间窗口按确认签收时间计算，缺签收时间为未知，不按付款日期替代。\n\n"
    poltext+='## 业务说明\n\n'
    poltext+=f"- 退货：确认签收后 {policy['return']['window_days_after_delivery']} 天内（含边界）按原因判断；非质量退货要求未使用且配件完整，客户自行安排寄回邮资，系统不编造邮费报价；质量问题由商家承担标签费用。超窗口转人工。\n"
    poltext+='- 全额退款：先确认退件签收及质检通过；可退金额为商品行实付减已成功退款和处理中占用金额。只建立内部申请，人工模拟执行后凭成功回执答复，不承诺到账天数。\n'
    poltext+=f"- 部分退款：模拟报价上限为商品行实付的 {policy['refund']['partial_offer_max_basis_points']/100:g}%；客户须明确接受金额与币种，不能把询价或沉默视为同意。\n"
    poltext+=f"- 换货：缺陷场景在确认签收后 {policy['replacement']['defect_window_days_after_delivery']} 天内检查资格；默认同 SKU、有库存、地址已确认、退件质检通过后换出；替代型号需另行确认及人审。\n"
    poltext+=f"- 补件：缺陷场景在确认签收后 {policy['spare_part']['defect_window_days_after_delivery']} 天内核对资格、部件兼容、库存和地址；安全相关部件转人工，购买咨询不等于免费补寄资格。\n"
    poltext+=f"- 物流：超过 {policy['logistics']['stale_tracking_days']} 天未更新进入查件判断；显示签收但未收到时先核对包裹，再处理争议。生成标签不等于发货。\n"
    poltext+='- 人审：接管期间邮件和业务事件只入库；人工回复后的下一封客户来信恢复 Agent。退款、换货、补件冲突需澄清，同一事项不得重复补偿。\n\n'
    translations={'return':'退货','refund':'退款','replacement':'换货','spare_part':'补寄配件','logistics':'物流','conflicts':'冲突处理','human_review':'人工接管','identity':'订单与选择'}
    for key,val in policy.items():
        if isinstance(val,dict):
            poltext+=f"## {translations.get(key,key)}\n\n| 字段 | 值 |\n|---|---|\n"+''.join(f"| {k} | {json.dumps(v,ensure_ascii=False)} |\n" for k,v in val.items())+'\n'
        else:poltext+=f"- {key}：{json.dumps(val,ensure_ascii=False)}\n"
    md(OUT/'policies/policy-profile.md',poltext)
    doc('POL-SIM-V1','模拟售后政策说明','policy_md','policies/policy-profile.md',None)
    bindings.append({'binding_id':'BIND-POL','document_id':'POL-SIM-V1','document_version':VERSION,'section_id':'all','brands':policy['brands'],'markets':policy['markets'],'channels':policy['channels'],'currencies':policy['currencies'],'sku_scope':'all_products_within_explicit_policy_scope','basis':'explicit_project_policy','allowed_modes':['simulation'],'available_at':available,'status':'active_simulation_only'})
    # Reviewed summaries only; raw text and evaluation holdout never enter this build.
    manifest=read(OUT/'sources/case-manifest.json');mby={m['source_conversation_id']:m for m in manifest}
    raw=read(PRIVATE/'case-source.json');cby={c['id']:c for c in raw['cases']}
    summaries=[]
    for n,review in enumerate(read(OUT/'authoring/case-reviews.json'),1):
        meta=mby[review['source_conversation_id']];assert meta['usage_split']=='rag_candidate'
        source=cby[review['source_conversation_id']];msgs={m['id']:m for m in source['messages']}
        turns=[]
        for t in review['timeline']:
            original=msgs[t['message_id']]
            turns.append({**t,'direction':original['direction'],'source_at':original['at'],'source_text_field':original['text_source']})
        row={**review,'timeline':turns,'case_id':meta['case_id'],'document_id':f'CASE-{n:03d}','source_kind':'production_derived_paraphrase','usage_split':'rag','brand':meta['brand'],'skus':meta['registration_skus'],'group_id':meta['group_id'],'customer_key':meta['customer_key'],'available_at':available,'last_evidence_at':max(t['source_at'] for t in turns),'review':'assistant_reviewed_paraphrase_not_manufacturer_approval','allowed_modes':['simulation'],'attachments_reviewed':False}
        summaries.append(row)
        body=f"# {row['title']}\n\n资料 ID：{row['document_id']}；版本：{VERSION}；来源：生产邮件审读后的去标识摘要。\n用途：simulation 检索经验；不是政策或当前客户的执行凭证。\n\n## 问题\n\n{row['problem']}\n\n## 往来摘要\n\n"+'\n'.join(f"- {t['source_at']} / {t['direction']}：{t['summary']}（来源消息 {t['message_id']}）" for t in turns)+f"\n\n## 可观察结果\n\n{row['outcome']}\n\n## 项目处理启示\n\n{row['lesson']}\n\n## 限制\n\n"+'\n'.join('- '+x for x in row['limitations'])+'\n'
        md(OUT/'cases'/f"{row['document_id']}.md",body)
        doc(row['document_id'],row['title'],'case_md',f"cases/{row['document_id']}.md",row['brand'],source='production_derived_paraphrase');bind(row['document_id'],row['skus'],basis='observed_registration_scope_only_not_universal_procedure')
    jsonl(OUT/'cases/reviewed-summaries.jsonl',summaries)
    write(OUT/'knowledge-bindings.json',bindings)
    for d in docs: d['source_hash']=digest((OUT/d['path']).resolve())
    write(OUT/'documents.json',docs);jsonl(OUT/'evaluation/retrieval-queries.jsonl',queries)
    write(OUT/'sources/build-manifest.json',{'version':VERSION,'product_count':len(products),'family_count':len(families),'document_count':len(docs),'pdf_pages':17,'case_cards':len(summaries),'parts_count':len(parts),'vectorized':False,'policy_executed':False,'source_catalog_observed_at':catalog['observed_at'],'source_catalog_hash':digest(PRIVATE/'live-catalog.json'),'pdf_hash':digest(PDF)})
    print(json.dumps({'products':len(products),'families':len(families),'documents':len(docs),'pdf_pages':17,'case_cards':len(summaries),'parts':len(parts)},ensure_ascii=False))

if __name__=='__main__':build()
