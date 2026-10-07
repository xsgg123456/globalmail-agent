# 前期资料数据约定

版本：1.1.0。此处描述后续加载器需要遵守的语义，不表示加载器已经实现。

## 1. 稳定标识与范围

- `product_id` 为项目商品标识，`sku` 保留生产精确字符串，`brand` 使用 OUTON / OUTONLIFE / BELEEV。
- `family_id` 为项目组织分组，`category_id` 为产品分类，与 BIZ-01 至 BIZ-07 的业务诉求分开。
- `manufacturer_*` 空值表示未知；`simulation_hardware_revision=SIM-V1` 仅是模拟版本，禁止反写成生产硬件版本。
- `listing_observations` 保留生产订单中的商品标题、图、站点、ASIN、单价等记录；同名商品或同一 SKU 不同快照可能有差异，不能自动合并成厂家核准参数。`photo_match` 区分精确 SKU 商品图与同族外观参考。
- `part_id` 一律以 SIM- 开头。`compatibility.json` 规定精确 SKU/模拟版本适配，名称、前缀和向量相似均不能替代它。
- 时间使用带时区 ISO8601。来源事件时间、采集时间、资料 `available_at`、政策有效时间是不同字段，不相互覆盖。

## 2. 知识逻辑文档

`documents.json` 包含 document_id、version、document_type、path、source_kind、allowed_modes、usage_split、available_at、status、source_hash。`path` 以资料包根目录为基准，source_hash 对实际文件完整字节计算。

PDF 的八条逻辑文档共用一个物理文件，但各自有 page_range。可以只解析物理文件一次，再将章节绑定给对应逻辑文档。切块必须保留 doc/version/section/page/figure/source_kind 和适用关系；禁止把整个 PDF 的文本复制给每个 SKU。

`knowledge-bindings.json` 是业务范围的权威清单，正文中的名称或编辑源只是说明。绑定包括 document_version、section_id、skus 或明确政策范围、basis、allowed_modes、available_at、status。没有匹配绑定就不能向该商品提供专属步骤。

`prepared_not_indexed` 表示资料已经生成但未进入向量库。当前没有 chunk_id、embedding、索引状态或向量检索通过记录；后续导入器负责生成。

## 3. 来源与案例

`sources/case-manifest.json` 只包含去标识分组、内部来源 ID 与用途，不含正文。eval_holdout 的消息、期望动作和结果不进入知识构建。

`cases/reviewed-summaries.jsonl` 保存审读后的中文摘要及来源消息映射，不是未经改写的真实邮件。timeline.summary 是概括，source_text_field 记录 original/current_reply/历史 ai_plain_text 等实际读取字段；一律不声称附件已读取。

`outcome` 描述能从邮件看见的结果。customer_reported_resolved 不等于厂家确认根因或系统已经人工结案；replacement_promised 不等于已出库。`lesson` 是项目归纳，不能伪装成历史执行事实。

## 4. 模拟业务输入

每个 scenarios/inputs.jsonl 对象是一份隔离分支。`initial_state` 交给模拟业务服务，Agent 通过工具查询；绝不能将整个对象原样塞入模型上下文。`initial_messages` 是按时间交付的客户往来。

- access_scope 控制本场景客户和订单，数据服务拒绝其他客户的查询。
- order_id 是内部测试主键；客户邮件使用 display_order_number，全部为生成的 999 前缀演练订单号，不能向真实系统查询。金额来自同 SKU/币种商品单价原型，仍是演练订单金额，不复原客户交易。
- 所有金额以最小货币单位整数保存，quantity 为正整数，币种明确。退款余额是实付减已成功与处理中占用。
- address_confirmation.version 与该次客户选择绑定，地址更改使旧确认失效。
- orders、operations、execution_records、shipments、returns 是独立对象；通过订单行、操作号和执行号关联，不能从客户邮箱猜关联。
- attempted_steps 保存已尝试结果。fault injection 位于 tool_overrides，只由模拟器读取，不暴露给 Agent。
- controller-events.jsonl 包含未来事件，仅供控制台/测试驱动。按 sequence、requires_event_id、trigger_condition 推进；不能预先把未来成功状态注入初始查询结果。
- 用 operation_selector 查找 Agent 实际建立的内部申请，匹配不到不能直接生成成功回执。事件中固定 SIM 执行号只是控制器测试标识。
- 重复 event_id 仅在 replay_same_event=true 且内容相同的专门重放用例允许；业务层应返回已有结果。
- SCN-029 是人工合成的历史只读边界测试，不是真实历史评测，也不允许注入本包政策作为当时事实。

## 5. 验收与部署边界

### 连续流程扩展

`scenarios/journeys/` 与原 51 个单环节样例分开。inputs.jsonl 仅含当前初始邮件和业务事实，业务事实只由服务端工具读取；controller-events.jsonl 由控制台持有，按唯一事件、时间和 gate 依次交付。manifest、readable、authoring 和 evaluation 的完整故事、参考回复、最终结果不得进入 Agent 上下文或 RAG。

- checkpoint 是等待本轮实际 Agent 行为的屏障，不是预写的客服回复。控制器只能在该轮运行已持久化且对应条件满足后推进；失败应停在当前步骤，不把示例答案注入会话代替模型。
- gate.after_step/ requires_event_id 只表达前后顺序；operation_required 还要求本分支、客户、订单行及问题一致的实际内部申请。找不到申请不创造退款/补发成功记录。取消记录指向原申请，重试支付保留原申请并区分处理尝试。
- 模拟业务适配器仍必须执行政策、客户选择、精确适配、库存与地址版本等校验；静态事件文件不授予绕过这些检查的权限。全额退款和换货的收件前提必须来自仓库记录；部分退款须有客户对金额和币种的明确接受。
- human_reply 后业务事件可以更新记录，不能重新唤起 Agent；下一条客户来信才恢复。human_close 只能由客服操作，并保留确认依据。签收状态本身不是客户确认解决。
- reference_reply 是可接受表述的例子，仅供评测理解语气和事实；评测允许同义表达，也允许在证据变化后给出不同合理方案，不能按逐字匹配打分。
- 寄回资料 HTML 是本地虚构资料样本，有完整地址、包装、邮资与凭据要求。隔离记录中的标签有效仅指演练分支；没有真实承运商授权，不可真实寄件，不能成为生产运单。客户自付邮资不要求商家预付标签，商家承担邮费时必须先取得对应预付资料。
- 全部新增联系人、地址、运单、往来和回执为编写内容；商品身份与金额沿用原型。来源与用途字段不能被客户正文的自然语言覆盖。

evaluation/ 中预期文档、预期动作和禁止动作只给测试器，不进 Agent 上下文或知识索引。当前全为开发测试数据，execution_status=not_run。

未来 pgvector 查询须保持正确模式、用途、可用时间、文档状态和精确商品适用范围；索引失效、解析失败、无适用资料分别报告。文档更新停用和库存状态查询具有不同刷新语义，不能混为向量检索的新旧问题。
