# Phase 14–16 正式邮件与 Agent 运行台整体独立关闭审查

日期：2026-10-09启动，2026-10-10关闭。审查者：fresh code-reviewer。采用 [.agents/skills/code-review/SKILL.md](../../.agents/skills/code-review/SKILL.md) 的两阶段规则。先重新读取源文档、实现并实测，再参考旧报告的问题输入；没有沿用旧 PASS 作为本次结论。

**关闭审查：Stage 1 PASS；Stage 2 PASS。Phase 14–16 当前正式工程契约通过；没有未关闭 HIGH/MEDIUM。原问题及本实例发现的问题均保留输入和关闭证据，末次实现、422项后端、86项前端、生产构建、CLI与本期实际截图已重新核对。**

本报告只覆盖用户已批准的正式改造工程。没有验证 Qwen 七类业务语义、实际邮件投递/ERP、全部 82 项产品 AC、自托管 Langfuse、完整删除或备份恢复，不将这些未来 Phase 11–13 范围记为本期缺陷或完成。审查没有改实现、使用 Git、操作主 Agent 独占的浏览器 tab、启动子 Agent或测试正式数据库；只新增本报告。

## 1. 依据、顺序与证据约定

- 主源：`Product-Spec.md:3`、`:5` 的 v1.18 授权；`AGENT-ARCHITECTURE.md:27` 的当前正式运行契约八条；`DEV-PLAN.md:51` 的 Phase 14–16 与其后 11–13；`docs/planning/WORKBENCH-REFACTOR-IMPLEMENTATION.md:11` 的四步交付标准。
- 完整阅读 AGENTS、code-review skill、Product-Spec、DEV-PLAN、正式实施规划、主架构当前契约及两个旧初审/修复证据报告。旧报告保持原有结论；下面每个关闭结论来自本实例重新读取和执行。
- Stage 1：逐项对照八契约、相关 REQ/AC、实际资源/界面及引导。未发现未修 HIGH 后进入 Stage 2：类型/文件职责/大小、安全、测试前提及视觉比较。
- 自有定向后端测试使用随机 PostgreSQL schema 和临时对象目录，`T/test_protocol.py:30`、`:36`、`:44`；凭据由忽略的本地配置私下读取，未打印。主 Agent 的全量422项结果由本实例读取原始日志核对，未重复执行全量后端。独立执行的29项后端与86项前端、CLI只读/输入守卫在第6节单独列明。

路径前缀：`B/` = `globalmail-agent/backend/src/globalmail_agent/`；`T/` = `globalmail-agent/backend/tests/`；`M/` = `globalmail-agent/backend/migrations/versions/`；`F/` = `globalmail-agent/frontend/src/`；`FT/` = `globalmail-agent/frontend/scripts/`。所有行号对应本次末次读取实现；没有 Git 提交基准。

## 2. Stage 1：当前正式八契约

