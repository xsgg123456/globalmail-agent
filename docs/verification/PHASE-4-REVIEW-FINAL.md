# Phase 4 独立复审（本轮 FAIL）

日期：2026-10-08。执行者：fresh code-reviewer `phase4_review_final`。本报告记录补修前的本轮独立结论，不覆盖 [初审](PHASE-4-REVIEW.md)。主 Agent 收到新问题后开始补修，其后修改不属于本报告已验收的快照。

**Stage 1：FAIL，新发现 1 项 HIGH。Stage 2：未执行。Phase 4 不能据本报告声明完成。** 初审质检数量问题已由正式数据库→查询→资格 HTTP 反例证明关闭；但客户选择数组乱序时，最新拒绝被旧同意覆盖，资格预览错误返回 `eligible`。仍 `authorized:false`，没有执行退款或库存变更。

## 范围、计划与边界

重新读取 AGENTS、code-review SKILL、reviewer TOML、Product-Spec v1.13 REQ-002/004/005/011/014、5.10–5.12、全部 AC 归属，AGENT-ARCHITECTURE 第2/4.4/5/6/7/8节、DEV-PLAN Phase4、PHASE-4-IMPLEMENTATION、docs 索引/SESSION-HANDOFF、v1 DATA-CONTRACT及原始 FAIL。无设计稿/Design Brief；实际视觉基线为 Art Design Pro 和现有知识页。

规划：①按源文档逐项检查完整 diff/untracked；②独立真实 PG/API 验证资格、隔离和原反例；③核对 UI 交付与真实性；④Stage1没有HIGH才能签署Stage2。执行到②发现新的HIGH，按 Skill 停止④，UI最终明暗/邻居视觉验收留给下一轮，不伪造完成。

路径简称：`B/`＝`globalmail-agent/backend/src/globalmail_agent/`，`BT/`＝`globalmail-agent/backend/tests/`，`F/`＝`globalmail-agent/frontend/src/`，`FT/`＝`globalmail-agent/frontend/scripts/`。行号对应本轮发现时源码。

只在 `ProtocolFixture` 随机 `test_protocol_*` schema 与临时对象目录验证，finally 调用 `doCleanups()`。私有连接串由 `.local-data/runtime/settings.json` 读入 `GLOBALMAIL_TEST_DATABASE_URL`，未打印。仅修改内存 prepared 副本，未改 v1 字节、未写生产数据、未调用模型/事件推进/真实邮件。独立 Playwright session `phase4_review_final` 已打开隔离15174工作台，发现HIGH后关闭；未启动或停止主 Agent 服务器。

改动盘点：已检查 tracked 的 DEV-PLAN/docs索引、database/system/main注册、test_api/runtime契约与前端状态、AgentProcessPanel/ConversationList/workbench入口、phase3-test-server隔离脚本，以及全部 untracked 的12表冻结迁移、business_schema/fixture_loader/fixture_ledger、fixture_conversations、business_read_model/business_projection/business_customer_view/business_queries/eligibility/API、orders/inventory/policy/conditions/fulfillment/ledger、业务与政策测试、business API/contract、Business组件/格式/记录/选择辅助、3个useBusiness composable、v2的authoring/规则/说明/bundle/generator/README。新UI产物属于证据，不能用文件存在替代视觉核验。

## Stage 1 · 新问题

### P4-F1 · HIGH：选择数组顺序覆盖实际最新来信，客户已拒绝仍计算符合退款资格

