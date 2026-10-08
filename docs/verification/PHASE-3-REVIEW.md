# Phase 3 独立审查（初审）

日期：2026-10-08。审查者：fresh `code-reviewer`。范围：当前未提交 Phase 3 增量，依据根目录 AGENTS、Product-Spec、DEV-PLAN、AGENT-ARCHITECTURE，`code-review`/`dev-builder` Skill、PHASE-3-IMPLEMENTATION/CONTRACT 及 AGENT-ACCEPTANCE 原文。仅审查和记录，未修复、未提交。

**结论：Stage 1 FAIL，发现 1 项 HIGH；Stage 2 未执行。31 项后端和 17 项前端已有测试通过，但没有覆盖发现的合法操作序列，不能据此通过 Phase 3。** 本报告记录发现时的实现；主 Agent 后续修复须重新从 Stage 1 审查。

初审结束时主 Agent 已通知修复：ReviewDraft/saveHuman 显式携带已核对的 expected_input_revision，save_review 保留该版本，并新增真实PG回归。本审查者没有对修复后版本复验；此说明不改写下面原始FAIL事实，修复结果由下一次fresh审查确认。

## Stage 1：阻塞问题

### HIGH P3-R1：保存旧草稿会静默把已覆盖输入版本更新为最新；整页刷新后可发送未核对新来信的旧回复

要求原文：DEV-PLAN.md:101，“过期人工表单409”；AGENT-ARCHITECTURE.md:114，“UI 已覆盖最新输入版本”；AGENT-ARCHITECTURE.md:122，“若另一封来信先提交，回复返回 409 并提示重新核对”。

代码证据：

- `globalmail-agent/backend/src/globalmail_agent/application/human_review.py:39`，保存草稿只检查 `review.version`，随后在第54行无条件设置 `input_revision=conversation["input_revision"]`；`ReviewDraft` 在 `globalmail-agent/backend/src/globalmail_agent/domain/conversation.py:47` 未携带人工已核对的输入版本。
- `globalmail-agent/frontend/src/components/mail-agent/HumanReviewPanel.vue:79`，旧草稿处于 `stale` 状态时仍可“保存草稿”，只有完成按钮受 `stale` 限制。允许保留旧草稿本身合理，但不能因此声明已核对新输入。
- `globalmail-agent/frontend/src/composables/useMailWorkbench.ts:71`、第74行，新实例从服务器草稿及 `review.input_revision` 初始化表单；第182行完成人工回复提交这个版本。因此整页刷新后旧草稿被当成覆盖最新输入，明确核对步骤消失。

真实隔离 PostgreSQL 复现，使用生产 `ConversationService` 和有效 Pydantic command，未改表、未使用非法版本：

1. 创建会话、接管，在 input_revision=1 保存回复草稿。
2. 合法追加新来信，input_revision=2，原草稿仍只覆盖版本1。
3. 使用最新 review.version 再保存同一旧草稿，没有“我已核对最新邮件”动作。
4. 重新 GET 详情，等价于整页刷新后前端初始化；review.input_revision 已变为2。
5. 用该持久版本和原草稿调用 human_reply，实际成功新增模拟人工邮件。

原始输出：

```text
before_stale_save {'form_input_revision': 1, 'review_input_revision': 1, 'conversation_input_revision': 2}
after_stale_save_and_reload {'review_input_revision': 2, 'conversation_input_revision': 2, 'draft': 'Reply written before new input'}
completion {'accepted': True, 'owner': 'human_wait_customer', 'message_count': 3}
```

影响：人工表单版本屏障可被正常“保存草稿→刷新”流程绕过；最新来信未被核对却被回复屏障覆盖。修复标准：保存草稿保持其真实已核对输入版本，或显式携带并持久化用户核对的版本；整页刷新、SSE刷新和保存草稿均不能替代明确核对。须补“新输入→保存旧草稿→新前端实例/整页刷新→仍过期”的前后端回归，核对前完成操作应409或在UI保持禁用，核对后才可成功。

## Stage 1：逐条需求对照

下面路径前缀：`B/` = `globalmail-agent/backend/src/globalmail_agent/`，`F/` = `globalmail-agent/frontend/src/`，`BT/` = `globalmail-agent/backend/tests/`。表中“已实现”只指 Phase 3 明确交付；未来模型、业务、图片或删除功能不记作本期缺失，也不声称产品 AC 全部通过。

