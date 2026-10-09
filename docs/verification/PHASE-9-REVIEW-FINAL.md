# Phase 9 fresh 独立最终审查

日期：2026-10-09。审查基线：`3b4fff08cf116740d4fe3b5d4b1440cc1b7e1c54`，包含 Phase 8 `6b55d03` 与获准汇报规则。本报告审查全部本轮 tracked diff、未跟踪源码及迁移，排除 `.idea/`。审查者未修源码、未提交、未派生子 Agent；仅编写独立临时反例、操作隔离测试页面和保存本报告/证据。

**结论：Stage 1 本期工程 PASS；Stage 2 PASS。当前审查范围内 HIGH 0、MEDIUM 0、LOW 0。** 初轮 H01 政策发布竞争、M01 质检误标已由独立反例和真实页面关闭。[初轮 FAIL](PHASE-9-REVIEW-INITIAL.md) 与[修前竞争 JSON](artifacts/phase9/reviewer-policy-race.json)保留原结论，未覆盖、未重跑原脚本。

此结论只覆盖 Phase 9 已授权的工程边界。Phase 1/7/8 模型质量原 FAIL、82 项最终产品 AC、AC-082、Phase 10 连续旅程、Phase 11 实际观测、Phase 12 完整清理恢复及 Phase 13 总验收仍未完成。有限模型响应验证真实程序路径，不证明付费模型语义质量。依据 `DEV-PLAN.md:193/:209/:224/:238/:254/:314`、`Product-Spec.md:743/:786`。

## 审查输入与方法

审查者自行完整读取 `AGENTS.md`、`.agents/skills/code-review/SKILL.md`、`Product-Spec.md`、`AGENT-ARCHITECTURE.md`、`DEV-PLAN.md`、`docs/README.md`、`docs/planning/SESSION-HANDOFF.md`、`docs/planning/PHASE-9-IMPLEMENTATION.md`、`docs/verification/PHASE-9-VALIDATION.md`、`docs/verification/PHASE-9-REVIEW-INITIAL.md`。按 code-review skill 先完成 Stage 1；没有剩余 HIGH 后才执行 Stage 2。无本期 Design Brief/设计稿，UI 基准为 `Product-Spec.md:550/:586/:767` 及既有工作台、人工区、知识页面。

除文档外逐文件读取本轮 70 个应用/测试/脚本/提示/模块文档变更，原始路径、行数、SHA 见[独立审计清单](artifacts/phase9/reviewer-final-audit.json)。后端下文的 `application/`、`agent/`、`domain/`、`adapters/`、`api/` 相对 `globalmail-agent/backend/src/globalmail_agent/`；`tests/` 相对 `globalmail-agent/backend/`；前端组件相对 `globalmail-agent/frontend/src/components/mail-agent/`。`useAfterSales.ts` 固定指 `globalmail-agent/frontend/src/composables/useAfterSales.ts`；前端表内 `frontend/` 前缀相对 `globalmail-agent/`。审查清单是当前实际文件清单，未将 evidence runner 当应用新增功能。

独立后端运行通过 `bootstrap.isolated_database_environment()` 获取测试配置，使用真实 PostgreSQL 随机私有 schema 与独立 ObjectStore。独立 UI 使用本轮修后 15174/18181 服务、自己的 `phase9-review-final` 浏览器会话和 `phase9_browser_440e46cb193947389184f06019a706cc` 私有 schema。manual Agent worker 关闭、模型未配置、付费模型请求 0；未升级、启动或向正式 0005 库写测试资料。浏览器会话已关闭。

## Stage 1：本期逐条实现核对