- 需求：`Product-Spec.md:451` 要求客户选择明确后才能进入申请，`:452` 要求核对客户同意，`:469` 要求后续改变方案时核对既有选择；`DEV-PLAN.md:108` 本期交付数量/客户选择检查。`B/domain/policy_conditions.py:79` 也明确声称检查“最新选择”。
- 原因：`B/application/business_read_model.py:24` 已读取真实 message seq，`:144` 将该 seq 投影到每个选择，却保持 `branch.state.customer_choices` 原数组顺序。`B/domain/policy_conditions.py:57` 收集对应行候选，`:63` 用 `candidates[-1]`，将数组最后一项当最新选择。`B/adapters/fixture_loader.py:134` 不要求选择数组按消息顺序，也未拒绝乱序，所以此输入可走正式装载路径。
- 独立复现：深拷贝 `BASE-OUTON-04`；首封接受USD5499退款，时间 `2026-10-08T09:59:00+08:00`；添加第二封明确 `I reject that refund amount.`，时间 `10:00:00+08:00`，不晚于原clock。两条选择仅改变顺序：正常 `[旧接受,新拒绝]` 和乱序 `[新拒绝,旧接受]`。`FixturePackage.validate` 均通过；正式 `FixtureConversations.create` 保存；`BusinessQueries.detail` 证明两封均可见且seq为1/2；经实际FastAPI路由→`EligibilityService.preview`→统一查询重新读取，提交相同refund命令。没有由HTTP传同意/证据、没有手工补内部上下文。

原始输出：

```text
chronological {'as_of': '2026-10-08T02:00:00+00:00', 'choices': [(1, True), (2, False)], 'http': 200, 'outcome': 'needs_input', 'customer_choice': [{'code': 'customer_choice', 'label': '最新选择尚未明确接受此动作、数量或金额币种', 'status': 'needs_input', 'fulfilled_by': []}], 'authorized': False}
reversed {'as_of': '2026-10-08T02:00:00+00:00', 'choices': [(2, False), (1, True)], 'http': 200, 'outcome': 'eligible', 'customer_choice': [{'code': 'customer_choice', 'label': '客户明确接受此次方案', 'status': 'fulfilled', 'fulfilled_by': ['message:SIM-M-BASE-OUTON-04-1']}], 'authorized': False}
```

仅数组排列改变资格结果，已足够证实错误；不是把未来消息、未绑定订单或不可达HTTP参数当作前提。当前72个标准初始资料多数只有一条选择，本反例证明受控初始事实处理契约有缺陷，不宣称现有客户已被真实退款。未发布门禁有效并不能替代正确资格计算。

修复验收：服务端按可见消息真实seq确定最新选择，不能信fixture数组顺序；领域再次按明确序号选最新，不因最新拒绝/改变动作/目标不明回退旧同意。同序号冲突或缺可靠序号应保守返回需要补充/核对。补正式PG→统一查询→资格服务/API回归，覆盖乱序的新拒绝、改动作和歧义；重新派fresh审查，从Stage1开始。

## 初审四项修复复核

| 原问题 | 本轮证据与结论 |
|---|---|
| P4-R1 HIGH · 质检数量投影丢失 | **关闭此原问题。** `B/application/business_projection.py:7`现保留inspected_quantity/inspected_unit_ids，read_model:98共用白名单，policy_fulfillment:46按实际份额。BT/test_business_regressions.py:29是真实PG→查询→EligibilityService集成。本实例额外经正式HTTP验证见下列输出，不能用绿色纯函数替代。 |
| P4-R2 MEDIUM · 重复SKU行/包裹难辨 | **代码及关系测试通过，最终视觉未签署。** `F/components/mail-agent/BusinessDetails.vue:69`选择label增加第几项，BusinessOrderCard:37标题增加序号，:47逐行recordsForLine，business-records.ts:157按order+line同时匹配。FT/business-format.test.ts的“同订单同SKU的两行物流严格分开”实际通过。HIGH后未继续实际明暗/窄屏验收，因此不把组件class当作最终UI通过。 |
| P4-R3 MEDIUM · 历史Mock行未过滤 | **关闭此原问题。** `B/application/business_read_model.py:56`产品独立检查来源/identity_observed_at，:71逐行拒Mock，:92账本独立拒Mock。BT/test_business_regressions.py:57将SCN029父来源改合法但保留synthetic行，正式PG查询needs_input、lines=[]且响应无SKU，实际执行通过。没有改变原SCN029的Oct8初信/Sept1clock，历史截点仍来自真实cursor（read_model:29）。 |
| P4-R4 MEDIUM · 未显示实际客户选择 | **接口与组件逻辑通过，最终视觉未签署。** `B/application/business_customer_view.py:4`白名单，:13只在唯一单件行补关系；BT/test_business_regressions.py:70/92确认未来选择被过滤、数据库确有隐藏记录、地址token不公开、多行不猜。`F/components/mail-agent/BusinessCustomerChoices.vue:3`真实折叠展示，business-choices.ts:17列金额/数量/商品/地址版本，:30第几封来信。发现P4-F1说明展示来源正确仍不足以证明最新选择规则正确。 |

