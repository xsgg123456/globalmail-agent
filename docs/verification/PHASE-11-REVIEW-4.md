# Phase 11 第四轮独立收口审查

日期：2026-10-10。角色：fresh code-reviewer。仅审查及报告，不修改产品代码、源需求文档，不提交。

## 审查规划与完成标准

1. 读取 AGENTS、code-review skill、完整 Product-Spec、主架构第9节、DEV-PLAN Phase11、文档索引、交接、实施规划与验证原文，按当前正式契约确定范围；不依赖前三轮结论判断当前实现。
2. 从 Git status/diff 枚举全部本期后端、前端、迁移、依赖、infra/scripts及真实生产调用链，对五项任务、REQ-013每条、AC-049–052、FT-12逐项建立代码与行为证据。
3. 独立执行有针对性的真实PG/Graph/SDK、只读读回守卫、前端生产渲染与SSE交互检查；核对最终451/91全量日志及283份后端冻结源码，不重复付费模型或23分钟全量。
4. 实际浏览运行台与知识库邻居的明暗主题、初始空记录和跨页返回、真实入口与自托管父树，保留去敏截图。Stage1有HIGH即停止，不进入Stage2。
5. Stage1无未闭合HIGH/MEDIUM后检查结构、类型、安全、测试前提、编译与版本；汇总原始输出和限制，旧FAIL报告不覆盖。
6. 仅清理本审查自己的浏览器与隔离测试夹具；通知主Agent可继续共用环境清理、最终文档和本地提交，不启动Phase12/13。

## 结论与审查范围

**Stage 1：PASS。Stage 2：PASS。当前审查范围内未发现未闭合 HIGH / MEDIUM。** 这是 Phase11 工程收口审查，不是82项产品AC、七类业务语义或Phase13整体验收通过。

已按 `git status --short` / `git diff HEAD` 审查后端 `src/`、五个新增观测测试模块、0011迁移、`pyproject.toml` / `uv.lock`，前端既有运行台、观测组件/API/composables、SSE及三项针对测试，独立Compose/镜像锁和全部观测脚本，并追到实际 `main → AgentRunner → AgentGraph → ToolGateway → commit_outcome` 与正式启停脚本。排除已消化的 `.codex/evolution/signals.jsonl` 队列变更。未修改主Agent的源文档、代码、共用schema或对象。已读取任务指定原文；没有独立新设计稿，本期视觉依据既有Art外壳及知识库页面。

独立源码审计覆盖52个代码相关变更路径，**其中包含 `.env.example`、配置、依赖和锁文件，不能称52份源程序**；路径、SHA、物理行数见 [本轮审计](artifacts/phase11/four-source-audit.json)。283份后端最终全量测试冻结文件当前SHA均相同。公共源程序口径49份、最大276行见 [代码大小](artifacts/phase11/code-size.json)；本轮检查的非锁文件也无超过300行者。依据：`agent/graph.py:24`、`observability/sdk_export.py:59`、`frontend/src/composables/use-agent-console.ts:10`、`scripts/verify-observability.py:136`（前缀均为 `globalmail-agent/` 对应 backend/src/globalmail_agent、frontend、scripts）。

## Stage 1：Spec Compliance

### 五项本期任务

