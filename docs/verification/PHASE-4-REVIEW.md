# Phase 4 独立审查（初审）

日期：2026-10-08。执行者：fresh code-reviewer。审查期间未修复源码、未提交、未启动或停止服务、未调用模型。本文保留本轮 FAIL；后续修复须重新从 Stage 1 派发独立复审，不覆盖本轮发现。

**结论：Stage 1 FAIL：1 项 HIGH、3 项 MEDIUM。发现 HIGH 后停止后续阶段，Stage 2 未完成、未签署通过。** 编译和现有测试均通过，但真实数据库查询投影丢失质检数量，使“收件 2 件、只质检合格 1 件”的全额退款被计算为 eligible。所有决定仍 `authorized:false`，没有发生退款或库存写入。

## 范围与方法

已读 AGENTS、`.agents/skills/code-review/SKILL.md`、`.codex/agents/code-reviewer.toml`、Product-Spec v1.13 的 REQ-002/004/005/011/014 与 5.10–5.12、数据实体/关系、DEV-PLAN Phase 4 及全部 AC 归属、AGENT-ARCHITECTURE 第 2/5/6/7/8 节、PHASE-4-IMPLEMENTATION、v1 DATA-CONTRACT、文档索引/交接及 Phase 3 最终 PASS。没有设计稿/Design-Brief，以实际复用的 Art Design Pro 页面为基线。

计划与完成标准：①逐项核对全部已跟踪改动和 untracked 新文件，给出 Spec/交付映射；②独立运行完整测试、编译、同版检查及生产可达路径的隔离 PG 反例；③检查实际 UI 与阶段边界；④只有 Stage 1 无 HIGH 才完成 Stage 2。第④步因 P4-R1 未达到进入条件。

路径简称：`B/`＝`globalmail-agent/backend/src/globalmail_agent/`；`BT/`＝`globalmail-agent/backend/tests/`；`F/`＝`globalmail-agent/frontend/src/`；`FT/`＝`globalmail-agent/frontend/scripts/`。下列路径行号对应初审源码，不能套用在后续修改上。

独立验证只创建随机 `test_protocol_*`/`test_phase2_*` schema 和临时对象目录，使用 fixture 清理；连接串从忽略目录读取，未打印。UI 使用独立 Playwright CLI 会话 `phase4_review`，只访问主 Agent 的隔离 15174/18181 服务并执行选择、展开、GET 查询及只读资格 POST。额外复现修改的是内存副本和临时 schema，未改 v1 原件或正式用户数据库。

## Stage 1：必须修复的问题

### P4-R1 · HIGH：查询丢失实际质检数量，全额退款资格计算错误

- 要求：`Product-Spec.md:452` 要求退款核对授权条件、退货核对数量；`AGENT-ARCHITECTURE.md:273` 要求按明确受影响份额校验；Phase 4 明确交付数量及证据条件（`DEV-PLAN.md:108`）。政策说明要求仓库收件/质检覆盖此次数量（`data/knowledge/v2/build_policy.py:97`）。
- 实际：`B/application/business_projection.py:7` 的 LEDGER_FIELDS 没有 `inspected_quantity`、`inspected_unit_ids`。`B/application/business_read_model.py:94` 在生成公开/资格共用账本投影时删除这两个字段。`B/domain/policy_fulfillment.py:46` 随后将未传递的质检数量默认为全部收件数量，`:48` 同样看不到质检单位标识。领域函数的数量校验因缺失上游事实被绕过。
- 独立真实 PG 复现：复制 `BASE-OUTON-04` 为 `REVIEW-PARTIAL-INSPECTION`；将该行 quantity 改为 2，退件 quantity 改为 2 且 `inspected_quantity=1`，把原可见 refund choice 显式关联该行并设置 quantity=2，其余真实初始字段不变。`FixturePackage.validate` 接受该初始数据；通过正式 `FixtureConversations.create` 装载、`BusinessQueries.eligibility_context` 读取，然后执行数量 2 / 原全行金额 / 原 USD 的退款预览。
- 结果：正式查询上下文的退件不再含 `inspected_quantity`，计算 `outcome=eligible`、`warehouse_receipt=fulfilled`、`warehouse_inspection=fulfilled`。仅把同一上下文的实际 `inspected_quantity=1` 补回后，同一命令变为 `outcome=needs_input`，质检条件为 needs_input/wait。没有使用请求伪造证据，也没有依赖模型。
- 修复标准：受控投影完整保留并校验实际质检数量/单位关联；存在局部质检时不得默认为全部通过。增加从正式 fixture→PG→查询服务→资格 API 的集成反例，分别覆盖部分质检数量和显式 inspected_unit_ids；不能只用纯函数测试替代。

