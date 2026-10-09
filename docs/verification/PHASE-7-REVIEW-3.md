# Phase 7 第三轮审查（进行中，非完成报告）

日期：2026-10-08 至 2026-10-09。审查者：主 Agent 派发的 code-reviewer。工具返回 `agent thread limit reached` 后，用户明确批准“允许本次复用审查实例”，本轮复用原审查实例，**不是 fresh**。重新读取原文及最新源码，从 Stage 1 开始；不信任上轮通过声明。本轮没有修改产品、提交或派发子 Agent。旧第二轮 [FAIL 报告](PHASE-7-REVIEW-FINAL.md) 和原始反例未改写。

**当前 202431 版本 Stage 1 FAIL（H-12/H-13），Stage 2 未执行；后修闭环仍进行中。** 德文真实核心PASS，但下一条件退款遗漏未来选择、无据商品类型实际出站，后三边界未调用。原 `180804`、`181730` 等真实FAIL及`184615` P7-03失败均保留；P7-02已有实际核验与真实提交PASS，191114 P7-03实际人审PASS。历史P7-04进行时升级实际出站（H-08）与来源晚拒0出站（H-09）均保留；194850 fresh04冻结核心目标PASS，另列M-01来源精度限制。195403德文格式/额度FAIL及200822 H-11无据原因实际出站FAIL均保持；202431新全文德文有据补问、1真实出站通过本独立gate。未将 completed、零错误拒发或工程测试折算为真实业务通过，本文件最终结论须待后修复审及Stage证据补齐。

最新2026-10-09进度：用户已授权仅validation 4k总输出/最多60秒的容量候选，text/5工程前检及独立18项通过；074740唯一negative全文门仍FAIL，条件遗漏识别和声明商品来源拒绝有局部进展，其他claim来源与精确引用仍失败。H-12/H-13尚未关闭，positive和新06–09未放行，Graph未接parsed表示；详见第7节逐版本证据，不以新工程PASS覆盖旧真实FAIL。

## 1. 依据、范围与快照

完整重读 AGENTS.md、`.agents/skills/code-review/SKILL.md`、`.codex/agents/code-reviewer.toml`、Product-Spec.md、AGENT-ARCHITECTURE.md、DEV-PLAN Phase 7、docs/README.md、PHASE-7-IMPLEMENTATION、SESSION-HANDOFF 顶部；重新读初审与第二轮原始失败。没有 Design-Brief/设计稿，按 Art Design Pro 和现有页面基线验 UI。

本期为 REQ-002/003/004/005/006/007/008/009/012/013、22 项指定 AC，以及 FT-01/02/04/05/08/09/10。售后写、正式图片、实际 Langfuse 服务和完整删除分别留 Phase 9/8/11/12；没有将这些后期能力算作 Phase 7 缺失，也没有宣布首版或 82 AC 整体验收通过。

HEAD `dd95be236b6d327c2e10adbadc10053e28107f37`，包含未提交改动。已读完整 tracked diff 和新增 backend agent/adapters/application/worker/0006、前端 API/panels/composables、测试/脚本/eval；依赖锁的新增固定版本及 SDK 实际版本也已核对。前缀：**B**=`globalmail-agent/backend/src/globalmail_agent/`；**T**=`globalmail-agent/backend/tests/`；**F**=`globalmail-agent/frontend/src/`。下列路径及行号按该前缀展开，对应本轮读取快照。

快照证据：[首次 SHA 清单](artifacts/phase7/review-3-snapshot.json)、[最新专项测试开始 SHA](artifacts/phase7/review-3-latest-tests-snapshot.json)、[当前 SHA/HEAD](artifacts/phase7/review-3-current-snapshot.json)、[tracked diff](artifacts/phase7/review-3-tracked-diff.txt)。首次 84 项运行期间 provider 采样及 eval helpers 改动，日志明确记录；最新 86 项期间只有 `prompts/validation.md` 改动。工程协议测试不评价该提示的真实语义，真实请求使用其各自 manifest。没有混算版本。

## 2. 历史 HIGH 的独立复核

| 项目 | 最新实现与独立证据 | 本轮判断 |
|---|---|---|
| 初审 H-01：全文依据/模型自报 kind 授权 | B`agent/outcome_validation.py:20` 对全部非空白正文字符确定性覆盖；B`agent/graph.py:161` 在原预算内全文语义核验；B`application/commit_outcome.py:36` 必须精确匹配 normalized draft hash 并重验来源/业务摘要。T`test_agent_validation.py:14/94/110/126` 覆盖全文遗漏、clarification 伪退款/危险拆机、未审和改后正文。 | 程序缺口关闭。语义核验是模型判断，**不是自然语言正确性的形式证明**；本轮真实 false-positive 仍阻断业务验收，见第 7 节。 |
| 初审 H-02：early wake/后继/版本消费 | B`application/waits.py:12` scoped Operation 锁与注册早到版本补查；`:41` Conversation 锁、版本、input/row 递增、旧任务 supersede/唯一后继；`:92` 只消费 ctx 实际 observed version；B`application/commit_outcome.py:117` early 情况提交持久后继而不发旧回复。T`test_agent_waits.py:32/60/73/106/144/155` 共 8 项实跑。 | 本期协议关闭。后继排队不是消费；比已观察版本更新的 wake 保留。完整模拟事件推进留 Phase 10。 |
| 初审 H-03：active risk 持久与人工门 | B`application/risk_records.py:24` 持久 active；B`application/commit_outcome.py:95` 同事务写风险、人审、撤自动权；B`worker/agent_runner.py:70` load 风险先于 configured/model；B`application/human_review.py:65/76` 当前 row/input 门及显式决定的当前非空 note。T`test_agent_risks.py:26/54`、T`test_agent_faults.py:178`。 | 协议关闭。普通人工回复不清，模型不能清；模型未配置/检查点故障也不能把 active 风险丢掉。 |
| 第二轮 H-03：旧来源换 quote 复活 | B`agent/understanding.py:52` 先核对原文精确 quote，`:70` 再按 kind+message_id 集匹配已 resolved/corrected 来源。审查者另外在真实 PG 执行两种人工决定：旧同 message_id 换 quote 均正常回复（3 模型/active0/出站1）；混合旧来源和真正新危险来源均接管（1 模型/active1/新增出站0）。 | **本反例关闭**，并证明没有用旧来源过滤遮住新危险。[独立四反例输出](artifacts/phase7/review-3-risk-repro.txt)。旧 FAIL 仍真实有效于旧源码。 |
| AC-047 理解修订 | B`application/understanding_revisions.py:25/31` initial/current；`:39` 限成功、scoped、同 run 的业务 command 原文；`:57/59/64` CAS 和同键回凭证；`:75/79` 精确 quote 与客户同意来源；`:86` 保留 risk；`:103/113` 修订和 command receipt 同事务；`:108` 清旧 draft 授权。T`test_agent_revisions.py:36/75/98/119/137/157/173/194`。 | 9 项独立通过；修订改变候选，不写交易、不清风险。F`components/mail-agent/UnderstandingPanel.vue:64` 显示初始与修订及来源，B`application/run_records.py:44/55` 返回最新理解与历史。 |

## 3. REQ 的本期实现归属

“完整”仅指表内明确列出的本期责任；跨 Phase 的整项需求仍按后期门槛验收。模型业务质量未通过的条目保留“部分”。

| REQ / 原文 | 本期责任与代码证据 | 状态/缺口 |
|---|---|---|
| 002，Spec:272 | B`agent/context.py:36/55` 当前历史前缀、历史截点、真实历史正文；排除 AI/人工对照、未来和旧候选；B`application/commit_outcome.py:134` 保存独立 comparison，不做模拟交易。T`test_agent_outcomes.py:131` 真实 PG 哨兵。 | 本期完整；完整历史业务写本版不开放。 |
| 003，Spec:287 | B`worker/agent_runner.py:49/80` 真实 Graph；B`application/commit_outcome.py:124/142` 原子出站与唯一凭证；已有来信服务触发任务。 | 部分：自动路径及去重已实现；真实连续闭环未达标（第 7 节）。 |
| 004，Spec:302 | B`agent/tool_gateway.py:90/108` 精确订单、scoped 行/operation；服务构建身份，模型不能设置身份/分支；T`test_agent_tools.py` 多商品/外客户反例。实际 P7-02 成功查单。 | 部分：技术定位完整，真实多商品澄清未完成。 |
| 005，Spec:319 | B`agent/tool_gateway.py:120/133/150` 当前 SKU/发布范围真实 RAG、先登记全部正文依赖；B`agent/guard.py:17/27` head/撤销/正文 hash；实际 P7-02 取完整原 SOP。 | 本期完整接入；不是全部 22 文档或三品牌业务质量验收，Phase 6 KQ-058 保留。 |
| 006，Spec:358 | B`agent/graph.py:64/107/128` 理解后动态工具循环；B`agent/memory.py:43` 来源/CAS 候选；修订不授权账本；B`agent/tool_schemas.py:75` 仅读工具/候选/终局。 | 部分：工程协议已实现，真实后继失败反馈与连续业务质量未过。无售后写工具，Phase 9。 |
| 007，Spec:378 | B`application/commit_outcome.py:95` 原子 HITL；B`application/human_review.py:65/104` 版本/人工回复/人工结案；新客户才恢复，普通回复保留风险。 | 本期核心已证：191114真实HITL、194850新Qwen人工后恢复通过，M-01仍列；新配置完整边界尚待。 |
| 008，Spec:396 | B`agent/budget.py:41/59/64/86` cycle 预算；B`adapters/checkpoint_repository.py:130/140` SDK 双写入口；B`worker/agent_runner.py:136` 明确失败；B`application/run_records.py:33` 只读恢复。 | 本期完整工程协议；模型业务失败没有自动改判成功。售后写去重待 Phase 9。 |
| 009，Spec:413 | F`components/mail-agent/AgentProcessPanel.vue:1`、`AgentRunPanel.vue:1`、`HumanReviewPanel.vue:1`；真实 API 运行/引用/人工控件，明暗双窗口。 | 本期完整 UI 责任；见第 6 节，有限工程模型数据不代表 Qwen 质量。 |
| 012，Spec:476 | B`agent/understanding.py:7/44/52` 多诉求、对象、condition/solution/consent/schema/source；B`application/understanding_revisions.py:57` 可修订；解析修复有预算。 | 部分：202431真实条件退款遗漏未来条件且无修订（H-12），新后修须实测；multiobject仍未调用。 |
| 013，Spec:493 | B`observability/local_records.py:18`、`usage.py` 本地持久/actual usage；B`worker/agent_runner.py:40` 每新 run 新 trace；F`AgentRunPanel.vue:117` 费用未知/Langfuse 尚未接入。 | 本期本地关联完整；实际 Langfuse 服务、导出和完整隐私验收**未实现，Phase 11**。不宣称完整 REQ-013。 |

## 4. 22 项 AC 逐项核对

| AC / Spec 行 | 证据 | 当前结论 |
|---|---|---|
| 007 / 298 自动有据发送 | B`application/commit_outcome.py:124/142`；T`test_agent_outcomes.py:19`；真实旧P7-01有1出站，184615 P7-02审计旧生成+新实际核验/提交1出站。 | 部分，真实后继完整闭环仍待。 |
| 008 / 299 同键不重复 | B`application/commit_outcome.py:19/78`；T`test_agent_outcomes.py:37/53` 同 effect/丢响应/重执行仅原凭证。 | 本期完整，独立 PG 通过。 |
| 009 / 300 第三轮失败反馈 | B`agent/context.py:36`、T`test_agent_outcomes.py:119` 保留旧 Agent 回复与客户失败；决策/validation 要求不重复。 | 本期核心已证：191114真实P7-03保留5失败事实、无重复、HITL0出站；其后只作审计历史，不称最新提示fresh质量。 |
| 010 / 315 沿用历史订单 | B`agent/understanding.py:71` 每 intent 自己引数字原文；B`agent/graph.py:100` 具体来源修复，不让客户重报；T`test_agent_tools.py` 具体修复回归。 | 191114/194850实际沿用来源已证；旧真实失败保留，当前新schema字面quote效果须德文等边界另验。 |
| 011 / 316 多商品澄清 | B`agent/tool_gateway.py:90` scoped 只读服务未选行时不授 SKU；T`test_agent_tools.py` 跨客户/多行拒选；理解候选不改作用域。 | 部分，真实 multiobject case 未执行。 |
| 015 / 345 不假读附件 | B`agent/context.py:80` 当前只读文本/metadata 不等于内容；无图片/PDF 客户读取工具；validation 全文核对依据。 | 本期文本边界完整；正式图片留 Phase 8，不宣称图片识别通过。 |
| 017 / 374 缺订单补问 | B`agent/graph.py:111` 无订单仅候选/澄清/人审；T`test_agent_outcomes.py:19`；旧真实 P7-01 英文补问 PASS。 | 旧真实样本及工程路径已证；当前连续整链仍部分。 |
| 018 / 375 不重复失败配对 | B`agent/prompts/decision.md`、`validation.md:5`；T`test_agent_outcomes.py:119` 历史保留。 | 191114真实HITL及194850人工后确认没有重复步骤；原失败保留，不把历史重放当新质量。 |
| 019 / 376 不受越权输入影响 | B`agent/tool_gateway.py:29/77/108` strict/no scope params/scoped queries；T`test_agent_tools.py` 拒 SQL/额外字段/外客户与 operation。 | 工程作用域完整；真实 crosscustomer 行为待验。 |
| 020 / 391 无资料转具体人审 | B`application/commit_outcome.py:95/105`，Handoff gaps 必需；T`test_agent_outcomes.py:73/102`，UI 危险接管 0 Agent 出站。 | 工程完整；真实 noSOP case 待验。 |
| 022 / 393 人工后新来信恢复 | B`application/human_review.py:65/88`；T`test_agent_human.py`、`test_agent_outcomes.py:73` 人审/事件两顺序与新 run；普通人回复不立即跑。 | 194850冻结恢复核心PASS，人工与note完整进input，0即时唤醒；191114 H-08原质量FAIL不改，M-01仍列。 |
| 024 / 409 旧结果不可覆盖 | B`agent/guard.py:44` 锁、lease、branch、input、owner；T`test_agent_faults.py:126` Event 定序；checkpoint 双入口迟到反例。 | 本期完整工程验证。 |
| 025 / 410 超时/停止不出站 | B`worker/agent_runner.py:136`；T`test_agent_faults.py:27/38/60`；真实 UI 超时保留 unknown，queued 停止 0 模型/0 出站；真实批失败 0 新出站。 | 本期完整。 |
| 026 / 411 恢复无重跑 | B`application/run_records.py:33` GET 不 invoke；B`worker/agent_runner.py:49` 原凭证优先；T`test_agent_outcomes.py:53/160`。 | 本期完整 PG/恢复协议。 |
| 028 / 425 人审控件与正常自动 | F`components/mail-agent/HumanReviewPanel.vue:1`；真实 UI risk reason/note/决定/提交与 normal 仅读已发送记录。 | 本期完整 UI；自动 Qwen 质量由 007 单独约束。 |
| 032 / 426 基线主题/可读 | F`views/mail-agent/index.vue` 使用现有 layout/ElDrawer；1440×900 明/暗、1280×720 暗真实浏览器；API 向本机 18181，无模板登录接口。 | 本期 UI 范围通过；Stage 2 邻居视觉对比尚未执行。 |
| 044 / 472 历史不注 Mock 交易 | B`agent/context.py:55/67` 历史 no release/no旧候选；B`application/commit_outcome.py:121/134` comparison；T`test_agent_outcomes.py:131`。 | 本期完整；售后写未开放。 |
| 045 / 488 多诉求/各对象 | B`agent/understanding.py:7/44` intents 列表；T`test_agent_tools.py` 条件/两个诉求及无交易写入。 | 部分，真实 multiobject/multiintent 待验。 |
| 046 / 489 条件退款不立即执行 | B`agent/understanding.py:12` condition/solution/consent 分离；无退款写工具；T`test_agent_tools.py` 条件意图保留与零交易。 | 部分：202431实际查询物流且不写交易，但原退款条件丢失，H-12 FAIL，不能只凭未执行退款算匹配。 |
| 047 / 490 根据证据修订 | B`application/understanding_revisions.py:57`；F`UnderstandingPanel.vue:64`；9 项 revision + 4 个审查者风险反例。 | 本期完整工程责任，不以初始类别锁路由。 |
| 048 / 491 解析失败不默认业务 | B`agent/graph.py:69/94/105` 两次修复及具体失败；T`test_agent_faults.py:16` 2 请求、0 工具/出站。 | 本期完整工程验证；真实旧来源失败未被抹去。 |
| 052 / 509 新 run/trace 不重放动作 | B`worker/agent_runner.py:40` 新关联；B`application/human_review.py:88` 仅新客户资格；T`test_agent_human.py`。 | 本期恢复协议及194850核心目标已实际执行；新run/trace、人工后未即时自动唤醒。H-08旧质量FAIL与M-01单列。 |

