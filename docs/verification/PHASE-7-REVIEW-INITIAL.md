# Phase 7 第一轮独立审查

日期：2026-10-08；审查窗口截至 17:06（Asia/Shanghai）。结论：**Stage 1 FAIL，3 项 HIGH；Stage 2 未执行。**

本轮基于 `dd95be236b6d327c2e10adbadc10053e28107f37` 上的未提交变更、新增源码和读取时工作区进行独立审查。主 Agent 同时修复、测试 Agent 同时补测，因此这是首轮发现记录，不能用于证明之后工作区的状态。只写本报告，未修源码、未提交、未重启服务。所有数据库复现使用随机 `test_protocol_<UUID>` schema 和临时对象目录，连接仅从忽略的 `.local-data/runtime/settings.json` 注入，未输出凭据，未写正式 public 业务数据；复现完成均执行 fixture cleanup。

已读取 `code-review/SKILL.md`、`code-reviewer.toml`、项目规则、需求、架构、计划、文档索引、交接和 Phase 7 实施步骤。范围为 Phase 7 的 REQ-002/003/004/005/006/007/008/009/012/013、指定 22 项 AC、FT-01/02/04/05/08/09/10。售后写工具、正式图片、Langfuse 服务和完整删除分别留 Phase 9/8/11/12；没有以这些后期能力缺失判 HIGH。正在制作的模型/页面质量报告缺失仅记未验收。

## 1. HIGH：终局仍能把无依据的执行成功和危险操作写成模拟已发送

**H-01，当前复现失败。**

需求原文：

- Product-Spec.md:369：`MUST 对外回复中的订单事实和产品步骤提供可追溯依据`。
- Product-Spec.md:370：`MUST 把补偿、发货等未执行建议与实际执行结果分开`。
- Product-Spec.md:628：`虚构已执行退款/补发`属于必须判失败的错误边界。
- docs/planning/PHASE-7-IMPLEMENTATION.md:24：`本期不能声称办理成功`。

实现差异：`globalmail-agent/backend/src/globalmail_agent/application/commit_outcome.py:52` 只遍历模型提供的 claims，:55/:57/:59 仅在模型自报 kind 为 product_step/order_fact/customer_fact 时要求对应来源。`globalmail-agent/backend/src/globalmail_agent/agent/tool_schemas.py:37` 允许 clarification/proposal 的无来源 claim。没有核验 claim 类型与正文实际含义、正文实质声称覆盖或执行成功对应的账本事实。模型把全部正文标为 clarification 后即可通过 :97 的 validate_draft 并在 :102 写模拟邮件。

真实 PG 可复现步骤：使用现有 `AgentFixture` 创建只有 “My lamp has stopped working.” 的客户会话，执行 `ScriptedModel(understanding, terminal(body))`。现有 `terminal`/`draft` helper 把整段 body 放入单个 `clarification` claim，source_ids/citation_ids 均为空（`globalmail-agent/backend/tests/agent_fixture.py:23`）。body 为下列原始输出中的文本。不查询订单、不检索知识、不读取既有执行记录，仍提交一封邮件。

原始输出（exit code 0）：

```text
REPLY_GROUNDING {"result": {"artifact_id": "d072ff47-a006-476f-b818-f55bae79d638", "outcome": "reply_and_wait"}, "outbound_count": 1, "body": "Your refund of EUR 999 has completed and your replacement has shipped. Open the lamp housing and bridge the two terminals.", "tool_names": ["create_reply_draft"]}
```

这证明生产提交门缺少必要的依据验证；脚本模型只用于固定反例，没有宣称真实 Qwen 已产生这段错误输出。复审须证明对错标 clarification/proposal、未列入 claims 的实质段落、错误执行状态和无适用资料步骤都拒绝提交，同时保留正常补问和未执行方案建议。

## 2. HIGH：基础等待早到事件不排后继，未观察的 wake 被终局全量消费

**H-02，读取时实现及真实复现失败；主 Agent 正在改动，修后必须重新验证。**

