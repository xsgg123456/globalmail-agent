# Phase 10 初轮独立审查

日期：2026-10-09；基线：`main / 6bbc075`；范围：当前 tracked diff 与 Phase10 untracked 实现、测试、文档。`.idea` 不在审查或编辑范围。使用 `.agents/skills/code-review/SKILL.md`；未修实现、未提交、未调用付费模型、未升级或启动正式库。

**Stage 1：初审 FAIL。Stage 2：未执行。** 初审独立发现两个 HIGH、一个 MEDIUM。主线程随后修复三个发现，针对性独立复验通过；本报告保留修前 FAIL，不将局部复验折算成完整新一轮审查。最终源码、整批报告、UI及冻结验证仍须 fresh reviewer 从 Stage1 审查。

## 1. 审查步骤和证据边界

1. 读取 AGENTS、Product-Spec、AGENT-ARCHITECTURE、DEV-PLAN Phase10、docs/README、PHASE-10-IMPLEMENTATION、SESSION-HANDOFF，按 Phase10 交付逐项查实现。
2. 核对事项、等待、业务事件、方案变更、连续事实、控制器 gate 与实际服务接线，做最小隔离反例。
3. 独立运行 35 项工程测试与 compileall；因 Stage1 HIGH 停止，不进行 Stage2 质量、安全扫描及邻居页面视觉验收。

主线程在初审期间继续补测试和修实现。因此独立35项测试的 `source_changed=true`，这是中间工程证据，不能充当最终冻结证明。原输出及摘要保存在 [engineering-tests.txt](artifacts/phase10/review-initial/engineering-tests.txt)、[engineering-summary.json](artifacts/phase10/review-initial/engineering-summary.json)。初审不改写 Phase1/7/8 原质量 FAIL，不勾82项产品 AC。

## 2. Stage 1 问题

### P10-S1-001 — HIGH：纠错尝试确认未执行，释放了原成功赔付并堵死后续纠错

- **要求原文**：`AGENT-ARCHITECTURE.md:27`：“已派送的纠正发件必须有人工纠错凭证、保持原成功记录和原赔付份额”。`Product-Spec.md:457` 要求同订单行及受影响数量核对互斥补偿；`docs/planning/PHASE-10-IMPLEMENTATION.md:9` 要求取消及纠错不绕过授权和执行前提。
- **触发**：创建真实补件申请→第一次 execution 建标签、承运收件并 `succeeded`→同 operation 创建有凭证的 corrective execution→第二次 execution `unknown`→仅对第二次提交 `reconciled_not_executed`，含明确未发件证明。
- **预期**：第二次尝试的库存预留可释放，原成功 execution 和原赔付份额继续有效；不能把整笔申请写成从未执行。纠错可按明确凭证继续处理。
- **实际**：原 execution 仍 `succeeded`，但整笔 operation 被写成 `failed / confirmed_not_executed=true`，唯一 `compensation_reservations.active=false`。真实返回的 `allowed_events` 只有 `inventory_changed`，没有继续纠错入口。
- **原因与位置**：`globalmail-agent/backend/src/globalmail_agent/application/simulation_execution.py:76` 的对账分支没有区分 original/corrective execution；`:91` 无条件 `release_compensation(conn, operation)`，`:92` 返回整笔 `failed,true`。`application/simulation_control.py:111` 将该返回值投影到整笔 operation。`domain/executions.py:47` 仅在整笔 succeeded 时提供 `create_corrective_execution`，因此后续入口断路。`simulation_execution.py:43` 又把任何历史 corrective 记录都视为已经纠错，未区分已证明未执行的尝试。
- **独立证据**：真实随机私有 PG schema，经实际 AfterSalesService / SimulationControlService；[corrective-repro.txt](artifacts/phase10/review-initial/corrective-repro.txt)。复现脚本 [repro.py](artifacts/phase10/review-initial/repro.py) 的 `test_correction_not_executed_releases_original_compensation`。1项测试/0失败是“断言缺陷确实发生”，不是正确行为通过。
- **限度**：本次没有观察到第二笔退款或重复补偿成功；领域账本仍会看到原成功执行而拒绝冲突。已确认的是成功赔付保留契约破坏、错误的申请投影与纠错后续断路。
- **修前源码**：[simulation-execution-reviewed.txt](artifacts/phase10/review-initial/simulation-execution-reviewed.txt)，SHA256 `96b8c778cba953fabd9d74beea83d900e384134fec88b5035f13e5edcaf027aa`，上述原因行号取自该版本。
- **针对性修复与独立复验**：主线程在当前 `simulation_execution.py:92` 查询其他成功execution，有则保留整笔succeeded/confirmed_not_executed=false，不释放原赔付；`:43` 仅未证明未执行的旧纠错阻止再次纠错。独立重跑 `tests/test_continuous_fulfillment.py:17` 的 `test_unknown_corrective_attempt_does_not_release_original_success_and_can_retry_only_after_proof`：unknown前拒绝重试→明确仅第二次未执行→原赔付active、operation成功、库存consumed/released→第三attempt保持一operation/一赔付，1项/0fail/0error/0skip，`source_changed=false`。原输出见 [corrective-fix-check.txt](artifacts/phase10/review-initial/corrective-fix-check.txt)，关闭这个反例；完整修后审查仍待 fresh。

