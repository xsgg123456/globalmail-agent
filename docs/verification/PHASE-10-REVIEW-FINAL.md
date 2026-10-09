# Phase 10 独立两阶段复审

2026-10-09；基线 `main / 6bbc075`。审查范围是当前 tracked diff 和 Phase10 untracked 源码、迁移、测试及交付文档，排除 `.idea`。本轮为新的独立 reviewer，从 Stage 1 重新读取原文，使用 `.agents/skills/code-review/SKILL.md`；没有修源码、commit、spawn、付费模型调用或正式数据库升级。

**本轮整体未通过。Stage 1 没有发现 HIGH，发现 1 个新的 MEDIUM；按无 HIGH 门槛执行 Stage 2，另发现 1 个测试完整性 MEDIUM。不能用本轮结果宣布工程四步全部通过。** 初审两个 HIGH 和一个 MEDIUM 的当前回归均通过；初审 FAIL 和修前证据保留。

## 1. 证据与范围

1. 独立读取 AGENTS、Product-Spec 全文、主架构、DEV-PLAN（包括 Phase10 原验收目标）、docs/README、SESSION-HANDOFF、PHASE-10-IMPLEMENTATION、PHASE-10-VALIDATION、PHASE-10-REVIEW-INITIAL；再读取当前 diff 与新增实现，不以旧审查代替当前判断。
2. 对照稳定订单行事项、多等待、事件接收/观察/消费、方案变更、取消与纠错、连续事实、实际服务驱动及 UI；独立运行 11 个工程测试模块，并补一个真实私有 PG 反例。
3. 无 HIGH 后执行类型/文件/安全扫描、测试真实性核对、独立前端测试与构建、实际工作台及邻居卡片视觉对照。独立 IAB 页面只执行展开、查询和空表单验证，未操作主线程 Playwright 会话，已关闭临时页。

独立 PG 测试从 `tests/test_protocol.py:31` 的随机 `test_protocol_<uuid>` schema 和临时对象目录运行，初始化迁移与 cleanup 针对该 schema；没有向正式0005 schema写测试。固定模型响应只提供理解/动作候选，实际 Conversation/账本/Graph/提交/租约/权限门均执行；不将这些响应称为真实模型业务质量。

源码清单与 SHA256 在 [review-final/code-audit.json](artifacts/phase10/review-final/code-audit.json)，独立回归前后全后端清单在 [backend-tests.json](artifacts/phase10/review-final/backend-tests.json)。本轮61项测试 `source_changed=false`，审计时当前后端所有文件仍与测试 after SHA一致。结论绑定该源码，不覆盖后续修改。

## 2. Stage 1 发现

### P10-FINAL-S1-001 — MEDIUM：同一方案的新来信重确认被当作改选，复用申请后仍无法执行

- **要求**：`Product-Spec.md:369` 要求使用当前有源信息修正旧信息；`:484` 要求支持同意、拒绝及改变方案；`:470` 未知结果/重试复用原操作；`AGENT-ARCHITECTURE.md:21` 要求原申请之后有新客户消息，执行前以当前有源理解重新核对。相同方案的重新同意不应等同于改选或撤销。
- **触发**：真实退款申请已受理，金额54.99 USD、单行单单位；客户随后说 `Please proceed with the same full refund of 54.99 USD.`；当前 run 已保存该最新消息逐字来源的 `explicit` 理解，无条件、同一退款。控制台执行原申请，然后按新来信重新 check/create，再执行返回的申请。
- **预期**：重新核验同一规范方案后复用原申请，关联当前确认并允许合法执行，不能产生第二笔赔付。
- **实际**：第一次执行返回 `selection_superseded`；新来信 check/create 返回 `operation_reused` 和同一个 OP，但再次执行仍 `selection_superseded`。正常重确认流程断路，必须另走取消/新建等绕路。未观察到重复赔付或越权执行。
- **原因**：`globalmail-agent/backend/src/globalmail_agent/application/selection_freshness.py:26`–30 和 `after_sales_selection.py:76`–80 仅凭后续 `explicit/declined/conditional` 意图与目标相关就判旧选择作废，没有比较是否仍为同一规范方案；`after_sales.py:129`–137 复用旧 OP，但保留原选择来源。
- **独立证据**：[reconfirm-repro.py](artifacts/phase10/review-final/reconfirm-repro.py) 经实际 AfterSalesService、SimulationControlService、持久化理解及私有 PG 运行；[reconfirm-repro.txt](artifacts/phase10/review-final/reconfirm-repro.txt)：`RECONFIRM_REUSED_BUT_EXECUTION_DENIED ... operation_reused selection_superseded`，1项/5.837秒/0失败。这一“OK”证明缺陷能复现，不表示业务通过。
- **修复方向**：区分同一规范方案的当前重确认与真正改变/撤销；复用申请时保存有源重核记录。仍须拒绝未理解、拒绝、条件、金额/币种/数量/对象变化，不可直接放行全部 `explicit`。