| Spec 约束 | 本期结论与代码证据 | 本轮验证证据 |
|---|---|---|
| REQ-001 保存源编号、split、时间，校验重复ID/时间/引用 | 已实现。`B/domain/conversation.py:61`、`B/adapters/import_loader.py:12`、`B/application/replay.py:31`、`B/adapters/conversation_schema.py:55`、第158行 | BT/test_conversations.py:178、第191行：schema拒绝非法包，复合FK拒绝跨scope对象；真实PG通过 |
| REQ-001 同演示邮箱归组，未经核验sender_key仅独立案例 | 已实现本期边界。`B/domain/conversation.py:29`、`B/application/conversations.py:12`、`B/application/replay.py:27`；公开包拒绝identity_verified=true | BT/test_conversations.py:77、第149行通过；保留本地部分加号、句点，规范化域名 |
| REQ-001 模式/分支记忆隔离 | 已实现。`B/application/conversation_base.py:34`创建独立branch；`B/adapters/conversation_schema.py:12`、第17行对子表/正文使用全部scope FK | BT/test_conversations.py:191和已有BT/test_postgres.py scope测试通过 |
| REQ-001 多订单、多待办、按事项关联 | 部分实现且按计划限定。`B/application/case_memory.py:9`复用稳定correspondence issue；语义多事项/订单关联属于Phase 7/4，未宣称已实现 | BT/test_conversations.py:149证明issue主键跨截点稳定，不证明多诉求理解 |
| REQ-001 group_id不得作身份、身份缺失标识 | 已实现。`B/application/replay.py:27`每独立案例独立dataset；group_id仅写data_imports。`F/components/mail-agent/ConversationList.vue:81`显示身份未验证 | BT/test_conversations.py:149同group不同源会话不合并 |
| REQ-002 当前真实消息前缀，不含未来正文 | 已实现查询/任务协议层。`B/application/conversation_queries.py:47` repeatable snapshot，第59/65行仅取当前可见消息/事实；`B/application/replay.py:47`服务端生成截点 | BT/test_conversations.py:149初截点无DEMO-1001未来哨兵；推进后才出现 |
| REQ-002 历史客服/对照区分，对照不入下一轮 | 已实现人工对照基础；AI结果待Phase 7。`B/application/human_review.py:71`仅simulation写Message；`B/application/conversation_queries.py:72`独立comparisons；`F/components/mail-agent/MessageTimeline.vue:50`、AgentProcessPanel.vue:61分区 | BT/test_conversations.py:149：审阅后消息仍1封，下一截点事实无对照文本 |
| REQ-002 从真实前缀重建案件事实 | 已实现基础事实。`B/application/case_memory.py:24`删除旧投影，只从visible_messages生成来源事实及依赖；自由note不写human_decision | BT/test_conversations.py:149事实3条且不含上一轮对照；不是语义记忆验收 |
| REQ-002 统一as_of，禁止未来订单/知识回退 | 本期实现不可由客户端指定的游标as_of：`B/application/replay.py:40`、第67行。订单/知识尚未接，AC-006待Phase 4/6 | BT/test_conversations.py:149验证as_of=2026-10-02T08:00Z；未执行未来snapshot查单验收 |
| REQ-002 回放结束不等于解决；缺附件/快照标注 | 结束与解决已分离：`B/application/replay.py:63`、`F/components/mail-agent/MessageComposer.vue:13`；当前仅文本JSON，无附件/查单入口，相关未知状态待Phase 4/8 | BT/test_conversations.py:149完成最后截点仍lifecycle=open |
| REQ-003 有效新来信自动运行，无逐封审批 | 已实现自动建cycle/run/job，当前runner仅协议验证。`B/application/conversation_base.py:64`、`B/application/task_queue.py:27`、`B/worker/runner.py:27` | BT/test_protocol.py:138新输入替代旧run，最新任务完成；模型执行待Phase 7 |
| REQ-003 最终自动回复一次性模拟出站、读取先前自动出站 | 未在本期实现，DEV-PLAN明确Phase 7接模型；`B/worker/protocol.py:29`仅outcome=protocol_verified_model_not_connected，无假邮件 | BT/test_protocol.py:83完成协议后消息仍1封；AC-007/008/009未标通过 |
| REQ-003 本地模拟标记，无真实邮件投递 | 已实现界面真实性。`F/components/mail-agent/AgentProcessPanel.vue:8`说明不生成AI回复/不向真实邮箱发信；当前API无发送服务 | frontend构建通过；没有模型/邮箱调用验收声明 |
| REQ-003 重复提交、刷新不能重复执行/新增邮件 | 已实现本期持久协议。`B/application/idempotency.py:8`同键同参原结果、异参409；`B/application/conversations.py:35`来源消息去重；详情/SSE仅GET | BT/test_conversations.py:85、BT/test_protocol.py:66及前端选择/刷新测试通过 |
| REQ-007 缺依据/冲突/失败方案转人审，模型说明原因/证据缺口 | 模型驱动handoff待Phase 7。当前主动takeover真实可操作，`B/application/human_review.py:20`、`F/components/mail-agent/HumanReviewPanel.vue:33`明确未接模型摘要/业务查询 | BT/test_protocol.py:124主动接管撤销旧任务；不声称AC-020已通过 |
| REQ-007 接管摘要/未发送草稿 | 已实现原因、可见邮件核对、草稿/备注基础；订单、步骤、资料摘要待Phase 7。`B/application/human_review.py:39`、`F/components/mail-agent/HumanReviewPanel.vue:23` | BT/test_conversations.py:101草稿持久与冲突保留；但P3-R1是版本阻塞 |
| REQ-007 人审期间追加但不排自主任务 | 已实现。`B/application/conversation_base.py:67`保持human_review并suppressed；`B/application/human_review.py:23`撤销执行权 | BT/test_conversations.py:101、BT/test_protocol.py:124真实PG通过 |
| REQ-007 完成人工回复与备注、之后只等下一封新来信恢复 | 正常路径已实现；完整协议因P3-R1不通过。`B/application/human_review.py:59`检查输入版并转human_wait_customer；`B/application/conversation_base.py:68`新来信才恢复 | BT/test_conversations.py:122及BT/test_human_events.py:13/32两种顺序通过；额外复现揭示刷新绕过 |
| REQ-007 可反复HITL，一次方案不进全局知识 | 已实现主动接管基础。`B/application/human_review.py:20`复用唯一open review；`B/adapters/conversation_schema.py:135`部分唯一索引；正文scope为conversation | BT/test_conversations.py:101，UI HumanReviewPanel.vue:21再次接管入口；无知识写入 |
| REQ-007 只有人工确认结案 | 已实现。`B/application/human_review.py:94`唯一结案写入口；`B/worker/protocol.py:36`完成不改resolved；`F/views/mail-agent/index.vue:237`危险动作确认 | BT/test_conversations.py:139结案撤销旧任务，新来信重开 |
| REQ-008 唯一轮次、触发、输入/权限/分支版本及过程持久化 | 已实现本期字段。`B/adapters/conversation_schema.py:73`、第86/99行；模型/工具/usage/资料版本待Phase 7/11 | BT/test_protocol.py:106原cycle重试唯一；前后端既有测试通过 |
| REQ-008 说明与可验证工具记录，不展示思维链 | 当前仅展示真实任务协议结果，`F/components/mail-agent/AgentProcessPanel.vue:39`；工具记录待Phase 7 | 无伪造工具步骤/结果；build通过，不等于未来工具验收 |
| REQ-008 会话串行，新来信/接管旧运行不得提交 | 已实现协议提交门。`B/worker/leases.py:23`、`B/worker/protocol.py:13`核对租约、权限、输入；`B/application/task_queue.py:9`关闭checkpoint资格并递增slot fence | BT/test_protocol.py:124/138两种受控时序通过 |
| REQ-008 停止、显式重试、刷新恢复记录，晚到结果拒绝 | 已实现。`B/worker/jobs.py:58`、第80行；`B/worker/leases.py:96`重启/过期中断；`F/components/mail-agent/AgentProcessPanel.vue:24`操作入口 | BT/test_protocol.py:83/106/152通过；新任务沿用原cycle，GET无调度副作用 |
| REQ-008 技术失败类别、预算/无进展、售后写去重与未知结果对账 | 本期仅真实worker_interrupted/user_stopped任务原因；模型错误/预算和售后写工具待Phase 7/9/10。`B/worker/leases.py:119`、`B/worker/jobs.py:65` | 未把技术失败包装成业务结论；相关未来AC未验收 |
| REQ-009 Art Design Pro外壳、chat基础、三栏 | 代码已使用既有page-content、El组件、公共主题工具类；左260、右360、中间自适应，`F/views/mail-agent/index.vue:6`、第12/112行；动态视觉尚未完成，不能判数值/渲染通过 | frontend vue-tsc/Vite通过；因Stage 1 HIGH停止，本审查者未打开邻居页面 |
| REQ-009 模式/客户/最新来信/状态可辨 | 代码已实现，`F/components/mail-agent/ConversationList.vue:52`、`F/views/mail-agent/index.vue:35`、MessageComposer.vue:8 | 前端列表/过滤/composable测试通过；视觉待复审 |
| REQ-009 过程仅右栏，正式邮件中间，对照独立 | 已实现本期分区代码。`F/components/mail-agent/MessageTimeline.vue:8`只渲染messages；AgentProcessPanel.vue:21/61独立任务和对照 | BT/test_conversations.py:149及frontend编译通过 |
| REQ-009 文字/图标来源区分 | 本期customer/historical_staff/simulated_human明确文字；模拟AI/Mock来源待后续，`F/components/mail-agent/MessageTimeline.vue:49` | 当前消息枚举无伪AI；frontend编译通过 |
| REQ-009 推进/来信/人工完成/结案/停止重试/重置删除按钮 | 本期前6项有真实API；`F/views/mail-agent/index.vue:76`、第115行，`F/components/mail-agent/MessageComposer.vue:11`、HumanReviewPanel.vue:79/112。重置删除在Phase 12，无死入口 | 后端31、前端17通过；P3-R1使人工版本部分不合规 |

