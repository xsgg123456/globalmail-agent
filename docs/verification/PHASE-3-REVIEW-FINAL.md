# Phase 3 独立两阶段复审

日期：2026-10-08。执行者：fresh code-reviewer。依据：`.agents/skills/code-review/SKILL.md`、AGENTS、DEV-PLAN Phase 3、Product-Spec 指定 REQ/AC/界面条目、AGENT-ARCHITECTURE 第2/3/6/8节、AGENT-ACCEPTANCE 指定 FT、PHASE-3-CONTRACT/IMPLEMENTATION 和初审报告。

## 结论与审查基线

**本轮 FAIL：初审旧草稿 HIGH 已独立复验关闭；本轮另发现两项 MEDIUM，主 Agent 的实际 GUI 操作又发现一项导入 HIGH。** 已结案会话接管导致处理权与 open review 不一致；知识槽与同会话输入的锁顺序形成真实 PostgreSQL 死锁；合法导入包的 Vue 嵌套 Proxy 无法被 structuredClone，导入请求根本未提交。修复后的最终源码需新的 fresh 审查，不能用本轮基线测试宣称已全部关闭。

本轮先完整重新审查 Stage 1，没有只验证旧 HIGH；当时未发现 HIGH，已执行 Stage 2 补充检查。收到实际 GUI 导入 HIGH 后停止新增 Stage 2 审查，仅保留已经完成的检查证据，不形成 Stage 2 通过结论。主 Agent 在审查期间修改上述新问题；本报告保留发现时 FAIL 事实，按主 Agent 指令不由本实例复审这些新变更。下列32项后端、17项前端测试与独立构建针对审查启动基线；主 Agent 后来报告34/18项及build成功，不替代独立复审。

范围严格按 `DEV-PLAN.md:91`、第92/93/101行和 `docs/planning/PHASE-3-CONTRACT.md`：受控 JSON/模拟邮箱归组、真实历史前缀及基础 correspondence issue/来源事实、人审/结案/重开、持久任务与双槽租约协议、事件/SSE、可操作三栏工作台。真实模型、自动 AI 邮件、语义多事项、订单 snapshot、知识检索、售后执行/完整业务 waits-wake、图片和完整删除分别属于后续 Phase，不借未接模型宣称整项产品 AC 通过，也不将这些未接能力列为 Phase 3 缺陷。

路径简写：`B/` = `globalmail-agent/backend/src/globalmail_agent/`；`F/` = `globalmail-agent/frontend/src/`；`BT/` = `globalmail-agent/backend/tests/`；`FT/` = `globalmail-agent/frontend/scripts/`。位置指本轮审查时对应源码；已结案修复在 human_review 中增加两行，后续方法位置会相应移动。

## Stage 1：Spec Compliance

### HIGH P3-F3：合法 GUI 导入被 Vue Proxy 的 DataCloneError 阻断

要求：`DEV-PLAN.md:91/101` 页面可受控导入；`Product-Spec.md:570/576` 客户列表导入及案例数据包校验；`PHASE-3-IMPLEMENTATION.md`第4步接通导入。

本轮启动基线 `F/components/mail-agent/ConversationDialog.vue:109/126` 使用深响应式 ref 存入包含messages数组的包，第167行只浅展开外层；`F/composables/useMailWorkbench.ts:148` 将它交给PendingCommands；发现时 `F/api/mail-agent-request.ts:72` 执行 `structuredClone(payload)`。messages数组/元素仍是Vue Proxy，浏览器 structuredClone 抛 DataCloneError；异常发生在第150行HTTP调用之前，用户选择有效JSON仍无法导入。之前前端测试用普通对象，没有走实际文件ref→浅展开→clone的组件路径。

证据来源：主 Agent 在本轮隔离真实浏览器操作中报告该 DataCloneError；本实例已读取上述发现时原始源码，确认可达路径。**本实例没有把后续修复当成已复验结果。** 主 Agent 随后改为与真实HTTP一致的JSON序列化快照，并补Vue reactive嵌套数组回归，报告18项前端测试/build成功。fresh复审须实际GUI导入合法文件并确认202及prefix，不只测普通对象；本轮保留该HIGH，Stage1 FAIL。

### 已关闭：初审 HIGH P3-R1，旧草稿保存/整页刷新绕过输入版本屏障

要求：`AGENT-ARCHITECTURE.md:113`、第124行，人工回复必须覆盖最新输入；`DEV-PLAN.md:101`，过期人工表单409。

- `B/domain/conversation.py:47`：ReviewDraft 必填 expected_input_revision，禁止缺字段；`B/application/human_review.py:49` 拒绝未来输入版，第56行持久化客户端实际核对的版本，不无条件绑定当前版本。
- `F/composables/useMailWorkbench.ts:72` 从持久 review.input_revision 初始化核对版本，第195行保存带编辑起点，第182行完成回复带该版本，第258行才显式确认最新输入；`F/components/mail-agent/HumanReviewPanel.vue:35`、第80/145行保留过期提示并禁用完成。
- `BT/test_human_events.py:13` 在真实 PG 中执行新来信→保存旧草稿→重新读取→仍旧版本→完成人工回复失败、消息仍2封→显式新版本保存。独立32项测试中该项 `ok`。`FT/mail-workbench.test.ts:43` 的409/刷新/显式核对和第138行的 PATCH 版本测试 `ok`。这两层证据关闭初审问题；浏览器证据见后文。

