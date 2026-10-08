# Phase 3 最终独立两阶段审查

日期：2026-10-08。审查者：fresh code-reviewer；从 Stage 1 全范围重新审查，之后执行 Stage 2。未修改源码、提交 Git、调用模型或另启浏览器测试服务器。

**结论：Stage 1 PASS，Stage 2 PASS；Phase 3 约定的技术交付通过。五项旧缺陷关闭；没有新增 HIGH/MEDIUM，另有一项非阻塞 LOW 文案字典建议。** 这是会话、历史前缀、人审与持久任务协议的阶段验收，不是七类业务、正式模型回复或整个产品的验收。

## 审查依据、范围与证据归属

已读取 AGENTS.md、[code-review skill](../../.agents/skills/code-review/SKILL.md)、DEV-PLAN Phase 3 全文、Product-Spec REQ-001/002/003/007/008/009 与 5.10–5.12 原文、AGENT-ARCHITECTURE 第2/3/6/8节、AGENT-ACCEPTANCE FT-01/02/05/07/08，以及 PHASE-3-CONTRACT、IMPLEMENTATION、VALIDATION 和前三次审查报告。依据源条目是 `DEV-PLAN.md:91/92/93/101`；前三次 FAIL 不被改写。

路径简称：B/＝`globalmail-agent/backend/src/globalmail_agent/`，F/＝`globalmail-agent/frontend/src/`，BT/＝`globalmail-agent/backend/tests/`，FT/＝`globalmail-agent/frontend/scripts/`。下表位置均对应本次最终源码。

本实例独立执行真实 PG 的34项测试、前端18项测试、Python编译、vue-tsc/Vite构建、迁移 metadata 比较和两连接事件提交屏障；逐张用 view_image 查看8张真实浏览器渲染图。GUI操作和真实HTTP/SSE采集由主 Agent 在隔离15174/18181服务完成，本实例读取原始记录和测试脚本并核对生产源码，不声称自己重复操作了该浏览器。测试服务已清理，未另起第二服务；独立测试只创建随机schema/TemporaryDirectory，并执行清理，未往正式用户会话写测试邮件。

本期公开导入只接受未复核身份的独立历史案例；group_id不授权身份。真实模型与语义多事项Phase7，订单历史snapshot Phase4，知识管线Phase5/6，完整wait/wake Phase10，图片Phase8，完整删除Phase12。没有假AI回复、付费模型或真实投递；没有宣称完整AC-006或完整FT-05/07通过。

## Stage 1：五项旧问题关闭

| 旧问题 | 最终代码与本次证据 | 结论 |
|---|---|---|
| HIGH P3-R1：保存旧草稿/刷新静默承认最新输入 | B/domain/conversation.py:47必填expected_input_revision；B/application/human_review.py:51拒未来版、第58行保存实际核对版、第66行回复核验。F/composables/useMailWorkbench.ts:74从review版初始化、第196行保存旧版、第259行才明确核对。BT/test_human_events.py:31真实新输入→旧save→reload→仍旧版→完成拒绝且消息仍2封，本次ok；FT/mail-workbench.test.ts:43/138本次ok；VALIDATION:89/90的实际整页刷新后仍disabled及明确核对后发送补齐GUI。 | 关闭 |
| MEDIUM P3-F1：resolved接管留下孤立open review | B/application/human_review.py:23在invalidate及任何写之前拒非open；BT/test_human_events.py:13本次ok：合法close→takeover返回conversation_not_open，会话完全不变且无review，新来信重开agent并可领取。 | 关闭 |
| MEDIUM P3-F2：knowledge→conversation与agent→conversation→knowledge死锁 | B/application/conversation_lock.py:16按slot_key排序先取agent/knowledge再取会话；B/worker/protocol.py:15/19只取自身槽再会话；JobService沿用前置双槽锁。BT/test_protocol.py:70本次ok：真实Event屏障、pg_blocking_pids确认append等待knowledge，第105行NOWAIT能取会话，completion成功、旧版append正确409，刷新重试成功。第217行双长期租约同时成立并分别完成。 | 关闭 |
| HIGH P3-F3：合法文件经Vue嵌套Proxy无法structuredClone | F/components/mail-agent/ConversationDialog.vue:126/167仍是实际ref→浅展开生产路径；F/api/mail-agent-request.ts:71改为HTTP JSON编码独立快照。FT/mail-agent-request.test.ts:55本次ok，真实reactive嵌套数组可快照、后续修改不污染未知结果重试；VALIDATION:93/94实际文件导入先1封、独立审阅后推进3封及history-light实图支持GUI。 | 关闭 |
| MEDIUM P3-R2：首次溢出挂载静止阅读遇SSE强跳底部 | F/components/mail-agent/MessageTimeline.vue:51/56在默认preflush消息watch中读取当前旧DOM距离，距离>=48时保留；第75行主动scrollSignal强制，已删除默认true缓存和scroll事件依赖。VALIDATION:97真实reload→选7封溢出会话→无scroll/wheel：before top0/height939/client324，外部POST来信经SSE后top仍0；实际wheel上翻后下一外部消息仍top0；主动追加top1043/height1327/client284，1327−284=1043。独立前端18项及build在最终源码上通过。 | 关闭；动态数值来自主Agent实际GUI，本实例独立核对源码与记录 |