### 5.10–5.12、AC 和故障时序覆盖

| 条目 | 本期结论与证据 |
|---|---|
| SCREEN-001、CMP-001–005、CMP-007当前会话部分 | 新建/JSON导入、筛选分页、可见正文、输入/回放、人审和运行操作代码齐全，`F/views/mail-agent/index.vue:10`、`F/components/mail-agent/ConversationDialog.vue:112`。CMP-002/003图片、CMP-004工具/usage/trace、CMP-005模型摘要待相应后续阶段；CMP-007删除待Phase 12 |
| SCREEN-002、CMP-006/008–013 | 不在Phase 3：知识、引用、业务单、模拟ERP、资料核对/版本/检索/图片证据按DEV-PLAN Phase 4–12实施；无新增假功能入口。Phase 3仅知识独立槽协议，`B/worker/leases.py:36` |
| chat滚动、多行输入、明确发送、公共风格 | `F/components/mail-agent/MessageTimeline.vue:58`只有底部/主动提交才滚到底；正文纯文本保留换行（第31行）；`F/components/mail-agent/MessageComposer.vue:25`明确按钮。动态滚动与视觉未由本审查者验收 |
| 桌面/窄面板布局 | 左260/右360、内容宽不足1024抽屉、640以下纵排已编码：`F/views/mail-agent/index.vue:211`；视觉待复审，不用静态类名代替渲染证据 |
| 5.11 默认/加载/空/错误/成功/受限 | 有ElEmpty/ElSkeleton、忙碌按钮、错误保留输入和成功提示：`F/views/mail-agent/index.vue:50`、第69/96行；`F/composables/useMailWorkbench.ts:105`；历史只读由`B/application/conversations.py:33`拒绝，模型未接文案准确。P3-R1导致过期人审保护不完整 |
| 5.12 mode、邮箱、subject、body、as_of | `B/domain/conversation.py:12/24/61/82`校验文本长度、非空、时区与公开包；`B/application/replay.py:47`服务生成as_of；`F/components/mail-agent/mail-inputs.ts:13`字段邻近错误。订单/图片/知识/业务输入按后续Phase，无假接入 |
| 5.12 human_reply/note、request_id/expected_version | `B/domain/conversation.py:47/52/57`限制20000/5000；`B/application/idempotency.py:8`、`B/application/conversation_lock.py:14`检查幂等与版本；**人审草稿已覆盖输入版本因P3-R1失败** |
| AC-001/002/003 | 本期对应PG验证通过：BT/test_conversations.py:77/85/149；身份、group隔离、来源重复不新增消息/任务 |
| AC-004/005/027 | 真实前缀/人工对照隔离基础通过BT/test_conversations.py:149；AI执行与AI产物未接，不能声称完整AI AC通过 |
| AC-006 | 明确未验收；Phase 4订单snapshot查询未接，不算Phase 3 HIGH |
| AC-021 | 正常接管期间追加不触发通过BT/test_conversations.py:101、BT/test_protocol.py:124 |
| AC-023 | 人工结案基础通过BT/test_conversations.py:139；模型建议解决的分支需Phase 7重验 |
| FT-01 | 协议旧commit屏障通过BT/test_protocol.py:124/138；真实模型晚返回Phase 7重验 |
| FT-02 | 业务事件先/后人工回复通过BT/test_human_events.py:13/32；新来信之后恢复资格。**保存旧草稿+刷新扩大了合法竞争路径，P3-R1失败** |
| FT-05 | 重启标interrupted、queued可保留、原cycle显式重试通过BT/test_protocol.py:152/106；真实模型/出站/checkpoint待Phase 7 |
| FT-07 | 本期record-only helper无HTTP/无wake注入，`B/application/event_store.py:53`；事件去重、人工屏障通过BT/test_human_events.py:32；WaitCondition先后/wake_pending属于Phase 10，未验收 |
| FT-08 | 当前消息/事实/人工审阅隔离通过BT/test_conversations.py:149；未来订单、知识、AI产物读取在后续接入时重验 |
| SSE与事件commit顺序 | `B/application/event_store.py:11`会话锁内seq同事务；`B/api/events.py:22`支持after_seq/Last-Event-ID/15秒heartbeat；`F/composables/conversation-event-session.ts:51`断线原生重连、切会话关闭且验scope。已有PG用例BT/test_conversations.py:211仅串行读事件，API用例第226行验证非法游标；前端事件3测试为受控Stream，不能替代真实HTTP断线补读或并发commit顺序验证。Stage 1因HIGH停止，本报告不判真实SSE重连验收完成 |