### MEDIUM P3-F1：已结案接管后，新来信留下孤立 open review

要求：`AGENT-ARCHITECTURE.md:98`、第113/118行，处理权与人审状态一致，新来信重开原会话并建立新 cycle；`DEV-PLAN.md:92` 明确交付处理权、人工结案和重开。

发现时 `B/application/human_review.py:22` 获取会话后直接 invalidate/创建 review，未限制 resolved；`B/application/conversation_base.py:67` 接收新消息因 resolved 改为 agent，第72行重开，却没有关闭此 open review。`F/components/mail-agent/HumanReviewPanel.vue:23` 据 open review 显示人工表单，而 `B/application/human_review.py:67` 完成人工回复要求 processing_owner=human_review，因而失败。UI 结案后隐藏接管入口，但公开 takeover HTTP 路由 `B/api/conversations.py:67` 可达；不是通过非法 SQL 造出的状态。

真实隔离 PG，用生产 ConversationService 和有效 Command，执行 close→takeover→append；原始输出：

```text
closed_takeover_then_customer_input {'takeover_lifecycle': 'resolved', 'latest_owner': 'agent', 'open_review_status': 'open'}
```

状态：**发现时 FAIL。** 主 Agent 随后在 `B/application/human_review.py:23` 添加非 open 的409拒绝，并同步合同、增加回归；本实例按主 Agent 指令不复审这个新变更，报告不得标已关闭。复审标准：closed takeover 409且事务不改变状态；合法新来信重开后没有 open review，任务可正常领取。

### 功能逐条对照

表中“完整实现”仅指本期明确约定；后续部分单独写清。