| 要求及原文位置 | 当前结论 | 源码与实证 |
|---|---|---|
| 五类 refund/return/replacement/spare_part/logistics 的资格、申请、查询、取消；`Product-Spec.md:446/:816`，`DEV-PLAN.md:193` | 完整实现 | `domain/operations.py:15/:20/:24`，`application/after_sales.py:27/:108/:168`，`application/after_sales_ledger.py:24`，`api/after_sales.py:8`；独立运行 `tests/test_after_sales_operations.py`、`test_after_sales_cancellation.py`、`test_simulation_safety.py`，覆盖五类真实 PG 效果 |
| 模型仅申请，人工控制器不得注册模型工具；`Product-Spec.md:797/:798/:803` | 匹配 | `agent/tools/after_sales.py:11/:14` 只三种内部动作；`agent/tool_schemas.py:80` 与独立 `api/simulation.py:8`；`tests/test_agent_after_sales.py:103` 实际有限 Graph 请求与工具菜单不含 simulation controller |
| 准确当前订单行、客户身份/分支/模式，不能猜首行；`Product-Spec.md:304/:817` | 匹配 | `application/after_sales.py:28/:37`、`after_sales_selection.py:12/:22`；独立 `test_agent_tools` 多商品/跨客户/伪造参数反例及 `test_simulation_safety.py:82` HTTP 跨分支反例 |
| 当前订单份额/数量/实付 minor/币种，金额不能来自图片；`Product-Spec.md:454/:464/:535` | 匹配 | `domain/compensation.py:9`、`domain/policy.py:143`、`application/after_sales_selection.py:44/:52`；`tests/test_after_sales_operations.py:44/:60/:95` 精确份额、超额/错币种、图片数字反例；退款真成功使用原申请 5499 minor USD |
| 明确无条件客户选择，逐字可见原文引用，后续否定/条件不能沿用旧同意；`Product-Spec.md:478/:816` | 工程门匹配；模型语义延期 | `after_sales_selection.py:12/:31/:62/:72`、`application/understanding_revisions.py:70`；独立 conditional refund、伪造 quote/来源反例没有售后写行；不将固定有源 fixture 的通过算自然语言质量通过 |
| 地址确认版本、精确硬件/地区规格兼容；`Product-Spec.md:466/:467/:610` | 匹配 | `after_sales_selection.py:78`、`application/business_queries.py:126`、`simulation_inventory.py:9`；`test_simulation_safety.py:18/:60` 缺地址/规格不匹配不能借缺货等待绕过 |
| 当前 immutable release 的政策规则、说明、来源 hash、SKU/品牌/时间/mode/split 同版；预览不可授权；`Product-Spec.md:352/:353/:455` | 匹配 | `application/after_sales_policy.py:14/:20/:32/:44/:51/:56` 重新核 manifest、build、eligible、绑定和 bundle；`test_after_sales_operations.py:13/:84` 未发布/已撤销/历史拒绝；新政策竞争反例见下表 |
| 人工实际效果必须与 publish/rollback 串行，不能验旧 epoch 后提交；`AGENT-ARCHITECTURE.md:295/:301` | H01 已关闭 | `simulation_control.py:31/:39/:40` 在 slot→branch→conversation 后、订单行/申请/库存前建立并 FOR UPDATE 锁 head，持有至 `event` 整体事务提交；独立六个真实竞争反例全部通过 |
| 内部申请只预留补偿，不扣库存；人工执行才占精确规格库存；`Product-Spec.md:458/:797/:798` | 匹配 | `after_sales.py:155` 写 compensation；`simulation_execution.py:32/:54` 与 `simulation_inventory.py:9` 执行才 reserve；`test_after_sales_operations.py:23` 与 `test_simulation_executions.py:46` 核实际库存/占用变化 |
| 同 run、新 run、新 key、新 issue 不重复补偿；`Product-Spec.md:469` | 匹配 | `after_sales.py:125` 同方案复用；`adapters/after_sales_schema.py:28` active unit 唯一索引；独立 `test_after_sales_operations.py:23/:44/:95` 跨键/轮次/事项互斥 |
| unknown/failed 保留补偿及库存，缺原尝试 ref/reason/明确 confirmed 不释放；`Product-Spec.md:470/:819` | 匹配 | `simulation_execution.py:59/:65/:75`、`simulation_inventory.py:28`、`after_sales.py:189`；独立未知/失败占用、未执行对账三条件反例；前端 `after-sales-inputs.ts:66` |
| unknown 晚到 shipped 可核对继续；已交运不能假称未执行；`Product-Spec.md:470/:476` | 匹配 | `domain/executions.py:68`、`simulation_control.py:127`、`simulation_fulfillment.py:101`、`simulation_execution.py:67`；独立 `test_simulation_executions.py:46`、`test_simulation_safety.py:49` 验真实 stock 消耗和拒绝否定 |
| 成功不可取消；确定无执行才释放/允许后续补偿；`Product-Spec.md:469/:819` | 匹配 | `after_sales.py:187/:189/:194`，`tests/test_after_sales_cancellation.py:34/:43`；未确定结果不会被新申请掩盖 |
| label_created 与 shipped/delivered、申请与 execution_attempt 分开；`Product-Spec.md:212/:476/:798` | 匹配 | `domain/executions.py:47/:60`、`simulation_fulfillment.py:12/:101`、`simulation_execution.py:82`；独立 label 不授权 success，shipped 消耗一次；`business-records.ts:36` 明示尚未交运 |
| 退件地址、包装、邮费、授权 ref 显式，merchant 必须 prepaid ref/carrier/tracking；`Product-Spec.md:465`，实施计划退货资料段 | 匹配 | `simulation_fulfillment.py:45`、`domain/returns.py:5`；`ScenarioControl.vue:14/:18/:25`、`after-sales-inputs.ts:55`；独立 merchant 缺资料拒绝；真实 UI 提交完整 customer 资料后才记录授权 |
| 仓库收件与质检实际 qty/ref 分别记录；未收件不得质检通过；`Product-Spec.md:465/:612` | 匹配 | `simulation_fulfillment.py:63/:69/:82` 校验两个独立事件；`simulation_control.py:110` 每次完整 payload（quantity、receipt_ref、reason）持久保存；passed 才增加可用质检覆盖；真实三值 UI 与账本核对见后表 |
| 质检菜单/确认框不得预称通过，数量表示受检总数；实施计划质检/数量段 | M01 及辅助标签已关闭 | `ScenarioControl.vue:36/:44/:87`、`after-sales-inputs.ts:8/:76`；实际 failed、disputed、passed 确认框分别准确显示未通过、有争议、通过；三者数量标签均为“实际收件或质检数量” |
| shipped/delivered/succeeded 必须真实模拟回执，不能仅填运单；实施计划发货回执段 | 匹配修后源 | `ScenarioControl.vue:14`、`after-sales-inputs.ts:41/:63/:64`、`simulation_fulfillment.py:107`；前端独立回归含缺回执反例；原实际 422 保存在 `browser-before-shipping-receipt-fix.txt`，不写成从未失败 |
| 已有执行单备用关联仅核原同分支/行/类型/份额，不造成功；`Product-Spec.md:580/:818` | 匹配 | `application/reconciliation.py:8`、`simulation_control.py:141`、`ScenarioControl.vue:53/:103`；独立错关联 HTTP/ServiceError 与原幂等关联测试，没有新增执行 |
| 历史模式两层只读，UI 仅查看，不读模拟未来状态；`Product-Spec.md:274/:794/:817` | 匹配 | `graph.py:152` 剔除写 schema；`agent/tools/after_sales.py:15`、`after_sales.py:28/:174`、`simulation_control.py:33` 再拒绝；前端 `OperationDetails.vue:16`；独立历史与未来快照反例 |
| stop/HITL/risk/input/source/head/budget/lease 等守门保持；`Product-Spec.md:398/:513`，架构 6.3 | 匹配 | `agent/guard.py:44/:60`、`agent/tools/after_sales.py:19`；独立 `test_agent_after_sales.py:86/:94` 停止前拒绝/合法提交后保留，`test_simulation_executions.py:96` 人审/停止只记账；完整352回归保留旧风险与预算门 |
| 效果、稳定命令映射、工具结果凭证同事务；`Product-Spec.md:398/:470` | 匹配 | `after_sales.py:94/:102`、`agent/tools/after_sales.py:19/:42`、`simulation_control.py:65/:121`；独立 save_result 真实异常后 operation=0，丢回包原键只一笔效果，预算不重复 |
| 旧 tool 对象/字节/SHA 不重写，只标 stale；当前新 digest 凭证才可提交；架构 6.3、实施计划末段 | 匹配 | `agent/tools/after_sales.py:28/:38/:42`、`application/draft_validation.py:16`；独立 `test_agent_after_sales.py:65` 断言原对象行及字节相等、旧凭证失效、新结果可提交 |
| 外部事件 input++/wake，HITL/stop 不越门；最新可见 customer 多消息查询不能 scalar 多行 500；`Product-Spec.md:838` | 本期基础完整；连续组合留10 | `simulation_control.py:113`、`application/waits.py:55/:63/:76` 使用降序 LIMIT 1；独立真实多消息/人审/停止与完整旧 waits 回归，不宣称21旅程已验完 |
| staged tool menu，压力先移非授权检查/取消，保留原查询和安全终点；全部正文/观察保留；实施计划 Graph 段 | 匹配 | `agent/tool_menu.py:6`、`graph.py:142/:164/:170`；独立生产 prompt 下 `test_agent_tools` 与 `test_agent_menu_pressure` 三项反例，完整查询仍超限时才缩安全终点 |
| conditions/plan_field_map 无损，原查询和 UI DTO 不变；实施计划结果压缩段 | 匹配 | `agent/tools/after_sales_result.py:2` 相同键/值才打包；`test_agent_after_sales.py:20` 逐字段还原全部 condition/plan，差异字段不去重；`after_sales_ledger.py:24` 列表保持完整 |
| review observation JSON 解为完整对象，原严格 Pydantic/独立 source audit 不放宽；`Product-Spec.md:616/:751` | 工程门匹配；语义延期 | `graph.py:241/:253/:256`、`review_audit.py:55`；独立16项 source/coverage/负面核验反例仍拒绝遗漏、假 quote、旧四字段、错误单位；有限 Graph 经独立审核真实提交等待 |
| 6模型/12工具/16k输入/80k累计/120秒总预算不放宽；`Product-Spec.md:764/:765` | 匹配 | 本期 `agent/budget.py` 无 diff；`graph.py:155/:161` 保留最终审核预留；实际页显示相同预算；prompt 仅去重，未追加付费语义调参；核验专属输出额度按已授权 Spec 保留 |
| 0008 additive 迁移，旧0001–7及旧数据保留，完整 scope FK/占用约束；实施步骤1 | 匹配 | `migrations/versions/0008_after_sales_ledger.py:7/:78/:86/:111` 冻结自带定义；`adapters/after_sales_schema.py:16/:28/:58`；独立真实0007旧行→0008逐列/行比对，正式库未升级 |
| public DTO mode 只能 interactive_simulation/historical_replay；`Product-Spec.md:603` | 匹配 | `frontend/src/api/after-sales-contract.ts:1`（前缀 `globalmail-agent/`）、`frontend/src/composables/useAfterSales.ts:17/:42`；测试按实际公开 DTO，不用内部simulation伪造页面前提 |
| 跨 scope 晚 GET/POST 丢弃；明确409/422保留输入可用新版本再提交；`Product-Spec.md:411/:595` | 匹配 | `frontend/src/composables/useAfterSales.ts:24/:74/:82/:95/:106`；独立前端 suite 覆盖请求顺序、切会话/模式、未知和明确拒绝；主 Agent 真实409输入保留证据已审读 |
| 未知回包保留原 payload/key/version，刷新事件消失仍可核对，核对前禁其他写；`Product-Spec.md:470`、实施计划重放段 | 匹配 | `useAfterSales.ts:43/:54/:61/:68`，`OperationDetails.vue:10/:26/:47` 原命令明确确认；独立前端和后端丢响应反例；主 Agent `browser-retry.json` 中两次请求内容/key相同、1 operation/1 execution |
| 页面 loading/empty/error/restricted/success、贴近字段验证与输入保存；`Product-Spec.md:588/:599` | 匹配本期新增控件 | `OperationDetails.vue:2/:8/:16`、`ScenarioControl.vue:49/:51/:93`、`after-sales-inputs.ts:33/:74` 安全整数与完整文档；真实页未填必填资料不发写请求，200后刷新实际账本，历史控件只读 |

