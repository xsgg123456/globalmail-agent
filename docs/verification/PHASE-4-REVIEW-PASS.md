# Phase 4 第三轮独立审查：FAIL

日期：2026-10-08。本报告文件名按派发要求保留 `PASS`，实际结论为 **Stage 1 FAIL；Stage 2 未执行**。审查的是本轮发现库存时间缺口前的工作区实现；主 Agent 在收到本轮问题后进行的修复不折算为本轮通过，须另派 fresh reviewer 重新开始。

## 范围、步骤和输入

按 `.agents/skills/code-review/SKILL.md:23`、`.codex/agents/code-reviewer.toml:20` 先审需求，有 HIGH 即停止第二阶段。步骤：读取原文及盘点变更 → 核对 Phase 4 每项交付 → 独立 PostgreSQL/正式 HTTP 复现旧缺陷和相邻边界 → 核验实际界面及记录测试/编译输出 → 给主 Agent 返回失败项。没有修实现、提交或派其他 Agent。

已读取 AGENTS、Product-Spec v1.13 的 REQ-002/004/005/011/014、5.10–5.12、主架构第2/4.4/5/6/7/8节、DEV-PLAN Phase4及AC归属、PHASE-4-IMPLEMENTATION、v1 DATA-CONTRACT、文档索引和 SESSION-HANDOFF。阶段边界见 `DEV-PLAN.md:103`、`docs/planning/PHASE-4-IMPLEMENTATION.md:15`；完整需求与本期前置子能力分别判断。无 Design-Brief，UI 继承既有 Art Design Pro 页面。

下文路径简写：`B`=`globalmail-agent/backend/src/globalmail_agent`；`BT`=`globalmail-agent/backend/tests`；`F`=`globalmail-agent/frontend/src`；`FT`=`globalmail-agent/frontend/scripts`。行号取发现问题时读取的实现；主 Agent 后续修改可能移动行号。

## 阻塞问题

### P4-R6 — HIGH：资格服务把没有时间依据的库存判为可用

要求：`Product-Spec.md:308` 要求返回快照时间并保持未知字段；`Product-Spec.md:452` 要求换货/补件核对可用库存；`AGENT-ARCHITECTURE.md:81` 规定时间来自可信服务端上下文；`DEV-PLAN.md:107` 要求身份、模式、截点限定的可用库存查询；`docs/planning/PHASE-4-IMPLEMENTATION.md:33` 定义库存快照及缺口。

实际：审查时 `B/domain/policy_fulfillment.py:109` 至 `:124` 仅检查库存数量、地区、硬件和来源，未检查 `snapshot_at`。`B/application/business_read_model.py:137` 允许未知时间的库存进入只读事实；这是展示未知资料所需的行为，但资格层随后将其判为 fulfilled。`B/application/business_queries.py:126` 能识别 `inventory.snapshot_at` 缺失，两个入口因此得出相反结论。

独立反例从 `BASE-OUTON-04` 深拷贝开始，使用测试器随机 schema 和真正迁移，将换货其他条件补成明确、合法的同商品/同地区/同硬件、已同意、当前地址版本及已收件质检；**保留原库存没有 snapshot_at**。仅改内存 fixture 副本及测试 schema，不改 v1。通过真实 `FixtureConversations` 入库、`BusinessQueries` 读取，再通过应用正式 `/api/v1/conversations/{id}/eligibility` 路由测试，HTTP=200。不是只调用领域函数，不是修改资格结果伪造通过。

本实例的原始输出（只显示本次打印的安全业务字段）：