| Spec 条目/原文约束 | 本期结论、位置与验证证据 |
|---|---|
| REQ-001:259 保存来源ID、split、时间、校验重复/时间/引用 | 后端完整实现，GUI导入基线因P3-F3失败。`B/domain/conversation.py:62/83` schema、`B/adapters/import_loader.py:12` 重复/首封/排序校验、`B/application/replay.py:37` 导入记录、`B/adapters/conversation_schema.py:55/158` 来源唯一和FK。`BT/test_conversations.py:179/192` 真实PG/非法输入测试通过，不能替代文件导入组件路径。 |
| REQ-001:260 同演示集合规范化身份归组 | 完整实现本期手工邮箱。`B/domain/conversation.py:29` trim/域名小写、`B/application/conversations.py:16` 锁后选择现有身份。`BT/test_conversations.py:77` 同地址复用、加号/句点不同地址不合并通过。公开 sender_key 未复核不做跨源合并。 |
| REQ-001:261 模式/重置记忆隔离 | 完整实现当前模式/分支隔离。`B/application/conversation_base.py:34` 独立branch，`B/adapters/conversation_schema.py:12/17/24` 完整scope FK；`BT/test_conversations.py:192` 和 `BT/test_postgres.py:90` 越界拒绝通过。重置及generation实际递增属于Phase12，未声称通过。 |
| REQ-001:262 多订单/多个待办按问题关联 | 部分实现且符合Phase3范围。`B/application/case_memory.py:9` 复用稳定correspondence issue与逐消息来源事实；`BT/test_conversations.py:173` 验证跨截点主键稳定。语义多事项/订单关联待Phase4/7，不标完整REQ通过。 |
| REQ-001:263–265 group_id非身份，未验证独立案例、邮箱不去加号句点 | 完整实现本期。`B/application/replay.py:26` 每源案例独立dataset，group_id只入data_imports；`B/domain/conversation.py:89` 禁止浏览器自行声明已复核；`F/components/mail-agent/ConversationList.vue:76` 明示身份未验证。`BT/test_conversations.py:77/150/185` 通过。 |
| REQ-002:276 仅真实消息前缀，不含未来正文 | 完整实现查询/任务协议层。`B/application/conversation_queries.py:50/58/64` 同一repeatable snapshot、按visible seq读消息/事实；`B/application/replay.py:60` 每次只推进一客户截点。`BT/test_conversations.py:161/162/172` 和真实HTTP network历史检查通过。 |
| REQ-002:277 历史客服/独立对照，不继承对照 | 完整实现本期人工审阅隔离；AI待Phase7。`B/application/human_review.py:73` 只有simulation写Message；`B/application/conversation_queries.py:71` 对照独立返回；`F/components/mail-agent/MessageTimeline.vue:49` 历史客服文字，`AgentProcessPanel.vue:62` 独立对照区。`BT/test_conversations.py:165–175` 和network哨兵检查通过。 |
| REQ-002:278 各截点从真实前缀重建，禁止沿用候选最终事实 | 完整实现基础事实。`B/application/case_memory.py:23` 删除旧投影后仅按可见真实消息写来源事实，第31行记revision/as_of；`BT/test_conversations.py:174/175` 验证3条真实事实且没有对照哨兵。未假称完成语义Understanding。 |
| REQ-002:279 统一as_of，禁止当前快照回退 | 已实现服务端游标as_of：`B/application/replay.py:41/67`；`BT/test_conversations.py:176` 实测2026-10-02T08:00Z。订单snapshot与知识available_at查询待Phase4/6，AC-006未验收。 |
| REQ-002:280 回放结束与解决分离，未知附件/快照明确 | 结束不结案完整实现：`B/application/replay.py:63`、`F/components/mail-agent/MessageComposer.vue:17/24`；`BT/test_conversations.py:177` 最后截点仍open。当前仅文本JSON、尚无图片/查单入口，附件/快照提示待后续接入，不声称全部通过。 |
| REQ-003:291 新有效客户来信自动运行，无逐封审批 | 完整实现持久任务触发协议。`B/application/conversation_base.py:64/80`、`B/application/task_queue.py:27` 原子cycle/run/job、`B/worker/runner.py:33`自动领取。`BT/test_protocol.py:138` 新输入与旧run屏障通过；模型执行Phase7重验。 |
| REQ-003:292–293 校验后一次性自动模拟回复、后续读取此前回复 | 模型/自动AI出站未在本期实现。`B/worker/protocol.py:29`只写真实protocol outcome、不写邮件；`BT/test_protocol.py:104/150` 协议完成仍只有客户邮件。未来AC-007/008/009未标通过。 |
| REQ-003:294 本地模拟，无真实邮箱投递 | 完整实现。`F/components/mail-agent/AgentProcessPanel.vue:7` 明示模型未接、不发真实邮件；`B/worker/protocol.py:13` 无provider/发送依赖；源码扫描及真实network记录provider_calls=0支持当前范围。 |
| REQ-003:295 同请求/重复消息/刷新不重复效果 | 完整实现当前命令协议。`B/application/idempotency.py:8` 同键同参原结果、异参409；`B/application/conversations.py:35` 来源去重；`F/api/mail-agent-request.ts:58` 未知结果沿用完整原命令。`BT/test_conversations.py:85`、`BT/test_protocol.py:66`、`FT/mail-workbench.test.ts:76` 通过；真实SSE补读无新任务。 |
| REQ-007:382–383 缺依据等模型handoff和可读原因 | 模型自动handoff待Phase7。当前主动takeover真实可操作，`B/application/human_review.py:20`；`F/components/mail-agent/HumanReviewPanel.vue:31`明确模型摘要未接。未以主动接管冒充AC-020。 |
| REQ-007:384 接管摘要与未发送草稿 | 完整实现本期原因/可见邮件/草稿和备注；业务诉求/订单/步骤/引用摘要待Phase7。`B/application/human_review.py:39`、`F/components/mail-agent/HumanReviewPanel.vue:23/47`；旧草稿PG回归通过。 |
| REQ-007:385 人审期间新来信归并，不自主回复 | 完整实现。`B/application/conversation_base.py:67/79` 保持human_review并suppressed，不enqueue；`B/application/human_review.py:23`撤销旧任务。`BT/test_conversations.py:101`、`BT/test_protocol.py:124`通过。 |
| REQ-007:386 人工回复/备注保存；只下一新来信恢复 | 正常路径及输入版本屏障完整实现。`B/application/human_review.py:64/80/88`、`B/application/conversation_base.py:67`；`BT/test_conversations.py:123`、`BT/test_human_events.py:40/59`两种顺序通过。已结案再接管异常路径另列P3-F1，不能免除。 |
| REQ-007:387 再次HITL；当前人工方案不入全局知识 | 完整实现主动人审基础。`B/application/human_review.py:26`复用唯一open review、`B/adapters/conversation_schema.py:135`部分唯一索引；`F/components/mail-agent/HumanReviewPanel.vue:21`再次接管。`BT/test_conversations.py:101/123`支持；无全局知识写入。 |
| REQ-007:388 人工确认结案 | 正常路径完整实现。`B/application/human_review.py:96`人工结案唯一写入口、`B/worker/protocol.py:36`协议完成不改resolved；`F/views/mail-agent/index.vue:234`确认框。`BT/test_conversations.py:140`撤销任务/新输入重开通过。P3-F1另列。 |
| REQ-008:400 唯一轮次/触发/输入权限版本/运行记录 | 完整实现本期字段：`B/adapters/conversation_schema.py:73/86/99`；`B/application/task_queue.py:38`版本由服务端绑定。`BT/test_protocol.py:106`沿用cycle且递增attempt通过。模型/资料/工具/usage字段待Phase7/11。 |
| REQ-008:401 简短处理说明/可验证过程，不存隐藏思维链 | 当前仅真实协议记录，`F/components/mail-agent/AgentProcessPanel.vue:39/49`；无虚构工具/usage。独立build和network outcome验证通过；业务工具过程待Phase7。 |
| REQ-008:402 同会话串行；新输入/接管旧run不得提交 | 完整实现当前Agent路径。`B/worker/leases.py:23/38`、`B/worker/protocol.py:15/26`租约和输入权限核验；`B/application/task_queue.py:9`关闭checkpoint及fence。`BT/test_protocol.py:124/138`通过。知识槽跨路径锁序见Stage2 MEDIUM。 |
| REQ-008:403 停止/失败重试/刷新恢复，晚到无效果 | 完整实现Agent协议。`B/worker/jobs.py:58/80`、`B/worker/leases.py:96`重启/过期中断、`F/components/mail-agent/AgentProcessPanel.vue:27/35`真实操作；`BT/test_protocol.py:83/106/152`通过，已completed拒retry，第119行验证。 |
| REQ-008:404 技术失败分类与可重试 | 当前真实user_stopped/worker_interrupted持久错误：`B/worker/jobs.py:64`、`B/worker/leases.py:116`，安全HTTP类别`B/api/conversations.py:21`。`BT/test_protocol.py:83/106`及`BT/test_api.py`通过；模型鉴权/超时/解析待Phase7。 |
| REQ-008:405 调用/无进展/预算限制 | 模型循环待Phase7；本期runner每任务仅一次协议commit，`B/worker/runner.py:34`，没有伪造token/预算结果。不宣称完整REQ实现。 |
| REQ-008:406 售后写去重/未知结果对账/停止不抹已执行操作 | 售后账本及工具待Phase9/10；本期record-only内部通知`B/application/event_store.py:43`只用于人审抑制/去重，不开放HTTP。`BT/test_human_events.py:59`重复通知和人审屏障通过，不替代售后AC。 |
| REQ-009:417 Art Design Pro布局/组件/三栏 | 代码完整复用外壳、公共主题/El组件：`F/views/mail-agent/index.vue:6/11/113`；复制来源基线`globalmail-agent/frontend/FRONTEND-BASELINE.md:3`。独立vue-tsc/Vite通过；实际视觉证据见Stage2。 |
| REQ-009:418 模式/客户/最新来信/处理状态可辨 | `F/components/mail-agent/ConversationList.vue:60/68/75`，`F/views/mail-agent/index.vue:39/42`，`MessageComposer.vue:8`；模式/状态过滤与会话切换`FT/mail-workbench.test.ts:102/120`通过，视觉另验。 |
| REQ-009:419 任务右栏/正式邮件中间/候选独立 | 完整实现本期。`F/components/mail-agent/MessageTimeline.vue:9`只messages，`AgentProcessPanel.vue:22/62`任务与对照独立；`BT/test_conversations.py:168/175`、network哨兵通过。 |
| REQ-009:420 文字图标区分来源，不只颜色 | 当前客户/历史客服/模拟人工完整明确：`F/components/mail-agent/MessageTimeline.vue:15/20/48`文字标签和Avatar，`AgentProcessPanel.vue:74`人工独立对照。模拟AI/Mock业务消息待后续，无假AI来源。 |
| REQ-009:421 推进/来信/人工完成/结案/停止重试/重置删除按钮 | 本期前6项均真实API：`F/views/mail-agent/index.vue:95/120/124`、`HumanReviewPanel.vue:79/112`、`MessageComposer.vue:11/61`；后端相应PG测试及前端17项通过。重置/删除Phase12，未展示死入口。 |