独立HTTP质检验证原始输出：

```text
inspection_http {'inspected_quantity': 1, 'inspected_units': None, 'http': 200, 'outcome': 'needs_input', 'inspection': ['needs_input', 'wait'], 'authorized': False}
inspection_http {'inspected_quantity': 1, 'inspected_units': ['0'], 'http': 200, 'outcome': 'wait', 'inspection': ['wait'], 'authorized': False}
inspection_http {'inspected_quantity': 2, 'inspected_units': ['0', '1'], 'http': 200, 'outcome': 'eligible', 'inspection': ['fulfilled'], 'authorized': False}
```

## Stage 1 · 交付逐项对照

| Spec/契约条目 | 结果与证据 |
|---|---|
| REQ-002可见历史前缀、真实客服/AI对照隔离、截点重建 | 本期基础回归通过。BT/test_conversations.py:150覆盖真实前缀与比较隔离；B/application/business_read_model.py:24只读visible seq；真实模型请求仍Phase7，未声称实现。 |
| REQ-002同as_of/无当前回退、未来快照和附件缺口 | 本期业务查询通过。B/application/business_read_model.py:29/42/46读取cursor，BT/test_business.py:108/118验证SCN029真实cursor和未来合法快照拒读；附件读取仍Phase8。 |
| REQ-004已有绑定/允许候选、工具订单事实/来源/时间/实时性 | 子能力通过。B/application/business_queries.py:69详情，read_model:65输出来源快照实时性、:78缺口；Agent主动复用/图片候选仍Phase7/8。 |
| REQ-004兼容ORDER/模拟号、当前身份/品牌/分支、不能从listing拼订单 | 通过。api/business.py:46仅长度约束；fixture_loader.py:82/84核对身份品牌；BT/test_business_api.py:111跨范围及手动同号拒读；无branch时read_model:39无当前订单回退。 |
| REQ-004多商品不默认首行、未知/无记录/历史不可用/技术错误分开 | 通过。B/application/business_queries.py:42、failure:51、detail:89多行needs_input；availability:139未知；BT/test_business.py:97/178与test_business_api:18实际验证。重复SKU视觉留下一轮。 |
| REQ-005资料白名单、用途隔离、不读取未来/故事/答案 | 本期通过。fixture_loader.py:31/43/47仅允许固定源和dev初始字段，BT/test_business.py:29/85与test_business_api:63覆盖72场景和禁字段。全文RAG/评测用途检索仍Phase5/6。 |
| REQ-005政策程序规则与中文说明同源同版、v2独立修订 | 本期准备能力通过。data/knowledge/v2/build_policy.py:26逐section和scope等值、:117绑定生成器/schema/v1摘要，独立--check通过；fixture_loader.py:38/174仍绑定v1。发布、检索、撤销、删除、PDF、向量空间仍Phase5/6/12。 |
| REQ-011五类查询/资格、来源区分、逐行包裹及独立申请/执行 | 本期读模型通过。read_model.py:85/94/120核验line/op/execution关联，BT/test_business.py:142、test_business_api:63返回正确包裹in_transit；创建申请/正常执行/例外闭环仍Phase9/10。 |
| REQ-011金额整数/币种/成功+pending+unknown占用、不同issue补偿互斥 | 本期规则通过。B/domain/policy_ledger.py:38收集执行、:79按申请只扣一次、:85跨份额冲突、:97对账；BT/test_policy_financial.py:39/55集成规则用例通过。真实写超时恢复仍Phase9。 |
| REQ-011数量、收件/质检、窗口、适配库存、安全件/地址版本 | 规则和原质检投影反例通过。policy_fulfillment.py:7/20/63/76分别检查；BT/test_policy_fulfillment.py:8/20/32/43/60/92通过；原数量跨层问题额外正式HTTP验证。当前缺快照/规格库存保持unknown，查询不预留库存。 |
| REQ-011客户最新选择及改方案 | **未完整实现：P4-F1 HIGH。** policy_conditions.py:63误认数组尾为最新，正式HTTP证实最新拒绝被绕过。 |
| REQ-011人审/人工回复后事件只记数据、历史不注入Mock、不连真实履约 | 本期边界通过。read_model.py:124历史提前返回；BT/test_human_events.py:58/77既有屏障回归；api/business.py:36–64仅目录/场景初始创建/查询/只读preview，无推进器或执行售后路由。事件跟进Phase10。 |
| REQ-014视觉kind不能升格订单/金额/仓库事实、政策无映射保守 | 本期规则通过。policy_conditions.py:36来源检查、:118局部图缺件拒绝；BT/test_policy.py:61/73 v1拒视觉、v2仅明确允许外观；图像接收/理解/风险HITL/缓存/撤销/预算为Phase8/12，未提前验收。 |
| 5.10/5.11业务详情Art卡片/折叠/抽屉、加载/空/错误/候选不是客户同意 | 代码/前端行为测试通过，最终视觉未完成。F/components/mail-agent/BusinessDetails.vue:7/19/20/44实际表单反馈；useBusinessDetails.ts:28/59防晚到；BusinessEligibilityForm.vue:5/67/140明确只读门禁；FT/business-workbench.test.ts会话切换、错误保留输入通过。 |
| 5.12严格请求整数、禁止extra身份/时间/政策/证据/同意 | 通过。B/domain/policy.py:15 strict+extra forbid；api/business.py:24严格查询名，BT/test_business_api.py:130 bool/float/负数与越权字段422；F/business-eligibility-input.ts精确最小单位、相关28前端测试通过。 |
| 架构一致事务、不可变来源、复合scope/订单行/执行关系FK | 通过。BusinessQueries.read:17 begin前指定REPEATABLE READ；business_schema.py:14/20/69/97/110/120/130；冻结migration0003:167不可变触发器；BT/test_business.py:142/211真实PG拒写来源/跨scope、穿插双连接一致快照通过。 |
| 未发布决策不能执行、没有scope creep/死引导 | 通过本期边界。policy.py:147固定authorized=false且decision仅摘要；eligibility.py:10纯读；BT/test_business_api.py:95比较messages/jobs/events/operations/executions/inventory数量不变；system.py:27 business_queries=true而agent/knowledge=false。场景入口仅创建允许的初始基线（实施计划:25），未宣称RAG/Agent/售后执行完成。 |