### P10-S1-002 — HIGH，针对性修复已复验：旧客户地址原文被重新标成当前确认

- **要求**：`Product-Spec.md:455` 换货/补件须核对地址确认，`:370` 当前来信和有来源人工更新修正过时信息；当前细化契约 `AGENT-ARCHITECTURE.md:25` 要求新地址确认引用最新可见客户消息，并按订单行保存。
- **触发**：有首封“地址不变”的 replacement 会话，追加客户“地址已变，不得用旧地址，发件前补问新地址”，再通过 branch-facts 用旧首封逐字原文提交 `confirmed=true`。
- **修前实际**：命令成功，`status=record_only`；当前业务地址投影为 `confirmed=true / version=1 / customer_statement`。存储来源仍是旧 `SIM-M-BASE-OUTON-06-1`。地址确认服务原先仅调用 `visible_quote`，未检查该来源是否已被后续客户消息取代。
- **修前证据**：[source-repro.txt](artifacts/phase10/review-initial/source-repro.txt)，第一项为真实隔离 PG 事务；脚本 `test_old_address_quote_accepted_after_new_customer_address`。首次复现因错误读取公共投影未公开字段而报 KeyError，随后纠正断言并干净重跑；报告采用第二次原输出，不把第一次测试错误当产品错误。
- **当前修复位置**：`application/branch_facts.py:103` 检查 latest visible customer，`:105` 拒绝旧来源；`:111` 按 order_line 保存 `address_confirmations`。修复由主线程完成。
- **独立复验**：[source-fix-check.txt](artifacts/phase10/review-initial/source-fix-check.txt)，`test_previous_address_source_rejected` 返回 `address_source_superseded`，通过。仅关闭这个已复现反例；多订单地址的完整回归仍交 fresh 复审。

### P10-S1-003 — MEDIUM，针对性修复已复验：退货前置 gate 借另一订单通过

- **要求**：`DEV-PLAN.md:216` 按实际 Agent 输出和业务账本满足 gate 后才提供下一事件；`Product-Spec.md:471` 多订单不得相互覆盖。当前细化契约 `AGENT-ARCHITECTURE.md:25` 明确同订单、同订单行实际退货申请。
- **触发**：当前被选中的 `REF-A / LINE-A`，会话内仅另有 `RET-B / LINE-B` 的 managed return。调用 `after_internal_return_request`。
- **修前实际**：gate 返回 `passed / ledger_verified`，证据却只列 `operation:REF-A / version:1`；没有 LINE-A 的退货申请。原实现仅遍历会话内任意 managed return。
- **证据和验证方式**：[source-repro.txt](artifacts/phase10/review-initial/source-repro.txt) 的 `REPRO_CROSS_ORDER_RETURN_GATE`。这是直接调用真实 gate 函数的构造账本反例，未声称真实 PG 整条 delivery 成功，也未声称绕过实际履约服务。
- **当前修复位置**：`evaluation/service_gates.py:37` 只接受同 order_id、同 order_line_id、未取消的 managed return。
- **独立复验**：[source-fix-check.txt](artifacts/phase10/review-initial/source-fix-check.txt) 的 `test_unrelated_return_gate_blocked` 返回 `blocked`，通过。须在最终审查核对报告的证据引用能指向真正满足前置的退货申请。