滚动回归满足首次静止阅读、实际上翻阅读、主动提交三条生产可达路径；没有用静态截图或普通对象单测替代DOM几何证据。

## Stage 1：功能逐条对照

“完整”限定本期DEV-PLAN交付；产品条目中的后续子功能列为部分/未实现及所属Phase，不跳过、不提前验收。

| Spec条目 | 本期结论、实现位置与验证 |
|---|---|
| REQ-001:259 来源会话/消息ID、split、时间、重复/时间/引用 | 完整。B/domain/conversation.py:62/83、B/adapters/import_loader.py:12/18、B/application/replay.py:37、B/adapters/conversation_schema.py:55/158保存及校验；BT/test_conversations.py:179/192非法包/来源重复/复合FK本次通过，GUI文件导入见VALIDATION:93。 |
| REQ-001:260 同集合规范化身份归组 | 手工模拟完整。B/domain/conversation.py:29 trim及域名小写；B/application/conversations.py:16锁后复用identity；BT/test_conversations.py:77同地址两封同conversation且首封可读。可信跨源sender_key复核入口未开放。 |
| REQ-001:261 模式/重置后记忆隔离 | 当前模式/分支完整。B/application/conversation_base.py:34独立branch，B/adapters/conversation_schema.py:12/17完整scope FK；BT/test_conversations.py:192及BT/test_postgres.py:92逐维越界拒绝。重置/generation实际递增待Phase12。 |
| REQ-001:262 多订单、多事项、关联证据 | 部分；本期稳定基础事项完整。B/application/case_memory.py:9复用correspondence issue，第27行来源事实关联；BT/test_conversations.py:173主键跨截点稳定。订单定位Phase4、语义多事项Phase7未实现。 |
| REQ-001:263 group_id不得作身份 | 完整。B/application/replay.py:26每源案例独立dataset；group_id仅data_imports元数据，B/adapters/conversation_schema.py:162；BT/test_conversations.py:150同group的不同来源不合并。 |
| REQ-001:264 缺可信身份独立回放且明确标识 | 完整当前公开边界。B/domain/conversation.py:89拒identity_verified=true；F/components/mail-agent/ConversationList.vue:76标未验证；BT/test_conversations.py:150/185通过。 |
| REQ-001:265 模拟邮箱、不得去加号/句点 | 完整。B/domain/conversation.py:36只小写域名；BT/test_conversations.py:77分别保留加号、句点且不错误合并。 |
| REQ-002:276 真实前缀、未来正文不入当前响应 | 查询/任务基础完整。B/application/conversation_queries.py:51同repeatable snapshot，第58/64行visible seq过滤；B/application/replay.py:60每次一客户截点。BT/test_conversations.py:161/162和网络脚本:75/76哨兵通过；真实模型请求待Phase7。 |
| REQ-002:277 历史客服/对照分别呈现、下一轮不继承对照 | 人工独立审阅完整；AI待Phase7。B/application/human_review.py:75仅simulation写Message；queries.py:71独立comparisons；F/components/mail-agent/MessageTimeline.vue:48标历史客服，AgentProcessPanel.vue:62独立对照。BT/test_conversations.py:165/175及网络脚本:85/90隔离断言通过。 |
| REQ-002:278 从真实前缀重建事实 | 基础事实完整。B/application/case_memory.py:23替换当前投影，只由可见真实邮件产生来源fact，第31行记revision/as_of。BT/test_conversations.py:174/175事实3条、无对照哨兵；未宣称语义Understanding完成。 |
| REQ-002:279 统一as_of、禁止未来订单/知识回退 | 游标as_of完整，B/application/replay.py:41/68；BT/test_conversations.py:176截点2026-10-02T08:00Z。订单snapshot及知识available_at查询尚未接，Phase4/6；AC-006未验收。 |
| REQ-002:280 回放结束不等于解决，缺附件/快照明确 | 本期结束/解决分离完整，B/application/replay.py:63、F/components/mail-agent/MessageComposer.vue:17/24；BT/test_conversations.py:177仍open。当前仅文本JSON，附件/快照读取与未知提示待Phase4/8。 |
| REQ-003:291 有效来信自动运行、不逐封审批 | 持久任务触发协议完整。B/application/conversation_base.py:64/80、task_queue.py:27同事务cycle/run/job；B/worker/runner.py:33自动领取；BT/test_protocol.py:190最新任务完成。正式模型执行待Phase7。 |
| REQ-003:292 校验后一次性最终自动模拟出站 | 未在本期实现，Phase7。B/worker/protocol.py:29只写真实protocol outcome、不写邮件；BT/test_protocol.py:135完成后仍1封客户邮件，未用假AI凑闭环。 |
| REQ-003:293 后续读取自动回复、每轮最多一封 | 自动AI产物待Phase7；当前持久cycle框架完整，B/adapters/conversation_schema.py:73/final_message_id；BT/test_protocol.py:158同cycle retry与completed拒retry通过，不代表AC-007/008/009通过。 |
| REQ-003:294 本地模拟、无真实邮箱投递 | 完整。F/components/mail-agent/AgentProcessPanel.vue:8/9和MessageComposer.vue:59明确说明；B/worker/protocol.py:13及runner.py:35没有provider或发送调用。 |
| REQ-003:295 重复点击、重试、刷新无重复效果 | 当前命令协议完整。B/application/idempotency.py:8同键同参原结果/异参409，conversations.py:35来源去重；F/api/mail-agent-request.ts:58未知结果原key/payload。BT/test_conversations.py:85、BT/test_protocol.py:118、FT/mail-workbench.test.ts:76本次通过；实际SSE补读不增run。 |
| REQ-007:382 无依据/冲突等模型handoff | 模型自动handoff待Phase7；主动takeover完整，B/application/human_review.py:20、BT/test_protocol.py:176旧commit拒绝/人审来信不自主调度；不将主动按钮当AC-020通过。 |
| REQ-007:383 模型原因/证据缺口、程序核验 | 模型子项待Phase7。当前主动接管reason持久，B/application/human_review.py:35；F/components/mail-agent/HumanReviewPanel.vue:25/31准确提示摘要和查询未接。实际暗色人审原因可读。 |
| REQ-007:384 接管摘要/未发送草稿 | 原因、可见邮件核对、草稿/备注基础完整，B/application/human_review.py:41、F/components/mail-agent/HumanReviewPanel.vue:33/47；BT/test_human_events.py:31真实旧save/reload通过。订单/尝试步骤/资料/待决策摘要待Phase7。 |
| REQ-007:385 接管期间新来信只归并 | 完整。B/application/conversation_base.py:67/79保持human_review并suppressed；human_review.py:25撤销旧任务。BT/test_conversations.py:101、BT/test_protocol.py:176通过。 |
| REQ-007:386 人工回复和备注持久；下一新来信才恢复 | 完整本期协议。B/application/human_review.py:66版本检查、第82/90行保存并等待；conversation_base.py:67新接收输入恢复。BT/test_conversations.py:123、BT/test_human_events.py:58/77两种顺序通过；实际GUI VALIDATION:89–91。 |
| REQ-007:387 可再次HITL、当前方案不进入全局知识 | 主动人审基础完整。B/application/human_review.py:28复用唯一open，B/adapters/conversation_schema.py:135部分唯一索引；F/components/mail-agent/HumanReviewPanel.vue:21再次接管。当前正文仅conversation scope，无全局知识写；PG/GUI通过。 |
| REQ-007:388 仅人工确认结案 | 完整。B/application/human_review.py:98人工入口，protocol.py:36不改resolved；F/views/mail-agent/index.vue:234确认框。BT/test_conversations.py:140/177、BT/test_human_events.py:13和实际GUI结案/原会话重开通过。 |
| REQ-008:400 唯一标识、触发/会话版本、模式/截点及运行记录 | 本期字段完整，B/adapters/conversation_schema.py:73/86/99、task_queue.py:38服务绑定版本；BT/test_protocol.py:158同cycle新attempt通过。模型/资料版本、工具、引用、token待Phase7/11。 |
| REQ-008:401 简短处理说明/可验证过程，不存隐藏思维链 | 当前真实协议记录完整，F/components/mail-agent/AgentProcessPanel.vue:39/49；仅真实状态/时间/outcome，无伪造工具或token。独立build和network脚本:49结果验证通过；业务工具过程待Phase7。 |
| REQ-008:402 同会话串行、旧版本未提交结果无效 | 协议完整。B/worker/leases.py:23/38、protocol.py:15/26核租约/输入/权属；task_queue.py:9取消/关闭checkpoint/fence。BT/test_protocol.py:176/190通过；knowledge锁序第70行受控竞争通过。 |
| REQ-008:403 stop、显式retry、刷新恢复，晚到无效果 | 完整。B/worker/jobs.py:58/80、leases.py:96中断仅显式retry；F/components/mail-agent/AgentProcessPanel.vue:27/35操作入口。BT/test_protocol.py:135/158/204通过，原cycle沿用、completed拒retry、GET无写。 |
| REQ-008:404 技术失败类别、可重试、不包装业务结论 | 本期持久user_stopped/worker_interrupted与HTTP类别完整，B/worker/jobs.py:64、leases.py:116、api/conversations.py:24/26；BT/test_api.py及protocol测试通过。UI停止/中断与显式重试可辨；文案字典旧别名另列LOW。模型鉴权/超时/解析待Phase7。 |
| REQ-008:405 调用预算、无进展与限制 | 模型循环待Phase7。B/worker/runner.py:35当前每task仅协议commit一次，没有假token/预算；不以当前工程测试宣称模型预算已验收。 |
| REQ-008:406 售后写去重/未知结果对账/停止不抹操作 | 售后账本/工具待Phase9/10。B/application/event_store.py:43内部record-only去重和人工抑制由BT/test_human_events.py:77通过；没有HTTP假业务注入，不代替售后验收。 |
| REQ-009:417 Art Design Pro外壳/chat基础、三栏 | 完整。F/views/mail-agent/index.vue:6/11/113复用page-content/公共组件，FRONTEND-BASELINE.md:3记录独立副本；明暗工作台与知识邻居真实渲染一致，独立build通过。滚动旧缺陷按前表关闭。 |
| REQ-009:418 模式/客户/最新来信/状态可辨 | 完整。F/components/mail-agent/ConversationList.vue:60/68/75、F/views/mail-agent/index.vue:39/42、MessageComposer.vue:8；FT/mail-workbench.test.ts:102/120及实图可读。 |
| REQ-009:419 右侧过程、中间正式邮件、候选独立 | 完整当前文本/人工基础。F/components/mail-agent/MessageTimeline.vue:9仅messages；AgentProcessPanel.vue:22/62分区。BT/test_conversations.py:168/175和真实network哨兵及history-light实图通过。 |
| REQ-009:420 来源文字/图标，不只颜色 | 当前客户/历史客服/模拟人工完整，F/components/mail-agent/MessageTimeline.vue:15/20/46标签与Avatar；AgentProcessPanel.vue:74人工独立对照。明暗实图可辨；正式AI/Mock业务来源待后续。 |
| REQ-009:421 明确推进/来信/人工回复/结案/停止重试/重置删除 | 本期前6项完整且有真实API，F/views/mail-agent/index.vue:96/97/120/124、HumanReviewPanel.vue:79/112、MessageComposer.vue:11/61；对应PG/前端和GUI通过。重置删除Phase12，未开放死按钮。 |