| 任务 / 判定 | 代码位置 | 实际证据 |
|---|---|---|
| ✅ 完整：独立六服务、五卷、loopback、版本与认证 | `globalmail-agent/infra/compose.observability.yaml:1,55,82,95,113,131,148,163`；`scripts/observability-common.ps1:5,16,50`；`scripts/init-observability.ps1:3,7,31`；`scripts/stop-observability.ps1:6` | 独立亲跑 [six health/auth](artifacts/phase11/four-deployment.log)：六服务healthy、镜像与锁相符、项目隔离，仅web绑定127.0.0.1:3001，匿名projects401、认证project及UI login成功。核对 [启停保留](artifacts/phase11/observability-preservation.json) 与真实脚本 `test-observability-preservation.ps1:32–56`：配置SHA、五卷、v2读回trace、业务PG容器/启动时刻不变；本轮未再次停共用服务。 |
| ✅ 完整：实际节点、安全receipt与树 | `backend/src/globalmail_agent/worker/agent_runner.py:74,80,144`；`agent/context.py:37`；`agent/graph.py:71,82,88,208`；`agent/tool_gateway.py:30,146`；`application/commit_outcome.py:47`；`observability/tracing.py:39`；`observability/sdk_export.py:82,124` | [独立31项](artifacts/phase11/four-backend-tests.log)走实际PG/Graph，context、attachment_prepare、understanding、model、retrieval、tool、policy、response、commit、outcome均来自执行路径，HITL终态保持handed_off。真实Qwen的 [远端读回](artifacts/phase11/four-actual-qwen-readback.json) 和本轮实际查看的 [文本树](artifacts/phase11/four-langfuse-text.png)、[图文树](artifacts/phase11/four-langfuse-image-tree.png)证明正式两run进入真实自托管UI。 |
| ✅ 完整：SDK前过滤、来源依赖、正确时间和关联 | `observability/media_filter.py:34,59`；`observability/sdk_export.py:84,96,101,108,124`；`observability/snapshot.py:17,27,35,54`；`observability/records.py:18,31,76,100`；`migrations/versions/0011_observability.py:11,23` | 真实授权图片会进入应用模型输入而不进入SDK/OTLP；UUID/枚举/hash/count白名单拒绝正文、图片URL/base64、原异常和未知字段。模型、上下文、工具、理解、回复对象登记依赖；祖先撤销、知识下架、scope/generation及发送中撤销测试通过。[独立31项](artifacts/phase11/four-backend-tests.log)，[图片实际属性](artifacts/phase11/four-langfuse-image-attributes.png)仅ID/count/状态/time，无媒体正文。 |
| ✅ 完整：有界异步、故障隔离、唯一usage | `observability/exporter.py:10,23,35,88,99,124`；`observability/records.py:116,130`；`observability/transport.py:41`；`observability/snapshot.py:35`；`agent/budget.py:46,87` | 队列只存run ID，大小与flush有界；提交后异步导出。确定未送达/429才有限重试；5xx/超时/断连及崩溃窗口未知ack只读核对完整唯一ID，不盲重发。队列满、raw exception、双exporter CAS、确认丢失与撤销竞态独立通过。实际usage只有既有ledger；[同一时序FT12](artifacts/phase11/four-ft12-near-budget.json)6/6预算边界、一次SDK503、无新模型/重复业务/重复账本。 |
| ✅ 完整：既有运行台真实六状态、加载、失效与交付证据 | `frontend/src/components/agent-runtime/ObservabilityStatus.vue:2,7,19,23`；`frontend/src/composables/use-run-observability.ts:12,26`；`frontend/src/composables/useConversationEvents.ts:26`；`frontend/src/composables/use-agent-console.ts:19,20,71`；`frontend/src/views/agent-runs/index.vue:16,47,51` | [独立5项生产渲染/事件测试](artifacts/phase11/four-frontend-targeted.log)、[真实初始空记录及返回](artifacts/phase11/four-initial-loading-browser.log)，pageerror0；仅exported出现当前run本机入口，degraded/撤销/loading/错误清旧链接。真实入口点入已登录Langfuse。正式升级证据 [备份](artifacts/phase11/formal-backup.json)、[77表70对象保旧](artifacts/phase11/formal-preservation.json)、[重启就绪](artifacts/phase11/formal-final-ready.json)已核对。 |

表内省略前缀的后端路径均位于 `globalmail-agent/backend/src/globalmail_agent/`，前端及脚本路径均位于 `globalmail-agent/`；迁移路径位于 `globalmail-agent/backend/`。

### REQ-013 原文逐条核对