```text
INVENTORY_SNAPSHOT {'query_status': 'unknown', 'snapshot': None, 'query_missing': ['inventory.snapshot_at'], 'eligibility': 'eligible', 'authorized': False, 'conditions': [{'code': 'policy_scope', 'label': '政策适用范围已核对', 'status': 'fulfilled', 'fulfilled_by': ['branch:e83f91a5-643e-456e-be2a-027262c25b15:order']}, {'code': 'order_identity', 'label': '当前客户准确订单商品已核验', 'status': 'fulfilled', 'fulfilled_by': ['branch:e83f91a5-643e-456e-be2a-027262c25b15:order', 'line:8333fc62-1c49-499c-9f1d-55b41f47e251']}, {'code': 'paid_amount', 'label': '订单行实付金额已核验', 'status': 'fulfilled', 'fulfilled_by': ['line:8333fc62-1c49-499c-9f1d-55b41f47e251']}, {'code': 'customer_choice', 'label': '客户明确接受此次方案', 'status': 'fulfilled', 'fulfilled_by': ['message:SIM-M-BASE-OUTON-04-1']}, {'code': 'quantity', 'label': '此次涉及整行商品数量', 'status': 'fulfilled', 'fulfilled_by': ['line:8333fc62-1c49-499c-9f1d-55b41f47e251']}, {'code': 'compensation_ledger', 'label': '已跨事项核对同订单行补偿', 'status': 'fulfilled', 'fulfilled_by': ['line:8333fc62-1c49-499c-9f1d-55b41f47e251']}, {'code': 'delivery_date', 'label': '在签收后365天窗口内', 'status': 'fulfilled', 'fulfilled_by': ['branch:e83f91a5-643e-456e-be2a-027262c25b15:order']}, {'code': 'reported_problem', 'label': '当前商品问题依据已具备', 'status': 'fulfilled', 'fulfilled_by': ['branch:e83f91a5-643e-456e-be2a-027262c25b15:defect']}, {'code': 'compatibility', 'label': '准确SKU、地区和硬件版本适配', 'status': 'fulfilled', 'fulfilled_by': ['branch:e83f91a5-643e-456e-be2a-027262c25b15:product']}, {'code': 'inventory', 'label': '当前库存可用', 'status': 'fulfilled', 'fulfilled_by': ['branch:e83f91a5-643e-456e-be2a-027262c25b15:inventory:0']}, {'code': 'address', 'label': '客户当前选择与已确认地址版本一致', 'status': 'fulfilled', 'fulfilled_by': ['branch:e83f91a5-643e-456e-be2a-027262c25b15:address:1']}, {'code': 'warehouse_receipt', 'label': '仓库已收到此次受影响份额', 'status': 'fulfilled', 'fulfilled_by': ['branch:e83f91a5-643e-456e-be2a-027262c25b15:returns:0']}, {'code': 'warehouse_inspection', 'label': '仓库质检已覆盖此次受影响份额', 'status': 'fulfilled', 'fulfilled_by': ['branch:e83f91a5-643e-456e-be2a-027262c25b15:returns:0']}]}
```

`authorized:false` 正确拦住未发布执行，但不使错误的 `eligible` 资格结论正确。需要在资格层校验有效、带时区且不晚于 as_of 的库存时间，未知/坏时间保持缺口，未来库存拒用；库存查询也不能为缺时间返回确定的可用数量。修复应有数据库→统一查询→正式 HTTP 的正反例，纯函数 fixture 必须包含与生产契约一致的时间前提。

主 Agent 已在本轮结束前告知完成该项补丁及新增回归。**本报告保留发现时的 FAIL，不审签该补丁，不覆盖前两轮 FAIL；修复后重新审查。**

## 旧缺陷独立复现

未以“84个测试绿了”替代验证。测试器 `BT/test_protocol.py:30` 建随机 schema、跑 Alembic、使用真实 PG，并在 `:60` 注册清理；本轮额外通过已有回归 fixture 的 setUp/create/preview 驱动自己的深拷贝反例，退出时执行 cleanup。