### Spec 漂移

当前新增的 example JSON、协议runner、record-only business_notification 和独立浏览器测试服务分别有 PHASE-3-CONTRACT.md、PHASE-3-IMPLEMENTATION.md 范围解释；`B/api/conversations.py:11`、`B/worker/protocol.py:13`、`B/application/event_store.py:53`、`globalmail-agent/scripts/phase3-test-server.py:28`均未接正式业务发送、模型或ERP功能。本轮未发现需作为阻塞项报告的scope creep。

## 本轮命令与原始结果

隔离：后端测试各自生成随机schema和TemporaryDirectory并注册清理（BT/test_conversations.py:31、BT/test_protocol.py:27）；额外复现复用ProtocolFixture并在finally执行doCleanups。未写15173浏览器使用的生产会话。数据库URL仅从本地设置注入环境，未打印。

```powershell
. 'globalmail-agent/scripts/local-common.ps1'
$phaseSettings=Get-LocalSettings
$env:GLOBALMAIL_TEST_DATABASE_URL=$phaseSettings.database_url
$env:PYTHONPATH=(Resolve-Path 'globalmail-agent/backend/src').Path
& 'globalmail-agent/backend/.venv/Scripts/python.exe' -m unittest discover -s globalmail-agent/backend/tests -v
```

原始汇总及警告：

```text
D:\Work_Project\globalmail-agent\globalmail-agent\backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
protocol_worker_dependency_unavailable
----------------------------------------------------------------------
Ran 31 tests in 16.968s

OK
```

`protocol_worker_dependency_unavailable` 来自预期依赖故障路径，不代表测试失败。当前31项全通过仍遗漏P3-R1，额外复现使用相同数据库/应用服务且证实问题。

前端cwd：`globalmail-agent/frontend`。

```text
pnpm exec tsx --test scripts/*.test.ts
ℹ tests 17
ℹ suites 0
ℹ pass 17
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 620.8451
```

原始编译输出摘录（省略资源大小清单）：

```text
pnpm build
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3255 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 29.39s
```

```text
& 'globalmail-agent/backend/.venv/Scripts/python.exe' -m compileall -q globalmail-agent/backend/src globalmail-agent/backend/migrations globalmail-agent/backend/tests
compileall exit=0
```

## Stage 2

**未执行：Stage 1存在HIGH。** 不输出代码质量、安全扫描或邻居页面视觉PASS。修复P3-R1后重新派发独立审查，补全实际SSE补读和UI/邻居渲染证据，再进入Stage 2。