### H01 六个独立真实并发反例

审查者另写新 runner，不运行会覆盖修前 JSON 的原脚本。发布使用真实 `ReleaseService.publish`；执行使用真实 `SimulationControlService.event`。执行先持锁时，仅在真实 `published_policy` 已完成后用 barrier 暂停，另一线程发布必须等待；释放 barrier 后执行 commit，再发布 epoch1→2。发布先完成时，旧授权必须拒绝，事件数、执行/退件/物流/补偿与库存读回保持原值。源码路径：`simulation_control.py:39/:40/:65/:79/:96/:121`、`simulation_execution.py:14/:32/:82`、`after_sales_policy.py:14`。

| 效果入口 | 发布先 commit | 执行先持 head 锁 |
|---|---|---|
| refund create_execution | PASS：`published_policy_required`，无账本效果 | PASS：publish future 超时仍等待；建立真实执行单 commit 后才完成发布 |
| refund succeeded | PASS：旧授权不能支付，无回执/余额写入 | PASS：成功回执 commit 后 publish 才可完成 |
| spare_part shipped | PASS：旧授权不能交运，库存/占用不变 | PASS：真实交运与 reservation=consumed commit 后才发布 |

结果：**6项、0失败/错误/跳过、37.547秒、source_changed=false**，实际六个不同随机私有 PG schema，paid_model_calls=0。[当前源 SHA/结果](artifacts/phase9/reviewer-final-policy.json)、[原始日志](artifacts/phase9/reviewer-final-policy-output.txt)、[独立 runner](artifacts/phase9/reviewer-final-policy-runner.py)。原较广70项 runner 中库存读回过滤使用了错误的 conversation_id；独立六项复制新 runner 已改按真实 branch_id 读取，再执行并保存新文件。没有用错误过滤的空集当本表库存不变证据，也未改写旧70项原始记录。

