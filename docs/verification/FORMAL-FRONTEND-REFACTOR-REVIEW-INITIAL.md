# 正式前端改造独立初审

日期：2026-10-09。范围：Phase 16 正式邮件/独立运行台及其 Phase 14–15 接口契约。依据：Product-Spec v1.18、AGENT-ARCHITECTURE 顶部正式授权、DEV-PLAN、WORKBENCH-REFACTOR-IMPLEMENTATION、15175 已批准交互验证。审查者只读源码、运行探针和工程检查；只新增本报告，没有修改源码、暂存、提交或启动子 Agent。

**Stage 1：FAIL。发现 2 项 HIGH、2 项 MEDIUM。Stage 2 未执行。**

源码在审查期间由主 Agent 修改。本报告保存首次读取实现与反例原始输出；后续修复声明不改写本次 FAIL。报告内初读行号属于发现时版本，不能当成后来版本已复核的证明。末段补记第一次修复仍漏掉的可达输入；最终关闭必须由 fresh 实例从 Stage 1 重新审查。

路径约定：表内省略完整前缀的前端路径均位于 `globalmail-agent/frontend/src/`，后端 `application/`、`adapters/`、`observability/` 路径均位于 `globalmail-agent/backend/src/globalmail_agent/`；文中 `backend/src/` 同样相对项目代码目录 `globalmail-agent/`。

## 审查步骤与边界

1. 阅读源需求及规划，明确正式界面与预览、真实业务质量与工程替身的边界。
2. 逐项核对邮件/建议/运行台/路由/事件/草稿与后端资源映射，跟踪异步和新轮次的可达路径。
3. 用生产 composable 和受控 API 替身执行反例；定向运行前端测试和类型编译。
4. 保存问题、对应需求、原始输出和未测范围。Stage 1 存在 HIGH，按 code-review skill 停止，不进行 Stage 2 质量、安全、测试真实性或邻居视觉终审。

正式后端联调地址 18184、前端 15176 是主 Agent 提供的隔离环境。本审查未操作 GUI、未调用付费模型、未连接正式数据库或修改测试数据。15175 的旧截图和 82 项预览测试不能证明 15176 正式页面已经通过。

## Stage 1 发现

### F-01 / HIGH：新 review 把保留的个人草稿自动标记为已核对新来信

需求原文：正式规划第 35 行，“采用只复制到客服输入框，确认期间二次校验run/输入/时效”；Product-Spec 第 408 行，“过时建议/草稿不能作为已核对当前来信的结果”。

初读实现：`globalmail-agent/frontend/src/composables/create-mail-workbench.ts:90–97` 在 review ID 变化时保留非空个人回复/备注，却无条件将 `humanRevisions[id]` 设为新 review 的 `input_revision`。`humanStale` 第 36–40 行因此变为 false；第 216 行提交的是新的核对版本。`components/mail-agent/StaffReply.vue:7` 允许等待客户时编辑个人回复，第 15 行只在 `stale` 时禁止发送。

实际路径：持续人工完成回复后旧 review 变为 completed（`backend/src/globalmail_agent/application/human_review.py:105–107`）；GET 只投影 open review，没有时返回 null（`application/conversation_queries.py:74–86`）；下一封来信由 `conversation_base.py:83–85` 创建新 review。第一次打开等待客户会话时，客服可以先写个人回复，再收到新来信。不是不可达的测试前提。

生产 composable 反例：初始 review=null、persistent_human=true、human_wait_customer，个人输入 `older-staff-draft`；新来信后 conversation.input_revision=3、row_version=4、review ID=`h-new`、review.input_revision=3；没有调用 acknowledgeHuman，就刷新并完成人工回复。

原始输出（exit 0）：

```text
{"humanStale":false,"reply":"older-staff-draft","currentInputRevision":3}
{"submitted":[{"path":"/conversations/c-1/human-replies","payload":{"body":"older-staff-draft","note":"","risk_decision":"keep_active","expected_input_revision":3,"expected_version":4}}]}
```

差异：旧文本被保留，却被默认认定已核对最新来信；UI 和后端的版本检查均不会要求客服重新核对。

修复方向：个人输入必须绑定编辑/核对当时的输入版本。新 review 的出现不能代替客服核对；首次进入 review=null 的会话也要保留这个绑定。只有显式核对/采用当前建议才推进版本。

**审查中第一次修复复查仍失败**：主 Agent 将赋值改为“版本未初始化或个人文本均为空时更新”，即读取时第 95–96 行。但上述首次打开等待客户会话路径中 `humanRevisions[id]` 恰好 undefined，非空旧文本仍被升级。再次运行同一输入，原始输出为：

