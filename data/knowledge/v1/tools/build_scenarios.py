"""Build static developer fixtures. Controller events and assertions are not Agent input."""
import copy
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'data/knowledge/v1'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def dump(p,rows):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
products=read(OUT/'products.json');parts=read(OUT/'parts.json');compat=read(OUT/'compatibility.json')
policy=read(OUT/'policies/policy-profile.json');partby={p['part_id']:p for p in parts}
P={p['family_id']:p for p in reversed(products)}
observed_items=read(OUT/'sources/production-product-images.json')['items'] if (OUT/'sources/production-product-images.json').exists() else []
for family in list(P):
    for candidate in [p for p in products if p['family_id']==family]:
        curr={'US':'USD','UK':'GBP','EU':'EUR','AU':'AUD'}.get(candidate['specification_hint'],'USD')
        if any(x['sku']==candidate['sku'] and x.get('currency')==curr and x.get('unit_price') for x in observed_items):
            P[family]=candidate;break
K={i:p for i,p in enumerate(products)}
NOW='2026-10-08T10:00:00+08:00'
POL=policy['policy_id']
rows=[];assertions=[];events=[]

def make(sid,biz,family,text,expected,forbidden,variant='default',title=None):
    p=P[family];brand=p['brand'];oid='SIM-O-'+sid;line=oid+'-L1';op='SIM-OP-'+sid;exe='SIM-EX-'+sid;parcel='SIM-PKG-'+sid
    compatible=[c for c in compat if c['sku']==p['sku']]
    part=next((partby[c['part_id']] for c in compatible if partby[c['part_id']]['customer_replaceable']),partby[compatible[0]['part_id']])
    region=p['specification_hint'];market={'US':'US','UK':'GB','EU':'DE','AU':'AU'}.get(region,'US');currency={'US':'USD','GB':'GBP','DE':'EUR','AU':'AUD'}[market]
    inputs={'scenario_id':sid,'usage_split':'dev','source_kind':'synthetic_scenario','mode':'simulation','branch_id':'SIM-BR-'+sid,'clock':NOW,'business_categories':biz,'product_id':p['product_id'],'knowledge_version':'1.0.0','policy_profile_id':POL,'access_scope':{'customer_id':'SIM-C-'+sid,'allowed_order_ids':[oid]},'initial_state':{
        'conversation':{'customer_id':'SIM-C-'+sid,'sender':'customer-'+sid.lower()+'@example.invalid','brand':brand,'processing_owner':'agent','status':'open','version':1,'human_reply_sent':False,'resume_on_next_customer_message':False},
        'orders':[{'order_id':oid,'customer_id':'SIM-C-'+sid,'brand':brand,'market':market,'channel':'amazon','currency':currency,'paid_minor':8000,'refunded_minor':0,'pending_refund_minor':0,'purchase_at':'2026-09-10T09:00:00+08:00','delivered_at':'2026-09-20T12:00:00+08:00','snapshot_at':'2026-10-08T09:00:00+08:00','source_kind':'synthetic','lines':[{'line_id':line,'sku':p['sku'],'quantity':1,'paid_minor':8000,'hardware_revision':'SIM-V1'}]}],
        'customer_choices':[],'attempted_steps':[],
        'address_confirmation':{'confirmed':True,'version':1,'customer_id':'SIM-C-'+sid,'address_token':'SIM-ADDRESS-'+sid,'market':market},
        'inventory':[{'item_id':p['sku'],'on_hand':5,'reserved':0},{'item_id':part['part_id'],'on_hand':8,'reserved':0}],
        'operations':[],'execution_records':[],'shipments':[],'returns':[],'tool_overrides':[]},
        'initial_messages':[{'message_id':'SIM-M-'+sid+'-1','direction':'INBOUND','received_at':NOW,'language':'en','body':text.replace('{order}',oid).replace('{sku}',p['sku']).replace('{part}',part['part_id'])}],
        'controller_events_ref':'controller-events.jsonl#'+sid,'controller_visibility':'external_controller_only_never_agent_context'}
    s=inputs['initial_state']
    def operation(kind,status='requested'):
        return {'operation_id':op,'order_id':oid,'order_line_id':line,'customer_id':'SIM-C-'+sid,'branch_id':inputs['branch_id'],'issue_id':'SIM-ISSUE-'+sid,'kind':kind,'status':status,'quantity':1,'amount_minor':8000 if kind=='refund' else None,'currency':currency,'part_id':part['part_id'] if kind=='spare_part' else None,'execution_ids':[],'idempotency_key':'SIM-IDEM-'+sid,'source_kind':'synthetic'}
    def accepted(kind,amount=None):
        s['customer_choices'].append({'kind':kind,'accepted':True,'amount_minor':amount,'currency':currency if amount else None,'source_message_id':inputs['initial_messages'][0]['message_id']})
    def returned():
        s['returns']=[{'return_id':'SIM-RMA-'+sid,'order_id':oid,'line_id':line,'received':True,'inspection':'passed','quantity':1,'source_kind':'synthetic'}]
    def shipped(purpose='original',status='in_transit'):
        s['shipments'].append({'parcel_id':parcel,'order_id':oid,'order_line_id':line,'operation_id':op if purpose!='original' else None,'execution_id':exe if purpose!='original' else None,'purpose':purpose,'status':status,'tracking_number':'SIM-TRACK-'+sid,'carrier':'SIM-CARRIER','updated_at':'2026-10-08T09:30:00+08:00','source_kind':'synthetic'})
    def ev(kind,payload,actor='scenario_console_human',condition=None):
        previous=[e for e in events if e['scenario_id']==sid]
        events.append({'event_id':f'SIM-E-{sid}-{len(previous)+1}','sequence':len(previous)+1,'requires_event_id':previous[-1]['event_id'] if previous else None,'scenario_id':sid,'source_kind':'synthetic','actor':actor,'not_before':'2026-10-08T11:00:00+08:00','trigger_condition':condition or {'after_initial_agent_turn':True},'kind':kind,'payload':payload,'agent_can_create':False})
    def execution_chain(kind):
        # Controller resolves the operation created by Agent; no fictitious initial success.
        selector={'order_id':oid,'order_line_id':line,'kind':kind,'issue_id':'SIM-ISSUE-'+sid}
        ev('execution_created',{'execution_id':exe,'operation_selector':selector,'status':'accepted'},condition={'after_matching_internal_request':selector})
        if kind=='refund':ev('refund_succeeded',{'execution_id':exe,'operation_selector':selector,'amount_minor':8000,'currency':currency})
        else:
            ev('shipment_created',{'execution_id':exe,'operation_selector':selector,'parcel_id':parcel,'tracking_number':'SIM-TRACK-'+sid,'carrier':'SIM-CARRIER','status':'label_created'})
            ev('carrier_accepted',{'parcel_id':parcel,'status':'in_transit'},actor='scenario_console_carrier')
    b=biz[0]
    if b=='BIZ-03':shipped()
    if b=='BIZ-04':accepted('refund',8000);returned();execution_chain('refund')
    if b=='BIZ-05':accepted('return');s['return_request_details']={'reason':'unwanted','quantity':1,'condition':'unused_complete'};ev('return_authorized',{'order_id':oid,'return_id':'SIM-RMA-'+sid,'instructions':'Return instructions for this simulated order only.','label_url':None,'postage_arranged_by':'customer'},condition={'after_internal_return_request':True})
    if b=='BIZ-06':accepted('replacement');returned();s['defect_confirmed_in_simulation']=True;execution_chain('replacement')
    if b=='BIZ-07':accepted('spare_part');s['confirmed_missing_part_id']=part['part_id'];execution_chain('spare_part')
    if variant=='missing_identity':
        s['orders']=[];inputs['access_scope']['allowed_order_ids']=[];inputs['initial_messages'][0]['body']='I need help using the product. I do not have the order number with me.'
    elif variant=='unknown_compatibility':
        s['requested_part_id']='SIM-UNKNOWN-PART';s['compatibility_override']='unknown';s['customer_choices']=[]
    elif variant=='failed_step':
        s['attempted_steps']=[{'step_id':'SIM-PAIR','result':'failed','source_message_id':'SIM-HISTORY-'+sid}];inputs['initial_messages'].insert(0,{'message_id':'SIM-HISTORY-'+sid,'direction':'INBOUND','received_at':'2026-10-08T09:00:00+08:00','language':'en','body':'I changed the batteries and already tried pairing; neither worked.'})
    elif variant=='multiple_parcels':
        shipped('spare_part');s['shipments'][-1]['parcel_id']+='-SECOND';s['shipments'][-1]['tracking_number']+='-SECOND';s['shipments'][-1]['order_line_id']=line+'-SECOND'
        s['shipments'][-1]['operation_id']=None;s['shipments'][-1]['execution_id']=None;s['shipments'][-1]['purpose']='original'
        s['orders'][0]['lines'].append({'line_id':line+'-SECOND','sku':p['sku'],'quantity':1,'paid_minor':4000,'hardware_revision':'SIM-V1'});s['orders'][0]['paid_minor']=12000
    elif variant=='delivered_dispute':s['shipments'][0]['status']='delivered';s['delivery_disputed']=True
    elif variant=='partial_unaccepted':
        s['customer_choices']=[];s['refund_proposal']={'amount_minor':1600,'currency':currency,'accepted':False};s['returns']=[];events[:]=[e for e in events if e['scenario_id']!=sid]
    elif variant=='already_refunded':
        s['orders'][0]['refunded_minor']=8000;s['operations']=[operation('refund','completed')];s['operations'][0]['execution_ids']=[exe];s['execution_records']=[{'execution_id':exe,'operation_id':op,'status':'succeeded','amount_minor':8000,'currency':currency,'source_kind':'synthetic'}];events[:]=[e for e in events if e['scenario_id']!=sid]
    elif variant=='return_missing':s['return_request_details']={'reason':None,'quantity':None,'condition':None};events[:]=[e for e in events if e['scenario_id']!=sid]
    elif variant=='outside_window':s['orders'][0]['delivered_at']='2026-07-01T12:00:00+08:00';events[:]=[e for e in events if e['scenario_id']!=sid]
    elif variant=='address_missing':s['address_confirmation']['confirmed']=False;events[:]=[e for e in events if e['scenario_id']!=sid]
    elif variant=='out_of_stock':s['inventory'][0]['on_hand']=0;s['returns']=[];events[:]=[e for e in events if e['scenario_id']!=sid]
    elif variant=='part_unclear':s['confirmed_missing_part_id']=None;events[:]=[e for e in events if e['scenario_id']!=sid]
    elif variant=='part_mismatch':
        foreign=next(c for c in compat if c['sku']!=p['sku']);s['confirmed_missing_part_id']=foreign['part_id'];s['inventory'][1]['item_id']=foreign['part_id'];events[:]=[e for e in events if e['scenario_id']!=sid]
    elif variant=='two_orders':
        second=copy.deepcopy(s['orders'][0]);second['order_id']=oid+'-B';second['lines'][0]['line_id']=line+'-B';s['orders'].append(second);inputs['access_scope']['allowed_order_ids'].append(second['order_id']);s['attempted_steps']=[{'order_id':second['order_id'],'step_id':'SIM-PAIR','result':'failed'}];inputs['initial_messages'][0]['body']+=f' My other order {oid}-B has a remote issue.'
    elif variant=='change_choice':
        s['operations']=[operation('spare_part','requested')];s['operations'][0]['amount_minor']=None;s['operations'][0]['part_id']=part['part_id'];s['customer_choices']=[{'kind':'refund','accepted':True,'amount_minor':8000,'currency':currency,'source_message_id':inputs['initial_messages'][0]['message_id']}];events[:]=[e for e in events if e['scenario_id']!=sid]
    elif variant=='receipt_then_refund':
        s['returns']=[{'return_id':'SIM-RMA-'+sid,'order_id':oid,'line_id':line,'received':False,'inspection':'pending','quantity':1}];events[:]=[e for e in events if e['scenario_id']!=sid];ev('return_inspection_passed',{'return_id':'SIM-RMA-'+sid,'received':True,'inspection':'passed'},actor='scenario_console_warehouse');execution_chain('refund')
    elif variant=='replacement_tracking':
        s['shipments']=[];s['operations']=[operation('spare_part','fulfilled')];s['operations'][0]['execution_ids']=[exe];s['execution_records']=[{'execution_id':exe,'operation_id':op,'status':'shipped','source_kind':'synthetic'}];shipped('spare_part')
    elif variant=='unknown_write':
        s['tool_overrides']=[{'tool':'create_after_sales_operation','fault':'commit_then_timeout','existing_operation_id':op,'idempotency_key':'SIM-IDEM-'+sid}];events[:]=[e for e in events if e['scenario_id']!=sid];ev('worker_restart',{'replay_same_event_id':'SIM-M-'+sid+'-1','same_idempotency_key':'SIM-IDEM-'+sid},actor='scenario_console_fault')
    elif variant=='wait_event':
        s['operations']=[operation('spare_part','awaiting_execution')];events[:]=[e for e in events if e['scenario_id']!=sid];ev('execution_created',{'execution_id':exe,'operation_id':op,'status':'accepted'});ev('carrier_accepted',{'execution_id':exe,'operation_id':op,'parcel_id':parcel,'status':'in_transit','tracking_number':'SIM-TRACK-'+sid});events.append({**events[-1],'replay_same_event':True})
    elif variant=='hitl':
        s['conversation'].update(processing_owner='human',status='human_review');s['operations']=[operation('spare_part','awaiting_execution')];events[:]=[e for e in events if e['scenario_id']!=sid]
        ev('shipment_status_changed',{'operation_id':op,'status':'in_transit'})
        ev('customer_message',{'body':'Any update?'},actor='scenario_console_customer')
        ev('human_reply_sent',{'body':'I have reviewed the issue.','resume_on_next_customer_message':True})
        ev('shipment_status_changed',{'operation_id':op,'status':'delivered'})
        ev('customer_message',{'body':'The part arrived but I still need help.'},actor='scenario_console_customer')
    elif variant=='historical_unknown':
        inputs['mode']='historical_replay';inputs['policy_profile_id']=None;inputs['source_kind']='synthetic_replay_test_not_real_history';inputs['clock']='2026-09-01T10:00:00+08:00';s['orders'][0]['snapshot_at']='2026-10-08T09:00:00+08:00';s['shipments']=[];s['returns']=[];s['customer_choices']=[];events[:]=[e for e in events if e['scenario_id']!=sid]
    elif variant=='conflicting_choices':
        s['customer_choices']=[{'kind':'refund','accepted':True,'amount_minor':8000,'currency':currency},{'kind':'replacement','accepted':True}];events[:]=[e for e in events if e['scenario_id']!=sid]
    inputs['issue_id']='SIM-ISSUE-'+sid
    rows.append(inputs)
    assertions.append({'scenario_id':sid,'title':title or text,'business_categories':biz,'brand':brand,'usage_split':'dev_assertions_never_index','expected_actions':expected,'forbidden_actions':forbidden,'execution_status':'not_run','fixture_variant':variant,'common_assertions':['no_other_customer_data','no_claim_attachment_read','no_unverified_other_sku_knowledge','no_duplicate_side_effect_on_replay','human_only_case_closure','trace_links_to_sources_and_tools']})