### 本轮修后实际 UI 质检与成功回执

failed 会话由本轮真实页面推进建立执行、完整退货资料、实际收件；另外两个 reviewer 专用 return seed 使用同一严格真实 fixture/业务服务先准备至收到货，随后只通过真实页面选择质检并确认 HTTP 请求。不是 mock DOM，也未用直接数据库修改代替质检事件。源证据为 `ScenarioControl.vue:36/:44/:87`、`simulation_fulfillment.py:63`、`domain/executions.py:60`。

| 页面选择 | 确认框实际文案 | HTTP/实际账本 | 后续安全状态 |
|---|---|---|---|
| 未通过 | 记录仓库质检结果 · 未通过 | 200，inspection=failed，数量1，`REVIEW-INSPECTION-FAILED` | allowed_events 不含 succeeded；不能重复覆盖原质检结果 |
| 有争议 | 记录仓库质检结果 · 有争议 | 200，inspection=disputed，数量1，`REVIEW-INSPECTION-DISPUTED` | allowed_events 不含 succeeded |
| 通过 | 记录仓库质检结果 · 通过 | 200，inspection=passed，inspected_quantity=1，`REVIEW-INSPECTION-PASSED` | 允许成功；再经真实页面记录成功 HTTP200，1申请/1执行，`REVIEW-RETURN-SUCCEEDED` |

三值都显示当前“实际收件或质检数量”，failed/disputed 不把数量称为合格。[实际 HTTP 摘要](artifacts/phase9/reviewer-final-browser.json)，原始响应分别为 [failed](artifacts/phase9/reviewer-final-ui-inspection-failed.txt)、[disputed](artifacts/phase9/reviewer-final-ui-inspection-disputed.txt)、[passed](artifacts/phase9/reviewer-final-ui-inspection-passed.txt)、[后续成功](artifacts/phase9/reviewer-final-ui-return-success.txt)。确认框截图：[未通过](artifacts/phase9/reviewer-final-inspection-failed-confirm.png)、[有争议](artifacts/phase9/reviewer-final-inspection-disputed-confirm.png)、[通过](artifacts/phase9/reviewer-final-inspection-passed-confirm.png)。

## Stage 1：完整 Spec 范围与延期核对

以下核对所有 REQ，不将本期工程结论扩为完整产品验收。原始模型质量 FAIL 保持；“继承”表示未改变原实现契约并审查当前回归证据，不表示本轮重做了付费语义评测。