| 原文条目 | 判定与代码证据 | 行为证据 |
|---|---|---|
| `Product-Spec.md:516` 单次触发run/trace、同模式分支会话，理解/模型/检索/工具/规则/业务/回复/HITL | ✅ 完整。`observability/sdk_export.py:89–117`固定同trace，session UUID由workspace/mode/branch/conversation生成；`snapshot.py:17–24`保留run/cycle/输入版本/parent_run；实际节点位置见任务表 | 独立完成的多工具/检索run和HITL；真实文本18 observation/5 generation/4 tool，图文7 observation/2 generation；父UUID低64位与实际parentObservationId逐一相符，见 [读回](artifacts/phase11/four-actual-qwen-readback.json)。 |
| `Product-Spec.md:517` 版本/来源/动作/错误/耗时/provider usage、不重复、费用未知 | ✅ 完整。`snapshot.py:27–51`版本hash、release/profile/contextID、request_hash→唯一usage；`tracing.py:42–59`实际起止；`sdk_export.py:111–118`只投影usage、不设cost | [31项](artifacts/phase11/four-backend-tests.log)真实模型回执与ledger核对；真实7个generation数值与既有ledger相同，费用null；父树恢复前后business hash一致，见 [单次安全恢复](artifacts/phase11/backend-hierarchy-single-restore.json)。 |
| `Product-Spec.md:518` 业务DB持久化，Langfuse不替代账本/队列/审计 | ✅ 完整。`worker/agent_runner.py:80–137`原业务运行/预算/终局优先；`records.py:76`另存安全导出对象；`main.py:40–59`服务生命周期 | 实际503时reply_and_wait仍完成、唯一outbound1、usage6不变，本地终态与degraded均保留，见 [FT12](artifacts/phase11/four-ft12-near-budget.json)。 |
| `Product-Spec.md:519` I/O/metadata/错误控制脱敏，演示身份，展示/模型上下文分开 | ✅ 完整。`media_filter.py:5–65`允许字段白名单；`sdk_export.py:84`先过滤再wrapper/media；`transport.py:36–69`固定响应；本地内容仍受 `observability/model_records.py:11,48` 及RunRecords权限管理 | 邮箱/地址/假key哨兵、媒体字节/可访问URL、HTTPError.__context__、远端body/reason均负向断言；SDK处理入口实际拦截测试通过。真实LF root及attachment input为null/output未设置，见 [文本](artifacts/phase11/four-langfuse-text.png)、[图片receipt](artifacts/phase11/four-langfuse-image-receipt.png)。 |
| `Product-Spec.md:520` 异常不阻塞/回滚合法提交，摘要保留，不重跑，过滤失败不送正文 | ✅ 完整。`records.py:77–98`后事务且隔离失败；`exporter.py:35–97`只读安全缓冲；`worker/agent_runner.py:74–77`观测初始化失败隔离 | 同一时序近预算FT12、队列满、三次确定失败、过滤失败0send，均检查既有outbound/usage未增。见 [31项](artifacts/phase11/four-backend-tests.log)、[FT12原始输出](artifacts/phase11/four-ft12-near-budget.log)。 |
| `Product-Spec.md:521` 推荐独立本地自托管环境 | ✅ 完整。Compose独立名称、全部digest、五卷；`settings.py:20–50`loopback/SecretStr；`scripts/observability-common.ps1:50`仅指定project执行 | 本轮独立真实six health/auth/login，保留原启停测试，未改动正式业务DB/其他项目。见 [部署日志](artifacts/phase11/four-deployment.log)、[保留证明](artifacts/phase11/observability-preservation.json)。 |
| `Product-Spec.md:522` 业务断言/人工核对，评分不唯一；新恢复trace，不跨天挂起 | ✅ 完整。`AgentRunner.execute`一次run close；`snapshot.py:14–24`parent_run；`sdk_export.py:96`受限session；无在线prompt修改/自动评分治理调用 | AC052真实PG新run检查最新人审记录及新来信，oldmodel2次保持不重放；本轮工程判断不依赖模型评分。两次真实Qwen业务失败仍明确FAIL，未宣称语义通过。 |

### AC-049–052 与 FT-12