| 原问题/边界 | 本轮实际结果 | 对应实现证据 |
|---|---|---|
| 首轮 HIGH：收件2件仅质检1件 | 无单位标识 needs_input；仅 `['0']` wait；2件 `['0','1']` eligible。正例 authorized=false。关闭旧缺陷。 | `B/application/business_projection.py:10` 保留字段；`B/application/business_read_model.py:98` 投影；`B/domain/policy_fulfillment.py:46` 按实际质检份额；`BT/test_business_regressions.py:42`。 |
| 第二轮 HIGH：choices反序导致旧同意覆盖最新拒绝 | 两条选择数组 `[新,旧]`，持久消息seq分别2/1；公开结果seq为 `[1,2]`。最新拒绝、改为退货、显式null目标都 needs_input；最新明确接受正例 eligible。关闭旧缺陷。 | `B/application/business_read_model.py:24`、`:144`；`B/domain/policy_conditions.py:55` 独立maxseq；`BT/test_business_regressions.py:117`。 |
| 相邻边界：同一封有两条无法区分的选择 | needs_input，不选最后一条。 | `B/domain/policy_conditions.py:68`。 |
| 相邻边界：多条选择缺seq | needs_input，不使用数组先后。额外领域级检查；正式读模型实际会填持久seq。 | `B/domain/policy_conditions.py:63`。 |
| 首轮 MEDIUM：合法历史父订单混入Mock子商品 | 父订单可见，但0个商品行；结果不含 `H-CTD16-US-BK`。关闭。 | `B/application/business_read_model.py:56`、`:71`、`:92`；`BT/test_business_regressions.py:70`。 |
| 首轮 MEDIUM：同SKU不同订单行与包裹难辨 | 实际截图显示第2项及专属 `SIM-PKG-SCN-008-SECOND`；严格order+line匹配。关闭。 | `F/components/mail-agent/BusinessOrderCard.vue:37`、`:47`；`business-records.ts:157`；`FT/business-format.test.ts:20`。 |
| 首轮 MEDIUM：实际客户选择未展示 | 实际截图显示退款已同意、第1封来信、第1项、数量1、US$54.99；原客户ID和地址token未公开。关闭。 | `B/application/business_customer_view.py:4`；`F/components/mail-agent/BusinessCustomerChoices.vue:12`；`business-choices.ts:17`；`BT/test_business_regressions.py:83`。 |
| 多商品未绑定选择不能补猜 | 公开结果没有order_line_id/quantity；仅单行且数量1才补关联。 | `B/application/business_customer_view.py:14`；`B/application/business_queries.py:185`；`BT/test_business_regressions.py:105`。 |

本实例额外复现的原始输出：

```text
INSPECTION 1 None needs_input [('warehouse_inspection', 'needs_input'), ('warehouse_inspection', 'wait')]
INSPECTION 1 ['0'] wait [('warehouse_inspection', 'wait')]
INSPECTION 2 ['0', '1'] eligible [('warehouse_inspection', 'fulfilled')]
LATEST latest_refusal [1, 2] needs_input
LATEST latest_action_change [1, 2] needs_input
LATEST latest_unbound [1, 2] needs_input
LATEST latest_accept [1, 2] eligible
SAME_MESSAGE_AMBIGUOUS needs_input
HISTORICAL_MIXED needs_input 0 False
MISSING_SEQ needs_input
```

## Stage 1 逐项交付核对