| Spec 条目 | 当前分类/本期结论 | 对应源码/边界 |
|---|---|---|
| REQ-001 (`Product-Spec.md:257`) | 前期工程继承 | `application/conversations.py:40` 与原导入/归组回归；售后新增 scope 不更改身份归组；完整352回归 |
| REQ-002 (`:274`) | 前期只读/截点继承，本期写门再次实测 | `application/business_read_model.py:143`、`agent/graph.py:152`；独立历史未来快照/写拒绝 |
| REQ-003 (`:289`) | 自动模拟终局工程继承，售后有限 Graph 贯通；语义部分延期 | `tests/test_agent_after_sales.py:103` 实际一次申请/一次出站/登记等待；无真实邮件发送工具 |
| REQ-004 (`:304`) | 精确身份/行工程继承，本期写入重新核验 | `application/after_sales.py:37`、`tests/test_agent_tools.py` 多行/外单反例；多目标语义最终验收仍未通过 |
| REQ-005 (`:321`) | 发布/RAG工程继承，售后同版来源授权完整 | `application/after_sales_policy.py:14`；H01六反例关闭；删除清理留12，跨语言命中语义不改原结论 |
| REQ-006 (`:360`) | 工程记忆/等待基础继承，本期 staged tools 实装；多事项组合部分未实现 | `agent/tool_menu.py:6`、`application/waits.py:55`；Phase10见 `DEV-PLAN.md:209` |
| REQ-007 (`:380`) | 接管/新客户恢复/人工结案工程继承，外部事件不越人审 | `application/waits.py:63`、`tests/test_simulation_executions.py:96`，UI `AgentProcessPanel.vue:74` |
| REQ-008 (`:398`) | 本期事务/重放/停止/来源/发布竞争完整 | `agent/tools/after_sales.py:19`、`simulation_control.py:31`；独立70+6及旧352工程回归 |
| REQ-009 (`:415`) | 本期 CMP008/009完整，既有页面继承 | `AgentProcessPanel.vue:73/:74`、`OperationDetails.vue:1`，实际宽/窄/明暗对比；trace实际接入留11 |
| REQ-010 (`:430`) | 分支/用途隔离继承；完整清理/联合恢复未实现 | `application/business_read_model.py:143`、`DEV-PLAN.md:238/:327`；未冒称Phase12 |
| REQ-011 (`:446`) | 本期五类申请/取消/查询/模拟执行完整；连续组合部分未实现 | `application/after_sales.py:27/:108/:168` 与上表；Phase10全旅程留后续 |
| REQ-012 (`:478`) | 有源选择、条件与否定程序门完整；真实模型语义延期 | `after_sales_selection.py:31/:72`，独立条件退款不写反例；原模型质量FAIL未覆盖 |
| REQ-013 (`:495`) | 本地 usage/trace基础继承；实际Langfuse、脱敏部署未实现 | `AgentRunPanel.vue:1`（同组件目录）、`DEV-PLAN.md:224/:326`，真实页明确观测尚未接入 |
| REQ-014 (`:513`) | 图片风险/来源/预算工程继承，本期再守交易授权；模型质量/完整清理延期 | `domain/policy.py:143`、`application/after_sales.py:43`，`DEV-PLAN.md:330/:339`；不把图片当实付或回执 |

82项 AC 保持未勾选，全部编号核对如下。`DEV-PLAN.md:314` 是分期归属，不是产品已通过清单。

