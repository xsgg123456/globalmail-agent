# Phase 11：自托管追踪验证

日期：2026-10-10。当前状态：Phase11工程四步验证完成；后端451项、前端91项、编译/功能测试及[第4轮fresh两阶段独审](PHASE-11-REVIEW-4.md)通过，无未关闭的本期HIGH/MEDIUM。正式升级保旧与隔离清理完成，正式/观测服务留运行。范围按 [实施规划](../planning/PHASE-11-IMPLEMENTATION.md)、Product-Spec v1.18 的 REQ-013 / AC-049–052 / FT-12及主架构第9节。

## 交付及边界

本期将实际 Agent run 的安全 receipt 导入独立本机 Langfuse，并在现有独立运行台提供真实入口和六种状态。既有四类商业售后只读、持续人工及客服发送权限保持；本期不增加交易执行、测试页面或在线 Prompt 管理。

真实模型两轮已进入追踪，但业务校验分别失败。工程观测通过不能将这些失败或历史 Phase1/7 的质量结论改为通过；七类业务、82项AC及模型语义仍在 Phase13 统一验收。完整删除、重置与联合恢复属于 Phase12，未实施。

## 按任务验收

| 任务 | 实际结果 | 证据 |
|---|---|---|
| 独立自托管 | 六服务 healthy，五个独立卷，Web仅127.0.0.1:3001；全镜像digest冻结；API认证、匿名401和UI实际登录通过 | [部署日志](artifacts/phase11/observability-deployment.log)、[停启保留](artifacts/phase11/observability-preservation.json)、[运行说明](../../globalmail-agent/scripts/OBSERVABILITY.md) |
| 正式安全观测 | context / 图片准备 / 理解 / 模型 / 检索 / 工具 / 规则 / 回复 / 提交 / 结果按实际执行记录；父拓扑恢复，不导出原模型输入输出、正文、媒体或原异常 | [真实读回](artifacts/phase11/actual-qwen-observation.json)、后端SDK与恢复测试、最终独审 |
| 本地状态及运行台 | disabled/local_only/pending/exported/degraded/revoked真实状态；本机合法trace链接；切换、离页、KeepAlive和SSE撤销立即失效，晚到读取不回填 | [前端回归](artifacts/phase11/frontend-tests.log)、[原前端FAIL](PHASE-11-FRONTEND-REVIEW.md)、明暗及错误态截图 |
| 故障隔离与用量 | 实际SDK发送503后业务reply_and_wait完成，模型/usage不重跑；实际Qwen7个generation与本地唯一账本一致 | [FT-12实应用](artifacts/phase11/ft12-actual-app.json)、[父图修复后单次恢复](artifacts/phase11/backend-hierarchy-single-restore.json) |
| 审查及正式升级 | 原三轮FAIL保留；[第4轮fresh Stage1/2均PASS](PHASE-11-REVIEW-4.md)，独立31项后端、5项前端、近预算FT-12、只读guard和实际明暗/父树均通过。正式0010→0011备份、升级并重新启动当前源码；77张旧业务表、70对象及配置保持 | [初审](PHASE-11-REVIEW.md)、[备份摘要](artifacts/phase11/formal-backup.json)、[保旧](artifacts/phase11/formal-preservation.json)、[最终启动](artifacts/phase11/formal-final-start.log)、[就绪](artifacts/phase11/formal-final-ready.json) |

服务冻结：Langfuse Web/Worker **4.56.0**，Python SDK **4.17.0**；PostgreSQL17.11、ClickHouse25.12.11.4、Redis7.4.11及Chainguard MinIO RELEASE.2026-09-22T19-25-18Z。具体镜像摘要在 [锁文件](../../globalmail-agent/infra/observability-images.lock.json)，SDK版本不作为服务版本。

## 真实模型与远端读回

使用隔离schema、独立临时objects及15178/18188端口，真实Qwen仅在初始验收调用一次文本多工具及一次图文。之后修复、远端核对及GUI没有再跑模型或旧业务。