| 条目 | 结论与证据 |
|---|---|
| REQ-002：可见消息、游标、未来快照、历史事实重建 | 本期读取子能力匹配；`B/application/business_read_model.py:24`、`:30`、`:46` 按持久可见seq与as_of过滤；`:124` 禁Mock政策/库存。SCN029取真实可见来信时间，不修源clock；`fixture_conversations.py:43`、`BT/test_business.py:108`/`:118`。完整模型请求归Phase7。 |
| REQ-004：范围内精确订单/商品、多商品澄清 | 匹配；`B/application/business_queries.py:42`/`:83`/`:90` 不选多行首项、不猜相似编号；无真实授权快照时手动会话返回空，历史返回不可用；`BT/test_business_api.py:111`。不从listing/案例摘要拼造客户订单。模型主动复用与图片候选归Phase7/8。 |
| REQ-004：来源/快照/实时性/缺失和失败区分 | 订单/账本匹配；`B/application/business_read_model.py:64`、`:76`、`:110`；`business_queries.py:51`/`:65`/`:71`；`BT/test_business.py:69`。库存资格时间不匹配，见HIGH P4-R6。 |
| REQ-005：白名单、用途、Mock及未来故事隔离 | 本期匹配；`B/adapters/fixture_loader.py:29`/`:45`/`:47`/`:50` 只消费10个允许路径及dev初始场景；`:148`目录不返回答案；`BT/test_business.py:29`实际拦截文件读取、`:85`逐72场景入库。RAG/知识维护为后续。 |
| REQ-005：政策规则/说明同版本、v1不变 | 本期未发布生成包匹配；`data/knowledge/v2/build_policy.py:26` 校验已批准全部规则与范围，`:77`同源生成中文说明，`:123`绑定摘要/schema/生成器/解释器/v1引用；独立 `--check`成功，git v1无差异。正式发布与检索仍Phase6。 |
| REQ-011：五类只读资格条件 | 金额整数、单位份额、余额/占用/冲突、退款收件/质检、窗口、选择、地址、兼容均有实现；`B/domain/policy.py:61`/`:91`、`policy_conditions.py:55`/`:96`、`policy_ledger.py:30`、`policy_fulfillment.py:20`/`:63`。库存时间不匹配，故不能签署整个资格服务通过。 |
| REQ-011：申请/执行/包裹/退件分别关联 | 匹配本期查询；`B/adapters/business_schema.py:91`/`:109`/`:120`复合FK；`fixture_ledger.py:37`/`:47`/`:55`分别装载；`business_read_model.py:94`/`:104`/`:119`重建关系。未创建售后申请、扣库或未来执行。 |
| REQ-014：图片不授权、不同来源kind、候选不能伪装事实 | 本期资格前置匹配；`B/domain/policy_conditions.py:36`限定kind，`:149`局部图不证明缺件；`data/knowledge/v2/build_policy.py:50`排除视觉履约凭据；`BT/test_policy.py:61`/`:73`。实际图片接收/理解/危险HITL/更正/清理仍Phase8/12，不能称完成。 |
| 主架构2：可信scope/分支/时间 | 匹配本期范围；`B/application/business_read_model.py:17`/`:21`、`fixture_conversations.py:29`创建独立dataset；`BT/test_business.py:47`检验四个独立身份字段；API不接受scope/time。库存资格仍有时间HIGH。 |
| 主架构5/6：严格schema、金额整数、只读无执行 | 匹配；`B/domain/policy.py:15` extra forbid/strict，`:147` authorized=false；`B/api/business.py:24`拒额外query，`:63`只读服务；`BT/test_business_api.py:95`实际比较messages/jobs/events/operations/executions/inventory数量不变，`:130`伪造字段422。 |
| 主架构7：政策未发布不授权、decision非通行证 | 匹配当前门禁；`B/domain/policy.py:147`/`:151`、`B/application/eligibility.py:10`只读调用，无创建执行接口；`data/knowledge/v2/README.md:14`标明Phase6发布。该门禁不消除计算结论的P4-R6。 |
| 主架构8：数据库范围约束与不可变来源 | 匹配本期结构；12表由 `B/adapters/business_schema.py:24` 至 `:138`定义；冻结迁移 `backend/migrations/versions/0003_business_catalog.py:7`/`:112`/`:124`/`:135`持有独立schema，`:167`触发器保护source与政策版本；`BT/test_business.py:142`实际FK及不可变反例通过。 |
| 单次一致读取 | 匹配；`B/application/business_queries.py:18`在begin前REPEATABLE READ，回调全部使用同conn；`BT/test_business.py:174`实际两连接插入和快照测试通过。 |
| 5.10 SCREEN001/CMP008/CMP009本期查询 | 匹配查询部分；`F/components/mail-agent/AgentProcessPanel.vue:83`嵌入详情，`BusinessDetails.vue:67`逐行/选择/政策/预览，`BusinessScenarioLauncher.vue:12`真实初始基线入口。执行和事件控制尚未实现，无假成功引导。 |
| 5.11 默认、加载、空、错误、成功、受限 | 本期实现匹配；`BusinessDetails.vue:19`/`:20`/`:44`、`BusinessAvailabilityForm.vue:51`/`:66`、`BusinessEligibilityForm.vue:5`/`:140`；`useBusinessDetails.ts:37`失败保输入，`:59`切上下文清空旧结果；`FT/business-workbench.test.ts:43`/`:80`/`:148`晚到和同key重试。实际浏览记录如下。完整模型及知识状态归后续。 |
| 5.12 输入限制 | 本期匹配；`B/api/business.py:47`长度、`:24`额外字段；`B/domain/policy.py:15`严格int；`F/components/mail-agent/business-eligibility-input.ts:14`输入不接受指数/小数数量/超精确范围，金额按币种精度；`BT/test_business_api.py:130`、`FT/business-format.test.ts:35`。 |
| runtime能力与范围漂移 | 匹配；`B/api/system.py:27`只开启conversations/business_queries，agent/knowledge=false；`F/api/runtime-contract.ts:40`和 `components/business/runtime-status.vue:48`同步Phase4。新增场景基线为实施计划允许入口，无模型、邮件、知识发布、交易执行、扣库或未来事件功能。 |
| 测试服务隔离 | 匹配；`globalmail-agent/scripts/phase3-test-server.py:35`/`:50`随机schema，`:73`服务端私有环境，`:83`清除前端GLOBALMAIL/LLM，`:125`清理。此次未停主 Agent 服务，只关闭自己的浏览器session。 |

