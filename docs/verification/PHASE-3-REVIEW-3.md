# Phase 3 第三轮独立两阶段审查

日期：2026-10-08。执行者：fresh code-reviewer。依据：AGENTS.md、.agents/skills/code-review/SKILL.md、DEV-PLAN Phase 3、Product-Spec REQ-001/002/003/007/008/009与5.10–5.12、AGENT-ARCHITECTURE第2/3/6/8节、AGENT-ACCEPTANCE FT-01/02/05/07/08、PHASE-3-CONTRACT/IMPLEMENTATION及前两轮审查原文。

**本轮结论：FAIL。四个旧问题已在本轮基线独立复验关闭；新增一项 Stage 1 MEDIUM：首次打开已有溢出邮件的会话，未滚动的阅读位置被后续外部来信/SSE刷新强制移到底部。** 主 Agent 随后修复，但按派发指令，本实例不复审这次新改动；需要新的 fresh 审查。报告文件名不预设通过，未创建 PHASE-3-REVIEW-PASS.md。

本轮先完整检查 Stage 1，原四个问题与其他本期条目均有证据，随后检查 Stage 2。最后补实际滚动证据时发现新缺陷，因此不签 Stage 1/2 最终 PASS。下文保留发现前已经执行的质量、安全与视觉检查，不把绿灯测试替代遗漏路径。没有改源码、运行模型、提交 Git 或派发其他 Agent。

路径简称：B/＝globalmail-agent/backend/src/globalmail_agent/；F/＝globalmail-agent/frontend/src/；BT/＝globalmail-agent/backend/tests/；FT/＝globalmail-agent/frontend/scripts/。代码行号指本轮启动与发现时的基线；MessageTimeline随后修改的行号不作为本轮复验依据。

## Stage 1：新增问题

### MEDIUM P3-R2：首次挂载的真实位置与缓存 atBottom 不一致，静止阅读遭外部输入强制滚动

要求原文：Product-Spec.md:562，“消息自动滚动仅在用户位于底部或主动提交时触发，保留阅读历史邮件的位置”；第594行，成功后“保留当前阅读位置”。

发现时代码：

- F/components/mail-agent/MessageTimeline.vue:47 初始化 atBottom=true；第53行仅收到 scroll 事件后才按实际 DOM 位置更新缓存。
- 第63/69行的消息与conversationId watcher均非 immediate；F/views/mail-agent/index.vue:80 在 detail 已返回时首次挂载 MessageTimeline。因此首次打开带多封邮件的会话，并不会执行 conversationId watcher 的滚到底部，也不一定发生 scroll 事件。
- 第58行直接使用缓存作门禁，第64行监听最后一封邮件 ID。首次挂载已溢出、实际 scrollTop=0 时，缓存仍是 true；外部客户来信经 SSE 刷新消息即可通过门禁并跳到底部，无需用户主动提交。

主 Agent 在隔离真实浏览器核实了这条生产路径；本实例读取发现时源码独立确认其可达性。真实操作的原始数值由主 Agent提供：

    初次检查：已溢出邮件区 scrollTop=0；外部真实 HTTP 来信/SSE 更新后 scrollTop=525。

这个初次检查直接设置 scrollTop=0，尚不足以证明用户滚动路径失效；但如果首次加载本来就是0，设置0并不产生scroll事件，正好暴露初始化缺口。本实例要求另测“整页刷新→选已有溢出邮件的会话→不scroll、不wheel→静止阅读→外部真实来信/SSE”，不能用产生scroll事件的wheel测试排除这条路径。主 Agent随后明确确认“首次静止阅读缺陷确认并修”。

影响：读者首次停在历史顶部，没有发送动作，也没有位于底部，后续新来信却把当前位置移走。不是数据隔离或回复屏障HIGH，但不符合本期明确交付的阅读位置规则。

修复后验收标准：初次挂载、实际滚动后、会话切换和消息更新均以真实位置判断；非底部遇到外部来信/SSE刷新保持 scrollTop；位于底部或主动提交才自动滚动。补真实初挂载静止阅读回归，并重跑前端测试与编译。

**本轮状态：发现时 FAIL，修复后尚未由本实例复验。** 主 Agent已报告取消默认true缓存，改为消息更新前依据旧DOM距离判断；修后浏览器 reported before={top:0,height:939,viewport:324}、第8封外部来信/SSE后after=0。本报告只记录修复通知，不将该通知或其数值签为本实例的最终通过结论。

## Stage 1：前两轮问题的独立复验

| 原问题 | 本轮基线结论与证据 |
|---|---|
| HIGH P3-R1：旧草稿save/reload误绑定最新输入 | 已关闭。B/domain/conversation.py:47必填expected_input_revision；B/application/human_review.py:51拒未来版本，第58行持久化实际核对版本，第66行完成前核验。F/composables/useMailWorkbench.ts:74从持久review版本初始化，第196行保存旧核对版，第259行才显式核对。BT/test_human_events.py:31真实PG执行新输入→旧save→reload→仍旧版本→human_reply拒绝且消息仍2封，通过；FT/mail-workbench.test.ts:43/138通过。真实GUI保存旧草稿、整页刷新仍disabled的记录见docs/verification/PHASE-3-VALIDATION.md:88。 |
| MEDIUM P3-F1：close→takeover→append遗留open review | 已关闭。B/application/human_review.py:23在任何invalidate/写之前拒非open；BT/test_human_events.py:13用合法生产command验证拒绝码conversation_not_open、会话对象完全不变、无review；新来信重开后agent且可领取，通过。不是修改DB制造预期状态。 |
| MEDIUM P3-F2：knowledge完成与同会话append锁逆序死锁 | 已关闭。B/application/conversation_lock.py:16按slot_key排序先锁agent/knowledge，之后第18行取会话；B/worker/protocol.py:15/19只自身槽→会话，B/worker/jobs.py:47沿用双槽前置锁。BT/test_protocol.py:70真实PG屏障已独立跑通：pg_blocking_pids证明append等knowledge锁，第三连接FOR UPDATE NOWAIT成功，随后complete成功、append合法stale_version、刷新重试成功。BT/test_protocol.py:217另证明长期双租约独立。内部kind控制只验证知识槽协议，不代表正式知识管线完成。 |
| HIGH P3-F3：Vue嵌套Proxy令文件导入structuredClone崩溃 | 已关闭。F/api/mail-agent-request.ts:71改HTTP JSON编码快照；FT/mail-agent-request.test.ts:55实际reactive嵌套数组经浅展开可快照、后续修改不改变未知结果重试内容，独立通过。F/components/mail-agent/ConversationDialog.vue:126/167真实文件→深ref→浅展开入口已核对；docs/verification/PHASE-3-VALIDATION.md:92记录修后实际文件导入1封，之后推进3封；本实例查看history-light截图，真实前缀/独立审阅明确。 |