## Stage 1：5.10页面、5.11状态、5.12输入逐项

| 条目 | 本期结论与证据 |
|---|---|
| 5.10外壳/路由/聊天/表单/主题复用 | 完整当前范围。F/views/mail-agent/index.vue:6/155及ConversationDialog.vue:2/12使用既有Art外壳、page-content、ElForm/Dialog/Drawer/Button；FRONTEND-BASELINE.md:3/25来源记录与实际邻居实图相符。没有独立设计稿/Brief，继承现有组件。 |
| SCREEN-001 | 当前会话、模式、模型配置标记及三栏完整，F/components/business/runtime-status.vue:25/48、F/views/mail-agent/index.vue:3/42；运行配置仅conversations=true，B/api/system.py:27/28与FT/runtime-contract.test.ts验证。 |
| SCREEN-002 | 知识管理尚未接，Phase5/6；F/views/knowledge/index.vue:4明确提示。实际明暗邻居页没有假资料或成功操作。 |
| CMP-001 | 模式/状态筛选、新建、导入、客户/主题/时间/状态、选择/分页完整，ConversationList.vue:7/36/50/81，FT/mail-workbench.test.ts:120通过。重置/删除Phase12。 |
| CMP-002 | 当前文本邮件/来源/独立审阅完整，MessageTimeline.vue:20/30、AgentProcessPanel.vue:62；历史实际1→3封且哨兵隔离。语言分析/图片缩略图/逐图读取Phase7/8。 |
| CMP-003 | 文本来信、历史推进/进度及人审期间来信完整，MessageComposer.vue:3/11/42/61；PG/API和GUI通过。图片/仅图片/草稿图片移除Phase8。 |
| CMP-004 | 运行/时间/状态/stop/retry完整，AgentProcessPanel.vue:22/27/35/39；协议测试通过。诉求/工具/引用/token/trace Phase7/11。 |
| CMP-005 | 主动原因/邮件核对/草稿/备注/人工完成/结案完整，HumanReviewPanel.vue:25/35/47/79/112；旧草稿屏障PG/GUI通过。模型接管摘要Phase7。 |
| CMP-006 | 引用资料抽屉未实现，Phase6/7；当前AgentProcessPanel.vue:8明示模型未接，无假引用入口。 |
| CMP-007 | 历史JSON数量提示、服务端校验及成功/失败保留完整，ConversationDialog.vue:51/70/164；实际GUI/reactive回归通过。知识上传/下架/彻底删除Phase5/6/12。 |
| CMP-008 | 业务单/状态详情未实现，Phase4/9/10；B/api/conversations.py:30公开路由未返回编造业务资料。 |
| CMP-009 | 模拟执行/事件抽屉未实现，Phase9/10；B/application/event_store.py:43仅内部记账控制，无HTTP注入业务成功。 |
| CMP-010 | 资料编辑/核对未实现，Phase5；F/views/knowledge/index.vue:4明确尚未接入。 |
| CMP-011 | 版本/索引/发布/回滚未实现，Phase5/6；知识页同位置准确提示，无假任务成功。 |
| CMP-012 | 检索试查未实现，Phase6；知识页同位置没有伪检索入口。 |
| CMP-013 | 图片证据未实现，Phase8；B/domain/conversation.py:63当前只接受文本历史消息且extra=forbid，无任意图片路径。 |
| 5.10多行、明确发送、无电话视频 | 完整文本范围。MessageTimeline.vue:30文本插值+whitespace-pre-wrap，MessageComposer.vue:42/61 textarea/明确按钮；FT/mail-agent-request.test.ts:73长度/换行通过，无电话视频动作。 |
| 5.10阅读位置 | 完整；MessageTimeline.vue:51/56按真实旧DOM、主动signal第75行；实际初挂载静止/上翻/SSE/主动提交数值见VALIDATION:97与前表，旧P3-R2关闭。 |
| 5.10桌面/窄内容区 | F/views/mail-agent/index.vue:11左260、第113行右360，第211/212行按内容宽<1024 drawer/<640纵排。实际1600×1000及1280×800截图通过；不据此宣称手机精细适配已完成。 |
| 5.11默认 | F/views/mail-agent/index.vue:100未选会话提示；useMailWorkbench.ts:84选择仅GET；FT/mail-workbench.test.ts:17与真实network无新增run通过。 |
| 5.11加载 | ConversationList.vue:44和页面:79加载反馈；composable:114/147 busy阻重复，表单/按钮加载可见；测试及build通过。 |
| 5.11空 | ConversationList.vue:45无案例，AgentProcessPanel.vue:24无任务，MessageComposer.vue:17回放结束分别处理；history-light显示末截点未结案。订单/知识查询空态留其后续实现。 |
| 5.11错误 | F/api/mail-agent-request.ts:13类别文案，composable:133保留文本并409刷新，Dialog.vue:176保留文件/表单；FT/mail-workbench.test.ts:43/76及实际网络abort→同key重试VALIDATION:96通过。 |
| 5.11成功 | composable:127/155/185真实反馈，模拟人工/历史审阅明确；PG与实际GUI通过；阅读位置按实际回归保持。 |
| 5.11受限 | B/application/conversations.py:33历史只读；MessageComposer.vue:14 active/HITL禁止推进；AgentProcessPanel.vue:8模型未接，不提供假运行；删除Phase12。当前零模型协议不需要Key，不把配置标志视为连接成功。 |
| 5.12 mode | 服务绑定simulation/historical_replay，B/application/conversation_base.py:34；B/domain/conversation.py:8禁止任意extra改scope，BT/test_conversations.py:192复合FK通过。 |
| 5.12 sender_email/sender_key | domain/conversation.py:24/29/88/89长度320、有效地址及公开包未复核；mail-inputs.ts:20邻近字段错误，BT/test_conversations.py:77/185通过。 |
| 5.12 subject | domain/conversation.py:14/67最多500，MessageTimeline.vue:29空主题占位；FT/mail-agent-request.test.ts:79超长断言通过。 |
| 5.12 body | domain/conversation.py:13/18/68/79非空/20000；MessageTimeline.vue:30纯文本，BT/test_conversations.py:235脚本文字保持文本；图片条件Phase8。 |
| 5.12 customer_images | 未接Phase8；domain/conversation.py:63禁止未知字段，BT/test_conversations.py:185拒任意路径，不冒充图片校验已完成。 |
| 5.12 as_of | domain/conversation.py:70强制带时区；replay.py:68服务端游标生成；BT/test_conversations.py:176真实截点通过，不接受客户端任意as_of。 |
| 5.12 order_id | 查单输入未实现，Phase4；DEV-PLAN.md:103及当前api/conversations.py:30路由范围一致，无假查单。 |
| 5.12 human_reply/note | domain/conversation.py:47/53/58约束20000/5000、完成正文非空；mail-inputs.ts:30前端匹配，PG版本屏障和FT/mail-agent-request.test.ts:88通过。 |
| 5.12 document | 知识受控输入Phase5；当前历史JSON独立受控，ConversationDialog.vue:51/65说明5MiB与来源/时间且不读取路径，实际文件测试通过。 |
| 5.12 business_action | 未实现，Phase9；内部event_store.py:43不是公开业务工具，ImportCase不接受任意业务字段。 |
| 5.12 scenario_event | 完整业务推进未实现，Phase10；event_store.py:43仅内部通知屏障，无假HTTP执行。 |
| 5.12 request_id/expected_version | idempotency.py:8、conversation_lock.py:22；composable:118/148自动带版本/key，PG幂等/409和未知网络原命令测试通过，用户无需填写。 |