复现核心代码（使用 BT/test_protocol.py:32 的随机 schema fixture，并在 finally 执行 `doCleanups()`）：

```python
s = deepcopy(f.package.scenarios['BASE-OUTON-04'])
s['scenario_id'] = 'REVIEW-PARTIAL-INSPECTION'
o = s['initial_state']['orders'][0]
l = o['lines'][0]
l['quantity'] = 2
s['initial_state']['returns'][0].update(quantity=2, inspected_quantity=1)
s['initial_state']['customer_choices'][0].update(order_line_id=l['line_id'], quantity=2)
f.package.validate(s)
f.package.scenarios[s['scenario_id']] = s
cid = UUID(f.scene(s['scenario_id'])['conversation_id'])
ctx = f.queries.eligibility_context(cid)['data']
cmd = EligibilityRequest(action='refund', order_line_id=l['line_id'], quantity=2,
                         amount_minor=l['paid_minor'], currency=o['currency'])
result = evaluate_eligibility(cmd, ctx)
```

原始结果的字段摘要（中文 label 不影响下列原始状态值）：

```text
query_projection: inspected_quantity absent; return.quantity=2
outcome: eligible
warehouse_receipt: fulfilled
warehouse_inspection: fulfilled
with_actual_inspection: inspected_quantity=1
outcome: needs_input
warehouse_inspection: needs_input, wait
```

### P4-R2 · MEDIUM：同订单重复 SKU 的目标和包裹在 UI 无法辨认

- 要求：`DEV-PLAN.md:114`、`docs/planning/PHASE-4-IMPLEMENTATION.md:10` 要求按订单行/包裹展示事实；`Product-Spec.md:310` 要求目标不明时澄清，不能随意选择。
- 实际：`F/components/mail-agent/BusinessDetails.vue:62` 用订单号+商品名+SKU作选择项 label；`BusinessOrderCard.vue:37` 也只展示商品名/SKU。`BusinessOrderCard.vue:48` 将整订单的账本放在商品行之外；`business-records.ts:93` 的记录字段没有目标 order_line_id/SKU。业务服务保存的行关联没有显示出来。
- 可复现输入为现有白名单场景 SCN-008，不需改数据。真实 PG 输出：两行 `SIM-O-SCN-008-L1` / `SIM-O-SCN-008-L1-SECOND` 都是 `H-SJJ0001-EU-WD`，两包裹分别关联这两行。API 返回 needs_input 正确，但用户看到两个相同选择项、两个无行关联的包裹，无法准确选择或核对。
- 修复标准：在同 SKU 场景显示稳定可辨认的订单行标识/序号；账本明确展示对应目标行，或逐行展示其关联记录。保留未选目标时 needs_input，不自动挑首行。

### P4-R3 · MEDIUM：历史订单过滤不覆盖其 Mock 商品行

- 要求：`Product-Spec.md:312/330/671`、`AGENT-ARCHITECTURE.md:89` 禁止把 Mock 增补注入历史事实，过滤应逐记录成立。
- 实际：`B/application/business_read_model.py:44` 排除 Mock order；`:49` 仅按 order_id 查行；`:68` 直接输出行，未检查行 source_kind。`B/adapters/fixture_ledger.py:33` 对没有独立来源字段的行默认写 synthetic。
- 独立 PG 复现：复制 SCN-029 为 `REVIEW-HISTORY-SOURCE`，仅将 order.source_kind 设为 historical_order_snapshot、snapshot_at 设为 `2026-10-08T09:00:00+08:00`，保留原 synthetic line；加载器接受，查询返回 `status=ok, order_source=historical_order_snapshot, line_source=synthetic, sku=H-CTD16-US-BK`。
- 此项没有夸大为现有真实客户数据已泄露：72个标准初始场景的 SCN-029 仍拒读，当前也没有可授权的真实订单快照。问题是加载/查询契约接受混合来源行；已有未来快照单测只改 order 来源且设未来时间，未覆盖合法时间的混合来源。
- 修复标准：历史逐订单行拒绝 Mock/无合规来源的增补；记录来源不能仅从父订单继承信任。合法父订单但无合法行应明确缺口，不返回 synthetic SKU，并增加真实 PG/API 回归。