## 3. Stage 1 逐项实现对照

以下“完整实现”仅指本期确定性工程交付。真实模型语义、全部产品 AC、完整 JRN 业务验收另列，未折算成 PASS。路径前缀 `backend/`、`frontend/` 均相对 `globalmail-agent/`。

| 本期要求与 Spec 归属 | 结论 | 当前代码和实际验证 |
|---|---|---|
| 同一客户、多订单及多事项，按真实订单行稳定关联；REQ-001/006，SCOPE-005/015 | 完整实现 | `backend/src/globalmail_agent/application/case_issues.py:11` 以真实 line+kind 复用，`:27` 从有源理解解析；`tests/test_business_waits.py:22` 同客户两订单、重复同步仍只有两事项，独立回归通过。无订单歧义不猜绑定。 |
| 事项、当前申请/方案、来源分别保留；REQ-006/011 | 完整实现 | `case_issues.py:49` 实际申请关联、`:61` 当前方案版本；`after_sales.py:159` 创建后绑定；当前 UI 实际显示订单退款事项、OP编号与第2版，邻居案件区显示两事项。 |
| 多等待并存、核验 issue/operation/scope、拒绝未来版本；REQ-006/008/011 | 完整实现 | `application/waits.py:12` 注册、`:21` scope、`:35` 对象匹配、`:41` future_business_version；`commit_outcome.py:90` 逐个额外等待及重复拒绝。`test_business_waits.py:38` 两订单两等待和未来版本拒绝通过。 |
| 早到结果注册补查、晚到唤起；REQ-008/011，AC-042/053归属 | 完整实现 | `waits.py:37`–48 注册补查当前水位、持久wake；`business_events.py:14` 同事务接收；`tests/test_agent_waits.py` 的 early version、early result、wake arriving after context、observed version 等8项全部通过。 |
| 重复/乱序/无关事件，无新事实不轮询；REQ-008/011，SCOPE-014/015 | 完整实现 | `business_events.py:27` 来源去重，`waits.py:80` 拒旧水位，`worker/event_dispatcher.py:5` 仅接受实际事件；`branch_facts.py:123` 只关联实际 managed申请或相关事项，无关联 record_only。真实重复库存0新增job、异参409、无关operation拒绝，独立回归通过。 |
| 排队不等于消费；只消费本轮上下文观察的ID/版本；REQ-003/008/011 | 完整实现 | `agent/context.py:70` 固定wake、`:73` 固定当前可见消息/业务event IDs；`waits.py:128` 限观察水位及scope事件；`commit_outcome.py:132` 终局同事务消费。`test_business_waits.py:60` 晚到无关通知不消费、`test_agent_waits.py` 更新水位保pending通过。主线程浏览器证据的事件/wake均pending、observed_run_id=null，未把排队写成消费。 |
| HITL、人工回复后等待客户、停止/需显式重试、结案屏障；REQ-007/008/011，SCOPE-007 | 完整实现 | `waits.py:79` 同时要求 lifecycle=open/owner=agent/gate=open；真实 `test_business_waits.py:145` 人审库存不排队、`test_agent_waits.py` 人工屏障下一客户恢复，以及 `test_human_events.py` 来信/人工事件并发和恢复独立回归通过。事件不改人工处理权。 |
| 改方案核原申请、未知保留份额、冲突拒绝；REQ-006/008/011/012，SCOPE-015/016 | 部分实现 | `plan_changes.py:9` 原待办取消/对账门、`after_sales.py:174` 取消与回执保留、现有policy账本核对互斥。未知不能释放及不能盲目再建已独立通过；但同方案新重确认反例见 P10-FINAL-S1-001，未完成。 |
| 自然单行单单位全额/同SKU/唯一兼容件；多行/单位/部分金额明确；REQ-004/011/012 | 完整实现；测试覆盖存在缺口 | `choice_binding.py:5` 条件/否定、单行单位、精确实付/币种/原SKU/唯一兼容件；`after_sales_selection.py:33` 有源explicit且无条件；`:44`–58 多行、数量、金额和单位明确。独立全额正例/错金额币种、未理解/declined反例通过；conditional/multi-unit测试未能执行完第二场景，见Stage2，不据此说覆盖全过。 |
| 新消息后旧选择执行须有覆盖current-input的来源理解；REQ-004/006/008/012 | 部分实现 | `selection_freshness.py:17` 精确 visible_message_seq/input_revision，`:23` 没理解拒绝；`simulation_execution.py:24` 执行重核；真实旧申请0新增执行反例通过。但重确认错误拒绝仍在。 |
| 明确取消未执行回执才释放一次，已派送拒绝；REQ-008/011，SCOPE-013/015 | 完整实现 | `simulation_execution.py:77` 要求取消请求/明确未执行/回执/理由，`:83` 本次已派送冲突拒绝，`:97` 释放；`tests/test_after_sales_cancellation.py:61` 实际取消证明与重复拒绝通过，unknown原占用保留通过。 |
| 原成功补发的同operation纠错、新attempt独立库存、一份赔付；REQ-006/011 | 完整实现，原HIGH已关闭 | `simulation_execution.py:36` 原成功/人工纠错证明及未知阻止；`:43` 已明确未执行的纠错可重试；`:67` 每次独立库存；`:92` 有原成功时保留 succeeded/原赔付。`test_continuous_fulfillment.py:17` unknown→证明仅第二次未执行→第三attempt，以及`:64` 两次成功库存消费/一赔付，独立回归通过。 |
| 连续事实来源、人员、回执、原因、版本与重复校验；REQ-006/008/011 | 完整实现 | `domain/business_events.py:9` 严schema；`branch_facts.py:26` 幂等与`:33` stable source ID异参拒绝，`:39` 会话版本、`:53` 连续事实版本。真实PG及浏览器表单有证据；历史模式不可写。 |
| 库存精确商品/市场/hardware/time、不默补；REQ-004/011，SCOPE-014 | 完整实现 | `branch_facts.py:73` 必需字段、`:76`–85 精确规格/时间/已预留核验；`test_business_waits.py:115` 缺硬件拒绝和无申请仅记账通过；`test_scenario_driver.py` 原缺库存字段不补通过。 |
| 最新客户逐字地址、按订单行保存，不借另一订单确认；REQ-006/011 | 完整实现，原HIGH已关闭 | `branch_facts.py:102` visible_quote、`:103`–106 latest customer、`:111` per-line；`business_read_model.py` 按选定行投影确认。`test_business_waits.py:105` 新客户改地址后旧源address_source_superseded，独立通过。 |
| 原包裹、退件资料/质检修订留原历史及资源版本；REQ-006/011，SCOPE-012 | 完整实现 | `branch_fulfillment.py:8` 同line/resource/version、`:27` 已收且failed/disputed的质检修订、`:36` 未收件资料及原邮费约束；`branch_facts.py:59` 不可变事件；`test_continuous_fulfillment.py:42` 原disputed事件保留/新passed及旧resource版拒绝通过。 |
| 0009 additive，不重建基础表、不抹旧行 | 完整实现 | `migrations/versions/0009_business_waits.py:12` 增列、`:30` scoped FK及索引，无drop/backfill；`:48` downgrade拒绝无保全方案。独立 `test_after_sales_migration.py:20` 0008→0009旧列/行及重复upgrade通过；源资料SHA在该fixture核对。 |
| 正式0005/54表、160原件及设置不改；REQ-010范围边界 | 已有主线程可查证据，本轮未重复查询正式库 | [formal-readonly.json](artifacts/phase10/formal-readonly.json) 的54表原列/行SHA全部相同、revision=0005、设置及160原件一致、formal_upgrade=false；本轮只运行上述私有测试。此项明确是读取主线程原始证据，不伪称独立重跑。 |
| 当前过gate事件调用真实服务；参考/预期/未来不入Agent；REQ-002/006/010/011，SCOPE-010/015 | 完整实现 | `evaluation/journey_driver.py:39` 固定controller路径、`:179` 只送允许delivery字段；`journey_gates.py:66` 未知gate拒绝；`service_adapter.py:17` 私有schema、`:23` 实际服务、`:42` 可注入真实runner；`service_delivery.py:18` 实际服务提交。真实Graph handoff与无出站、读取路径隔离、伪回执/错误scope/未知gate反例独立通过。 |
| gate须真实同订单行退货、合法状态转移，不用kind代替证据 | 完整实现，原MEDIUM已关闭 | `evaluation/service_gates.py:37`–42 要求同order+line未取消managed return且proof指向实际RET版本；`:49`–64 查allowed_events。`test_controller_business_gates.py:17` 跨订单/跨行拒绝及同目标正例、`:33` kind不能通过非法转移，独立通过。 |
| 72项逐项报告、实际编号/时间、81文字checkpoint不自动PASS | 工程报告已实现；完整业务验收未实现/未验 | `reporting.py:12` 实际run/gate/账本证据与not_run；`:22` 状态及quality_status；`journey_gates.py:132` checkpoint要求实际run/revision/人员/证据。最新 [scenario-engineering.json](artifacts/phase10/scenario-engineering.json) 72初始化、71实际Graph，SCN-028原人工屏障actual_run=null；31in_progress/20blocked/21awaiting_checkpoint、294后续步骤not_run。JRN不冒称完成。 |
| UI真实事项/等待/消费run，多业务执行与HITL独立；REQ-009/011，CMP-004/008/009 | 完整实现 | `frontend/src/components/mail-agent/CaseIssues.vue:2`、`AgentProcessPanel.vue:71` 真实detail；`BranchFactControl.vue:5` 独立事实表单，`OperationDetails.vue:15` 集成；独立IAB实际显示OP/第2版/manual_execution与人工接管/结案分开，空提交准确提示。 |
| 丢响应按原键原参核对，原命令待确认时阻新命令；REQ-003/008/011 | 完整实现 | `frontend/src/composables/useAfterSales.ts:44` 拦新命令，`:65` 原对象retry、`:80` 保存命令；当前64项前端测试独立通过，包括丢响应/跨会话/401类错误控制；页面不暗生新操作。 |