## Stage 1：架构不变量、AC和故障时序归属

| 条目 | 当前证据及边界 |
|---|---|
| 架构§2可信scope与历史隔离 | B/adapters/conversation_schema.py:12/17/46完整FK；conversation_base.py:34服务分配branch/customer，queries.py:51只当前前缀；BT/test_conversations.py:192及test_postgres.py:92通过。真实工具权限/知识时间过滤后续重验。 |
| 架构§3状态拆分与输入/权限版本 | B/adapters/conversation_schema.py:38/42–45分生命周期/处理权/gate/调度；human_review.py:26/66与conversation_base.py:67分别处理接管/人工屏障/新输入；PG人审事件4项通过。自由备注只在人审及依赖对象，不写成业务授权human_decision，case_memory.py:29。 |
| 架构§6幂等/cycle/双槽/提交门 | idempotency.py:12绑定参数+持久receipt；task_queue.py:27 trigger唯一，jobs.py:87/91同cycle重试；leases.py:13数据库时钟、第64/89行60/90秒租约，protocol.py:17/26最终栅栏；真实协议8项通过。模型心跳调度、业务命令/最终AI提交在后续接入。 |
| 架构§8持久表/API/事件 | migration0002:9/198冻结表与双槽，database.py:8/34检查迁移和列；events.py:25/35/70补读/Last-Event-ID/15s心跳；event_store.py:14/16持会话锁递增seq且事实同commit。独立metadata=[]与两连接seq=[2,3]，HTTP原始记录通过。 |
| AC-001 | BT/test_conversations.py:77同模拟身份两封同会话/首封可读，本次通过。 |
| AC-002 | BT/test_conversations.py:150同group不同源会话不合并，本次通过；公开包仅未验证独立案例，不声称可信sender_key复核接入。 |
| AC-003 | BT/test_conversations.py:85/155请求/来源消息/来源导入去重，不增消息/任务，本次通过。 |
| AC-004/005/027 | BT/test_conversations.py:150、网络脚本:71及实际历史GUI证明真实前缀/人工独立对照/未来哨兵。AI请求与AI产物未接，不能标完整AI AC通过。 |
| AC-006 | 未验收。历史订单snapshot Phase4，只有replay.py:68的as_of基础，未返回未来订单或假不可用结果。 |
| AC-007/008/009 | 未验收，正式自动AI出站/AI多轮输入Phase7；protocol.py:29不写假回复，BT/test_protocol.py:135只有客户邮件。 |
| AC-020/022 | 模型handoff与恢复模型输入未验收，Phase7；主动接管与下一新来信恢复资格基础由BT/test_protocol.py:176及test_conversations.py:123通过。 |
| AC-021/023 | 当前人审来信不调度、人工才resolved完整，BT/test_conversations.py:101/140/177及test_human_events.py:13通过；模型建议解决分支Phase7重验。 |
| AC-024/025/026 | 当前协议层旧提交拒绝/stop/interrupted/retry/GET不重跑通过，BT/test_protocol.py:135/158/176/190/204；真实模型超时/出站/checkpoint Phase7重验。 |
| AC-028/032 | 本期主动人审及Art外壳/明暗/无模板登录依赖通过，HumanReviewPanel.vue:23/80、FRONTEND-BASELINE.md:3、实际8张截图及前端测试。模型摘要/引用未接，不标整项所有子功能已交付。 |
| FT-01 | BT/test_protocol.py:176/190生产新输入/接管之后旧complete=False、最新任务处理新版本，本次真实PG通过；真实旧模型/业务副作用Phase7/9。 |
| FT-02 | BT/test_human_events.py:58/77交换内部业务通知和人工回复提交顺序，过期409、business suppressed、下一客户才恢复；第31行旧草稿reload屏障通过。完整业务执行事件Phase10。 |
| FT-05 | BT/test_protocol.py:135/158/204中断/原cycle显式retry/completed拒retry框架通过；业务或最终出站commit后checkpoint丢失的完整FT-05未执行，Phase7/9。 |
| FT-07 | event_store.py:43与test_human_events.py:77只证明内部通知记账、去重和人工抑制；WaitCondition先后补查/wake_pending消费Phase10，完整FT-07未执行。 |
| FT-08 | test_conversations.py:150、网络脚本:71/90、实际GUI验证真实前缀/人工对照/未来文本隔离；未来订单/资料/Mock/真实AI上下文完整哨兵集Phase4/6/7重验。 |
| SSE客户端范围与只读补读 | F/composables/conversation-event-session.ts:27/52/66检查scope、去重、关闭旧流；FT/conversation-events.test.ts受控Stream本次通过。真实HTTP补读和15秒心跳由network脚本补证；不是用模拟Stream冒充真实网络。 |