| 条目 / 判定 | 生产代码与独立验证 |
|---|---|
| ✅ AC-049，工程完整 | `agent/tool_gateway.py:146`真实search_reference触发retrieval，其parent为实际工具receipt；`snapshot.py:35–46`只读既有usage；`sdk_export.py:101–120`恢复真实层级。独立31项内包含真实发布知识→实际Graph多工具→合法reply_and_wait→检索receipt父节点→下架阻止发送；另有完整普通多工具/HITL/实际远端7generation ledger核对。[原始测试](artifacts/phase11/four-backend-tests.log)、[真实读回](artifacts/phase11/four-actual-qwen-readback.json)。 |
| ✅ AC-050，工程完整 | `media_filter.py:34,59`、`sdk_export.py:84`、`transport.py:41`。正常/异常哨兵、真实图片、raw exception/media traversal入口、实际SDK HTTP payload均负向检查。[31项](artifacts/phase11/four-backend-tests.log)、[FT12](artifacts/phase11/four-ft12-near-budget.json)。 |
| ✅ AC-051，工程完整 | `records.py:76`、`exporter.py:35`、`worker/agent_runner.py:144`。真实PG/Graph/官方SDK/本机HTTP503故障时，合法业务提交保留、模型仍6次、ledger前后相同、outbound1，固定本地降级且无URL；真实降级页面 [light](artifacts/phase11/four-runtime-degraded-light.png) / [返回dark](artifacts/phase11/four-return-ready-dark.png)。 |
| ✅ AC-052，工程完整 | `snapshot.py:14–24`、`sdk_export.py:96`与现有人工回复/新来信屏障。独立31项中的 `ReviewAC052.test_human_reply_and_new_input_have_new_trace_and_latest_facts` 真实PG断言：人审中来信和人工回复均不建任务，下一封新来信启动新run/trace；上下文含最新人工正文、note和新来信，parent_run/会话相符，旧模型调用次数不变，敏感新事实不入receipt。[原始测试](artifacts/phase11/four-backend-tests.log)。 |
| ✅ FT-12，同一时序近预算工程完整 | `agent/graph.py:46–79,94–146,208`与 `agent/budget.py:46–77,87–115`。本轮新独立UUID schema使用**明确ScriptedModel**，实际理解第一次格式失败修正、一次供应商失败重试、正常决策/工具/核验共6/6次；每次provider入口已持久化次数及token预留，最后一次尚占25733 tokens、unknown2；第7次reserve被真实Budget守卫拒为budget_exhausted且无新增账本。合法reply_and_wait唯一outbound1后真实SDK POST一次503，降级ack_unknown无URL；导出前后usage6、SHA不变，实际已知input100/output50、未明usage1仍保留11475预留，总reserved11625，未记零也未调用第7次模型。两种哨兵不在实际OTLP wire中。[JSON](artifacts/phase11/four-ft12-near-budget.json)、[原始日志](artifacts/phase11/four-ft12-near-budget.log)。 |

FT-12首个审查探针夹具错误先请求未获准订单工具，随后重复相同get_case_context触发既有no_progress；均由生产守卫正确拒绝。改成上述可达格式修正/供应商重试序列后完成同一故障时序；没有因此修改生产代码或把不可达输入当预期通过。日志中的SDK `400 / observability_http_rejected` 是安全session提供给SDK的固定响应；实际HTTP接收器收到了503，应用将其标为ack_unknown，不能将400日志当作真实远端状态。

### 历史FAIL与修复复审

