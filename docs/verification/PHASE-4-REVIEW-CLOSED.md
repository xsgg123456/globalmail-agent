# Phase 4 第四轮独立审查：PASS

审查日期：2026-10-08。审查角色：fresh `code-reviewer`，会话 `phase4_review_closed`。审查基线：HEAD `cc884fe74d2ced7d08ca6a68abdcf3345ace0e73` 上的全部 tracked diff、untracked 实现、测试、v2资料及本期文档。本报告没有修改实现、提交代码或重写前三轮结论。

**签署结论：Stage 1 PASS；Stage 2 PASS；HIGH 0、MEDIUM 0、LOW 1。** PASS只覆盖DEV-PLAN Phase 4的受控初始资料装载、精确只读查询、未发布政策条件预览与对应界面。本报告不签署全产品82项AC、七类业务端到端、模型、RAG、图片专项或真实生产订单验收。

## 审查规划与证据范围

| 顺序 | 目标及完成标准 | 实际完成 |
|---|---|---|
| 1 | 阅读原文、盘点全部变化，确定本期/后续期边界 | 已读AGENTS、审查skill及角色定义、Spec v1.13、主架构指定章节、DEV-PLAN、实施计划、v1数据契约、文档索引与交接、三份原FAIL报告；盘点全部diff/untracked |
| 2 | Stage 1逐条对照Spec、实体、AC归属与阶段交付；独立复现旧HIGH和新增来源/时间边界 | 独立执行88项后端测试，无skip；另执行4项邻接边界；正式PG装载→查询→服务/HTTP路径证实旧HIGH已修；未发现本期HIGH |
| 3 | 仅Stage 1无HIGH后进入Stage 2，检查类型/大小/安全/测试真实性/实际视觉 | 独立执行前端28项、类型检查/构建、compileall、依赖兼容、v2一致性；实际打开业务和知识邻居页面并查看截图；发现1个LOW |
| 4 | 按证据签署，保留历史失败和未完成项 | 本文签署阶段限定PASS；前三轮FAIL、Phase 1失败、人工pending及后续阶段未实现不变 |

依据：`.agents/skills/code-review/SKILL.md:22`要求逐项有证据，`:28`要求Stage 1无HIGH才进入Stage 2；`.codex/agents/code-reviewer.toml:12`规定两阶段和只审查。无Design Brief/专门设计稿，因此按`Product-Spec.md:550`及`AGENTS.md`继承实际Art Design Pro邻居与Phase 3界面。

路径缩写仅用于下方证据表：`B/`=`globalmail-agent/backend/src/globalmail_agent/`，`BT/`=`globalmail-agent/backend/tests/`，`F/`=`globalmail-agent/frontend/src/`，`FT/`=`globalmail-agent/frontend/scripts/`。所有行号指本次审查的工作区源码。

盘点范围包括：

- 后端新增adapters的business_schema/fixture_loader/fixture_ledger，application的fixture_conversations/business_read_model/business_projection/business_customer_view/business_queries/eligibility，domain的orders/inventory/policy/policy_conditions/policy_ledger/policy_fulfillment，api/business及现有main/system/database；冻结迁移0003；所有新增业务/政策/回归测试。
- 前端business-api/business-contract、三个useBusiness composable、七个Business组件及四个business辅助模块、AgentProcessPanel/ConversationList/工作台、phase4 runtime契约和测试。
- v2 authoring/rules/中文说明/bundle/schema/生成器、phase3-test-server的`--phase4`、根架构/计划/索引/模块说明/验证文档。源代码扫描覆盖57份新增/修改的`.py/.ts/.vue`文件。
- 本期截图及前三轮报告也在untracked清单内。截图不是实现；旧报告不是可覆盖的待修文件。

## Stage 1：Spec Compliance

### Phase 4交付逐项验收

| DEV-PLAN Phase 4交付 | 结论 | 代码及实际证据 |
|---|---|---|
| 允许清单、仅dev初始状态、来源快照不可变 | 完整实现 | `B/adapters/fixture_loader.py:30`固定文件、`:47`过滤dev、`:50`禁止未来控制/故事/答案；`B/adapters/fixture_ledger.py:10`仅装初始账本；`BT/test_business.py:29`检验实际读取名单、`:85`逐个装载72场景。迁移`:167`触发器及`BT/test_business.py:142`验证不可变约束 |
| 每次新场景独立身份/dataset/customer/branch，重试不重建 | 完整实现 | `B/application/fixture_conversations.py:29`建立新scope、`:63`通过既有幂等命令；`BT/test_business.py:47`两次新命令独立；`FT/business-workbench.test.ts`核对未知结果重试沿用命令。主Agent真实丢响应重试证据见验证记录，不能把纯mock测试当此证据 |
| 12表同scope与行/操作/执行复合FK，冻结迁移 | 完整实现 | `B/adapters/business_schema.py:15`scopeFK、`:69`订单行、`:97`账本行、`:110`操作、`:121`执行关联；`backend/migrations/versions/0003_business_catalog.py:7`自含metadata、`:163`升级。`BT/test_business.py:142`真实PG跨scope/跨行失败反例；不是仅查询层过滤 |
| 查订单/行/包裹/操作，精确SKU、适配与库存；多行不默认第一行 | 完整实现 | `B/application/business_queries.py:42`精确号、`:48`仅唯一行可自动选、`:90`多行needs_input；`B/domain/inventory.py:4`精确适配。`BT/test_business.py:97`、`BT/test_business_api.py`实际越界/未知/多行测试；UI多行及SECOND运单实际截图 |
| 统一读时刻、历史排Mock及未来、缺快照保持未知 | 完整实现 | `B/application/business_queries.py:18`在begin前设REPEATABLE READ；`BT/test_business.py:211`另一连接更新后本事务仍读同快照。`B/application/business_read_model.py:30`真实游标、`:71`逐行排Mock、`:92`逐账本排Mock、`:124`历史不取模拟政策/库存；`:137`库存时间过滤。HTTP库存缺/未来时间正反例见`BT/test_business_regressions.py:139` |
| 程序规则/同版中文说明、版本摘要、保留v1原字节 | 完整实现 | `data/knowledge/v2/build_policy.py:26`版本/数值/用途校验、`:77`结构化生成说明、`:123`生成bundle；`--check`实际verified/unpublished。对111个tracked v1文件与HEAD逐字节比较零差异；`B/adapters/fixture_loader.py:174`原场景固定v1 |
| 数量/金额/客户选择/地址/份额/已有补偿/证据kind核验，只读不授权 | 完整实现 | `B/domain/policy.py:15`严格模型、`:61`整数退款、`:121`起逐条件、`:147`始终authorized:false、`:151`预览摘要；`policy_conditions.py:55`最新真实seq选择、`policy_fulfillment.py:20`收件/质检份额、`:63`地址版本、`:109`库存；`policy_ledger.py:30`既有操作与执行去重占用。无提交售后/扣库接口 |
| UI事实/来源/缺口/逐行账本/实际选择与只读试查 | 完整实现 | `F/components/mail-agent/BusinessDetails.vue:29`来源/时刻、`:49`行选择、`:74`真实选择、`:87`预览；`BusinessOrderCard.vue:37`第n项、`:47`严格行账本；`BusinessCustomerChoices.vue:24`真实动作/同意/数量/钱/出处/地址版本；实际页面和截图见视觉节。缺口汇总有1个LOW，不影响具体条件列表或计算 |