## 3. Stage 1 逐项对照

下表“已接入”仅表示本期工程路径存在并有对应验证，不能折算成付费模型业务质量或产品 AC 勾选。

| 本期要求 | 结论 | 实现位置与验证 |
|---|---|---|
| 同客户多订单、多事项，不拆会话、不覆盖另一事项 | 已接入 | `application/case_issues.py:11` 按真实 line+kind 复用事项；`:28` 从有源理解绑定。`tests/test_business_waits.py:22` 实际双订单事项与重复同步；新增双等待测试位于`:38`，本次35项测试开始后源码有变，不能宣称此新增项已冻结通过。 |
| 事项、申请及方案关联；改方案先核原申请 | 已接入 | `application/case_issues.py:68` bind_plan；`application/plan_changes.py:9` 退货转换检查；`application/after_sales.py:39` 调用关联/原计划门，补偿冲突继续由 `domain/policy_ledger.py:28` 检查。 |
| 多个等待可并存，关联真实 order/issue/operation | 已接入 | `application/waits.py:12` 注册并校验 scope/issue；`application/commit_outcome.py:91` 额外等待逐条注册、去重；`agent/tool_schemas.py` 的 additional_waits schema。双订单新增项仍须最终冻结。 |
| 结果先于 wait，补查并持久 wake；不能等下一事件 | 已接入 | `application/waits.py:37` 查最新水位，`:44` 过时等待事务内建立 wake。已有 `tests/test_agent_waits.py:60`、`:106` 真实事务时序；本次独立35项不包含该旧模块，不冒称独立重跑。 |
| 结果后于 wait、重复/乱序/无关事件 | 已接入 | `application/business_events.py:13` 同scope相关申请；`:27` 来源去重；`application/waits.py:80` 拒绝旧版本。`tests/test_business_waits.py:118` 实际执行→早到pending；原wait反例 `test_agent_waits.py:32,73,144`。 |
| 排队不等于消费；终局只消费本轮观察版本 | 已接入 | `agent/context.py:70` 固定 observed_wakes，`:73` 固定 observed_event_ids；`application/waits.py:128` 只按本轮观察消费；`application/commit_outcome.py:133` 同事务消费。独立 `test_business_waits.py:60` 证明晚到无关通知仍未消费。 |
| HITL、人工回复后待客户、停止/中断、结案屏障 | 已接入 | `application/waits.py:79` 同时要求 lifecycle=open/owner=agent/gate=open，否则记账不排队；`test_business_waits.py:132` 真实人审库存不增job；原 `test_agent_waits.py:155` 与 `test_human_events.py` 覆盖人工恢复屏障。原35项无完整屏障组合重跑，最终须冻结。 |
| unknown 保留原申请与赔付；明确未执行后方可释放 | 普通原申请已接入；纠错修前不匹配、已针对性复验 | `application/after_sales.py:196` 保留未知取消并记录请求；`simulation_execution.py:76` 要求凭证并拒绝与该 execution 已发件冲突。纠错修前释放原成功份额，修复与真实对账重试复验见 P10-S1-001。 |
| 自然单行、单单位全额/同SKU/唯一兼容件绑定真实值；条件、多单位、部分金额须明确 | 已接入，质量延期 | `application/choice_binding.py:5` 确定性拒绝条件/否定、限制单行单单位；`after_sales_selection.py:30` 要求有源显式理解；独立 `test_selection_freshness.py:28` 实际全额退款/错金额/错币种反例通过。其他自然语言覆盖不等于模型质量通过。 |
| 新客户消息后旧选择执行必须以当前有源理解重核 | 已接入 | `application/selection_freshness.py:10` 核对当前 visible/input_revision；`:26` 未理解拒绝，`:30` 当前改选拒绝。独立 `test_selection_freshness.py:40` 旧退款执行0新增。 |
| 连续人工事实来源、版本、人员、回执、原因、scope、幂等 | 已接入 | `domain/business_events.py:9` 严格schema；`application/branch_facts.py:26` 原键重试、source_event_id冲突、`:39` 会话/业务版本及line核验；`tests/test_business_waits.py` 库存重复和同ID异参反例通过。 |
| 库存显式商品/市场/硬件/时间，不默补；无申请仅记账 | 已接入 | `application/branch_facts.py:73` 必填、规格/快照及已占用检查；`:123` 只关联相应申请/事项；独立库存缺规格被拒和record_only不增job。 |
| 地址必须当前客户原文、按订单行 | 修前不匹配，已针对性复验 | P10-S1-002；`application/branch_facts.py:99` 当前源码已加旧源拒绝与按行保存。完整多订单复审待执行。 |
| 原包裹、退件资料和质检更正保留不可变历史 | 已接入 | `application/branch_fulfillment.py:8` scope/resource/version；`:24` 质检更正前提；`branch_facts.py:59` 不可变来源事件。独立 `test_continuous_fulfillment.py:42` 原disputed事件保留且当前passed（35项执行时该方法在修前文件`:19`）。 |
| 原成功履约纠错在同operation中新execution，库存再记、赔付一次 | 修前部分实现，HIGH；已针对性复验 | `simulation_execution.py:36` 有源纠错、`:58` original execution关联，独立 `test_continuous_fulfillment.py:64` 成功纠错保留一operation/一赔付/两库存消费（35项执行时在`:44`）；unknown→未执行破坏原成功的修前证据及修后重试见 P10-S1-001。 |
| 0009 additive，旧资料保留，正式0005不升级 | 实现存在，正式库未独立验收 | `migrations/versions/0009_business_waits.py:12` 增列/FK/索引，无drop/backfill抹历史；`:48` downgrade拒绝无保全方案。`tests/test_after_sales_migration.py:20` 为0008→0009旧行保留测试；主线程正式库保旧证明待最终报告，不从测试schema推定正式库已核对。 |
| controller只送当前过gate事件，不注入未来、参考回复、期望答案 | 已接入 | `evaluation/journey_driver.py:29` 固定controller路径；`:178` 仅delivery允许字段；`journey_gates.py:65` fail-closed gate；`test_scenario_driver.py:47` 实际读取路径只两份controller文件，原库存未暗填。 |
| 实际 Conversation/Simulation/BranchFacts/AgentRunner 接线；门必须真证据 | 部分实现，gate已针对性修复 | `evaluation/service_adapter.py:14` 私有schema限制，`:25` 实际服务，`:43` runner；`service_delivery.py:18` 实际提交；真实 `test_journey_services.py:14` JRN01 Graph handoff后checkpoint仍待审。P10-S1-003 证明有名处理器不自动等于正确业务证据。 |
| 21 JRN/原51逐项报告，不把文字checkpoint或缺材料伪造PASS | 报告器已接入；整批实际报告本轮待交付 | `evaluation/scenario_driver.py:10` 建立72驱动；`reporting.py:19` 每步not_run及blocked，`:33` model_semantics延期；`journey_gates.py:132` checkpoint须绑定实际run/revision/人员/证据。独立单测72项初始not_run不是72项实际业务运行。主线程正生成scenario-engineering.json，本报告不提前称其通过。 |
| CaseIssues和连续事实UI，真实数据/状态，业务执行与接管分开 | 静态接线已核，实际UI未在本轮验收 | `frontend/src/components/mail-agent/CaseIssues.vue:2` 真实issues/waits/wakes/events；`BranchFactControl.vue:5` 来源/规格/资源表单；`ScenarioControl.vue` 独立事实/执行区，`AgentProcessPanel.vue` 接入。组件沿用Element Plus和模板样式；没有本轮独立浏览器对照证明，不能写UI PASS。 |
| 丢响应按原幂等键、原参数重试，不自动开新命令 | 已接入 | `frontend/src/composables/useAfterSales.ts:18` retryCommand；`:80` 保存原请求；`:65` retry执行原对象，`:44` 原请求待核时阻止新操作。前端64项/build为主线程证据，非本轮独立重跑。 |