## Stage 1：功能逐条对照

以下“完整”只针对DEV-PLAN.md:91/92/93/101的Phase 3约定；部分或未实现明确保留后续归属，不把模型、业务和图片AC包装成完成。

| Spec条目 | 结论、实现与验证 |
|---|---|
| REQ-001:259 来源会话/消息ID、split、时间、重复/时间/引用检查 | 本期完整。B/domain/conversation.py:62/83、B/adapters/import_loader.py:12、B/application/replay.py:37、B/adapters/conversation_schema.py:55/158；BT/test_conversations.py:179/192真实PG/非法包/跨scope FK通过；实际GUI文件导入见VALIDATION:92。 |
| REQ-001:260 规范化发信身份归组 | 本期手工邮箱完整。B/domain/conversation.py:29 trim/域名小写，B/application/conversations.py:16锁后查询已有身份；BT/test_conversations.py:77同地址追加同会话通过。公开来源未经可信复核，不跨源归组。 |
| REQ-001:261 模式/分支记忆隔离 | 本期完整。B/application/conversation_base.py:34创建独立branch，B/adapters/conversation_schema.py:12/17完整scope FK；BT/test_conversations.py:192和BT/test_postgres.py:90逐维拒越界通过。重置/generation实际递增属Phase12。 |
| REQ-001:262 多订单、多待办、证据按问题关联 | 部分实现、符合Phase3基础范围。B/application/case_memory.py:9稳定correspondence issue及消息来源事实，BT/test_conversations.py:173主键跨截点稳定通过。语义多事项和订单关联待Phase4/7。 |
| REQ-001:263 group_id非身份 | 完整。B/application/replay.py:26独立来源会话/独立dataset，group_id仅data_imports元数据；BT/test_conversations.py:150同group不同来源不合并通过。 |
| REQ-001:264 身份缺失独立回放且标未验证 | 完整当前公开边界。B/domain/conversation.py:89拒浏览器identity_verified=true，F/components/mail-agent/ConversationList.vue:76明示未验证；BT/test_conversations.py:150/185通过。可信受控sender_key复核入口未开放。 |
| REQ-001:265 演示邮箱、不去加号/句点 | 完整。B/domain/conversation.py:36只规范域名；BT/test_conversations.py:77加号/句点保留、不同地址不合并通过。 |
| REQ-002:276 当前真实前缀、未来正文不泄漏 | 查询/任务协议层完整。B/application/conversation_queries.py:51 repeatable snapshot、第58/64行visible seq过滤；B/application/replay.py:60每次一客户截点。BT/test_conversations.py:150、真实HTTP网络脚本和history-light截图通过。模型上下文待Phase7。 |
| REQ-002:277 历史客服/独立对照、不继承对照 | 当前人工审阅完整；AI待Phase7。B/application/human_review.py:75只有simulation写Message，B/application/conversation_queries.py:71独立comparisons；F/components/mail-agent/MessageTimeline.vue:50历史客服文字，AgentProcessPanel.vue:62独立对照。BT/test_conversations.py:165/175及网络哨兵通过。 |
| REQ-002:278 从真实前缀重建事实 | 基础事实完整。B/application/case_memory.py:23替换旧投影，只读可见真实邮件，第31行记revision/as_of；BT/test_conversations.py:174/175事实3条、无对照哨兵通过。语义Understanding待Phase7。 |
| REQ-002:279 统一as_of、禁止当前快照回退 | 游标as_of完整：B/application/replay.py:41/68，BT/test_conversations.py:176截点2026-10-02T08:00Z通过。订单snapshot/知识available_at查询属Phase4/6，AC-006未验收。 |
| REQ-002:280 回放结束与解决分离、缺证据标注 | 本期结束不结案完整：B/application/replay.py:63、F/components/mail-agent/MessageComposer.vue:17/24，BT/test_conversations.py:177仍open。文本JSON没有附件/查单能力，相关提示待Phase4/8。 |
| REQ-003:291 新有效来信自动运行、不逐封审批 | 持久任务协议完整。B/application/conversation_base.py:64/80、B/application/task_queue.py:27原子cycle/run/job、B/worker/runner.py:33自动领取；BT/test_protocol.py:190新输入最新上下文完成通过。模型Phase7重验。 |
| REQ-003:292 最终校验后一次性自动模拟出站 | 未在本期实现，Phase7。B/worker/protocol.py:29仅真实protocol outcome，不写假AI邮件；BT/test_protocol.py:135协议完成后仍1封客户邮件通过。 |
| REQ-003:293 后续读取先前自动回复、每轮最多一封 | 自动AI产物未接，Phase7。B/adapters/conversation_schema.py:73已备cycle/final_message_id；BT/test_protocol.py:158同cycle显式retry和completed拒retry通过，不能替代AC-007/008/009。 |
| REQ-003:294 本地模拟、无真实投递 | 完整。F/components/mail-agent/AgentProcessPanel.vue:7明确未接模型/不发真实邮件，B/worker/protocol.py:13无provider/发送依赖；源码及网络结果provider_calls=0支持本期范围。 |
| REQ-003:295 重复点击/重试/刷新无重复效果 | 命令协议完整。B/application/idempotency.py:8同键同参原结果/异参409，B/application/conversations.py:35来源去重，F/api/mail-agent-request.ts:58未知结果原key/payload；BT/test_conversations.py:85、BT/test_protocol.py:118、FT/mail-workbench.test.ts:76通过，真实SSE补读不增run。 |
| REQ-007:382 缺依据/冲突等进入人审 | 模型handoff待Phase7。本期主动takeover完整：B/application/human_review.py:20，BT/test_protocol.py:176旧commit拒绝且新来信无自主任务通过；不声称AC-020。 |
| REQ-007:383 模型解释原因/缺口并程序核验 | 模型部分待Phase7；当前主动接管原因持久，F/components/mail-agent/HumanReviewPanel.vue:31明确摘要/查询未接。编译与真实GUI原因可见。 |
| REQ-007:384 接管摘要与未发送草稿 | 原因/可见邮件/草稿/备注基础完整，B/application/human_review.py:41、F/components/mail-agent/HumanReviewPanel.vue:24/47；BT/test_human_events.py:31旧save/reload通过。订单/已尝试/资料/决策摘要待Phase7。 |
| REQ-007:385 接管期间来信归并、不自主回复 | 完整。B/application/conversation_base.py:67/79保持human_review并suppressed，B/application/human_review.py:25撤销旧任务；BT/test_conversations.py:101与BT/test_protocol.py:176通过。 |
| REQ-007:386 回复/备注入会话、只下一新来信恢复 | 完整本期版本协议。B/application/human_review.py:63/82/90，B/application/conversation_base.py:67按持久接收序号恢复；BT/test_conversations.py:123、BT/test_human_events.py:58/77交换提交顺序通过；真实GUI见VALIDATION:89/90。 |
| REQ-007:387 再次HITL、方案不进全局知识 | 主动人审基础完整。B/application/human_review.py:28复用唯一open review，B/adapters/conversation_schema.py:135部分唯一索引；F/components/mail-agent/HumanReviewPanel.vue:21再次接管；真实GUI人审及PG通过，无知识写入。 |
| REQ-007:388 人工确认结案 | 完整。B/application/human_review.py:98唯一结案入口，B/worker/protocol.py:36不改resolved，F/views/mail-agent/index.vue:234确认；BT/test_conversations.py:140/BT/test_human_events.py:13及实际GUI结案/原会话重开通过。 |
| REQ-008:400 唯一轮次/触发/输入权限版本及记录 | 本期字段完整。B/adapters/conversation_schema.py:73/86/99、B/application/task_queue.py:38服务绑定版本；BT/test_protocol.py:158保持cycle并递增attempt通过。模型/资料/工具/usage待Phase7/11。 |
| REQ-008:401 简短可验证过程、不存隐藏思维链 | 本期真实协议记录完整。F/components/mail-agent/AgentProcessPanel.vue:39/49只展示真实任务结果，无虚构工具或token；编译和network outcome通过。业务工具过程待Phase7。 |
| REQ-008:402 会话串行、新输入/接管旧提交无效 | 完整协议层。B/worker/leases.py:23/38、B/worker/protocol.py:15/26租约/输入/权限栅栏、B/application/task_queue.py:9关闭checkpoint资格和递增fence；BT/test_protocol.py:176/190通过。双槽锁序另见已关闭P3-F2。 |
| REQ-008:403 停止/重试/刷新恢复，晚到拒绝 | 完整。B/worker/jobs.py:58/80、B/worker/leases.py:96中断须显式retry；F/components/mail-agent/AgentProcessPanel.vue:27/35真实入口；BT/test_protocol.py:135/158/204通过，completed拒retry。正式模型副作用Phase7重验。 |
| REQ-008:404 技术失败类别、不伪装业务结论 | 本期user_stopped/worker_interrupted持久错误完整：B/worker/jobs.py:64、B/worker/leases.py:116；B/api/conversations.py:24安全HTTP类别；BT/test_api.py与BT/test_protocol.py通过。模型鉴权/解析/超时待Phase7。 |
| REQ-008:405 调用/无进展/预算限制 | 模型循环待Phase7。B/worker/runner.py:35每任务一次protocol commit，未伪造预算或token；本期34项PG/API和网络provider_calls=0，不宣称完整REQ。 |
| REQ-008:406 售后写去重/未知结果对账/停止保账本 | 售后账本与工具待Phase9/10。本期内部record-only B/application/event_store.py:43去重/人工抑制，BT/test_human_events.py:77通过；无HTTP假ERP注入，不替代售后验收。 |
| REQ-009:417 Art Design Pro外壳/chat/三栏 | 外壳、主题、El组件及三栏完整，F/views/mail-agent/index.vue:6/11/113，复制来源FRONTEND-BASELINE.md:3；独立build和实渲染邻居对比支持。阅读位置因P3-R2不通过，不据“复用组件”免除。 |
| REQ-009:418 模式/客户/最新来信/状态可辨 | 完整。F/components/mail-agent/ConversationList.vue:60/68/75、F/views/mail-agent/index.vue:39/42、MessageComposer.vue:8；FT/mail-workbench.test.ts:102/120和明暗实际截图通过。 |
| REQ-009:419 右侧过程/中间正式邮件/独立对照 | 完整本期。F/components/mail-agent/MessageTimeline.vue:9只messages，AgentProcessPanel.vue:22/62分区；BT/test_conversations.py:168/175、network哨兵和history-light截图通过。 |
| REQ-009:420 来源文字/图标、不只颜色 | 当前客户/历史客服/模拟人工完整，F/components/mail-agent/MessageTimeline.vue:15/20/48标签/Avatar；AgentProcessPanel.vue:74人工独立对照，明暗截图可辨。AI/Mock待后续，无假AI邮件。 |
| REQ-009:421 推进/来信/人工完成/结案/停止重试/重置删除 | 本期前6项完整且真实API：F/views/mail-agent/index.vue:95/120/124、HumanReviewPanel.vue:79/112、MessageComposer.vue:11/61；PG/前端测试与GUI正常流程通过。重置/删除Phase12，无可点击死入口。 |