### P4-R4 · MEDIUM：业务详情没有展示实际客户选择

- 要求：`Product-Spec.md:577` 的 CMP-008 要展示客户选择、金额/数量及等待条件；本阶段已经读取并以可见选择判断资格（`DEV-PLAN.md:108`），详情需要让人工能够核对所用事实。
- 实际：`B/application/business_queries.py:72` 的公开明细没有 customer_choices，`F/api/business-contract.ts:66` 没有对应字段，`F/components/mail-agent/BusinessDetails.vue:33` 没有实际选择呈现。资格表单中的 action/金额/币种是人工候选输入；条件 label 仅称已接受或缺资料（`B/domain/policy_conditions.py:79/81`），无法看到接受了哪项方案、多少金额、哪种币种、哪一行、哪封可见消息。
- 可复现为 `BASE-OUTON-04`：初始可见选择为 refund / 5499 / USD（BT/test_business.py:66 查询该实际scene）；公开详情只有订单/账本/政策，浏览器没有这条实际选择卡或字段。此项不要求完成正式模型理解或Phase9执行，只要求展示本阶段已参与计算的服务端事实。
- 修复标准：通过受控白名单输出当前可见、当前范围内的选择，并展示动作、数量、金额/币种、商品行及来源消息；缺失关联明确标记，不能将单行补关联规则扩展到多行。候选表单不得被展示为客户已接受。

## Stage 1：已实现与部分实现的逐项证据

“完整”只表示本阶段约定子能力通过；未发生售后执行，不把产品全量目标提前勾选。