需求原文：

- DEV-PLAN.md:165：`Phase 10扩展业务事件，不延后基础防漏唤醒规则`。
- AGENT-ARCHITECTURE.md:130：`若结果已变化或条件已满足，在同事务保存wake_pending及唯一后继触发`；`wake_pending只有被新run实际观察并提交结果后才能消费，排队本身不算消费`。

读取时实现差异：

- `globalmail-agent/backend/src/globalmail_agent/application/waits.py:34` 的 record_wake 只 upsert 状态/版本；:35 明示 future receiver，没有递增 input_revision 或创建唯一后继。
- 同文件 :27 检测先到新版本后只抛 `stale_business_context`，未形成可恢复后继。
- 同文件 :44 的 consume_wakes 把该会话所有 pending 改 processed，未核验 run 观察了哪个 condition/version。
- `globalmail-agent/backend/src/globalmail_agent/application/commit_outcome.py:127` 在任意终局调用上述全量消费。
- `globalmail-agent/backend/src/globalmail_agent/agent/context.py:61` 当时 payload 没有 wake/最新业务版本；`agent/tool_schemas.py:48` 当时只允许客户信息/反馈等待，业务等待无可达注册入口。

真实 PG 可复现步骤：创建会话、领取任务、构建 context；在 guarded 会话事务内 `record_wake(conn, conv, 'customer_information:customer', 1)`；再以 observed_version=0 注册同一条件。随后使用旧 context 提交不相关 `customer_feedback` 正常补问。检查 jobs、input_revision、wake_pending。

原始输出（exit code 0）：

```text
EARLY_WAKE {"registration_error": "stale_business_context", "jobs_added": 0, "input_revision_delta": 0, "wake_status": "pending", "context_has_wake": false}
UNOBSERVED_WAKE {"result": {"artifact_id": "6d7cfdd5-b95a-46b6-8de7-dad61b258c33", "outcome": "reply_and_wait"}, "wake_status": "processed"}
```

这不是要求 Phase 10 的完整业务事件控制台，而是本期已承诺的基础版本/排后继/消费协议。复审必须覆盖事件先到、wait 先到、旧 run 尚未观察、更新多次、人审期间抑制与保留、观察后合法提交才消费。

## 3. HIGH：已识别且未解决的文本危险没有跨轮确定性加载门

**H-03，当前危险原子修复后仍真实复现失败。**

需求原文：

- AGENT-ARCHITECTURE.md:226：`已有有效风险进入load_context时同样先检查此门`。
- AGENT-ARCHITECTURE.md:228：风险带 `active / resolved_by_human / corrected_by_human`；`仅点完成回复不自动清除风险`；`不能让模型自行清除未处理风险`。
- DEV-PLAN.md:160：本期交付 `风险直接人审`。

实现差异：当前 `globalmail-agent/backend/src/globalmail_agent/agent/graph.py:68` 已在有效新风险时直接调用 risk_handoff；`application/commit_outcome.py:82` 在同事务保存 understanding 和 HumanReview，这部分本轮中已修。但 `agent/context.py:34` 不读取会话仍有效的旧风险，`adapters/agent_schema.py:34` 仅保存 run 级 understanding 对象，没有风险 active/人工解决状态；新 run 再依赖模型本轮 risk_flags。`application/human_review.py:84` 完成回复后进入 human_wait_customer，下一来信恢复时没有未处理风险门。

真实 PG 可复现步骤：客户 “The plug sparked and I felt an electric shock.”；来源有效 electric_shock 理解后第一轮 handoff。人工回复 “We have received your information.”，备注 “No risk resolution or correction has been made.”，没有结构化解决/纠正危险。客户再来 “Any update?”；脚本固定新理解 risk_flags=[]，随后普通草稿。新 run 仍调用两次模型并自动出站，未创建新 review。

原始输出（exit code 0）：

