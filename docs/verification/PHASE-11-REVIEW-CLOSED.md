# Phase11 fresh 收口审查：Stage 2 FAIL

日期：2026-10-10。独立 code-reviewer，按 `.agents/skills/code-review/SKILL.md` 执行；只审查、运行隔离验证和保存证据，未修复、提交或派发子 Agent。

**结论：Stage 1 本期观测功能及安全契约通过，无 HIGH；Stage 2 FAIL，新增一项 MEDIUM F11-FE-04：运行台可达初始加载状态将 null 传入 executionSteps，产生真实 Vue 渲染异常。** 名称 CLOSED 不表示通过。F11-VERIFY-03 的只读脚本修复已独立验证闭合，旧链接撤销、父树、重复发送及原异常链问题亦经本轮验证闭合；原 FAIL 报告不改写。后端最终451项已完整通过且283文件 SHA 与冻结清单一致，不能据此忽略本轮前端反例。

本报告发现时 `use-agent-console.ts:20` 为缺少非空保护的原表达式；主Agent随后已单点修复并重跑前端验证，新的fresh审查另行进行，本报告保留发现时FAIL，不为未独审的后续修复出PASS。真实 Qwen 的 `reply_citation_invalid`、`understanding_schema_invalid` 继续为业务失败。完整删除/联合恢复属于 Phase12，模型质量、七类业务与82项产品AC属于后续总验收，未在本报告中改判。

## 范围与规划

已读取 AGENTS、code-review skill、当前 Product-Spec 的 Phase11需求及权限/UI/失败契约、主架构第9节、DEV-PLAN Phase11、文档索引、当前交接、Phase11实施规划和验收记录。范围为 git status/diff 中全部本期后端源码/迁移/依赖、前端独立运行台、基础设施、启动及验证脚本，并检查实际生产调用链；`.codex/evolution/signals.jsonl` 排除。未发现 Design-Brief，本期按既有 Art 页面先例比较。

执行步骤及完成标准：

1. 对照 REQ-013 七条要求、AC-049–052、FT-12和五项交付，逐项找生产调用点与可复核行为证据。
2. Stage1 无 HIGH 后审 SDK前白名单、唯一usage、异步导出协议/恢复、撤销/作用域、类型/结构与真实测试前提。
3. 使用本人独立浏览器实际查看运行台、Langfuse和邻居知识页；检查明暗宽窄、故障显示与真实入口。
4. 核对完整451原始SUMMARY及283冻结文件当前SHA，保存本轮结论；任何未闭合 MEDIUM/HIGH 均不给整体PASS。

下文 `backend/`、`frontend/`、`scripts/`、`infra/` 相对于 `globalmail-agent/`；证据位于 `docs/verification/artifacts/phase11/`。本轮程序文件 SHA 与扫描位置见 [独立源码审计](artifacts/phase11/closure-source-audit.json)，该文件保存F11-FE-04修前审查快照。审查时51个变更程序/基础设施文件均登记 SHA；生成锁文件 `backend/uv.lock` 除外，程序文件均不超过300行。

## Stage 1：Spec Compliance

### 完整实现