### Spec 范围与延期项

本期相关 REQ-001/003/004/006/007/008/009/011/012/014 的多订单、唯一出站、范围校验、有源记忆、处理权、恢复、工作台及售后门已逐项纳入上表。REQ-002/005 的历史和知识契约继续由既有服务使用；本期没有扩展其已交付范围，0009及模拟事实不开放历史写。REQ-010 完整重置/删除和 REQ-013 自托管观测按 DEV-PLAN Phase12/11 交付，属于明确后续范围，不能列成本期缺陷，也不能称已实现。相关产品 AC-041/042/043/053 等只作验收归属，不勾选；21JRN完全模型闭环、SCN业务语义、81文字checkpoint人工核对和最终82AC继续未验。

新增 branch-facts 是 REQ-011 显式模拟事件与有来源更正的实现，没有观察到本期另建ERP、真实支付/收发或模型状态推进工具；`api/simulation.py:15` 与 `agent/tools/after_sales.py` 注册边界分开。不存在设计稿/Design-Brief新变更，UI应继承原Art Design Pro；实际视觉一致性还不能从“复用组件”推出。

## 4. 编译与测试原始输出

独立工程命令：`.venv/Scripts/python.exe tmp/phase10-tests.py test_business_waits test_continuous_fulfillment test_selection_freshness test_journey_driver test_scenario_driver test_journey_services`。原输出结尾：