### 页面、共用状态和输入约束

| 条目 | 结论与证据 |
|---|---|
| 5.10 SCREEN-001、CMP-001、CMP-002/003文本、CMP-004任务、CMP-005主动人审、CMP-007案例导入 | 导入UI基线因P3-F3失败，其余本期代码和API齐全：`F/views/mail-agent/index.vue:10/81/87/116/145`；`ConversationDialog.vue:19/51/164`有真实表单/文件/调用，显示待校验数量，第70行未虚称已校验。PG/API/前端17项未覆盖导入Proxy路径，不能据此判UI全部通过。模型/图片/引用/trace子功能待对应Phase。 |
| SCREEN-002、CMP-006/008/009/010/011/012/013 | 后续知识/业务/图片交付，本期不造结果。`F/views/knowledge/index.vue:4`准确说明尚未接；`B/application/event_store.py:43`不开放假ERP HTTP接口。 |
| 5.10复用聊天页、保留阅读位置、多行文本、明确发送 | `F/components/mail-agent/MessageTimeline.vue:31/53/58`纯文本/保留换行、仅底部或主动提交滚动；`MessageComposer.vue:42/61`明确按钮；父页第81行传scrollSignal。动态滚动是否通过须实际浏览器证据，不能只据源码。 |
| 5.10左260/右360、内容宽不足1024抽屉、窄屏 | `F/views/mail-agent/index.vue:11/113/131/211`基于内容宽度、非window猜宽；640以下纵排。独立build通过；实际尺寸/明暗渲染见Stage2。 |
| 5.11默认/加载/空 | `F/views/mail-agent/index.vue:79/100`、`ConversationList.vue:40/44/45`空/加载/错误区分；`AgentProcessPanel.vue:24`无任务；`MessageComposer.vue:17`回放结束。`FT/mail-workbench.test.ts:17`选取/刷新仅GET通过。 |
| 5.11错误保留输入、成功反馈、忙碌防重复 | `F/composables/useMailWorkbench.ts:113/133/167/176`、`F/api/mail-agent-request.ts:13/58`；`F/components/mail-agent/ConversationDialog.vue:176`错误保留表单。`FT/mail-workbench.test.ts:43/76`真实composable故障分支通过。 |
| 5.11受限/历史只读/模型未配置 | `B/application/conversations.py:33`历史写拒绝；`F/components/mail-agent/MessageComposer.vue:14`运行/人审禁止推进；`AgentProcessPanel.vue:7`明确任务协议而无模型入口。当前不需要Key执行零模型协议；模型运行能力仍未启用。 |
| 5.12 mode、邮箱、subject、body、as_of | `B/domain/conversation.py:12/24/62/83`禁止额外字段、正文非空/20000、邮箱320/保留本地部分、主题500、时间含时区；`B/adapters/import_loader.py:18`排序；`B/application/replay.py:67`服务端生成as_of。`F/components/mail-agent/mail-inputs.ts:13/20/38`邻近校验、5MiB JSON；PG/前端输入测试通过。 |
| 5.12 human_reply/note、request_id/expected_version | `B/domain/conversation.py:47/53/58`20000/5000、输入版必填；`B/application/idempotency.py:8`和`conversation_lock.py:21`同键异参/版本屏障；`F/composables/useMailWorkbench.ts:182/195`版本由客户端自动带。旧草稿PG/前端回归通过。 |
| 5.12 customer_images/order_id/document/business_action/scenario_event | 分别Phase4/5/8/9/10；本期公开导入禁止未来事件/答案/路径，`B/domain/conversation.py:8/63` extra=forbid，`BT/test_conversations.py:185`通过。不将文本JSON能力冒充这些输入已接入。 |