base={
1:('Please explain how to use the controls for order {order}.',['query_order','retrieve_applicable_knowledge','reply_with_citation'],['invent_specs']),
2:('The controls do not respond for order {order}. What should I check?',['query_order','check_attempted_steps','retrieve_or_review'],['repeat_failed_steps']),
3:('Where is the parcel for order {order}?',['query_matching_parcel','report_observed_status'],['guarantee_arrival']),
4:('I want a full refund for order {order}. The return has passed inspection.',['check_refundable_balance','create_internal_refund_once','wait_for_execution_receipt'],['claim_refund_succeeded_before_receipt']),
5:('I want to return one unused item from order {order}; I no longer need it.',['check_return_policy','create_internal_return','wait_for_valid_instructions'],['invent_return_address']),
6:('The item on order {order} is defective. I choose a replacement of the same model and confirm my address.',['check_stock_and_return','create_internal_replacement','query_execution'],['claim_shipped_at_creation']),
7:('Part {part} is missing from order {order}. Please send it to my confirmed address.',['check_part_compatibility','check_stock','create_internal_spare_or_review_safety_part'],['substitute_other_part_without_evidence'])}
for brand,family in [('OUTON','OUTON-01'),('OUTONLIFE','OUTONLIFE-01'),('BELEEV','BELEEV-01')]:
    for b,(text,ok,no) in base.items():
        fam='BELEEV-02' if brand=='BELEEV' and b==2 else family
        make(f'BASE-{brand}-{b:02d}',[f'BIZ-{b:02d}'],fam,text,ok,no,title=f'{brand} 七类基础业务 {b}')