| 历史问题 | 本轮独立复审 | 保留记录 |
|---|---|---|
| F11-FE-01 HIGH：旧SSE撤销未及时清旧trace链接 | ✅ 关闭。`useConversationEvents.ts:26`先invalidate再判断refreshPending；`use-agent-console.ts:71–74`单独traceRevision；`use-run-observability.ts:26`sync watch立即清record。生产SSE在业务GET挂起/失败、KeepAlive离页晚到下仍清链接，独立5项通过。 | [前端初审FAIL](PHASE-11-FRONTEND-REVIEW.md) |
| F11-OBS-02 MEDIUM：同started_ns时子先完成导致parent丢失 | ✅ 关闭。`sdk_export.py:124–144`父依赖拓扑优先，timestamp只排列已就绪节点；缺父/环/重复UUID/低64碰撞全部阻断。独立实际SDK同开始时间HTTP断言parent、timestamp、usage通过，真实父树逐UUID复核。 | [第一轮FAIL](PHASE-11-REVIEW.md) |
| F11-VERIFY-03 MEDIUM：existing-report只读模式启动恢复导出 | ✅ 关闭。`scripts/verify-observability.py:164–183`start仅在else新模型分支。亲跑守卫实际远端GET2次，exporter.start / export_one / ModelProvider.request / execute全0，七表完整hash均不变且script SHA对应当前文件。 | [第二轮FAIL](PHASE-11-REVIEW-FINAL.md)；[本轮守卫](artifacts/phase11/four-readback-no-side-effects.json) |
| F11-FE-04 MEDIUM：undefined===undefined使executionSteps(null)渲染崩溃 | ✅ 关闭。`use-agent-console.ts:19–20`record先按当前run校验，steps仅在record非null时调用；`frontend/scripts/agent-console-loading.test.ts:10`实际Vue生产renderer/memoryrouter覆盖可达初始loading。独立针对测试通过；真实页面fresh reload→GET延迟→知识库→返回，初始record空仍可渲染、pageerror0，GET恢复后正常降级页。原表达式Git HEAD已存在，不称本期引入。 | [第三轮FAIL](PHASE-11-REVIEW-CLOSED.md)、[旧反例](artifacts/phase11/closure-null-render-before-fix.log)、[本轮浏览器](artifacts/phase11/four-initial-loading-browser.log) |

### 完整 / 部分 / 未实现与Spec漂移

- **本期完整实现**：上述五项任务、REQ-013七条、AC-049–052工程契约、FT-12工程故障契约。依据已逐行列出，无以“其余正常”替代未检查项。
- **本期部分实现 / 未实现 / 无效引导**：未发现。六状态为真实API记录的投影，失败不出现成功链接；按钮“刷新追踪状态”实际发GET，入口指向本机已认证LF。依据 `ObservabilityStatus.vue:3–10` / `observability-api.ts:36–41`，本轮真实浏览器点击与5项生产交互测试。
- **保留后续范围**：完整本地/远端删除、联合备份恢复属于Phase12；业务模型质量、七类业务及82AC总验收属于Phase13。`records.py:146`明确仅为停止写入/撤销入口，未伪称完整远端清除；0011保旧升级不等于联合恢复验收。
- **未发现本期scope creep**：新增仅安全缓冲列/FK、只读观测API、实际运行台状态组件、独立Compose与脚本；`agent/tool_menu.py:2,5,17`商业写工具仍封锁，持续人工与人工发送未开放解除/自动交易/业务事件主动发信。没有新增场景实验室、测试UI或在线Prompt治理页面。依据 `api/observability.py:10–21`、`main.py:94`、`views/agent-runs/index.vue:47` 与Git diff/实际四个导航入口。

## Stage 2：Code Quality

Stage1无未闭合HIGH/MEDIUM后执行。本节结论均为本期范围。