### 指定REQ的逐条对照

下表“部分实现/未实现”明确对应产品完整需求；后续阶段内容不以本期PASS关闭。当前阶段边界来自`DEV-PLAN.md:103`、`:262`及`docs/planning/PHASE-4-IMPLEMENTATION.md:19`。

| Spec条目 | 本期结论 | 证据与未完成限制 |
|---|---|---|
| REQ-002.1真实前缀、未来不可入当前响应 | 本期查询完整；模型待Phase 7 | `B/application/business_read_model.py:24`持久消息seq过滤、`:46`订单时间；`BT/test_business_regressions.py:82`数据库确有未来选择但响应不含；未来模型请求未验收 |
| REQ-002.2历史客服/AI对照分开、不继承对照 | Phase 3协议保留；真实模型待7 | `BT/test_protocol.py`既有回放测试在88项中重跑；`B/application/fixture_conversations.py:43`历史源消息路径。Phase 4不创建AI输出，不能据此宣称实际模型继承正确 |
| REQ-002.3真实前缀重建、不继承最终事实 | 本期查询完整；案件理解待7 | `business_read_model.py:24`、`:88`只投影可见账本、`:144`可见选择；loader不读完整故事/最终答案。自动案件记忆未实现 |
| REQ-002.4同一as_of、不得空截点回退 | 本期订单/业务完整；知识待6 | `business_read_model.py:30`/`:42`、`business_queries.py:18`；库存未来/缺时间正式HTTP不eligible。知识available_at检索尚未实现 |
| REQ-002.5回放结束≠解决，显式缺口 | 本期完整，附件理解待8 | 既有Phase 3回放协议测试重跑；`BusinessDetails.vue:37`/`:44`显式历史不可用；SCN029实际页面无订单/Mock补造，不冒充真实历史评测 |
| REQ-004.1先已知订单/候选再针对性补问 | 查询基础部分实现 | 当前scope订单可读`business_queries.py:46`；图片候选和自动回复待7/8，现有元数据不能算读图 |
| REQ-004.2工具返回来源/时刻/实时性/列表/缺字段 | 完整实现 | `business_queries.py:27`标准结果、`business_read_model.py:62`订单安全字段；`BusinessDetails.vue:29`、`BusinessOrderCard.vue:25`展示；独立SCN025实际页面核验 |
| REQ-004.3脱敏/模拟编号，不套真实号正则 | 完整实现 | `B/api/business.py:45`长度约束，`business_queries.py:42`精确字符串，无亚马逊号正则；`BT/test_business_api.py`准备号/不存在号测试 |
| REQ-004.4身份/用途scope、查无记录不串客户 | 完整实现 | scope由`business_read_model.py:21`服务器确定、`business_queries.py:83`拒绝；`BT/test_business_api.py:111`手动会话不因号或同名自动绑定，跨客户测试通过；AC-012本期证据充分 |
| REQ-004.5多商品澄清、不得猜SKU | 查询/UI完整；自动澄清回复待7 | `business_queries.py:90`needs_input、`BusinessDetails.vue:49`显式第n项；多行choice不自动绑定`business_customer_view.py:14`；SCN008实际选择第2项 |
| REQ-004.6不存在/历史不可用/未知/错误分开，Mock标注 | 完整实现 | `business_queries.py:21`/`:78`/`:90`、`F/.../business-format.ts:100`各状态；`BT/test_business_api.py`真实数据库故障/缺表路径；库存无快照available_quantity=null |
| REQ-005.1新白名单/用途、旧卡/答案不自动入索引 | 本期资料白名单完整；索引待6 | `fixture_loader.py:30`/`:47`/`:50`；v1DATA-CONTRACT原文为白名单边界；没有实现索引，不声称RAG完成 |
| REQ-005.2五售后政策、说明+程序规则，不能相似度授权 | 管理预览完整；真实执行待9 | `policy.py:124`五actions、v2生成器；规则有条件结果且始终不可执行。现无获授权正式政策交易入口 |
| REQ-005.3产品知识来源/版本/范围/可用时间、视频不编造 | 已有资料只读，管理待5 | `fixture_loader.py:157`catalog来源；本期不生成产品步骤、不读视频；知识新制作/核对不在本次实现 |
| REQ-005工程默认代表产品族、七类业务覆盖 | 资料基础已装，端到端待13 | 72dev初始场景不等于72个业务闭环；无模型排障/自动指导验收 |
| REQ-005.4语义/跨品牌适配过滤、标识精确 | 精确业务部分完成；RAG未实现 | `inventory.py:4`精确适配、查询精确号；`api/system.py:30`knowledge=false；关键词或目录没有作为RAG证据 |
| REQ-005.5外语检索中文、标注集相关性 | 未实现，Phase 6/13 | `DEV-PLAN.md:135`/`:241`；没有相关性或准确率声明 |
| REQ-005.6引用ID/版本/片段/条件，案例非授权 | 业务evidence/政策部分完成；知识引用待6/7 | `business_queries.py:27`与`policy.py:151`；无知识命中片段或引用浏览器闭环 |
| REQ-005.7Mock/真实分开、历史可用时间 | 本期业务完整；检索待6 | `business_read_model.py:46`/`:71`/`:92`/`:124`、历史混合来源真实PG反例；不能用合法父订单授权Mock子行 |
| REQ-005.8知识管理入口及业务人员操作 | 未实现，Phase 5/6 | `F/views/knowledge/index.vue:1`实际诚实“尚未实现”邻居页；不把v2脚本当管理UI |
| REQ-005.9原件不可变/草稿不可检索/显式发布 | 本期v1与业务快照完整；知识生命周期待5/6 | v1逐字节不变；冻结迁移immutable触发器；v2unpublished，无发布接口 |
| REQ-005.10原子发布/回滚/并发与晚到 | 未实现，Phase 6 | `DEV-PLAN.md:135`；本期没有releases/head或发布成功声明 |
| REQ-005.11下架/彻底删除及衍生清理 | 未实现，Phase 6/12 | `DEV-PLAN.md:226`；本期不删除知识/媒体，不改旧清理结论 |
| REQ-005.12操作者审计、保存不等于发布 | 政策预览有未发布门禁；管理审计待5/6 | `policy.py:147`、v2bundle；没有把客服回复升格全局知识 |
| REQ-005.13规则/说明同版发布、模拟标签不得普通解除 | 同版预览完整；正式发布待6 | `build_policy.py:26`/`:77`/`:123`，说明/规则摘要一致；`fixture_loader.py:183`验证，不把v2自动替换v1 |
| REQ-005.14解析/切分/Embedding配置与独立索引 | 未实现，Phase 5/6 | `DEV-PLAN.md:119`/`:135`；政策生成器不是Embedding构建器 |
| REQ-005.15PDF页码图文解析，不用编辑源替代 | 未实现，Phase 5 | `DEV-PLAN.md:119`；本期没有PDF解析验收声明 |
| REQ-005.16独立知识章节适用关系 | 业务商品适配完成；知识章节待5/6 | `business_schema.py:76`及`inventory.py:4`；不能把此表当文档章节Applicability |
| REQ-005.17模拟说明结构化生成、模拟件SIM前缀 | 本期完整 | `build_policy.py:77`；`fixture_loader.py:30`装已有受控配件目录、无新增真实工厂编号；不修改v1原件 |
| REQ-011.1物流/退款/退货/换货/补件正常与例外 | 查询/五action预览完整；执行未实现 | `policy.py:124`五分支与条件测试；Phase 9/10执行和事件跟进未实现，不全算转人工或七业务完成 |
| REQ-011.2生产/历史/正式/Mock分开 | 本期完整 | `orders.py:4`受控Mock kinds、`verified():42`保留其余kind；`business_read_model.py:124`历史禁Mock政策；SCN029显式合成 |
| REQ-011.3自动内部待办/人工执行/查结果/选择澄清 | 预览条件及既有结果读取完成；写入待9 | `eligibility.py:10`只有preview；`policy_conditions.py:55`最新choice不允许旧同意覆新拒绝；无售后写工具 |
| REQ-011.4订单/具体包裹/来源/时间，原退补区分 | 既有包裹只读完成；查件申请/跟进待9/10 | `business_read_model.py:94`复合关联、`F/.../business-records.ts:157`严格order+line；SCN008 SECOND截图验证 |
| REQ-011.5钱币/额度/同意/退件/规格/库存/地址 | 只读条件完整；执行复算待9 | `policy.py:61`、`policy_ledger.py:30`、`policy_fulfillment.py:20`/`:63`/`:109`；正式HTTP缺库存时间/视觉收件均不eligible |
| REQ-011.6受理/等待/处理中/成功/失败/未知/取消分开 | 既有只读展示完整；生命周期写待9 | `F/.../business-records.ts:35`区分label_created，`BusinessLedger.vue:41`分组；建物流单不显示成发货，policy_ledger未知占用不当成功 |
| REQ-011.7申请≠ERP执行，库存占用对应履约、去重 | 数据结构/既有占用核验完成；事务写待9 | `business_schema.py:103`/`:114`分表，`policy_ledger.py:52`/`:80`单次占用；本期没有新申请、库存reserve或扣库 |
| REQ-011.8同一行份额补偿互斥、改方案先核原操作 | 计算完整；取消/转换待10 | `policy_ledger.py:85`冲突、`policy_conditions.py:96`单位分配；独立财务/份额测试；无取消操作端点 |
| REQ-011.9开发者推进、来源顺序、Agent不得伪造 | 未实现推进；本期边界完整 | 场景创建仅初始状态`fixture_conversations.py:29`；`api/business.py:36`至`:67`无事件推进路由，controller文件不读 |
| REQ-011.10HITL事件屏障与等待唤醒 | Phase 3屏障保留；业务事件待10 | 人审既有测试重跑、root SCN028实际回复后wait_customer；无新增业务事件唤起实现 |
| REQ-011.11归组/结案/语言/历史/预算/前端/无真实支付写 | 本期边界完整，其余继承/后续实现 | 独立scope、历史过滤、模拟只读UI；未新增模型/预算循环、支付ERP/物流下单；系统能力标志诚实 |
| REQ-014.1接收图片字节/格式/限制/CID，禁止远程HTML | 未实现，Phase 8 | `DEV-PLAN.md:166`；本期不新增图片接收、远程访问或声称读图 |
| REQ-014.2候选字符来源/歧义/精确核验 | 业务精确核验基础完成；读图待8 | `business_queries.py:83`scope拒绝；无视觉字符候选模型 |
| REQ-014.3观察/陈述/推测/工具/人工分开 | 资格证据边界完成；视觉存储待8 | `orders.py:42`不提升未知类型、`policy_conditions.py:36`证据kind；4种不可信退件实际HTTP均requires_review |
| REQ-014.4图文+SOP分流，图片不授权/回执需核验 | 程序资格边界完成；模型分流待8/9 | `BT/test_business_regressions.py:166`视觉退件不等于仓库回执；`policy.py:147`不可授权；没有图文端到端结果 |
| REQ-014.5危险HITL/不通电拆机/补问 | 未实现正式视觉危险分流，Phase 8 | `DEV-PLAN.md:166`；普通初始human_review场景不是危险图片分流验收 |
| REQ-014.6合法危险标记直接持久HITL/预算失败不抹除 | 未实现，Phase 8 | 没有视觉Schema/危险程序门；不把既有人工接管协议冒算此需求 |
| REQ-014.7逐图状态、覆盖、技术失败≠模糊 | 未实现，Phase 8 | 系统agent/knowledge=false，尚无逐图接口/组件 |
| REQ-014.8视觉/裁剪/重试共预算、未知用量 | 未实现，Phase 8 | 没有视觉调用或usage；本期测试88绿不证明此项 |
| REQ-014.9会话证据不入共享库、历史/缓存scope | 查询scope基础完成；图片/缓存待8 | `business_read_model.py:24`当前前缀；没有读取图片缓存或写向量库 |
| REQ-014.10不可信图片/指令不扩大权限，观测隐私 | 资格边界完成；模型/视觉观测待8/11 | 请求extra forbid与source kind保留；没有实际图片trace隐私验收 |
| REQ-014.11人工修订/晚到失效/HITL恢复屏障 | 未实现视觉修订，Phase 8 | 当前composable晚到丢弃只证明UI请求，不证明视觉任务失效 |
| REQ-014.12撤销/彻底清理/晚到恢复/保留交易审计 | 未实现，Phase 12 | `DEV-PLAN.md:226`；不关闭任何媒体删除AC |