| 条目 | 对照结果与代码证据 | 独立验证证据 |
| --- | --- | --- |
| 1. 持续人工、待接管/已主导、autonomous/human_assist；租约/工具/提交共同守卫 | 完整实现。`B/adapters/conversation_schema.py:42`、`:89` 增量字段；`B/worker/leases.py:23` 校验 lifecycle、处理权、gate、revision/epoch/generation；`B/agent/tool_gateway.py:29` 拒绝内部自主草稿/未知工具；`B/application/commit_outcome.py:64` 最终再次检查。没有恢复按钮。 | `T/test_human_assistance.py:36` 四类实际 PG/Graph 路径，首轮 persistent=true、claimed=false，后续 human_assist；`:64` 真实网关拒绝伪造写工具及自主草稿。 |
| 2. 四类首轮有源理解同租约转换；后续每封来信内部独立 run、实际人工往来；普通 HITL 恢复例外 | 完整实现。`B/agent/graph.py:118` 先验证来源后转换，`:184` 修订理解后再次转换；`B/application/human_assistance.py:28` guarded 同事务修改会话/run/cycle 权限；`B/application/conversation_base.py:68`、`:88` 内部来信入队，普通 human_wait_customer 后来信恢复；`B/agent/context.py:36`、`:49` 读取真实邮件和 completed 人工备注。 | `T/test_human_assistance.py:36` 四类首轮/人工回复/后续；`:60` 输入包含 simulated_human；`T/test_formal_boundary.py:109` 首轮遗漏商业意图，修订后下一决策已 human_assist、无自主草稿工具；`T/test_agent_human.py:16` 普通人工回复、通知竞态及下一来信恢复通过。 |
| 3. 内部只提交 human_advice/handoff，无客户 Agent 邮件、商业等待或申请；发送先撤销辅助；不覆盖个人草稿 | 完整实现。`B/application/commit_outcome.py:64`、`:79` 拒绝自主终局/商业等待；`B/application/advice_commit.py:14`、`:19` 分离建议和个人字段；`B/application/human_review.py:79` 先 invalidate，`:98` 人工发送 input_revision++；`F/composables/create-mail-workbench.ts:85`、`:288` 保留个人文本与编辑时版本，`:135` 阻止未核对提交。 | `T/test_formal_boundary.py:74` 个人 draft/note 精确保留；`:90` 模型在途时人工发送，旧 run superseded、晚到响应只诊断、artifacts=0；`FT/advice-adoption.test.ts:24` 新 review 的两种前提均保留旧草稿且 stale=true、不发 POST。 |
| 4. 结案后来信只登记；接管/发送/重试不绕结案；业务更新不生成 run/邮件 | 完整实现。`B/application/conversation_base.py:67`、`:81`、`:88` 保持 resolved、不 rebuild 开放事项、不 enqueue；`B/application/human_review.py:26`、`:72` 只允许 open；`B/worker/jobs.py:83` 重试检查生命周期；`B/application/branch_facts.py:60` 与 `B/application/waits.py:99` 仅事实/失效事件，无 enqueue；`F/views/mail-agent/index.vue:77` 结案确认后复查会话/version/path。 | `T/test_human_assistance.py:86` 结案后追加邮件、无新 run，并拒绝接管和发送；`T/test_formal_boundary.py:44` 停止旧 run 后结案不能重试；`:52` 已 resolved 的 correspondence 事项保持关闭；`:134` 实际查库存再更新使旧建议 stale=true。GUI切页拒绝结案及4会话仍open的实际快照见6.7。 |
| 5. 只读业务/知识及内部理解/草稿/接管工具；伪造商业写也拒绝；历史可查、旧执行 API 退出默认 | 完整实现。`B/agent/tool_schemas.py:85` 默认目录无商业写；`:104` 新 Schema 移除商业等待；`B/agent/tool_gateway.py:33` 未注册工具拒绝，`:110` 查询已有售后/物流，`:120` 查询历史操作；`B/main.py:75`–`:86` 未注册 simulation 执行 router；`B/api/after_sales.py:22`、`:26` 仅 GET。 | `T/test_human_assistance.py:64` 对 create/cancel/eligibility 三个伪造工具逐个拒绝，operations=0、Agent 出站=[]；普通有据回复 `:99` 仍只发送一次。旧私有 ledger 的存在不表示默认权限仍可写。 |
| 6. 完整真实逐次请求/Schema/参数/返回；图片受控引用、依赖撤销/作用域；reasoning 空态；预算不放宽 | 完整实现。`B/agent/graph.py:45` 每 attempt 预留，`:71` finally 记返回/失败；`B/observability/model_records.py:11` 不截断文本，`:39` 保存响应依赖，`:56` 区分历史未采集/返回/失败/未启用/未返回；`B/adapters/model_provider.py:19` SDK retry=0，`:43` 原字段；`B/agent/budget.py:12`、`:48`、`:58`、`:108` 原预算；`F/components/agent-runtime/RequestView.vue:8`、`:29`、`:35` 完整请求/Schema，`NodeDetail.vue:26` 供应商字段与空态。 | `T/test_model_records.py:8` 逐次精确比 messages/schema/tools/reasoning；`:24` 两次超时不同 failed receipts、usage=null；`T/test_formal_boundary.py:27` 异 workspace GET 均404、三种跨域对象 FK 拒绝；`:181` 实际图片引用无 base64、撤回后410；独立预算/鉴权/Schema/安全六项见第6节。 |
| 7. 建议绑定 run/input 过期；采用只本地复制，确认后服务及本地文本重验；人工发送 | 完整实现。`B/application/advice_commit.py:16` run/revision/queried_at；`B/application/conversation_advice.py:33` lifecycle/input/最新 run；`F/composables/use-conversation-advice.ts:29` 捕获 run/input/个人正文，`:36` 重新读取服务，`:37` 拒绝本地编辑变化，`:38` 拒绝服务失败/版本/会话变化，`:40` 仅 setHuman/acknowledge，无发送；`StaffReply.vue:15` 明确人工发送。 | `FT/advice-adoption.test.ts:42` 初始空/已有正文，确认/网络期间编辑均保留；`:60` stale 或网络失败拒绝；`:74` 合法采用 commands=0；`T/test_formal_boundary.py:134` 业务版本更新过期。当前实际GUI取消/确认/采用不发送观测见6.7。 |
| 8. 正式真实 API/执行，不复制演示节点；Mock 来源明确；替身测试仅工程证据 | 完整实现。`F/components/agent-runtime/run-presentation.ts:20`、`:31`、`:36` 节点只来自实际模型/工具/artifact；`F/views/agent-runs/index.vue:41` 未读记录不写零，`:42` 任一 token null 标仅已知用量，`:53` 不补造节点；`F/components/mail-agent/BusinessObservation.vue:3`、`:4` 明确模拟/来源/时间；`B/application/run_records.py:33` 和 advice GET 无排队；`F/router/modules/mail-agent.ts:8` 正式四入口，无业务中心/实验室。 | 本期相关views/composables/runtime源码及最终dist没有preview依赖，直接扫描无命中；`T/test_model_records.py:16`实际执行与账本逐项相等。本期实际API/GUI见6.7；模型是ScriptedModel，不是七类Qwen语义证明。全前端86项含既有预览测试，不能据其数量声称正式语义业务验收。 |

