-- 只读目录提取；不返回客户身份、订单号、邮件标题/正文或附件内容。
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '12s';
SET LOCAL lock_timeout = '1s';
WITH
registration_products AS (
  SELECT upper(trim(i.brand)) AS brand, trim(i.sku) AS sku,
         i.product_name, i.site, r.id AS registration_id,
         r.conversation_id, r.first_message_id, r.reviewed_at, r.feedback_time
  FROM after_sales_registration_items i
  JOIN after_sales_registrations r ON r.id=i.registration_id
  WHERE upper(trim(i.brand)) IN ('OUTON','OUTONLIFE','BELEEV')
),
products AS (
  SELECT brand,sku,array_agg(DISTINCT product_name) FILTER (WHERE product_name IS NOT NULL) AS product_names,
    array_agg(DISTINCT site) FILTER (WHERE site IS NOT NULL) AS sites,
    count(DISTINCT registration_id) AS registration_count,
    count(DISTINCT registration_id) FILTER (WHERE reviewed_at IS NOT NULL) AS reviewed_registration_count,
    count(DISTINCT conversation_id) AS linked_conversation_count,
    array_agg(DISTINCT registration_id ORDER BY registration_id) AS registration_ids,
    array_agg(DISTINCT conversation_id ORDER BY conversation_id) FILTER (WHERE conversation_id IS NOT NULL) AS conversation_ids
  FROM registration_products WHERE nullif(sku,'') IS NOT NULL GROUP BY brand,sku
),
reg_by_conversation AS (
  SELECT conversation_id, array_agg(DISTINCT brand ORDER BY brand) AS brands,
    array_agg(DISTINCT sku ORDER BY sku) FILTER (WHERE nullif(sku,'') IS NOT NULL) AS skus,
    array_agg(DISTINCT registration_id ORDER BY registration_id) AS registration_ids,
    count(DISTINCT registration_id) FILTER (WHERE reviewed_at IS NOT NULL) AS reviewed_count
  FROM registration_products WHERE conversation_id IS NOT NULL GROUP BY conversation_id
),
message_stats AS (
  SELECT m.conversation_id,
    count(*) FILTER (WHERE m.direction::text='INBOUND') AS inbound_count,
    count(*) FILTER (WHERE m.direction::text='OUTBOUND') AS outbound_count,
    count(*) FILTER (WHERE nullif(trim(ec.current_reply_plain_text),'') IS NOT NULL) AS current_reply_count,
    count(*) FILTER (WHERE nullif(trim(ec.current_reply_plain_text),'') IS NULL AND nullif(trim(ec.ai_plain_text),'') IS NOT NULL) AS fallback_text_count,
    count(*) FILTER (WHERE m.has_non_inline_attachment) AS attachment_message_count,
    min(coalesce(m.received_at,m.sent_at,m.created_at)) AS first_visible_at,
    max(coalesce(m.received_at,m.sent_at,m.created_at)) AS last_visible_at,
    string_agg(CASE WHEN m.direction::text='INBOUND' THEN lower(coalesce(nullif(trim(ec.current_reply_plain_text),''),ec.ai_plain_text,'')) ELSE '' END, ' ') AS search_text
  FROM email_messages m LEFT JOIN email_contents ec ON ec.message_id=m.id
  WHERE m.sensitive_data_deleted_at IS NULL AND NOT m.is_auto_reply
  GROUP BY m.conversation_id
),
case_base AS (
  SELECT c.id AS conversation_id,c.first_status::text AS first_status,c.workflow_status::text AS workflow_status,
    c.customer_language_code,
    CASE WHEN cardinality(r.brands)=1 THEN r.brands[1]
      WHEN lower(b.display_name) LIKE '%outon%life%' THEN 'OUTONLIFE'
      WHEN lower(b.display_name) LIKE '%outon%' THEN 'OUTON'
      WHEN lower(b.display_name) LIKE '%beleev%' THEN 'BELEEV' END AS brand,
    CASE WHEN cardinality(r.brands)=1 THEN 'registration' ELSE 'mailbox_hint' END AS brand_source,
    coalesce(cardinality(r.brands)>1,false) AS multi_brand_registration,
    r.skus AS registration_skus,r.registration_ids,coalesce(r.reviewed_count,0) AS reviewed_registration_count,
    o.id AS order_binding_id,
    (o.order_summary_json::jsonb ? 'details') AS has_order_details,
    o.order_summary_json::jsonb->'details'->>'country' AS order_country,
    o.order_summary_json::jsonb->'details'->>'currency' AS order_currency,
    ARRAY(SELECT x->>'sku' FROM jsonb_array_elements(coalesce(o.order_summary_json::jsonb->'details'->'items','[]'::jsonb)) x WHERE nullif(x->>'sku','') IS NOT NULL) AS order_skus,
    m.inbound_count,m.outbound_count,m.current_reply_count,m.fallback_text_count,m.attachment_message_count,
    m.first_visible_at,m.last_visible_at,m.search_text
  FROM mail_conversations c JOIN mailboxes b ON b.id=c.mailbox_id
  JOIN message_stats m ON m.conversation_id=c.id
  LEFT JOIN reg_by_conversation r ON r.conversation_id=c.id
  LEFT JOIN order_bindings o ON o.conversation_id=c.id
  WHERE c.lifecycle_status::text='ACTIVE' AND NOT c.is_irrelevant AND c.sensitive_data_deleted_at IS NULL
),
case_tags AS (
  SELECT *,array_remove(ARRAY[
    CASE WHEN search_text ~ '(how to|instructions|manual|assembly|install|compatible|说明|安装|使用方法)' THEN 'BIZ-01' END,
    CASE WHEN search_text ~ '(not work|stopped|broken|defect|flicker|pairing|fault|故障|不亮|配对)' THEN 'BIZ-02' END,
    CASE WHEN search_text ~ '(tracking|deliver|shipment|parcel|arriv|物流|未收到)' THEN 'BIZ-03' END,
    CASE WHEN search_text ~ '(refund|reimburse|money back|退款|rembours|erstatt)' THEN 'BIZ-04' END,
    CASE WHEN search_text ~ '(return|退货|retour|zur.cksend)' THEN 'BIZ-05' END,
    CASE WHEN search_text ~ '(exchang|replacement|replace|换货|umtausch)' THEN 'BIZ-06' END,
    CASE WHEN search_text ~ '(parts?|remote|wheel|brake|screw|配件|补寄|补发)' THEN 'BIZ-07' END
  ],NULL) AS keyword_candidate_categories
  FROM case_base WHERE brand IN ('OUTON','OUTONLIFE','BELEEV')
),
ranked_candidates AS (
  SELECT c.*,t.category,row_number() OVER (PARTITION BY brand,t.category ORDER BY
    (first_status='FIRST_CONFIRMED' AND inbound_count>=2 AND outbound_count>=1) DESC,
    (brand_source='registration') DESC,has_order_details DESC NULLS LAST,
    reviewed_registration_count DESC,inbound_count DESC,last_visible_at DESC,conversation_id) AS candidate_rank
  FROM case_tags c CROSS JOIN LATERAL unnest(keyword_candidate_categories) t(category)
),
case_manifest AS (
  SELECT conversation_id,first_status,workflow_status,customer_language_code,brand,brand_source,multi_brand_registration,
    registration_skus,registration_ids,reviewed_registration_count,order_binding_id,coalesce(has_order_details,false) AS has_order_details,
    order_country,order_currency,order_skus,inbound_count,outbound_count,current_reply_count,fallback_text_count,attachment_message_count,
    first_visible_at,last_visible_at,keyword_candidate_categories,
    (first_status='FIRST_CONFIRMED' AND inbound_count>=2 AND outbound_count>=1) AS complete_history_candidate,
    'keyword_candidate_not_semantically_reviewed' AS review_status
  FROM case_tags WHERE conversation_id IN (SELECT conversation_id FROM ranked_candidates WHERE candidate_rank<=3)
    OR EXISTS (SELECT 1 FROM unnest(registration_skus) sku WHERE sku ~ '^(H-CTD16-|H-SJJ0001-|H-LBD05-|F-SJ001-|F-ZZZ0002-|SP-SLHBC01-|SP-SLHBC12-|SP-XLLHBC02-)')
),
coverage AS (
  SELECT brand,t.category,count(*) AS keyword_candidate_count,
    count(*) FILTER (WHERE first_status='FIRST_CONFIRMED' AND inbound_count>=2 AND outbound_count>=1) AS first_contact_multiturn_candidates
  FROM case_tags c CROSS JOIN LATERAL unnest(keyword_candidate_categories) t(category)
  GROUP BY brand,t.category
)
SELECT jsonb_build_object(
 'schema_version','catalog-v1',
 'observed_at',current_timestamp,
 'observed_at_beijing',to_char(current_timestamp AT TIME ZONE 'Asia/Shanghai','YYYY-MM-DD HH24:MI:SS'),
 'transaction_read_only',current_setting('transaction_read_only'),
 'transaction_isolation',current_setting('transaction_isolation'),
 'source','hengxin-smartmail live production / read-only metadata',
 'limitations',jsonb_build_array('No customer identity, order numbers or mail bodies exported','Keyword candidates are not verified business labels','First-contact marker is not proof of complete history or successful resolution','Product/video compatibility not established by name matching'),
 'counts',jsonb_build_object(
   'mailboxes',(SELECT count(*) FROM mailboxes),
   'conversations_total',(SELECT count(*) FROM mail_conversations),
   'messages_total',(SELECT count(*) FROM email_messages),
   'target_brand_conversation_candidates',(SELECT count(*) FROM case_tags),
   'registrations',(SELECT count(*) FROM after_sales_registrations),
   'product_rows',(SELECT count(*) FROM products),
   'selected_case_candidates',(SELECT count(*) FROM case_manifest)),
 'products',coalesce((SELECT jsonb_agg(to_jsonb(p) ORDER BY p.brand,p.registration_count DESC,p.sku) FROM products p),'[]'::jsonb),
 'videos',coalesce((SELECT jsonb_agg(jsonb_build_object('source_file_id',id,'brand',brand,'title',display_name,'customer_title',customer_title,'url',external_url,'updated_at',updated_at,'content_reviewed',false,'sku_mapping_status','not_available') ORDER BY brand,display_name) FROM after_sales_files WHERE status::text='ACTIVE'),'[]'::jsonb),
 'quick_reply_catalog',coalesce((SELECT jsonb_agg(jsonb_build_object('source_template_id',id,'title',title,'updated_at',updated_at,'authority','staff_convenience_template_not_policy') ORDER BY title) FROM quick_reply_templates WHERE status::text='ACTIVE'),'[]'::jsonb),
 'coverage',coalesce((SELECT jsonb_agg(to_jsonb(c) ORDER BY brand,category) FROM coverage c),'[]'::jsonb),
 'case_candidates',coalesce((SELECT jsonb_agg(to_jsonb(c) ORDER BY brand,conversation_id) FROM case_manifest c),'[]'::jsonb)
);
ROLLBACK;