```text
ACTIVE_RISK {"first": {"artifact_id": "cb1d20b1-17a7-4060-9cac-8a9c3f1983d6", "outcome": "handoff"}, "second": {"artifact_id": "03e6c44b-ba6b-446f-b500-71dd7fe2a176", "outcome": "reply_and_wait"}, "model_requests_in_new_run": 2, "human_review_count": 1, "new_outbound": 1, "context_risk_keys": []}
```

复审须证明未解决风险在 load_context 时无需新增模型/工具就重新安全收口；人工明确解决/纠正须有版本与来源，模型不能自行清除。这里是已交付文本危险，不要求 Phase 8 图片流程。

## 4. 本轮中已修改的发现

最初读取 `agent/graph.py:68` 调 save_understanding，再由 `worker/agent_runner.py:77` 调 risk_handoff，风险与 HumanReview 分属两个提交。违反 AGENT-ARCHITECTURE.md:226 的同事务要求，存在持久危险已保存、人审未保存的崩溃窗口。

主 Agent 在本轮改为 `agent/graph.py:68` 直接 risk_handoff，`application/commit_outcome.py:82` 使用同一 guarded 事务的 store_understanding 后建立 review。上述 ACTIVE_RISK 的 first=handoff 证明正常危险路径仍可收口。**本报告将原子拆分记为迭代已改，不作为第 4 项当前 HIGH；同事务回滚/提交后 checkpoint 拒绝及原凭证回查仍须复审故障验证。**

## 5. 指定 22 项 AC 逐项状态

以下“代码存在”只表明实现可定位，不替代仍在进行的真实模型/UI验收；没有把未验收写成通过。