### 本期范围与未验事项

本期对应 SCOPE-005/007/012/013/014/015/016；SCOPE-001/002/003/004/006/008/019/020/021 作为已有输入、知识、UI、图片与业务服务依赖继续使用，未扩张已交付范围。REQ-005 的发布政策同版与引用资格仍由 `application/after_sales_policy.py`/`knowledge/release_queries.py` 的既有服务复核，未新增自由模型授权；REQ-014图片已有schema/危险/来源门在执行重核继续使用，未做新图片质量验收。REQ-010完整清理/重置与REQ-013自托管观测在 DEV-PLAN Phase12/11，不能列成本期已实现；此轮未发现新增真实支付/收发、ERP写接口、独立权限后台或模型状态推进工具。

`DEV-PLAN.md:222` 的“21条JRN逐条实际运行并到人工结案，原51环节输入回归，SCN并列变体补足”验收目标仍保留。用户只调整工程推进次序；当前72初始化/首gate报告、固定两响应handoff及单测不满足这条完整业务验收。21JRN到人工结案、原51真实模型业务语义、81文字checkpoint核对、图片质量和82产品AC继续未验，按用户决定留Phase13；原Phase1/7/8质量FAIL不变。该质量验收缺口与 P10-FINAL-S1-001 确定性工程缺陷分开，不能用延期掩盖后者。