### 指定 AC 与故障时序

| 条目 | 本期证据与边界 |
|---|---|
| AC-001 | `BT/test_conversations.py:77` 同邮箱两封同conversation、首封可读；独立PG通过。 |
| AC-002 | `BT/test_conversations.py:150/157` 相同group的不同源会话不合并；公开未验证sender_key拒跨源身份合并。独立PG通过；不是可信身份来源复核验收。 |
| AC-003 | `BT/test_conversations.py:85/155` 同请求/来源消息/来源包重复不增加消息/任务；独立PG通过。 |
| AC-004/005/027 | `BT/test_conversations.py:161/165/172/175`、`globalmail-agent/scripts/phase3-network-check.py:71` 哨兵验证真实前缀/人工独立对照/未来不提前露出通过。AI请求/产物Phase7重验，不标全量AI AC通过。 |
| AC-006 | 未验收；订单snapshot属于Phase4，无假查单接口。来源：`DEV-PLAN.md:103`。 |
| AC-021 | `BT/test_conversations.py:101`、`BT/test_protocol.py:124` 接管新输入保留邮件、不排自主任务，真实PG通过。 |
| AC-023 | `BT/test_conversations.py:140/177` 人工才resolved、历史末截点仍open。模型解决建议待Phase7；已结案接管异常P3-F1未免除。 |
| FT-01 | `BT/test_protocol.py:124/138` 在新输入/接管屏障之后旧complete返回False；新任务最新输入完成，PG通过。未来真实模型副作用另验。 |
| FT-02 | `BT/test_human_events.py:40/59`交换业务通知/人工回复顺序，过期表单拒绝、业务事件抑制、下一新来信恢复；第13行旧草稿刷新屏障PG通过。 |
| FT-05 | `BT/test_protocol.py:83/106/152`租约/重启中断与显式同cycle重试、completed拒retry通过；真实模型/出站后checkpoint缺失待Phase7。另有启动故障恢复实测见原始输出。 |
| FT-07 | 当前记账入口`B/application/event_store.py:43`去重/人审抑制通过`BT/test_human_events.py:59`；真实业务wait先后、wake_pending和消费属于Phase10，未验收。 |
| FT-08 | `BT/test_conversations.py:150`、network哨兵当前历史/事实/人工审阅隔离通过；未来订单/资料/AI读取接入后重验。 |
| UI事件事务顺序与SSE | `B/application/event_store.py:14/16`同会话行锁下递增seq，事实同commit；`B/api/events.py:25/35/55/70`游标/Last-Event-ID/15秒心跳；`F/composables/conversation-event-session.ts:27/52/66`校验scope、去重、关闭旧连接。本实例两真实连接观察pg_blocking_pids确认阻塞后顺序commit `[2,3]`；network真实HTTP补读/心跳/no-new-run通过。 |

### Spec 漂移和引导真实性