| AC | 原文目标 | 读取时结论与证据 |
|---|---|---|
| 007 | 完整有依据回复自动模拟发送 | 部分实现；`application/commit_outcome.py:101` 自动写 Message，但 H-01 的无依据正文也被放行。 |
| 008 | 同请求不重复出站 | 代码存在；`application/commit_outcome.py:19` 原 cycle 凭证回查；`adapters/agent_schema.py:41` reply_artifacts cycle 唯一；`tests/test_agent_outcomes.py:37` 有重复反例。独立完整故障验收未完成。 |
| 009 | 第三轮读取旧回复及反馈 | 代码存在；`agent/context.py:36` 加载全部可见模拟消息；`tests/test_agent_outcomes.py:118` 检查 sender 前缀与失败反馈。三封真实 Qwen 质量仍未验收。 |
| 010 | 复用已知订单 | 代码存在；`agent/context.py:36` 保留原文；`agent/tool_gateway.py:88` 要求订单号在可见来源；decision.md:3 明确复用。真实模型不重复索取仍未验收。 |
| 011 | 多商品澄清，不任选 SKU | 代码存在；`agent/tool_gateway.py:75` scoped line 查询；`tests/test_agent_tools.py:40` 多商品/外部 line 反例；decision.md:3 明确不得默认第一件。真实模型澄清质量未验收。 |
| 015 | 未读附件/视频不声称已读 | 部分实现；`agent/context.py:64` 明示文本限制，decision.md:7 提示；最终正文只有模型自报 kind 校验（H-01），尚无正文真实性门的完整证据。 |
| 017 | 缺订单正常补问 | 已观察可达补问提交；`tests/agent_fixture.py:23` 和本轮两个真实 PG 补问终局。真实 Qwen 是否无理由转人工仍未验收；错误型号步骤可经 H-01 放行。 |
| 018 | 不重复失败步骤 | 部分实现；`agent/context.py:36` 保留旧回复；decision.md:5 要求新依据/人审；`tests/test_agent_outcomes.py:118` 只证明读取，未证明程序拒绝重复步骤，真实质量未验收。 |
| 019 | 注入不跨客户/不改变发信边界 | scope/schema 代码存在；`agent/understanding.py:7` extra forbid；`agent/tool_gateway.py:75` scoped detail；`tests/test_agent_tools.py:14`/ :26 反例；模拟发信固定 `application/commit_outcome.py:101`。H-01 仍允许错误业务/操作正文。 |
| 020 | 无依据下一步人审、零出站 | 部分实现；`application/commit_outcome.py:81` handoff 原子建 review；但 H-01 可把无依据步骤改标签直接出站。 |
| 022 | 人工完成后下封新来信自动恢复并含备注 | 代码存在；`application/human_review.py:84` 门禁；`agent/context.py:42` completed notes；`tests/test_agent_outcomes.py:72` 与本轮 ACTIVE_RISK 均实际走新来信恢复。未解决风险恢复缺门见 H-03。 |
| 024 | 新输入/接管拒绝旧结果 | 代码存在；`agent/guard.py:46`–:66 事务资格；`tests/test_agent_faults.py:133` deterministic Event 反例已编写，独立执行未完成。 |
| 025 | 超时/停止零出站，原因和步骤可见 | 代码存在；`worker/agent_runner.py:131` 持久失败；`agent/graph.py:45` 超时；`frontend/src/components/mail-agent/AgentRunPanel.vue:11` 与 :47 显示错误/工具；UI/全故障独立验证未完成。 |
| 026 | 终局重启持久，不重调/重发 | 代码存在；`application/commit_outcome.py:19` 先查原终局，`worker/agent_runner.py:50` 无模型回查；`tests/test_agent_outcomes.py:52` 提交响应丢失测试。独立实测重启未完成。 |
| 028 | 接管理由、人工输入、处理按钮 | 代码存在；`frontend/src/components/mail-agent/HumanReviewPanel.vue:24`、:47、:80；`AgentRunPanel.vue:72` 终局材料。页面渲染未独立验收。 |
| 032 | Art 基线、主题、引用/人审、首次无演示接口 | Element Plus/主题类复用代码存在：`AgentRunPanel.vue:54`、`ReferenceDrawer.vue:2`、`views/mail-agent/index.vue:135`。实际明暗/两尺寸及邻居渲染尚未对比，不宣称匹配。 |
| 044 | 历史只建议，无模拟售后执行或 Mock | 代码存在；`agent/context.py:47` 历史 facts 重建清空、:59 无授权 manifest 不回退；`agent/tool_gateway.py:122` historical RAG unavailable；TOOLS 无售后写。正文虚构成功门缺口见 H-01。 |
| 045 | 两诉求及各自对象 | schema 支持；`agent/understanding.py:16`–:23 Intent 对象/条件、:45 多条 intents；`tests/test_agent_tools.py:114` 固定多诉求样例。真实 Qwen 提取未验收。 |
| 046 | 条件退款不立即创建 | 工具边界已限制；`agent/understanding.py:22` consent 分离，`agent/tool_schemas.py:58` 无售后写，`tests/test_agent_tools.py:114` 零业务行断言。错误执行成功文案仍可出现 H-01。 |
| 047 | 工具/人工可修正初始理解并保留来源 | 部分实现；`agent/graph.py:111` 工具结果进入后续决策，`agent/memory.py:41` 仅支持消息来源 facts 更新；`StateUpdate` (`agent/tool_schemas.py:32`) 无 intent 修订、Fact.kind 无 tool_fact、validate_sources 只消息/人工 notes。理解 UI/保存对象始终为初始理解，修正意图和工具来源修订尚缺明确实现。 |
| 048 | schema 持续失败受预算、明确停止 | 代码存在；`agent/graph.py:63` 最多两次 schema 修复，:87 明确异常；`worker/agent_runner.py:134` failed/budget 状态；`tests/test_agent_faults.py:14` 反例已编写，独立执行未完成。 |
| 052 | 人审后新 run/trace，不重放旧动作 | 代码存在；`worker/agent_runner.py:42` 每 run 新 trace；`AgentGraph.invoke` (`agent/graph.py:117`) 新 run ID 和新输入，不 resume；`tests/test_agent_human.py:17` 两顺序/新 trace 测试。文本风险状态跨轮缺口见 H-03。 |

路径说明：上表 backend 短路径均相对 `globalmail-agent/backend/src/globalmail_agent/`；tests 相对 `globalmail-agent/backend/`；frontend 路径相对 `globalmail-agent/`。文件行号以本轮读取版本为准。