| AC 编号 | 本轮分类/结论 | 原文与代码/证据 |
|---|---|---|
| AC-001、AC-002、AC-003、AC-004、AC-005、AC-006、AC-021、AC-023、AC-027 | 前期工程继承，产品总验收未执行 | `DEV-PLAN.md:318`；`business_read_model.py:143`、`graph.py:152`、`waits.py:63`；352原工程回归 |
| AC-012 | 身份工程继承，新增效果再次核验 | `DEV-PLAN.md:319`；`after_sales.py:37`、`test_simulation_safety.py:82` |
| AC-055、AC-063 | 前期知识解析工程归属，不重记产品通过 | `DEV-PLAN.md:320`；本期迁移未变知识解析实现，正式只读保旧 |
| AC-013、AC-014、AC-016、AC-030、AC-056、AC-057、AC-058、AC-059、AC-061、AC-062、AC-064 | 前期知识工程归属；本期实际授权同版/head门通过，不替代知识总验收 | `DEV-PLAN.md:321`；`after_sales_policy.py:14`、`simulation_control.py:39` 与六竞争反例 |
| AC-007、AC-008、AC-009、AC-010、AC-011、AC-015、AC-017、AC-018、AC-019、AC-020、AC-022、AC-024、AC-025、AC-026、AC-028、AC-032、AC-044、AC-045、AC-046、AC-047、AC-048、AC-052 | 原 Agent/可靠性工程继承；模型语义延期、原FAIL保持 | `DEV-PLAN.md:322`；`agent/guard.py:44`、`agent/tools/after_sales.py:19`；独立有限Graph/严格审核/停止反例；AC032本期控件实际宽窄明暗核对 |
| AC-065、AC-066、AC-067、AC-068、AC-070、AC-072、AC-073、AC-074、AC-075、AC-076、AC-077、AC-079、AC-080、AC-081 | Phase8工程基础继承，图片语义质量延期 | `DEV-PLAN.md:323`；本期不删除风险/来源/附件权限门；完整352回归当前源 |
| AC-069、AC-071 | 本期再守图片不能自行授权交易的工程边界 | `Product-Spec.md:535/:537`、`DEV-PLAN.md:330`；`domain/policy.py:143`、`after_sales.py:43`，独立图片金额反例 |
| AC-034 | 工程退款申请、准确金额币种、支付回执、余额/去重通过 | `Product-Spec.md:464`；`test_simulation_executions.py:18`、`test_agent_after_sales.py:103`；create/success竞争反例 |
| AC-035 | 工程退货资料/收件/三值质检/后续成功门通过 | `Product-Spec.md:465`；`simulation_fulfillment.py:63`、`ScenarioControl.vue:87`；本轮真实三值HTTP200与成功读回 |
| AC-036 | 工程换货规格/库存/地址/仓库条件通过 | `Product-Spec.md:466`；`test_simulation_safety.py:18/:60`、`simulation_inventory.py:9`；连续模型转换留10/13 |
| AC-037 | 工程配件选择、精确库存、标签/交运/成功分开通过 | `Product-Spec.md:467`；`test_simulation_executions.py:46`、`simulation_fulfillment.py:101`；shipped竞争反例 |
| AC-038 | 模拟政策/资料独立，当前不可变manifest真实授权通过 | `Product-Spec.md:468`；`after_sales_policy.py:14`、`business_read_model.py:143` |
| AC-039 | 跨run/key/issue同份额补偿互斥工程通过 | `Product-Spec.md:469`；`adapters/after_sales_schema.py:28`、`test_after_sales_operations.py:23/:44/:95` |
| AC-040 | 原命令重放、未知占用保留、结果核对工程通过 | `Product-Spec.md:470`；`test_agent_after_sales.py:48`、`test_simulation_executions.py:31/:81`、`useAfterSales.ts:61`；实际browser-retry.json |
| AC-054 | 工程申请/执行/回执来源分离、缺证据不成功通过；回复语义延期 | `Product-Spec.md:476`；`simulation_execution.py:82`、`graph.py:253`；有限Graph不替代付费语义 |
| AC-033、AC-041、AC-042、AC-043、AC-053 | Phase10完整连续、多事项转换、乱序组合未验收 | `DEV-PLAN.md:325/:209`；本期仅 `waits.py:55` 基础，不能写成21旅程已通过 |
| AC-049、AC-050、AC-051 | Phase11实际观测/脱敏部署未验收 | `DEV-PLAN.md:326/:224`，UI明确观测未接入 |
| AC-029、AC-060、AC-078 | Phase12完整清理/联合恢复未验收 | `DEV-PLAN.md:327/:238`，本期只读正式保旧不算删除恢复验收 |
| AC-031、AC-082 | Phase13总验收与模型质量仍延期 | `DEV-PLAN.md:328/:330`、`Product-Spec.md:548/:739`；参考答案未进有限Graph请求 |

其余 Spec 区域逐条归属核对：

- `Product-Spec.md:115/:143` 全部 SCOPE/OUT 边界保持；新增接口只对应已列五类模拟售后，不新增真实支付、邮件、ERP、多用户权限后台、浏览器/Shell工具。代码证据 `agent/tools/after_sales.py:11`、`api/simulation.py:8`、`main.py:85`。
- TASK-001–008、FLOW-001–006（`:156/:171/:183/:195/:206/:212/:224`）按前期、9期申请执行、10期连续、12期清理、13期总验收区分。当前有限Graph→申请→等待、人工事件→新input基础有真实证据；多轮自然语言闭环未冒称完整。代码 `test_agent_after_sales.py:103`、`simulation_control.py:113`、`waits.py:55`。
- SCREEN-001/002、CMP-001–013（`:550/:571`）全部有分期映射 `DEV-PLAN.md:332`；本期 CMP008/009 实装，其他页面继承，CMP004真实trace留11，CMP007/013完整清理留12。代码 `AgentProcessPanel.vue:73`、`OperationDetails.vue:1`、`ScenarioControl.vue:1`；真实邻居对比见 Stage2。
- 共用状态/输入（`:588/:599`）及数据实体/关系（`:634/:664`）由新增严格 DTO、integer minor、scope FK、同账本 operation/attempt/reservation/event 实装，既有消息/知识/图片约束未变。代码 `domain/operations.py:6`、`domain/executions.py:10`、`adapters/after_sales_schema.py:16`、`after-sales-inputs.ts:33`。
- AI规格（`:616`）、依赖（`:676`）、NFR（`:700`）、ASM001–012/Q001–008（`:756/:773`）保持分期真实限制。本期无新依赖，单用户本机；反馈/字段验证/中文UI/1280及1440继承布局，900实证抽屉；当前独审验证1440/900，1280由本轮主Agent截图佐证，不冒称新的性能/吞吐/全键盘可访问性认证。预算/密钥/恢复证据见 Stage2与完整回归，模型120秒不能被有限响应测试替代实测性能。
- SCN-001–030、21条 JRN、DEMO-001–017、VIS-001–018、FT-01–18（`:719/:744`）按 `DEV-PLAN.md:341` 留完整逐例总验收。本期 FT03–06 的事务/去重/停止/未知窗口已实际测试，完整进程恢复/全部连续故事未标完成。完成清单 `Product-Spec.md:743` 仍全部未勾选。
- Agent自主性/工具/上下文/编排/观测/预算/失败/恢复（`:790/:805/:827/:836/:842/:850/:854/:858`）逐项检查本期 diff：限定内部工具、当前有源记忆、查询账本、无等待轮询、同事务提交、预算/停止门不放宽；实际Langfuse、总模型质量及删除恢复仍按原阶段。代码 `agent/tool_menu.py:6`、`agent/tools/after_sales.py:14`、`agent/graph.py:142/:241`、`application/waits.py:55`。