## 82项AC归属逐项核对

本表不勾选产品AC。完整断言和唯一主归属按 `DEV-PLAN.md:302`，正式模型/履约/图片等后续条件不能由工程回归替代。每项均列出；“前置”仅表示本期子能力已核对，“后续”不是本期缺陷。

| AC | 本轮状态/证据 |
|---|---|
| 001 | Phase3回归：BT/test_conversations.py:77同身份归组。 |
| 002 | Phase3回归：BT/test_conversations.py:150 group_id不合并身份。 |
| 003 | Phase3回归：BT/test_conversations.py:85去重。 |
| 004 | 前缀回归BT/test_conversations.py:150；实际模型请求Phase7（DEV-PLAN:318）。 |
| 005 | 真实客服/AI隔离回归BT/test_conversations.py:150；模型Phase7（DEV-PLAN:318）。 |
| 006 | 业务未来快照BT/test_business.py:118通过；模型请求Phase7（DEV-PLAN:318）。 |
| 007 | 后续Phase7：正式自动回复（DEV-PLAN:310）。 |
| 008 | 命令去重回归BT/test_conversations.py:85；正式回复Phase7（DEV-PLAN:310）。 |
| 009 | 后续Phase7：正式多轮记忆（DEV-PLAN:310）。 |
| 010 | 前置业务绑定B/application/business_queries.py:71；主动复用Phase7（DEV-PLAN:310）。 |
| 011 | 前置多行needs_input BT/test_business.py:97；正式澄清Phase7（DEV-PLAN:310）。 |
| 012 | 本期查询断言通过：BT/test_business_api.py:111跨客户/手动同号拒读。 |
| 013 | 前置精确适配BT/test_business.py:190；RAG Phase6（DEV-PLAN:309）。 |
| 014 | 后续跨语言检索Phase6（DEV-PLAN:309）。 |
| 015 | 后续未读内容声明Phase7/8（DEV-PLAN:310/311）。 |
| 016 | 前置dev白名单/Mock拒读BT/test_business.py:29/108；检索Phase6（DEV-PLAN:309）。 |
| 017 | 后续缺订单回复Phase7（DEV-PLAN:310）。 |
| 018 | 前置attempted_steps可见来源B/application/business_read_model.py:146；Agent Phase7（DEV-PLAN:310）。 |
| 019 | 前置跨范围拒绝BT/test_business_api.py:111；模型注入Phase7（DEV-PLAN:310）。 |
| 020 | 后续正式Agent HITL Phase7（DEV-PLAN:310）。 |
| 021 | 人审新信回归BT/test_conversations.py:104、初始人审BT/test_business.py:131。 |
| 022 | 基础恢复回归BT/test_conversations.py:123；正式Agent Phase7（DEV-PLAN:310）。 |
| 023 | 人工结案/重开回归BT/test_conversations.py:140；Agent建议Phase7（DEV-PLAN:306/310）。 |
| 024 | 基础旧任务栅栏BT/test_protocol.py:190；模型Phase7（DEV-PLAN:310）。 |
| 025 | 停止/中断BT/test_protocol.py:135/158；模型超时Phase7（DEV-PLAN:310）。 |
| 026 | 持久恢复BT/test_protocol.py:205；正式模型Phase7（DEV-PLAN:310）。 |
| 027 | 历史前缀回归BT/test_conversations.py:150。 |
| 028 | 初始人审/nojob BT/test_business.py:131；正式HITL Phase7（DEV-PLAN:310）。 |
| 029 | 后续完整删除Phase12（DEV-PLAN:315）。 |
| 030 | 后续知识下架Phase6（DEV-PLAN:309）。 |
| 031 | 后续评测指标Phase13（DEV-PLAN:316）；本轮未宣称模型准确率。 |
| 032 | UI代码前置F/components/mail-agent/BusinessDetails.vue:1；最终视觉及正式模型仍待核验（DEV-PLAN:310）。 |
| 033 | 包裹读模型BT/test_business_api.py:63；跟进Phase10（DEV-PLAN:313）。 |
| 034 | 退款账本BT/test_policy_financial.py:39；选择P4-F1失败；执行Phase9（DEV-PLAN:312）。 |
| 035 | 收件质检BT/test_business_regressions.py:29及HTTP通过；创建推进Phase9（DEV-PLAN:312）。 |
| 036 | 规格/地址/库存BT/test_policy_fulfillment.py:32/43；执行Phase9（DEV-PLAN:312）。 |
| 037 | 配件/安全件/购买用途BT/test_policy_fulfillment.py:43/60/70；执行Phase9（DEV-PLAN:312）。 |
| 038 | 初始独立Mock分支BT/test_business.py:47/85；闭环Phase9（DEV-PLAN:312）。 |
| 039 | 份额冲突BT/test_policy_financial.py:55；写前重验Phase9（DEV-PLAN:312）。 |
| 040 | unknown余额BT/test_policy_financial.py:39；写恢复Phase9（DEV-PLAN:312）。 |
| 041 | 改方案前置P4-F1失败；正式变更取消Phase10（DEV-PLAN:313）。 |
| 042 | 后续业务事件唤起Phase10（DEV-PLAN:313）。 |
| 043 | 人审事件屏障BT/test_human_events.py:58/77；业务连续跟进Phase10（DEV-PLAN:313）。 |
| 044 | 历史Mock拒读BT/test_business.py:108及regressions:57；对照Phase7（DEV-PLAN:310）。 |
| 045 | 后续语义多诉求Phase7（DEV-PLAN:310）。 |
| 046 | 后续条件退款语义Phase7（DEV-PLAN:310）。 |
| 047 | 后续理解动态修正Phase7（DEV-PLAN:310）。 |
| 048 | 后续schema修复预算Phase7（DEV-PLAN:310）。 |
| 049 | 后续真实trace/usage Phase11（DEV-PLAN:314）。 |
| 050 | 后续Langfuse脱敏Phase11（DEV-PLAN:314）。 |
| 051 | 后续观测故障降级Phase11（DEV-PLAN:314）。 |
| 052 | 新run基础BT/test_protocol.py:190；正式trace Phase7（DEV-PLAN:310）。 |
| 053 | 后续业务wait/wake Phase10（DEV-PLAN:313）。 |
| 054 | 独立申请/执行/包裹BT/test_business.py:142/api:63；正式声明校验Phase9（DEV-PLAN:312）。 |
| 055 | 后续PDF解析Phase5（DEV-PLAN:308）。 |
| 056 | 后续适用/停用检索Phase6（DEV-PLAN:309）。 |
| 057 | 后续失败/发布Phase6（DEV-PLAN:309）。 |
| 058 | 规则/说明冻结BT/test_policy.py:85；正式发布检索Phase6（DEV-PLAN:309）。 |
| 059 | 后续撤销Phase6及在途回复Phase7（DEV-PLAN:309/318）。 |
| 060 | 后续完整删除Phase12（DEV-PLAN:315）。 |
| 061 | 后续向量输入复用Phase6（DEV-PLAN:309）。 |
| 062 | 后续向量空间切换Phase6（DEV-PLAN:309）。 |
| 063 | 后续PDF结构/单位/图步骤Phase5（DEV-PLAN:308）。 |
| 064 | 后续完整知识维护Phase6（DEV-PLAN:309）。 |
| 065 | 精确查询前置BT/test_business_api.py:111；实际图片提取Phase8（DEV-PLAN:311）。 |
| 066 | 查号不猜/多目标前置BT/test_business.py:97；图片冲突Phase8（DEV-PLAN:311）。 |
| 067 | 后续实际观察Phase8（DEV-PLAN:311）。 |
| 068 | 图片未证明缺件规则BT/test_policy.py:73；图文处理Phase8（DEV-PLAN:311）。 |
| 069 | v1/v2来源kind BT/test_policy.py:73；图片及申请Phase8/9（DEV-PLAN:311/318）。 |
| 070 | 安全件规则BT/test_policy_fulfillment.py:60；危险直接HITL Phase8（DEV-PLAN:311）。 |
| 071 | 视觉不能当账本BT/test_policy.py:61；实际材料/写入Phase8/9（DEV-PLAN:311/318）。 |
| 072 | 后续逐图失败类别Phase8（DEV-PLAN:311）。 |
| 073 | 后续接收/CID/远程拒取Phase8（DEV-PLAN:311）。 |
| 074 | 历史范围前置BT/test_business.py:108/118/regressions:57；图片Phase8（DEV-PLAN:311）。 |
| 075 | 后续图片注入Phase8（DEV-PLAN:311）。 |
| 076 | 后续视觉预算/usage Phase8（DEV-PLAN:311）。 |
| 077 | 旧任务栅栏BT/test_protocol.py:158；在途视觉Phase8（DEV-PLAN:311）。 |
| 078 | 后续图片完整删除Phase12（DEV-PLAN:315）。 |
| 079 | 后续多图覆盖Phase8（DEV-PLAN:311）。 |
| 080 | 后续人工视觉修订Phase8（DEV-PLAN:311）。 |
| 081 | 本期Art业务组件代码F/components/mail-agent/BusinessDetails.vue:1；图片交互Phase8（DEV-PLAN:311）。 |
| 082 | 后续冻结图集正式验收Phase13（DEV-PLAN:316/318）；Phase1旧FAIL保留。 |