| 需求/交付 | 本轮结论及代码/验证证据 |
|---|---|
| 白名单加载、来源摘要、禁止未来故事/答案 | 本期完整。B/adapters/fixture_loader.py:30/45 只读10个固定原件；:47 拒非dev，:50/53投影初始字段；BT/test_business.py:29 实际拦截 Path.read_bytes 精确核对路径，:85装载72个初始场景；BT/test_business_api.py:63 禁止controller/answer字段。没有读取未来文件。 |
| 商品/配件/兼容/库存精确来源 | 本期完整。B/adapters/fixture_loader.py:157按原SKU/part登记，B/domain/inventory.py:4精确硬件关系；B/application/business_queries.py:114/116/137精确item/region/hardware，BT/test_business.py:190验证当前分支且无全局库存回退。 |
| 来源快照不可变、frozen 0003 | 本期完整。migrations/versions/0003_business_catalog.py:167/175/179禁止改来源及订单/商品/适配/同版政策说明；BT/test_business.py:142实际 UPDATE失败，说明冻结失败；独立 compare_metadata=[]。迁移定义不引用动态业务 schema。 |
| 模式/客户/分支、brand/SKU复合关系 | 本期完整。B/adapters/business_schema.py:15/59/69/71/97/110/121包含scope及order/line关系；BT/test_business.py:142拒跨客户shipment.operation和错行execution，BT/test_postgres.py:92各scope维度拒绝。 |
| REQ-002 同一截点、空截点无回退 | 基础读取完整，混合来源行见P4-R3。B/application/business_read_model.py:27历史只取cursor，:40无截点即unavailable，:44/:84时间过滤；BT/test_business.py:108确认真实首信Oct8，而非资料Sept1 clock，:118未来order不能泄露SKU。正式模型/历史知识查询仍Phase7/6。 |
| REQ-004 当前身份、精确订单号、多行澄清 | API本期完整，UI重复SKU辨识见P4-R2。B/application/business_queries.py:41/82/84/89无目标needs_input、越权denied；api/business.py:46/50严格查询字段；BT/test_business_api.py:111手动同号不能读其他分支，BT/test_business.py:97多行不默认选择。订单号不套亚马逊正则。 |
| 未取得真实订单不得拼造 | 本期完整。B/application/business_read_model.py:37无branch返回空/历史不可用，公开创建只接收scene_id（api/business.py:40），既有手动会话不从商品名/group_id造订单；BT/test_business_api.py:111验证同订单号手动会话无订单。 |
| 无记录/当时不可用/未知/技术失败 | 本期完整。B/domain/orders.py:28结果语义、business_queries.py:50/64/139、api/business.py:31技术错误转503，BT/test_business_api.py:18无DB503不报无订单；BT/test_business.py:178故障error/empty分开；实UI库存5不能显示available5。 |
| 单次一致读取、纯GET/预览无业务写 | 本期完整。B/application/business_queries.py:17在begin前指定REPEATABLE READ；BT/test_business.py:211两连接穿插读仍同快照；BT/test_business_api.py:95核对messages/jobs/events/operation/execution/inventory数量不变。 |
| 场景创建独立身份/分支且幂等 | 本期完整。B/application/fixture_conversations.py:29每次dataset UUID，:63沿用写命令回执；BT/test_business.py:47同key复用、不同scene同key409、相同sender独立；初始human场景BT/test_business.py:131无job且open review。 |
| REQ-005 同版可读政策、v2独立修订 | 准备子能力完整。data/knowledge/v2/build_policy.py:26保留原业务规则及scope，:117/123绑定规则/说明/生成器/schema/v1摘要；v2 --check实际完整字节一致，BT/test_policy.py:85核对所有生成物。v1无diff，原fixture继续1.0.1（fixture_loader.py:174）。正式同版发布/RAG仍Phase6。 |
| 30/365/2000bp/7、政策范围/时间 | 本期完整。B/domain/policy.py:27严格整数和批准数值，:40范围/生效时间；BT/test_policy.py:35、test_policy_financial.py:8、test_policy_fulfillment.py:92验证无换汇、整数取整和精确窗口。 |
| REQ-011 客户选择/数量/金额/币种 | 规则完整，跨层质检数量不完整见P4-R1。B/domain/policy_conditions.py:55/69/85最新可见选择精确动作/金额币种/数量；business_queries.py:184仅单行单件补关联，多行不乱绑；BT/test_policy.py:47最新拒绝/错币/未来选择及test_policy_financial.py:17/30分摊反例。正式Agent提取/提交仍Phase7/9。 |
| 退款账本扣一次、成功/处理中/unknown占用 | 本期完整。B/domain/policy_ledger.py:38按operation收集所有execution、:79一申请只扣一次、:85跨issue份额冲突、:97汇总对账；BT/test_policy_financial.py:39真实金额7001、成功/unknown/pending及:55不重叠份额/重叠拒绝。不是执行退款验收。 |
| 收件/质检、地址版本、精确规格、安全部件 | 规则层已实现；查询质检数量失败见P4-R1。B/domain/policy_fulfillment.py:20/63/76逐份额、choice.address_version、准确SKU/地区/hardware、安全关键件；BT/test_policy_fulfillment.py:8/20/32/43/60；未进行库存占用/履约写入。 |
| REQ-014 kind区别，视觉不能当订单/金额/执行事实 | 本期规则完整。B/domain/policy_conditions.py:36 v1无映射只用可信kinds，:118缺件/推测拒绝；BT/test_policy.py:61/73订单金额仓库视觉拒绝，v2仅允许规则明确的普通缺陷证据。实际图片上传/理解/人审属于Phase8，此阶段未实现。 |
| 未发布政策和decision_id不得授权 | 本期完整。B/domain/policy.py:147固定authorized=false/unpublished，:151只摘要；B/application/eligibility.py:10只读，BT/test_policy.py:23计算纯函数且不授权，BT/test_business_api.py:95实际请求无业务副作用；未注册执行路由。 |
| 5.10/11 UI继承、状态/输入/来源/金额 | 本期查询界面完整，重复SKU行关联见P4-R2。F/components/mail-agent/BusinessDetails.vue:7/19/20/44表单/错误/加载/空；BusinessOrderCard.vue:9/21/24来源快照金额；BusinessEligibilityForm.vue:5/67/140未发布/只读/结论；BusinessAvailabilityForm.vue:39/51/66未知和零库存区分。实际浏览器见下节。 |
| 5.12 严格请求约束、不允许客户端授予身份/证据 | 本期完整。B/domain/policy.py:15 extra forbid/strict；api/business.py:24拒额外查询字段；BT/test_business_api.py:130 bool/float/负数/证据/地址/政策/as_of拒绝422；FT/business-format.test.ts:35整数/币种精度/范围输入。 |
| 会话切换/输入版本、迟到结果、场景未知结果重试 | 本期完整。F/composables/useBusinessDetails.ts:28/59 generation+contextKey，useBusinessPreviews.ts:24/45撤销旧预览；useBusinessScenarios.ts:28保留幂等命令；FT/business-workbench.test.ts:43/80/148分别覆盖晚到、错误保留输入和同键重试。 |
| runtime Phase4真实性 | 完整。B/api/system.py:27启用business_queries而agent/knowledge=false；F/api/runtime-contract.ts:40验证同契约，components/business/runtime-status.vue:48展示当前阶段；后端test_api与FT/runtime-contract.test.ts独立通过。 |
| Spec漂移/死引导 | 未发现新增超范围执行能力。创建初始场景为DEV-PLAN允许的独立模拟入口（PHASE-4-IMPLEMENTATION.md:25），不是controller；F/BusinessScenarioLauncher.vue:12/46说明初始资料和重试语义，对应实际loader/write实现。完整RAG/Agent/退款执行无误导性完成声明。 |