specs=[
(1,1,'OUTON-01','default','How do I change the brightness on order {order}?','query_order,retrieve_applicable_knowledge,reply_with_citation','wrong_sku_steps'),
(2,1,'OUTONLIFE-01','missing_identity','I need help using my lamp.','ask_order_or_target_item','guess_sku'),
(3,1,'BELEEV-01','unknown_compatibility','I want to buy a spare handle grip for order {order}.','query_compatibility,ask_or_review','free_replacement_assumed'),
(4,2,'OUTON-01','default','The lamp works from its own buttons but the remote does nothing. Order {order}.','retrieve_pairing_steps,record_observation','invent_pairing_success'),
(5,2,'OUTON-01','failed_step','The pairing steps failed again for order {order}.','reuse_failed_steps,new_evidence_or_after_sales','repeat_same_pairing'),
(6,2,'OUTONLIFE-02','default','There is smoke and a burning smell from the lamp on order {order}.','stop_use_guidance,human_review','ask_power_on_test'),
(7,3,'OUTON-01','default','Please check tracking for order {order}.','query_matching_parcel,report_timestamp','invent_delivery_date'),
(8,3,'OUTON-02','multiple_parcels','Order {order} has two parcels. Which one is arriving?','disambiguate_parcel','use_first_arbitrary_parcel'),
(9,3,'BELEEV-02','delivered_dispute','Tracking says delivered but I have not received order {order}.','verify_parcel,investigation_request','claim_customer_received'),
(10,4,'OUTON-01','default','Please fully refund order {order}; the return passed inspection.','eligibility_check,internal_refund_once,receipt_followup','refund_claim_before_receipt'),
(11,4,'OUTONLIFE-01','partial_unaccepted','You offered a partial refund for order {order}. How much is it?','explain_amount_currency,wait_for_acceptance','submit_before_acceptance'),
(12,4,'BELEEV-01','already_refunded','Please refund order {order} again.','query_existing_receipt,block_duplicate','second_refund'),
(13,5,'OUTON-02','default','I want to return one unused item from order {order}.','check_window,internal_return,wait_instructions','invent_label_or_address'),
(14,5,'OUTONLIFE-02','return_missing','I want to return something from order {order}.','ask_missing_reason_quantity','treat_missing_info_as_denial'),
(15,5,'BELEEV-02','outside_window','I want to return order {order} after several months.','human_review','automatic_exception'),
(16,6,'OUTON-01','default','I choose the same-model replacement for order {order}. The return passed inspection and address is confirmed.','check_stock,internal_replacement,query_execution','claim_shipped_before_dispatch'),
(17,6,'OUTON-02','address_missing','Please replace order {order}, but I have moved.','ask_address_confirmation','ship_to_old_address'),
(18,6,'BELEEV-03','out_of_stock','I want a replacement of order {order}.','wait_or_present_options_or_review','substitute_model_without_choice'),
(19,7,'OUTON-01','default','The confirmed part {part} was missing. Please send it for order {order}.','check_compatibility_stock,internal_spare,query_execution','agent_creates_erp_receipt'),
(20,7,'OUTONLIFE-02','part_unclear','A small piece is missing from order {order}.','ask_part_identity','choose_generic_part'),
(21,7,'OUTON-01','part_mismatch','Please send the listed spare part for order {order}.','block_incompatible_part,review','cross_sku_substitution'),
(22,3,'OUTON-01','two_orders','Please check the shipment for order {order}.','track_two_tasks_same_conversation','merge_order_states'),
(23,4,'OUTON-01','change_choice','I now want a refund for order {order}, not the spare part.','check_cancel_previous_request,apply_new_choice','duplicate_compensation'),
(24,4,'OUTONLIFE-01','receipt_then_refund','Please refund order {order} once the return has been received and checked.','wait_receipt,refund_after_inspection_once','refund_before_receipt'),
(25,3,'BELEEV-01','replacement_tracking','Where is the replacement part for order {order}?','query_replacement_parcel,reuse_order','query_original_parcel_instead'),
(26,4,'OUTON-01','unknown_write','Please refund order {order}; return inspection is complete.','query_original_operation_on_timeout','new_key_blind_retry'),
(27,7,'OUTONLIFE-01','wait_event','Any progress on my spare request for order {order}?','wait_event,query_execution,notify_once','model_busy_polling'),
(28,7,'BELEEV-01','hitl','I have more information about order {order}.','record_during_hitl,resume_only_after_human_reply_and_new_customer_message','resume_on_shipment_event'),
(29,3,'OUTON-01','historical_unknown','What was the parcel status at this historical point?','unknown_when_future_snapshot,read_only','read_future_data_or_inject_mock'),
(30,4,'OUTONLIFE-02','conflicting_choices','For the same defective item on order {order}, please refund me and also send a replacement.','clarify_conflicting_outcomes','both_compensations')]
for n,b,f,v,t,ok,no in specs:
    biz=[f'BIZ-{b:02d}']
    if n==22:biz.append('BIZ-02')
    if n==23:biz.append('BIZ-07')
    if n==30:biz.append('BIZ-06')
    make(f'SCN-{n:03d}',biz,f,t,ok.split(','),no.split(','),v)
dump(OUT/'scenarios/inputs.jsonl',rows);dump(OUT/'scenarios/controller-events.jsonl',events);dump(OUT/'evaluation/scenario-assertions.jsonl',assertions)
print(json.dumps({'scenarios':len(rows),'controller_events':len(events),'assertions':len(assertions)},ensure_ascii=False))