未发现阻塞Spec漂移或死引导。example JSON API（B/api/conversations.py:11/34）是受控输入示例，protocol runner（worker/protocol.py:30）明确模型未接，内部通知（event_store.py:43）和隔离QA helper（scripts/phase3-test-server.py:31）有CONTRACT/IMPLEMENTATION范围依据，不成为编造模型、知识或ERP功能。知识页与右栏准确标后续接入。

## Stage 2：质量、安全、测试真实性

| 检查 | 结论与证据 |
|---|---|
| 类型/职责/文件大小 | 新增/修改核心文件均<=300行：composable262、页面247、test_conversations239、test_protocol230、migration216。F/api/mail-agent-contract.ts:22/54/64/82明确契约；frontend/tsconfig.json:6 strict=true；新增会话TS/Vue的any扫描无匹配，独立vue-tsc通过。71文件扩展扫描中唯一838行clean-dev.ts是未改模板脚本，非本期新增核心。 |
| 冻结迁移一致性 | migration0002:9独立metadata、不动态import未来schema，第198行升级/第211行降级；B/adapters/database.py:8/34版本和所有列就绪核验。独立随机schema升级后compare_metadata=[]。迁移重复表定义是冻结历史所需。 |
| 事务/正文依赖/失败清理 | B/application/conversation_base.py:22先BodyWriter再DB事务；body_store.py:19回滚文件、第37行同conn对象及依赖、第50/55行scope+摘要。BT/test_conversations.py:192真实跨scope失败/事务文件清理通过。完整崩溃孤儿清理仍Phase12。 |
| 锁与事件提交 | conversation_lock.py:16双槽→会话；worker只自身槽→会话，无模型期间长事务。test_protocol.py:70可控同会话knowledge竞争本次通过；独立两连接event_store.py:14屏障确认第二事务在第一commit前等待，seq=[2,3]，不拿全局sequence假称提交顺序。 |
| 密钥/错误输出 | 71文件扫描eval/v-html/innerHTML/dangerouslySetInnerHTML、公开VITE密钥变量、硬编码provider Key模式无匹配；main.py:43/52、api/conversations.py:24/26、runner.py:39只安全类别。test_api.py:57、test_postgres.py:106 SECRET_MARKER不泄漏通过。私有database_url仅注入环境，未打印。 |
| SQL/XSS/任意路径 | idempotency.py:12和replay.py:15用户输入为绑定参数；body_store.py:26路径用服务UUID；MessageTimeline.vue:30文本插值。test_conversations.py:185/235拒路径额外字段、HTML保持纯文本；隔离schema的f-string仅拼服务生成uuid4标识，非用户SQL。没有新增安全HIGH。 |
| 本地Host/Origin/CORS | api/security.py:23/35/37唯一Host/Origin、写入需JSON；第54/55行PATCH/Idempotency-Key/Last-Event-ID预检允许；test_api.py:42/48恶意Host/Origin及写保护本次通过。SSE events.py:74 no-store，仅安全资源ID/状态，正文不进流。 |
| 启动与实际readiness | main.py:28有engine即启动runner，首次故障后runner.py:31保持restart恢复语义；database.py:33/34与api/system.py:16检查实际依赖/迁移/列。test_postgres.py:52/106/124、test_api.py:36通过；之前故障恢复原报告保留，未声称本实例重做了物理PG断电。 |
| 后端测试真实性 | tests/test_protocol.py:31与test_conversations.py:31创建随机schema/Temp、正式迁移/生产service/合法Pydantic命令，34项全部实际执行无skip。过期租约显式设置DB过去时间，第139行；knowledge用Event/pg_blocking_pids/NOWAIT，不靠随机sleep碰竞态。内部kind控制只证明槽协议，非正式知识管线。 |
| 前端故障/交互真实性 | FT/mail-workbench.test.ts:17/43/76/102/120/138直接运行生产composable，证明GET无写、409保留、未知结果原key/payload、晚到响应、分页、人审版；FT/mail-agent-request.test.ts:55实际Vue reactive嵌套数组，修复普通对象盲区。真实GUI文件/旧草稿/网络abort另由VALIDATION补证。 |
| DOM与HTTP测试边界 | 18项前端脚本没有挂载MessageTimeline/测几何，滚动闭环由实际GUI数值和最终源码补足；受控EventStream只证明客户端协议，真实SSE由网络脚本补齐。本期并无真实模型/工具端到端测试，不把绿灯推断为AI能力。 |
| QA helper隔离 | scripts/phase3-test-server.py:47/50独立schema/Temp对象、第67行私有环境只给API、第77行给Vite前移除GLOBALMAIL/LLM、第119行清理；本实例只读取，不启动第二服务。旧两份Temp日志删除被自动审批拒绝的事实见VALIDATION:134，不假称它们已删除；不影响源码/会话对象验收。 |