```text
{"humanStale":false,"reply":"older-staff-draft","currentInputRevision":3}
```

已将此遗漏及永久回归输入发回主 Agent。此处仍为 FAIL；后续修复由独立复审关闭。

### F-02 / HIGH：采用草稿的网络复查期间会无确认覆盖客服新输入

需求原文：正式规划第 31 行，“辅助不覆盖个人草稿”；第 35 行，“采用只复制到客服输入框，确认期间二次校验”；Product-Spec 第 442 行及派发材料要求跨页保留个人草稿、覆写需确认，AI 异步不能覆写个人输入。

初读实现：`globalmail-agent/frontend/src/composables/use-conversation-advice.ts:29–37` 只在采用开始时检查个人回复并决定是否确认。第 34 行异步读取建议与会话，之后只检查服务端 run/input/stale，第 37 行直接 setHuman。`StaffReply.vue:7` 只受 busy/resolved 控制，而 adopt 不设置 busy，因此网络等待期间客服仍可编辑。

生产 composable 反例：初始个人回复为空，当前有效建议草稿=`agent-draft`。把 `agentRunApi.advice` 的复查响应延后；调用 adopt 后、响应到达前，客服输入 `staff-text-entered-during-network`；随后返回相同有效 run/input 的建议。

原始输出（exit 0）：

```text
{"before":"staff-text-entered-during-network"}
{"after":"agent-draft","adviceError":""}
```

差异：服务端版本未变不能证明本地个人文本未变；新个人输入丢失，未触发覆盖确认。已有草稿确认后、网络等待期间继续编辑，也存在同类窗口。

修复方向：采用开始记录本地个人文本/编辑版本，所有 await 后重新校验；有变更就拒绝本次采用或针对最新文本重新确认。保留会话/run/input/错误状态的服务复查。主 Agent 在审查中开始修复，此报告不将修复声明记为关闭。

### F-03 / MEDIUM：默认进入最新轮未固定选择，新 run 会替换当前阅读节点

需求原文：Product-Spec 第 442 行，“历史新轮仅提示不抢位置”；正式规划第 13 行，“深链接和历史新轮提示”。

初读实现：`globalmail-agent/frontend/src/composables/use-agent-console.ts:14–18` 用 route.query.run_id 选 run，缺失时始终取 `detail.runs.at(-1)`；第 43–49 行进入页面未写入实际 run_id。通过侧栏或邮件“全部轮次”进入，只带会话 ID 时当前 run 是动态 latest。SSE 在第 53–55 行更新 runs 后，computed 会转到新增 run；原 step 不属于新 run 时回退首节点，不会出现“保留历史轮次”的提示。

差异：用户已经开始阅读默认轮，其阅读选择仍未固定。新来信/重试造成的新记录会切走阅读位置。

主 Agent 已在审查中加入默认 run_id 固定及会话阅读记忆；这需要 fresh 复审和真实 GUI 证明，不改写初读问题。特别要覆盖“历史轮/节点 → 触发来信 → 侧栏返回运行台”和 KeepAlive 重新激活，不能只验证显式 URL 下的新 run。

### F-04 / MEDIUM：未读取的运行指标显示成实际零，部分未知用量没有完整标注

需求原文：正式规划第 13 行，“真实加载/空/错误态，无预置run/指标”；Product-Spec 第 423 行要求实际用量，第 541 行明确“未知用量不记零”。

证据：`globalmail-agent/frontend/src/views/agent-runs/index.vue:41–42` 在 run 已有但 record=null 时显示 `0 次模型 / 0 次工具`；第 68 行用空数组或 nullable token 值累加成 0。`use-agent-console.ts:16、23–29` 在记录请求尚未返回、切换 run 或错误时 record 可为 null；页面概览仍显示。未知提示第 42 行只检查 input_tokens===null，`api/agent-run-contract.ts:122–123` 的 output_tokens 同样允许 null。

差异：尚未取得实际回执被表示成确定的零；例如 input_tokens=10、output_tokens=null 会显示“10 Tokens”且不提示未知。

修复方向：记录未取得时显示读取中/读取失败/不可用；完整回执中的真实 0 才显示 0；任一侧 token 未知时明确“已知用量”和“含未知”。本项为源码和契约可确定的表达式差异，尚未由本审查者做正式 GUI 截图验证。

## Phase 16 逐项对照

以下“结构匹配”只表示对应生产实现存在并可定位，不代表未执行的 GUI、后端集成或模型语义验收通过。