## 独立测试、编译与原始输出

后端命令：从忽略配置赋值测试URL，绝对PYTHONPATH为backend/src，然后运行 `backend/.venv/Scripts/python.exe -X utf8 -m unittest discover -s backend/tests -v`。全部真实PG启用，无skip。以下是原始输出节录，省略其它ok行：

```text
D:\Work_Project\globalmail-agent\globalmail-agent\backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_historical_parent_does_not_authorize_synthetic_child_line (test_business_regressions.BusinessRegressionTests.test_historical_parent_does_not_authorize_synthetic_child_line) ... ok
test_inspected_share_survives_database_projection_and_service (test_business_regressions.BusinessRegressionTests.test_inspected_share_survives_database_projection_and_service) ... ok
test_multi_line_choice_remains_unbound_without_explicit_target (test_business_regressions.BusinessRegressionTests.test_multi_line_choice_remains_unbound_without_explicit_target) ... ok
test_public_choices_exclude_future_messages_and_private_address_tokens (test_business_regressions.BusinessRegressionTests.test_public_choices_exclude_future_messages_and_private_address_tokens) ... ok
test_newest_visible_choice_must_accept_exact_amount_currency_and_action (test_policy.PublicCommandTests.test_newest_visible_choice_must_accept_exact_amount_currency_and_action) ... ok
test_database_failure_and_missing_table_are_degraded (test_postgres.PostgresTests.test_database_failure_and_missing_table_are_degraded) ... protocol_worker_dependency_unavailable
ok
----------------------------------------------------------------------
Ran 83 tests in 98.716s

OK
```