| 维度 | 判定、位置与证据 |
|---|---|
| ✅ 结构/类型/大小 | tracing、snapshot、records、exporter、transport、SDK、media_filter各有明确职责；`sdk_export.py:59`199行，`records.py:13`148行，`graph.py:24`276行；新增API有RunObservability typed interface，composables使用Ref/unknown并运行时核验；本期前端无any。全路径SHA及大小见 [独立审计](artifacts/phase11/four-source-audit.json)；vue-tsc成功。 |
| ✅ 错误处理与恢复 | `records.py:116`发送前持久CAS，避免进程断开后盲发；`transport.py:41`隔离原HTTP对象，禁redirect与SDK隐藏重试；`sdk_export.py:163`有界v2读回；`exporter.py:99,124`恢复量/queue/flush有界。真实SDK HTTP、双并发、发送中撤销、response lost、重复/不完整远端receipt独立通过，见 [31项](artifacts/phase11/four-backend-tests.log)。 |
| ✅ 密钥/危险语法/注入检查 | `settings.py:20–50`SecretStr/repr=False及loopback；`scripts/start-local.ps1:43–51`启动Vite前清服务端敏感环境，测试server同样隔离。独立审计在本期路径未发现eval、innerHTML赋值、危险HTML、VITE Key/Secret/Token、硬编码真实provider key、用户绝对路径或TS any。SQL使用SQLAlchemy绑定；审读迁移/配置schema选择与对象路径处理，未见本期字符串输入拼SQL/任意命令执行。负向测试还实际证明第三方propagated metadata不混入、异常.__context__/远端body不进入SDK；证据 [审计](artifacts/phase11/four-source-audit.json) / `test_observability_sdk.py:113,139,178,208`。 |
| ✅ 测试真实性 | 使用真实临时PG schema、对象存储、Graph、生产renderer/SSE/composables及官方SDK/OTLP。FakeTransport只用于应用队列确定性状态断言；SDK网络路径有实际HTTP/protobuf/503，FT12明确ScriptedModel且包含实际预算预留。无用mock GET声称真实SDK断网；无用构造model response声称模型语义通过。依据 `test_observability.py:56,99,138`、`test_observability_sdk.py:70,160,192`、`test_observability_recovery.py:27,54,82`、`frontend/scripts/observability-events.test.ts:16`、本轮FT12 JSON。 |
| ✅ 迁移与正式保旧 | `0011_observability.py:11–24`只增列和复合作用域FK，旧trace/usage未重写；迁移两项实际PG测试通过。核对真实pg_dump465744 bytes、pg_restore --list成功、77张旧表原字段/行hash全部保持，70 objects、settings不变，authorized_transition_columns={}，私有ACL仅current/SYSTEM/Admin；正式重启API及15173代理200。见 [正式备份](artifacts/phase11/formal-backup.json) / [保旧](artifacts/phase11/formal-preservation.json) / [重启](artifacts/phase11/formal-final-start.log)。未重跑或中断正式服务。 |
| ✅ 视觉与邻居实际比较 | 实际查看1440×900亮色运行台/知识库、1280暗色和1280×720两页。继承Art左导航/顶栏、ElButton/ElTag、theme主色、文本层级/边框/卡片；追踪状态在既有概览下，段落与按钮间距一致，degraded有文字和warning，成功有明确外链。`views/agent-runs/index.vue:4,17,47,72–81`与邻居 `views/knowledge/index.vue:6–23`；不以CSS复用数量代替渲染证据。1440和1280的document.scrollWidth等于innerWidth；1280×720返回邮件y148、trace入口y516均在视口内，见 [量测日志](artifacts/phase11/four-720-browser.log)。 |

本轮已实际查看的渲染证据：

- 1440亮色：[成功入口](artifacts/phase11/four-runtime-exported-light.png)、[实际SDK故障降级](artifacts/phase11/four-runtime-degraded-light.png)、[知识邻居](artifacts/phase11/four-knowledge-light.png)。
- 暗色：[运行台](artifacts/phase11/four-runtime-exported-dark.png)、[知识邻居](artifacts/phase11/four-knowledge-dark.png)、[1280×720运行台](artifacts/phase11/four-runtime-dark-1280x720.png)、[同尺寸邻居](artifacts/phase11/four-knowledge-dark-1280x720.png)。
- 空记录/返回：[初始null record](artifacts/phase11/four-initial-null-record-dark.png)、[真实GET完成后的跨页返回](artifacts/phase11/four-return-ready-dark.png)、[pageerror与请求延迟量测](artifacts/phase11/four-initial-loading-browser.log)。初始截面已有1个真实GET等待，空数据渲染；返回后3个延迟GET全部完成、pageerror仍0。
- 真实Langfuse：[文本父树](artifacts/phase11/four-langfuse-text.png)、[图文父树](artifacts/phase11/four-langfuse-image-tree.png)、[图片receipt无I/O](artifacts/phase11/four-langfuse-image-receipt.png)、[图片count/父UUID/时间](artifacts/phase11/four-langfuse-image-attributes.png)。

## 测试与编译原始输出

最终全量日志由主Agent执行，本轮完整读取尾部与对应源码SHA；独立针对验证另外执行，互不冒充。

后端最终全量 [原始日志](artifacts/phase11/backend-full-tests.log)，对应 [冻结283文件](artifacts/phase11/backend-source-freeze.json) 与本轮再次逐SHA核对的 [独立审计](artifacts/phase11/four-source-audit.json)：

```text
Ran 451 tests in 1388.164s
OK
SUMMARY 451 failures 0 errors 0 skipped 0
FROZEN_SOURCE_CHANGED False
```