## 5. FT、预算和终局协议

| FT / 本期责任 | 代码与独立结果 |
|---|---|
| 01，旧模型迟到/接管/输入 | B`agent/guard.py:44`；T`test_agent_faults.py:126` Event 可控顺序，接管/来信/租约皆拒迟到；双 SDK 入口同样拒。未以随机 sleep 猜竞态。 |
| 02，人工与业务事件顺序 | B`application/waits.py:41/65` suppressed；T`test_agent_human.py` 两种事务顺序、陈旧表单和新客户后恢复；业务事件不能越人审。完整业务事件模拟器 Phase 10。 |
| 04，本期回复/候选/checkpoint 同锁 | B`adapters/checkpoint_repository.py:55/130/140` 取 guarded 原连接、同锁/同连接 SDK put 与 pending writes；`:22/39` strict finite JSON/no pickle。16 项真实 SDK+PG 通过，含回滚/stop 锁等待/branch/delete/租约/head。正式售后申请/执行仍 Phase 9，完整删除 Phase 12。 |
| 05，提交丢响应/未知结果 | B`application/commit_outcome.py:19` 模型/effect 前查原 scoped receipt；B`application/understanding_revisions.py:59/113` 同键回凭证且效果/receipt atomic；T`test_agent_outcomes.py:53` 与 revision:98 实跑。重启仅展示，不盲重发。 |
| 08，历史/未来/对照 | B`agent/context.py:55`；T`test_agent_outcomes.py:131` 历史 AI/人工对照/未来哨兵排除，comparison 不回注当前前缀；只读工具继续按历史截点查询。 |
| 09，全部暴露 RAG 与撤销共锁 | B`agent/tool_gateway.py:133/150` 先登记全部返回正文；B`agent/guard.py:27` head 和 deps 当前校验；T`test_agent_knowledge.py:53/172` 最终没引用的已暴露文也阻提交，真实 head 锁等待后撤销。 |
| 10，stale 只重建一次 | B`worker/agent_runner.py:69/100` 一次；B`agent/context.py:82/97/113` 保留同输入理解/可信业务 receipt、clear old RAG+deps+旧 draft hash；T`test_agent_knowledge.py:74/115/149` 预算共用、第二次变更人审、query embedding 期间切头。 |

B`agent/budget.py:41/59/64/86` 的同 cycle 6 模型、12 工具、120 活动秒、16k 输入/2k 输出、80k 累计和 30s 网络门实跑；未知 usage 保守预留，重试不归零。B`application/business_digest.py:8`、`commit_outcome.py:53/59` 最终锁账本并比摘要，静默库存更新也拒旧回复（T`test_agent_tools.py`）。

最新 B`agent/graph.py:113/116/118` 追加固定来源 role 提示；剩 <=2 只给 reply/handoff，<=1 只给 handoff，不删原文。B`agent/transcript.py:6` 去掉等价 assistant 终局副本，保留完整 normalized 终局 result 为 user，读工具 call/result 保留；T`test_agent_validation.py:36/54` 独立检查完整 body/claims/defaults/command_source_id/read payload。审查者另让模型无视最后 handoff-only 列表返回伪退款 reply，validation 仍被 budget_exhausted 拦截：[输出](artifacts/phase7/review-3-last-request-repro.txt)，6 ledger/2 本轮实际请求/0 出站。没有靠模型自律绕过独立核验。

## 6. 独立编译、测试与真实 UI

| 执行 | 原始证据/结果 |
|---|---|
| 全 Agent 第一次独立 | [原日志](artifacts/phase7/review-3-backend-key-tests.txt)：84 tests / 202.637s / OK；运行期间 provider/eval 改动边界在日志及 SHA 明示。 |
| 最新 Python/Graph/transcript 独立 | [原日志](artifacts/phase7/review-3-backend-latest-tests.txt)：86 tests / 164.346s / OK；唯一运行中改动 validation.md。Scripted 仅证明真实 PG/Graph/guard/commit 协议，不证明自然语言质量。 |
| 最新 lean 菜单专项独立 | [validation](artifacts/phase7/review-3-menu-validation-tests.txt)：8 tests / 17.090s / OK；[tools](artifacts/phase7/review-3-menu-tools-tests.txt)：12 tests / 22.916s / OK，含真实 PG full>16k/lean≤16k 的读取可达反例。 |
| 最新人审菜单及近邻独立 | [31项PG](artifacts/phase7/review-3-handoff-menu-tests.txt)：31 tests / 66.898s / OK，含human-fit真实接管与human仍超预算拒绝0人审，tools/validation/revisions全回归。Graph64bf/最新理解提示；有限模型仅工程协议证据。 |
| 最新工具协议及故障独立 | [48项](artifacts/phase7/review-3-protocol-final-tests.txt)：48 tests / 85.547s / OK / exit0 / 0skip；[before/after SHA](artifacts/phase7/review-3-protocol-final-snapshot.json)完整相等，Graph65580d/provider a8379e。4个SDK边界mock证明kwargs，真实PG证明菜单拒绝、同预算、修订及故障；不称mock为实际模型HTTP。 |
| 最新知识夹具与撤销独立 | [5项](artifacts/phase7/review-3-protocol-knowledge-tests.txt)：5 tests / 21.332s / OK / exit0。两个有限模型夹具从原BASE01客户BODY字面订单补合法候选；真实Gateway重新核来源和身份，原6请求/3工具、旧refs清空、最多一次重建和第二次切头人审断言未改。 |
| H-08三提示后独立工程回归 | [15项](artifacts/phase7/review-3-plan-tests.txt)：15 tests / 21.305s / OK / exit0 / 0skip；[before/after SHA](artifacts/phase7/review-3-plan-tests-snapshot.json)完全相同。provider/menu-pressure/validation的全文、最后额度、未声明拒绝、修复和hash门通过，不能替代实际时态语义判断。 |
| 来源早验/Commit完整门独立 | [47项PG](artifacts/phase7/review-3-source-tests.txt)：47 tests / 114.028s / OK / exit0 / 0skip；[全部src before/after SHA](artifacts/phase7/review-3-source-tests-snapshot.json)完全相同。validation/tools/menu/knowledge/outcomes/revisions验证坏来源无paid review、只修复一次、完整旧结果、末端hash/语言/引用/业务摘要、stale重建及修订；[compileall原输出](artifacts/phase7/review-3-source-compile.txt) exit0。这仍是工程协议，不替代新真实P7-04。 |
| 精简grounding最新边界独立 | [6项PG](artifacts/phase7/review-3-source-prompt-tests.txt)：6 tests / 12.354s / OK / exit0 / 0skip；[before/after SHA](artifacts/phase7/review-3-source-prompt-tests-snapshot.json)相同。菜单human-fit/not-fit/越界拒绝，坏source早验/一次repair及最终hash均符合原预算；0paid HTTP。 |
| 新 validation 专项独立 | [原日志](artifacts/phase7/review-3-latest-validation-tests.txt)：8 tests / 17.827s / OK。 |
| 前端独立 | [test](artifacts/phase7/review-3-frontend-tests.txt)：53/53 / 2519.9525ms；[build](artifacts/phase7/review-3-frontend-build.txt)：vue-tsc + Vite PASS / 26.27s。 |
| 编译/评测本地门 | [compile](artifacts/phase7/review-3-backend-compile.txt)：exit0；[eval local](artifacts/phase7/review-3-eval-local-tests.txt)：7/7 / 0.339s；[freeze](artifacts/phase7/review-3-freeze-check.txt)：9 case 已冻结、0 paid。 |
| 独立 SSE | [network JSON](artifacts/phase7/review-3-network-check.json)、[raw](artifacts/phase7/review-3-network-output.txt)：monotonic reconnect/scope/safe payload；15.0s heartbeat 0 新 run/邮件；422 negative、409 future cursor；0 provider。 |

原始编译关键输出：

```text
Command: uv run python -m compileall -q src
Exit code: 0
$ vue-tsc --noEmit && vite build
vite v7.1.7 building for production...
✓ 3318 modules transformed.
✓ built in 26.27s
```

浏览器 `phase7-review` 无 route stub，实际请求读取隔离 API18181/PG；UI15174、manual-agent，无后台 provider。根服务重新加载后的 schema 是 `phase7_browser_ebeba169fde948308e74db38bfb99d01`。Scripted 有限工程序列经真实 Graph/RAG/guard/commit 初始化，**不冒充真实 Qwen**。未访问或写正式18080/15173；正式库升级和 cleanup 由主 Agent 控制。

实测：[真实 API 状态](artifacts/phase7/review-3-ui-state.json)；normal 的 query/RAG/refdrawer/understanding/usage 来自持久记录（人工工程样本没产生意图，UI如实为空）；失败显示 model_timeout+unknown2/reserve16512，retry 新 attempt 仍同 cycle/原账单而仅 queued；queued stop 经确认变 stopped、0模型/出站；risk 显式更正无当前 note 被真实表单阻止，补当前 note 后 active0/人工出站1/Agent0，human_wait_customer、没有立即模型执行。

截图（均隔离合成数据）：[normal 暗1440](artifacts/phase7/review-3-ui/review-3-normal-1440.png)、[明1440](artifacts/phase7/review-3-ui/review-3-normal-light-1440.png)、[正常暗1280](artifacts/phase7/review-3-ui/review-3-normal-dark-1280.png)、[详情抽屉暗1280](artifacts/phase7/review-3-ui/review-3-process-dark-1280.png)、[引用](artifacts/phase7/review-3-ui/review-3-reference-1440.png)、[失败](artifacts/phase7/review-3-ui/review-3-failure.png)、[停止](artifacts/phase7/review-3-ui/review-3-stopped.png)、[无 note 验证](artifacts/phase7/review-3-ui/review-3-risk-note-validation.png)、[显式更正](artifacts/phase7/review-3-ui/review-3-risk-corrected.png)。实际查看截图确认内容可读、可滚动，1280 使用原 ElDrawer。Stage 2 邻居对比尚未执行。

## 7. 真实 Qwen：180804 失败永久保留，最新复验待定

**H-04 / HIGH，真实核心闭环当时不匹配。** DEV-PLAN:170 要求真实 Qwen 至少三封客户来信及 HITL 恢复和英德/条件退款/多诉求多商品/无 SOP 边界。最新实际 `20261008-180804-6cae1f4f` 中，P7-02 查单及完整适用 SOP 成功，英文草稿中性询问 `Have you tried ... before? If so ...`，没有把文档示例当客户配对历史，也没有复述未经核准的操作步骤。但第 6 个模型 validation 把该 yes/no 条件问句误判为已做配对，返回 supported=false。没有授权 hash/出站；其后修复决策 reserve 被 input_budget_exceeded 拒绝，未发生第 7 HTTP。

审查者逐一人工读完整六个 response、request06 中客户前缀/工具观察/全文草稿，以及原 `data/knowledge/v1/sop/OUTON-01.md`（SHA `543cd121...439952c`），独立同意这里是核验器 false-positive；**草稿合格不等于合法完成**。实际结果 6 new Qwen HTTP / 3 tools / 53,265 活动毫秒 / 21,103 累计实际 tokens / 0 新出站；status=budget_exhausted，error=input_budget_exceeded，原目标 completed1 未达到。[安全摘要 real-model.json:6372](artifacts/phase7/real-model.json)。完整原始输入/响应仅在 `tmp/phase7-agent-eval/20261008-180804-6cae1f4f`。

