# Phase 10 独立关闭审查（本轮未关闭）

日期：2026-10-09；基线：`6bbc075`。fresh code-reviewer，按 code-review skill 从 Stage 1 开始。**Stage 1 FAIL：1 项 HIGH；Stage 2 未执行。**文件名 `CLOSED` 不表示通过。前两轮 FAIL 报告不改写。本报告只评审 DEV-PLAN 第 224 行明确的本期工程范围，原 51 业务质量、21 JRN 到人工结案、图片质量及 82 AC 仍留 Phase 13。

## 审查步骤与来源

1. 重新读取 AGENTS、code-review skill、Product-Spec、AGENT-ARCHITECTURE、DEV-PLAN、文档索引、SESSION-HANDOFF、Phase 10 实施/验证原文，以及 BUSINESS-SCENARIOS、AGENT-ACCEPTANCE、数据契约和连续流程清单；以当前工程合同逐项定位代码。
2. 独立运行随机私有 PostgreSQL schema 的重点模块，核对实际账本、事件、等待及执行结果；测试入口先调用 `isolated_database_environment()`，不连接正式应用 schema，不调用付费模型。
3. 对最新客户重确认加入作者测试未覆盖的金额边界反例。真实执行放行了不一致金额，立即向主 Agent 报告 HIGH，停止进入 Stage 2。

审查 `git diff 6bbc075` 及 Phase 10 新增源码、迁移、测试、文档；排除原有 `.idea/` 与临时工作目录。没有修复代码、提交、push、正式库迁移或正式服务启动。独立测试过程均已退出，私有 schema/对象由 fixture 的 cleanup 回收。没有创建浏览器页面。

## Stage 1：Spec Compliance

### HIGH P10-C-01：退款金额按子串匹配，最新不同金额被误认成原方案重确认

**需求证据**：Product-Spec.md:452、454 要求金额/币种的客户选择与退款执行核对；AGENT-ARCHITECTURE.md:29 明确“原订单行、数量、金额币种及商品精确核验”及“不同方案或参数不明确仍拒绝旧方案”。DEV-PLAN.md:213 要求客户改方案、取消/未知结果不能误执行业务。

**被测代码证据**（绑定下列被测 SHA，不代表后来修改后的源码）：

- `globalmail-agent/backend/src/globalmail_agent/application/after_sales_selection.py:24` 经 `execution_selection` 取得最新确认后，31 行递归校验；58、60 行以 `decimal in quote` 与 `currency in quote` 判定显式金额/币种。`54.99` 是 `154.99` 的子串，因此未进入拒绝路径。
- `globalmail-agent/backend/src/globalmail_agent/application/selection_freshness.py:27` 将当前有源、单项、explicit、同类别选择作为重确认；43 行返回最新原文。它没有补偿上述金额匹配漏洞。
- `globalmail-agent/backend/src/globalmail_agent/application/simulation_execution.py:13`、25 行调用 `_evaluate` 重验，38 行继续建立执行，因此缺陷可以经实际人工模拟控制服务产生账本效果。

**真实反例**：`artifacts/phase10/review-closed/adversarial-original.py:17`。

1. 通过真实服务建立 54.99 USD 的原退款申请。
2. 追加客户来信 `Yes, I confirm a full refund of 154.99 USD.`，并持久化引用该实际消息的当前 Understanding。
3. 调用同一申请的 `create_execution`。
4. 预期拒绝不同金额、执行数为 0；实际返回成功，新增一条金额 `5499`、币种 `USD` 的执行，执行数为 1。

原始响应中的实际标识：conversation `8f9e0c9f-3c02-4d24-be7d-499fc5966608`，operation `OP-a4f26df0c584440097a6d0574e1b6d74`，execution `EXEC-f47c284f666f41a5a48aafa39047c5ec`，event `faa9b4d4-5242-4bd1-ae4c-19cd18d50b1d`。原文保存在 [反例输出](artifacts/phase10/review-closed/adversarial-output.txt)。这证明客户具体选择与执行方案不一致，不把“未超实付”当作授权正确。