| 本轮需求 | 对照结果与证据 |
|---|---|
| Art 外壳、批准邮件布局、运行概览/时间线/详情 | 结构匹配：`views/mail-agent/index.vue:3–24`、`views/agent-runs/index.vue:17–52`，Agent/runtime 子组件使用主题变量；真实视觉一致性未测，不判 PASS。 |
| 邮件只有正常往来/人工通信，内部建议抽屉 | 结构匹配：邮件第 19–25 行只挂 MessageTimeline、StaffReply、AgentAdviceDrawer；`MessageTimeline.vue:64–68` 文字区分客户/历史客服/模拟人工/模拟 Agent；不把请求或 tool JSON 塞入消息气泡。 |
| 接管、个人草稿、人工发送、明确结案 | 结构匹配：邮件第 8、20、77 行；StaffReply 第 7–15 行；create-mail-workbench 第 201–252 行。旧草稿核对屏障存在 F-01。结案确认期间跨会话导航尚未 GUI 复测。 |
| 采用仅复制，覆盖确认及二次版本校验 | 部分实现：use-conversation-advice 第 25–38 行有确认和服务复查；F-02 证明缺本地编辑复查。 |
| 新来信/人工回复/结案/事实变化使旧建议不可直接采用 | 静态匹配：`application/conversation_advice.py:24–37` 从持久 artifact 判 run/input/lifecycle；use-conversation-advice 第 10–13 行再判最新 run/input/open。完整事实更新/SSE/API 联调由主 Agent 执行，本审查未独立跑 PG。 |
| 个人草稿跨页、跨会话不串、不被 AI 覆写 | 部分实现：`useMailWorkbench.ts:4–8` 共享 work，create-mail-workbench 第 25–35、74–97、293–295 行按会话 ID 存输入；既有定向测试覆盖跨会话。F-01/F-02 阻塞完整通过。 |
| Agent 会话 → 客户轮次 → 重试尝试 → 实际节点 | 结构匹配：`views/agent-runs/index.vue:6–38`；`run-presentation.ts:19–55` 只从 model_calls/tools/artifacts 生成节点，cycle 分组并保留 attempts。默认轮选择有 F-03。 |
| 真实完整 system/user/tool、Schema、参数、返回 | 静态匹配：`RequestView.vue:8–38、54–67` 原文及完整原始请求；`NodeDetail.vue:25、50–70` 输入输出；`observability/model_records.py:11–19、48–61` 读取持久请求/返回；`adapters/model_provider.py:40–46` 保存实际 content/calls/reasoning。没有独立供应商业务质量验证。 |
| 供应商实际 reasoning，未返回/历史未采集明确空态 | 静态匹配：`run-presentation.ts:25–29`、`presentation.ts:108–113`、NodeDetail 第 26–47 行。没有生成隐藏 CoT 的代码；历史请求缺失明确占位，未反填当前文本。 |
| 不造计数或成功节点 | 节点来源结构匹配：run-presentation 第 20–50 行只映射实际资源，失败/空步骤页面第 53 行明确不补造。概览计数不匹配：F-04。 |
| 历史选择不被新 run 抢走、跨页阅读保留、触发来信定位 | 显式 run_id/step_id 结构匹配：use-agent-console 初读第 14–18、34–42 行；邮件第 50、53–59 行。默认入口不匹配 F-03；跨页/KeepAlive 真实 GUI 未测。 |
| 四类首轮/后续内部辅助、持续客服主导；普通有据回复保留 | 前端契约结构匹配：`api/mail-agent-contract.ts:45–48、79–80`、邮件第 51 行、运行页第 23、32 行。后端辅助模式与人工生命周期有 `human_assistance.py:16–45`、`conversation_base.py:64–91`、`advice_commit.py:10–25`。本审查仅跟踪接口可达性，不声称四类真实模型全流程验收。 |
| Mock/source_kind、时间、事实/建议/缺口区分 | 结构匹配：`AgentAdviceDrawer.vue:7–16、30`、`BusinessObservation.vue:3–8`，显示 simulation/source_kind/observed_at；原回执可展开，内部工具分开。实际有源回执由主 Agent GUI 核对。 |
| 正式不依赖 preview fixture，不做业务中心/实验室/测试 UI | 结构匹配：`router/modules/mail-agent.ts:8–32` 仅邮件/运行/知识/系统；`router/modules/index.ts:3–5` 按模式隔离；本轮 views/composables 无 preview import。正式 dist 隔离需要末次生产 build 扫描，本审查未运行 Vite 构建。 |
| 清理旧缓存入口 | 定向测试通过；`router/local-tabs.ts:1–5`、`router/guards/beforeEach.ts:19–23` 过滤页签及搜索历史。 |
| 真 loading/empty/error，无读取副作用 | 部分实现：mail/agent 页面有 skeleton/empty/error，create-mail-workbench 第 49–104 行 GET 与 generation guard；use-agent-console 初读第 19–29 行同类 guard；useConversationEvents 第 42–49 行停用旧订阅。F-04 的指标错误仍存在。GET 不调度的后端入口见 RunRecords 第 33–88 行与 ConversationAdvice 第 15–37 行。 |
| 结案不能隐式重开，后续来信只登记 | 静态接口匹配：邮件第 8、51、77 行、StaffReply 第 4、7、15 行；后端 conversation_base 第 67–88 行保留 resolved 且不 enqueue，human_review 第 71–75 行拒绝非 open。具体事件联调未独立跑。 |