## Stage 1：页面、共用状态及输入

| 条目 | 本期结论与证据 |
|---|---|
| 5.10复用外壳、路由、主题、聊天/表单 | F/views/mail-agent/index.vue:6/11/155使用既有page-content、RuntimeStatus与业务组件，ElDialog/Drawer/Form/Button等沿用模板；FRONTEND-BASELINE.md:3/25记录实际独立副本。明暗工作台与邻居实图对比见后文。没有设计稿/Design-Brief，按现有工程先例审查。 |
| SCREEN-001、CMP-001列表 | 本期会话/状态/模型标记、模式筛选、导入、新建、分页/选择完整。F/components/mail-agent/ConversationList.vue:7/36/50/81、F/components/business/runtime-status.vue:15，FT/mail-workbench.test.ts:120与实图通过；重置/删除Phase12。 |
| CMP-002中间邮件 | 本期文本/来源/独立对照完整，F/components/mail-agent/MessageTimeline.vue:20/31、AgentProcessPanel.vue:62；历史1→3封实测通过。图片缩略图/逐图状态/模型语言分析Phase7/8。 |
| CMP-003底部输入 | 文本来信与历史按钮/进度完整，F/components/mail-agent/MessageComposer.vue:3/25/61；人审期间可新增，PG/API及GUI通过。仅图片/上传移除Phase8。 |
| CMP-004右侧处理 | 本期运行/停止/显式重试完整，F/components/mail-agent/AgentProcessPanel.vue:22/27/35/39；FT/BT协议测试通过。诉求/工具/引用/usage/trace待Phase7/11。 |
| CMP-005右侧人审 | 本期原因/草稿/备注/明确核对/完成/结案完整，F/components/mail-agent/HumanReviewPanel.vue:24/35/47/79/112；PG和GUI旧草稿屏障通过。模型接管摘要待Phase7。 |
| CMP-007导入/移除 | 当前受控JSON选择、数量提示、校验失败保留及成功导入完整，F/components/mail-agent/ConversationDialog.vue:51/70/164；reactive回归与实际文件导入通过。知识上传/下架/彻底删除Phase5/6/12。 |
| SCREEN-002、CMP-006/008/009/010/011/012/013 | 知识、引用、业务单、模拟控制、编辑核对/版本/试查、图片证据属Phase4–12。本期F/views/knowledge/index.vue:4真实说明未接；没有假的查询或成功入口；B/application/event_store.py:43不开放HTTP注入。 |
| 5.10:562多行文本、明确提交/无电话视频 | F/components/mail-agent/MessageTimeline.vue:31纯文本保留换行，MessageComposer.vue:42/61明确按钮，FT/mail-agent-request.test.ts:66输入校验通过。不存在电话/视频业务入口。 |
| 5.10:562与5.11成功态阅读位置 | **不通过P3-R2**；F/components/mail-agent/MessageTimeline.vue:47/58/63缓存初始失配，首次静止阅读外部SSE路径确实跳到底，未被18项前端测试覆盖。 |
| 5.10:584桌面/窄面板 | F/views/mail-agent/index.vue:11/113左260/右360，第211行依内容宽度<1024改drawer，<640纵排。1600×1000与1280×800实图可读，主Agent页面/body宽度不超viewport断言见VALIDATION:94；不声称手机精细适配完成。 |
| 5.11默认 | F/views/mail-agent/index.vue:100未选时ElEmpty，F/composables/useMailWorkbench.ts:84选择仅GET；FT/mail-workbench.test.ts:17及无新增run网络证据通过。 |
| 5.11加载 | F/components/mail-agent/ConversationList.vue:44、F/views/mail-agent/index.vue:79加载反馈，composable:114/147 busy门禁；前端/实际API与build通过。 |
| 5.11空 | ConversationList.vue:45、AgentProcessPanel.vue:24、MessageComposer.vue:17分别无会话/无任务/回放结束；实图历史末截点仍open。订单/知识空态后续接入。 |
| 5.11错误 | F/api/mail-agent-request.ts:13安全类别、F/composables/useMailWorkbench.ts:133保留并409刷新、ConversationDialog.vue:176保留输入；FT/mail-workbench.test.ts:43/76及真实网络abort→同key重试记录VALIDATION:95通过。 |
| 5.11成功 | F/composables/useMailWorkbench.ts:127/155/185真实反馈，人工模拟发送/审阅完成实图可见。**阅读位置子项因P3-R2失败。** |
| 5.11受限 | B/application/conversations.py:33历史只读；MessageComposer.vue:14阻止active/human推进；AgentProcessPanel.vue:7准确未接模型。本期零模型协议无需Key，不提供假模型运行；删除入口Phase12。PG/API测试通过。 |
| 5.12 mode | B/domain/conversation.py:8/65、B/application/conversation_base.py:34服务绑定模式，不可原地任意切scope；BT/test_conversations.py:192跨scope拒绝通过。 |
| 5.12 sender_email/sender_key | B/domain/conversation.py:24/29/88/89校验320字符、域名规范、未可信复核；mail-inputs.ts:20前端邻近校验，BT/test_conversations.py:77/185通过。 |
| 5.12 subject | B/domain/conversation.py:14/67最多500，MessageTimeline.vue:30空主题占位；FT/mail-agent-request.test.ts:66超长和纯文本通过。 |
| 5.12 body | B/domain/conversation.py:13/18/68/79非空/20000，MessageTimeline.vue:31文本插值；BT/test_conversations.py:235脚本文字不执行、FT/mail-agent-request.test.ts:66通过。本期图片条件Phase8。 |
| 5.12 customer_images | Phase8，当前导入schema禁止额外字段/任意路径，B/domain/conversation.py:8/63；BT/test_conversations.py:185通过，不假称图片输入已实现。 |
| 5.12 as_of | B/domain/conversation.py:70强制时区，B/application/replay.py:68游标生成且不接受任意as_of字段；BT/test_conversations.py:176/185通过。 |
| 5.12 order_id | Phase4尚未查询，当前无假查单；DEV-PLAN.md:103及B/api/conversations.py:30公开路由范围支持。 |
| 5.12 human_reply/note | B/domain/conversation.py:47/53/58、mail-inputs.ts:30限制20000/5000、完成非空；PG版本屏障及FT/mail-agent-request.test.ts:66通过。 |
| 5.12 document | Phase5知识受控导入，当前只历史JSON，ConversationDialog.vue:51/65正确说明，不冒充知识输入。 |
| 5.12 business_action/scenario_event | Phase9/10，B/application/event_store.py:43仅内部通知、无HTTP假ERP；公开ImportCase额外字段拒绝，BT/test_conversations.py:185通过。 |
| 5.12 request_id/expected_version | B/application/idempotency.py:8、conversation_lock.py:22、F/composables/useMailWorkbench.ts:118/148客户端自动带；PG重复/版本、前端未知结果同key/payload及GUI真实重试通过。 |