被测 `after_sales_selection.py` SHA-256：`efaafe62389618d7ab5b68f0cd9768e0cddb6cb6a15c6159d009e96720214d46`。本轮反例执行期间 `source_changed=false`，完整前后 SHA 在 [原测试 manifest](artifacts/phase10/review-closed/adversarial-tests-original.json)。主 Agent 接到报告后已开始修改；收尾读取的当前 SHA 为 `90e72db1af0e38a2baf9aed73b28cf0030392bcab65af773571db55d943ec1ba`，故本轮失败绑定原被测版本，**不宣称已证明新版本仍失败或已修复**。各关键文件的测试/当前 SHA 对照在 [source-binding.json](artifacts/phase10/review-closed/source-binding.json)。修复后须 fresh 从 Stage 1 重审。

### 本期逐项核对结果

以下“已验证”只表示指定工程断言有实际证据，不表示相关产品 AC 或全部业务质量通过。

| 当期条目 | 结论 | 代码位置与证据 |
|---|---|---|
| 稳定订单行/类别事项；同客户多订单 | 已验证该工程断言 | `application/case_issues.py:11、27、69` 精确解算/复用；`tests/test_business_waits.py:22、38` 实际双订单事项、独立等待及未来版本拒绝通过 |
| 等待及 wake 与实际业务版本关联；排队不消费 | 已验证重点路径；全时序未在本轮逐条重跑 | `application/waits.py:12、72、128` 登记、门禁、仅消费上下文观察版本/IDs；`tests/test_business_waits.py:60、118` 终局不消费后来无关事件、早到真实执行保持 pending/null 通过；晚到/重复/乱序基础测试位于 `tests/test_agent_waits.py:32、64、80、113`，本轮未执行，不借静态阅读写 PASS |
| 无新事实正常等待不持续调用模型 | 代码对应；本轮未独立执行该完整断言 | `application/waits.py:90` 旧/相同业务版本不创建触发；`tests/test_agent_waits.py:100` 终局等待释放槽且无新领取的断言需重跑 |
| 客户改方案、取消与 unknown 占用 | 部分已验证；重确认整体不匹配 | `application/after_sales.py:187` 取消入口，未确定执行不释放；`application/plan_changes.py:9` 原互斥方案门；`tests/test_after_sales_cancellation.py:34、43、54、61` 取消、unknown、条件取消及有证据回执通过；不同金额误放为本报告 HIGH |
| 相同方案最新重确认沿用原申请/记录新来源 | 常规正/负例通过，边界失败 | `tests/test_selection_freshness.py:76、91、94` 正常同方案、50.00、EUR 的作者测试通过；`adversarial-original.py:17` 的 154.99 真实服务反例失败，不能仅据常规测试通过关闭该项 |
| 地址按最新客户来源及逐订单行确认 | 已验证旧地址反例，逐订单行代码对应 | `application/branch_facts.py:100` 检查最新来源，113 行按行保存；`tests/test_business_waits.py:94` 旧原话被拒绝通过 |
| 连续库存/包裹/退件/质检人工事实来源与版本 | 已验证指定路径 | `application/branch_facts.py:20、72` 幂等、事实/资源版本、规格和来源；`tests/test_business_waits.py:102、132` 无规格拒绝、record_only不排队、人审库存只记录通过；`tests/test_continuous_fulfillment.py:45` 质检修订保留原事件通过 |
| 成功履约后的纠错与赔付/库存历史 | 已验证原 HIGH 反例 | `application/simulation_execution.py:43、94` 检查纠错来源，原成功存在时只释放此次库存；`tests/test_continuous_fulfillment.py:19、68` unknown→未执行证明→重试保留原赔付，以及同申请纠错发件通过 |
| 补件后物流、退货后退款及账本 scope | 代码对应，重点 gate 通过；完整模型旅程未验 | `evaluation/service_gates.py:21` 按具体申请/订单行检查；`tests/test_controller_business_gates.py:15` 另一订单/另一行退件不能满足当前退款 gate 通过。完整补件/退款语义与 JRN 到结案按 DEV-PLAN.md:224 延期 |
| 人工执行业务与 HITL 独立、人工屏障 | 已验证本轮人审库存和当前 Graph 路径；其余完整时序未重跑 | `application/waits.py:89` 只有 open/agent/open 可唤起；`tests/test_business_waits.py:132` 不排自主任务；`tests/test_journey_services.py:15` 实际 Graph handed_off 仍不把文字 checkpoint 判过。人工回复后的双顺序测试需下一轮独立重验 |
| 连续驱动只按当前事实和实际证据推进 | 已验证重点驱动行为 | `evaluation/journey_driver.py:39、132` 只读固定控制文件、逐项 gate，未提交回执不推进；`evaluation/journey_gates.py:69` unknown gate 默认 blocked，139 行 checkpoint 需要人工证据；独立 driver/scenario/gate 模块全部通过，见原输出 |
| 21 JRN + 原51逐项初始化/当前 gate 报告 | 代码及现有汇总对应；本轮不是独立72全初始化 | `evaluation/service_adapter.py:17、28、49` 私有 schema 限制、实际服务/运行关联；`evaluation/scenario_driver.py` 与 `evaluation/reporting.py` 保留未运行项。本轮独立验证一条真实 Graph 与全部目录/命名 gate，主线程72报告31 in_progress、20 blocked、21 awaiting_checkpoint不改为业务 PASS |
| 0009增量扩展不重建基础表 | 已验证 | `migrations/versions/0009_business_waits.py:12` 仅新增列/FK/index；`tests/test_after_sales_migration.py:20` 0008→0009重复增量迁移及旧行/来源保存通过 |
| 工作台事项/等待、连续事实、独立人工操作 | 源码对应；本轮实际 UI 未验证 | `frontend/src/components/mail-agent/CaseIssues.vue:2、13、24` 展示真实事项/等待/消费运行；`BranchFactControl.vue:5、78` 表单/解析与确认；本轮发现 HIGH 后收尾，没有浏览器、宽窄/明暗或邻居页面 PASS |
| 不改历史质量 FAIL、不以固定响应/blocked/not_run冒充业务 PASS | 已核对本期文档边界 | `DEV-PLAN.md:224`、`docs/verification/PHASE-10-VALIDATION.md:29` 保留延期及未运行限制；本报告不勾82 AC，不将作者53项工程测试推成完整旅程通过 |