## 全部 REQ 的本轮审查归属

没有将未执行的旧功能/未来 Phase 略写成“其余正常”。本轮按正式规划覆盖前端增量；以下明确每个 REQ 的范围。

| REQ | 本轮检查/边界 |
|---|---|
| 001 客户归组与导入 | 只检查会话 ID 选择/输入隔离：create-mail-workbench 第 25–35、64–113 行及定向 tests；导入去重、sender_key 归组不在 Phase 16 UI 增量回归范围。 |
| 002 历史回放 | 检查可见邮件标签/独立运行结果：MessageTimeline 第 64–68 行、运行页第 53 行。逐封推进由脚本/API，历史数据/时间栅栏未重新全量验收。 |
| 003 自动模拟回复 | 时间线有模拟 Agent 标签且读取不新增邮件；MessageTimeline 第 64–68 行、create-mail-workbench 第 49–104 行。普通场景真实模型回复质量未测。 |
| 004 只读订单查询 | 建议抽屉显示工具来源/时间/未知字段，BusinessObservation 第 3–8 行及 observation-fields 第 15–23 行；客户归属和查单质量属于后端审查。 |
| 005 知识/RAG/维护 | 四入口保留知识，router/modules/mail-agent 第 21–25 行；知识管线既有页面及全量发布/撤销行为不属本轮新增实现审查，不借本报告重判通过。 |
| 006 Agent 决策/记忆 | 只审真实请求/返回展示与内部建议分离；RequestView、run-presentation、AgentAdviceDrawer 上述行号。模型决策和七类质量延期。 |
| 007 人工协作/结案 | 本轮重点，见 F-01/F-02 及逐项表；因此不能通过。 |
| 008 运行可靠性/记录 | 轮/尝试/停止/重试入口、请求/失败记录结构检查，运行页第 28–53、69 行；新 run 保留及用量有 F-03/F-04。租约/晚到写栅栏由后端审查。 |
| 009 邮件/运行台 | 本轮完整增量逐项表已覆盖，Stage 1 FAIL。 |
| 010 数据清理/评测 | 无测试 UI 结构检查；完整删除、恢复、隐私链仍 Phase 12，不在此次 Phase 16 中声明完成。 |
| 011 四类只读/持续人工 | 前端权限/建议/来源及新 review 路径检查，见逐项表；后端权限由另一审查范围，工程替身不等于真实业务质量。 |
| 012 意图/实体理解 | AgentAdvice 类型区分 facts/intents，agent-run-contract 第 5–49、125–135 行；理解内容可查看原始模型记录，意图语义质量未测。 |
| 013 Langfuse/观测 | 本轮只审逐次本地模型请求/返回资源；自托管 Langfuse、导出、降级仍 Phase 11，未执行 Stage 2 安全扫描，也不关闭此 REQ。 |
| 014 图片 | 正式邮件保留缩略图/状态/证据抽屉：MessageTimeline 第 31–43 行、邮件第 26 行；输入用脚本/API，未恢复测试来信 UI。视觉模型质量、彻底删除/备份恢复仍未验收。 |

## 测试与编译原始结果

工作目录：`globalmail-agent/frontend`。由于源码并发修改，下列通过只针对当次读取版本，不能代替修复后的冻结复审。

定向命令：

```text
pnpm exec tsx --test scripts/mail-workbench.test.ts scripts/runtime-contract.test.ts scripts/local-tabs.test.ts scripts/conversation-events.test.ts scripts/agent-run.test.ts
```

原始输出（exit 0）：