## 4. Stage 2 发现

### P10-FINAL-S2-001 — MEDIUM：条件/多单位用例第二场景未执行，全回归不能标通过

- **要求**：`AGENTS.md` 的开发测试规则和 code-review skill 的测试真实性要求；`docs/planning/PHASE-10-IMPLEMENTATION.md:12` 要求当前源码四步证据。
- **实际**：独立61项回归唯一FAIL为 `test_selection_freshness.py:62`，`current_selection` 调 `agent_fixture.py:95` components，随后 `:91` claim返回None。首个循环场景占用了全局Agent单槽，尚未收口/释放，第二个场景无法领取，断言还没走到多单位拒绝。
- **影响**：不能说 conditional/multiple units 两场景均被当前测试证明；不能把测试装配FAIL改称产品PASS或跳过。当前61项是60通过、1失败、0错误、0跳过，source_changed=false；测试前提应按真实生命周期释放首个run，或将两个场景拆成独立fixture。
- **原证据**：[backend-tests.txt](artifacts/phase10/review-final/backend-tests.txt)、[backend-tests.json](artifacts/phase10/review-final/backend-tests.json)。主线程当前旧冻结文件亦为394项/1FAIL/source_changed=true，不作为本轮最终PASS。

### 其他质量、安全与视觉结论