### 全部REQ、页面及共用约束覆盖

未指定为本期核心的条目也逐项定位，不能遗漏或因阶段PASS改为“已完成”：

| REQ | 当前阶段状态与归属 | 证据 |
|---|---|---|
| 001 | Phase 3身份/导入协议继承，Phase 4独立场景scope已补；生产真实订单授权缺口仍在 | `DEV-PLAN.md:262`、`fixture_conversations.py:29`；listing/group摘要不制造交易 |
| 003 | 模拟来信/人审协议保留；自动模型回复及完整cycle后续7 | `DEV-PLAN.md:264`、runtime `api/system.py:30`agent=false；既有测试重跑 |
| 006 | 业务事实可查；Agent动态决策/案件记忆/多事项等待未实现 | `DEV-PLAN.md:267`，Phase 7/10 |
| 007 | 人审协议保留，新场景human_review不入自动job；危险/模型恢复后续 | `fixture_conversations.py:32`、`BT/test_business.py:131`、`DEV-PLAN.md:268` |
| 008 | 既有持久命令/任务协议保留；业务只读不新建任务；完整模型预算/删除后续 | `fixture_conversations.py:63`、`eligibility.py:10`、`DEV-PLAN.md:269` |
| 009 | 三栏基础+业务详情本期完成；运行/引用/业务执行后续 | `F/components/mail-agent/AgentProcessPanel.vue:83`、`DEV-PLAN.md:270` |
| 010 | 只使用dev场景；评测保留集不读；完整重置/评测后续 | `fixture_loader.py:47`、`DEV-PLAN.md:271` |
| 012 | 最新可见选择/精确目标条件基础；语义理解、多诉求和格式修复后续 | `policy_conditions.py:55`、`DEV-PLAN.md:273` |
| 013 | 无新增观测导出；实际Langfuse/脱敏/usage未验收 | `DEV-PLAN.md:274`，Phase 7/11/12 |