### 2.1 相关界面、可靠性与迁移逐项

| 要求 | 结论与证据 |
| --- | --- |
| 邮件仅正常往来/人工通信，内部建议独立 | 完整实现：`F/views/mail-agent/index.vue:19` MessageTimeline、`:20` StaffReply、`:25` 建议抽屉；`AgentAdviceDrawer.vue:3` 内部提示、`:19` 采用；没有请求/日志节点插入邮件气泡。`B/application/advice_commit.py:18` 独立对象。 |
| 会话→客户轮次→重试尝试→实际节点 | 完整实现：`F/components/agent-runtime/run-presentation.ts:52` cycle 分组保留 attempts；`F/views/agent-runs/index.vue:28`、`:34`、`:52`；`B/application/conversation_queries.py:89` 运行带 trigger_message_id。 |
| 默认轮固定、历史新轮仅提示，侧栏跨页恢复 run/node | 完整实现：`F/composables/use-agent-console.ts:58` 默认写入固定 run_id；`:49` 保存阅读位置，`:60` 仅恢复会话内存在的 run；`F/views/agent-runs/index.vue:48` 仅历史提示；`F/composables/agent-reading-state.ts:1` 会话映射。本期截图与主Agent GUI观测见第5/6节。 |
| 触发来信深链接、邮件阅读位置及个人草稿跨页 | 完整实现：`F/composables/use-agent-console.ts:46` message_id；`F/views/mail-agent/index.vue:50`、`:53`、`:59` 定位与阅读位置，`:71` 离页保存；`F/composables/useMailWorkbench.ts:4` 共享正式状态，`create-mail-workbench.ts:25` 客户分别存输入；读取/失败不会清空输入。 |
| 真 loading/empty/error、晚到 GET 不覆盖 | 完整实现：`F/composables/create-mail-workbench.ts:63` generation/id 门禁；`use-agent-console.ts:21` 记录读取与错误清空，`:15`、`:26` 显式外会话run_id错误且不回落最新轮；`useConversationEvents.ts:42`、`:49` 切会话/停用断开；`F/views/agent-runs/index.vue:14`、`:51`、`:53` 真实状态；86项及初审原输入重新执行，原F-04为未读取→读取中/不可用、任一未知用量→仅已知。 |
| 旧页签/搜索入口清理，无测试 UI 死引导 | 完整实现：`F/router/local-tabs.ts:1` 正式四名称白名单；`F/router/guards/beforeEach.ts:19` 过滤旧页签/搜索；`FT/local-tabs.test.ts:1` 相关回归通过；`MailConversationList.vue:5` 搜索明确只本页。正式邮件无新建样例、注入来信、推进历史、重置测试按钮。CLI/API交付见6.6。 |
| 可用的测试入口/正确能力文案 | 完整实现：`globalmail-agent/scripts/mail-test-api.py:29`提供列表/创建/读取/来信/逐封历史/事实更新，`:38`、`:72`允许固定原expected-version、`:47`复用key；`start-workbench-test.ps1:12`启动Phase16随机schema；`phase3-test-server.py:112`生成无凭据session、`:122`清理自有进程和schema/对象。`F/components/business/runtime-status.vue:48`说明只读/持续人工/记录，`F/views/knowledge/index.vue:18`说明实际发布规则；无死引导。 |
| 增量0010保留存量、completed review/human_wait_customer；旧 active/checkpoint/图片安全 interrupt | 完整实现：`M/0010_human_assistance.py:16` 仅增列/FK/check；`:46` 商业历史 backfill，`:48` 保留 human_wait_customer；`:55` 在途图片失败/解绑，`:62` run 中断且 checkpoint_writable=false，`:67` slot fence++；没有删旧表/正文。 |
| 旧 schema 冻结、隔离迁移正确 | 完整实现：`T/test_human_assistance_migration.py:47` 真实0009→0010，`:109` 原字段逐个精确比较，`:123` 图片字节不变；`:132` completed人工历史无假open review；`M/0008_after_sales_ledger.py:108` current_schema 目标存在性检查。独立23项包含两个迁移场景全通过。 |

### 2.2 全部 REQ 及相关 AC 的本期归属