此前语法、工程 metadata、输入预算、旧 SOP 示例历史假定（validator 漏判）、P7-03 每 intent 缺订单数字原文、0.7 prefix 最后 validation timeout 均保留在该摘要，不被后修覆盖。旧 P7-01 真实补问合格仅用作实际历史 seed，不改写为本次新 HTTP。9 个 case/SOP 原冻结输入及标签未改；0.7 采样与系统来源提醒的单样本改进不被宣称为概率模型正确性证明。

180804 后，主 Agent 先更新 IMPLEMENTATION，再仅补 `B agent/prompts/validation.md:7/9/11` 的通用句类顺序和正反例：neutral WHETHER/if-so 不要求既往肯定报告；真正 WHEN 历史断言仍需客户/本案人工来源，型号动作仍需 scoped target+适用知识。第三轮重新读取该最新原文，没有用特定 case ID/固定答案白名单放行。独立完整正/负 request 的真实提示适配与全新真实业务 attempt 尚待证据；适配 HTTP 不计作原 cycle 第7，也不算业务闭环。

后续原始证据也已独立阅读：`181311` 接受 neutral 问句但拒绝前导 `we will check` 的 actor 歧义，原完整稿保持 FAIL；`181658` 仅删除该前导及对应 customer_fact claim 的显式合成纯问题变体 supported=true、原 WHEN 负例 supported=false。`globalmail-agent/agent-eval/validate_frozen.py:43/55/69` 对变体列出 body/claims 差异，所有非 draft context/understanding/observations 不变，`:84` 付费前 manifest，`:96` 每项实际独立 HTTP，未连接业务 DB/提交原 cycle。这两个已知边界的提示适配通过，不算真实连续链通过。

**H-05 / HIGH，181730 的预算菜单导致正常 RAG 缺失。** 已读该批全部三份实际响应及 request03：一次 Understanding 成功，真实查单成功，随后没有任何 reference 时 B`agent/graph.py:118` 因“完整 messages+全部工具声明”的输入代理 `16,201>16,000`，仅暴露 reply/handoff（12,324），当时仍剩 4 个模型请求。合法菜单没有 `search_reference`，无法继续取得冻结 P7-02 必需知识；模型另幻觉 `get_product_manual`（line_id/sku），B`agent/tool_gateway.py:32` 正确拒绝为 tool_not_allowed。实际3 HTTP/1工具/25,170ms/0出站，原 completed/出站/RAG 目标 FAIL。预算/权限门正确拒发不能代替业务完成。完整输入未修改的独立复算见 [review-3-181730-budget-repro.json](artifacts/phase7/review-3-181730-budget-repro.json)。不建议提高预算、删原文或新增虚构工具别名；该能力缺口需保留必需的当前可用读取并给核验留余量。

H-05 后续程序复核：最新 B`agent/graph.py:121/125/126` 在尚有读取额度且全声明超过16k时，仅暂缓 `get_case_context/update_case_state/revise_understanding`，保留8个读取/终局；精简后仍超限才切终局，最后两次/一次额度规则不变。审查者直接调用当前 `AgentGraph.decide` 捕获冻结 request03（不调用 provider、不连接DB）：全部原 messages 逐字相等，16,201→13,737，`search_reference` 和所有 scoped 业务读均保留，来源SHA记录在 [独立当前菜单反例](artifacts/phase7/review-3-menu-pressure-repro.json)。另外独立12项 tools/8项 validation实际PG通过。该程序菜单缺口关闭，原181730真实失败保留；这项测试没有实际执行RAG或证明新Qwen回复质量，最新完整目标仍待验。

182447后续完整真实尝试仍为 H-04 未达标：最新合法菜单使实际 order→search_reference→draft 均完成，5个实际HTTP/3工具/37,515ms/19,171tokens；核验器把 `Have you tried…? If so, when you attempted…?` 的明确条件内部when误当无条件历史。审查者逐一读完整5个response、全文request05及原SOP，独立判断仍为false-positive；随后只剩一次额度时reserve因input_budget_exceeded拒绝，0新出站。[独立阅读摘要及原始SHA](artifacts/phase7/review-3-182447-semantic-check.json)。最新validation只补通用完整条件作用域，ledger/entitlement/物理承诺/型号指令证据门仍保留，提示全文已重读；新的正/负诊断及审计prefix最终出处待验，原FAIL不会被后修重写。

182942独立核验提示诊断仍FAIL：原182447全文草稿和全部数据保持不变，仅替换system（prompt SHA `3e142152...863ea9b`），1次真实HTTP/3,970tokens/4.641s，依然误判条件内部when；按首失败即停规则没有跑负例。原响应已逐字独立阅读，不算业务PASS或原cycle第7次；后续prefix不能越过该真实诊断失败。

182942后续结构修复的Stage 1独立重核：B`agent/graph.py:174/178` 保留原完整首system和完整user DATA，再追加固定 `validation-grounding.md:1` 的整条件分类提醒；没有把客户/工具/知识正文升为system。直接捕获当前Graph请求，原182447 user字节和全部schema相等，角色system→user→system，输入代理14,988≤16k，5份prompt及graph SHA见 [请求结构](artifacts/phase7/review-3-tail-request-structure.json)。独立 [17项 PG](artifacts/phase7/review-3-tail-validation-tests.txt) / 35.749s / OK，按角色读取完整user并断言真实尾system。通用正负提示没有case ID、固定答案或额外账本授权；真实正负诊断及闭环结果仍待验。

183751最新结构正负控制通过，仅核验适配：独立读两份实际完整response后，逐字比较各实际request与原182447/175613 request，完整user与schema不变、首尾system来自当前源文件，实际归一请求SHA匹配付费前冻结；14,988/14,880输入代理合法。原完整conditional正文supported=true，原无条件When正文supported=false；2个实际HTTP/8,441tokens/12,077ms/0业务/原cycle未变。[独立校验](artifacts/phase7/review-3-tail-real-adaptation-check.json)。这关闭本次已知正负判界，不构成最新三封+人工恢复+五边界的真实业务PASS；下一步审计prefix后实际终局及后继仍待。

184249 审计已有实际四响应的工程出处通过：审查者全文重读 `globalmail-agent/agent-eval/draft_prefix.py:9/77/91/131`、`audit_draft_prefix.py:51` 与 `run_eval.py:78/111/186`，读完整下一核验request及12路径审计。独立重建严格比较而非只信helper标志：4原paid响应SHA匹配此前独立证据，provider IDs/usage/全文值仅作精确ID映射；8个UUID、两次observed_at及当前derivedbusiness_digest列明，完整业务data/原SOP/理解/客户记录/draft非ID均相等。SOP仍含原When模板，draft body SHA `ad219354...37b78f1`。当前loader付费前另冻结全部11可信原文件SHA，request05读前复查；原失败response05不读取/重用。保守旧整轮37,515ms进入新cycle，4旧请求/3当前真实工具/15,257tokens/42,780ms/unknown0；进入validation reserve前显式停止，0新对话HTTP/0出站/0artifact，cleanup全true。真实Embedding初始化另记，不能称全部网络调用免费。[独立严格比对](artifacts/phase7/review-3-draft-prefix-provenance.json)，[10项本地反例](artifacts/phase7/review-3-draft-prefix-tests.txt)：0.342s/OK，改金额或完整SOP均拒绝。这是原真实生成+当前实时重查的出处核对，**不是新fresh生成或业务PASS**；已向主Agent确认可进入已授权的新validation及后继，每案实际语义仍待。

184615 P7-02目前独立真实终局PASS：完整actual response05、request05及持久record理解/3工具/SOP/ref/artifact/claims/客户时间线已人工读。原182447全文draft不变；当前实时scoped订单和原完整SOP有据，客户机身正常/已换电池来源明确，Ifso整条件问句不预设配对，未发未经核准操作或履约承诺。1新actual validation supported=true→guarded真实提交1出站/customer_information等待，5账本=4已审计旧生成+1新核验，3工具/19,438tokens/47,748ms含37,515base/unknown0。全文body/claims/citations与送审draft精确相等。[独立语义及原始SHA](artifacts/phase7/review-3-business-semantic-checks.json)。本次H-04的P7-02终局缺口关闭，180804/181311/181730/182447/182942旧FAIL不改；这里只新增核验+真实提交，**不称fresh生成**，P7-03/04及五边界仍待，不能提前Stage1 PASS。

**H-06 / HIGH，184615 P7-03 原完整真实后继因菜单压力未形成合法人审。** 已独立读全部3个实际response、客户前缀、实际查单和完整SOP；本案沿用历史订单的intent.sources确实引含数字原文，5项失败/拒绝重复事实完整。随后第四决策发送前被16k门拒绝：完整声明20,424、精简17,960、双终局16,547，均超限；仅人审声明15,372却能合法容纳。实际3个fresh HTTP/2工具/11,340tokens/31,359ms/unknown0/0新出站，无proposal或人审，原handed_off目标FAIL。人工、P7-04与五边界均未调用。重建第四请求明确是 `blocked-next-request-reconstructed.json`，不是实际已发HTTP；原真实失败不能改成成功。

H-06后续程序复核：B`agent/graph.py:130/132` 对所有菜单分支最后再次检查输入，仅在双终局仍超限时保留人审schema；保留完整原messages，仍须模型明确选择人审，完整人审仍超限时由原Budget拒绝，不由技术错误默认造HITL。审查者从原request03/response03及当前真实normalized检索receipt独立重构再直接捕获当前decide，全部messages与阻断重建相等，当前菜单只含request_human_review、代理15,372；Graph SHA `64bf8539...32ffc1`，0付费/0DB。[独立原反例及当前菜单](artifacts/phase7/review-3-P7-03-budget-repro.json)。全文重读新增T`test_agent_menu_pressure.py:34/51`，并独立31项PG/66.898s/OK：320次合法客户详情同时证实双终局>16k、人审≤16k、3请求/2工具/真实HITL/0出站；400次仍超门作为拒绝且0人审的负例。程序可达缺口关闭，新真实后继尚待，不能凭工程Scripted宣称业务关闭。主Agent旧245项456.435s全量对应此修复前源码，原日志保留，新源码需另验。[最新compileall](artifacts/phase7/review-3-handoff-menu-compile.txt) exit0。

**L-01 / LOW，理解类别精度。** 原184615 P7-03把明确失败排障标成product_inquiry，事实和诉求均保留、未据类别固定路由。依据Spec:476、B`agent/understanding.py:7/44` 的类别可修订契约，记录为分类质量偏差。最新 `prompts/understanding.md:7` 加通用故障/规格语义边界，没有case ID或固定答案；此提示变化不能由旧P7-02历史seed证明，新实际P7-03分类待验。

185555 仅初始化已接受历史的独立出处PASS：全文重读 `globalmail-agent/agent-eval/second_history_seed.py:9/54/99`、`eval_options.py:31` 与本次完整真实PG record/SOP/原及当前核验DATA。独立脚本逐字段验证5个原paid响应的provider ID/usage/content/calls，组合两层8个UUID映射，完整context/understanding/draft/所有业务资料在4条明确observed_at/business_digest路径外相等；完整SOP与草稿body/claims/citations原值不变。付费前manifest中原11文件和accepted13文件SHA均匹配，accepted request05/response05/runrecord另匹配本审此前独立SHA。5旧请求/3当前真实工具/19,438tokens/52,185ms含原47,748base、unknown0、0新chatHTTP，真实Graph/commit生成历史出站1、cleanup true。[独立逐字段证据](artifacts/phase7/review-3-second-seed-provenance.json)。没有使用失败P7-03作为历史、未重用旧失败validation、无Scripted阳性；该seed不是新生成/核验质量，也不证明最新understanding类别提示。已向主Agent确认可推进其授权fresh P7-03/04逐封语义gate。