## 82 AC逐项归属核对

本表不勾选产品AC。`回归`指本轮既有基础协议测试通过；`部分`只验证此阶段前置；`后续`是尚未实现的正式产品断言。主归属证据为 `DEV-PLAN.md:302–318`。每个AC均有一行，不用“其余正常”替代。

| AC | 本轮结果/边界与证据 |
|---|---|
| 001 | 回归：同手动身份归组；BT/test_conversations.py:77；DEV-PLAN:306。 |
| 002 | 回归：group_id不合并身份；BT/test_conversations.py:150；DEV-PLAN:306。 |
| 003 | 回归：导入/来源去重；BT/test_conversations.py:85；DEV-PLAN:306。 |
| 004 | 部分：真实前缀隔离回归；BT/test_conversations.py:150，正式模型Phase7（DEV-PLAN:318）。 |
| 005 | 部分：历史客服与AI对照隔离回归；BT/test_conversations.py:150，正式模型Phase7（DEV-PLAN:318）。 |
| 006 | 部分：未来快照拒读BT/test_business.py:118；混合来源P4-R3；模型请求Phase7（DEV-PLAN:318）。 |
| 007 | 后续：正式Agent一次性模拟回复Phase7；DEV-PLAN:310，B/api/system.py:28 agent=false。 |
| 008 | 部分：现有命令回执去重回归BT/test_conversations.py:85；正式自动回复Phase7（DEV-PLAN:310）。 |
| 009 | 后续：正式多轮Agent记忆Phase7；DEV-PLAN:310。 |
| 010 | 部分：当前绑定可读B/application/business_queries.py:70；Agent主动复用Phase7（DEV-PLAN:310）。 |
| 011 | 部分：API多行needs_input BT/test_business.py:97；UI同SKU P4-R2；Agent澄清Phase7（DEV-PLAN:310）。 |
| 012 | 本期查询子能力通过：BT/test_business_api.py:111跨身份/手动同号拒读；主归属DEV-PLAN:307。 |
| 013 | 部分：精确库存/兼容过滤BT/test_business.py:190；RAG过滤Phase6（DEV-PLAN:309）。 |
| 014 | 后续：跨语言正式检索Phase6；DEV-PLAN:309。 |
| 015 | 后续：正式回复的未读声明Phase7/8；DEV-PLAN:310。 |
| 016 | 部分：仅白名单初始dev BT/test_business.py:29和Mock历史拒读:108；历史检索Phase6（DEV-PLAN:309）。 |
| 017 | 后续：Agent针对缺订单生成回复Phase7；DEV-PLAN:310。 |
| 018 | 部分：尝试步骤按可见消息过滤B/application/business_read_model.py:142；Agent决策Phase7（DEV-PLAN:310）。 |
| 019 | 部分：查询身份拒绝BT/test_business_api.py:111；正式模型注入回归Phase7（DEV-PLAN:310）。 |
| 020 | 后续：Agent无依据主动HITL Phase7；DEV-PLAN:310。 |
| 021 | 回归：人审中新信仅保存BT/test_conversations.py:104；初始human无job BT/test_business.py:131；DEV-PLAN:306。 |
| 022 | 部分：人工回复/下封恢复基础BT/test_conversations.py:123；正式Agent Phase7（DEV-PLAN:310）。 |
| 023 | 回归：人工结案/新信重开BT/test_conversations.py:140；Agent建议不结案Phase7（DEV-PLAN:306）。 |
| 024 | 部分：旧任务栅栏BT/test_protocol.py:190；实际模型Phase7（DEV-PLAN:310）。 |
| 025 | 部分：停止/租约中断BT/test_protocol.py:158/135；实际模型超时Phase7（DEV-PLAN:310）。 |
| 026 | 部分：持久任务恢复BT/test_protocol.py:205、只读查询无新job BT/test_business_api.py:95；正式模型Phase7（DEV-PLAN:310）。 |
| 027 | 回归：真实历史只可见前缀BT/test_conversations.py:150；DEV-PLAN:306。 |
| 028 | 回归基础：SCN028 open review/nojob BT/test_business.py:131；正式HITL Phase7（DEV-PLAN:310）。 |
| 029 | 后续：完整重置/删除Phase12；DEV-PLAN:315。 |
| 030 | 后续：知识下架/移除Phase6；DEV-PLAN:309。 |
| 031 | 后续：保留评测及指标Phase13；DEV-PLAN:316；本轮不宣称模型准确率。 |
| 032 | 部分：实际Art页面查询/抽屉可读F/BusinessDetails.vue:1，正式模型工作台Phase7（DEV-PLAN:310）。 |
| 033 | 部分：SCN025关联包裹in_transit BT/test_business_api.py:63；同SKU显示P4-R2；查件跟进Phase10（DEV-PLAN:313）。 |
| 034 | 部分：整数退款/账本BT/test_policy_financial.py:39；质检投影P4-R1；执行Phase9（DEV-PLAN:312）。 |
| 035 | 部分：退件/质检投影与规则B/domain/policy_fulfillment.py:20；P4-R1；正式创建/推进Phase9（DEV-PLAN:312）。 |
| 036 | 部分：地址/规格/库存BT/test_policy_fulfillment.py:32/43；仓库投影P4-R1；执行Phase9（DEV-PLAN:312）。 |
| 037 | 部分：精确配件/安全件/购买不授免费BT/test_policy_fulfillment.py:43/60/70；执行Phase9（DEV-PLAN:312）。 |
| 038 | 部分：独立Mock初始branch BT/test_business.py:47/85；完整业务闭环Phase9（DEV-PLAN:312）。 |
| 039 | 部分：跨issue份额冲突BT/test_policy_financial.py:55；创建时重验Phase9（DEV-PLAN:312）。 |
| 040 | 部分：unknown余额占用BT/test_policy_financial.py:39；真实写超时恢复Phase9（DEV-PLAN:312）。 |
| 041 | 部分：多订单关联B/application/business_read_model.py:115/117；变更/取消Phase10（DEV-PLAN:313）。 |
| 042 | 后续：事件唤起正式Agent Phase10；DEV-PLAN:313。 |
| 043 | 回归基础：人审事件屏障BT/test_human_events.py:58/77；连续业务Phase10（DEV-PLAN:313）。 |
| 044 | 部分：SCN029 Mock政策/订单拒读BT/test_business.py:108，混合行P4-R3；正式对照Phase7（DEV-PLAN:310）。 |
| 045 | 后续：语义多诉求Phase7；DEV-PLAN:310。 |
| 046 | 后续：条件退款与物流语义Phase7；DEV-PLAN:310。 |
| 047 | 后续：意图动态修正Phase7；DEV-PLAN:310。 |
| 048 | 后续：正式理解schema修复预算Phase7；DEV-PLAN:310。 |
| 049 | 后续：真实run/trace/usage Phase11；DEV-PLAN:314。 |
| 050 | 后续：真实Langfuse脱敏导出Phase11；DEV-PLAN:314。 |
| 051 | 后续：Langfuse故障降级Phase11；DEV-PLAN:314。 |
| 052 | 部分：新信新run基础BT/test_protocol.py:190；正式trace/不重放写操作Phase7（DEV-PLAN:310）。 |
| 053 | 后续：wait/wake业务跟进Phase10；DEV-PLAN:313。 |
| 054 | 部分：独立operation/execution/parcel BT/test_business.py:142与api:63；正式声明验证Phase9（DEV-PLAN:312）。 |
| 055 | 后续：PDF图文解析Phase5；DEV-PLAN:308。 |
| 056 | 后续：章节适用/停用检索Phase6；DEV-PLAN:309。 |
| 057 | 后续：知识失败/发布流程Phase6；DEV-PLAN:309。 |
| 058 | 部分：规则/说明冻结与摘要BT/test_policy.py:85、test_business.py:142；正式发布/检索Phase6（DEV-PLAN:309）。 |
| 059 | 后续：撤销/迟到任务Phase6与正式回复Phase7；DEV-PLAN:309/318。 |
| 060 | 后续：正文完整删除Phase12；DEV-PLAN:315。 |
| 061 | 后续：向量输入复用Phase6；DEV-PLAN:309。 |
| 062 | 后续：向量空间切换/回退Phase6；DEV-PLAN:309。 |
| 063 | 后续：PDF结构/单位/图专属步骤Phase5；DEV-PLAN:308。 |
| 064 | 后续：完整知识管理页面Phase6；DEV-PLAN:309。 |
| 065 | 部分：准确客户订单接口BT/test_business_api.py:111；图片实际提取Phase8（DEV-PLAN:311）。 |
| 066 | 部分：精确查号不猜、无目标澄清BT/test_business.py:97；图文冲突Phase8（DEV-PLAN:311）。 |
| 067 | 后续：实际视觉观察Phase8；DEV-PLAN:311。 |
| 068 | 部分：局部图缺件拒绝BT/test_policy.py:73；正式图文处理Phase8（DEV-PLAN:311）。 |
| 069 | 部分：v1/v2证据kind BT/test_policy.py:73；图像/申请Phase8/9（DEV-PLAN:311/318）。 |
| 070 | 部分：规则risk/safety件需review BT/test_policy_fulfillment.py:60；实际危险HITL Phase8（DEV-PLAN:311）。 |
| 071 | 部分：视觉不作账本证据BT/test_policy.py:61；实际截图与写入Phase8/9（DEV-PLAN:311/318）。 |
| 072 | 后续：逐图可读/技术失败状态Phase8；DEV-PLAN:311。 |
| 073 | 后续：图片接收/CID/远程拒取Phase8；DEV-PLAN:311。 |
| 074 | 部分：业务身份与历史来源检查BT/test_business.py:108/118，混合行P4-R3；图片Phase8（DEV-PLAN:311）。 |
| 075 | 后续：实际图片提示注入Phase8；DEV-PLAN:311。 |
| 076 | 后续：图片预算/usage Phase8；DEV-PLAN:311。 |
| 077 | 部分：任务旧结果栅栏BT/test_protocol.py:158；在途视觉Phase8（DEV-PLAN:311）。 |
| 078 | 后续：图片派生内容删除/恢复Phase12；DEV-PLAN:315。 |
| 079 | 后续：多图覆盖/商品关联Phase8；DEV-PLAN:311。 |
| 080 | 后续：人工视觉更正/epoch Phase8；DEV-PLAN:311。 |
| 081 | 部分：本期业务组件Art复用F/BusinessDetails.vue:1；图片预览/撤销Phase8（DEV-PLAN:311）。 |
| 082 | 后续：冻结图集逐次模型验收Phase13，Phase1原失败保留；DEV-PLAN:316/318。 |