`SCREEN-001`本期业务区符合现有外壳；`SCREEN-002`仍为诚实未实现页面，待Phase 5/6。`CMP-001`增加受控场景入口；`CMP-002/003`保留现有邮件/回放/文字输入，图片待8；`CMP-004`增加只读预览，实际模型工具/引用/token/Langfuse待7/11；`CMP-005`人审保持；`CMP-006/007`知识/导入清理完整功能待5/6/12；`CMP-008`现有账本展示完成，售后申请操作待9；`CMP-009`仅初始场景创建，执行/事件推进待9/10；`CMP-010/011/012`未实现管理/任务/试查；`CMP-013`图片抽屉未实现。依据`Product-Spec.md:567`、`DEV-PLAN.md:278`及`BusinessDetails.vue:1`、`BusinessScenarioLauncher.vue:12`，不存在虚构的可点击执行入口。

5.11六类状态逐项核验：默认不选中不调用预览；加载按钮禁重；空订单与历史不可用分别显示；错误保留查询输入并可重试；场景创建成功选择真实返回会话；受限提示政策未发布/只读，模型功能仍禁用。证据`useBusinessDetails.ts:29`/`:37`/`:59`、`useBusinessPreviews.ts:24`、`useBusinessScenarios.ts:28`、`BusinessDetails.vue:37`/`:81`、实际错误/未知结果截图。模型/知识等未来状态没有本期代验收。

5.12输入逐项核验：mode创建后固定；sender/subject/body/human_reply/note沿Phase 3现有校验，不因场景入口绕开幂等；as_of只由服务器游标/场景时钟确定；精确订单号max100、item_id max160；business_action只接收enum、行、严格正整数数量、最小货币单位整数/币种/编号。请求不能提供scope、consent、evidence、未来时钟或政策版本；额外字段拒绝。前端数额用BigInt和安全整数，不接受指数/超精度；场景写入expected_version/Idempotency-Key由既有命令框架绑定。customer_images/document/scenario_event对应未来8/5/10尚未实现。证据`B/api/business.py:24`/`:45`/`:54`/`:63`、`B/domain/policy.py:15`、`F/.../business-eligibility-input.ts:11`、`F/.../business-format.ts:14`/`:28`、`BT/test_business_api.py:130`。

### 数据实体、关系及架构契约

| Spec实体/关系 | 本期实际覆盖和限制 | 证据 |
|---|---|---|
| DataImport、CustomerIdentity、CustomerConversation、Message | 复用Phase 3，场景创建独立dataset/identity/branch及持久消息；不合并group_id | `fixture_conversations.py:29`/`:37`、`BT/test_business.py:47` |
| MessageAttachment/AttachmentRevision、VisualAnalysis/VisualEvidence/EvidenceRevision | 未建正式图片处理实体，待8 | `DEV-PLAN.md:360` |
| CaseState、UnderstandingResult | 初始场景state受控读取，非正式理解/案件记忆产物 | `fixture_loader.py:11`/`:45`、`DEV-PLAN.md:358` |
| OrderSnapshot、Brand/ProductIdentity | products、orders、order_lines带来源/摘要/时间及同scopeFK | `business_schema.py:24`/`:53`/`:64`，快照不可变触发器 |
| KnowledgeDocument/Version、Block/Chunk/Applicability | 未建知识管理/解析实体；业务compatibility不能冒算文档适用关系 | `DEV-PLAN.md:356`/`:357` |
| EmbeddingProfile/IndexBuild/ChunkEmbedding、Release/IngestionJob/Audit | 未实现，待5/6 | `DEV-PLAN.md:356`/`:357` |
| AgentRun/ToolCall、ReplyArtifact | 既有协议重跑；Phase 4不创建业务模型run/回复产物 | `DEV-PLAN.md:358`、`api/system.py:30` |
| HumanReview | 复用既有人审，初始接管与模拟人工回复保持；不因此签视觉危险分流 | `fixture_conversations.py:32`/`:55`、SCN028根AgentGUI证据 |
| EvaluationCase/Result | 仍隔离，不从保留答案创建运行事实；无准确率结论 | `fixture_loader.py:50`、`DEV-PLAN.md:367` |
| PolicyProfile/Decision | policy_profiles/policy_decisions基础表；本期计算预览不落执行授权，不写交易decision | `business_schema.py:33`/`:135`、`policy.py:147` |
| SimulationBranch/Event | 分支已建，仅读初始state；事件推进未实现 | `business_schema.py:42`、`fixture_ledger.py:18`；controller不读 |
| AfterSalesOperation、ExecutionRecord/Reshipment | operations/executions装已有账本；本期不申请、不人工履约 | `business_schema.py:103`/`:114`、`fixture_ledger.py:37`/`:47` |
| Shipment/ReturnReceipt | 两表装已有记录，复合scope/order/line/op/execution关联；质检份额投影保留 | `business_schema.py:126`/`:130`、`business_projection.py:10` |
| Inventory/Compatibility | 精确商品/部件/地区/硬件，库存缺时间不做可用事实 | `business_schema.py:76`/`:82`、`policy_fulfillment.py:109` |
| TraceCorrelation | 本期无实际Langfuse追踪，待11 | `DEV-PLAN.md:212` |
| 6.2消息与引用来源、游标≠事件、历史对照不注入 | 本期读取守边界；正式知识引用/模型案件待7 | `business_read_model.py:24`/`:30`、`fixture_conversations.py:43` |
| 6.2申请/执行/库存事务、防重与结果恢复 | 既有账本结构及只读互斥核验完整；新业务事务待9/10 | `policy_ledger.py:30`、`DEV-PLAN.md:365` |
| 6.2源快照不可变、Mock属分支、历史不写售后 | 本期完整 | 冻结迁移`:167`、historical read_model`:124`、API无售后执行 |
| 6.2运行库忽略目录、源文件不改、衍生删除 | 本期不改v1/正式数据；完整衍生删除待12 | v1 byte diff零；`DEV-PLAN.md:366` |