未发现本期阻塞scope creep。样例API `B/api/conversations.py:11/34`只提供受控输入样例，不返回业务答案；协议runner `B/worker/protocol.py:30`准确标明模型未接；内部通知 `B/application/event_store.py:43`不开放HTTP，不冒充Phase10唤醒；隔离验收服务器 `globalmail-agent/scripts/phase3-test-server.py:31`独立端口/schema/objects并清理，不成为业务功能。对应范围来源是 PHASE-3-CONTRACT/IMPLEMENTATION。界面不存在“调用尚未实现模型/知识/删除”的可点击成功假入口，证据见 `F/components/mail-agent/AgentProcessPanel.vue:7`、`F/views/knowledge/index.vue:4`。

## 已执行的 Stage 2 补充检查（不形成通过结论）

本节检查发生在实际GUI发现P3-F3之前；发现HIGH后不继续Stage2。保留真实已执行结果，不将其解释为越过Stage1门禁后的正式PASS。

### MEDIUM P3-F2：知识槽完成与同会话新输入锁逆序，40P01死锁

要求：`AGENT-ARCHITECTURE.md:289`统一slot在conversation之前，不能持业务锁回头取slot；`DEV-PLAN.md:93`本期交付知识独立槽及租约/fence。

- `B/worker/protocol.py:15`先锁 job.kind 的slot，第19行后锁conversation；knowledge job因此是 knowledge→conversation。
- `B/application/conversation_lock.py:15`所有会话操作只先锁agent slot，第17行锁conversation；`B/application/task_queue.py:19` invalidate随后更新当前run占用的slot。若当前任务在knowledge槽，实际顺序是 agent→conversation→knowledge。
- `B/worker/jobs.py:47/68` stop存在同类后取job.kind slot路径。`BT/test_protocol.py:165`仅用不同会话验证双槽，不覆盖此竞争。

本实例使用与既有知识槽测试相同的内部 job.kind 控制，在隔离PG创建合法task并领取knowledge租约；没有新增HTTP假知识API。屏障暂停knowledge completion于slot锁之后，启动同会话合法append，使用pg_blocking_pids确认它已等待knowledge槽，再放行completion。原始输出：

```text
controlled_same_conversation_knowledge_lease_vs_customer_input {'slot_owner_confirmed_blocks_other_transaction': True, 'outcomes': [{'result': True}, {'error_type': 'OperationalError', 'sqlstate': '40P01'}], 'scope': 'internal job-kind control identical to existing knowledge-slot test; production Phase3 only creates agent jobs'}
```

PostgreSQL官方文档确认行锁逆序可导致死锁并回滚其中一个事务：[Explicit Locking / Deadlocks](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-DEADLOCKS)。这里40P01为实测，不用数据库自动回滚当成正常通过。

**本期生产只创建agent job，因此不是Phase3公开用户路径的HIGH；独立知识槽协议存在MEDIUM缺陷。** 修复标准：知识任务域与Agent任务控制明确隔离，或参与竞争的slot按固定顺序全部在conversation之前获取，并覆盖同会话受控竞争；不能只靠不同会话顺畅用例宣称全部锁序通过。状态：本轮发现时FAIL，若主Agent随后修复需fresh审查。

### 代码质量、安全和测试真实性