### AC与指定故障时序

| 条目 | 已证实的当前层及未验收边界 |
|---|---|
| AC-001/002/003 | BT/test_conversations.py:77/85/150真实PG同邮箱追加、同group不跨源合并、重复请求/消息/来源不增任务通过；不代表可信身份复核接入已完成。 |
| AC-004/005/027 | BT/test_conversations.py:150、网络脚本:71和实际历史GUI验证真实前缀/人工独立对照/未来哨兵。AI请求/产物尚未接，不能标完整AI AC通过。 |
| AC-006 | 未验收，订单snapshot属Phase4；B/application/replay.py:68只有as_of基础，不假称已有历史查单。 |
| AC-007/008/009 | 自动AI出站和此前AI回复记忆属Phase7，未验收；B/worker/protocol.py:29只协议结果，BT/test_protocol.py:135无新增邮件通过。 |
| AC-020/022 | 模型自动handoff、正式模型恢复输入属Phase7；当前主动接管和后续新输入资格基础由BT/test_protocol.py:176、BT/test_conversations.py:123验证，不标全项通过。 |
| AC-021/023 | 人审来信无自主任务、人工才resolved的当前层通过BT/test_conversations.py:101/140/177和BT/test_human_events.py:13；模型解决建议分支待Phase7。 |
| AC-024/025/026 | 旧任务提交拒绝、stop/interrupted/retry、持久状态及GET不重跑的协议层通过BT/test_protocol.py:135/158/176/190/204；真实模型超时/自动出站/checkpoint仍待Phase7。 |
| AC-028/032 | 当前主动人审可操作，模板外壳/主题/无模板登录依赖有代码、前端测试和真实GUI证据；模型摘要/引用未接，P3-R2阅读位置子项不通过，不能签完整工作台体验PASS。 |
| FT-01 | BT/test_protocol.py:176/190新输入/接管后旧complete=False，最新任务处理新版本，真实PG通过；真实旧模型与业务写副作用Phase7/9重验。 |
| FT-02 | BT/test_human_events.py:58/77交换内部业务通知/人工回复提交顺序，过期409、业务suppressed、只有之后客户来信恢复；第31行旧草稿reload屏障通过，GUI见VALIDATION:88/89。 |
| FT-05 | BT/test_protocol.py:135/158/204租约/重启中断、原cycle显式retry、completed拒retry通过。业务commit→checkpoint丢失→重启的完整FT-05尚未执行，Phase7/9。 |
| FT-07 | B/application/event_store.py:43内部record-only与BT/test_human_events.py:77去重/人审抑制通过；wait注册先后、补查、wake_pending消费Phase10，未验收。 |
| FT-08 | BT/test_conversations.py:150、network脚本:71/95、历史GUI真实前缀和人工对照哨兵通过；未来订单/知识/AI上下文在Phase4/6/7重验。 |
| UI事件事务/真实SSE | B/application/event_store.py:14/16会话锁内seq与事实同commit，B/api/events.py:25/35/55/70支持游标/Last-Event-ID/15秒心跳。独立额外PG两连接屏障seq=[2,3]通过；网络实际HTTP补读/heartbeat/只读重连通过。F/composables/conversation-event-session.ts:27/52/66校验scope、去重、切会话关闭。 |