## 实际 UI 与基线核验（Stage 1）

本实例亲自操作正常 `/workbench`，选 SCN025，打开“处理详情与人审”窄屏抽屉、展开只读条件，填写USD 3.50并核对，再查SP-SLHBC01-BL库存。当前界面显示：需人工核对（已有补偿+缺明确选择）、余额US$35.99、政策1.0.1；库存现有5/占用0，但可用数未知，缺快照/地区/硬件版本。没有把建单当发货或把库存粗数当可用数。证据为 `.playwright-cli/page-2026-10-08T02-44-41-754Z.yml`，实现 `F/BusinessEligibilityForm.vue:85/140`、`BusinessAvailabilityForm.vue:39/66`。

逐张实际 view_image：`output/playwright/phase4-business-desktop.png`、`phase4-conditions-desktop.png`、`phase4-network-error.png`、`phase4-reviewer-narrow.png`，并看 Phase3 light-wide 和 knowledge-light。已采集亮色页面的蓝色按钮、ElCard/ElCollapse/ElAlert、表单留白、边框/文字层级延续相同外壳；订单金额/时间可读，窄屏420px抽屉有滚动和关闭控件。网络错误图保留 ORDER-NETWORK-CHECK 输入且明确重试，对应 `useBusinessDetails.ts:37`。这一 UI 核验不代替 Stage 2 的完整暗色/邻居实际页面比较；发现HIGH后未继续签署该阶段。