下表明确每个 REQ；“本期增量完成”表示本次工程契约，不勾选整产品 AC。源 Spec 的未改旧交易/场景控制叙述由顶部 v1.18 授权覆盖，不能拿历史段落反向授予权限。

| REQ | 本期检查/AC | 证据与边界 |
| --- | --- | --- |
| 001 客户归组/导入 | 客户选择/输入隔离；AC001–003保留原归组/去重能力 | `B/application/conversation_base.py:64` 原会话追加，`F/composables/create-mail-workbench.ts:25` 客户输入隔离；原导入去重由全量工程回归保留，不宣称重验生产跨源稳定身份。 |
| 002 历史回放 | AC004–006、027：当前前缀/原历史与对照隔离保留 | `B/agent/context.py:36`、`:55` 不加入历史比较/最终状态；`B/application/conversation_queries.py:68` 当前可见前缀；`commit_outcome.py:99` 独立对照结果；逐封推进改脚本/API，历史资料可用性和模型语义不是本轮整体重验。 |
| 003 模拟自动回复 | AC007–009：普通回复一次性保留，商业不得出站 | `B/application/commit_outcome.py:87`、`:95`；`T/test_human_assistance.py:99` 正常回复一次，`:36` 四类无Agent出站；`F/components/mail-agent/MessageTimeline.vue:64` 模拟标签。没有真实发送适配器。 |
| 004 订单定位 | AC010–012：只读/有源/身份服务不放宽 | `B/agent/tool_gateway.py:101` 原文候选限制，`:89` 同scope订单行；`BusinessObservation.vue:4` 来源与快照；具体多商品/语言判断留业务质量专项。 |
| 005 知识/RAG/维护 | AC013–016、055–064的既有查询/维护保留；AC060完整删除未开始 | `F/router/modules/mail-agent.ts:21` 知识入口；`B/agent/tool_gateway.py:132` 精确SKU/发布/模式限制；知识全量回归由主 Agent结果补入，不用本报告关闭全部知识AC。 |
| 006 决策/记忆 | AC017–019：实际上下文/输入、权限边界；语义待验 | `B/agent/context.py:36`、`:49` 人工历史，`graph.py:118` 来源验证，`tool_gateway.py:29` 权限；普通/商业路径定向测试通过；失败步骤是否正确用自然语言处理留Phase13。 |
| 007 HITL/人工结案 | AC020–023本期相关分支工程完成 | 八契约1–4/7；`T/test_agent_human.py:16` 普通恢复，四类持续人工与结案永久测试；F-01/F-02旧反例均重跑。当前GUI观测见6.7，并与生产confirm/adopt代码和永久反例核对。 |
| 008 可靠性/记录 | AC024–026、040：终局/权限/独立记录/预算工程完成 | 八契约1/3/4/5/6；独立29个后端永久测试，23条包含晚到诊断无提交/Scope/图片撤回/迁移，6条包含风险、鉴权、Schema及重试预算。 |
| 009 邮件/独立运行台 | AC027、028、032：正式增量工程完成 | 2.1逐项已覆盖；当前正式1440截图与批准预览源CSS匹配，1280×720明暗邮件/运行、建议及当前知识基准已由本实例打开比较，见第5节。 |
| 010 清理/评测 | AC029–031：本轮无测试UI、无虚假评测准确率；完整删除未来 | `F/router/modules/mail-agent.ts:8`，未来范围 `DEV-PLAN.md:261`、`:276`；旧生命周期服务保留，不由本报告签完整删除/恢复。 |
| 011 四类只读/持续人工 | AC033–044、053–054工程边界本期完成，七类语义待验 | AC034/035/036/037四种首轮→持续人工逐个测；039/041既有多目标记录只读；040网关/终局拒绝；042业务更新不唤起；043后续内部独立run；053真实库存变化过期；044历史只对照；054不由登记/客户声明生成执行事实。`tool_gateway.py:110`、`:117`、`context.py:93`、八契约2–5/7。 |
| 012 理解/实体 | AC045–048：有源schema、修订商业权限及解析失败停止工程完成 | `B/agent/graph.py:94`、`:118`、`:184`；`T/test_formal_boundary.py:109` 有源修订后权限变更；独立Schema故障用例通过。七类多诉求语义质量留Phase13。 |
| 013 Langfuse/观测 | AC049–052：本地逐次记录/去重工程完成；Langfuse未来11 | `B/observability/model_records.py:11`、`budget.py:82`、`worker/agent_runner.py:44` local_only；`:19` 新run独立本地trace；自托管/导出/网络降级 AC049–051不能据此关闭。 |
| 014 图片 | AC065–082：原图片能力保留、记录受控引用/撤回/来源/预算/风险本期核对 | `T/test_formal_boundary.py:181` 引用与撤回，`T/test_vision_graph.py:69` 风险直接HITL不增加第二模型；`F/views/mail-agent/index.vue:26` 证据抽屉保留；065–069/071/079语义质量、078彻底清理/恢复、082冻结真实模型专项仍未完成。 |

