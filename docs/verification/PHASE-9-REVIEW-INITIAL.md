# Phase 9 初轮独立审查

日期：2026-10-09。结论：**Stage 1 FAIL；1 项 HIGH、1 项 MEDIUM。Stage 2 未执行。**

本轮使用 `.agents/skills/code-review/SKILL.md`，由 fresh code-reviewer 独立读取原文、代码与运行证据。审查范围是 `3b4fff0` 后 Phase 9 的已跟踪 diff 与未跟踪源码，排除 `.idea/` 与用户目录；不修源码、不提交、不派子 Agent。主 Agent 在发现反馈后已经开始补丁，本文件保存修前结论，不代表修后版本审查。

输入：`AGENTS.md`、`Product-Spec.md`、`AGENT-ARCHITECTURE.md`、`DEV-PLAN.md`、`docs/README.md`、`docs/planning/SESSION-HANDOFF.md`、`docs/planning/PHASE-9-IMPLEMENTATION.md`，以及场景/故障映射。测试采用 `backend/.venv`、`agent-eval/bootstrap.isolated_database_environment()`、随机私有 PostgreSQL schema 与临时 ObjectStore；审查未升级、启动或写入正式数据库，未调用付费模型。

用户已经授权先完成工程链路，Phase 1/7/8 模型语义质量、原 FAIL 与 82 项 AC/AC-082 保持未验收。该延期不构成本期重新微调模型的理由；本报告的 HIGH 是已实证的事务授权缺陷，仍属于本期完成门。依据：`Product-Spec.md:5`、`AGENT-ARCHITECTURE.md:5`、`docs/planning/SESSION-HANDOFF.md:15`。

## Stage 1 发现

### P9-H01：人工执行未与知识发布头串行，旧政策授权可以在新 epoch 已提交后产生执行效果

**HIGH，未实现必要的事务门。**

原文要求：`AGENT-ARCHITECTURE.md:283` 要求执行时再次核验当前条件；`:299` 规定发布头先于订单行/Operation/Inventory；`:315` 要求政策/知识依据与效果在同一事务复核，不能只 guard 再无保护 insert。`docs/planning/PHASE-9-IMPLEMENTATION.md:24` 要求当前政策和原方案复查、旧 decision 不能成为永久令牌。

修前源码证据（行号为本轮发现时版本；对应 SHA 可在不可变存档 `artifacts/phase9/backend-tests-351-before-policy-lock.json` 的源清单核对）：

- `backend/src/globalmail_agent/application/simulation_control.py:27` 的 `_locked()` 取得槽/分支/会话后直接锁订单行与 Operation，没有锁 KnowledgeReleaseHead。
- `backend/src/globalmail_agent/application/after_sales_policy.py:15` 调用 `head(conn, workspace)`；`knowledge/release_queries.py:9` 的默认 `lock=False`，故只是读取发布头。
- `backend/src/globalmail_agent/application/simulation_execution.py:14` 的 `recheck()` 检查上述旧 epoch 后，`:53` 插入执行记录。
- `backend/src/globalmail_agent/knowledge/releases.py:88` 的真实 `publish()` 锁 head、文档并切换 release；它不取控制台持有的任务槽。`:111` 的 rollback 同类。withdraw 在 `:138` 有 knowledge slot，因此此次证据不声称 withdraw 可以越过该槽。
- 对照：模型内部写入口 `agent/tools/after_sales.py:19` 使用 `guarded(..., lock_business=True)`，`agent/guard.py:59` 确实锁 head；问题在独立人工控制台的发布竞争。

独立真实反例：`tmp/phase9-review-race.py:21`。创建退款申请后，在真实 `published_policy()` 校验返回处设障；并发调用真实 `ReleaseService.publish()` 重发布同一不可变 build。新 release 从 epoch 1 升到 2 且 commit，然后才解除执行障碍。旧授权控制台仍成功创建一笔 accepted execution。重发布相同内容也不能豁免显式当前 epoch 门。

原始输出：