## 82 AC逐项归属

不勾选任何产品AC。归属来自 `DEV-PLAN.md:306` 至 `:318`；后续项目均以 `B/api/system.py:27` 的agent/knowledge=false及开发阶段为范围证据。部分表示已验证前置，未满足完整 Given/When/Then。Phase1原业务失败及人工pending保持 `DEV-PLAN.md:5` 的历史结论。

| AC | 本轮结论/证据 |
|---|---|
| 001 | 既有身份归组回归；BT/test_conversations.py:77；主归属Phase3。 |
| 002 | 既有group_id不并身份回归；BT/test_conversations.py:150；Phase3。 |
| 003 | 既有去重回归；BT/test_conversations.py:85；Phase3。 |
| 004 | 部分：持久前缀隔离；B/application/business_read_model.py:24；真实模型Phase7。 |
| 005 | 部分：既有历史/对照隔离；BT/test_conversations.py:150；真实模型Phase7。 |
| 006 | 部分：未来订单拒读；BT/test_business.py:118；真实模型Phase7。 |
| 007 | 未实现正式Agent出站；DEV-PLAN.md:310，Phase7。 |
| 008 | 部分：既有命令去重；BT/test_conversations.py:85；出站Phase7。 |
| 009 | 未实现正式多轮Agent；DEV-PLAN.md:310，Phase7。 |
| 010 | 部分：范围内已知订单读取；B/application/business_queries.py:71；主动复用Phase7。 |
| 011 | 部分：多商品needs_input；B/application/business_queries.py:90；回复澄清Phase7。 |
| 012 | 本期查询子能力匹配；BT/test_business_api.py:111；主归属Phase4。 |
| 013 | 部分：精确业务适配；B/domain/inventory.py:4；RAG Phase6。 |
| 014 | 未实现正式跨语言RAG；DEV-PLAN.md:309，Phase6。 |
| 015 | 未实现正式未读内容声明；DEV-PLAN.md:310，Phase7/8。 |
| 016 | 部分：dev白名单与历史Mock隔离；B/adapters/fixture_loader.py:47；RAG Phase6。 |
| 017 | 未实现Agent索取订单；DEV-PLAN.md:310，Phase7。 |
| 018 | 部分：可见尝试过滤；B/application/business_read_model.py:147；Agent Phase7。 |
| 019 | 部分：跨身份查询拒绝；BT/test_business_api.py:111；模型注入Phase7。 |
| 020 | 未实现Agent主动HITL；DEV-PLAN.md:310，Phase7。 |
| 021 | 既有人审收信屏障回归；BT/test_conversations.py:104；Phase3。 |
| 022 | 部分：既有人工回复后新信恢复协议；BT/test_conversations.py:123；Agent Phase7。 |
| 023 | 既有人工结案回归；BT/test_conversations.py:140；Agent行为Phase7。 |
| 024 | 部分：持久任务旧结果栅栏；BT/test_protocol.py:190；真实模型Phase7。 |
| 025 | 部分：停止/中断协议；BT/test_protocol.py:135；模型故障Phase7。 |
| 026 | 部分：重启恢复及查询无写；BT/test_protocol.py:205、test_business_api.py:95；Agent Phase7。 |
| 027 | 既有可见历史前缀回归；BT/test_conversations.py:150；Phase3。 |
| 028 | 部分：初始人审无job；BT/test_business.py:131；正式HITL Phase7。 |
| 029 | 未实现完整运行清理；DEV-PLAN.md:315，Phase12。 |
| 030 | 未实现知识下架；DEV-PLAN.md:309，Phase6。 |
| 031 | 未执行整体模型评测；DEV-PLAN.md:316，Phase13。 |
| 032 | 部分：实际Art查询与抽屉；F/components/mail-agent/BusinessDetails.vue:1；Agent Phase7。 |
| 033 | 部分：关联包裹查询；BT/test_business_api.py:63；跟进Phase10。 |
| 034 | 部分：金额/占用/质检计算；B/domain/policy.py:61；执行Phase9。 |
| 035 | 部分：独立退件/质检查询；B/domain/policy_fulfillment.py:20；执行Phase9。 |
| 036 | 部分且有HIGH：库存时间缺口P4-R6；B/domain/policy_fulfillment.py:109；执行Phase9。 |
| 037 | 部分且有HIGH：库存时间缺口P4-R6；B/domain/policy_fulfillment.py:109；执行Phase9。 |
| 038 | 部分：独立Mock分支；BT/test_business.py:47；完整闭环Phase9。 |
| 039 | 部分：份额/跨事项冲突；B/domain/policy_ledger.py:85；申请时重验Phase9。 |
| 040 | 部分：未知结果占用；B/domain/policy_ledger.py:52；写恢复Phase9。 |
| 041 | 部分：多订单行保留；B/application/business_read_model.py:119；变更/取消Phase10。 |
| 042 | 未实现业务事件跟进；DEV-PLAN.md:313，Phase10。 |
| 043 | 部分：既有人工事件屏障；BT/test_human_events.py:58；完整事件Phase10。 |
| 044 | 部分：历史Mock订单/子行/政策拒读；B/application/business_read_model.py:71、:124；Agent Phase7。 |
| 045 | 未实现多诉求理解；DEV-PLAN.md:310，Phase7。 |
| 046 | 未实现条件意图理解；DEV-PLAN.md:310，Phase7。 |
| 047 | 未实现意图动态修正；DEV-PLAN.md:310，Phase7。 |
| 048 | 未实现模型schema修复预算；DEV-PLAN.md:310，Phase7。 |
| 049 | 未接真实trace/usage；DEV-PLAN.md:314，Phase11。 |
| 050 | 未接实际Langfuse导出；DEV-PLAN.md:314，Phase11。 |
| 051 | 未执行Langfuse故障降级；DEV-PLAN.md:314，Phase11。 |
| 052 | 部分：既有新run协议；BT/test_protocol.py:190；正式Agent Phase7。 |
| 053 | 未实现业务wait/wake跟进；DEV-PLAN.md:313，Phase10。 |
| 054 | 部分：申请/执行/物流独立；B/adapters/fixture_ledger.py:37；正式结果声明Phase9。 |
| 055 | 未实现正式PDF图文解析；DEV-PLAN.md:308，Phase5。 |
| 056 | 未实现章节RAG及停用检索；DEV-PLAN.md:309，Phase6。 |
| 057 | 未实现知识入库发布；DEV-PLAN.md:309，Phase6。 |
| 058 | 部分：同版规则/说明摘要；data/knowledge/v2/build_policy.py:123；正式发布Phase6。 |
| 059 | 未实现知识撤销/迟到回复；DEV-PLAN.md:309、:318，Phase6/7。 |
| 060 | 未实现完整正文删除；DEV-PLAN.md:315，Phase12。 |
| 061 | 未实现向量输入复用；DEV-PLAN.md:309，Phase6。 |
| 062 | 未实现向量空间切换/回退；DEV-PLAN.md:309，Phase6。 |
| 063 | 未实现正式PDF结构切分；DEV-PLAN.md:308，Phase5。 |
| 064 | 未实现完整知识管理页面；DEV-PLAN.md:309，Phase6。 |
| 065 | 部分：精确客户订单接口；BT/test_business_api.py:111；图片Phase8。 |
| 066 | 部分：精确匹配、多行不猜；B/application/business_queries.py:42；图文冲突Phase8。 |
| 067 | 未实现正式视觉观察；DEV-PLAN.md:311，Phase8。 |
| 068 | 部分：局部图不证明缺件；B/domain/policy_conditions.py:149；图文Phase8。 |
| 069 | 部分：证据kind资格前置；B/domain/policy_conditions.py:36；图像/申请Phase8/9。 |
| 070 | 部分：安全件规则转review；B/domain/policy_fulfillment.py:87；实际危险HITL Phase8。 |
| 071 | 部分：视觉不作履约账本；BT/test_policy.py:61；正式截图/动作Phase8/9。 |
| 072 | 未实现逐图状态和故障分类；DEV-PLAN.md:311，Phase8。 |
| 073 | 未实现正式图片接收/CID；DEV-PLAN.md:311，Phase8。 |
| 074 | 部分：业务/历史隔离；B/application/business_read_model.py:21、:71；图片Phase8。 |
| 075 | 未实现正式图片注入防护验证；DEV-PLAN.md:311，Phase8。 |
| 076 | 未实现正式视觉预算；DEV-PLAN.md:311，Phase8。 |
| 077 | 部分：既有任务栅栏；BT/test_protocol.py:158；在途视觉Phase8。 |
| 078 | 未实现图片派生清理；DEV-PLAN.md:315，Phase12。 |
| 079 | 未实现多图覆盖/关联；DEV-PLAN.md:311，Phase8。 |
| 080 | 未实现人工视觉更正；DEV-PLAN.md:311，Phase8。 |
| 081 | 部分：Art业务组件；F/components/mail-agent/BusinessDetails.vue:1；正式图片UI Phase8。 |
| 082 | 未执行最终图片业务验收；DEV-PLAN.md:316；Phase1原失败/人工pending保留。 |