```text
✔ 默认只读取最新run，展开旧run才读取；空列表不发请求 (7.3034ms)
✔ 会话切换立即清理旧run，旧会话晚到响应不能覆盖 (0.8291ms)
✔ SSE刷新相同row_version仍读取展开记录，旧请求和更早同run响应均不覆盖 (0.9342ms)
✔ run读取失败有错误且不保留旧结果，显式读取重试可恢复；卸载丢弃晚到响应 (1.0006ms)
✔ 引用只带run和引用ID读取；切换/关闭忽略旧引用，停用真实状态不伪造有效 (0.913ms)
✔ 引用鉴权/网络失败清空正文并显示重试，重试成功后恢复 (0.8118ms)
✔ 预算耗尽不可重试；失败仅当前输入、人工处理权/生命周期/门禁允许才可重试 (0.251ms)
✔ 费用null保持未知，真实0与未知分开；历史对照结果文案不声明模拟已发送 (0.15ms)
✔ 事件只接受本会话作用域并按序去重 (0.9041ms)
✔ 连接带after_seq；断线保持同连接让原生EventSource补读；切会话取消旧连接与晚到事件 (0.9357ms)
✔ 跨作用域或畸形事件关闭流，给出明确刷新恢复路径 (0.2275ms)
✔ 清理已持久化的模板页签，保留业务页签和其参数 (1.4177ms)
✔ 预览启动清理已删除的业务/实验室页签与搜索历史，保留有效会话参数 (0.2366ms)
✔ 选择/刷新只GET，不生成任务；输入按会话保存；服务错误有真实状态 (2.3637ms)
✔ 人工提交409保留文本并刷新；新来信不能静默重绑定草稿，明确核对后才使用新输入版本 (1.2652ms)
✔ 网络结果未知后即使快照更新，重试仍是同key和同payload；成功才清空来信 (0.7928ms)
✔ 快速切换会话时忽略前一会话晚到快照 (0.3256ms)
✔ 列表分页和模式/状态过滤传给服务端，过滤变化重置页码 (0.6771ms)
✔ 人审草稿PATCH使用review版本，完成人工回复另带会话和输入版本 (0.3238ms)
✔ Agent人审晚于首次打开会话时建议不自动放入回复框，已有用户输入保留 (0.4981ms)
✔ 普通人工回复显式保持风险；自由文字不授权清除风险 (0.2944ms)
✔ 风险更正没有依据不提交；有依据提交明确决定及版本，失败保留输入 (0.4832ms)
✔ 切会话、新接管、新输入或新风险都重置风险决定，保留人工文本 (0.5258ms)
✔ 接受实际HTTP200存活与503依赖故障 (0.9422ms)
✔ 拒绝假成功、失配状态及非法配置 (0.2893ms)
✔ 运行配置仅接受当前阶段实际能力标志 (0.5072ms)
ℹ tests 26
ℹ suites 0
ℹ pass 26
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 563.1992
```

类型编译命令与原始输出：

```text
pnpm exec vue-tsc --noEmit
标准输出：空
退出码：0
```

主 Agent 已提供的 `tmp/refactor-front-tests-3.log` 原始尾部是 82 tests / 82 pass / 0 fail / 0 skip / 5424.7974ms；这是既有主 Agent 结果，本审查未把它写成自己的全量独立运行。`tmp/refactor-typecheck-2.log` 为空；本审查独立执行了以上类型编译。末次生产 Vite build 尚未在本审查执行，不声明 build PASS。

## 未测范围与后续审查要求

- 主 Agent 负责真实 GUI：15176 与 15175/Art 邻居视觉对照、明暗/响应式、实际草稿采用/取消/确认/等待期间新来信/个人继续编辑、历史轮和节点跨页/KeepAlive、trigger 来信定位、来源标识、真实加载/空/错误态。本审查未操作同一 tab，也未使用旧截图冒充正式截图。
- 结案确认期间浏览器后退到另一客户再确认：初读邮件第 77 行在 await 确认后调用当前 shared work.close，没有捕获目标 ID；已发精准探针给主 Agent。尚未 GUI 复现，不计入上述缺陷数量。
- 本报告没有重验 Langfuse、完整删除/恢复、全部 82 AC、七类真实模型语义、Phase 11–13，工程替身/Schema通过不折算模型质量。
- Stage 2 未执行：不作命名/类型/300 行/单一职责/安全扫描/测试真实性/邻居实际视觉的通过结论。主 Agent 修复 Stage 1 后，应派 fresh code-reviewer 从 Stage 1 开始；需要补充新 review 首次进入、采用网络等待期间本地编辑、默认轮固定和跨页历史阅读、未知指标永久回归。

报告落盘阶段，主 Agent 汇报已补首次无 review 编辑版本绑定、采用前后个人文本检查/错误拒绝、run/node 阅读记忆、结案确认目标/版本检查、未知指标展示，并运行 86/86 测试。这是后续修复声明，未由本初审实例作为冻结版本完整复核，因此本报告继续保持 Stage 1 FAIL、Stage 2 未执行。