本轮独立真实PG/SDK及AC052/检索，[原始日志](artifacts/phase11/four-backend-tests.log) / [汇总](artifacts/phase11/four-backend-summary.json)：

```text
Ran 31 tests in 91.253s
OK
FOUR_REVIEW_SUMMARY {"tests":31,"failures":0,"errors":0,"skipped":0,"frozen_files":283,"mismatches_after":[]}
```

本轮生产前端renderer/SSE针对 [原始日志](artifacts/phase11/four-frontend-targeted.log)：

```text
tests 5
pass 5
fail 0
cancelled 0
skipped 0
duration_ms 2330.7813
```

最终前端全部 [原始日志](artifacts/phase11/frontend-tests.log)：

```text
tests 91
pass 91
fail 0
cancelled 0
skipped 0
duration_ms 15590.3801
```

最终前端编译 [完整输出](artifacts/phase11/frontend-build.log)，vue-tsc与Vite同一 `&&` 命令退出0；原90项/36.93s修前日志只作历史保留：

```text
$ vue-tsc --noEmit && vite build
vite v7.1.7 building for production...
✓ 3356 modules transformed.
✓ built in 29.02s
```

本轮独立后端编译/依赖检查分别退出0：`.venv/Scripts/python.exe -m compileall -q src migrations ../scripts`、`uv lock --check`、`uv pip check`，见 [编译](artifacts/phase11/four-compile.log)、[锁检查](artifacts/phase11/four-lock-check.log)、[依赖](artifacts/phase11/four-dependency-check.log)：

```text
compileall_exit=0
Resolved 72 packages in 14ms
Checked 70 packages in 7ms
All installed packages are compatible
```

本轮只读辅助守卫退出0：[实际GET2、所有禁止调用0、七表完整SHA不变](artifacts/phase11/four-readback-no-side-effects.json)。真实模型只读读回没有启动新模型或发送span。

## 版本、真实模型结论与审查边界

服务Web/Worker固定Langfuse4.56.0，官方Python SDK4.17.0；PG17.11、ClickHouse25.12.11.4、Redis7.4.11、Chainguard MinIO RELEASE.2026-09-22T19-25-18Z全部真实digest冻结（`observability-images.lock.json:1`、`backend/pyproject.toml:21`）。核对官方 [v4.56.0 Compose](https://github.com/langfuse/langfuse/blob/v4.56.0/docker-compose.yml)、[不可变v4数据说明](https://langfuse.com/faq/all/tracing-data-updates)、[Public API](https://langfuse.com/docs/api-and-data-platform/features/public-api)：同ID重发会产生重复观测，必须避免把未知ack当作可盲重发；当前持久CAS及完整唯一ID读回与该行为匹配。推断范围仅为应用这一发送链路，未声称第三方可提供业务幂等。

真实Qwen文本run `e214058a-eefb-4346-a35b-b8ce3f43a33b`，trace `308337ae660e413dbecb46b95f82b5b8`：18 observation/5 generation/4工具，input16798/output1253，**业务FAIL：reply_citation_invalid**。图文run `6a25f963-639c-4176-8ffc-eefa83af6e3a`，trace `a42744ffe3b246198446289a67509cca`：7 observation/2 generation，每次1个实际image view，input6850/output1862，**业务FAIL：understanding_schema_invalid**。本轮只读真实远端、查看GUI，不再付费调用。追踪导出及privacy/usage/父树PASS不改变这两项业务FAIL；原正文/模型原始内容留在私有归档，未放入报告。

前三轮整体FAIL和独立前端HIGH报告均保持原结论。最终文档状态回写、共用测试环境清理及用户已授权的本地Git提交由主Agent继续；本报告不授权Phase12/13，不push，不把后续工作写成已完成。

本审查自己的 `phase11-four-review` 浏览器已关闭，最后独立FT12 schema查询不存在，其他独立测试使用UUID schema的既有addCleanup；共用环境和正式服务未动，gui-state已不再使用。[清理证明](artifacts/phase11/four-cleanup.json)、[浏览器关闭原始输出](artifacts/phase11/four-browser-cleanup.log)。