主架构第2节scope对应`business_read_model.py:21`服务器绑定、12表FK；第4.4节视觉非交易事实对应`orders.py:42`和证据kind回归，正式图像pipeline尚待8；第5节ToolResult状态/来源/版本对应`business_queries.py:27`；第6节本期场景命令幂等及一致查询已验证，售后事务/锁库后续9；第7节规则与说明绑定但未发布，知识head原子切换后续6；第8节12表及API清单在冻结迁移/标准router中。没有用本期预览替代架构中执行重算或发布门禁。

### 全部82项AC的唯一主归属与本期限制

此表逐项登记，**“保留”不表示本轮替旧报告重新签署；“基础”不表示完整产品AC通过。** 唯一本期主验收项AC-012有实际越权HTTP证据；其他条目的主归属按`DEV-PLAN.md:306`至`:316`，补验约束按`:318`。Spec原checkbox未由审查角色勾选。

| AC | 主Phase | 本轮状态/限制与证据 |
|---|---:|---|
| 001 | 3 | 既有连续消息协议测试保留；本期独立场景不改归组。`DEV-PLAN.md:306` |
| 002 | 3 | group不是身份；本期新scope验证补强。`fixture_conversations.py:29` |
| 003 | 3 | 既有导入幂等保留，真实模型触发不代验。`DEV-PLAN.md:306` |
| 004 | 3 | 查询前缀补强；真实模型请求仍须7补验。`business_read_model.py:24`、计划`:318` |
| 005 | 3 | 历史/对照协议保留；真实模型继承仍须7补验。计划`:318` |
| 006 | 3 | 未来订单/子行/库存本期补强；完整模型查单须7补验。`test_business_regressions.py:69`/`:139` |
| 007 | 7 | 未实现依据生成/自动模拟出站；agent=false。`api/system.py:30` |
| 008 | 7 | 既有幂等基础保留，自动出站完整AC未验。计划`:310` |
| 009 | 7 | 未接模型读取此前模拟回复。计划`:310` |
| 010 | 7 | 已知scope订单可查，模型复用订单号补问未验。`business_queries.py:46` |
| 011 | 7 | 查询/UI多行澄清基础通过，自动回复及知识选择未验。`business_queries.py:90` |
| 012 | 4 | 本期实现匹配：跨客户/分支精确查询拒绝、手动会话不绑他人。`test_business.py:97`、`test_business_api.py:111` |
| 013 | 6 | 业务SKU精确适配不是知识检索AC；RAG未实现。计划`:309` |
| 014 | 6 | 未执行德文→中文前5相关性。计划`:309` |
| 015 | 7 | 元数据不假称读取边界保留；模型回复/支持图片待7/8。计划`:310` |
| 016 | 6 | 本期历史排Mock基础通过；真实历史RAG/模型评测待6/7。`business_read_model.py:71` |
| 017 | 7 | 无订单查询缺口可见；自动补问未实现。计划`:310` |
| 018 | 7 | 既有尝试读取基础，模型不重复失败方法未验。计划`:310` |
| 019 | 7 | 服务器scope拒绝基础通过；邮件指令模型攻击未验。`business_queries.py:83` |
| 020 | 7 | 人审协议基础保留；模型因资料不足转人审未验。计划`:310` |
| 021 | 3 | 既有人审来信屏障测试保留。`test_protocol.py`、计划`:306` |
| 022 | 7 | Phase 3恢复协议保留；实际Agent读取人工回复未验。计划`:310` |
| 023 | 3 | 既有人工结案协议保留；本期不自动结案。计划`:306` |
| 024 | 7 | UI晚到查询抛弃通过，不能代替旧模型终局栅栏。`useBusinessDetails.ts:29` |
| 025 | 7 | 查询技术失败有错误；模型超时/停止真实调用未验。计划`:310` |
| 026 | 7 | 数据持久基础保留；真实模型/发送重启不重复待7。计划`:310` |
| 027 | 3 | 历史可见前缀基础保留并补业务过滤；AI对照模型未验。计划`:306` |
| 028 | 7 | 既有人审GUI保留，SCN028已回归；自动模式模型未验。计划`:310` |
| 029 | 12 | 删除栅栏/衍生内容/晚到重建完整清理未验。计划`:315` |
| 030 | 6 | 知识移除/新检索/旧引用未实现。计划`:309` |
| 031 | 13 | 本报告不报准确率；全量评测与保留集未验。计划`:316` |
| 032 | 7 | 本期业务UI/实际邻居/主题视觉补强；完整Agent引用等待7。视觉节，计划`:310` |
| 033 | 10 | 既有包裹行关联基础通过；查件/延误跟进未实现。`business-records.ts:157` |
| 034 | 9 | 退款资格/额度只读通过；内部申请/模拟执行未实现。`policy.py:61` |
| 035 | 9 | 收件/质检条件只读通过；退货单/推进未实现。`policy_fulfillment.py:20` |
| 036 | 9 | 型号/库存/地址条件只读通过；换补履约未实现。`policy_fulfillment.py:63`/`:109` |
| 037 | 9 | 配件适配/库存只读通过；内部待办/执行跟进未实现。`inventory.py:4` |
| 038 | 9 | Mock初始profile隔离通过；完整业务闭环未实现。`fixture_ledger.py:18` |
| 039 | 9 | 同份额冲突计算通过；Agent完整决策/事务写未验。`policy_ledger.py:85` |
| 040 | 9 | 场景创建未知重试通过；售后操作未知/锁库恢复尚未实现。计划`:312` |
| 041 | 10 | 既有多订单账本能查；方案转换/取消待办未实现。计划`:313` |
| 042 | 10 | 无业务结果事件唤醒/去重跟进。计划`:313` |
| 043 | 10 | 人审屏障基础保留；业务事件仅提示未实现。计划`:313` |
| 044 | 7 | 历史禁Mock查询及无写工具通过；Agent对照提议未验。`business_read_model.py:124` |
| 045 | 7 | 未实现语义多诉求理解。计划`:310` |
| 046 | 7 | 未实现条件退款/物流联合理解。计划`:310` |
| 047 | 7 | 最新choice计算不沿旧同意；动态意图更新未验。`policy_conditions.py:55` |
| 048 | 7 | 未实现理解修复预算及失败收口。计划`:310` |
| 049 | 11 | 未实现真实追踪关联/usage。计划`:314` |
| 050 | 11 | 业务响应私密token不泄露通过；实际trace payload脱敏未验。`test_business_regressions.py:82` |
| 051 | 11 | 未实现真实Langfuse离线导出降级。计划`:314` |
| 052 | 7 | 既有人审屏障基础；新run/trace不重放动作未验。计划`:310` |
| 053 | 10 | 无模拟执行业务事件及自动跟进。计划`:313` |
| 054 | 9 | 账本按真实执行kind/状态计算基础；完整Agent结果误判防护待9。`policy_ledger.py:52` |
| 055 | 5 | 未执行PDF图文解析位置验收。计划`:308` |
| 056 | 6 | 未实现章节范围切分/停用检索。计划`:309` |
| 057 | 6 | v2未发布是基础；知识入库失败/旧发布可用未实现。计划`:309` |
| 058 | 6 | 同版说明/规则摘要通过；原子发布/回滚检索快照未实现。`build_policy.py:123` |
| 059 | 6 | 下架/迟到入库未实现；在途回复另需7补验。计划`:318` |
| 060 | 12 | 原件/衍生/缓存/备份彻底删除未实现。计划`:315` |
| 061 | 6 | 无向量构建/重复生效块/输入复用。计划`:309` |
| 062 | 6 | 无Embedding空间切换及失败回退。计划`:309` |
| 063 | 5 | 无跨页步骤/表格/图片范围解析验收。计划`:308` |
| 064 | 6 | 知识业务人员维护/发布/试查UI未实现。计划`:309` |
| 065 | 8 | 精确查询基础通过；图片提取核验未实现。计划`:311` |
| 066 | 8 | 查单不猜编号基础；图片字符/冲突澄清未实现。计划`:311` |
| 067 | 8 | 不可信视觉kind保留基础；实际观察定位未验。`orders.py:42` |
| 068 | 8 | 客户陈述不能变收件证据；正常图/功能故障理解未验。邻接来源测试 |
| 069 | 8 | 程序资格基础；图文SOP分流未实现，真实动作另需9补验。计划`:318` |
| 070 | 8 | 无有效危险标记程序持久HITL。计划`:311` |
| 071 | 8 | 图片不能变仓库/交易事实通过；读图与真实动作完整AC须8/9。`test_business_regressions.py:166`、计划`:318` |
| 072 | 8 | 未实现图片质量/技术错误区分。计划`:311` |
| 073 | 8 | 未实现受控图片/CID接收；无远程图访问。计划`:311` |
| 074 | 8 | 业务scope/前缀基础；图片读取/缓存越界未验。计划`:311` |
| 075 | 8 | 请求权限不能制造同意；图内prompt攻击未验。`policy.py:15` |
| 076 | 8 | 无实际视觉usage/预算/多图成本验收。计划`:311` |
| 077 | 8 | UI请求晚到丢弃不是视觉任务fencing；完整未实现。计划`:311` |
| 078 | 12 | 图片及衍生撤销/备份晚到不复活未验。计划`:315` |
| 079 | 8 | 逐图关联/限制/覆盖未实现。计划`:311` |
| 080 | 8 | 视觉人工更正/修订/缓存屏障未实现。计划`:311` |
| 081 | 8 | 图片上传预览移除未实现；本期业务UI不暴露地址token。计划`:311` |
| 082 | 13 | 图片专项真实输入未由本期代验；Phase 1原FAIL与人工pending保留。计划`:316`/`:318` |