## 3. 本实例发现与关闭

| 编号/级别 | 实际输入/差异 | 修复后独立复查 |
| --- | --- | --- |
| R-01 / MEDIUM，已关闭 | `FT/advice-adoption.test.ts:24` 的 previousReview=false：等待客户、旧个人正文、新review/input3。UI humanStale=true禁用，但直接调用completeHuman仍发一次command，`:37` writes期望0实为1；本实例第一次定向27项26通过/1失败。后端旧revision仍拒绝，未判授权越界HIGH。 | `F/composables/create-mail-workbench.ts:135` 共用command入口拒绝 stale 的 human-replies和reviewVersion PATCH；重新从Stage1核对并独立全量pnpm test86/86、0fail，旧文本保留/核对不自动推进。 |
| R-02 / MEDIUM，已关闭 | 首次计数 `F/composables/create-mail-workbench.ts` 302物理行，超过skill≤300门槛。 | 主Agent压缩后本实例重新计数297，最大相关正式前端源文件297、后端graph269。职责/行为未因此删除。 |
| R-03 / LOW，已关闭 | `B/agent/prompts/validation.md:9` 原句仍允许有条件no-body商业等待，和decision/服务端禁令冲突。服务端依然阻断，不是写权限缺陷。 | 原句删除并明确四类human ownership/internal advice、禁止business waits/自主客户回复。现`:9`与`decision.md:7`、`commit_outcome.py:79`一致；风险/普通恢复/预算6项在新进程通过。 |

旧前端初审F-01/F-02：本次分别跟踪编辑时revision绑定、新review保留文本/旧核对版，以及采用前后local reply/server version/network错误检查，并运行上述永久输入；未复现。F-03：默认run固定/离页记忆代码及本期GUI观测已核对。F-04：读取中/不可用及input或output任一null提示代码匹配。旧后端五项：个人草稿、库存更新过期、结案事项、旧在途图片、completed人审迁移均由本实例真实PG重新执行通过。

主Agent末次自检还修正显式异会话run_id的回落及旧能力文案。本实例重新从Stage1读取`:15`–`:27`与相应界面、CLI和提示文本，查看实际错误截图并核对末次测试/build；未引入新的未关闭问题。

## 4. Stage 2：代码、安全及测试真实性

| 维度 | 结果及证据 |
| --- | --- |
| 命名/结构/职责/≤300 | 当前检查范围无超300行源文件；正式前端最大`create-mail-workbench.ts`297，后端`graph.py`269；末次触及knowledge index265、runtime-status71、console85、CLI92、启动器19、隔离server142。`human_assistance.py:28`权限、`advice_commit.py:10`提交、`model_records.py:11`观测对象分别独立。API DTO/schema、frontend contract和unknown解析保持类型约束。 |
| 无any | 对正式邮件/运行页、runtime组件、相关邮件组件/composables/API/路由扫描TS `\bany\b`无命中，rg exit1。Python内置any和prompt英语any不当作类型逃逸。 |
| 错误与版本 | `create-mail-workbench.ts:63`、`:135`读写门禁；`use-conversation-advice.ts:36`完整复查；`use-agent-console.ts:21`清空失败记录，`:15`显式错误run不回落；`agent/graph.py:71`失败也记录；`model_records.py:29`晚到不执行，`:33`撤回仍阻断；`human_review.py:79`同事务废除旧权限。 |
| 安全扫描 | 本次相关正式frontend/agent/worker/新增advice/records/modelprovider源扫描eval、危险HTML/v-html、VITE密钥前缀、硬编码password/key前缀及外部绝对路径，无命中、rg exit1。`adapters/model_provider.py:19`凭据只注入SDK，不入provider_options；图片base64仅网络传输（`:33`），持久记录是授权引用（`model_records.py:15`）。不以grep单独证明安全，另有scope FK/撤回/伪造写工具实际探针。 |
| SQL/模型输入 | 没有本增量接受模型SQL/路径/命令的接口；`tool_gateway.py:33`固定目录、`:43`Pydantic；0010静态SQL无外部插值。测试CREATE/DROP随机schema是测试隔离基础设施，`T/test_protocol.py:32`、`:36`，不混同业务模型输入。 |
| 测试可达性 | 新review=null属于真实GET路径：`conversation_queries.py:74`只取open review，人工发送completed后下一来信创建新review；`StaffReply.vue:7`等待客户时可以编辑。采用测试直接运行生产composable并延迟真实代码的await、spy命令，不只断言纯函数。PG测试使用真正服务/租约/Graph/BodyWriter/FK；模型输出可控，不用替身证明语言质量。 |
| 迁移测试前提 | `T/test_human_assistance_migration.py:47`先真实0009再反射老表插入；`:109`精确比较原字段、`:123`原图片字节。不用0010 ORM列向老schema写入不可达输入。真实老completed review无open review前提覆盖。vector反射SAWarning保留，测试未读写该向量列，迁移/比较未skip。 |
| Spec漂移 | 新advice GET、模型对象字段、0010和测试facts API均在正式规划；旧simulation执行router不默认注册。仍保留preview独立模式和旧私有ledger作为历史/测试，不是新业务页面。当前正式源无preview依赖；末次dist扫描`ui-preview/business-scope-final/preview-workbench/scriptedModel`无命中、rg exit1。 |
| 测试限制 | 生命周期warning来自既有knowledge单元测试无组件实例的调用，原输出保留。`useAgentConsole`历史导航/KeepAlive、结案确认切页主要采用主Agent当前真实GUI观测，并由本实例读取生产守卫、实际截图及关键采用永久反例；86项里包含预览纯状态测试，不能将其当真实执行记录或Qwen验证。 |