| 运行 | 模型 / 工具 | 远端观测 / generation | 输入 / 输出tokens | 真实业务结果 |
|---|---|---|---|---|
| e214058a-eefb-4346-a35b-b8ce3f43a33b | 5 / 4 | 18 / 5 | 16798 / 1253 | reply_citation_invalid |
| 6a25f963-639c-4176-8ffc-eefa83af6e3a | 2 / 0；两次理解均有1个实际图像视图 | 7 / 2 | 6850 / 1862 | understanding_schema_invalid |

最终读回逐项确认单root、ID唯一、同project/trace、每个metadata.parent_observation_id与真实parentObservationId一致，模型数与usage精确相同，敏感邮箱哨兵及image/base64/可访问媒体URL不存在。费用保持null，没有把未知模型价格记为0。原完整模型记录已私有归档供Phase13分析，公开证据仅保留ID、状态、计数及安全元数据。

实际只读核对命令（backend工作目录，session属于本次隔离服务；服务清理后不可复用）：

```powershell
.venv/Scripts/python.exe ../scripts/verify-observability.py `
  --session ../../tmp/globalmail_phase11_browser_xcfdberi/session.json `
  --existing-report ../../docs/verification/artifacts/phase11/actual-qwen-observation-initial.json `
  --output ../../docs/verification/artifacts/phase11/actual-qwen-observation.json