```text
test_console_execution_serializes_current_policy_epoch ... FAIL
{"schema": "test_protocol_4d4304f1b198419f807007beaa8f8039", "paid_model_calls": 0, "race": "published policy read vs console execution commit", "policy_published_before_execution_resume": true, "old_epoch": 1, "new_epoch": 2, "console_committed": true, "execution_count": 1, "execution_status": "accepted"}
AssertionError: True is not false : Stale policy authority committed after a new release was published
Ran 1 test in 6.764s
FAILED (failures=1)
```

证据：[安全摘要](artifacts/phase9/reviewer-policy-race.json)，完整 stdout 在 `tmp/phase9-review-race-output.txt`。反例只 patch 事务中途的等待，不改政策检查结果、不伪造业务效果；发生的发布和执行均由生产服务完成。schema 由原 fixture cleanup 清除。

修复要求：控制台按槽 → 分支 → 会话 → 发布头 → 订单行 → Operation/Execution → Inventory 的顺序，在同一 effect transaction 持有 head 锁并处理空头初始化；所有 recheck 复用该锁。不得等已持订单行/库存锁后才补取 head 锁。至少重验两种顺序：执行先锁头则发布等待、发布先提交则旧执行拒绝且无新增账本/事件/库存效果；覆盖 create_execution 与有实际效果的 succeeded/shipped。PostgreSQL 官方说明确认普通读取不保护当前有效性，显式行锁需要由应用用于并发一致性保护：[应用级一致性检查](https://www.postgresql.org/docs/18/applevel-consistency.html)。

### P9-M01：质检未通过/有争议时，选项与确认框仍说“质检通过”

**MEDIUM，引导真实性不匹配。**

原文：`Product-Spec.md:455` 要求状态分开、不能把一个阶段当另一结果；`:580` 的 CMP-009 要求明确模拟收件/质检结果。控制台 `ScenarioControl.vue:38` 提供 `passed/failed/disputed`，但 `after-sales-inputs.ts:8` 把 inspected 固定标成“记录仓库质检通过”；`ScenarioControl.vue:86` 的确认框直接采用该 label。

独立执行生产输入函数，选择 `reason=failed` 且提供真实模拟回执、数量，得到：

```json
{"display":"记录仓库质检通过","result":{"errors":[],"input":{"event":"inspected","receipt_ref":"review-inspection","reason":"failed","quantity":1}}}
```

生产状态保存使用真实 reason，故不是仓库账本被改成通过。修复要求：把事件名称改为“记录仓库质检结果”，确认框同时显示实际选择的通过/未通过/有争议；保留三值、数量和回执校验。

## Phase 9 逐项功能核对

下列“匹配”限于对应工程行为与所列证据，不勾选产品 AC，不替代真实模型质量或 Phase 10 连续旅程。

源码路径以下统一相对 `globalmail-agent/`，文档路径相对仓库根目录。

| 需求/完成标准 | 结论 | 源码位置与验证证据 |
|---|---|---|
| 同一账本，保留旧迁移与来源快照 | 匹配 | `backend/migrations/versions/0008_after_sales_ledger.py:63` 仅追加字段/约束/四表；`application/business_read_model.py:100` 使用原表 source_snapshot + details；真实升级保留测试 `tests/test_after_sales_migration.py:17` 在冻结全量 PASS |
| scope/FK、受影响单位与并发补偿约束 | 匹配 | `adapters/after_sales_schema.py:19`、`:28` 的组合 FK/active unit 唯一索引；`:58` 一未确定执行；真实跨分支约束拒绝 `tests/test_after_sales_migration.py:53` |
| 五类资格检查与内部申请 | 匹配，受 H01 整体阻塞 | `domain/policy.py:16` 五枚举，`application/after_sales.py:79`/`:107` 真正持久 decision/Operation；退款/退货/换货/补件/查件真实服务测试分别见 `test_simulation_executions.py:18/:66/:46`、`test_simulation_safety.py:18/:29` |
| 当前已发布 immutable 政策、source/hash、适用范围、epoch | 静态与串行检查匹配，并发执行不匹配 | `application/after_sales_policy.py:14` 检查 manifest SHA、build/原件/适用/说明 bundle、head 与撤销；`tests/test_after_sales_operations.py:13/:61` 拒绝未发布/撤销和错误数值；H01 证明效果事务缺锁 |
| 不把未发布 Phase 4 预览当授权 | 匹配 | `application/after_sales.py:40` 必经 published_policy；`domain/policy.py:147` 仅 policy_validated 能标 published；真实未发布拒绝 `test_after_sales_operations.py:13` |
| 精确当前客户订单行、issue 范围 | 匹配 | `application/after_sales.py:37`、`application/after_sales_selection.py:23` 再验行与 issue；`tests/test_after_sales_operations.py:84` 跨 scope decision 拒绝 |
| 明确无条件客户选择、可见逐字来源 | 匹配来源与字段门，语义按既定延期 | `application/after_sales_selection.py:12` 可见客户原文逐字核对，`:31` 当前理解/explicit/无 condition，金额/币种/目标/数量验证至`:59`；fixture 已核验选择路径保留；`test_after_sales_operations.py:13` 假 quote 拒绝 |
| 后续可见选择可使旧选择失效；取消用最新客户消息 | 匹配 | `application/after_sales_selection.py:61` 检查后续选择/当前理解，`:84` max(seq) 最新来源与否定/条件取消拒绝；`test_after_sales_cancellation.py:54` 实证负/条件取消不能授权 |
| 退款实付 minor、币种、余额、份额 | 匹配 | `domain/policy.py:61` 零/超额/换汇拒绝，`domain/policy_conditions.py:96` 受影响实付，`domain/policy_ledger.py:30` 原账本重算；`test_after_sales_operations.py:95` u0 份额，`test_simulation_executions.py:18` 5499 USD 与余额从 pending 转 refunded |
| 同 run/新 run/新 key/新 issue 不重复补偿 | 匹配 | `application/after_sales.py:94/:125/:155` 持久 key/plan/单位复用；`domain/policy_ledger.py:87` 跨 issue 份额互斥；`test_after_sales_operations.py:23/:44/:95` 真实 PG 数量/金额只占一次 |
| 库存/仓库允许 wait；缺身份、选择、地址、兼容/风险不能借 wait 授权 | 匹配 | `application/after_sales.py:63` wait 白名单，`domain/policy_fulfillment.py:63/:76` 地址/适配，`domain/policy.py:143` 风险；`test_simulation_safety.py:60` 库存为零同时缺地址仍拒绝 |
| 申请只预留补偿，manual execution 才占精确规格库存 | 匹配 | `application/after_sales.py:155` 只补偿行，`simulation_execution.py:54` 触发 reserve，`simulation_inventory.py:9` 精确 item/region/hardware 行锁；`test_simulation_executions.py:46` reserved 0→1→发货 consumed，库存只减一次 |
| 执行前重核政策、客户选择、地址版本、兼容和仓库 | 部分实现 | `application/simulation_execution.py:14` 从原 plan 重算；`simulation_control.py:126` label/dispatch 精确预留复查；串行行为和地址拒绝有证据；并发政策 H01 未通过 |
| unknown/failed 默认保留补偿和库存 | 匹配 | `domain/policy_ledger.py:52`、`domain/compensation.py:18` 保留；`test_simulation_executions.py:31` 和 `test_simulation_safety.py:36` 真正账本/库存断言 |
| confirmed_not_executed 需原尝试 ref+reason+明确确认才释放 | 匹配 | `application/simulation_execution.py:64` 三条件；`:75` 释放原预留；`ScenarioControl.vue:14/:33/:41` 三输入，`after-sales-inputs.ts:69` 不仅 checkbox；前端 `scripts/after-sales.test.ts:51` 与后端 `test_simulation_executions.py:31` |
| 晚到 shipped 可由 unknown 核对继续；已发货不可假确认未执行 | 匹配 | `domain/executions.py:68` 包括 unknown；`simulation_control.py:127`、`simulation_fulfillment.py:101` 查原尝试和 label；`test_simulation_executions.py:46` unknown→shipped；`test_simulation_safety.py:49` 交运后否定回执拒绝 |
| 已成功不可取消；尚无执行取消一次释放 | 匹配 | `application/after_sales.py:187` 成功拒绝/不明尝试 unknown，`:194` 释放；`test_after_sales_cancellation.py:34/:43` 核原 operation 后取消 |
| 标签、交运、送达与执行成功分开 | 匹配 | `simulation_fulfillment.py:12/:101` 独立 parcel 状态，`simulation_execution.py:87` success 必须派发证据；`test_simulation_executions.py:46` label 不授权 success；页面 `business-records.ts:36` 明确尚未交运 |
| 退货地址、包装、邮费、商家预付标签必须显式输入 | 匹配 | `simulation_fulfillment.py:45` 不默填仓库地址，merchant 还需 prepaid/tracking/carrier；`ScenarioControl.vue:17` 真表单；`test_simulation_executions.py:66` 缺资料拒绝，`test_simulation_safety.py:72` merchant 缺标签拒绝 |
| 收件/质检数量与回执分别记录，不认未收件为通过 | 匹配账本；质检确认文案 M01 | `simulation_fulfillment.py:63` 各事件数量/ref/inspection 独立检查，`simulation_control.py:110` 每次 event payload 留 ref；`test_simulation_executions.py:66` 收件前质检、缺数量均拒绝 |
| 历史模式两层只读、不灌未来事实 | 匹配 | `agent/graph.py:152` 无写 schema；`agent/tools/after_sales.py:15`、`application/after_sales.py:28` 再拒绝；控制端 `simulation_control.py:29` simulation-only；`business_read_model.py:143` 历史不取 Mock；`test_after_sales_cancellation.py:61` |
| 模拟推进器不注册模型工具 | 匹配 | `agent/tool_schemas.py:80` 仅检查/内部申请/取消；HTTP 控制端在 `api/simulation.py:8` 独立注册；有限 Graph 测试 `test_agent_after_sales.py:103` 枚举实际 requests 未含 controller |
| stop/HITL/risk/input/lease/head 等 Agent 栅栏 | 匹配本期新增入口，人工 head 竞争除外 | `agent/tools/after_sales.py:19` 与 `agent/guard.py:44` 实际事务门；`test_agent_after_sales.py:86/:94` 分别停止前拒绝与合法 commit 后保留；既有风险/预算/图片门在 351 冻结回归覆盖 |
| 效果、稳定命令映射、工具结果凭证同事务 | 匹配 | `agent/tools/after_sales.py:19/:42` 同事务 save_result，`application/after_sales.py:102` operation_commands；`test_agent_after_sales.py:48` save_result 真崩溃后 operation 0，原请求 replay 一笔且预算不重复 |
| 旧工具来源 stale，原对象/SHA 不重写，新结果 current digest | 匹配 | `agent/tools/after_sales.py:28/:38` 仅变凭证 status、列 superseded_source_ids；`application/draft_validation.py:16` 仅有效来源；`test_agent_after_sales.py:65` 原 Object 行/字节均相同、新凭证可提交等待 |
| 外部业务事件 input++/wake，人工/stop 仅记录 | 匹配基础机制，完整连续旅程留 Phase 10 | `simulation_control.py:113` 事件类别→wake；`application/waits.py:56/:71` 新版本/门禁；`test_simulation_executions.py:96` human suppressed；不声称 21 条 JRN 已完成 |
| 最新可见客户触发查询不能多行 scalar 500 | 匹配 | `application/waits.py:75` ORDER BY DESC + LIMIT 1；本期真实多消息事件以及冻结旧 wait 回归通过；未削弱原 gate |
| 按阶段开放 schema，压力先保原查询，全部正文/观察保留 | 匹配工程路径 | `agent/tool_menu.py:6` 与 `agent/graph.py:142`，压力只缩 schema；`test_agent_tools.py` 压力用例、`test_agent_menu_pressure.py:51/:69` 与真实有限售后 Graph 均在 16 专项 PASS |
| conditions 表、plan_field_map 无损，不改查询/UI DTO | 匹配 | `agent/tools/after_sales_result.py:2` 有相同键/值才打包；`tests/test_agent_after_sales.py:20` 逐字段还原所有条件/plan，不同事实不去重；列表仍 `application/after_sales_ledger.py:49` 原完整 DTO |
| 观察 JSON 解为完整对象，原严格 OutcomeReview 与独立核验门保留 | 匹配工程门，语义质量延期 | `agent/graph.py:241` 解码/compact schema 后`:253` 仍原 Pydantic，`:256` 完整 audit 与 AND；`agent/review_audit.py:55` 双格式兼容；有限 Graph 独立审核/来源测试与冻结旧 review 回归 PASS |
| 6模型/12工具/16k输入/80k累计/120秒不变 | 匹配 | `agent/graph.py:155` 预留最终独审，`:161` 16k 压力；原 budget 文件无本期 diff；页面实渲染 0/6、0/12、80,000、120s；16专项覆盖真实生产 prompt 输入压力 |
| 公开模式 interactive_simulation/historical_replay | 匹配 | `frontend/src/composables/useAfterSales.ts:17/:42` 使用公开模式；`OperationDetails.vue:16` 历史只看；前端 `scripts/after-sales.test.ts:12/:122` 使用真实公开 DTO；独立页面实际出现人工控制台 |
| 跨 scope 旧 GET/POST 不覆盖新会话 | 匹配 | `useAfterSales.ts:25/:79/:102` generation、id、mode 与读 request；`scripts/after-sales.test.ts:75/:152` 晚到原请求直接拒绝 |
| 未知响应保留原 key/payload，刷新事件消失仍可核对，核对前阻新写 | 匹配本期数据刷新路径 | `useAfterSales.ts:44/:65` 持原 RetryCommand，`OperationDetails.vue:9/:45` 独立 button/明确确认；`scripts/after-sales.test.ts:95` 原事件不可选仍重放同 key/version，`artifacts/phase9/lost-response-recovered.png` 与 `tmp/phase9-ui-retry.txt` 主 Agent 真实断回包证据 |
| 409/422 明确拒绝可当前版本重新提交 | 匹配 | `useAfterSales.ts:90` 明确4xx清原请求；`scripts/after-sales.test.ts:122` 409 后 expected_version 2→3；未把网络未知当明确拒绝 |
| 退货字段/回执、数量/库存整数校验 | 匹配 | `domain/executions.py:13/:22/:24` strict int，`after-sales-inputs.ts:30` SafeInteger/无指数或小数；`scripts/after-sales.test.ts:22/:51` 字段与非法整数拒绝 |
| 备用关联不能造成功或移动其他申请执行 | 匹配 | `application/reconciliation.py:8` existing execution/同 scope/line/kind/份额/地址/金额均匹配；`test_simulation_executions.py:81` 同键异参拒绝及已有正确关系核验；`test_simulation_safety.py:82` 跨 branch HTTP422 且 ledger/event 0 |
| 控制页加载/空/错/成功/禁用与确认真实存在 | 匹配功能，M01 除外 | `OperationDetails.vue:5/:13/:26`、`ScenarioControl.vue:79`；独立 `phase9-review` 页面实渲染内部申请/执行/物流和独立人工控制台；截图 `artifacts/phase9/reviewer-stage1-console.png`。无设计稿/Brief，本期复用 Element Plus/既有 ledger/抽屉；邻居视觉 Stage 2 未做 |
| 只做本机模拟，无真实财务/ERP/邮件、副依赖 | 匹配范围 | 新入口 `main.py:85`、`api/simulation.py:8` 只访问同一 local service；`tool_schemas.py:80` 三项内部工具；依赖锁/pyproject/package 文件无本期变更；页面明确本机模拟 |

## 全部 Spec 的范围与延期核对

| Spec 条目 | 本期结论/归属 | 原文与实现依据 |
|---|---|---|
| REQ-001 | 继承归组/导入/身份；本期新业务仍逐次 scope 验证，不宣称重做全量验收 | `Product-Spec.md:257`；`business_read_model.py:16`；`DEV-PLAN.md:274` |
| REQ-002 | 继承历史前缀与截点，售后无写权限，Mock 不进入历史 | `Product-Spec.md:274`；`business_read_model.py:28/:143`；`graph.py:152` |
| REQ-003 | 继承自动模拟发送与 cycle 唯一终局；有限退款 Graph 真申请后只出站一次 | `Product-Spec.md:289`；`tests/test_agent_after_sales.py:103`；语义质量按原延期 |
| REQ-004 | 查询精确订单行/商品、不猜 SKU；本期 create 重查 scope | `Product-Spec.md:304`；`application/after_sales.py:37`；多目标语义仍总验收待测 |
| REQ-005 | 继承不可变发布与 RAG；本期正式授权必须当前政策 bundle，人工效果 head 门未过 | `Product-Spec.md:321`；`after_sales_policy.py:14`；H01 |
| REQ-006 | 原 Graph/记忆门保留，本期 operation/plan/等待入账；多事项连续过程留 Phase 10 | `Product-Spec.md:360`；`graph.py:142`；`DEV-PLAN.md:279` |
| REQ-007 | 继承接管/新客户恢复/人工结案，业务事件保持人审抑制 | `Product-Spec.md:380`；`waits.py:63`；`test_simulation_executions.py:96` |
| REQ-008 | 原停止/预算/持久记录门继续，本期事务/重放/stale 工具来源验证；H01 为未通过点 | `Product-Spec.md:398`；`agent/tools/after_sales.py:19`；上述故障测试 |
| REQ-009 | 本期 CMP-008/009 已接入工作台抽屉和原账本；M01 文案不匹配 | `Product-Spec.md:415/:579/:580`；`OperationDetails.vue:1`；真实页面证据 |
| REQ-010 | 分支/来源隔离沿用，完整删除/重置/联合恢复尚属 Phase 12，不冒称实现 | `Product-Spec.md:430`；`DEV-PLAN.md:282/:238` |
| REQ-011 | 本期内部申请/取消/未知对账与五类模拟执行实装；H01 阻塞本期，连续组合留 Phase 10 | `Product-Spec.md:446`；`DEV-PLAN.md:193/:209`；逐项表 |
| REQ-012 | 客户选择来自当前有源理解或已核验 fixture，条件/否定受门；真实模型语义不在本期改为 PASS | `Product-Spec.md:478`；`after_sales_selection.py:31/:84`；`DEV-PLAN.md:285` |
| REQ-013 | 本期继续本地 trace/usage，真实 Langfuse/脱敏导出部署留 Phase 11，清理留12 | `Product-Spec.md:495`；`DEV-PLAN.md:286/:224` |
| REQ-014 | 图片不是退款/库存/履约授权；已有风险/来源门进入售后校验；图片语义/AC082未验收，完整清理留12 | `Product-Spec.md:513/:548`；`domain/policy.py:143`/`policy_conditions.py:36`；`DEV-PLAN.md:330` |

82 项 AC 均保持未勾选；逐编号范围核对如下，归属取 `DEV-PLAN.md:314`，不把 Phase 归属表当产品通过表。

| AC 编号（全部列出） | 本轮结论 | 证据/边界 |
|---|---|---|
| AC-001、002、003、004、005、006、021、023、027 | 前期工程继承；产品整体验收未执行 | `DEV-PLAN.md:318`；历史/归组/人审原门本期无放宽，351冻结回归 |
| AC-012 | 前期精确身份基础继承；新增决策/执行再验 scope | `DEV-PLAN.md:319`；`test_after_sales_operations.py:84`、`test_simulation_safety.py:82` |
| AC-055、063 | 前期知识工程归属，无本期解析变更；不重记产品 AC 通过 | `DEV-PLAN.md:320` |
| AC-013、014、016、030、056、057、058、059、061、062、064 | 前期知识工程归属；本期授权依赖发布完整性，H01不通过；删除完整性另见AC060 | `DEV-PLAN.md:321`、`after_sales_policy.py:14` |
| AC-007、008、009、010、011、015、017、018、019、020、022、024、025、026、028、032、044、045、046、047、048、052 | 继承 Agent/工具/运行门；已授权模型语义延期，原 FAIL 原样保留 | `DEV-PLAN.md:322`；有限 Graph/停止/来源新证据仅证明工程；AC044的售后写拒绝本期再次核对 |
| AC-065、066、067、068、070、072、073、074、075、076、077、079、080、081 | Phase 8 工程基础继承；图片模型质量仍延期，不改产品总验收 | `DEV-PLAN.md:323`；本期未移除 risk/source/evidence/预算守卫 |
| AC-069、071 | 本期补售后动作授权门：图片观察不作为实付/库存/回执；条件与当前风险仍真实复算 | `Product-Spec.md:535/:537`；`policy_conditions.py:36`、`after_sales.py:43`；工程补验不替代实际图片质量 |
| AC-034 | 工程退款申请/回执/余额/去重有真实证据；并发执行授权H01未通过 | `Product-Spec.md:464`；`test_simulation_executions.py:18`、`test_agent_after_sales.py:103` |
| AC-035 | 退货授权/寄回/收件/质检分状态工程实现；M01确认文案不匹配 | `Product-Spec.md:465`；`test_simulation_executions.py:66`；H01仍涉及效果当前政策 |
| AC-036 | 工程精确同型号/库存/地址/仓库条件实现，执行竞争H01未过 | `Product-Spec.md:466`；`test_simulation_safety.py:18/:60` |
| AC-037 | 工程指定配件/库存预留/物流/禁止无据免费与标签冒发货实现；模型连续跟进待总验收 | `Product-Spec.md:467`；`policy.py:130`、`test_simulation_executions.py:46` |
| AC-038 | 独立有源 Mock profile/真实 immutable release 工程支持；不污染原快照/历史 | `Product-Spec.md:468`；`business_read_model.py:143`、`after_sales_policy.py:14` |
| AC-039 | 同行份额跨 run/issue/key 互斥工程实现 | `Product-Spec.md:469`；`test_after_sales_operations.py:23/:44/:95` |
| AC-040 | 原命令未知/丢响应查询重放、占用保留工程实现，真实页面同key故障证据保留 | `Product-Spec.md:470`；`test_agent_after_sales.py:48`、`test_simulation_executions.py:31/:81`、真实abort恢复截图 |
| AC-054 | 工程状态来源分离/成功回执要求实现；回复语义质量仍延期 | `Product-Spec.md:476`；`simulation_execution.py:82`、`simulation_fulfillment.py:101`、`graph.py:253` |
| AC-033、041、042、043、053 | Phase 10 连续多事项/异步旅程最终验收；本期保留基础 wake 与人工屏障，未宣称完整旅程 | `DEV-PLAN.md:325/:209`；`waits.py:56` |
| AC-049、050、051 | Phase 11 实际观测部署/脱敏/故障最终验收延期 | `DEV-PLAN.md:326/:224` |
| AC-029、060、078 | Phase 12 完整删除/联合恢复延期；本期只守住scope与撤销门 | `DEV-PLAN.md:327/:238` |
| AC-031、082 | Phase 13 总验收；Phase 1/7/8 原FAIL不改，参考答案不入真实模型 | `DEV-PLAN.md:328`；`Product-Spec.md:548` |

SCN-001–030、21 条 JRN、DEMO-001–017 仍按 `DEV-PLAN.md:341` 分期最终验收，工程单例不冒充完整逐旅程通过。FT-03/04/05/06 的本期证据分别是跨key/run/issue互斥、停止前/后效果、效果与凭证原子及checkpoint独立、未知占用/原key结果核对；完整重启/连续组合仍按原归属总验收。

## 编译与测试原始结果

审查者实际执行 `backend/.venv/Scripts/python.exe -m compileall -q src tests migrations`：**exit_code=0，stdout/stderr 为空**。编译仅说明语法通过，不关闭 H01。

主 Agent 的完整冻结后端快照在反例提出前完成，原始汇总：

```text
{"method": "all_60_modules_in_four_independent_processes_private_PG_schemas", "expected_tests": 351, "exit_codes": [0, 0, 0, 0], "tests": 351, "failures": 0, "errors": 0, "skipped": 0, "source_changed": false, "duration_seconds": 311.375, "successful": true}
```

来源：不可变存档 `artifacts/phase9/backend-tests-351-before-policy-lock.json`、四个 `backend-group-0..3-before-policy-lock.txt/json`。当前 `backend-tests-frozen.json` 留给修后352项全量，不能作为这份初轮351项证据。前两个旧 full 文件含历史错误/运行中源码变化，不用它们冒充冻结结果。351项全部通过仍未覆盖本轮发布竞争，不能覆盖独立 FAIL。主 Agent 修 H01 后需要新的源稳定证据。

16项专项原始摘要：`tests=16, failures=0, errors=0, skipped=0, duration_seconds=63.35899999993853, source_changed=false`，来自 `artifacts/phase9/focused-tests-final.json`，覆盖压力菜单、有限售后 Graph、原子效果/凭证、模拟执行等。

本轮发现时已读取的主 Agent 前端原始输出摘录（修后同名产物可能被更新，此处保留当时输出）：

```text
ℹ tests 61
ℹ pass 61
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ duration_ms 2616.8466
✓ built in 26.22s
```

当时来源：`tmp/phase9-frontend-tests-final.txt`、`tmp/phase9-frontend-build-final.txt`；package 脚本为 `vue-tsc --noEmit && vite build`。本轮质检标签反例发生于此输出之后，该输出不关闭M01。页面原 shipped/delivered 缺回执字段的问题由主 Agent 已发现并开始修复；本轮读到 `ScenarioControl.vue:14` 和 `after-sales-inputs.ts:41/:64` 已加入对应字段/必填反例，完整真实页面重验由主 Agent继续，不将原缺口掩写为始终通过。

正式库只读保旧摘要来自 `artifacts/phase9/formal-readonly.json`：revision `0005_knowledge_index`、54表各旧列/行/SHA一致、设置与160原件字节保持。审查者只在私有 schema测试。

## Stage 2 与修复路由

**Stage 2 未执行。** 根据 code-review skill，Stage 1 存在 HIGH 时停止，不做本轮代码质量、安全扫描、测试真实性完整抽查和邻居页面视觉对比；本期单页 Stage 1 控件实渲染不算 Stage 2 视觉通过。

未发现独立新增业务范围：新增表/API/工具/控制台对应 `DEV-PLAN.md:195` 的明确交付；Stage 2 更完整的漂移/安全审查仍待修后执行。本轮没有把未经验证的风险猜测写成安全问题。

修复路由：主 Agent 通过 dev-builder/bug-fixer 修 H01 的控制台效果事务和M01的真实质检确认文案，保留本报告/原FAIL/源快照；补真实竞争与三值UI反例、更新稳定测试和编译证据后，重新派 fresh reviewer 从 Stage 1 起。不能把模型质量延期当作绕过 H01 的授权。

主 Agent 已报告补入同顺序发布头行锁、真实并发回归及质检结果文案，并重跑专项和前端；这些是修后工作，未经本轮重新审查，不改变本报告的初轮 FAIL。后续 fresh reviewer 应读取修后源码与新352项源稳定证据，从 Stage 1 独立开始。