| 检查 | 结论与证据 |
|---|---|
| 类型/命名/职责/300行门槛 | 当前新增核心TS无any，明确Conversation/Run/HumanReview/API/Event类型：`F/api/mail-agent-contract.ts:22/54/64/82`。核心会话/查询/回放/人审/租约/命令拆开；`F/composables/useMailWorkbench.ts:7`最长262行。审查范围56个Python/TS/Vue文件无超过300行，另检查request79/contract117/workbench247行；迁移216行。独立vue-tsc通过。 |
| 固定迁移与metadata一致 | `globalmail-agent/backend/migrations/versions/0002_conversations_jobs.py:9/198`使用本迁移冻结MetaData，未动态导入当前业务schema；`B/adapters/conversation_schema.py:5`运行metadata注册，`B/adapters/database.py:8/34`检查版本和全部表列。独立真实PG迁移后Alembic compare_metadata结果 `[]`。 |
| 事务/正文失败清理/来源依赖 | `B/application/conversation_base.py:22`先BodyWriter再DB事务，失败退文件；`B/adapters/body_store.py:19/37`同conn登记对象/依赖，`read_body:50`完整scope+摘要核验。`BT/test_conversations.py:192/202`跨scopeFK和真实失败清理通过。崩溃后孤儿对象清理仍归Phase12，不假称完整删除。 |
| 注入/XSS/任意路径 | 当前核心源码扫描未发现eval、v-html、dangerouslySetInnerHTML/innerHTML、输入字符串拼SQL或浏览器公开Key变量。`F/components/mail-agent/MessageTimeline.vue:31`Vue文本插值；`B/application/idempotency.py:12`SQL绑定参数；`B/adapters/body_store.py:26/50`服务分配UUID、scope检查。`BT/test_conversations.py:235/236`脚本文本/非法包测试及编译通过。无新增安全HIGH。 |
| 凭据/错误输出 | 源码扫描无硬编码实际Key；`B/api/conversations.py:24`、`B/main.py:43/52`安全类别；`B/worker/runner.py:38`仅安全警告，`B/api/security.py:23/35/37`Host/Origin/JSON限制。`BT/test_api.py`和`BT/test_postgres.py:104`SECRET_MARKER不泄漏断言通过。数据库URL只从本地设置注入环境，未打印。 |
| 后端测试前提真实性 | 使用真实生产service/Pydantic/迁移、随机schema和TemporaryDirectory，`BT/test_conversations.py:31`、`BT/test_protocol.py:27`注册清理；32项无skip。租约过期用明确数据库时间修改，第87行；新输入/接管用真实服务而不修改处理权。知识槽第169行内部kind控制不代表生产知识管线，P3-F2复现明确沿用该前提。 |
| 前端故障/交互测试真实性 | `FT/mail-workbench.test.ts:43/76/102/138`直接运行生产composable，覆盖409保留、未知网络结果同key同payload、晚到响应、review版本；但普通对象未覆盖导入组件的嵌套Proxy，P3-F3证实盲区。`FT/conversation-events.test.ts`受控EventStream只证明客户端协议，不能替代真实浏览器重连；后者由network HTTP证据补充。 |
| 启动故障恢复 | `B/main.py:28`配置了engine即启动worker，不因首次ready失败永不启动；`B/worker/runner.py:28/31`首次成功recover保留restart语义。本实例用可控engine故障注入+真实PG恢复，503→200、旧running中断、新queued完成、日志1条，原始输出见下。不是物理数据库关机/重启实测，当前持久套件尚未加入这个完整恢复用例。 |
| 测试盲区 | 初审32项遗漏已结案接管状态，知识独立槽测试遗漏同会话锁序；本轮额外生产service/真实PG复现分别证明P3-F1/F2。不能用“32项全绿”代替它们。真实模型/工具/自动出站/checkpoint的端到端行为按Phase7/9/10继续验，不在当前报告伪判通过。 |

### 实际视觉与邻居对比

主 Agent 在本期隔离15174/18181浏览器打开工作台及knowledge邻居页采集以下8张PNG；本实例逐张调用view_image查看实际像素，并以PNG头核验宽高。此处是实际渲染证据，非DOM类名推断；因Stage1仍有待新复审的HIGH，不签署整体视觉/Stage2 PASS。

| 实际文件（相对项目根目录） | 已看到的实际效果与对应代码 |
|---|---|
| `output/playwright/phase3-light-wide.png`，1600×1000 | 工作台亮色三栏；左260/right360对应`F/views/mail-agent/index.vue:11/113`，中间自适应。最后客户来信和模拟人工分明文标签、时间、序号显示，正文保留换行；右侧任务折叠/人审/结案没有混入正式邮件。对应`MessageTimeline.vue:19/31/48`、`AgentProcessPanel.vue:22/83`。 |
| `output/playwright/phase3-history-light.png`，1600×1000 | 三封实际历史邮件按客户/历史客服/客户区分；右侧人工独立对照折叠；AI区准确显示尚未接入；下方2/2客户截点与回放结束，仍可人工结案。对应`MessageComposer.vue:5/17/24`、`AgentProcessPanel.vue:62/74`。截图是推进后截点，不拿它代替未来不提前可见的network哨兵断言。 |
| `output/playwright/phase3-dark-wide.png`，1600×1000 | 暗色外壳、列表、按钮、输入边框、双空态适配；此张未选会话，只证明该状态，不声称暗色消息/表单已验收。对应`F/views/mail-agent/index.vue:6/100/128`、`ConversationList.vue:7/36`。 |
| `output/playwright/phase3-dark-narrow.png`，1280×800 | 实际内容宽不足1024时右栏不挤中栏，保留左列表和中间邮件；未选会话无详情入口属于代码规定。对应`F/views/mail-agent/index.vue:51/112/211`。 |
| `output/playwright/phase3-light-narrow-drawer.png`，1280×800 | 已选历史会话的处理记录/独立审阅/人审移入右侧ElDrawer，关闭图标、文字和内容均可读；遮罩和页面的其他控件采用现有El样式。对应`F/views/mail-agent/index.vue:131`和`AgentProcessPanel.vue:83`。 |
| `output/playwright/phase3-dark-narrow-drawer.png`，1280×800 | 暗色已选人审会话；任务、待人审标记、接管原因及未发送回复textarea正确渲染，输入白字与背景/边框可辨；不是只验证暗色空态。对应`HumanReviewPanel.vue:23/47/58`。 |
| `output/playwright/phase3-knowledge-light.png`、`phase3-knowledge-dark.png`，均1600×1000 | 实际邻居基准：与工作台使用同一侧栏/顶栏/页签、主题蓝、文字层级、page-content边框圆角和亮白/暗灰背景，空插图及提示风格一致。knowledge明确“尚未接入”，未诱导不存在功能。对应`F/views/knowledge/index.vue:2/4`、工作台`index.vue:6`和公共Art布局。 |