REQ-001 的多订单、REQ-006 的多事项记忆、REQ-007 的事件人审屏障、REQ-008 的版本/恢复、REQ-009 的工作台增量、REQ-010 的报告/答案隔离、REQ-011 的连续业务和 REQ-012 的后续选择按表逐项核对。REQ-002/003/004/005/013/014 的其余完整产品验收由 DEV-PLAN 各既有/后续阶段负责，本次不重复授予 PASS、不修改原验收状态。引导文案已静态核对来源/回执/规格对应服务，实际交互未验证。没有把新增 branch-facts 或控制器当作模型可调用业务成功工具。

## 独立执行原始结果

命令：`uv run --frozen --project globalmail-agent/backend python tmp/phase10-review-closed-tests.py test_business_waits test_continuous_fulfillment test_selection_freshness test_controller_business_gates test_journey_services test_journey_driver test_scenario_driver test_after_sales_cancellation test_after_sales_migration`。

原始输出：[independent-tests-output.txt](artifacts/phase10/review-closed/independent-tests-output.txt)，前后 SHA：[independent-tests.json](artifacts/phase10/review-closed/independent-tests.json)。

```text
Ran 53 tests in 126.079s

OK
```

manifest：53 项、0 failure、0 error、0 skipped、126.10999999998603 秒、`source_changed=false`。迁移反射的 `public.vector` SAWarning 原文保留，不把警告删除后描述为零输出。

自写反例的原始结果：

```text
Ran 3 tests in 16.302s

FAILED (failures=1, errors=2)
```

其中金额用例是实际服务断言失败，已形成 HIGH。两个 replacement 用例在创建原申请时因自写自然语句未满足现有选择条件而 `TypeError: 'NoneType' object is not subscriptable`，没有走到待审执行，**前提不可用，不能据此报告 wrongitem/units 缺陷或正确**。原脚本、错误和 SHA 全部保留；未删错例伪造“全部反例执行成功”。作者7项选择测试仍未覆盖154.99金额边界，该实证说明常规测试绿不证明参数精确绑定。

## Stage 2 及编译

**未执行**。code-review skill 要求 Stage 1 有 HIGH 停在 Stage 1。本轮不输出 Code Quality、安全扫描、视觉邻居对比、前端测试/vue-tsc/Vite 或 Python 编译 PASS；主线程已有输出不冒充本轮独立执行。待主 Agent 修复并冻结后，fresh reviewer 应从 Stage 1 重起，重验精确金额/币种、wrongitem/units/conditions及全部故障时序，再进入 Stage 2。正式库保旧由主线程只读汇总负责，本轮没有重连正式库，也不以未连接替代正式库完整性验收。