## 6. REQ 功能范围逐项对照

| REQ | 本期已定位实现 | 部分/未实现及阶段边界 |
|---|---|---|
| 002 | `agent/context.py:36` 可见前缀，:47 历史 facts 清空，:48 历史 as_of；`agent/tool_gateway.py:122` 禁 simulation manifest 回退；`tests/test_agent_outcomes.py:130` future/AI/human 对照哨兵 | AC-004/005/006 原文已核对（Spec:276–285）；没有允许的历史知识清单就返回 unavailable 合规。历史实际请求/浏览器截点未独立执行；正文声称错误受 H-01。 |
| 003 | `application/commit_outcome.py:101` 正式模拟 Message 一次提交；:19 原终局回查；后续 context 全前缀；仅本地模拟 | 依据验证不完整 H-01；独立真实三封质量未验收。 |
| 004 | `agent/tool_gateway.py:87` 原文订单候选；:75/:119 scoped line/SKU 工具核验；`application/business_queries.py:10` 复用已交付业务查询 | 多商品/真实澄清质量未验收；字段缺失和历史快照区分依赖 Phase 4 服务；不要求 Phase 8 图片候选。 |
| 005 | `agent/tool_gateway.py:118` 当前 pinned release 的 RAG；:144 正文暴露前登记全部 references；`agent/guard.py:17` 全 active deps；`worker/agent_runner.py:71` 最多一次重建原预算 | Phase 6 上传/核对/发布/下架继续沿用，本期不要求重做向量评测或完整删除；未读附件真实性和最终依据门见 H-01。RAG并发窗口独立实测未完成。 |
| 006 | `agent/graph.py:23` 单主动态图、:36 共用预算；`agent/memory.py:14` facts/revisions；context 原文与人工备注；固定 Qwen `adapters/model_provider.py:10` | 事实/推断有来源 schema，但同消息事实更新覆盖旧对象、人工 note 单独来源不进入 persist_facts 分组（:19–:24）；诉求修订/工具事实更新不完整（AC-047）；订单/步骤/执行正文可绕 H-01；售后金额/地址等完整写业务记忆留 Phase 9。 |
| 007 | `application/commit_outcome.py:81` 持久接管，`application/human_review.py:84` 人工屏障；下封新消息开新 run；人工结案继续沿用已交付入口 | 无依据不保证被拒 H-01；已识别有效危险未解决却恢复 H-03。人工自由文本不是风险清除授权。 |
| 008 | `agent/budget.py:33` 预留/settle，:78 工具限额；`agent/graph.py:37` 限次网络重试；`adapters/model_provider.py:16` SDK max_retries=0；`application/run_records.py:35` 持久记录 GET | 预算常量6/12/120秒/80k和16k/2k/30秒代码吻合；重试同cycle由既有 JobService。基础wake失效 H-02。独立完整故障测试未执行，不能称可靠性通过。 |
| 009 | `frontend/src/components/mail-agent/AgentProcessPanel.vue:19` 运行/停止/重试、:57 独立历史对照；`AgentRunPanel.vue:45` 理解/工具/引用/结果；`ReferenceDrawer.vue:2` 抽屉；`useAgentRunDetails.ts:26` 客户/请求代次门 | 无 Brief/设计稿，继承 Art/Element Plus 先例；实际明暗和1440×900/1280×720未独立验收。重置/完整删除仍后期。没有把过程塞进 Message 的代码。 |
| 012 | `agent/understanding.py:43` schema、多诉求/对象/条件/同意、:52 原文校验；`agent/graph.py:63` 有限修复 | `message acts` 未单独建字段；工具支持修正决策但初始理解没有修订版本/工具来源，AC-047 部分实现；真实理解质量未验收。 |
| 013 | `worker/agent_runner.py:42` run/trace 关联；`agent/budget.py:52` request 去重usage；`application/run_records.py:57` 本地 usage 与 trace 展示 | 本期只本地观测；Langfuse 服务/正式导出 Phase 11，不将缺少服务记缺陷。`AgentRunPanel.vue:117` 准确显示未接入和未知费用。完整 export 脱敏/服务失败待 Phase 11。 |

