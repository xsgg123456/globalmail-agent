# 连续业务资料编辑格式

文件是 JSON 数组，每条使用 journey_id（JRN-01..21）、title（中文）、business（BIZ-01..07）、variant（main/branch）、seed_scenario_id（原51条中的ID）、tags（中文覆盖点）、initial_message（英文自然来信）、initial_state_patch（覆盖种子状态的对象，数组整体替换）、steps（有序）、outcome（中文）、knowledge_note（依据与未知）。

每步：id（s01起，条内唯一）、after_hours（从首封来信起的小时数，递增）、kind、actor、text（自然正文或内部业务说明）、gate（结构化条件）、record（业务记录对象，可空）、expected_actions（中文验收要求数组）、forbidden_actions（中文禁止行为数组）、reference_reply（英文参考回复，可空；只供评测，不进入初始输入/事件）。

kind 可用 customer_message、checkpoint、execution_record、shipment_update、return_update、inventory_update、human_reply、human_close、service_note、address_update。actor 可用 customer、agent_checkpoint、staff、warehouse、carrier、payment。checkpoint 只是等待真实 Agent 运行的评测点，不伪造 Agent 输出。

gate 必须用 after_step 关联前一步（首步 initial_message）；外部执行需要 operation_required 对象 {kind:refund/return/replacement/spare_part/investigation, order_id:"$order", order_line_id:"$line", issue_id:"$issue"}，运行时解析 Agent 实际创建的申请，查不到就停，不能预填 Agent 申请。涉及退回、地址、客户选择的前提在 expected_actions 中写清，并以之前的客户/仓库步骤为事实来源。

可用符号（构建时替换，未知符号报错）：$order、$line、$customer、$issue、$sku、$part、$amount（原实付，最小货币整数）、$partial（20%向下取整）、$currency、$order_number、$price_text、$partial_text、$return、$execution、$parcel、$return_parcel、$tracking、$return_tracking、$address。符号作为完整 JSON 值时保留数字类型；正文只用 $order_number/$price_text/$partial_text，不泄露内部ID。

record 按种类提供：退款/执行 {execution_id,operation_selector,status,kind,amount_minor,currency}；包裹 {parcel_id,order_id,order_line_id,purpose,execution_id,tracking_number,carrier,status}；退件 {return_id,order_id,order_line_id,quantity,reason,status,received,inspection,instructions}；库存 {item_id,on_hand,reserved}；地址 {version,confirmed,address}。字段缺少时不得假定执行成功。物流状态 label_created/in_transit/delivered；退款 accepted/failed/succeeded；退件 authorized/in_transit/received/inspected。

种子会复制重命名所有内部标识，保留商品/配件ID和实付。初始订单及订单号已知；需要客户补单号时 initial_message 不写编号，patch 清除会话已知订单引用（订单仍留服务端候选库）。初始状态默认清空已有申请、执行、退件、包裹、客户选择；confirmed_missing_part_id 和 defect_confirmed_in_simulation 不继承；地址默认未确认，后续由客户说明与业务记录建立证据。

七类主流程 JRN-01..07；分支 JRN-08..21 各两个。每条最终须 human_close，且理由来自此前客户确认或人工明确处置，不根据物流显示签收直接结案。所有路径设在隔离演练，所有地址、运单、退款回执均虚构，不向外部系统提交。不得编造危险维修步骤、厂家参数、视频观看结果或平台硬性期限；有技术证据缺口可按业务事实转人工。

商业往来应贴近实际：具体客户疑问、已做过的事、询问进度、解释等待原因、金额币种、数量、退件材料与期限、客户明确选择。不出现 SIM/HITL/RAG/fixture 等字样。每条至少两次客户来信；主流程要闭合，分支也要有处理结果，不能只停在“等待人工”。退款与换货默认先退回验收；部分退款先明确接受；补件要精确适配、有库存且地址确认；普通履约人工操作不等于会话接管。