83通过不能关闭P4-F1：BT/test_policy.py:47原测试按正确顺序append新选择，只证明数组尾新拒绝；BT/test_business_regressions.py:70只覆盖不可见选择过滤，没有真实seq乱序新拒绝。独立反例是本轮额外证据，未改测试刷绿。

前端在frontend执行 `pnpm exec tsx --test scripts/*.test.ts`；`pnpm build`独立退出0。原始输出节录（只省略资源大小表）：

```text
✔ 同订单同SKU的两行物流严格分开，无关联记录不凭型号猜归属 (1.4197ms)
✔ 已取得的客户选择保留明确拒绝、零金额与未绑定商品，不用候选表单补齐 (1.4868ms)
ℹ tests 28
ℹ suites 0
ℹ pass 28
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 694.6572
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3277 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 33.13s
```

`python -X utf8 data/knowledge/v2/build_policy.py --check`独立原始输出：

```json
{"status": "verified", "publication_status": "unpublished", "artifacts": {"policies/policy-profile.json": "cf355a4031415ccccc6be439a24703b80aa7d6de9270591cc3dca34fe86bac19", "policies/policy-profile.md": "05d051061c181a5809e73f2068b65dfbbce75b491b34c0c110f265317fc45b34", "policy-bundle.json": "21440f5c07181c85430f86e548aff0b41d5566a74934789194de5c03075ed2f5"}}
```

```text
compileall -q globalmail-agent/backend/src globalmail-agent/backend/migrations data/knowledge/v2: exit=0, no output
Using Python 3.12.10 environment at: globalmail-agent\backend\.venv
Checked 24 packages in 1ms
All installed packages are compatible
git diff --name-only -- data/knowledge/v1: exit=0, no output
```

## Stage 2 与交回

**Stage 2未执行：没有签署完整代码质量、安全扫描或最终明暗/窄屏/邻居页面视觉比较通过。** 已完成的测试与编译只是Stage1证据。UI原P4-R2/R4有明确实现及行为测试，但最终实际视觉仍要下一轮打开页面/截图验证；不能用本轮因HIGH停止的审查宣布完成。

P4-F1交回主Agent按Stage1失败补实现、补正式可达路径回归，再派fresh code-reviewer从Stage1重审。本报告保留FAIL，不改成补修后的PASS，不替产品AC签署验收，不改变Phase1未通过及Phase5–13边界。