## 7. FT 与事务门证据

| FT | 实现/已有测试位置 | 本轮结论 |
|---|---|---|
| 01 | `agent/guard.py:46` slot→branch→conversation→head→run/cycle 的同事务租约/版本门；`tests/test_agent_faults.py:133` Event 阻塞旧模型 | 代码可定位，真实旧输入/接管组合独立实测未执行。 |
| 02 | `application/human_review.py:69`–:87 人工输入屏障；`tests/test_agent_human.py:17` 交换通知/人工回复顺序 | 人工完成后的下一来信本轮复现可达；基础事件 wake 协议 H-02 尚失败。 |
| 04 | `adapters/checkpoint_repository.py:130` put、:140 put_writes 都调用同 guarded 连接；`tests/test_agent_checkpoint.py:182` 共锁、:230 stop-first | 同事务适配代码存在，不是检查后另连接。售后写工具留 Phase 9，本期检查点/终局窗口独立完整验证未执行。 |
| 05 | `application/commit_outcome.py:19` / `worker/agent_runner.py:50` 原 scoped 凭证；`tests/test_agent_outcomes.py:52` post-commit 响应丢失 | 代码存在，未知终局不会直接重新建消息；独立进程故障验证未执行。 |
| 08 | `agent/context.py:47` 当前真实前缀重建，:59 historical manifest unavailable；`tests/test_agent_tools.py:133` 未来快照；`tests/test_agent_outcomes.py:130` 对照/未来哨兵 | 阶段边界匹配；独立真实请求和浏览器响应未执行。 |
| 09 | `agent/guard.py:17` 全暴露依赖检查，:56 head锁；`agent/tool_gateway.py:144` 暴露前登记；`tests/test_agent_knowledge.py:45` 下架未最终引用证据 | 正文依赖登记与提交共锁实现可定位；独立两连接下架竞争未执行。 |
| 10 | `worker/agent_runner.py:71` 两次循环（最多一次重建）；`agent/context.py:67` rebuild_count 门、:82 清旧 active deps；`tests/test_agent_knowledge.py:69` 和 :150 | 重建消息重新建立，沿用 Budget 对象；独立两次 head switch/Embedding 返回期间切换未执行。 |

## 8. UI 一致性、Spec 漂移和验证限制

UI Stage 1 静态检查可定位 Element Plus 按钮/Alert/Collapse/Drawer 及主题类复用，没有设计稿数值可比。新右栏和基准页面的实际渲染、主题/尺寸/引用交互仍未独立验收，不能写 UI 匹配。HIGH 已足够判 Stage 1 失败，按 skill 不进入 Stage 2 的邻居视觉对比。

新增模型工具集合（`agent/tool_schemas.py:58`）、run/reference API（`application/run_records.py:18`）、11张记录表（`adapters/agent_schema.py:77`）对应 DEV-PLAN.md:164–168；没有发现超出 Phase 7 的售后执行工具或通用 SQL/path/shell 入口。wait_business/no_material_update 结果枚举虽已声明（agent_schema.py:43），读取时没有可达终局路径，归为不完整实现而非新增范围。

编译原始输出：**未执行**。本轮因 Stage 1 HIGH 停止，未运行 Code Quality/安全扫描/编译/邻居视觉；未把主 Agent 同时运行的检查结果作为自己的通过证据。独立完成的是上述三组真实 PostgreSQL 业务反例（两次脚本，退出均为0），原始输出保留在各发现节。它们验证真实事务和持久效果，不证明模型语义质量。

本轮不给 Phase 7 验收通过。修复上述 HIGH 后由主 Agent 重新派 fresh reviewer 从 Stage 1 开始，补真实模型连续流程、完整故障窗口和真实 UI 证据，再决定是否进入 Stage 2。