完整实现：本期五类内部售后及所需事务/模拟执行/UI工程。部分实现：整个产品的多轮语义、异步组合、观测、生命周期。未实现/未验收部分：上述明确延期项。未发现本期新增功能缺少 Spec 或计划依据，不以延期制造本期 HIGH。

## Stage 2：代码质量、安全、测试真实性与实际视觉

Stage1无剩余HIGH后执行本阶段，结论 PASS。

| 维度 | 结论与证据 |
|---|---|
| 文件大小/命名/职责 | 当前70个变更文件最大288行，无超过300。`agent/graph.py:1` 288行、工作台 `globalmail-agent/frontend/src/views/mail-agent/index.vue:1` 277行、`application/after_sales.py:1` 199行。领域/资格/选择/账本/库存/履约/控制器分离，迁移自带冻结定义而非导入活应用；[独立全部行数/SHA](artifacts/phase9/reviewer-final-audit.json) |
| 类型/参数 | 新TS源码无 `any`；公开mode使用ConversationMode，unknown回复先校验 envelope；`frontend/src/api/after-sales-contract.ts:1`、`useAfterSales.ts:17`（均相对globalmail-agent/）；Pydantic forbidden extra/strict quantity 与 bounded refs 在 `domain/operations.py:6`、`domain/executions.py:10`，safe integer在 `after-sales-inputs.ts:33`；独立vue-tsc退出0 |
| 错误处理/竞态 | `useAfterSales.ts:74/:82/:95` 丢弃跨scope回包、明确4xx与unknown分别处理；`ScenarioControl.vue:93` 确认期间版本变化拒绝；`simulation_control.py:65` 与 `agent/tools/after_sales.py:19` 整体原子事务，独立故障/竞争验证真实效果 |
| 密钥/XSS/危险执行 | 扫描本轮所有源码，未发现真实硬编码密钥、eval/任意命令、v-html/innerHTML/危险HTML渲染或前端VITE密钥变量。唯一api_key字面量为 `tests/test_api.py:15` 的合成 `SECRET_MARKER`，`:30` 检查HTTP响应不得含此标记；不是实际密钥。新页面由ElInput/文本绑定显示手工ref，`ScenarioControl.vue:14/:18`；无可疑实风险需要外部已知漏洞推断 |
| SQL/范围 | 新查询使用SQLAlchemy绑定条件，API UUID及服务端workspace/scope；`application/after_sales_policy.py:39`、`simulation_control.py:35`、`reconciliation.py:8`。0008的SQL为静态CHECK/受控表列定义，不接受模型SQL/路径。scope复合FK和active占用唯一约束在 `adapters/after_sales_schema.py:16/:28/:37`；跨分支、外部执行、错关联真实拒绝无事件写入 |
| 依赖/功能漂移 | pyproject/uv.lock、package.json/pnpm-lock无本期diff；新增0008/DTO/API/组件对应实施步骤1–5与`Product-Spec.md:579/:580/:816`。没有新增真实财务、通用执行或独立ERP页面；`api/after_sales.py:8`、`api/simulation.py:8`、`AgentProcessPanel.vue:73` |
| 测试前提真实性 | 新测试先真实核对/解析/索引/发布带SKU的policy；客户引用为真实可见消息，金额5499最小单位USD；不伪造model权限。`tests/after_sales_fixture.py:31/:49/:114`、`test_after_sales_migration.py:15`；实际PG迁移/约束/HTTP/对象写回，不用mock库假装事务。有限Graph只替换模型响应，生产context/menu/tool/严格review/gate照常执行，`test_agent_after_sales.py:103` |
| 故障/交互测试完整性 | 独立70项覆盖效果回执原子故障、历史/身份、未知重放/占用、停前停后、库存/地址、return docs、source audit和压力；独立6项补三个实际效果入口的两顺序竞争。前端61含跨会话晚包/原键/409与422/安全整数/三值表单；另三值真实UI HTTP200、failed/disputed不能成功。初轮未覆盖的H01由独立反例发现并补验，不能因为351绿就关闭 |
| 新控件与邻居实际渲染 | 已实际查看1440×900工作台中售后控制与人工区、900×900详情抽屉，以及知识页同宽窄；另实切暗主题看知识与售后/人工抽屉。`ScenarioControl.vue:2` 的border/spacing/text/token与 `AgentProcessPanel.vue:74` 人工区一致，ElButton/ElSelect高度、描边/禁用态沿用邻居；`views/knowledge/index.vue:4/:6/:23` 的卡片/按钮/自动换行同系。新控件未使用硬编码品牌色/独立布局。1440右栏与900抽屉均可滚到控件与人工按钮；长OP在select中缩略，实际选项/记录保留完整ID；正文和状态读得清 |