**H-07 / HIGH，185852 新鲜实际P7-03仍未完成：模型返回未声明读取，修复上下文挤出最后人审。** 已逐一读5份完整actual response、完整record理解/业务/SOP/客户前缀。初理解quote人为插省略号，原精确来源门正确拒绝；一次修复后类别troubleshooting、5项失败/拒绝事实及intent历史数字quote有效，L-01在该fresh样本关闭。实际order与完整RAG成功；第5请求真实只有request_human_review schema、代理15,517，但模型返回未声明的search_reference且types是字符串非array，B`agent/tool_gateway.py:35`参数门正确拒绝，B`agent/graph.py:149`加入一次错误修复。后继完整人审代理16,004>16,000，发送前拒绝；没有第6HTTP、proposal、人审或出站。实际5 fresh HTTP/2工具/18,649tokens/55,609ms/unknown0，P7-04/人工/边界没有调用。独立复算确认两次菜单与数值，[原始SHA及安全摘要](artifacts/phase7/review-3-185852-semantic-check.json)。B`adapters/model_provider.py:27`当时tool_choice=required，B`agent/graph.py:145`仅交全局网关参数门而未限制当次菜单返回；安全拒发成立，冻结handed_off业务目标仍FAIL。独立检查[阿里官方Function Calling协议](https://help.aliyun.com/zh/model-studio/qwen-function-calling)：Qwen非thinking的required不保证调用，具体命名function choice是受支持选项；不能将required当作后端菜单授权证明。没有提高预算、截断或改标签来关闭此缺口；最新修复与真实复验待验。

H-07后续协议复核：B`adapters/model_provider.py:27/29` 单合法工具命名function、多工具auto；B`agent/graph.py:134/136`在模型usage settle后核对全部返回工具属于本次声明菜单，不执行越界调用、不抹已付费记录。无订单时B`:112`显式允许纯本案get_case_context，业务读取仍禁。独立48项85.547s/OK/0skip、before/after源码SHA一致；另让最后额度模型恶意返回退款reply，[独立PG](artifacts/phase7/review-3-declared-last-request.txt)1项2.823s/OK，6账/unknown0/tools0/0出站，现更早model_tool_not_allowed，旧budget_exhausted反例不覆盖。首次协议36项[原日志](artifacts/phase7/review-3-protocol-tests.txt)65.884s/1FAIL保留：旧长输入夹具先触发未声明读取，且运行中源码修订，不作稳定版本PASS。最新负夹具T`test_agent_menu_pressure.py:69`用合法350次原文及有精确来源的4完整facts，断言理解可放入预算、人审全文仍超限、1请求/0工具/0人审/0出站；历史future夹具补真实客户字面候选而不改未来快照断言。声明及请求代理不提高、正文未删，程序缺口关闭，实际业务另验。

191114 P7-03核心真实目标独立PASS：全文4份actualresponse、完整req04的5邮件/旧casefacts/理解/真实订单/完整原SOP、实际SDK payload与持久review/artifact均人工读；4份SDK允许字段和原Graph messages逐字核对，实际最后tool_choice明确命名request_human_review。历史订单及全部sources精确，5失败/拒重复事实保存，troubleshooting一次理解成功，真实handed_off/0新出站，无重复步骤或售后执行。4fresh HTTP/3工具/16,602tokens/41,797ms/unknown0；[独立语义与raw SHA](artifacts/phase7/review-3-business-semantic-checks.json)。该实际HITL关闭H-06/H-07的本冻结P7-03终局缺口，184615/185852原FAIL保持；后续人工→P7-04及五边界尚待。

L-02/LOW（本期非阻塞候选与未发送草稿限制）：该P7-03的requested_solution扩成“diagnosis or replacement”，客户未明确要求replacement，不能解释为客户已同意补发。它仍是可修订的排障候选，没有新增replacement意图或交易权限，本期无补发写工具。人工未发送draft含“in this phase”内部措辞，summary/gaps为英文而decision prompt请求中文；不称该draft为核准客户成稿。核心失败事实和具体转人工缺口有据，0自动出站，不将这些局部限制隐瞒或误判为已执行售后。

**H-08 / HIGH，191114 P7-04把人工计划升级为正在执行，核验漏判后实际出站。** 依据Spec:106不得把计划/承诺当执行事实、REQ-006 Spec:366/370事实与推断及建议/执行分离、AC-007 Spec:298有据回复。审查者独立读4份完整actualresponse、完整request04的human正文/note/客户前缀/理解/订单观察/draft，以及持久artifact和时间线。人工seq6只说`Our staff will check the compatible remote before proposing any replacement.`，当前note为`待员工核对适用遥控器兼容性`；没有本案来源说员工已开始核对。自动正文却说`Our staff is currently checking the compatible remote specifications before proposing any next steps.`。实际response04的supported=true，理由错误地把该进行时陈述称为proposed next step；B`agent/graph.py:181`预算内全文语义门因此授权，B`application/commit_outcome.py:36/142`精确提交相同正文，并实际新增1封模拟Agent出站。Hash/来源/预算工程门正常不等于该事实正确。

该批4fresh实际HTTP/2工具/15,836tokens/45,609ms/unknown0，真实新run/trace、人工原文与note均进输入，恢复工程成功；**业务质量FAIL**，五边界没有调用，不能凭completed1放行。全部14份raw文件SHA与当次Graph65580d/5prompt源码快照永久记录在[独立完整语义反例](artifacts/phase7/review-3-business-semantic-checks.json)。这不是此前无出站的草稿措辞LOW；此句已经提交给模拟客户。原P7-03核心PASS和所有旧失败保持。

H-08后续源文档/提示结构复核（尚未真实关闭）：已重读IMPLEMENTATION最新失败记录及`B agent/prompts/grounding.md:7`、`validation-grounding.md:9`、`understanding.md:7`全文。通用计划/待办不得升格为进行/完成，客户正文不包含实施阶段，requested_solution只记录客户真实请求，不自行增补replacement/refund；没有case ID白名单、预算调整或改9个冻结目标。直接捕获当前AgentGraph.validate对原失败稿的请求：完整context/understanding/observations/body/claims user逐字相等，原首system及schema不变，尾system取最新源文件，代理15,474≤16k，0HTTP/0DB。原请求SHA及当前5prompt/Graph SHA见[独立结构证据](artifacts/phase7/review-3-plan-request-structure.json)。当前代码仍保留全文DATA与原独立核验/commit门；真实正负判界及新P7-04尚待，不能用提示自述关闭H-08。

192652时态适配控制的独立窄范围PASS：完整两份actualresponse已人工读；negative原失败DATA/schema/其他请求字段不变，currently checking明确supported=false；positive只对body与第二claim同一状态句替换为awaiting staff review，其他所有字段/source IDs/正文/人工输入不变，supported=true。actual请求与付费前prepared/冻结SHA完全相同，SDK messages逐字相同且字段不含凭据；代理15,474，2实际HTTP/8,325tokens/11,359ms/0业务，原cycle不变。[独立逐字段证据](artifacts/phase7/review-3-plan-real-adaptation-check.json)。positive理由仍以lack fulfillment tool record佐证no-dispatch，不能据此独立证明当前账本不存在履约；本案人工原文明确无派发，可作有来源的人工记录转述。新P7-04须另判正文是否保留这个范围，H-08未据两例诊断关闭。

192935第三封HITL历史初始化的独立出处PASS：完整重读`globalmail-agent/agent-eval/third_history_seed.py`、`draft_prefix.py`、`second_history_seed.py`及本次真实PG/Graph原始record和4request/response。原accepted191114第三封的16可信文件SHA与此前本审独立accepted原SHA相符；所有4response的usage/providerID/finish/calls/content逐字段相同，schema理解只映射精确来源ID，工具调用附带普通content完整原样。4request全部user context/understanding、当前实际order/完整SOP仅10随机UUID和4条read observed_at/business_digest变化；initial/current/revisions、人审9个领域字段含完整summary/gaps/note/draft、artifact5字段以及全部工具参数/result均严格相同。持久终局工具的真实observed_at另列为工程时间，不删其业务data。4旧请求/3当前真实工具/16,602tokens/45,499ms含原41,797base/unknown0/0新chat/0新增出站，cleanup三项true、代码快照无变化。[独立第三来源审计](artifacts/phase7/review-3-third-seed-provenance.json)。

同批第二层也重新严格比对5个原actualresponse、两层完整DATA/SOP/draft、原11+accepted13 SHA；历史首尾system匹配原accepted源快照，current重放首尾system匹配最新源快照，不能把“历史提示不同于最新”误当原数据变更。[独立第二层审计](artifacts/phase7/review-3-third-second-seed-provenance.json)。192730首工程FAIL由eval错误json.loads普通assistant文本导致，原失败保留；源码只对schema响应解析映射，未到HITL先明确停止，[独立14项](artifacts/phase7/review-3-eval-third-seed-tests.txt)1.605s/OK/0skip含实际旧response02完整保留和修改金额/全文SOP拒绝。这批不加载/重放失败P7-04或未来human，没有新fresh理解质量；已确认可进入主Agent授权的单次fresh P7-04，实际语义仍待。

**H-09 / HIGH，193324 fresh P7-04的确定性来源错误直到付费核验后才拒绝，缺少预算内修复。** 当次源快照Graph `65580d84...eab5`、Commit `34e5e9a2...94a`。审查者独立读全部4份actualresponse、完整request04 DATA、SDK payload与持久record；新正文`Our staff will review…`没有进行时升级，但claims[0]把纯`Thank you for your message.`标作customer_fact且source_ids为空；claims[1]/[2]均标order_fact，只引用客户/人工message和human_note，没有任何成功业务command来源。当次B`agent/graph.py:181`仅预验全文覆盖，实际response04 supported=true后保存hash；B`application/commit_outcome.py:64/74`的最终来源门先报customer_fact_without_message，另外两项也不符合order_fact的business command要求。4fresh HTTP/2工具/15,568tokens/42,702ms/unknown0，artifact0/出站0，未完成原completed1目标，五边界未执行。最终拒发正确，但不等于恢复业务合格。

原人工note只有“没有创建补发或退款”，新claim额外说`no refund has been issued at this time`，且没有引用当前订单查询凭证。创建与实际退款执行不能混为同一事实；本案人工记录可以按原范围转述，当前账本事实须成功scoped业务观察。全部14raw SHA和当次source快照保留于[独立H-09完整反例](artifacts/phase7/review-3-business-semantic-checks.json)。主Agent提出把相同确定性source/language/citation预验移到paid语义核验之前以支持原预算内一次repair，同时保留Commit重验/hash/business摘要门；这项后修尚待独立重新核验及真实P7-04，不覆盖193324 FAIL，不关闭H-08。

H-09后修的独立工程边界通过：已全文重读IMPLEMENTATION最新步骤、B`application/draft_validation.py:11`、`commit_outcome.py:36`、`agent/graph.py:176`和通用decision/grounding提示；共享源门保持原语言/deps/command来源/业务摘要锁检查。Graph在paid review前guarded预验，只有八种明确格式/来源错误可用原一次repair；stale、接管、租约等异常继续重抛。Commit先要求相同normalized hash，再调用同一门重验；没有把clarification自报当事实授权，完整语义核验仍必经。初次读到落地中间版函数内guarded重复导入会导致UnboundLocalError，主Agent在启动PG前删掉；稳定版已重新读取且47项PG通过，不把中间源码当已跑版。通用提示与repair说明明确courtesy/customer/human/ledger角色，全部已拒稿字段及读观察保留。最新真实闭环仍待，H-08/H-09的原FAIL不被工程通过覆盖。

194223新初始化仅工程FAIL：新增来源提示的当前Graph重放accepted第三封历史，在真实查单和完整SOP后，actual human-only decision 输入代理16,157>16,000，原门拒绝，0新chat且尚未写人工/运行fresh04。独立与accepted191114比较，五封历史正文逐字相同，完整SOP SHA仍2f0d709e…，没有截断或放宽预算；[原被挡请求与SHA](artifacts/phase7/review-3-194223-seed-budget.json)。3旧responses/2当前真实工具/11,776tokens/46,265ms含41,797base/unknown0，cleanup三项true。旧accepted03不改；这不是新的04自然语言质量结果，后续须在原预算内重验工程初始化。

194223后预算修复的独立离线边界通过：全文重读通用grounding精简规则及IMPLEMENTATION，条件模板/未知WHETHER/已知动作保留、计划与执行状态、courtesy/customer/human/ledger/知识引用来源边界均仍明确。直接捕获当前AgentGraph.decide（保留剩3原额度，0DB/0HTTP），除最后grounding system外，原所有messages逐字相同，tools/schema相同；human-only原16,157→15,809≤16k。没有删客户/人工/业务/原SOP正文或改估算与预算。[独立当前图请求证据](artifacts/phase7/review-3-source-prompt-budget.json)记录5prompt/Graph SHA。这只证明原反例现在输入可达，最新第三历史出处审计和fresh04仍待。

194702最新三层历史工程初始化独立PASS：沿用上次严格比较脚本但另存本轮证据，[第三层](artifacts/phase7/review-3-194702-third-seed-provenance.json)、[第二层](artifacts/phase7/review-3-194702-second-seed-provenance.json)。16第三/11+13第二原文件SHA再次与本审accepted源相符；全部4/5response的provider IDs/usage/普通content/arguments及完整request user DATA保持，第三只10UUID+4read metadata明确变化，understanding initial/current/revisions、人审9域含summary/gaps/note/draft、artifact5域、order与完整SOP非ID值严格相同。历史首尾system符合旧accepted源SHA，当前图首尾system符合最新源SHA。第三4旧请求/3当前tools/16,602tokens/45,890ms含41,797base；第二5旧/3/19,438tokens/51,638ms含47,748base；0新chat/0新增出站/unknown0/cleanup三项true/源码稳定。未加载失败04或未来human，仍不是新03理解/生成质量。194223原初始化FAIL保留；已确认可推进授权单次fresh04，质量仍待独立全文gate。

194850 fresh第四封独立冻结核心目标PASS：人工原文/note和新客户来信进入当前完整DATA，understanding的5失败事实/order数字quote精确、troubleshooting/consent none，不自行增补客户办理选择。实际4new Qwen HTTP/2tools/16,438tokens/54,280ms/unknown0，在原6/12/120秒内核验→guarded单出站；全文body/claims与artifact/最终时间线精确相同。只确认失败检查已记录及本案人工记录无派发，没有新退款、正在核对、设备步骤、重复配对或重复索取订单。全部4actualresponse、完整validation DATA/record/SDK已独立读，当前source SHA与付费前manifest相同，14raw冻结在[独立语义审计](artifacts/phase7/review-3-business-semantic-checks.json)。前三阶段仅已审accepted actual历史重放，不能称全链新fresh生成。H-08具体进行时反例及H-09来源早验缺口在本新样本关闭；所有旧FAIL不改，不把一次样本视为模型正确性证明。

**M-01 / MEDIUM，194850来源精度和核验理由限制。** 完整context的人工seq6明确`No replacement has been dispatched.`，满足该冻结客户请求的本案记录确认；但单一customer_fact claim只引human_note“没有创建补发”，没有引用明确无派发的人工message ID，validator理由也把创建与派发混为同义。该样本不能宣称已经独立查询并核实当前售后派发账本（本次仅get_order_snapshot）。原REQ-006仍要求历史声称与实际执行分开；建议来源直接指向人工原文并按本案记录范围措辞。这不改变冻结目标或当次实际记录，五边界继续独立逐案核验。

**H-10 / HIGH，195403 P7-05德文核心边界未完成，后四项未执行。** 原冻结目标是completed/1出站、de、有真实查单/适用知识与引用；实际6fresh HTTP/4tools/19,330tokens/53,250ms/unknown0，handed_off/0出站。审查者独立读全部6response、原完整OUTON-01及持久under/tools/draft：首understanding在order_candidates已有数字quote，却没在intent自身sources引用数字，被原门正确要求修复；真实订单和完整SOP成功；第五draft的首句`Vielen Dank für Ihre Nachricht.`没有任何claim覆盖，被全文覆盖门正确拒绝。剩最后1请求只能human，实际SDK命名human选择并持久HITL；没有付费semantic review或第7请求。这是安全拒发后业务未达标，不能把该case的期望改成允许HITL。

未发送draft还额外推断`liegt das Problem wahrscheinlich an der Verbindung…`（问题可能在连接），SOP没有直接给出该诊断；后修稿必须另做全文语义判断，不能只以格式修复通过。最后人审原因把非厂家认证资料与无法询问既往配对现象混为一谈；资料确支持有前提的历史现象补问，不支持未经适用核准的具体通电配对步骤。全部20raw SHA及当次source快照保留于[独立H-10反例](artifacts/phase7/review-3-business-semantic-checks.json)。06条件退款/07多商品/08无SOP/09注入没有调用，不能借工程测试宣称真实通过。

H-10拟议结构修复只作契约评估，尚未代码/真实验收：模型仅输出有序claims.text，Gateway逐字双换行组装body，内部Draft/Commit/记录仍保留body+claims；旧显式body严格保留全文覆盖门，不补删漏句。必须保持extra禁止、组装后原8000字/30claims等边界、精确normalized hash、全文语义核验及Commit全部事务门；不能自动分类/猜来源或让自报kind授权。Intent.sources专属schema描述可强调当前/历史任何非空order_number都需本intent精确数字quote，原source门不放松。主Agent须文档先同步、独立工程反例及当前真实德文另验，原195403 FAIL和194850原配置PASS分别保留。

H-10后 claims-first 协议的独立工程通过：已重新完整读 `B agent/tool_schemas.py:53/65/95`、`tool_gateway.py:30/34/42`、`understanding.py:19/25/73` 及 decision/grounding/understanding 源提示。模型菜单公开 ReplyParts，无 body 字段；Gateway 仅对缺 body 的参数先严格解析 ReplyParts，再将原 claim.text 顺序逐字用双换行组装，随后严格 Draft 校验。显式旧 body（含 None）不自动重组，原 8000 字、extra 禁止、来源/覆盖/hash/paid 全文语义/Commit 事务门保留。新旧参数规范化相同即复用原 UUID5 凭证且只计一 tool，不同 body 同 key 冲突；空普通邮件不得靠组装通过。Intent 自身数字 quote 的专属 schema 描述与当前/历史邮件提示均已落地，原 exact-source 判定未降低。

独立当前 [19 项真实 PG 原始输出](artifacts/phase7/review-3-claims-parts-tests.txt) 41.571s/OK/0skip，覆盖新四项、原十项 validation（legacy 漏句/恶意分类/精确 hash/完整 read 保留/一次 repair）、三项菜单以及 literal-source/schema-pressure。全部 backend src/prompts/tests [before-after SHA](artifacts/phase7/review-3-claims-parts-tests-snapshot.json) 相同，事后对当前再比无变化，gateway SHA `8c026035c21a85dc95ecf21a97fe7ad6d5c6590a7d8b6f82cdb14ce824abc891` 含 TypeError 格式转换；没有以运行中中间版冒充当前版本。独立 [17 项 eval](artifacts/phase7/review-3-claims-parts-eval-tests.txt) 1.514s/OK、[compileall](artifacts/phase7/review-3-claims-parts-compile.txt) exit0。`agent-eval/draft_lineage.py:9/27` 以真实 run/provider-call 的 UUID5 关联 normalized result，缺原 body 的 SHA 为 None，顺序 claim 文本 SHA 与真实组装 body 比较，无修剪或补句；旧 explicit body 单独精确比较，仅元数据诊断，不更改原请求/语义 gate/业务目标。H-10 原失败保留，当前真实德文及后四边界仍待，Stage 2 未执行。

**H-11 / HIGH，200822 P7-05德文无据“很可能是连接问题”经核验漏判实际出站。** 已独立全文读6份actualresponse、完整request06 DATA、原OUTON-01、持久工具/引用/最终artifact与时间线。新首次理解自己引用订单数字、claims-only两份草稿均由真实Gateway逐字双换行组装；第四请求的customer_fact只引business command被来源早门正确要求一次修复，第五稿来源分类修正后第六请求独立语义核验。确定性协议均符合，但实际正文仍写`Da die Lampe selbst reagiert, liegt das Problem wahrscheinlich an der Verbindung zur Fernbedienung.`（灯体正常，因此问题很可能在遥控连接）。客户只证明机身按键正常和新电池；完整SOP说明分开核查遥控及条件询问配对现象，没有判断连接原因或其概率的依据。“很可能”仅修饰模型推断，不能把它变成适用资料结论。`B agent/prompts/decision.md:5` 明确不得编造 causes，`validation.md:3` 对任何无据事实断言应拒绝；Spec:366/369、AC-007的可追溯有据回复仍不匹配。

实际response06却supported=true，理由称无unsupported assertions，漏掉前导因果陈述，只讨论后面合格的yes/no与Falls ja条件问句。`B agent/graph.py:176/200/219` 保存该normalized全文授权，`application/commit_outcome.py:36/88/92`按相同hash提交，最终模拟出站正文精确包含该句。6fresh HTTP/4tools/22,979tokens/45,750ms/unknown0/1出站，无第7HTTP；工程completed并不等于业务语义PASS。已向主Agent/真实评测worker先行反馈FAIL禁止后继gate，全部20raw SHA和当前source snapshot保存在[独立H-11反例](artifacts/phase7/review-3-business-semantic-checks.json)。旧195403 H-10、194850 PASS和全部旧FAIL均保持，后四边界不能以未执行工程结果填PASS。

201501 H-11后控制预案的独立窄范围PASS：重读 `agent-eval/prepare_cause_controls.py:27/65/91` 与原req06、两份完整prepared，重新构造逐字段比较；negative的完整user字节不变，positive仅`draft.body`和`draft.claims[2].text`各删除同一完整原因句一次，其余DATA/schema/claims来源/知识/问题全部相同。尾system仅为当前原尾加一换行和通用planned cause规则，首system原样。两代理14,384/14,184、预留32,568，0DB/0HTTP；原文件SHA与本审H11冻结相符。[独立预案审计](artifacts/phase7/review-3-cause-preflight-audit.json)。当前生产尾尚未后修，不能据planned版本称产品PASS或放行付费；落地/PG后须核实际源尾SHA与prepared完整尾一致再验正负控制。独立最新[19项eval](artifacts/phase7/review-3-cause-eval-tests.txt)1.661s/OK/0skip，包含原实际草稿的精确两字段删除及缺句/重复句拒绝。即使控制通过仍仅已知材料边界诊断，新德文及后四业务目标另验，H-11不提前关闭。

H-11后实际source独立工程通过：全文重新读取generation grounding/validation-grounding及Graph专用repairhint。生产validation首不变，`prompt()` 返回的实际尾system文本UTF-8 SHA `91c1f65a27b14bac1002acbb3c017037e2bb0946c6dca4495d721c994f56fdd4` 精确等于201501两份prepared的planned完整尾文本。该值不是raw源文件字节SHA：`Path.read_text`按Python通用换行将CRLF读成LF；artifact的 `source_sha256` 使用read_bytes另记录raw文件SHA，最终源码对比使用后者。全部旧条件问句/时态/ledger/执行/产品依据规则仍在，只追加通用症状与诊断原因/概率区分。generation提醒不得自推原因；current-or-historical订单源repair措辞关闭先前LOW精度问题，来源门未变。[独立源码/预算核对](artifacts/phase7/review-3-cause-source-check.json)。当前[19项真实PG](artifacts/phase7/review-3-cause-rule-tests.txt)54.981s/OK/exit0/0skip，[before-after源码SHA](artifacts/phase7/review-3-cause-rule-tests-snapshot.json)完全相同，[compileall](artifacts/phase7/review-3-cause-rule-compile.txt)exit0。覆盖新旧草稿协议、来源早验、一次repair、全文核验/hash、最后额度与菜单压力；只确认工程可按主Agent授权做2实际判界控制，H-11及新完整业务仍待，不提前Stage1 PASS。

202127两实际cause控制的独立窄范围PASS：两份完整actualresponse逐字人工读，negative精确列出原probable-connection句并拒绝，positive准确接受中性配对是否问句及Falls ja条件观察，没有要求客户先回答才能补问。逐字段比对两actual request=201501 prepared，SDK全messages/schema一致且仅允许字段；当前全部source SHA匹配paid manifest，首/尾运行文本来自当前源文件。2实际HTTP/7,822tokens/14,750ms（网络request记录14.516s，外层还含客户端初始化开销）、unknown0/0业务/原cycle计数不变，[独立全文/SDK/出处审计](artifacts/phase7/review-3-cause-actual-check.json)冻结12raw SHA。positive仍是明确删句的合成对照，不是新模型生成稿；已向root确认一次fresh德文及后四边界的有条件工程前提，H-11仍需新完整业务匹配后关闭。

202431 P7-05德文新完整真实核心PASS：独立读五actualresponse、完整validation DATA、全部持久order/完整SOP/ref/draft/artifact/时间线。首次理解来源与订单数字quote精确，正文仅复述客户已知故障和新电池，询问是否曾配对与Falls ja条件下灯本体/红灯现象；没有原因/概率诊断、重复电池要求、未经适用核准的通电步骤或履约承诺。全部SDK messages/schema/tools/tool_choice按本次声明一致，当前source SHA匹配paid manifest，五usage总和等于cycle。raw claims-only原顺序/原文本精确join、UUID5真实凭证、送审全文及唯一出站完全相同。5fresh HTTP/3tools/18,425tokens/40,578ms/unknown0/1出站，17raw SHA保存[独立业务gate](artifacts/phase7/review-3-business-semantic-checks.json)。本冻结德文的H-10/H-11反例在新版本关闭，195403/200822原FAIL和实际出站不删除；这不证明模型普遍正确，其余四边界另审。

**H-12 / HIGH，202431 P7-06真实条件退款未保留。** 已独立全文读全部5份actualresponse、原客户request01、全部决策/核验DATA与持久record。Spec:480要求多诉求、条件及选择，AC-046 / Spec:489明确“当前查询关联物流，记录退款条件”。实际客户原文完整包含 `If it still does not arrive, I will want a refund then, but I am not asking you to refund it now.`，B`agent/prompts/understanding.md:1/3`当时亦明确保留条件未来偏好且conditional refund须consent=conditional。然而response01与持久initial/current只保留一个troubleshooting intent、condition=null、consent=none，revisions=[]；shipment分类也失准。order+shipment真实读取成功，仍不能代替丢失的未来退款意图。最终回复仅通报物流/再问是否查更多，未记录或确认该条件。5fresh HTTP/3tools/16,841tokens/31,327ms/unknown0/1出站，原冻结conditional_refund断言不匹配；07–09没有任何HTTP。

**H-13 / HIGH，同一P7-06无据商品类型译名核验漏判后实际发送。** scoped查单的product_name是“朝天灯-四按键-美规-黑色”，客户原文只有parcel；没有适用资料或英语类型字段支持 `OUTON ceiling light`。实际response04的order_fact正文自行加入该类型，并仅引用物流command（该command没有商品类型）。完整response05却supported=true/unsupported=[]，称没有任何无据事实；B`agent/graph.py:176/195/200/219`与`application/commit_outcome.py:36/88/92`按同一normalized全文/hash合法提交，唯一实际模拟出站包含ceiling light。属于生成及语义核验共同漏判，未损坏claims组装/覆盖协议。查单物流值及未写交易只作工程局部通过，不改变有据回复FAIL。17份原raw SHA、5项SDK字段/完整schema和输入预算复算、逐字draft→送审→artifact→出站链见[独立H12/H13证据](artifacts/phase7/review-3-conditional-refund-failure.json)。证据保留202431当时manifest SHA；审计结束时understanding.py已后修，另列later_changed_source，未把新源覆盖成旧版反例。

203514零HTTP预案独立工程通过：全文阅读 `agent-eval/prepare_request_controls.py:19/61` 与 `test_request_controls.py:16/32`，不调用helper重新构造对照。negative整份请求仅尾追加planned通用规则、完整user字节与schema原样；positive严格只改商品prefix于body/claim1.text并追加原客户未来条件段及其customer_fact，共4operations。其余全部DATA、物流/订单及错误旧Understanding不变，21可信原SHA与本审反例一致；代理13,445/13,688，预留31,133。[独立预案](artifacts/phase7/review-3-request-preflight-audit.json)，[独立21项eval原始输出](artifacts/phase7/review-3-request-controls-eval-tests.txt)1.642s/OK/0skip。显式合成正稿不证明理解或真实业务通过，原202431 H12/H13保留。

最新请求规则源码的Stage1工程重核：全文重读B`agent/understanding.py:17/21/48`专属schema描述、`prompts/understanding.md:7/9`逐请求类别及未来/not-now、decision完整诉求、grounding通用商品称呼、validation尾部原邮件独立完整性及译名。删除schema的description再比较，所有结构/必填/枚举/长度限制与原request01精确相同；来源/风险/authority/Graph菜单/预算/claims组装/hash/末门不变。实际首system/尾system与两prepared逐字相等，运行尾文本SHA `c01aa204…42891`（LF文本摘要，raw文件SHA另列）和两代理与预案一致。[独立源码核对](artifacts/phase7/review-3-request-source-check.json)。[独立31项真实PG](artifacts/phase7/review-3-request-rules-tests.txt)68.671s/OK/exit0/0skip，[全src/prompts/tests SHA](artifacts/phase7/review-3-request-rules-tests-snapshot.json)运行前后完全相同；覆盖新旧草稿/早来源门/全文语义与hash、原菜单压力、9项修订/CAS/风险权、条件/身份/多商品。[compileall](artifacts/phase7/review-3-request-rules-compile.txt)exit0。只确认已授权两实际控制工程前提，不凭Scripted证明语义或关闭H12/H13；控制及fresh06/后三案仍待。root旧258项773.268s全量已保存为before-request-rules，未当作该新源码最终验收。

204212独立真实负控制FAIL，后修仍未关闭H12/H13：全文实际response仍supported=true/unsupported=[]，理由只核对物流字段和neutral closing，声称未处理退款却不核未来选择，也未发现ceiling light类型添加。actual完整request与本审203514negative逐字段相等，SDK完整messages/schema及允许字段一致，21原SHA不变、付费manifest源码前后相同；1实际HTTP/3,604tokens/5,967活动ms（adapter 5.890s）/0业务/原cycle未追加。5raw SHA见[独立负控制证据](artifacts/phase7/review-3-request-control-negative-failure.json)。`agent-eval/run_request_controls.py:18/79/98/116/144`新runner已全文读，失败/unknown/source变化和精确negative response SHA门阻止positive，unknown收费保守保留；`test_request_control_runner.py:29/44`负门前提也已读。positive未调用，fresh06及07–09继续待。已反馈主Agent，未因工程PASS或尾规则存在改判语义PASS。

独立新runner[4项门控测试](artifacts/phase7/review-3-request-control-runner-tests.txt)0.016s/OK/exit0：失败/unknown/source-change负控制、不同raw response的语义门以及bool充当token均不放行。这只证明评测停止/出处规则，没有替代actual负控制FAIL。

对于主Agent提出的schema理由先行方案，审查者已重读B`agent/outcome_validation.py:9`与Provider直传schema。保持相同字段、类型、required集合、20项/1500字限制、原Graph判决AND门时，改变property顺序/description可兼容旧JSON；须从新actual SDK确认真正送出schema顺序。官方[Structured output](https://help.aliyun.com/en/model-studio/qwen-structured-output)描述的是输出结构/类型控制；本审未找到保证字段先后导致语义正确的承诺。因此“先true后理由合理化”只是待检验诊断，新顺序也只是假设，不能在实际正负原文/新业务前关闭H12/H13。后续预案、源码、预算及实际结果另冻，不覆当前FAIL。

205035新schema-only预案独立工程通过：全文读B`agent/outcome_validation.py:9`、`agent-eval/prepare_review_schema_controls.py:23/50/95`及其两反例。相对203514只替换schema，完整messages/head/user/tail、工具/timeout逐字不变，原错under和四operations合成正稿保持。独立验证34可信raw SHA、产品源SHA、properties与required的显式顺序为reason→unsupported_claims→supported→language_correct；前三字段只增加description，各字段类型、必填集合、20项/1500长度、extra=false和其余schema逐字段不变。旧actual JSON仍可parse，预算代理14,128/14,371，预留32,499。[独立预案/顺序审计](artifacts/phase7/review-3-review-schema-preflight.json)。注意sorted canonical SHA或dict相等不能证明property顺序，本审另比较list(properties)，后续actual SDK仍须实际检查。新[19项真实PG](artifacts/phase7/review-3-review-schema-tests.txt)46.942s/OK/exit0/0skip、[全src/prompts/tests before-after](artifacts/phase7/review-3-review-schema-tests-snapshot.json)稳定；[两schema反例](artifacts/phase7/review-3-review-schema-eval-tests.txt)0.002s/OK、[compileall](artifacts/phase7/review-3-review-schema-compile.txt)exit0。工程前提通过，机制改善/实际正负控制与新06仍未证实，H12/H13未关闭。

205412新reason-first实际负控制仍FAIL：独立人工阅读全文response和SDK，明确实际schema properties及required顺序、新描述和response字段顺序都已送出/遵守；完整actualrequest精确等205035prepared，34可信raw SHA/前后源码相同。reason仍只确认订单/物流和不立即退款，笼统称“尊重客户条件”，没有核对未来退款承接，也漏商品ceiling light添加；另把tool source_ids误说成citation_ids（真实citation_ids=[]）。实际supported=true/unsupported=[]，1HTTP/3,602tokens/6,282活动ms/0业务，[独立顺序及反例证据](artifacts/phase7/review-3-review-schema-negative-failure.json)冻结5raw SHA。假设正确送出不等于改善已证，不能关闭H12/H13；positive、fresh06和07–09均未调用，未扩大预算或重写此前204212/202431失败。

主Agent在205412后暂停付费重审机制，本审按授权完成[只读独立诊断](artifacts/phase7/review-3-validator-diagnosis.md)：逐claim/原邮件审项可加强精确出处与缺项拒绝，但引用和字符覆盖不能证明语义分解/映射/译名蕴含，不能用模型自报kind构造伪授权。服务端期望claim索引应来自真实草稿，原邮件期望不能来自已漏项的Understanding；需保留合法背景/撤回/条件问句和2k输出边界。另对两个真实观察进行零HTTP无损parsed JSON形状比较，全部字段canonical roundtrip精确、其他DATA不变，输入代理14,128→13,548，见[格式比较](artifacts/phase7/review-3-observation-shape-diagnosis.json)。这只证明可无损节省580代理字符，没有证据说明转义是漏判根因或解析必然修好；未修改产品、未付费、未进入Stage 2。

205412 后新逐项核验协议的 Stage 1 工程重核：已重新全文读 B`agent/review_audit.py:9/27/39/59`、`outcome_validation.py:10`、`graph.py:176/194/201`、`context.py:16` 和 validation 首/尾提示，以及显式 `tests/agent_review_fixture.py:6`。服务端从原 trigger 正文无损派生单位，要求每个单位/claim 索引恰一项；漏项、重复、越界、负项、草稿中不存在的回复 quote、非当前/非 claim 来源及假 source quote 均不能被顶层 true 覆盖。原完整 context/错旧理解/工具观察/草稿不删，源早验、全文覆盖、一次 repair、预算、精确 hash 与 Commit 全门保留；text/2、text-graph/2 是新契约标记，原四字段实际响应不补新数组。`agent-eval/legacy_review.py:5` 在旧 history 初始化、Embedding/DB 前明确拒绝不兼容记录；历史原语义标签仅保留当期范围。

独立 [41项协议与真实PG原始输出](artifacts/phase7/review-3-item-audit-tests.txt) 64.968s/OK/exit0/0skip，[全src/prompts/tests运行快照](artifacts/phase7/review-3-item-audit-tests-snapshot.json) 前后稳定。额外由本审临时测试走真实 Graph：空正文已有 scoped operation 等待通过真实 validation/Commit、0邮件；不存在 operation 被末门拒绝，0等待/0artifact；真实来源ID配伪 quote 两次拒绝，validated_hash 一直为空、0出站。另 [14项eval](artifacts/phase7/review-3-item-audit-eval-tests.txt) 0.056s/OK/0skip 和 [compileall](artifacts/phase7/review-3-item-audit-compile.txt) exit0。这里的新审项由工程 Scripted fixture 明确构造，只证明拒绝/绑定/事务协议，不能证明 Qwen 自然语义正确。

该批包含 `test_agent_review_audit.py:77` 的错误礼貌正例：保留“The parcel is in transit.”事实正文，仅改 kind=clarification/空来源，不能当作纯礼貌合法输入；已先反馈主Agent，主Agent确认须另改真实 greeting 前提，当前运行日志与快照保留修正前版本，不称最终测试。真正事实的 supported、条件单位的 context 分类、quote 对整段属性的蕴含仍由独立模型判读。0HTTP反例证实把活跃条件误标 context、把含事实段标 clarification 并给 true，机械出处门仍可通过；因此精确来源门是必要条件，不能被描述为语义形式证明。

211045 新预案的独立出处/预算复算通过，但 **付费控制前提未通过**：[独立45可信SHA与完整审计](artifacts/phase7/review-3-item-audit-preflight.json)。两份 prepared 相对205035只换当前 schema/首 system 和无损 trigger_units，原 DATA 逐字段相同，三单位合并精确等原邮件；原尾文本SHA `c01aa204…42891`、源码快照、显式 required/property 顺序和代理15,378/15,621、预留34,999均一致。正稿仍保留 claim[2] “system shows ... in transit, you mentioned it has not arrived”两项事实却 source_ids=[]；当前首提示只允许无事实问题空证据，quote又必须属于该claim真实来源，因此这不是新出处协议的合法纯问题正例。claim[0]“checked shipment”仅引order凭证也须完整核定。已同步root/真实worker保持0付费，原211045不改写；若增来源修正，须另冻显式新变体，不可偷偷改原对照或以提案kind豁免事实。

容量限制也已有0HTTP实测：287字、41个“Hello.”派生41单位，完整41项输出被 `outcome_validation.py:11` 的max40拒绝；截成40项又被 `review_audit.py:62` 的完整性门拒绝。没有截短原文或提高预算，这个短信也说明合法输入不等于任意句数都可完整审计；2k输出和复杂来源摘录容量仍须明确失败/业务回归，不能假定schema存在就已覆盖全部合法长信。当前H12/H13未关闭，新actual正负和fresh06–09未运行，Stage 2未执行。

逐项协议容量/礼貌后修独立重核通过：current `outcome_validation.py:11` 只移除 request_checks 人为max40，required/property顺序、其他字段类型及source_checks原30、reason1500、unsupported20边界逐字段不变；原完整单位索引门与provider2000输出/finish-length及Budget超量门保持。`test_agent_review_audit.py:77/88` 已改为真正Hello原信、Thank you纯礼貌正文/context单位/空来源；41全单位能通过，少最后一项仍拒绝。主Agent首次41夹具仍留原customer_fact/旧quote的FAIL原始输出保留，本审全文读修前FAIL和修后用例，不把其当产品缺陷或伪装最终PASS。

修后 [17项独立测试](artifacts/phase7/review-3-item-audit-fixed-tests.txt) 11.416s/OK/exit0/0skip，[全src/prompts/tests before-after](artifacts/phase7/review-3-item-audit-fixed-tests-snapshot.json) 完全稳定，含14模块用例和本审三项真实Graph/PG。另 [零HTTP独立schema/41单位核对](artifacts/phase7/review-3-item-audit-fixed-source.json) 逐字段记录差异及原authority门源码SHA。原41单位被max40阻止是211045当期配置，当前已不再有该人工句数限；无法在2k内完整输出的真实情况仍须明确失败，不能截断输入/数组、加请求或伪造HITL。新positive出处变体及actual控制仍待，H12/H13未关闭。

212036 新出处正对照的独立零HTTP工程门通过：不调用准备helper重新构造两份完整request，核对51可信raw文件及所有当前源码/冻结输入SHA。negative原202431完整DATA/坏稿不改；positive相对203514原合成正稿只增加claim[0]物流command来源、将含物流/客户事实的claim[2]标order_fact并列原物流command与原客户ID，恰3项元数据变化。正文和每条claim.text逐字不变，全部non-draft DATA、旧错误Understanding及完整观察仍相同。新增来源逐字段对应原真实持久成功scoped订单/物流凭证及客户正文，未靠猜测ID或补写模型响应。

[独立全字段/来源/SDK预检](artifacts/phase7/review-3-item-audit-source-repaired-preflight.json)记录两代理15,364/15,742及预留35,106；当前六字段properties与required顺序、无max40、strict schema准确。使用不初始化网络客户端的捕获对象调用当前Provider，全文messages/schema、.7/nonthinking/2000输出及≤30秒均匹配；0HTTP/0DB/0业务。独立[15项eval门回归](artifacts/phase7/review-3-item-audit-source-repaired-eval-tests.txt)0.054s/OK/exit0/0skip。只向主Agent确认已授权的一次actual negative工程前提，完成后须暂停全文双审；positive/fresh06尚不放行。正对照现有真实来源可供逐项审计，不等于模型已正确理解或自然语义PASS，H12/H13保持开放。

212722 恰一次actual negative的结论分层：实际model仍supported=true/unsupported=[]，unit2把未来退款/not-now错映到无关delivery-details问句，ceiling subtype被称合法翻译，含真实事实段被称无需来源的clarification；模型语义FAIL。当前产品绑定则正确拒绝：3个quote均不是原canonical来源连续片段，claim1第二来源同时不属于该claim声明source_ids；`B agent/review_audit.py:59/84/86` 的audit_accepts=false，`graph.py:202/204` effective AND=false。因此不能描述为本次Graph放行或实际出站。1HTTP/4,366tokens/17,702活动ms/0业务，positive/fresh06均0HTTP；完整SDK、六字段顺序、51可信SHA及当期全文输入已独立复算，[实际分层证据](artifacts/phase7/review-3-item-audit-negative-actual.json)。冻结控制要求的实质负判仍未匹配，H12/H13未关闭。

[只读机制诊断](artifacts/phase7/review-3-item-audit-mechanism-diagnosis.md)与[0HTTP比较/反例](artifacts/phase7/review-3-item-audit-mechanism-diagnosis.json)记录：仅把两观察content无损parsed、其余DATA/首尾/schema不变，输入15,364→14,784、15,742→15,162；只是格式候选，不证明锚定或转义导致语义错。实际伪重构JSON提供了引用协议问题的新证据。明确机械反例只在内存纠正两个quote并删除未声明来源，坏稿/错unit映射/模型true不变，binding即能通过；因此引用格式改善不等于条件/译名蕴含正确。`B agent/graph.py:209/218` binding拒绝却把affirmative review.reason交给草稿repair，丢失程序失败位置，属于具体反馈缺口；审查者未修产品或授权付费。

已独立读取root [反馈修复前全量原始输出](artifacts/phase7/backend-tests-before-audit-feedback.txt)：272 tests/530.155s/OK/0skip，并逐项比较[运行快照](artifacts/phase7/backend-tests-before-audit-feedback-snapshot.json)before=after=当时全部backend源码/提示/测试/migrations/lock。主Agent随后原字节归档为该修前版本；该工程全量通过不能替代当前负控制语义FAIL或尚未完成的fresh06–09，Stage 2仍未执行。

确定性反馈初版后修的独立复现仍有范围偏差：`audit_failure`也将合法绑定下的request omitted/changed_condition及claim supported=false当成audit_error，Graph因此同时丢掉正常模型语义拒绝的具体reason，与源架构“模型语义拒绝仍使用原reason”不符。本审新增三条真实PG分别覆盖全局false/逐claimfalse/请求omitted；[21项23.899s原始日志](artifacts/phase7/review-3-audit-feedback-tests.txt)中后两项准确FAIL、全局false保持reasonPASS，[运行前后SHA](artifacts/phase7/review-3-audit-feedback-tests-snapshot.json)稳定。真binding伪quote不再传错误批准reason、完整索引及空正文既有scoped等待/未知operation拒绝仍PASS。主Agent已接受需typed区分binding与semantic，先完整扫描绑定再处理语义负项；后修新源另验，不覆该初版FAIL或将其当语义HIGH已经关闭。

typed反馈后修工程独立通过：重新全文读 `B agent/review_audit.py:29/66/99` 的AuditFailure(code,binding)及 `graph.py:202/209`。所有索引/回复quote/证据绑定先核对，binding失败优先，即使较早模型项已omitted或claimfalse也不能掩盖；合法绑定的语义负项保留具体review.reason，真binding错误仅传实际代码。原bool audit_accepts、schema/全部prompt/原一次repair与预算/最后hash门保持。

[22项独立真实PG](artifacts/phase7/review-3-audit-feedback-final-tests.txt)22.997s/OK/exit0/0skip，[全src/prompts/tests快照](artifacts/phase7/review-3-audit-feedback-final-tests-snapshot.json)前后稳定。三条额外全局false/claimfalse/请求omitted分支现在均保具体语义reason，真binding拒绝不再传错误批准；无正文已存在scoped operation等待及未知operation末门拒绝保持。另[15项0HTTP API检查](artifacts/phase7/review-3-audit-feedback-api-check.json)核typed code/flags/wrapper一致、极大越界不IndexError及晚到binding覆盖早semantic，[compileall](artifacts/phase7/review-3-audit-feedback-compile.txt)exit0。初版21项2FAIL与root错误addressed-empty-quote夹具日志均另保；该反馈工程缺口在此源码关闭，H12/H13不因此关闭。

主Agent提出仅核验节点的有界thinking候选，目前尚未实施/HTTP；本审仅完成[官方接口与本地预算只读评估](artifacts/phase7/review-3-thinking-candidate-readonly.md)，指出DEV-PLAN当期nonthinking契约、总推理+答案2k门、1990的10-token容差、必须实际SDK捕获总限制且不可减免推理账。用户契约授权、事前预案及actual语义结果另审，未将候选模式或官方一般能力写成已修复。

`planned-review-thinking-512`两完整候选SDK预案的[独立0HTTP预检](artifacts/phase7/review-3-thinking-proposal-preflight.json)通过，结论明确仅候选结构：独立重构全部payload，messages/完整user DATA/schema/原source角色逐字等212036，仅enable_thinking、thinking_budget512、max_tokens→max_completion_tokens1990三参数变化。prior manifest、212722原actual response、51可信旧SHA及当前typed源码全部相等；六字段顺序、无max40、原timeout30/.7/重试0、两输入15,364/15,742与预留35,106核定，1990+官方10-token容差不超过2000，512不能另加到输出预算。当前产品仍非thinking，没有候选actual SDK或HTTP；用户对DEV-PLAN契约变更尚未回复，预检没有代替授权或质量验证。

隔离浏览器收尾仅关闭本审查者自有 `phase7-review` CLI 会话：[原始 close 结果](artifacts/phase7/review-3-ui-close.txt)，exit0，输出 `Browser 'phase7-review' closed`。已保存截图和所有审查证据保留；root-owned 服务/CLI 及正式 Phase6 服务未由本审操作。审查实例继续活跃等待契约授权与后续实测，Stage 2 邻居实渲仍须通过 Stage 1 后重新启动隔离场景核对。

当时 typed-feedback 源的后端全量工程证据已完成并独立核原始输出：[274项/542.232s/OK，后归档](artifacts/phase7/backend-tests-before-thinking-workflow-contract-274.txt)，0失败/0错误/0跳过。本审对[当时运行快照，后归档](artifacts/phase7/backend-tests-before-thinking-workflow-contract-274-snapshot.json)全部179个源码/提示/测试/migrations/lock的before、after及当时文件原字节SHA逐项比较完全相等，并核原始日志274个测试入口及最终总数；[独立复算](artifacts/phase7/review-3-current-full-verification.json)保存原证据SHA，不重复运行同源全量。未将当时工程final文件名等同本轮Stage 1或真实业务最终通过。

已全文读取主Agent[正式库只读保旧/清理证据](artifacts/phase7/formal-current-readonly.json)：仍0005、54总表/53旧业务表，全部旧表列行SHA、设置与160原件字节保持；知识22资料/22版本，build/release/cache为0，formal-before未改。四端口当前均未监听，root-owned临时schema/对象已清理，正式服务没有重启/升级。此处明确为主Agent只读查询的产物核对，本审没有另查询正式库或把它写成Phase7发布验证。候选thinking仍等用户契约授权，0新HTTP；H12/H13继续保留，Stage 2未开始。

主Agent随后同步用户明确授权“那你根据你的方案继续调整一下吧 尽快结束 Phase7”，本期仅核验节点有界thinking候选及后续验收可继续，复用审查实例许可保持。本审不重复已核同份0HTTP预案；等待源文档/profile/实际SDK捕获冻结后独立核定：理解/decision仍nonthinking，512为推理子限额，推理与回答共用原2k账，原6/12/120/16k/80k/30秒及.7/retry0保持。actual negative须明确拒原客户条件遗漏与无据译名，quote程序门拒绝不能替代模型语义负判；首FAIL停止，positive及fresh06–09仍逐案全文双门，不重付已通过05或写正式库。当前未将授权写成实现、HTTP或质量通过。

获准的核验专属profile现已落地并完成工程独审：全文重读 `B adapters/model_provider.py:8/25`、`agent/graph.py:45/195`、`agent/budget.py:38/60` 及eval recording/bootstrap。只在服务端OutcomeReview schema且无tools时选择true/512/1990，其余理解/工具生成使用false/2000；实际SDK捕获新增总输出参数、阶段采样和原usage，reasoning_content保留于私有raw，不进入Graph业务状态或前端回复。Budget按供应商completion总数结算，不额外加或减reasoning子项；原finish-length拒绝、超2000记录实际消耗后拒绝、一次repair与所有最终提交门未放宽。DEV-PLAN:348/Architecture:304/实施记录:5及eval README:33已明确模式和版本边界。

新223750[独立54可信来源/实际适配器零HTTP预检](artifacts/phase7/review-3-thinking-authorized-preflight.json)通过：两完整212036请求原字节不改，当前六字段properties/required顺序、首尾、业务原文/schema都保持，capture逐字段等原已批准候选；输入15,364/15,742、预留35,106，1990+10≤2000，512仅子限额。独立[10项SDK/真实PG](artifacts/phase7/review-3-thinking-profile-tests.txt)6.828s/OK/0skip，[源码/测试快照](artifacts/phase7/review-3-thinking-profile-tests-snapshot.json)稳定。三项额外真实PG明确验证completion含512推理总数只结算一次、即使完整工程审计但finish=length也不授权、completion2001保留真实消耗却0out；[compileall原始输出](artifacts/phase7/review-3-thinking-profile-compile.txt)为空、exit0。主Agent[73项专项](artifacts/phase7/review-thinking-tests.txt)39.747s/OK/0skip的原始日志已全文核对，运行before=after；后续只有README默认/核验分列修正使其当前文档SHA变化，产品源码不变，未混称整份当前snapshot全部相等。这里只放行已授权的一次actual negative工程前提，完成后暂停全文双审，positive/业务未提前放行，H12/H13仍开放。

224147核验有界thinking首次actual negative仍首FAIL停：[独立完整request/最终JSON/实际SDK及54可信来源审计](artifacts/phase7/review-3-thinking-negative-actual.json)。1HTTP、3,571输入+1,299总输出=4,870tokens，总输出已含512reasoning，24.875秒适配器/25,030活动ms，cached0、source_changed=false、原预算内、0业务/positive及fresh06–09均0HTTP。实际schema/profile/messages与223750准备逐字段一致，原请求/资料和目标没改，私有推理文本只保raw与SHA，不导出。

本次模型supported=false、unit2=changed_condition，最终reason明确解释未来refund及not-now被遗漏，H12原控制有局部进展；但含无据“ceiling light”整段claim1仍supported=true，含物流/客户事实的claim2空证据仍true，unsupported_claims=[]，H13未匹配。商品quote原Unicode确为“朝天灯-四按键-美规-黑色”，终端乱码只是显示编码，不能诊断为原文损坏或没看到来源。三quote均重构为label:value而非当前canonical来源连续片段，claim1另引未声明order来源；typed audit先返回claim_0_quote_not_in_source，binding/effective拒绝正确，不能代替双缺陷自然语义负判。模型总false、程序拒绝及原预算内都没有使该控制成为PASS。

已给主Agent下一步只读判断：可以把“先逐claim/逐属性证据判界、再完整原mail诉求/条件”作为受控任务顺序假设，保两独立否决轴、全部审项/正文及exact source绑定；尚无证据证明仅去双重转义能修商品含义错判，也不把思考模式写成质量证明。礼貌/中性If-so条件问句、当前scope、计划≠执行、观察≠原因及2k输出容量均须回归。源更新/0HTTP新准备及一次actual控制另审，不继续同配置随机复验，不放行positive/真实业务，H12/H13保持开放。

text/3 source-first任务后修的工程预检通过：[独立59可信raw/全字段diff与实际适配器capture](artifacts/phase7/review-3-workflow-preflight.json)。全文重读当前validation.md、context.py和准备helper，独立重构两个完整request，仅首system的任务段重写及原source/request两段互换；其余每段、tail/schema、原DATA/旧错Under/草稿/来源都逐字保留。当前SDK仅换同一head，true/512/1990/.7/30秒/retry0保持。输入15,406/15,784、原两控制预留35,190，无输入截断/上限扩大。相对typed反馈274项源码，产品路径只已审provider、context版本label、validation头三项变化，其他Budget/Graph/引用/末提交门原SHA保持。

独立[4项最小真实PG](artifacts/phase7/review-3-workflow-tests.txt)10.136s/OK/0skip，[运行前后快照](artifacts/phase7/review-3-workflow-tests-snapshot.json)稳定，覆盖双终局超16k仍合法human、human也超门不伪造接管、未声明工具不执行及完整read观察正文保留；[compileall原始输出](artifacts/phase7/review-3-workflow-compile.txt)为空、exit0。这里只确认再次有因的一次actual negative工程前提；工作顺序假设没有语义证明，任一原错误仍漏判即停止，positive/fresh尚未放行，H12/H13和Stage 1 FAIL保持。

225432 text/3实际negative的全文门仍FAIL：[独立request/SDK/59原来源及最终审项审计](artifacts/phase7/review-3-workflow-negative-actual.json)。1HTTP、3,577输入+1,455总输出=5,032tokens（输出含512推理）、31,358活动ms，SDK实际31.25秒；这是实际耗时，不能写成每次网络必然≤30秒，SDK配置仍timeout30。当前120秒总活动门在 `B worker/agent_runner.py:84` 提交前另行检查。实际paid源码before=after，等本审225009快照；其后三个schema/context后修路径单列，未混用当前text/4判旧请求出处。

本次总supported=false、claim1=false及理由指出错误类型和未来refund遗漏有局部进展，但unit2仍addressed并把解释串当reply_quote，与理由自相矛盾。三个request quote都不是草稿连续原文；含物流/客户事实的claim2仍true/空证据，claim1另引未声明来源，typed门首先拒 `request_unit_0_reply_quote_not_in_draft`。本轮六条source quote均是canonical来源精确片段，已改正此前“仍伪重构quote”的初步备注；不能因早期引用失败推测本次也同因。理由另指未写four-key，该属性并非客户当前回复必须复述的内容，不应强制成为新要求。runner全部检查true不等于独立全文PASS，positive与fresh06–09继续0HTTP，H12/H13未关闭。

text/4局部字段合同的0HTTP工程门通过：[独立64可信raw、完整有序schema/SDK/预算检查](artifacts/phase7/review-3-contract-preflight.json)。重新全文读 `B agent/review_audit.py:10/22`、`outcome_validation.py:10`、`context.py:16` 和 `agent-eval/prepare_review_contract_controls.py:19`，只将properties/required改为source_checks→request_checks，再增加status、reply_quote、supported三条局部description；所有字段类型、必填集合、长度/数量边界、additionalProperties及其他嵌套字段顺序相同，没有max40。完整messages/head/user-DATA/tail、正负草稿/原错Understanding和资料逐字等225009；当前适配器Mock capture除同一schema变化外与旧实际计划全字段相等，true/512/1990/.7/timeout30/retry0未变。现场64源码运行前后SHA相同，inputs15,615/15,993、实际余量385/7、两控制预留35,608。只确认下一次获准negative工程前提，不凭输出顺序证明思考或语义正确，不重复无关已绿PG。

225934预案保留了部分旧继承元数据：顶层code_snapshot_after仍text/3（三路径SHA），input_headroom仍594/216，旧reserved_tokens_for_two_future_controls仍35,190；新的original_budget_preflight为正确35,608。已即时反馈root，要求新的paid manifest现场冻结before/after并附勘误，不改原准备文件历史。本审自行按当前原字节计算稳定快照和真实385/7余量，不依赖旧after或sorted hash证明顺序。原绑定/一次repair/hash/预算门保持，此候选仍需唯一negative全文双审；positive/业务尚未放行，Stage 2未开始。

随后root另建230632勘误预案，原225934不变：[独立65可信来源及元数据勘误](artifacts/phase7/review-3-contract-preflight-errata.json)。两完整prepared request与SDK文件原字节均等225934，新的现场before=after=current，余量385/7和预留35,608准确；只修准备helper的元数据继承问题，没有后端源码或业务材料变更。本审另核[root41项原始日志](artifacts/phase7/review-contract-tests.txt)72.979s/OK/0skip及[179文件运行快照](artifacts/phase7/review-contract-tests-snapshot.json)before、after、当前原字节SHA全相等。只确认一次negative的工程前提，不重跑未变路径；完成后仍须全文双审再决定positive，Stage 1未改判。

230652 text/4唯一actual negative的独立全文门仍FAIL：[65原可信来源/现场源码/实际SDK及全审项](artifacts/phase7/review-3-contract-negative-actual.json)。1HTTP、3,577输入+1,510总输出=5,087tokens（含512推理）、28.313秒SDK/28,405活动ms，cached0、原预算内、0业务。实际source-first顺序及三描述正确送出，全部材料/旧错Under原样，不是配置或来源文件变化。unit2的reply quote确为草稿片段，但只是物流补问，模型仍addressed并称未来条件已满足；这是语义错映。claim1=false却明确认可ceiling译名，改因不复述four-key/US/black否决，不能作为H13匹配；claim2混合事实仍true/空证据。

本次三条source quote又重构字段/空格并拼多字段，不是canonical来源连续摘录，claim1还越声明来源；request1跨段用空格也不连续。typed审计首码为 `request_unit_1_reply_quote_not_in_draft`，程序拒绝正确，但model总false/unsupported一段/runner11项true不代替自然语义双目标。positive、fresh06及07–09保持0HTTP。[只读机制诊断](artifacts/phase7/review-3-contract-mechanism-diagnosis.md)指出无损parsed表示只能作为引用协议假设，225432引用全精确仍漏语义已经反证“精确quote就证明正确”；不再建议同类警句或schema顺序小改付费，不通过删材料/改原冻结目标宣布完成。Stage 1 FAIL及Stage 2未开始保持。

231517仅表示prototype的0HTTP工程门通过：[独立70可信原SHA/全字段roundtrip/SDK检查](artifacts/phase7/review-3-observation-preflight.json)。全文读 `agent-eval/review_observations.py:6/13`、`prepare_review_observation_controls.py:14`、`item_audit.py:6` 与3codec用例；独立从原JSON字符串重建完整对象，role/tool_call_id、所有receipt字段/Unicode/数值/null保留，canonical往返整个原user字串逐字等值，每个原scoped source ID及完整canonical正文同原audit_sources。其余DATA/错误Under/正负稿、head/tail/schema/profile不变，当前adapter Mock捕获只改变同一user表示；输入15,035/15,413，各省580代理字符，reserve34,448，原门不变。

全部后端产品原SHA保持，这只是eval表示prototype，Graph未接入/无业务提交。eval审计完整canonical还原再调用原绑定门，没有帮模型修quote或增加来源。独立[3codec测试原始输出](artifacts/phase7/review-3-observation-codec-tests.txt)通过，证明真实原文往返/来源映射及非canonical与坏JSON拒绝，非语义质量证明。只向root确认唯一negative的工程前提，结果须完整双错误全文门；正稿及接Graph/真实业务须依次另审，H12/H13仍开放。先前准备将json_bytes空格表示当产品canonical导致0HTTP roundtrip失败属于工程准备过程，不改成新模型质量FAIL。

text/4当前后端全量工程完成：[276项/548.623s/OK原始输出](artifacts/phase7/backend-tests-final.txt)，0失败/0错误/0跳过；[179文件before-after快照](artifacts/phase7/backend-tests-final-snapshot.json)与现场源码原字节SHA逐项全部相等，[独立复算](artifacts/phase7/review-3-text4-full-verification.json)。原始276测试入口中两故障用例中间输出预期安全日志，其ok另起一行，总计仍276成功；本审核定后未重复全量。该版产品Graph仍未接parsed表示，276工程PASS不关闭H12/H13，也没有使Stage 2开始。

231655无损parsed表示唯一actual negative整体FAIL：[独立70可信来源/完整request-SDK及DATA还原检查](artifacts/phase7/review-3-observation-negative-actual.json)。当前实际请求=231517prepared，整个原user canonical往返逐字相同，产品Graph/审计门没改；1HTTP、3,542输入+1,350总输出=4,892tokens（含512推理）、25.703秒SDK/25,780活动ms、source稳定、0业务。unit2仍把未来退款/not-now映到物流补问并称已满足；request1含省略号，三source quote去JSON标点/重排多字段且越声明来源，typed首码仍 `request_unit_1_reply_quote_not_in_draft`。claim2事实空证据true，binding拒绝不能替代语义门。

H13本次有局部进展：reason已经说英语subtype未明确核准/存在歧义，但仍把没复述four-key/US/black当“more importantly”错误否决前提；不得简化为已完全识别原类型问题，也不得说完全没提歧义。表示假设停止，Graph不接，positive/fresh06–09均0HTTP。主Agent随后提出需用户确认的核验容量契约候选（总输出4000、thinking2048、网络60秒且受原cycle120剩余限额）；该候选尚未落地/付费，不改变当前Stage 1 FAIL。本审指出必须同步服务端按阶段预留/结算/unknown额度，推理不另加或减账、finish-length与120秒提交前门保持；这只是资源假设，没有证据保证可修语义。

核验容量的具体0HTTP提案仅结构审通过：[独立完整SDK/预算/来源检查](artifacts/phase7/review-3-capacity-proposal-preflight.json)。70旧可信SHA及现场全部before/after源不变，完整parsed正负请求的messages/schema/head/tail/旧错Under/草稿保持；在内存暂替profile并Mock当前Adapter捕获，SDK仅1990→3990与512→2048，request仅timeout30→60，随后当前产品1990/512恢复。input15,035/15,413，按新4000总限额分别预留19,035/19,413，合计38,448。官方[Chat API](https://help.aliyun.com/en/model-studio/qwen-api-via-openai-chat-completions)明确max_completion_tokens涵盖推理与回答且最多10-token容差，因此3990+10≤4000、2048只为子限额；并没有语义改善或时延保证。

提案需要用户确认ASM-006输出/网络契约，不是本审授权。服务端分阶段reserve/unknown/settle4000、有效timeout=min(60,cycle剩余活动秒)尚未实施；其他节点2k/30、6请求/12工具/120活动秒/16k输入/80k累计、finish-length/过限拒绝和提交晚到栅栏均须保持。当前模型/profile及Graph没有变，0新增HTTP/0业务。现有512全部用满只提供容量可能不足的线索，不能作为2048必能修好的根因证据；负正完整判界及fresh业务仍待，Stage1/H12/H13保持未过。

当前root已就ASM-006容量契约向用户发问，尚未收到回答；本审没有将提案结构PASS当作许可。root当前[42项eval原始输出](artifacts/phase7/review-observation-eval-tests-current.txt)通过与276全量/静态门均属于工程证据，root另存231655最终FAIL为[root全文复核](artifacts/phase7/root-observation-negative-audit.json)。当前四端口无监听、正式库仍保旧、needs_review，未stage/commit/正式升级；本审继续保留本期获准复用实例等待同一Phase7闭环，不进入Stage2或重复未变测试。

2026-10-09用户随后明确“好的那你继续”，主Agent确认是对上一轮具体核验容量方案的授权。本审继续本次已获准复用实例，等待源文档/仅validation 4000总输出、2048思考及按stage计账/剩余活动超时实现冻结后独审。此处只记录授权，未写成配置已落地或语义PASS；schema/prompts/原parsed正负材料不变，先工程0HTTP再唯一negative全文双门，FAIL立即停止，不提前positive或接Graph。此前全部FAIL及276当期工程结论原样保留，H12/H13仍开放，Stage2未开始。

获准的2026-10-09容量修改已完成独立工程门审，当前label为text/5。重读 `B agent/budget.py:14/18/48/88`、`adapters/model_provider.py:8/25`、`agent/graph.py:54` 及 `worker/agent_runner.py:84`：仅validation按4000总输出预留/unknown保留/按持久stage结算，SDK 3990、thinking子限额2048；其他阶段2000/30/false/.7/retry0保持。网络timeout=min(stage 60或30,剩余120活动秒)，累计6请求/12工具/16k输入/80k及提交前120秒栅栏未放宽。推理是供应商completion总数的子项，未另加或扣减。源文档 Product-Spec:763、CHANGELOG:5、DEV-PLAN:348、Architecture:304及实施记录:5明确用户授权及同一资源边界。

最新074344-66a5c470的[独立75可信原件/全文SDK/预算预检](artifacts/phase7/review-3-capacity-authorized-preflight.json)通过，0HTTP/0业务：相对231517，两完整request只timeout30→60；SDK仅1990→3990、512→2048，所有messages、旧错Understanding、正负draft、完整资料、schema有序结构/head/tail及完整canonical来源正文逐字保持。input15,035/15,413、余量965/587、两控制预留38,448；旧34,448明确位于prior_observation_original_budget_preflight历史键，旧074135/074243准备原件保留。产品后端相对231517只budget、graph超时、context label、provider四路径变化；Graph仍使用原字符串observations，parsed仅eval实验，不声称已接入。

`agent-eval/run_request_controls.py:17/125/153`已将实际记录与受剩余时间限制的完整有效请求比较；61秒已耗时→59秒timeout，其余字段不改、原准备request不变，120秒拒HTTP。实际SDK完整等准备仍单独核查。独立[18项SDK/真实PG/runner及普通阶段上限回归](artifacts/phase7/review-3-capacity-stage-tests.txt)19.541s/OK/0skip，[源码快照](artifacts/phase7/review-3-capacity-stage-tests-snapshot.json)before=after：validation4000含2048推理结算一次、unknown保全额、4001或length拒发并留实际usage、80k/16k拒前、剩余2.5秒timeout，以及stop/new_input/takeover/实际过期lease恢复/活动预算五类晚到均0out。额外普通decision completion2001仍拒绝、实际消耗2021持久且重复不加账。工程模型/显式审计fixture只证明协议与门禁，不证明语义质量；随机schema自动cleanup，不写正式/public资料。

[独立compileall原始输出](artifacts/phase7/review-3-capacity-compile.txt)为空、exit0。另全文核定主Agent[92项专项原始输出](artifacts/phase7/review-capacity-tests.txt)84.176s/OK/0skip和运行快照before=after，当前所有backend源码/测试/迁移/锁文件SHA匹配；其后仅三个eval文件变化（历史键改名、有效timeout记录、其回归），已单列，未混称整份旧快照当前全相等。后修[43项eval原始输出](artifacts/phase7/review-capacity-eval-tests-final.txt)0.757s/OK/0skip，本审已抽跑当前runner全5项。这里只确认按既有授权恰一次negative后的全文双审前提，未放行positive/fresh业务/Graph表示接入；H12/H13仍开放，Stage 1 FAIL、Stage 2未开始。旧全部失败和当期276全量工程结论保留，没有用此次专项替代最终稳定产品全量验收。

074740-90d0b3da已完成此次容量候选唯一actual negative，独立全文门仍 **FAIL**：[完整request/SDK/原75来源及逐审项核对](artifacts/phase7/review-3-capacity-negative-actual.json)。实际配置/材料等074344prepared，paid before=after=current，1HTTP、3542输入+2737总输出=6279tokens（总输出含2048reasoning，只计一次）、48.985秒SDK/49,062活动ms、usage已知/cache0、finish=stop、0业务/原cycle次数不变。实际采样与输入没有漂移，失败不归因于环境；private reasoning仅留raw与SHA，不导出原文。

此次有明确局部进展：request unit2正确omitted/空quote，reason指出未来退款选择被完全遗漏；claim1=false且unsupported列出商品/SKU，reason正确指出其声明shipment来源没有商品资料，不再要求回复必须复述four-key/US/black。三个request引文都是草稿连续原文或合法空值，没有上一轮省略/解释串错误。但claim0=true依然用order-only声明来源中订单数字认可整段“checked shipment”；claim2含system in_transit和客户未收到的事实，空source/evidence仍true，不能归为纯中性问题。claim1 final reason仅证明缺声明商品来源，未独立证明补上order来源后ceiling译名可成立，因此没有关闭原H-13。

两source quote均属于各自声明ID，但把canonical JSON改写成label:value或拼多个字段，均非原来源连续片段；本轮没有越源，应与之前失败区分。当前 `B agent/review_audit.py:91/96` typed首码 `claim_0_quote_not_in_source`、binding/effective均拒绝；`agent/graph.py:209`准确修复反馈门保持。模型总false、runner11checks全部true、资源合法及程序拒绝不构成完整核验PASS，也没有真实业务提交。已明确通知主Agent保存本次FAIL门、停止此容量候选的后续付费；positive/Graph表示接入/fresh06–09仍0HTTP，旧全部FAIL与局部进展分别保留，Stage 1/H12/H13仍未过，Stage 2未开始。

主Agent已写与本审一致的[root容量控制全文FAIL](artifacts/phase7/root-capacity-negative-audit.json)及私有negative-semantic-review，均绑定同一实际response SHA；正控制门在HTTP前拒绝，0额外HTTP。私有result/real-model状态随后仅补充stopped_on_fulltext_semantic_failure，保留原runner11true；本审actual artifact中result SHA记录的是全文判读时、最终gate注释前的快照，不将可追加状态记录误作原response被改写。正式保旧仍由主Agent只读复核：0005/54表/53旧业务表列行SHA、配置、160原件、22资料/22版本保持，四端口关闭、隔离schema及对象目录已清理。本审未另查询或写正式库。

4k容量候选本配置停止，后续“连续事实片段”与“由代码从结构化来源位置展开原文引用”只是尚待规划的机制方向，没有新源码/质量证据/HTTP许可；不据当前工程绿或两项局部进展关闭HIGH。保持本期获准复用实例及报告未过状态，不重复未变检查，Stage 2等待Stage 1全部通过。

## 8. Stage 门与后续证据

当前已确认本期工程协议、独立编译、隔离UI、有明确出处范围的连续历史/人工恢复及新德文核心目标；202431条件退款H-12/H-13为HIGH，因此 **该版本Stage 1 FAIL，Stage 2 未执行**。安全/质量/文件<=300/无 any 的完整 Stage 2 结论和实际邻居视觉对比没有提前作出。继续经用户授权复用的本轮后修闭环，保留第7节原失败与M-01；最新Stage1全部符合后才进入Stage2。

未勾选 82 AC，未声称七类售后完整、正式图片、实际 Langfuse、完整删除或生产准确率；最终全量测试快照与用户查看也没有替代。