## 5. 视觉数值与实际截图比较

本实例已打开并查看：本期`artifacts/phase16/formal-agent-desktop.png`、批准`tmp/ui-preview/business-scope-final-agent.jpg`/`business-scope-final-mail.jpg`、旧邻居`artifacts/phase8/review7/neighbor-knowledge-real.png`，以及本期1280×720的`formal-agent-1280-{light,dark}.png`、`formal-mail-1280-{light,dark}.png`、`formal-advice-1280.png`、`formal-knowledge-baseline.png`和`formal-run-scope-error.png`。正式图展示实际API账本的两轮/模型/工具/完整system输入；外壳、卡片边线、主色、主题变量和输入/按钮体系与批准布局和当前知识基准一致。截图中模型名称只是配置/账本字段，不能证明这些工程脚本完成真实Qwen业务质量验收。

| 设计数值 | 批准预览源 | 正式源 | 结论 |
| --- | --- | --- | --- |
| 头像44×44，10px圆角，主题浅底/主色 | `F/views/ui-preview/agent/index.vue:151` | `F/views/agent-runs/index.vue:72` | 完全匹配 |
| 运行概要间距10px/16px，12px字号 | 预览同文件`:162` | 正式`:73` | 完全匹配 |
| 四列轮卡，10px gap，12px padding，8px圆角；1050断点双列 | `F/views/ui-preview/components/ConversationRounds.vue:44`、`:49`、`:69` | 正式`:74`、`:75`、`:78` | 桌面完全匹配 |
| 时间线/详情min330px:.9fr、min400px:1.15fr，16px gap，min420px高度 | 预览agent`:170` | 正式`:77` | 完全匹配 |
| ≤1050px单列，详情min550px | 预览agent`:176` | 正式`:78` | 完全匹配 |
| 提示词/输出换行，JSON按需展开，不横向撑开 | `RequestView.vue:19`、`:35`、`:80`；`DataBlock.vue:51` | 当前正式截图可见原完整system文本在详情内阅读；raw JSON保持完整 | 代码与现有桌面渲染匹配 |

1280×720明暗图的会话/轮卡/按钮及执行双栏均完整位于内容区，无可见全局横溢出；邮件往来与个人输入分区、建议抽屉独立固定底部采用按钮可见。主Agent观测document.scrollWidth=1280，与图片和代码相符。纵向内容按批准容器可滚动，并非全部节点必须同时塞进720px。本期当前知识基准与两新页面使用相同Art导航、20px卡片内边距、按钮边线/主色/主题体系；旧商业能力/“下一阶段接入”文案已修正。异会话run图明确显示错误且无另一个客户的节点。

本实例还查看了`formal-agent-800.png`：左侧菜单处于覆盖展开态，这张图不作为窄屏菜单关闭后完整布局通过证据。没有执行键盘可达性或测量文字对比度，不将其写为通过。本轮授权为既有本机Art外壳及1280桌面交互，未据800菜单展开态新增移动端交付范围。

## 6. 本实例实测、编译原始输出

### 6.1 后端独立定向23项

命令：

```text
globalmail-agent/backend/.venv/Scripts/python.exe tmp/run-refactor-tests.py test_human_assistance test_model_records test_formal_boundary test_human_assistance_migration test_model_provider
```

原始汇总与关键断言输出（exit0；模型为替身，PG及服务真实）：