```

输出退出0、`observation_pass=true`，见 [只读日志](artifacts/phase11/actual-qwen-readback.log)。这条命令不导出新span、不执行Graph、不调用模型。

只读模式额外将导出器start/export_one、Graph执行与ModelProvider.request设为调用即失败，同时真实读取远端两条trace并比较七张本地表完整行hash；全部入口0调用、实际GET两次、七表完全不变，见 [只读副作用反例验证](artifacts/phase11/readback-no-side-effects.json)。

## 保留的失败与修复

1. **前端旧入口撤销HIGH**：SSE失效若等业务GET刷新，可能因其他读取挂起/失败留下旧链接。独立traceRevision在每个合法SSE去重前同步失效，generation token与KeepAlive阻止晚到回填。生产Vue renderer+memory router测试包含该反例，原 [前端FAIL](PHASE-11-FRONTEND-REVIEW.md) 保留。
2. **v4同ID重发双计**：HTTP200返回events_only JSON接受回执，旧OTLP解析误判失败后重发。原 [重复FAIL](artifacts/phase11/backend-pollution-before-cleanup.json) 保留；只精确清理本期两条隔离trace、v2确认至零，再由原安全缓冲单次恢复，7条usage和五张业务表完整行hash不变。生产发送前CAS登记ack_unknown，接受后持久化exported，恢复只核对远端，不盲发。
3. **真实父层级MEDIUM F11-OBS-02**：Windows同started_ns、完成顺序child先parent后，使旧时间排序将attachment_prepare挂根。改为父依赖拓扑，拒绝缺父/循环/重复或低64bit碰撞；新增同时间child-first实际protobuf测试。原 [整体FAIL](PHASE-11-REVIEW.md)、[加强校验后旧树FAIL](artifacts/phase11/actual-qwen-parent-failure.json) 保留。最终 [单次恢复](artifacts/phase11/backend-hierarchy-single-restore.json) 和 [严格只读核对](artifacts/phase11/actual-qwen-observation.json) 均逐项确认真实父关系。
4. **原网络异常链隐私边界**：`raise ... from None`仍会保留`__context__`。当前Session向SDK只返回固定安全Response，不传原body/reason/网络异常对象，应用独立保存接受/拒收/未知标志；SDK测试用实际HTTP和异常哨兵核验，而非只扫描函数参数。
5. **验收脚本只读辅助MEDIUM F11-VERIFY-03**：旧`--existing-report`在分支判断前启动恢复导出器，其他pending run可能被隐式发送；已有两条真实trace当时均exported，没有观察到额外发送，但原只读保证不足。[第二轮FAIL](PHASE-11-REVIEW-FINAL.md)保留。已将start仅放新模型运行分支，并以真实只读GET、禁止发送/模型入口及七表hash不变核验；后端冻结源码不受此脚本修复影响，最终审查重新从Stage1开始。
6. **加载空记录MEDIUM F11-FE-04**：已有`record?.run.id === run?.id`在两者均缺失时成立，`executionSteps(null)`令跨页返回/初始加载渲染异常。[第三轮FAIL](PHASE-11-REVIEW-CLOSED.md)、真实浏览器与生产Vue renderer反例 [修前FAIL](artifacts/phase11/closure-null-render-before-fix.log) 保留，不称本期引入。当前按已校验的record是否存在生成steps，空记录返回空节点；永久`agent-console-loading.test.ts`及 [修后针对验证](artifacts/phase11/frontend-loading-fix.log) 1/1通过，完整前端重新91项及构建通过；后端283文件未改。

Langfuse v4相同ID重发不能依赖去重，见 [官方不可变观测说明](https://langfuse.com/faq/all/tracing-data-updates)。实际读回使用有界起止时间的v2 observations，旧trace GET已被events_only移除，见 [官方API说明](https://langfuse.com/docs/api-and-data-platform/features/public-api)。

## 故障与安全

后端测试覆盖实际HTTP429/503、连接未建立与读取超时、队列积压、缓冲白名单失败、partial/重复/不完整回执、进程恢复、接受后本地落盘失败、同run并发发送、网络中撤销、generation/客户/知识/图片撤销及来源祖先清理围栏。未知接受结果仅受限远端核对，未证实则degraded/observability_ack_unknown，不自动补发或重新调用Agent。

FT-12额外使用真实PG/Graph/官方SDK/loopback503服务，模型输出明确为工程ScriptedModel：业务完成reply_and_wait、实际SDK POST一次、三次模型请求及usage不变、哨兵不进OTLP、前端无trace链接且显示降级。证据 [FT-12](artifacts/phase11/ft12-actual-app.json) 与 [真实故障页面](artifacts/phase11/runtime-degraded-light-1440.png)。此用例不计真实模型业务语义通过。

第4轮独审追加同一PG/Graph/SDK503时序的近预算验收：理解修正、一次供应商失败及有界重试后，六次模型请求在6/6上限内完成reply_and_wait和一次出站；第七次真实预算预留被budget_exhausted拒绝。六条原usage（五known、一unknown）及其SHA在导出前后相同；实际SDK POST一次503后degraded/ack_unknown、无URL、敏感哨兵不进线。各次provider调用前均有持久预留，未知调用保持unknown而不记零。见[独立近预算FT-12](artifacts/phase11/four-ft12-near-budget.json)与[日志](artifacts/phase11/four-ft12-near-budget.log)；仍为工程ScriptedModel，不计Qwen语义。

SDK手动观测使用隔离Context，不继承第三方原始传播内容；白名单在SDK媒体处理前复核。只将原usage账本投影到generation，费用未知保持null。私有配置不传给Vite，后端与观测凭据不进入Git或公开日志；备份及观测配置ACL限制当前用户/SYSTEM/管理员。

## 测试与编译

最终后端全量 **451/451通过，0fail/error/skip，1388.164s**。283份src/tests/migrations/pyproject/uv.lock测试前后SHA相同，source_changed=false、stopped_at_test_boundary=false、test_exit_code=0；主Agent逐份核对当前源码亦0差异。证据：[原始全量日志](artifacts/phase11/backend-full-tests.log)、[测试冻结](artifacts/phase11/backend-source-freeze.json)、[当前逐SHA核对](artifacts/phase11/backend-current-source-match.json)、[交付时283文件再核对](artifacts/phase11/backend-delivery-source-match.json)。修前中间437项日志保持历史，不作为最终证明。

- 前端全量：`pnpm exec tsx --test --test-concurrency=1 scripts/*.test.ts`，**91/91、0fail/skip，15590.3801ms**；[原始日志](artifacts/phase11/frontend-tests.log)。Windows并发runner中断记录不当通过，采用同一全量串行runner完成。原90项结果保存为 [修前日志](artifacts/phase11/frontend-tests-before-loading-fix.log)。
- 前端构建：`pnpm build`，vue-tsc退出0，Vite7.1.7构建 **29.02s**；[完整输出](artifacts/phase11/frontend-build.log)。修前36.93s日志保留为 [历史构建](artifacts/phase11/frontend-build-before-loading-fix.log)，已有bundle体积提示不是编译失败。
- 后端当前编译：`python -m compileall -q src migrations ../scripts`，退出0、原始stdout/stderr为空；[日志](artifacts/phase11/backend-compile.log)。
- `uv lock --check`与`uv pip check`退出0；[锁文件](artifacts/phase11/backend-lock.log)、[依赖](artifacts/phase11/backend-dependencies.log)。
- 本机脚本：`pwsh -File globalmail-agent/scripts/test-local.ps1`三项通过；[日志](artifacts/phase11/local-script-tests.log)。
- Git空白检查：全部暂存源码与Markdown通过；原始工具日志中的行尾空白/结束空行保持，不改写历史输出，完整检查的这类提示如实记录于[检查范围](artifacts/phase11/git-whitespace-check.json)。

数据库全量使用本项目PG连接，测试各自创建UUID schema和临时对象并清理。原始命令为 `.venv/Scripts/python.exe ../../tmp/phase11-frozen-tests.py`；包装器只私下读取本地连接、unittest discover，记录src/tests/migrations/pyproject/uv.lock全部文件SHA，源码改变则在test清理完成后停止。可复跑标准入口见 [后端说明](../../globalmail-agent/backend/README.md)，不配置测试数据库而跳过数据库用例不能算本期通过。

## GUI与正式保旧

主Agent实际打开1440亮色、1280暗色运行台及知识邻居页；document.scrollWidth与innerWidth一致。导出成功时实际点击入口进入已认证本机Langfuse；接口503故障注入只影响观测GET，旧链接立即清除、显示固定失败文案，恢复实际GET后入口恢复。实际SDK503造成的degraded另由FT-12页面证明，没有用GET mock冒充导出失败。

- [1440亮色运行台](artifacts/phase11/runtime-exported-light-1440.png)、[1280暗色](artifacts/phase11/runtime-exported-dark-1280.png)、[读取失败](artifacts/phase11/runtime-error-dark-1280.png)。
- [1440知识页](artifacts/phase11/knowledge-light-1440.png)、[1280暗色知识页](artifacts/phase11/knowledge-dark-1280.png)。
- [最终图文父树](artifacts/phase11/langfuse-image-final.png)、[图像处理安全receipt](artifacts/phase11/langfuse-image-receipt-final.png)、[文本多工具追踪](artifacts/phase11/langfuse-text-final.png)。图像处理位于understanding子节点，Input/Output无正文和原图，仅ID、张数/视图数及状态。

正式升级前停本项目API/frontend而保留业务PG，生成public自定义pg_dump并实际验证pg_restore --list，复制70对象与私有配置；465744bytes，私有目录 `before-0011-20261010-095740`，ACL已逐项核验。迁移0011仅新增观测列和作用域FK，未迁移或排除旧业务字段。正式重启后77旧表原列/行hash、objects字节与settings仍全部相同，authorized_transition_columns为空；API18080及15173代理ready均200，观测3001及原预览15175正常。没有向正式库增加测试邮件或付费模型调用。

## 清理与下一步

本期隔离15178/18188服务、专属schema和临时对象由原launcher精确清理；主Agent及各独审自己的浏览器已关闭，临时GUI登录状态文件删除被自动审批拒绝（blocked by policy），文件继续受私有ACL保护并排除Git，见[清理例外](artifacts/phase11/gui-state-cleanup-exception.json)。正式API/前端、原预览、六服务观测及五卷继续保留；私有原模型记录和升级备份保留，见[清理核验](artifacts/phase11/cleanup.json)、[清理后正式保旧](artifacts/phase11/formal-preservation.json)。

已按现有授权整理Phase11本地Git提交，不推送；提交号以Git日志为准，私有配置/备份/tmp、用户.idea及独立进化队列不纳入。本期工程完成，下一期Phase12负责完整删除/重置与联合恢复，开工前按0011 head重排历史迁移编号；Phase13负责模型质量、全量业务验收与本地交付。本报告不勾选产品AC。