```text
----------------------------------------------------------------------
Ran 35 tests in 52.967s

OK
```

摘要 `tests=35, failures=0, errors=0, skipped=0, source_changed=true`。私有随机 schema 与临时对象由测试 fixture cleanup 清除；没有付费模型调用。该结果不能覆盖后续修复的完整源码。

独立缺陷确认原输出：

```text
Ran 2 tests in 4.801s
OK
REPRO_STALE_ADDRESS_ACCEPTED ... "status": "record_only", "business_version": 1
REPRO_STORED_ADDRESS ... "confirmed": true, "source_message_id": "SIM-M-BASE-OUTON-06-1"
REPRO_CROSS_ORDER_RETURN_GATE ... "status": "passed", "resource_ids": {"operation_id": "REF-A"}

Ran 1 test in 5.832s
OK
REPRO_CORRECTION_NOT_EXECUTED ... "status": "failed", "confirmed_not_executed": true,
  "allowed_events": ["inventory_changed"], "compensation_active": false
```

地址/gate修复针对性独立复验：

```text
Ran 2 tests in 4.968s
OK
FIX_OLD_ADDRESS_SOURCE_REJECTED address_source_superseded
FIX_CROSS_ORDER_RETURN_GATE ... "status": "blocked"
```

独立编译命令：`globalmail-agent/backend/.venv/Scripts/python.exe -m compileall -q globalmail-agent/backend/src globalmail-agent/backend/migrations`。**退出码0；原stdout/stderr为空**，没有编译错误。主线程前端构建记录 `tmp/phase10-frontend-build.txt` 末行 `✓ built in 28.64s`，仅作收到的辅助证据，不替代最终冻结重跑。

## 5. Stage 2 与交接

**Stage 2 未执行**：P10-S1-001 是业务状态/赔付份额 HIGH，按两阶段规则停止。未声称安全扫描通过、文件质量通过或邻居视觉对比通过。

三个发现均有主线程修复及针对性独立复验；须冻结完整工程测试、72逐项实际运行报告和实际UI证据后重新派 fresh reviewer。从 Stage1 完整复审，通过后再执行 Stage2。保留本初审 FAIL 与修前原输出，不改成 PASS。