### 原FAIL与本次修复的独立证据

| 原问题/新增相邻问题 | 本次独立复现及结论 |
|---|---|
| 初审HIGH：收2检1投影丢失变eligible | `BT/test_business_regressions.py:41`真实PG→统一查询→资格HTTP；检1无units为needs_input、检1显式['0']为wait、检2['0','1']为eligible；三者authorized=false。`business_projection.py:10`保留两质检字段。已闭合 |
| 第二轮HIGH：choices[c2拒绝,c1同意]反序 | `BT/test_business_regressions.py:116`真实两个持久seq及反序数组；最新拒绝/改动作/目标null均阻eligible且customer_choice=needs_input。`business_read_model.py:144`绑定排序、`policy_conditions.py:66`独立取maxseq；另外同seq/缺seq邻接反例均needs_input。已闭合 |
| 第三轮HIGH：库存无snapshot仍正式HTTP换货eligible | `BT/test_business_regressions.py:139`同时核对availability和正式HTTP：无时间/未来时间unknown、available_quantity=null、eligibility needs_input；有效时间正例ok/eligible。`policy_fulfillment.py:116`严格时间，`business_queries.py:126`保留未知。已闭合 |
| 历史合法父订单夹Mock子行泄SKU | `BT/test_business_regressions.py:69`数据库真的有合法父与synthetic行；公开lines为空且不存在该SKU；`business_read_model.py:71`/`:56`逐行/product过滤。已闭合 |
| 同SKU行与包裹/客户选择UI不明确 | 实际SCN008第2行仅SECOND运单；真实choice金钱/数量/动作/第n封/地址版本截图；`business-records.ts:157`严格order+line。已闭合 |
| 未明确多行选择/未来选择/地址token | `BT/test_business_regressions.py:82`/`:104`源DB含未来choice，公开过滤且无token，多行不猜line/qty；单行qty1才补`business_customer_view.py:14`。已闭合 |
| 包装visual_observation为fixture仓库事实 | `BT/test_business_regressions.py:166`正式装载/HTTP不能满足warehouse_receipt；额外customer_statement/visual_observation/hypothesis/unknown四种均requires_review。`orders.py:42`仅known controlled Mock kinds提升。已闭合 |
| 显式未来消息地址进入资格 | `BT/test_business_regressions.py:177`公开address=null且内部state无address；`business_read_model.py:150`验证消息可见。已闭合 |

三份历史报告保持原文与原结论：`PHASE-4-REVIEW.md`为初审FAIL；`PHASE-4-REVIEW-FINAL.md`为第二轮FAIL；`PHASE-4-REVIEW-PASS.md`文件名含PASS但正文为第三轮FAIL。本报告是新的第四轮结论，未将历史失败抹去。

**Stage 1签署：PASS。** 未发现本期HIGH或MEDIUM。完整产品中的后续未实现项已逐项列出；按主归属不能因为它们尚未实现就假称本期失败，也不能因为本期通过提前关闭它们。Stage 2在上述回归及边界核验完成后执行。

## Stage 2：Code Quality

### 质量、安全与scope