| 检查 | 结论与证据 |
|---|---|
| 文件大小/类型/职责 | 当前69个变更程序文件最大291行，超过300为0，清单见独立code-audit.json。新TS用具体interface/Record<string,unknown>，未发现TS any。稳定事项、选择新鲜度、事实/履约更正、event、driver/gates/reporting各有独立职责。`branch_facts.py:154`/`business_events.py:48`扫描any命中是Python内置any，不是TS绕过类型。 |
| 安全扫描 | 变更源无eval/exec、dangerouslySetInnerHTML/v-html/innerHTML赋值、VITE秘密变量或常见sk密钥前缀。SQL f-string只命中`tests/test_after_sales_migration.py:26/29`及`scripts/phase3-test-server.py:61/131`的随机私有schema标识；该schema由固定phase枚举+uuid4生成，不接收邮件/HTTP值。产品服务SQL采用SQLAlchemy条件/绑定，`domain/business_events.py:9` forbid额外字段，`api/simulation.py:17`仅人工API，未注册到Agent工具。没有发现本轮安全HIGH。 |
| 错误态/幂等 | `useAfterSales.ts:26` 加载/读generation、`:82` 写generation/关联响应、`:98` 网络失败保原请求和4xx收口；`BranchFactControl.vue:70` 本地字段验证/确认取消不写，服务器过期scope错误通过API错误路径。独立实际空提交保留表单且显示“请填写订单行、记录人、回执、依据和非负原事实版本。”；无死引导。 |
| 测试真实性 | 旧地址、跨订单gate、成功纠错/unknown→明确未执行等当前真实PG反例均通过。跨订单gate单测是构造当前账本的函数反例，不冒称完整HTTP旅程；journey/services使用真实Graph但固定候选响应，不冒称模型语义通过。新重确认反例补到了已有否定用例漏测的正确认方向。唯Stage2测试槽问题见上，当前全套未通过。 |
| 实际邻居视觉对照 | 独立IAB打开15174真实工作台，展开CaseIssues、相邻CaseMemory/BusinessDetails/OperationDetails/HumanReview，新增卡片与邻居同为text-sm标题、text-xs说明、Element Plus折叠/按钮/输入，边线、间距和抽屉密度一致；实际库存表单与邻居控制台同一表单体系，错误alert靠近提交。参考代码 `CaseIssues.vue:2`、`CaseMemoryPanel.vue`、`BranchFactControl.vue:5`；独立截图观察没有新增字体/颜色体系。 |
| 明暗与宽窄 | 独立当前IAB在右栏折叠宽度实际使用详情抽屉；另逐图查看主线程保存的1440宽明/暗、390暗截图，新卡片文字可读且与邻居一致，[browser-observation.txt](artifacts/phase10/browser-observation.txt)的实际documentWidth=viewportWidth。当前独立浏览器只验证明主题及抽屉，明暗/390数值明确来自主线程原始浏览器证据，不冒充独立再次测量。 |
| Spec漂移 | branch-facts人工事实命令、增量事件列、CaseIssues和连续驱动均对应Phase10/REQ-011，不构成另建ERP或真实履约；模拟执行与HITL入口分开，未发现本轮scope creep。 |