非阻塞 LOW：`F/components/mail-agent/business-format.ts:36/50` 的展示字典尚缺 `synthetic_project_policy`、`historical_order_snapshot` 及部分资格condition code；已知模拟政策可能显示“来源未确认”，多个不同缺口可能合成“未确认的业务字段”。补齐实际服务返回值更便于核对。

## 独立验证命令与原始输出

后端（全套真实隔离PG，无skip）：

```powershell
$env:GLOBALMAIL_TEST_DATABASE_URL=(Get-Content -Raw .local-data/runtime/settings.json | ConvertFrom-Json).database_url
$env:PYTHONPATH=(Resolve-Path globalmail-agent/backend/src).Path
& globalmail-agent/backend/.venv/Scripts/python.exe -m unittest discover -s globalmail-agent/backend/tests -v
```

```text
D:\Work_Project\globalmail-agent\globalmail-agent\backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_all_statements_share_repeatable_read_snapshot (test_business.BusinessTests.test_all_statements_share_repeatable_read_snapshot) ... ok
test_every_scenario_initial_ledger_can_be_materialized (test_business.BusinessTests.test_every_scenario_initial_ledger_can_be_materialized) ... ok
test_source_snapshot_immutable_and_ledger_foreign_keys (test_business.BusinessTests.test_source_snapshot_immutable_and_ledger_foreign_keys) ... ok
test_reads_and_eligibility_do_not_execute_or_enqueue (test_business_api.BusinessApiTests.test_reads_and_eligibility_do_not_execute_or_enqueue) ... ok
test_receipt_and_inspection_must_cover_all_affected_quantity (test_policy_fulfillment.FulfillmentTests.test_receipt_and_inspection_must_cover_all_affected_quantity) ... ok
test_database_failure_and_missing_table_are_degraded (test_postgres.PostgresTests.test_database_failure_and_missing_table_are_degraded) ... protocol_worker_dependency_unavailable
ok
----------------------------------------------------------------------
Ran 79 tests in 87.603s

OK
```