实际截图由审查者生成并亲自查看，不只统计组件复用：[宽工作台与人工区](artifacts/phase9/reviewer-final-controls-wide.png)、[窄详情抽屉与人工区](artifacts/phase9/reviewer-final-drawer-narrow.png)、[暗主题抽屉](artifacts/phase9/reviewer-final-drawer-dark.png)、[宽知识邻居](artifacts/phase9/reviewer-final-knowledge-wide.png)、[窄知识邻居](artifacts/phase9/reviewer-final-knowledge-narrow-actual.png)、[暗知识邻居](artifacts/phase9/reviewer-final-knowledge-dark.png)。早期 `reviewer-final-controls-narrow.png` 尚未打开抽屉、`reviewer-final-knowledge-narrow.png` 导航未加载完成，不用它们冒充实际目标渲染；最终对比采用上述 drawer/actual 文件。一次passed测试器因隐藏select副本strict locator失败，收紧到实际region后继续取得真实HTTP200，未当作业务失败。

## 编译与测试原始输出

审查者独立运行后端编译：

```text
globalmail-agent/backend/.venv/Scripts/python.exe -m compileall -q globalmail-agent/backend/src globalmail-agent/backend/tests globalmail-agent/backend/migrations
exit_code=0
stdout/stderr=""
```

原始记录：[reviewer-final-compile.json](artifacts/phase9/reviewer-final-compile.json)。独立前端 `pnpm build` 实际执行 `vue-tsc --noEmit && vite build`，退出0，[完整原始输出](artifacts/phase9/reviewer-final-frontend-build.txt)结尾：

```text
✓ built in 26.35s
```

独立前端原始 `pnpm test`：[完整输出](artifacts/phase9/reviewer-final-frontend-test.txt)。

```text
ℹ tests 61
ℹ suites 0
ℹ pass 61
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2441.5846
```

独立真实PG广项结果原文：[日志](artifacts/phase9/reviewer-final-tests-output.txt)、[JSON及开始SHA](artifacts/phase9/reviewer-final-tests.json)、[runner](artifacts/phase9/reviewer-final-tests-runner.py)。

```text
Ran 70 tests in 285.367s
OK
tests=70, failures=0, errors=0, skipped=0, duration_seconds=285.5,
source_changed=true, successful=true
runner_exit_code=1（全清单SHA变化触发退出，不是测试失败）
```

**70项原始source_changed=true与runner退出1保持，不能作为全源冻结通过。** 此轮中主Agent修正了数量标签，后续Vite重建还产生了被忽略的 `frontend/src/types/import/components.d.ts`（第3行Generated by unplugin-vue-components，`.gitignore:10`）。[独立SHA差异审计](artifacts/phase9/reviewer-final-audit.json)保留两个当前可比对差异，确认所有backend源码/测试/迁移SHA与70项开始时一致；手写逻辑未改。随后另行六项当前源稳定竞争证据`source_changed=false`、退出0，前端又完成当前标签的61项及类型构建。未改原70项值或借“成功测试”掩盖源变化。

主Agent完整352项回归由本审查读取runner、模块清单、四组原始日志和before/after SHA，并与当前后端源核对，作为旧模块全量回归佐证；不是审查者自己重跑352。原始摘要：

```text
expected_tests=352, tests=352, failures=0, errors=0, skipped=0
groups=[88,88,88,88], exit_codes=[0,0,0,0]
source_changed=false, duration_seconds=303.875, successful=true
```

来源：[backend-tests-frozen.json](artifacts/phase9/backend-tests-frozen.json)、[四独立进程runner](artifacts/phase9/backend-frozen-runner.py)、`backend-group-0..3.txt/json`、[236后端文件当前SHA核对](artifacts/phase9/current-source-evidence.json)。修前351PASS与两次原FAIL均保留，当前352不回写历史结论。政策专项20项0fail/skip也有独立日志，但不替代本审查六个新竞争反例。

正式数据保旧消费主Agent只读证据：[formal-readonly.json](artifacts/phase9/formal-readonly.json)：revision `0005_knowledge_index`、54表旧列/行/SHA一致、设置不变、160原件字节不变，知识22文档/22版本、build/release/cache为0。本审查所有写入均在明确私有测试schema。浏览器关闭后又读取[正式保旧及实际清理证据](artifacts/phase9/formal-readonly-and-cleanup.json)：正式基线仍一致，两个自有浏览器schema/对象目录均不存在，15174/18181已关闭，未执行正式升级。清理由主Agent实施，本审查未以计划代替完成证据。

## 最终状态

本期 Stage1功能/权限/来源/预算/事务/UI门通过，Stage2质量/安全/测试真实性/实际视觉对比通过；没有剩余本期阻塞或修复项。初轮H01/M01在当前源的独立证据关闭，原FAIL不变。隔离资源清理证据已读取；主Agent可同步验证/索引/进度并完成本地提交。本报告不将Phase9工程通过当整个产品或模型质量通过。