### Spec漂移与引导真实性

本轮没有新增阻塞scope creep。B/api/conversations.py:11/34只提供受控输入样例；B/worker/protocol.py:30真实说明模型未接，不生成假回复；B/application/event_store.py:43为内部竞争接口、不开放假ERP；globalmail-agent/scripts/phase3-test-server.py:31隔离schema/临时对象/端口属于验收设施。它们有PHASE-3-CONTRACT/IMPLEMENTATION范围依据。F/components/mail-agent/AgentProcessPanel.vue:7、F/views/knowledge/index.vue:4明确后续能力，没有指向不存在模型/知识/删除行为的成功入口。界面阅读位置问题单独列P3-R2，不用准确阶段文案掩盖。

## Stage 2：发现新滚动问题前已经完成的检查

本节保留实际证据；**不形成最终Stage 2 PASS**。新问题属于Stage1 UI契约，主Agent须修后派fresh从Stage1重来。

| 维度 | 结论与证据 |
|---|---|
| 文件大小/职责/类型 | 审查时58个增量Python/TS/Vue文件无超过300行：最长F/composables/useMailWorkbench.ts:1为262行，页面247、BT/test_conversations.py239、BT/test_protocol.py230、migration216。F/api/mail-agent-contract.ts:22/54/64/82明确契约，frontend/tsconfig.json:6 strict=true；独立vue-tsc通过。核心TS扫描无any，Python的any()为内置谓词而非类型绕过。会话/回放/人审/查询、租约/提交/控制和API分工明确。 |
| 冻结迁移一致性 | backend/migrations/versions/0002_conversations_jobs.py:9独立冻结metadata，第198行升级，不动态导入未来业务schema；B/adapters/conversation_schema.py:5注册运行metadata，database.py:8/34检查版本及所有表列。独立随机schema升级后Alembic compare_metadata输出[]。迁移定义重复是历史冻结所需。 |
| 事务/正文/隔离 | B/application/conversation_base.py:22事务异常清理新文件；B/adapters/body_store.py:19/37同conn登记对象/依赖，第50/55行完整scope+摘要读取；BT/test_conversations.py:192跨scope FK与真实失败清理通过，BT/test_postgres.py:90逐维scope通过。崩溃孤儿对象/彻底删除仍Phase12。 |
| 秘钥与错误 | 增量源码扫描无硬编码实际Key、公开VITE密钥、任意路径输入、eval/v-html/innerHTML/dangerouslySetInnerHTML；B/api/conversations.py:24/26、B/main.py:43/52、B/worker/runner.py:38安全类别，不打印raw SQL/凭据。BT/test_api.py:57和BT/test_postgres.py:104 SECRET_MARKER不泄漏通过。私有database_url仅注入环境，未输出。 |
| SQL/XSS/任意资源 | B/application/idempotency.py:12及replay.py:15绑定参数；F/components/mail-agent/MessageTimeline.vue:31纯文本；B/adapters/body_store.py:26使用服务器UUID路径。BT/test_conversations.py:235 HTML保持文本、非法导入路径拒绝通过；随机schema的f-string SQL只在隔离测试内，用uuid4生成标识，不是公开用户SQL。未发现新增安全HIGH。 |
| Host/Origin/CORS | B/api/security.py:23/35/37校验唯一合法Host/Origin，写入需JSON，OPTIONS允许PATCH/Idempotency-Key/Last-Event-ID；BT/test_api.py:42/48恶意Host/Origin、preflight/write protection通过。B/api/events.py:74 no-store且事件仅安全状态/ID。 |
| 启动/readiness | B/main.py:28只要engine存在即启动runner，B/worker/runner.py:28/31首次失败后保持restart恢复；B/adapters/database.py:33/34及B/api/system.py:16真实依赖/列/版本检测。BT/test_postgres.py:50/104/123与BT/test_api.py:36通过。前一轮额外故障恢复保留其原始报告，不冒充本轮重新做了物理PG停机。 |
| 后端测试真实性 | BT/test_conversations.py:31、BT/test_protocol.py:31随机schema/TemporaryDirectory及addCleanup，生产service/合法Pydantic命令和真实迁移/PG；34项无skip。过期测试显式设置过去DB租约，BT/test_protocol.py:135；知识槽:70真实Event/pg_blocking_pids/NOWAIT，未依靠随机sleep撞竞态。内部kind控制不代表知识生产管线。 |
| 前端故障/交互真实性 | FT/mail-workbench.test.ts:17/43/76/102/120/138直接调用生产composable，覆盖GET无写、409保留、未知结果原命令、晚到响应、分页和review/input版本；FT/mail-agent-request.test.ts:55真实Vue reactive嵌套Proxy回归。实际GUI导入、过期草稿、网络abort/同key重试补足普通对象/纯函数盲区。 |
| SSE测试边界 | FT/conversation-events.test.ts:77使用受控Stream验证scope/去重/切换/晚到，不冒充真实浏览器重连；network脚本:36/57实际HTTP补读/15秒心跳补齐服务端流证据。独立额外两连接PG屏障补齐已有串行事件测试未覆盖的commit顺序。 |
| 本轮暴露的测试盲区 | 18项前端测试没有实际挂载MessageTimeline和真实DOM几何；F/components/mail-agent/MessageTimeline.vue:47默认true的前提未经验证。独立代码检查配合要求主Agent补初挂载静止阅读实测发现P3-R2。需修后补该生产可达前提，不能把“34/18全绿”当整期完成。 |