该 quantity 纯函数用例虽然通过，却不能证明正式读取没有丢字段；P4-R1是本轮额外集成复现，不能用79测试通过覆盖它。版本警告与故障注入日志原样保留。

前端在 `globalmail-agent/frontend` 执行 `pnpm exec tsx --test scripts/*.test.ts`：

```text
ℹ tests 26
ℹ suites 0
ℹ pass 26
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 725.143
```

独立 `pnpm build` exit=0（以下只省略资源大小表）：

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3274 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 28.18s
```

独立 `python -X utf8 data/knowledge/v2/build_policy.py --check`：

```json
{"status":"verified","publication_status":"unpublished","artifacts":{"policies/policy-profile.json":"cf355a4031415ccccc6be439a24703b80aa7d6de9270591cc3dca34fe86bac19","policies/policy-profile.md":"05d051061c181a5809e73f2068b65dfbbce75b491b34c0c110f265317fc45b34","policy-bundle.json":"21440f5c07181c85430f86e548aff0b41d5566a74934789194de5c03075ed2f5"}}
```

```text
compileall -q backend/src backend/migrations data/knowledge/v2: exit=0, no output
git diff --name-only -- data/knowledge/v1: exit=0, no output
metadata_diffs []
multi_line_response {"status":"needs_input","lines":[["SIM-O-SCN-008-L1","H-SJJ0001-EU-WD"],["SIM-O-SCN-008-L1-SECOND","H-SJJ0001-EU-WD"]],"parcels":[["SIM-PKG-SCN-008","SIM-O-SCN-008-L1"],["SIM-PKG-SCN-008-SECOND","SIM-O-SCN-008-L1-SECOND"]]}
historical_order_accepted_with_mock_line {"status":"ok","order_source":"historical_order_snapshot","line_source":"synthetic","sku":"H-CTD16-US-BK"}
```

## Stage 2与交回路径

**Stage 2 未完成，不能宣称代码质量、安全及完整明暗/邻居视觉比较已通过。** 本轮HIGH是在跨层数量反例中发现；停止继续阶段验收。已运行的编译、测试和UI基础检查仅作为Stage1证据保存。

P4-R1/P4-R2/P4-R3/P4-R4均回主Agent按Stage1失败补实现与集成回归。修复后重新派fresh code-reviewer，从Stage1重新核对最终文件与本轮反例，再通过Stage2。当前不接受“已有测试全部通过”作为关闭依据，不签署Phase4完成，也不改变Phase1未通过、正式知识/模型/履约/事件尚未实现的产品边界。