```text
Ran 23 tests in 54.547s
OK
PROBE staff_draft {'draft': 'Staff personal wording', 'note': 'Staff verified note'}
PROBE closed_issues {'lifecycle': 'resolved', 'issue_states': {'correspondence': 'resolved'}}
PROBE late_response {'result': {'error_code': 'lease_expired'}, 'run_status': 'superseded', 'call_status': 'completed', 'artifacts': 0}
PROBE scopes {'foreign_workspace_read': '404', 'foreign_object_updates': '3 FK rejections'}
PROBE inventory_change {'event_status': 'facts_updated', 'before_revision': 2, 'after_revision': 3, 'advice_stale': True, 'new_on_hand': 7}
PROBE revised_intent {'persistent_human': True, 'execution_mode': 'human_assist', 'outcome': 'handoff'}
PROBE image_records {'image_transport': 'authorized_reference', 'revoked_read': 'image_content_revoked'}
PROBE migration_0010 {'persistent_human': True, 'run_status': 'interrupted', 'slot_fence': 8, 'image_status': 'failed', 'conversation_state': 'failed', 'objects_preserved': 2}
PROBE migration_0010 {'persistent_human': True, 'run_status': 'handed_off', 'slot_fence': 8, 'image_status': 'understood', 'conversation_state': 'waiting_customer', 'objects_preserved': 3}
PROBE migrated_staff {'processing_owner': 'human_wait_customer', 'human_claimed': True, 'open_review': False}
SUMMARY 23 failures 0 errors 0 skipped 0
```

迁移反射原警告（不是skip）：

```text
SAWarning: Did not recognize type 'public.vector' of column 'vector'
SAWarning: Did not recognize type 'public.vector' of column 'probe_vector'
```

### 6.2 原保护链独立风险/预算/普通恢复6项

命令参数：`test_agent_human`、`test_agent_faults.AgentFaultTests.test_valid_safety_understanding_checkpoint_failure_handoffs_at_last_request_budget`、`.test_retry_retains_cycle_consumption_and_cannot_buy_seventh_model_request`、`.test_authentication_failure_is_one_request_and_preserves_unknown_cost`、`.test_schema_failure_repair_uses_two_requests_then_stops_without_default_business`、`test_vision_graph.VisionGraphTests.test_visual_risk_goes_directly_to_atomic_hitl_with_no_second_model`，同一私有配置/隔离launcher。

```text
Ran 6 tests in 17.147s
OK
SUMMARY 6 failures 0 errors 0 skipped 0
```

### 6.3 前端独立回归与类型编译

修复前本实例定向原结果：

```text
ℹ tests 27
ℹ pass 26
ℹ fail 1
AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
1 !== 0
at TestContext.<anonymous> (.../scripts/advice-adoption.test.ts:37:39)
```

修复后工作目录`globalmail-agent/frontend`，独立`pnpm test`原始汇总，exit0：

```text
$ tsx --test scripts/*.test.ts
✔ 新review保留已编辑个人草稿但不能自动确认最新来信
✔ 采用等待服务器复查时再次输入，不能被Agent草稿覆盖
✔ 服务器判定过期或读取失败时拒绝采用，保持个人文本
✔ 合法采用只更新客服输入，不调用发送接口
ℹ tests 86
ℹ suites 0
ℹ pass 86
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3674.3251
```

既有knowledge测试原警告：`[Vue warn]: onMounted/onUnmounted is called when there is no active component instance ...`。沒有因此跳过用例或将警告说成零。

```text
pnpm exec vue-tsc --noEmit
标准输出：空
退出码：0
```

### 6.4 Python编译/依赖

```text
python -m compileall -q globalmail-agent/backend/src globalmail-agent/backend/migrations
COMPILE_EXIT=0
uv pip check --python globalmail-agent/backend/.venv/Scripts/python.exe
Using Python 3.12.10 environment at: globalmail-agent\backend\.venv
Checked 58 packages in 14ms
All installed packages are compatible
```

### 6.5 主 Agent 全量/生产构建/当前GUI补证

本实例读取完整原始汇总并核对永久归档：[后端全量](artifacts/phase16/backend-full-tests.log)、[提示词末次回归](artifacts/phase16/backend-prompt-regression.log)、[末次前端测试](artifacts/phase16/frontend-tests.log)、[末次生产构建](artifacts/phase16/frontend-build.log)。这四项由主Agent执行，区别于6.1–6.4本实例执行。

```text
Ran 422 tests in 1173.482s
OK
SUMMARY 422 failures 0 errors 0 skipped 0

Ran 21 tests in 81.703s
OK
SUMMARY 21 failures 0 errors 0 skipped 0

ℹ tests 86
ℹ pass 86
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3277.9707

$ vue-tsc --noEmit && vite build
vite v7.1.7 building for production...
✓ 3352 modules transformed.
✓ built in 25.66s
```