| 原文要求/本期交付 | 独立结论、代码位置与证据 |
|---|---|
| REQ-013:516：一次触发run/trace，同模式分支会话，理解/模型/检索/工具/规则/回复/提交/HITL | 本期完整。`backend/src/globalmail_agent/worker/agent_runner.py:72` 在实际执行时开启receipt；`agent/context.py:37`、`agent/graph.py:63,82,87,208`、`agent/tool_gateway.py:32,146,166`、`application/commit_outcome.py:47` 为生产接入点；`observability/tracing.py:32` 记录实际终态。`observability/sdk_export.py:87,94` 为独立trace及workspace/mode/branch/conversation session。独立29项PG/SDK验证与真实检索探针确认实际节点/HITL/检索父关系；本人点击真实运行台链接进入Langfuse文本及图文树。见 [29项](artifacts/phase11/closure-focused-backend.log)、[检索及AC052](artifacts/phase11/closure-ac052-retrieval.log)、[文本树](artifacts/phase11/closure-langfuse-text.png)、[图文树](artifacts/phase11/closure-langfuse-image-receipt.png)。 |
| REQ-013:517：版本、来源、动作/错误/时间及实际usage，不能重复计量，未知费用 | 完整。`observability/snapshot.py:17,29,41` 从context/节点/既有usage_records投影ID、版本hash、时间及终态；`agent/budget.py:48,82` 保留原唯一计量路径，导出器不写usage；`observability/usage.py:10` 费用null。本轮真实读回确认文本18观测/5generation、16798输入/1253输出，图文7观测/2generation、6850输入/1862输出；全部parent关系逐项一致、ID唯一、用量精确一致。恢复证据所有cost为null。见 [只读核对](artifacts/phase11/closure-readback-guard.log)、[实际结果](artifacts/phase11/actual-qwen-observation.json)、[单次恢复](artifacts/phase11/backend-hierarchy-single-restore.json)、[独立审计](artifacts/phase11/closure-source-audit.json)。 |
| REQ-013:518：业务持久化，Langfuse不代替账本/队列/审计 | 完整。`application/commit_outcome.py:105` 仍由业务事务持久化；`worker/agent_runner.py:138` 在业务处理后保存观测；`observability/records.py:76` 失败仅降级，`api/observability.py:11` GET只读本地状态。独立故障/恢复验证保持一次合法回复，model与usage不增加；FT12实际Graph/PG/SDK503证据为reply_and_wait。见 [29项](artifacts/phase11/closure-focused-backend.log)、[四竞态](artifacts/phase11/closure-faults.log)、[FT12](artifacts/phase11/ft12-actual-app.json)。 |
| REQ-013:519 / AC-050：input/output/metadata/error控制和脱敏，SDK媒体处理前禁止正文/媒体/原异常 | 完整。`observability/media_filter.py:34,59` 只允许UUID、固定枚举、64位hash及非负计数；`tracing.py:24,39` 不复制调用参数/结果/异常原文；`sdk_export.py:84` 在SDK wrapper/媒体遍历之前复核，`:91,104` 使用隔离Context；`transport.py:36,41` 对SDK只返回固定安全Response。独立真实protobuf/HTTP测试覆盖邮箱、地址/假密钥、bytes/dataURL/媒体外链、第三方传播内容及原异常/响应体哨兵；无出站泄漏。真实图文页面Input null/Output undefined且attachment_prepare在understanding下面。见 [29项](artifacts/phase11/closure-focused-backend.log)、[本人实际截图](artifacts/phase11/closure-langfuse-image-receipt.png)。 |
| REQ-013:520 / AC-051 / FT-12：观测失败不阻塞/回滚业务，不为追踪重跑 | 完整工程验证。`observability/exporter.py:13,23,35,124` 为有界ID队列、有限尝试与受限flush；`settings.py:26` 限制队列/超时/尝试/flush。独立故障/并发验证无重跑/双计。FT12使用实际PG/Graph/官方SDK/loopback503，明确为ScriptedModel工程fixture：业务completed/reply_and_wait、实际POST1次、model3次及usage不变、ack_unknown/degraded、无链接、哨兵缺席。本人实际页面读取降级且链接数0，见 [FT12](artifacts/phase11/ft12-actual-app.json)、[降级截图](artifacts/phase11/closure-runtime-degraded-light-1440.png)。 |
| REQ-013:521 / 任务1：独立本机自托管环境/凭据/卷/版本 | 完整。`infra/compose.observability.yaml:1,53,163` 建立独立六服务、五卷，Web唯一127.0.0.1:3001；`infra/observability-images.lock.json:1` 固定全部digest与Web/Worker4.56.0，`backend/pyproject.toml:20` SDK4.17.0。`scripts/init-observability.ps1:6` 保旧随机私有配置，`observability-common.ps1:14` 限定ACL；启停脚本仅操作独立项目并保卷。本轮独立部署检查六服务healthy、digest/卷/项目/端口、匿名401、API认证及UI实际登录全部通过；本人Langfuse显示4.56.0。见 [部署日志](artifacts/phase11/closure-deployment.log)、[既有启停保旧](artifacts/phase11/observability-preservation.json)。本审没有重复停启服务。 |
| REQ-013:522 / AC-052：业务断言和人工核对，新run独立trace/最新事实/不重放 | 完整工程验证。`observability/snapshot.py:14` 保存parent_run；生产执行沿用`worker/agent_runner.py:76`加载新context。本轮重新运行真实PG探针：人审期间来信/人工回复不排新job，下一来信取最新人工回复、备注及客户事实，新run/trace不同且同会话、parent_run正确，仅一次合法Agent回复。见 [独立2项](artifacts/phase11/closure-ac052-retrieval.log)。真实Qwen业务失败保留；本期未采用模型自评作为通过依据。 |
| AC-049：多工具/意图/检索/模型/工具/结果同run及无重复累计 | 工程关联完整。实际Qwen文本5模型/4工具及18观测、图文2模型及7观测；本轮真实GET读回完整唯一树及usage精确一致。完成的PG/Graph多工具/检索fixture补足成功业务分支，而Qwen本身未通过业务语义。`agent/tool_gateway.py:146` 的真实检索receipt父工具为search_reference；见 [29项](artifacts/phase11/closure-focused-backend.log)、[检索](artifacts/phase11/closure-ac052-retrieval.log)、[实际读回](artifacts/phase11/actual-qwen-observation.json)。 |
| 主架构9:457：v4不可变观测，SDK不内部retry、发送前CAS、未知接受不盲发 | 完整。`observability/records.py:116` 发送前持久CAS ack_unknown；`exporter.py:48,66,88` 已知拒收/未连接才能有限尝试，未知接受只核对；`transport.py:41` 向SDK固定非retry Response，`sdk_export.py:163` 用有界v2时间/ID完整唯一集合核对。本轮真实HTTP429/503均单POST、read/connect timeout、响应丢失、重复/不完整集合、接受后本地mark失败与并发验证通过。符合 [Langfuse官方不可变观测约定](https://langfuse.com/faq/all/tracing-data-updates)，API使用方式核对 [官方v2说明](https://langfuse.com/docs/api-and-data-platform/features/public-api)。 |
| 主架构9:459 / 任务2：父关系恢复，以依赖而非时间决定层级 | 完整。`observability/sdk_export.py:124` 父拓扑创建，拒绝缺父/循环/重复UUID及低64bit冲突；`:82` 保留真实开始/结束时间。本轮实际HTTP同时间child-first测试通过。真实图文中attachment_prepare与understanding started_ns相同，远端实际parent匹配receipt且UI确实呈父子关系，见 [29项](artifacts/phase11/closure-focused-backend.log)、[实际读回](artifacts/phase11/actual-qwen-observation.json)、[截图](artifacts/phase11/closure-langfuse-image-receipt.png)。 |
| 任务2：作用域/源依赖/撤销与本地清理入口 | 完整本期入口。`observability/records.py:18,31` 复核workspace及scope、生命周期/generation、对象/来源祖先journal、图片内容及知识撤销epoch；`:85` 登记缓冲与来源依赖；`:146` 提供停写入口。`migrations/versions/0011_observability.py:23` export对象scope复合FK。独立跨客户FK、图片撤销、generation变化、知识下架及网络中撤销均通过，见 [29项](artifacts/phase11/closure-focused-backend.log)、[检索下架](artifacts/phase11/closure-ac052-retrieval.log)、[四竞态](artifacts/phase11/closure-faults.log)。完整远端删除和联合恢复未在本期实施。 |
| 任务3 / REQ-009：现有独立运行台真实六状态、实际本机入口、异步失效 | 本期观测行完整。`frontend/src/components/agent-runtime/ObservabilityStatus.vue:2,19` 为disabled/local_only/pending/exported/degraded/revoked；`api/observability-api.ts:12`校验run/trace/loopback路径及无凭据/query/hash。`use-agent-console.ts:13,24,72` traceRevision同步失效；`use-run-observability.ts:12,24` sync watcher/generation与KeepAlive拒晚到。本人实际已导出状态链接打开正确Langfuse；GET503清旧链接并显示固定错误，恢复GET后回到1链接；实际FT12降级0链接。本轮生产Vue/Router/KeepAlive4项通过，见 [4项](artifacts/phase11/closure-focused-frontend.log)、[错误态](artifacts/phase11/closure-runtime-get-error-dark-1280.png)。既有加载渲染缺陷另列F11-FE-04，不能据观测行正常忽略。 |
| REQ-009及14–16权限边界：邮件/运行台分离、无测试UI、商业工具拒绝 | 本期保持。`frontend/src/views/agent-runs/index.vue:48`只新增观测状态行；新增前端模块不建页面，未恢复旧AgentRunPanel。`agent/tool_gateway.py:37,40,168`及`agent/tool_schemas.py:88`仍仅允许原只读/辅助集合、human_assist拒自动草稿终局；本期diff无商业授权扩张。本轮实际邻居页面仍为邮件、运行台、知识、状态四入口，无测试控件或业务CRUD中心；完整后端451回归包括既有权限契约。 |
| 任务5：正式0010→0011增量升级、备份与保旧 | 本期工程证据完整。`migrations/versions/0011_observability.py:12`仅新增五列和scope FK，`adapters/database.py:9`检查0011。`formal-backup.json:1`记录真实custom pg_dump/pg_restore-list，465744bytes、70对象、受限ACL；`formal-preservation.json:1` 77旧表原字段/行hash全true、对象/配置保持且authorized_transition_columns为空；`formal-final-ready.json:1`正式API/proxy、原预览、观测均200。本审未停止或写入正式服务。最终独审门因F11-FE-04仍未闭合，不将任务5整体勾为完成。 |

### F11-VERIFY-03：本轮独立关闭

实施规划 `docs/planning/PHASE-11-IMPLEMENTATION.md:26` 明确existing-report只读合同。当前 `scripts/verify-observability.py:164` 进入既有报告分支，`observer.start()`只在`:183`的新模型else分支；构造service本身不开线程。退出时`ObservabilityService.close()`→`TraceExporter.close()`在thread未启动时只关闭资源，不恢复导出。

本轮先审guard源码再实际执行两次（后一遍保存原始日志），每次都是实际远端GET2、start/export_one/ModelProvider.request/execute全0、七表完整行hash不变；独立核对guard中的script SHA等于当前verify脚本 SHA `cbbfd37229acba820303ed6c4d4c00a1b1eec850db04d628d75641555a181974`。见 [原始日志](artifacts/phase11/closure-readback-guard.log)、[七表hash和调用计数](artifacts/phase11/readback-no-side-effects.json)、[当前SHA核对](artifacts/phase11/closure-source-audit.json)。没有付费模型/Graph执行或新span。原 [上轮FAIL](PHASE-11-REVIEW-FINAL.md) 保留。

### 部分实现 / 未实现 / Spec漂移

- 本期Stage1无核心缺失或HIGH。任务5的fresh审查完成门未过，原因是下方Stage2 MEDIUM；不提前将Phase11交付标记完成。
- 本期没有新增未批准页面/API商业操作/表职责。新增观测GET、五列、缓冲依赖、infra和辅助脚本均落在Phase11文件清单；源依赖登记仅为Phase12入口，不声称完成删除/联合恢复。
- 真实Qwen文本和图文各自业务失败、历史Phase1/7质量FAIL、七类业务与82项AC均保持后续验收边界。观测关联工程验证不勾选完整产品AC。

## Stage 2：Code Quality

### MEDIUM F11-FE-04：初始加载/暂时无run时null被传入执行时间线

- 位置：`frontend/src/composables/use-agent-console.ts:20`、`frontend/src/components/agent-runtime/run-presentation.ts:20`；实际调用来自 `frontend/src/views/agent-runs/index.vue` 渲染。
- 发现时表达式：

```ts
const steps = computed(() => record.value?.run.id === run.value?.id ? executionSteps(record.value!) : [])
```

- 原因与可达性：客户详情/运行记录尚未返回时，`record.value`是null、`run.value`是undefined；两个optional chain都得到undefined，比较为true。TypeScript非空断言只影响类型，运行时仍把null传到executionSteps，首次访问detail.model_calls就抛TypeError。实际GUI从知识页回运行台已记录同一渲染栈；读取完成后可恢复，因此定MEDIUM，不编造持续白屏或观测泄漏。
- 独立反例：生产`useAgentConsole`、真实Vue renderer、memory RouterView，mailApi.list及run读取挂起模拟真实初始loading；render实际读取`model.steps.value.length`，记录Vue errorHandler。没有伪造内部run或不可达input，结果0PASS/1FAIL，断言预期无渲染异常，实际`Cannot read properties of null (reading 'model_calls')`。见 [原始失败](artifacts/phase11/closure-null-render-before-fix.log)、[真实浏览器栈](artifacts/phase11/closure-null-render-browser.log)、[去敏probe源码](artifacts/phase11/closure-null-render.probe.ts)。probe原执行位置为`frontend/scripts/closure-null-render.probe.ts`；复制回该位置后，frontend目录运行`pnpm exec tsx --test scripts/closure-null-render.probe.ts`可重现。临时执行副本已清理，公开证据保留。
- 该表达式在Git HEAD已存在，本期在同一生产composable增加观测同步失效时保留了它，属于本轮实际调用链审查发现的既有缺陷，不称本期新增。需要主Agent按bug-fixer增加明确非空保护，并补初始loading/无run及跨页渲染回归，再fresh从Stage1复审。
- 测试盲区：`frontend/scripts/observability-events.test.ts:29`虽调用生产console，但组件只render空div，未读取console.steps；原90项及本轮观测4项通过均未证明本失败路径。这是额外证据，不将90项结果改写为没有通过。

### 其他质量与安全结论

| 检查 | 结论及证据 |
|---|---|
| 单一职责/大小/类型 | 51本期程序/infra文件完整登记SHA；唯一超300行是生成`backend/uv.lock`，非需拆分源码。receipt、投影、存储、SDK、Session和队列各自成模块；新增前端API/composable/component职责分开。变更TS/Vue未检出any；`frontend/src/api/observability-api.ts:12`先校验unknown再返回契约。见 [审计](artifacts/phase11/closure-source-audit.json)。除F11-FE-04外未确认新增质量缺陷。 |
| 注入/危险HTML/密钥/路径 | 变更程序扫描eval/危险HTML写入、VITE密钥前缀、provider密钥模式、用户绝对路径均无命中；`settings.py:20,38` SecretStr/loopback校验、`records.py:18` 参数化SQL、`local-common.ps1:40` 后端私有字段导入及`start-local.ps1:43`前端子进程清凭据均实际读码。测试合成key不当真实泄漏。备份及观测配置ACL证据仍为当前用户/SYSTEM/Admin。本轮未输出私有文件密钥。 |
| SDK前安全边界与测试真实性 | `media_filter.py:34`fail-closed；`sdk_export.py:84`早于SDK媒体遍历；`transport.py:41`不把rawbody/reason/HTTPError.context传SDK。独立29项包含真实OTLP protobuf、HTTP与PG/Graph，测试故障真实到达发送/恢复/撤销路径；没有仅凭mask参数声明安全。fake Model/Transport测试明确为工程控制，另有真实SDK及远端GET/GUI补证。 |
| 单次恢复与错误隔离 | 本轮四竞态包括接受后本地mark失败、并发CAS、网络中撤销及generation撤销，全部通过。原safe-buffer恢复只精确处理两条隔离trace至v2零确认，业务前后五表完整hash一致、usage7条；本轮再次核对恢复JSON全部未知cost为null。不得对v4盲重发。见 [四竞态](artifacts/phase11/closure-faults.log)、[审计](artifacts/phase11/closure-source-audit.json)。 |
| 实际视觉/邻居比较 | 本人浏览器实际打开1440×900亮色运行台及知识邻居、1280×720暗色两页，DOM scrollWidth=innerWidth；观测行复用既有Element Plus标签/按钮、theme文本与间距，不增加独立视觉体系。真实导出链接可点击、真实SDK503降级、GET503错误和恢复均分别观察。见 [运行亮](artifacts/phase11/closure-runtime-light-1440.png)、[运行暗](artifacts/phase11/closure-runtime-dark-1280.png)、[知识亮](artifacts/phase11/closure-knowledge-light-1440.png)、[知识暗](artifacts/phase11/closure-knowledge-dark-1280.png)、[GET错误](artifacts/phase11/closure-runtime-get-error-dark-1280.png)。另确认F11-FE-04真实控制台错误，不以截图视觉正常掩盖。 |

## 测试、冻结与编译原始证据

本轮独立测试使用本项目PG的各自UUID schema/temp objects，由fixture清理；没有正式邮件或新付费模型请求。

| 验证 | 精确结果/原始证据 |
|---|---|
| 本轮SDK/PG/恢复/图片/迁移/观测 | 29/29，80.343s，fail/error/skip=0；[原始日志](artifacts/phase11/closure-focused-backend.log) |
| 本轮AC052/真实检索及知识撤销 | 2/2，10.889s；[原始日志](artifacts/phase11/closure-ac052-retrieval.log) |
| 本轮恢复与并发四竞态 | 4/4，14.510s；[原始日志](artifacts/phase11/closure-faults.log) |
| 本轮生产Vue/Router/KeepAlive观测 | 4/4，1768.9762ms，0fail/cancelled/skip；[原始日志](artifacts/phase11/closure-focused-frontend.log) |
| 本轮新增可达null-render反例 | 0/1，568.071ms，1fail；[原始日志](artifacts/phase11/closure-null-render-before-fix.log) |
| 最终后端全量 | 完整451/451，1388.164s，fail/error/skip=0；本人读最终SUMMARY并独立核对283文件SHA，0差异、source_changed=false、stopped_at_test_boundary=false、test_exit_code=0。见 [原始日志](artifacts/phase11/backend-full-tests.log)、[冻结清单](artifacts/phase11/backend-source-freeze.json)、[本轮独立核对](artifacts/phase11/closure-source-audit.json)。未重复20分钟全量。 |
| 前端既有全量及构建 | 发现缺陷时原90/90串行，15788.7825ms；vue-tsc退出0，Vite7.1.7构建36.93s，3356 modules。对应 [90项修前原输出](artifacts/phase11/frontend-tests-before-loading-fix.log)、[修前构建原输出](artifacts/phase11/frontend-build-before-loading-fix.log)。可达渲染反例表明测试覆盖不足，编译/原测试通过并不等于该版本Stage2通过；后续91项/29.02s证据由下一fresh报告审查。 |
| Python编译 | 本轮在backend目录独立执行`.venv/Scripts/python.exe -m compileall -q src migrations ../scripts`，exit_code=0，原始stdout/stderr均为空；此前 [空日志](artifacts/phase11/backend-compile.log) 同结论。 |
| 锁与依赖/本机脚本 | `uv lock --check`、`uv pip check`均0；原输出下附。`test-local.ps1`三项通过，见 [锁日志](artifacts/phase11/backend-lock.log)、[依赖](artifacts/phase11/backend-dependencies.log)、[本机脚本](artifacts/phase11/local-script-tests.log)。 |

451原始结束输出：

```text
----------------------------------------------------------------------
Ran 451 tests in 1388.164s

OK
SUMMARY 451 failures 0 errors 0 skipped 0
FROZEN_SOURCE_CHANGED False
```

构建相关原始输出（摘录；完整资源清单在上方链接）：

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3356 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 36.93s
```

锁/依赖原始输出：

```text
Resolved 72 packages in 1ms
Checked 70 packages in 5ms
All installed packages are compatible
```

反例原始关键输出：

```text
✖ 生产运行台在可达初始loading状态不得把null交给executionSteps (13.4402ms)
ℹ tests 1
ℹ pass 0
ℹ fail 1
ℹ duration_ms 568.071
AssertionError [ERR_ASSERTION]: 首次生产render发生异常：TypeError: Cannot read properties of null (reading 'model_calls')
```

## 清理与后续责任

本人独立`phase11-closure-review`浏览器已关闭，两个本人标签均清理；本人前端临时probe执行副本及精确登记的临时截图/控制台snapshot已删除，去敏反例源码/日志及closure截图留在证据目录。各focused fixture自己的UUID schema/temp objects由清理函数释放，未操作共用schema/objects。共用15178/18188及正式15173/18080、原预览15175、观测3001均未被本人停止或重启。

主Agent负责F11-FE-04修复、新fresh复审、最终阶段文档回写、本地提交及共用隔离服务/schema/objects清理。存在该MEDIUM时不能整体PASS或记录Phase11完成；不得为此次前端修复再调用Qwen或重放业务。完整Phase12/13仍未实施。