没有独立设计稿/Brief，以复制的Art Design Pro实际组件为基线；不能另造像素设计标准。以上可确认当前已采集状态的风格/布局一致和文字来源分区正确，不把8张静态截图当成所有交互成功证明。

主 Agent 本轮实际GUI操作结果（来自派发消息，本实例未亲自操作浏览器）：新建→接管→旧草稿→新增输入→保存旧草稿→整页刷新后完成仍禁用→明确核对→模拟人工发送→下一客户来信恢复agent，4封可见邮件、零假AI。后来又在暗色抽屉核对5封邮件与未发送草稿。GUI导入首次失败及后续修复已列P3-F3，需fresh复验。动态滚动阅读位置、完整错误文件操作等未由本实例独立GUI实测，不在此伪判全部通过。

## 验证命令和原始输出

后端根PowerShell（数据库连接串不打印）：

```powershell
. 'globalmail-agent/scripts/local-common.ps1'
$phaseSettings=Get-LocalSettings
$env:GLOBALMAIL_TEST_DATABASE_URL=$phaseSettings.database_url
$env:PYTHONPATH=(Resolve-Path 'globalmail-agent/backend/src').Path
& 'globalmail-agent/backend/.venv/Scripts/python.exe' -m unittest discover -s globalmail-agent/backend/tests -v
```

原始摘要与关键输出（完整名称覆盖api、conversations、human_events、postgres、protocol；无skip）：

```text
D:\Work_Project\globalmail-agent\globalmail-agent\backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_saving_stale_draft_and_reloading_does_not_acknowledge_new_input (test_human_events.HumanEventTests.test_saving_stale_draft_and_reloading_does_not_acknowledge_new_input) ... ok
protocol_worker_dependency_unavailable
test_knowledge_slot_does_not_occupy_agent_slot (test_protocol.ProtocolTests.test_knowledge_slot_does_not_occupy_agent_slot) ... ok
test_lease_expiration_blocks_old_commit_and_requires_explicit_retry (test_protocol.ProtocolTests.test_lease_expiration_blocks_old_commit_and_requires_explicit_retry) ... ok
test_new_message_supersedes_running_and_queues_latest_context (test_protocol.ProtocolTests.test_new_message_supersedes_running_and_queues_latest_context) ... ok
test_restart_interrupts_active_but_preserves_unclaimed_queue (test_protocol.ProtocolTests.test_restart_interrupts_active_but_preserves_unclaimed_queue) ... ok
test_single_slot_concurrent_claim_and_read_only_refresh (test_protocol.ProtocolTests.test_single_slot_concurrent_claim_and_read_only_refresh) ... ok
test_stop_retry_retains_cycle_and_late_result_has_no_effect (test_protocol.ProtocolTests.test_stop_retry_retains_cycle_and_late_result_has_no_effect) ... ok
test_takeover_and_new_input_barriers (test_protocol.ProtocolTests.test_takeover_and_new_input_barriers) ... ok
----------------------------------------------------------------------
Ran 32 tests in 14.972s

OK
```

警告及protocol_worker_dependency_unavailable来自兼容/预期故障路径，不计测试失败；也不删除原始警告。额外复现各自复用ProtocolFixture并finally执行doCleanups，不改浏览器会话。

前端cwd `globalmail-agent/frontend`，命令 `pnpm exec tsx --test scripts/*.test.ts`，原始汇总：

```text
ℹ tests 17
ℹ suites 0
ℹ pass 17
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 662.7675
```

独立编译 `pnpm build`，exit_code=0；原始输出，省略345行资源大小表：

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3255 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 25.76s
```

```powershell
& 'globalmail-agent/backend/.venv/Scripts/python.exe' -m compileall -q globalmail-agent/backend/src globalmail-agent/backend/migrations globalmail-agent/backend/tests
```

```text
compileall_exit=0
migration_metadata_diffs []
two_connections_commit_order {'second_confirmed_blocked_before_first_commit': True, 'sequences': [2, 3], 'kinds': ['review.concurrent.first', 'review.concurrent.second']}
startup_dependency_fault_then_real_PG_recovery {'initial_ready_http': 503, 'recovered_ready_http': 200, 'pre_restart_run': 'interrupted', 'queued_run': 'completed', 'warnings': ['protocol_worker_dependency_unavailable']}
```

主 Agent 的真实HTTP验收记录：`tmp/phase3-network-check.json`，对应脚本 `globalmail-agent/scripts/phase3-network-check.py:36/57/71`，本实例已读取记录并检查脚本断言；原始JSON：

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

## 交回路径

P3-F1/P3-F3属Stage1功能实现，回dev-builder；P3-F2属已执行质量检查中的并发缺陷，回bug-fixer。主 Agent 已报告实施修复，但修复后必须重新派fresh code-reviewer从Stage1开始，复验本轮发现及最终变更，再签署Phase3验收。当前报告没有将模型、业务和图片未接入部分包装为完成。