## 实际 UI 验证及限制

本实例通过独立 Playwright CLI session `phase4_review_pass` 打开 `http://127.0.0.1:15174/#/workbench`，选择SCN025，再打开“处理详情与人审”抽屉。实际显示Phase4、模型未配置/Phase7接入、当前第1项、精确SKU、订单US$35.99、已退款/处理中均US$0.00、来源模拟设定/快照资料、未发布政策及独立只读核对入口。人审接管和人工结案按钮仍存在。证据：`.playwright-cli/page-2026-10-08T03-06-24-061Z.yml`；实现 `F/components/mail-agent/BusinessDetails.vue:29`/`:67`/`:87`、`AgentProcessPanel.vue:83`。

另逐张实际打开 `output/playwright/phase4-multiline.png`、`phase4-choices.png` 与基线 `phase3-light-wide.png`。同SKU第2项有独立包裹，选择显示准确商品/金额/来信；蓝色按钮、边框、卡片、折叠、字体和三栏外壳延续Phase3。该证据只覆盖Stage1的已查看状态，不冒充完整暗色/窄屏/邻居页面的Stage2视觉通过。发现HIGH后停止第二阶段；没有宣称无any、≤300行、完整安全扫描或完整主题比较通过。自有浏览器已关闭，主 Agent 服务未停止。