### 实际视觉与邻居对比

本实例逐张打开主Agent实际浏览器截图查看：明色三栏、历史前缀、暗色三栏、明暗窄屏drawer、明暗知识邻居和网络故障图；没有通过DOM注入假业务结果。浏览器操作由主Agent执行并记录于docs/verification/PHASE-3-VALIDATION.md:85；本实例据真实渲染图独立视觉判断，不声称自己重复操作了同一浏览器。

- [明色工作台](../../output/playwright/phase3-light-wide.png)与[明色知识邻居](../../output/playwright/phase3-knowledge-light.png)：同一侧栏/顶栏/页签、内容卡片边框圆角、主色按钮、表单与文字层级；三栏确为260/360和自适应中间，邮件来源标签、模拟人工、当前模式可读。实现位置F/views/mail-agent/index.vue:6/11/113、ConversationList.vue:55、MessageTimeline.vue:27。
- [暗色工作台](../../output/playwright/phase3-dark-wide.png)与[暗色知识邻居](../../output/playwright/phase3-knowledge-dark.png)：同一外壳/卡片背景、文字、边框、主色和选中态；客户邮件、模拟人工与过程区仍能辨认，没有新增明色硬编码白底。实现位置F/components/mail-agent/MessageTimeline.vue:27/28与公共主题。
- [明色抽屉](../../output/playwright/phase3-light-narrow-drawer.png)、[暗色人审抽屉](../../output/playwright/phase3-dark-narrow-drawer.png)：1280×800右侧变drawer，人审原因/表单可读、抽屉可纵向阅读。F/views/mail-agent/index.vue:131/211基于内容宽度阈值；VALIDATION:94真实页面/body宽度断言不超viewport。手机精细适配没有验收声明。
- [历史渲染](../../output/playwright/phase3-history-light.png)三封真实邮件均有来源，人工独立对照不占中间正式邮件位置；回放2/2结束不等于已解决。实现位置MessageTimeline.vue:20/50、MessageComposer.vue:17/24、AgentProcessPanel.vue:62/74。
- [故障渲染](../../output/playwright/phase3-network-error.png)保留人审输入与明确连接错误；VALIDATION:95记录解除真实PATCH网络拦截后同Idempotency-Key重试成功。实现位置F/api/mail-agent-request.ts:19、composable:119/133/137。
- 静态截图不能证明保持阅读位置；P3-R2最终由实际初挂载/SSE数值和源码确认，不给予视觉整体PASS。