LOW Q3-L1（非阻塞）：`F/components/mail-agent/AgentProcessPanel.vue:142` 的文案字典使用 `stopped_by_user/process_interrupted`，后端在 `B/worker/jobs.py:64`、`B/worker/leases.py:116`实际保存 `user_stopped/worker_interrupted`，因此目前第149行总回落到通用错误提示。状态标题的“已停止/运行中断”和第55行显式重试提示仍正确；建议之后对齐这两个键，减少无效别名并显示更具体原因。没有将此建议伪装成已修复。

### 实际渲染与邻居对比

本实例逐张查看以下PNG实际像素；GUI截图由主Agent在真实隔离服务采集。没有设计稿/Brief，比较已复制Art组件和实际知识邻居，不另造像素设计标准。

| 实图 | 已观察结论与源码 |
|---|---|
| [明色三栏](../../output/playwright/phase3-light-wide.png)，1600×1000 | 左客户/中邮件输入/右任务人审分区；模拟人工与客户有文字来源，输入保留多行。F/views/mail-agent/index.vue:11/113、MessageTimeline.vue:20/30、AgentProcessPanel.vue:22/83。 |
| [历史页](../../output/playwright/phase3-history-light.png)，1600×1000 | 三封真实customer/staff/customer；独立人工审阅右侧，2/2结束仍可人工结案，AI明确未接。MessageComposer.vue:17/24、AgentProcessPanel.vue:62/74。此末截点图不代替首截点未来隔离哨兵。 |
| [明色窄抽屉](../../output/playwright/phase3-light-narrow-drawer.png)，1280×800 | 内容宽不足1024，右栏变ElDrawer，左/中仍可辨；抽屉文字、关闭、任务和审阅可读。页面:131/211。 |
| [暗色三栏邮件](../../output/playwright/phase3-dark-wide.png)，1600×1000 | 已选实际邮件，客户与模拟人工卡片/来源和暗色输入可辨；不是只验空态。MessageTimeline.vue:27/30沿用主题变量，无新增固定白底。 |
| [暗色窄人审](../../output/playwright/phase3-dark-narrow-drawer.png)，1280×800 | 待人审、接管原因及未发送textarea真实渲染、字色/边框可辨；HumanReviewPanel.vue:25/58，页面:131。 |
| [网络错误](../../output/playwright/phase3-network-error.png)，1280×800 | 中间明确连接错误，右侧原草稿仍保留、可重试。mail-agent-request.ts:19、useMailWorkbench.ts:137；解除abort后同key成功由VALIDATION:96记实，不从静态图推断请求成功。 |
| [知识明色](../../output/playwright/phase3-knowledge-light.png)/[知识暗色](../../output/playwright/phase3-knowledge-dark.png)，1600×1000 | 与工作台同侧栏/顶栏/页签、卡片圆角边框、主题蓝和层级文字，亮白/暗灰背景、El空态一致；knowledge/index.vue:2/4与工作台page-content:6。资料入口真实说明尚未接。 |