## 独立测试与编译原始输出

私有连接串只赋给 `GLOBALMAIL_TEST_DATABASE_URL`，从未打印。`PYTHONPATH`用绝对backend/src。后端完整执行：

```powershell
$env:GLOBALMAIL_TEST_DATABASE_URL=(Get-Content -Raw .local-data/runtime/settings.json | ConvertFrom-Json).database_url
$env:PYTHONPATH=(Resolve-Path globalmail-agent/backend/src).Path
& globalmail-agent/backend/.venv/Scripts/python.exe -X utf8 -m unittest discover -s globalmail-agent/backend/tests -v
```

```text
D:\Work_Project\globalmail-agent\globalmail-agent\backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_inspected_share_survives_database_projection_and_service (test_business_regressions.BusinessRegressionTests.test_inspected_share_survives_database_projection_and_service) ... ok
test_latest_choice_uses_message_sequence_not_fixture_array_order (test_business_regressions.BusinessRegressionTests.test_latest_choice_uses_message_sequence_not_fixture_array_order) ... ok
test_database_failure_and_missing_table_are_degraded (test_postgres.PostgresTests.test_database_failure_and_missing_table_are_degraded) ... protocol_worker_dependency_unavailable
ok
----------------------------------------------------------------------
Ran 84 tests in 92.128s

OK
```

原始输出仅省略其他成功用例行。全部真实PG启用，无skip；本轮测试完成后主 Agent 新增的86项不是这里的结果。84项通过仍有P4-R6，证明库存资格时间原先存在测试盲区。`BT/policy_helpers.py:30` 原纯函数库存前提没有snapshot_at，不能拿这种样本证明截点正确。