## 本轮独立命令与原始输出

后端cwd为globalmail-agent/backend。连接串只从根目录私有设置注入环境，不打印。首次误用一级相对路径得到28项skip的尝试已废弃，不作通过依据；修正为二级根目录路径后才完成下面34项真实PG测试。全部隔离随机schema/Temp对象目录并清理，不写用户会话数据。

    $ErrorActionPreference='Stop'
    $phaseReviewSettings=Get-Content -LiteralPath ../../.local-data/runtime/settings.json -Raw | ConvertFrom-Json
    $env:GLOBALMAIL_TEST_DATABASE_URL=$phaseReviewSettings.database_url
    $env:PYTHONPATH=(Resolve-Path src).Path
    & .venv/Scripts/python.exe -m unittest discover -s tests -v


后端原始输出（exit_code=0，无skip）：

    D:\Work_Project\globalmail-agent\globalmail-agent\backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
      from starlette.testclient import TestClient as TestClient  # noqa
    test_bad_hosts_and_origins_rejected (test_api.ApiTests.test_bad_hosts_and_origins_rejected) ... ok
    test_live_and_safe_runtime (test_api.ApiTests.test_live_and_safe_runtime) ... ok
    test_non_local_config_rejected (test_api.ApiTests.test_non_local_config_rejected) ... ok
    test_preflight_and_write_protection (test_api.ApiTests.test_preflight_and_write_protection) ... ok
    test_readiness_degraded_without_database (test_api.ApiTests.test_readiness_degraded_without_database) ... ok
    test_validation_and_exceptions_are_sanitized (test_api.ApiTests.test_validation_and_exceptions_are_sanitized) ... ok
    test_api_errors_and_controls_have_safe_envelopes (test_conversations.ConversationTests.test_api_errors_and_controls_have_safe_envelopes) ... ok
    test_close_revokes_and_new_customer_message_reopens (test_conversations.ConversationTests.test_close_revokes_and_new_customer_message_reopens) ... ok
    test_event_commit_order_safety_and_after_cursor_are_read_only (test_conversations.ConversationTests.test_event_commit_order_safety_and_after_cursor_are_read_only) ... ok
    test_history_cannot_advance_active_run_and_import_validates_schema (test_conversations.ConversationTests.test_history_cannot_advance_active_run_and_import_validates_schema) ... ok
    test_history_real_prefix_group_id_and_comparison_isolation (test_conversations.ConversationTests.test_history_real_prefix_group_id_and_comparison_isolation) ... ok
    test_input_before_human_reply_conflicts_and_preserves_draft (test_conversations.ConversationTests.test_input_before_human_reply_conflicts_and_preserves_draft) ... ok
    test_manual_identity_grouping_preserves_plus_and_dots (test_conversations.ConversationTests.test_manual_identity_grouping_preserves_plus_and_dots) ... ok
    test_reply_before_next_input_waits_and_next_local_sequence_resumes (test_conversations.ConversationTests.test_reply_before_next_input_waits_and_next_local_sequence_resumes) ... ok
    test_request_replay_same_key_conflict_and_source_duplicate (test_conversations.ConversationTests.test_request_replay_same_key_conflict_and_source_duplicate) ... ok
    test_scoped_foreign_keys_and_transaction_failure_cleanup (test_conversations.ConversationTests.test_scoped_foreign_keys_and_transaction_failure_cleanup) ... ok
    test_business_notification_before_reply_conflicts_until_rechecked (test_human_events.HumanEventTests.test_business_notification_before_reply_conflicts_until_rechecked) ... ok
    test_closed_conversation_rejects_takeover_and_new_input_reopens_without_review (test_human_events.HumanEventTests.test_closed_conversation_rejects_takeover_and_new_input_reopens_without_review) ... ok
    test_reply_before_business_notification_does_not_resume_and_duplicates_do_not_queue (test_human_events.HumanEventTests.test_reply_before_business_notification_does_not_resume_and_duplicates_do_not_queue) ... ok
    test_saving_stale_draft_and_reloading_does_not_acknowledge_new_input (test_human_events.HumanEventTests.test_saving_stale_draft_and_reloading_does_not_acknowledge_new_input) ... ok
    test_database_failure_and_missing_table_are_degraded (test_postgres.PostgresTests.test_database_failure_and_missing_table_are_degraded) ... protocol_worker_dependency_unavailable
    ok
    test_every_scope_dimension_is_enforced (test_postgres.PostgresTests.test_every_scope_dimension_is_enforced) ... ok
    test_migration_repeat_restart_and_ready (test_postgres.PostgresTests.test_migration_repeat_restart_and_ready) ... ok
    test_missing_schema_and_unwritable_store_degraded (test_postgres.PostgresTests.test_missing_schema_and_unwritable_store_degraded) ... ok
    test_path_and_digest_protection (test_postgres.PostgresTests.test_path_and_digest_protection) ... ok
    test_source_dependency_and_scope_database_constraint (test_postgres.PostgresTests.test_source_dependency_and_scope_database_constraint) ... ok
    test_knowledge_completion_and_new_input_keep_slot_before_conversation_lock_order (test_protocol.ProtocolTests.test_knowledge_completion_and_new_input_keep_slot_before_conversation_lock_order) ... ok
    test_knowledge_slot_does_not_occupy_agent_slot (test_protocol.ProtocolTests.test_knowledge_slot_does_not_occupy_agent_slot) ... ok
    test_lease_expiration_blocks_old_commit_and_requires_explicit_retry (test_protocol.ProtocolTests.test_lease_expiration_blocks_old_commit_and_requires_explicit_retry) ... ok
    test_new_message_supersedes_running_and_queues_latest_context (test_protocol.ProtocolTests.test_new_message_supersedes_running_and_queues_latest_context) ... ok
    test_restart_interrupts_active_but_preserves_unclaimed_queue (test_protocol.ProtocolTests.test_restart_interrupts_active_but_preserves_unclaimed_queue) ... ok
    test_single_slot_concurrent_claim_and_read_only_refresh (test_protocol.ProtocolTests.test_single_slot_concurrent_claim_and_read_only_refresh) ... ok
    test_stop_retry_retains_cycle_and_late_result_has_no_effect (test_protocol.ProtocolTests.test_stop_retry_retains_cycle_and_late_result_has_no_effect) ... ok
    test_takeover_and_new_input_barriers (test_protocol.ProtocolTests.test_takeover_and_new_input_barriers) ... ok

    ----------------------------------------------------------------------
    Ran 34 tests in 18.005s

    OK