## 本轮独立命令与原始结果

后端cwd `globalmail-agent/backend`，私有配置只赋值、不输出连接串：

```powershell
$phaseReviewSettings=Get-Content -LiteralPath ../../.local-data/runtime/settings.json -Raw | ConvertFrom-Json
$env:GLOBALMAIL_TEST_DATABASE_URL=$phaseReviewSettings.database_url
$env:PYTHONPATH='src'
& .venv/Scripts/python.exe -m unittest discover -s tests -v
```

本实例原始输出（exit0，34项无skip）：

```text
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
Ran 34 tests in 16.593s

OK
```

Starlette警告来自既有测试客户端依赖；protocol_worker_dependency_unavailable来自刻意坏数据库的降级测试，不抹去原始警告，不把它作为业务失败。

前端cwd `globalmail-agent/frontend`，`pnpm exec tsx --test scripts/*.test.ts`，exit0；本实例原始汇总：

```text
ℹ tests 18
ℹ suites 0
ℹ pass 18
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 530.4119
```

同cwd `pnpm build`，独立exit0；原始诊断/完成输出如下，仅省略351行输出中的生成资源尺寸清单：

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3255 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 27.15s
```

后端cwd编译：

```powershell
& .venv/Scripts/python.exe -m compileall -q src migrations tests
Write-Output "compileall_exit=$LASTEXITCODE"
```

```text
compileall_exit=0
```

额外真实PG检查复用BT/test_protocol.py:31隔离fixture，finally执行doCleanups。migration比较和事件第二事务等待观察不是继承旧报告；本实例原始输出exit0：

```text
migration_metadata_diffs []
two_connections_commit_order {'blocked_before_first_commit': True, 'sequences': [2, 3], 'kinds': ['review.commit.first', 'review.commit.second']}
```

已读取主Agent原始 `tmp/phase3-network-check.json` 并检查 `globalmail-agent/scripts/phase3-network-check.py:36/57/71` 的实际HTTP断言，没有再次运行已停止的server。原始记录：

```json
{
  "status": "passed",
  "checks": [
    "real_SSE_Last_Event_ID_reconnect_preserves_order_and_scope",
    "15_second_heartbeat_and_read_only_reconnect_no_new_task",
    "invalid_and_future_event_cursors_rejected",
    "real_HTTP_history_prefix_and_human_comparison_isolation"
  ],
  "provider_calls": 0,
  "isolation": "phase3-test-server disposable PostgreSQL schema and objects"
}
```

其中provider_calls是脚本固定写入的字段，不是供应商调用仪表；本期零provider执行由worker/protocol.py:13及runner.py:35的实际无模型路径支持，不能把这个字段当将来AI能力或真实调用计数的测试。

## 交回结论

Stage 1与Stage 2通过；阶段内五项旧缺陷有修后证据，不以前三轮的全绿测试替代新路径。未发现新的HIGH/MEDIUM，LOW文案字典建议保留。正式服务升级和遗留日志处理以VALIDATION:132/134主Agent实测为准，本实例未把未删除日志写成已清理。后续按DEV-PLAN进入Phase4业务数据/精确查询；Phase7等接入时必须重验本文明确留下的模型、业务、知识、图片、删除和完整故障时序。