前端在 `globalmail-agent/frontend` 执行 `pnpm exec tsx --test scripts/*.test.ts`：

```text
ℹ tests 28
ℹ suites 0
ℹ pass 28
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 578.9795
```

Python `compileall -q globalmail-agent/backend/src globalmail-agent/backend/migrations data/knowledge/v2` 无输出。`python -m pip check` 首次输出 `No module named pip`，未当作通过；用现有 uv 对同一解释器检查：

```text
Using Python 3.12.10 environment at: globalmail-agent\backend\.venv
Checked 24 packages in 1ms
All installed packages are compatible
```

独立 v2 `build_policy.py --check`：

```json
{"status": "verified", "publication_status": "unpublished", "artifacts": {"policies/policy-profile.json": "cf355a4031415ccccc6be439a24703b80aa7d6de9270591cc3dca34fe86bac19", "policies/policy-profile.md": "05d051061c181a5809e73f2068b65dfbbce75b491b34c0c110f265317fc45b34", "policy-bundle.json": "21440f5c07181c85430f86e548aff0b41d5566a74934789194de5c03075ed2f5"}}
```

`git diff --name-only -- data/knowledge/v1` 无输出。前端 `pnpm build` exit=0，原始输出仅省略资源大小表：

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3277 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 27.94s
```

该构建发生在主 Agent 并行修复期间，仅证明构建时前端文件通过类型检查和打包；不签署后端新修复或关闭Stage1 HIGH。

## 变更盘点与 Stage 2 状态

启动时完整执行 `git status --short`、`git diff --stat`、`git diff --name-only`、`git diff`及目录文件盘点，包含未跟踪文件，未只审tracked diff。已跟踪14项变更为 DEV-PLAN、docs/README，B/adapters/database.py、B/api/system.py、B/main.py、BT/test_api.py，FT/runtime-contract.test.ts、F/api/runtime-contract.ts、F/components/business/runtime-status.vue、F/components/mail-agent/AgentProcessPanel.vue/ConversationList.vue、F/hooks/core/useRuntimeStatus.ts、F/views/mail-agent/index.vue、globalmail-agent/scripts/phase3-test-server.py。

新增实现/产物逐文件盘点：B/adapters/business_schema.py、fixture_loader.py、fixture_ledger.py；B/application/fixture_conversations.py、business_read_model.py、business_projection.py、business_customer_view.py、business_queries.py、eligibility.py；B/domain/orders.py、inventory.py、policy.py、policy_conditions.py、policy_ledger.py、policy_fulfillment.py；B/api/business.py；backend/migrations/versions/0003_business_catalog.py；F/api/business-api.ts、business-contract.ts；F/composables/useBusinessDetails.ts、useBusinessPreviews.ts、useBusinessScenarios.ts；F/components/mail-agent/BusinessDetails.vue、BusinessOrderCard.vue、BusinessLedger.vue、BusinessCustomerChoices.vue、BusinessEligibilityForm.vue、BusinessAvailabilityForm.vue、BusinessScenarioLauncher.vue、business-format.ts、business-choices.ts、business-records.ts、business-eligibility-input.ts；data/knowledge/v2 的authoring/policy-profile.json、policies/policy-profile.json、policies/policy-profile.md、build_policy.py、policy-bundle.json、README.md。新增测试盘点为BT/policy_helpers.py、test_business.py、test_business_api.py、test_business_regressions.py、test_policy.py、test_policy_financial.py、test_policy_fulfillment.py、test_policy_service.py，以及FT/business-fixture.ts、business-format.test.ts、business-workbench.test.ts。新增文档PHASE-4-IMPLEMENTATION/两轮旧REVIEW和新增output/playwright图均计入范围，旧报告不改写。

**Stage 2未执行。** 代码质量、无any/文件≤300行、完整密钥/注入/危险函数安全扫描及完整邻居/主题视觉比较不予PASS。上述结构检查和测试属于Stage1交付核验，不代表第二阶段签署。主 Agent 对P4-R6按Stage1失败补实现，再派fresh reviewer从Stage1开始，不能以测试全绿或本报告文件名关闭问题。Phase4尚未完成；Phase1业务失败、人审pending及82项AC未整体完成的状态保持原样。