| 检查 | 结论及证据 |
|---|---|
| 命名/职责/类型/文件大小 | 查询、投影、客户公开视图、资格条件/履约/账本、API和UI请求分别模块化；57份本期源码含测试扫描无TS/Vue `any`，无>300行。最大工作台258、test_business228、queries201、冻结迁移200、loader191。`BusinessResult`/表单契约见`F/api/business-contract.ts:1`；错误/晚到状态有明确处理 |
| 一致事务 | `business_queries.py:18`连接先设隔离再begin；`BT/test_business.py:211`真实双连接snapshot反例。与[SQLAlchemy官方隔离级别说明](https://docs.sqlalchemy.org/en/21/core/connections.html)核对，不能把多次独立读或单次查询当一致快照 |
| 严格输入/金额精度 | Pydantic strict/extra forbid加整数约束，bool/float/制造consent等正式HTTP拒绝；前端BigInt校验最小货币单位、安全范围，不隐式汇率折算。`policy.py:15`/`:61`、`business-format.ts:14`/`:28`；已核对[Pydantic官方严格类型说明](https://docs.pydantic.dev/latest/concepts/strict_mode/) |
| SQL/注入 | 业务查询使用SQLAlchemy表达式和参数；冻结DDL的text只含迁移固定表名，测试服务schema为受控随机UUID，不将请求字符串插入SQL。`0003_business_catalog.py:167`/`:189`、`phase3-test-server.py:58`/`:127` |
| 密钥/危险执行/DOM/路径 | 扫描本期57份源码未发现硬编码sk类Key/密码、暴露VITE密钥、eval/exec、危险HTML写入、用户目录绝对路径。公开choice/address字段白名单无地址token/原客户ID，错误封装不吐数据库信息。`business_customer_view.py:4`/`:6`、`business_queries.py:21`、`test_business_regressions.py:82` |
| 服务器可信scope与防权限伪造 | 服务器从conversation绑定scope/time/policy；请求不收identity/branch/consent/evidence/version/as_of。`api/business.py:24`、`policy.py:15`；跨客户/手动无绑定实际HTTP证据；库存/evidence来源不足不能提权 |
| 源码/资料scope creep | 场景基线创建、业务详情、查询/预览、v2解释器均已在Phase 4实施约定；12表提前装已有账本由计划明确授权。没有模型、知识发布/向量检索、售后执行/库存占用、未来事件推进、真实邮箱或支付连接。`api/business.py:36`、`eligibility.py:10`、`api/system.py:30` |
| decision_id用途 | `policy.py:147`始终不授权，`:151`仅摘要；API无接受decision_id的执行路由，界面明确“条件满足尚不能执行”。不是执行令牌 |

### 测试真实性与剩余盲区

- 88项后端本轮真实启用数据库，**无skip**；`BT/test_protocol.py:30`的环境条件满足，`:33`随机schema、`:49`实际Alembic升级、`:60`只清理自己的schema/temp。未在正式服务创建测试订单/会话。测试没有把数据库缺失跳过再称绿。
- 8项回归读取受控prepared副本，真实装载到PG，经过正式read_model/queries/EligibilityService/HTTP，验证投影与来源包装，不只直接给纯函数喂“正确事实”。库存正例提供明确地区/硬件/可信有效snapshot，负例只变时间；同时断言availability与eligibility避免两条路径标准分裂（`test_business_regressions.py:139`）。
- 收2检1覆盖有/无单位分配，既断言投影字段又断言condition/outcome与不可授权（`:41`）；反序choice先持久两条message再由seq核验（`:116`）；历史父/子混合来源和未来choice明确证明隐藏输入确在数据库（`:69`/`:99`）。这些前提生产路径可达，断言方向正确。
- `BT/test_business_api.py`覆盖纯只读前后核心/账本/库存计数一致、跨scope、请求extra/strict字段及真实依赖故障；`test_business.py:211`不是mock隔离标志而是实际并发读实验。政策财务测试覆盖30日/365日/7日边界、部分退款2000/2001、币种、分配份额、成功/处理中/未知/失败执行、冲突及重复占用。
- 前端28项含实际Vue composable状态请求、切会话/输入revision晚到响应丢弃、错误保留文本、创建结果未知保留同key/body。mock网络单元测试不等同真实断网/丢响应；真实路径由主Agent的route.abort/route.fetch实测及本审查实际页面补充，来源在下节区分。
- 尚无真实模型、完整七业务、RAG、图片字节/视觉usage、售后写事务与未来事件的测试；它们对应未实现阶段，不用当前88/28数量掩盖。当前没有获授权真实客户订单，SCN029只是合成历史边界。Phase 1原失败和人工pending继续有效。

### 实际页面与视觉对比

审查者使用独立`phase4_review_closed` CLI session打开15174工作台，实际创建SCN025并展开业务详情/只读资格，看到真实订单、来源、USD35.99、缺库存时间/规格、既有补偿与未发布门禁。实际页面没有模型成功/已退款/已扣库提示；打开只读预览后条件结果为需人工核对。随后打开同工程知识管理邻居，等待实际DOM完成后查看页面。第一次导航过渡截图不作为设计证据。

审查者实际读取的页面证据：`.playwright-cli/page-2026-10-08T03-18-01-155Z.yml`、`page-2026-10-08T03-19-53-237Z.yml`；实际查看业务截图`page-2026-10-08T03-19-22-365Z.png`和知识邻居截图`page-2026-10-08T03-22-08-544Z.png`。CLI session已仅通过`-s=phase4_review_closed close`关闭；未运行close-all，未关闭其他会话或主Agent服务。

下列主Agent生成的PNG均由审查者实际打开查看像素，与`output/playwright/phase3-light-wide.png`、`phase3-knowledge-light.png`、`phase3-knowledge-dark.png`及上述现有知识页面对比；不是仅数class或确认文件存在：

| 图片 | 实际视觉结论与证据限制 |
|---|---|
| `phase4-business-desktop.png`、`phase4-conditions-desktop.png` | 与既有侧栏/顶栏/页签/白色圆角卡片/薄边框/蓝色按钮一致，来源/时刻/货币/未发布/逐条件可读，业务区密度延续工作台；自己的实际预览也复核行为 |
| `phase4-network-error.png` | 错误反馈在业务区，精确查询输入保留；真实断网及恢复动作由主Agent执行，记录见PHASE-4-VALIDATION，不冒称审查者亲自注入故障 |
| `phase4-multiline.png` | 相同SKU两行以第1/第2项清楚区分；当前第2项只展示SECOND运单，无首行包裹混入；代码严格order+line对应`business-records.ts:157` |
| `phase4-choices.png` | 实际客户choice退款同意、数量1、USD54.99、来源第1封/第1项、地址版本均显示；候选表单与已取得选择分开；未知地址版本如实提示 |
| `phase4-narrow-light.png`、`phase4-narrow-dark.png` | 900px详情抽屉保留阅读/查询/条件，主题背景、边框、文字对比及按钮沿邻居；截图中无裁断关键标签。主Agent另记录两主题scrollWidth=clientWidth=900，数值不是本审查独立测量 |
| `phase4-historical.png` | 合成历史标记和真实可见消息截点清楚；无订单、政策或SKU补造。SCN029原clock 9月1日/消息10月8日不一致未偷偷改源，由真实游标确定as_of |
| `phase4-create-unknown.png` | 真实创建响应未知时弹窗保留场景输入及重试；主Agentroute.fetch先提交后abort、同key/body重试sameCID/list仅1条证据见验证记录。不是仅按钮disabled证明幂等 |
| `phase4-human.png` | 人工回复后wait_customer、模拟人工邮件与客户邮件分开；人审按钮及消息样式延续Phase 3。执行/草稿/回复由主Agent实测，本审查看图核对最终状态 |

`Product-Spec.md:584`的内容宽度不足1024转详情抽屉符合现有工作台实现；900px实际明暗图满足本期窄屏可用标准。移动端精细适配列P1，本轮不签手机全尺寸验收。知识邻居仍为诚实占位，并未把空知识页当已完成管理入口。

### LOW-001：缺口汇总的三个条件名没有中文映射

位置：`F/components/mail-agent/business-format.ts:50`/`:97`/`:98`；调用：`BusinessEligibilityForm.vue:105`。领域会返回`warehouse_receipt`、`warehouse_inspection`、`delivery_date`，但字典只有return_receipt/inspection/delivered_at等别名。独立执行真实formatter：

```text
missingLabels(["warehouse_receipt", "warehouse_inspection", "delivery_date"])
未确认的业务字段
```

三个不同缺口在末尾汇总被同一fallback去重，精细信息减少。具体条件列表使用后端中文label（`BusinessEligibilityForm.vue:95`），仍正确显示仓库收件/质检/时间条件，计算、阻止授权、正式HTTP结果均不受影响。因此定级LOW增强建议，建议后续补齐映射；不能把它升格为旧HIGH，也不能因反复修审降低资格门槛。本轮不修改代码。

### 独立执行的测试、编译与数据一致性原始输出

连接串只从忽略目录settings读取并赋测试环境变量，未打印。PYTHONPATH为backend/src绝对路径。下面为实际输出原文摘录，成功用例长列表/构建资源表省略；没有用主Agent结果替代审查者执行。

后端命令：`globalmail-agent/backend/.venv/Scripts/python.exe -X utf8 -m unittest discover -s globalmail-agent/backend/tests -v`。

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
test_future_address_confirmation_is_not_projected_or_used ... ok
test_historical_parent_does_not_authorize_synthetic_child_line ... ok
test_inspected_share_survives_database_projection_and_service ... ok
test_inventory_time_gap_cannot_become_eligible_in_formal_http ... ok
test_latest_choice_uses_message_sequence_not_fixture_array_order ... ok
test_loading_fixture_cannot_upgrade_visual_evidence_to_warehouse_fact ... ok
test_multi_line_choice_remains_unbound_without_explicit_target ... ok
test_public_choices_exclude_future_messages_and_private_address_tokens ... ok
test_database_failure_and_missing_table_are_degraded ... protocol_worker_dependency_unavailable
ok
----------------------------------------------------------------------
Ran 88 tests in 99.503s
OK
```

测试退出码0，无skip。弃用警告真实保留，不当测试失败，也未擅自升级依赖。依赖故障用例的worker告警是预期故障路径，不掩盖为无故障日志。

额外邻接边界通过内存prepared副本和随机schema执行，没有改v1或提交测试文件：

```text
test_adjacent_receipt_sources ... ok
test_adjacent_choices ... ok
test_adjacent_missing_stock_kind ... ok
test_verified_preserves_all_untrusted_kinds ... ok
Ran 4 tests in 4.109s
OK
receipt_kind=customer_statement outcome=requires_review
receipt_kind=visual_observation outcome=requires_review
receipt_kind=hypothesis outcome=requires_review
receipt_kind=unknown outcome=requires_review
choice=same_seq outcome=needs_input
choice=missing_seq outcome=needs_input
inventory_kind=customer_statement outcome=needs_input
inventory_kind=visual_observation outcome=needs_input
inventory_kind=unknown outcome=needs_input
verified preserves untrusted source kinds: PASS
```

前端目录执行`pnpm exec tsx --test scripts/*.test.ts`，退出码0：

```text
ℹ tests 28
ℹ suites 0
ℹ pass 28
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 654.3683
```

同目录`pnpm build`，退出码0；资源大小表省略，未记录本审查构建耗时因而不填估计值：

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3277 modules transformed.
rendering chunks...
computing gzip size...
```

`python -X utf8 -m compileall -q globalmail-agent/backend/src globalmail-agent/backend/migrations data/knowledge/v2`无诊断，单独复核输出`compileall exit=0`。venv没有pip模块，实际使用`uv pip check --python globalmail-agent/backend/.venv/Scripts/python.exe`：

```text
Using Python 3.12.10 environment at: globalmail-agent\backend\.venv
Checked 24 packages in 1ms
All installed packages are compatible
```

`python -X utf8 data/knowledge/v2/build_policy.py --check`实际原输出：

```json
{"status":"verified","publication_status":"unpublished","artifacts":{"policies/policy-profile.json":"cf355a4031415ccccc6be439a24703b80aa7d6de9270591cc3dca34fe86bac19","policies/policy-profile.md":"05d051061c181a5809e73f2068b65dfbbce75b491b34c0c110f265317fc45b34","policy-bundle.json":"21440f5c07181c85430f86e548aff0b41d5566a74934789194de5c03075ed2f5"}}
```

v1逐文件与`git show HEAD:<path>`原始字节比较：

```json
{"v1_tracked_files":111,"byte_differences":[]}
```

源码扫描结果原值：`source_count=57`、`over300={}`、`danger=[]`、`secret=[]`、`absolute=[]`、`any=[]`、`v1_tracked_changes=[]`。扫描结果结合手工SQL/字段白名单/FK审查，不能只凭正则无命中推定权限安全。

主Agent另提供最终重复回归88/88（98.897s）、前端28/28（666.8995ms）、Vite26.22s及正式本机0002→0003升级后只读核验：head0003、12业务表零行、原核心四表前后为空且相等、phase4/72目录正常。这些归属`PHASE-4-VALIDATION.md`，审查者独立随机schema迁移/88项证据在上，不冒称亲自操作正式启动/升级。

**Stage 2签署：PASS，LOW-001保留为非阻塞建议。** 文件大小、类型、安全边界、测试真实性、编译及实际视觉均有本轮证据。主Agent可据此完成本期验证与交接收尾；完整产品、Phase 1失败、人工pending和后续阶段AC仍按原文继续，不由本报告关闭。