其中 StarletteDeprecationWarning 是现有测试客户端依赖警告；protocol_worker_dependency_unavailable 来自受控坏数据库降级测试。没有输出实际连接串。

前端cwd为globalmail-agent/frontend，执行 pnpm exec tsx --test scripts/*.test.ts（exit_code=0）：

    ✔ 事件只接受本会话作用域并按序去重 (1.037ms)
    ✔ 连接带after_seq；断线保持同连接让原生EventSource补读；切会话取消旧连接与晚到事件 (1.0943ms)
    ✔ 跨作用域或畸形事件关闭流，给出明确刷新恢复路径 (0.3104ms)
    ✔ 清理已持久化的模板页签，保留业务页签和其参数 (1.3634ms)
    ✔ 接受真实200/202资源，拒绝HTTP和envelope不一致以及空资源 (1.4927ms)
    ✔ 未知结果重试沿用key和原payload版本，只有新参数或已完成才另建命令 (0.253ms)
    ✔ 响应式导入对象按HTTP JSON编码快照，编辑后不改变未知结果重试内容 (0.5957ms)
    ✔ 表单校验覆盖空白、长度、邮箱及保留换行 (0.3057ms)
    ✔ 受控文件输入读取JSON，拒绝错误扩展、非法JSON和超限文件 (2.2668ms)
    ✔ 选择/刷新只GET，不生成任务；输入按会话保存；服务错误有真实状态 (3.374ms)
    ✔ 人工提交409保留文本并刷新；新来信不能静默重绑定草稿，明确核对后才使用新输入版本 (1.3393ms)
    ✔ 网络结果未知后即使快照更新，重试仍是同key和同payload；成功才清空来信 (0.7741ms)
    ✔ 快速切换会话时忽略前一会话晚到快照 (0.2703ms)
    ✔ 列表分页和模式/状态过滤传给服务端，过滤变化重置页码 (0.7114ms)
    ✔ 人审草稿PATCH使用review版本，完成人工回复另带会话和输入版本 (0.37ms)
    ✔ 接受实际HTTP200存活与503依赖故障 (1.0113ms)
    ✔ 拒绝假成功、失配状态及非法配置 (0.2896ms)
    ✔ 运行配置仅接受当前阶段实际能力标志 (0.173ms)
    ℹ tests 18
    ℹ suites 0
    ℹ pass 18
    ℹ fail 0
    ℹ cancelled 0
    ℹ skipped 0
    ℹ todo 0
    ℹ duration_ms 580.7223

同cwd执行 pnpm build，原始诊断及完成输出如下（exit_code=0）。仅省略dist资源尺寸清单；类型检查与Vite构建均完成，未在本轮更改依赖版本。

    $ vue-tsc --noEmit && vite build
    🚀 API_URL = /api/v1
    🚀 VERSION = 0.2.0
    vite v7.1.7 building for production...
    transforming...
    ✓ 3255 modules transformed.
    rendering chunks...

    [省略生成资源尺寸清单]
    ✓ built in 25.31s

后端cwd执行编译检查，命令与原始结果：

    $env:PYTHONPATH=(Resolve-Path src).Path
    & .venv/Scripts/python.exe -m compileall -q src migrations tests
    Write-Output "compileall_exit=$LASTEXITCODE"

    compileall_exit=0

补充独立真实PG检查使用BT/test_protocol.py:31的生产迁移/随机schema/Temp目录fixture，finally执行doCleanups。第一事务持有会话锁，第二事务追加安全UI事件，观察pg_blocking_pids确认等待后才释放第一事务；检查两事件的序号及提交顺序。迁移与运行metadata同时比较。原始结果（exit_code=0）：

    migration_metadata_diffs []
    fresh_two_connection_commit_order {'second_confirmed_blocked': True, 'sequences': [2, 3], 'kinds': ['review.fresh.first', 'review.fresh.second']}

主Agent网络实测证据tmp/phase3-network-check.json及tmp/phase3-network-check.py:36/57/71已读取；本实例未再并行启动测试server。其原始记录的status=passed、provider_calls=0，四个checks为：

    real_SSE_Last_Event_ID_reconnect_preserves_order_and_scope
    15_second_heartbeat_and_read_only_reconnect_no_new_task
    invalid_and_future_event_cursors_rejected
    real_HTTP_history_prefix_and_human_comparison_isolation

这些记录使用独立测试server的临时PG schema/对象目录，不是用户数据库会话。真实GUI写入也由主Agent在同一隔离服务执行；本实例没有调用付费模型或发出伪造AI邮件。

## 交回与下一轮范围

本轮不能完成Phase3签收：Stage1新增MEDIUM P3-R2仍须修后fresh重审。原四项问题已在本轮独立复验关闭；34个后端测试、18个前端测试、vue-tsc/Vite构建、compileall、真实PG提交顺序与迁移一致性均通过，不能替代实际初挂载阅读位置路径。

按code-review技能闭环，Stage1功能不匹配回开发修复。主Agent已通知修复；本实例按明确派发范围保留发现时FAIL，不复审新提交。下一fresh应从Stage1重新完整核对，重点验证“已有溢出会话首次挂载、没有scroll事件、外部来信/SSE刷新仍保留位置”与底部/主动提交的滚动分支，然后才能签Stage2与最终结论。不得据本报告宣称AC006、真实AI业务处理、完整waiting-wake、知识产线、图片或删除已验收。