## 5. 独立命令与原输出

后端命令：`globalmail-agent/backend/.venv/Scripts/python.exe tmp/phase10-review-final-tests.py test_business_waits test_agent_waits test_continuous_fulfillment test_selection_freshness test_controller_business_gates test_journey_driver test_scenario_driver test_journey_services test_after_sales_migration test_after_sales_cancellation test_human_events`，退出码1，原输出结尾：

```text
FAIL: test_conditional_full_refund_or_multiple_units_cannot_bind_ambiguous_natural_choice (test_selection_freshness.SelectionFreshnessTests.test_conditional_full_refund_or_multiple_units_cannot_bind_ambiguous_natural_choice)
AssertionError: unexpectedly None
----------------------------------------------------------------------
Ran 61 tests in 150.316s

FAILED (failures=1)
```

期间Alembic旧向量列reflect出现 `SAWarning: Did not recognize type 'public.vector' ...`；迁移旧值比对及重复upgrade测试仍通过。警告未被删除或当失败掩盖。

独立新缺陷命令：`globalmail-agent/backend/.venv/Scripts/python.exe tmp/phase10-reconfirm-repro.py`，退出码0；原输出（缺陷断言，不是产品PASS）：

```text
RECONFIRM_REUSED_BUT_EXECUTION_DENIED OP-9cba2afd2b384a2db1cb56c59325c45f operation_reused selection_superseded
Ran 1 test in 5.837s
OK
```

前端命令在 `globalmail-agent/frontend` 独立运行 `pnpm test` 和 `pnpm build`，均退出0。原输出：

```text
ℹ tests 64
ℹ suites 0
ℹ pass 64
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2941.254

$ vue-tsc --noEmit && vite build
vite v7.1.7 building for production...
✓ built in 28.39s
```

完整输出见 [frontend-tests.txt](artifacts/phase10/review-final/frontend-tests.txt)、[frontend-build.txt](artifacts/phase10/review-final/frontend-build.txt)。独立编译命令 `globalmail-agent/backend/.venv/Scripts/python.exe -m compileall -q globalmail-agent/backend/src globalmail-agent/backend/migrations`：**退出0，stdout/stderr为空**。没有用无输出编造条目数或模型验收。

## 6. 当前版本哈希及交接

| 文件（backend/src/globalmail_agent/相对路径） | SHA256 |
|---|---|
| application/selection_freshness.py | `3afec7ddb3decf528af34e2182d69e76db100cd4fba2a2211a237680a557305c` |
| application/after_sales_selection.py | `0758b9751fa2dc1930d0fd0e7d640787b76adde00309617570a7c59546ff487a` |
| application/simulation_execution.py | `be95e67f6cbef5e26b26af4837bcf809e2939a87abc87a03054c1560ff143e2e` |
| application/waits.py | `ef4e459863b9e44f566a59f1d8945b13749d747116355c681a1b523b4fe421c3` |
| evaluation/service_gates.py | `a380900609476c659c3adba203cc22f12818bf6b8e5a38f0fc093799b2dad3c1` |

当前结论：无HIGH；Stage1有同方案重确认MEDIUM，Stage2有测试未完整执行MEDIUM；整体未通过。由主Agent修复/重跑当前冻结证据，再重新从Stage1派fresh reviewer。不能仅修测试就忽略重确认反例，也不能把21完整旅程延期解释为本轮确定性工程缺陷可以不处理。本轮没有修改初审或历史质量FAIL，没有勾任何产品AC。

报告收口时主Agent通知已针对两个MEDIUM修改执行重确认及测试fixture，正在运行新focused回归。这些修订不在上表SHA及本轮61项冻结回归中，本报告保留发现和FAIL，修后结果交下一轮fresh审查；不把收到的“已修”折算成独立验证通过。