本实例对末次dist重新扫描`ui-preview|business-scope-final|preview-workbench|scriptedModel`无命中（rg exit1）；不存在正式bundle引入批准预览fixtures/control的证据。上述用例不是模型网络语义质量测试。迁移反射public.vector/probe_vector的既有SAWarning保留，0 skipped；本次比较的旧邮件/运行/人审/图片没有依赖这些反射列写入。

### 6.6 CLI/API独立复读与探针

末次新增源码逐行复读：`globalmail-agent/scripts/mail-test-api.py:13`检查session schema格式及本机HTTP地址，`:47`写请求key，`:57`编码路径ID，`:65`按实际嵌套conversation提取show，`:72`固定重试版本；`start-workbench-test.ps1:8`、`:18`保存/恢复进程环境；`phase3-test-server.py:53`随机schema、`:70`迁移、`:76`子进程私有环境、`:87`移除前端凭据、`:112`无凭据manifest、`:122`清理自有进程、`:134`清理schema、`:136`清理对象目录。schema由UUID hex生成，清理目标不来自CLI用户字符串。

本实例只读调用当时存活的18186隔离API，输出确有3客户消息、2 cancelled旧run及1 queued新run（ManualAgent），row_version=4/input_revision=3；没有把未执行的queued当模型完成。独立session函数探针与源码语法验证：

```text
CLI_SESSION_GUARD 1 accepted / 5 rejected; no HTTP mutations
CLI_PYTHON_COMPILE 2 passed
CLI_POWERSHELL_PARSE 1 passed
FINAL_NEW_SECURITY_SCAN_EXIT=1
```

五种拒绝输入：schema=public、HTTPS、外部hostname、URL带凭据、URL query。允许格式来自隔离启动器生成的session文件；这是本机测试约束，不声称session文件格式能认证任意人为伪造的服务器。没有向正式服务发送请求。

主Agent实际CLI结果另核对`tmp/refactor-api-cli-{created,show-3,mail-repeat-1,mail-repeat-2,error}.log`及[测试说明](WORKBENCH-API-TESTING.md)：同正文/key/expected-version两次返回同message/run/job/cycle、version=4；故障输出`{"status":"error","http_status":409}`并退出1。最初show KeyError失败日志保留；当前脚本已按嵌套conversation读取，经本实例live show重新验证。facts沿用Pydantic BranchFact和原幂等/版本服务，只失效旧建议；不扩展商业执行权限。

### 6.7 本期GUI/API原始观测与交付边界

本实例读取[GUI观测](artifacts/phase16/gui-observations.json)、[实际API快照](artifacts/phase16/isolated-api-outcomes.json)及[本期验证](FORMAL-WORKBENCH-REFACTOR-VALIDATION.md)，逐项与实现、永久测试和本实例查看的截图比对。GUI由主Agent独占操作，本实例没有重播其tab；观测环境是FastAPI18184/Vite15176、独立schema/对象，真实Graph配ScriptedModel。

| 原始观测 | 与实现/独立断言核对 |
| --- | --- |
| 1440×1000 scrollWidth=1440；1280×720 light/dark scrollWidth=1280 | 8张本期截图已打开，当前知识基准/新页面外壳与第5节数值一致；不签800菜单关闭后的移动细节。 |
| 退款取消采用保留输入、确认采用仅复制、客服手动发送；新来信第二轮内部辅助 | API退款senders精确为customer/simulated_human/customer；2run均human_assist，handoff与human_advice，无Agent邮件；operations/executions/shipments/returns均空。与6.1、6.3生产composable输入反例一致。 |
| 退货/换货/补件首轮 | 3会话各1customer/1handed_off human_assist，persistent_human=true、owner=human_review，执行数组空；没有编造客户Agent回复。 |
| 历史run/工具step跨触发来信导航恢复，新轮仅提示；触发第3封定位 | `use-agent-console.ts:49`、`:58`和mail深链/阅读存储；截图历史提示明确可见，默认run固定且不被SSE刷新改query。 |
| 结案确认后切客户/页拒绝，4会话仍open | `F/views/mail-agent/index.vue:77`复查path/id/version，实际4API快照lifecycle=open；永久服务结案后来信/重试/发送保护另由6.1验证。 |
| 另客户run_id深链接显示错误，选合法轮恢复 | 本期scope-error截图显示错误且无节点；`use-agent-console.ts:15`只在当前会话find，`:26`错误，`:29`合法读取清错，未回落另一run。 |
| provider缺reasoning明确提示，Mock来源可查 | `NodeDetail.vue:26`、`model_records.py:56`明确供应商/历史空态，建议截图source_kind=synthetic_scenario/时间/版本标识。 |

**正式0009→0010升级、升级后的旧表/对象/设置核对、正式服务ready和隔离服务清理仍由主Agent在本审查通过后执行。本报告签工程代码审查通过，没有提前签本机部署完成或备份恢复演练通过。** Phase11–13及整产品82项AC仍保持原状态。
