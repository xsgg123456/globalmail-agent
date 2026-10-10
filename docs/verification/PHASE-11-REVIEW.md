# Phase11 整体独立审查：Stage 2 FAIL

日期：2026-10-10。本报告由 fresh code-reviewer 依据 `.agents/skills/code-review/SKILL.md` 独立执行，只审查，不修复、不提交、不派 Agent。

**结论：Stage 1 核心 Spec / 本期工程关联检查通过，无未闭合 HIGH；Stage 2 FAIL，1 项确认 MEDIUM：真实图文 trace 在相同开始时间下丢失父层级。Phase11 尚不满足交付门槛。** 本报告保留发现时结论，后续拓扑修复、新传输安全调整、重新冻结后的全量回归与 fresh 复审另出报告，不覆盖本报告为 PASS。

本次不推进 Phase12/13，不称七类业务或82项产品AC完成。真实 Qwen 两个运行分别保留 `reply_citation_invalid` / `understanding_schema_invalid`，工程观测结果不能反证这些业务失败。

## 范围与规划

已读 `AGENTS.md`、`Product-Spec.md:155,512–528`、`AGENT-ARCHITECTURE.md:447–459` 当前原文、`DEV-PLAN.md:3,253–265`、`docs/planning/PHASE-11-IMPLEMENTATION.md:3–24`、`docs/README.md` 和 `docs/planning/SESSION-HANDOFF.md`。旧 Phase11 关键文件中的 `AgentRunPanel` 路径以2026-10-10授权及本期实施规划的独立运行台责任覆盖，不恢复旧邮件侧面板。

执行顺序：逐条映射 Spec 与五项交付 → 审查实际节点、白名单、计量、队列及撤销围栏 → 隔离 PG / SDK / 前端交互和真实自托管读回 → 在无 HIGH 后检查质量、安全、测试真实性与邻居页面渲染。报告范围为本期增量及其生产调用链，不将历史报告的通过声明替代本次证据。

下文 `backend/`、`frontend/`、`scripts/`、`infra/` 均相对于仓库内 `globalmail-agent/`，证据文件相对于仓库根目录。测试没有向正式库写入邮件，fixture 使用 UUID schema 和临时 objects 并自行清理；没有停止 Langfuse 或用户的正式服务。

## Stage 1：Spec Compliance

### 完整实现与验证

| 条目 | 本次结论与证据 |
|---|---|
| SCOPE-017 / REQ-013 首版 Langfuse、一次触发的 run/trace 及分支会话关联 | 已实现独立自托管服务与正式节点 receipt。`infra/compose.observability.yaml:1–36,53–170` 为独立六服务、五卷、唯一 loopback UI 入口；`infra/observability-images.lock.json:1–77` 固定服务4.56.0与全部依赖digest。`backend/src/globalmail_agent/worker/agent_runner.py:72–95,138–144` 启动/结束本轮 recorder；`observability/sdk_export.py:82–123` 创建同 trace 的手动官方 SDK 观测，以 workspace/mode/branch/conversation 生成 session。独立部署检查六服务 healthy、镜像及卷隔离、telemetry关闭、匿名401、UI登录通过；实际打开两个 trace 并截图。父树准确性另见 Stage2 F11-OBS-02，不能据同 run 关联宣称父树全部正确。 |
| REQ-013 第1项：意图、模型、检索、工具、规则、执行、回复与 HITL | 实际调用点有证据，不补造未执行节点：`agent/context.py:37`、`agent/graph.py:64–68,82–91,208`、`agent/tool_gateway.py:30–35,146–149,165–167`、`application/commit_outcome.py:47–48`、`observability/tracing.py:32–35`。独立 retrieval 探针走真实 PG 发布、KnowledgeSearch 和 Graph，确认 retrieval 的父 receipt 为 search_reference，撤回后不再导出。`application/risk_handoff.py:5–10` 最终调用同一个受观测的 commit_outcome，因此已有危险、理解后危险及兜底没有遗漏 commit；持续人工建议在 `commit_outcome.py:66–77` 同样走实际提交。当前授权为只读辅助，不恢复交易/履约执行。 |
| REQ-013 第2项：版本、来源、动作/结果、错误、耗时、实际 usage，未知价格 | `observability/snapshot.py:17–47` 导出模式/来源对象ID、版本摘要、实际起止时刻及既有 usage_records 投影；`:48–53` 导出真实终态和安全错误码。`agent/budget.py:48–69,82–101` 是唯一预留/结算账本；导出器不写第二账本。`observability/usage.py:7–10` 费用保持 null。handed_off/cancelled 枚举缺口已补入 `media_filter.py:14–16`，`tests/test_observability.py:123–135` 用真实人审提交断言 handed_off/handoff。 |
| REQ-013 第3项：业务状态、恢复与技术观测分工 | `observability/records.py:76–98` 在业务事务后保存安全缓冲，失败仅标观测异常；`application/commit_outcome.py:105–117` 仍由业务库保存 artifact、状态、事件与租约。`api/observability.py:9–19` 只读真实本地状态。独立故障检查合法回复仍只产生一次，usage与模型请求数不变；`backend-single-restore.json:2–63` 的业务前后摘要一致。 |
| REQ-013 第4项 / AC-050：字段控制、真实正文与媒体禁入 SDK，正常/异常无明文 | `observability/media_filter.py:4–65` 仅接受规范 UUID、固定枚举、64位hash及非负整数；`tracing.py:24–30,49–59` 不复制模型返回或异常正文，非法字段使本轮 degraded。`sdk_export.py:82–85` 在包装器/媒体处理前再次校验；隔离父 Context 不导入第三方传播 metadata。`tests/test_observability_sdk.py:87–99,113–117` 真实 SDK media traversal 拒绝邮箱/原图bytes/data URL/外链/任意错误和传播哨兵；`test_observability.py:111–121,138–152` 验证异常及脱敏失败。`test_observability_vision.py:18–61` 实际加载授权图像但序列化 OTLP 不含图像、base64或可访问URL。最终安全缓冲读回中测试邮箱、data:image、image_url、base64、sk-lf-均未出现。传输异常 context 的后续调整未在本报告复审，见安全部分。 |
| REQ-013 第5项 / AC-051 / FT-12：Langfuse失败不回滚/阻塞业务，不补跑 | `observability/exporter.py:13–16,23–32,35–82,121–136` 为有界 run ID 队列、有限尝试与flush/停机；`settings.py:26–30` 限制队列、HTTP与flush预算。独立测试 HTTP拒收/超时、队列积压、缓冲脱敏失败、撤销期间成功与接受后本地mark失败，业务、模型请求及usage不重跑。前端 `use-run-observability.ts:11–23` 的失败仅清当前观测并给固定错误文案，`ObservabilityStatus.vue:3–10` 显示降级与只读刷新。 |
| REQ-013 第6项：本机自托管独立配置/凭据/卷，固定镜像 | `scripts/init-observability.ps1:6–27,36–47` 生成随机凭据并保持已有配置；`observability-common.ps1:10–35` 限制私有文件ACL；`start-observability.ps1:1–7` 启动且核验，`stop-observability.ps1:1–8` 仅停止本项目并保留卷。独立执行 test-observability.ps1 确认实际六服务和本机入口。停启保留证据由主Agent提供，未在本审再次停服务；`scripts/test-observability-preservation.ps1:41–75` 核对配置hash、五卷、原追踪与业务PG容器身份/启动时间。 |
| REQ-013 第7项：业务断言/人工核对，不用模型自评当唯一依据 | 工程测试显式标注 scripted outputs，不测语义准确率（`tests/test_observability.py:1`）。`scripts/verify-observability.py:57–133` 从实际模型调用和远端观测比对，而非模型自评；真实两次业务失败保留在 `actual-qwen-observation-initial.json`。新运行有独立 trace 与历史 parent，既有 Prompt 文件和当前规则没有由 Langfuse 在线替换。 |
| AC-049：多工具处理、同run关联、usage无重复 | 隔离完整回复 fixture 有理解、模型、工具、规则、提交与结果；真实 retrieval 探针补检索分支。实际 Qwen 文本5次模型/4次工具，远端18观测/5 generation，输入16798、输出1253；图文2次模型，远端7观测/2 generation，输入6850、输出1862。远端唯一ID及usage与7条本地账本一致，见 `backend-single-restore.json:75–84,1154–1163`。旧同ID重试造成36/10与14/4的FAIL在 `backend-reexport.json` / `backend-pollution-before-cleanup.json` 保留，精确清理本轮两trace至零后只恢复原安全缓冲；模型和业务不重跑。F11-OBS-02 的父关系不能由这些计数反证。 |
| AC-052：人审后新来信、最新事实、新run/trace、不重放旧动作 | 独立 `tmp/phase11-review-ac052.py` 真实 PG 探针通过：人审中来信及人工回复不排新job；下一来信取最新人工回复/备注与客户事实；新 trace 不同，metadata 同 conversation 且 parent_run 为旧run；只新增一次合法 Agent 回复。生产依据为 `worker/agent_runner.py:72–95`、`observability/snapshot.py:14–24` 与 `application/commit_outcome.py:89–118`。测试是工程验证，未称模型语义验收通过。 |
| 本地作用域、撤销/删除/知识撤回/generation 与 Phase12 清理入口 | `observability/records.py:18–54` 按 workspace与完整 SCOPE_KEYS、生命周期、branch_generation、对象祖先删除journal、图片撤销及知识revocation_epoch围栏；`:85–92` 保存observability_buffer及来源依赖，`:145–148` 提供停止写入口；迁移 `migrations/versions/0011_observability.py:12–26` 对export_object_id使用复合作用域FK。独立PG探针证实其他workspace404、跨客户缓冲FK拒绝、图片/knowledge/generation撤销禁导出、网络中撤销不恢复链接。远端完整清理/联合恢复仍属Phase12，本审不记完成。 |
| 独立运行台真实入口、六状态与异步失效；不恢复旧邮件面板 | `frontend/src/views/agent-runs/index.vue:48,66,69` 只增加当前 run 的观测行；`api/observability-api.ts:12–41` 验当前run、hex trace、loopback路径并拒外链/凭据/query/hash；组件 `ObservabilityStatus.vue:19–25` 提供六状态、KeepAlive及离页失效。`use-agent-console.ts:13,24,72` 独立traceRevision，`useConversationEvents.ts:26` 在刷新去重前失效；`use-run-observability.ts:13–28` sync watcher与generation阻止晚到回填。独立 production Vue renderer+router+KeepAlive 测试4/4通过，原 F11-FE-01 已闭合；旧初审 `PHASE-11-FRONTEND-REVIEW.md` 未改写。 |
| 0010→0011保旧与正式服务 | 迁移只增加五列和作用域FK（`migrations/versions/0011_observability.py:12–26`），正式版本要求 `adapters/database.py:9` 为0011。`formal-preservation.json:2–84` 核对77旧表既有列/记录摘要、objects和settings保持，authorized_transition_columns为空；正式启动地址15173/18080见 `formal-start.log:4–6`。独立增量迁移/跨客户FK测试通过，不据备份存在推断Phase12恢复验收完成。 |

### 未完成 / 限制

- **Phase11整体交付未完成**：父层级MEDIUM成立；发现后即将重新冻结，448后端全量运行尚未结束，不能将正在运行或修前全量记为最终通过。`docs/verification/artifacts/phase11/backend-full-tests.log` 本次读取仍为逐项进行状态。
- 真实 Qwen 的两项业务失败保留。文本多工具与图文已进入实际自托管UI，未通过的业务语义不因观测正常而转为通过。证据：`actual-qwen-observation-initial.json`、`backend-single-restore.json:75–84,1154–1163`。
- 完整本地/远端删除与联合恢复没有在本期交付；本期仅登记安全缓冲依赖与即时停读/停导出入口，证据 `observability/records.py:31–54,145–148`。不得以本轮精确删除两条隔离污染trace代替Phase12。

## Stage 2：Code Quality

### 确认问题

**MEDIUM F11-OBS-02：相同 started_ns 时，子 receipt 在父 receipt 之前创建，静默挂到 run，实际图文父树错误。**

- 要求：主架构第9节规定真实节点层级，本期规划Task4要求实际层级核对；SDK应忠实恢复 recorder 保存的父关系。
- 根因：审查时 `backend/src/globalmail_agent/observability/sdk_export.py:100–103` 仅按 `started_ns` 稳定排序，再用 `spans.get(parent_observation_id, root)`。`tracing.py:54–59` 按完成顺序保存 receipt，子先父后；相同开始时刻不代表父依赖先完成排序。
- 真实反例：`backend-single-restore.json:1361–1385` 的 attachment_prepare ID `a76e6a0495682b29`，远端parent是根 `b0050f0b3d80b007`；metadata的parent是 UUID `7eb2e422-7af4-4847-9d4c-6ddd264e793e`，应对应 understanding ID `9d4c6ddd264e793e`（`:1419–1438`）。两者 started_ns 都是 `1791596717322231300`。独立真实UI截图 [review-langfuse-image.png](artifacts/phase11/review-langfuse-image.png) 也显示 attachment_prepare 挂根。
- 测试盲区：`backend/tests/test_observability_sdk.py:54–67,70–85` 原父树测试给父/子不同起点；`scripts/verify-observability.py:121–127` 原 hierarchy_pass 只核对“父ID存在”，根ID存在就放过错误父层级。不能由测试绿或run关联正确推断父树正确。
- 修复标准：按父依赖拓扑创建，保持真实起止时刻和稳定span ID；缺父/循环不可静默改根；新增相同开始时刻用例，并把远端parent ID逐项对照receipt元数据。Langfuse v4不可依赖同ID覆盖，修复后实际trace重建必须遵守本期精确隔离清理边界。[官方不可变观测说明](https://langfuse.com/faq/all/tracing-data-updates)

主Agent已接收该问题并启动后续修复。本报告到此留存 FAIL，不替后续新源码出通过结论。

### 质量、测试真实性与安全

| 检查 | 结论与证据 |
|---|---|
| 命名、结构、类型与文件大小 | 观测按recorder/snapshot/scoped records/exporter/transport职责分开；审查时变更文件最大 `agent/graph.py:1–276`，`sdk_export.py:1–178`、`records.py:1–148`；新增前端生产代码无any。`frontend/src/api/observability-api.ts:3–10,14–34` 从unknown校验真实合同。未发现超过300行文件或新增重复计量实现。 |
| 测试真实性 | 新SDK用真实HTTP与protobuf，`test_observability_sdk.py:134–166` 核验429/503单POST、ReadTimeout/ConnectTimeout、接受后丢回执、完整/重复/不完整ID集合；`test_observability_recovery.py:27–96` 用真实PG验证发送前CAS、恢复只读、两个exporter与撤销。独立14/14通过。另独立4个PG探针验证generation、发送中撤销、接受后本地mark丢失、同run并发，只发一次且业务不重跑。父树相同时间测试盲区由F11-OBS-02确认，故该维度整体不能通过。 |
| 安全扫描 | 本次新增观测/API/前端和相关脚本未发现eval、危险HTML、前缀密钥或硬编码真实凭据；`media_filter.py:4–65` 严格拒任意内容，`settings.py:32–48` 与前端API`:23–28` 限制本机链接。`local-common.ps1:40–54` 仅导入五项观测私有env，`start-local.ps1:43–52` 在启动Vite前移除观测/模型凭据。git check-ignore确认 `.local-data/observability/{backend.env,compose.env,gui-state.json}` 被忽略。测试密钥是固定合成标识，不作真实泄漏。 |
| 传输安全后续变化 | 主Agent在收口时补充：原 `HTTPError from None` 的异常context仍可保留底层网络异常对象。报告落盘前 `observability/transport.py:24–53` 已开始改为固定安全Response。此变化发生在本次独立SDK/恢复14项及compileall之后，**未在本报告重验，不给新版安全/编译通过结论**；须由下一轮fresh审查核对SDK接收对象及原始异常哨兵。 |
| Spec 漂移 | 仅新增只读 `/api/v1/observability/runs/{run_id}`（`api/observability.py:9–19`）、既有trace表五列、registered object安全缓冲和运行台状态行。对应REQ013及Task1–3；没有新增测试控制台、客户发送入口、在线prompt治理或交易写权限。`commit_outcome.py:66–83` 原权限门保留。未发现本期未经授权scope creep。 |
| 实际视觉对比 | 独立打开运行台与邮件邻居页面并截图查看：[运行台](artifacts/phase11/review-runtime-light.png)、[邮件](artifacts/phase11/review-mail-light.png)。1440宽下同Art侧栏/顶部/卡片、ElTag/按钮字体及主题色相符，新状态行使用 `ObservabilityStatus.vue:2–10` 的原主题变量和组件；没有把日志混入客户邮件。主Agent1280暗色/1440亮色及错误态截图已读作补充，未将CSS类数量当渲染证据。Langfuse实际图文/文本截图为 [image](artifacts/phase11/review-langfuse-image.png)、[text](artifacts/phase11/review-langfuse-text.png)，I/O为空是本期安全导出设计；其父树存在F11-OBS-02。 |

## 验证与编译原始结果

### 独立定向验证

命令：`globalmail-agent/backend/.venv/Scripts/python.exe tmp/run-refactor-tests.py test_observability_sdk test_observability_recovery`。私有数据库URL只进进程env，fixture自行隔离。完整输出保存在 [review-sdk-recovery.log](artifacts/phase11/review-sdk-recovery.log)，退出0；原始结尾：

```text
SUMMARY 14 failures 0 errors 0 skipped 0

----------------------------------------------------------------------
Ran 14 tests in 29.603s

OK
```

本轮早期还独立执行观测/媒体/迁移旧版18项：`Ran 18 tests in 52.635s / OK / SUMMARY 18 failures 0 errors 0 skipped 0`。它在一次性导出修复前运行，不能当新版全量证据，也没有发现真实同ID重发双计，故不据此宣称最终通过。

独立 supplemental PG 探针实际结果（仅工程断言）：

```text
test_human_reply_and_new_input_have_new_trace_and_latest_facts ... ok
test_actual_search_receipt_and_withdrawal_export_fence ... ok
----------------------------------------------------------------------
Ran 2 tests in 11.138s
OK

test_generation_revokes_pending_without_rerun ... ok
test_revoke_during_send_wins_over_http_success ... ok
test_crash_after_acceptance_resolves_existing_receipt_without_resend ... ok
test_concurrent_export_claim_sends_once ... ok
----------------------------------------------------------------------
Ran 4 tests in 14.496s
OK
```

前端独立命令：`pnpm exec tsx --test --test-concurrency=1 scripts/observability*.test.ts`，退出0；原始输出：

```text
✔ 生产SSE撤销在其他读取失败或挂起时立即清追踪；KeepAlive离页拒绝晚到 (735.1376ms)
✔ 仅接受当前运行的真实本地追踪入口，拒绝外链、凭据及伪造成功 (1.6855ms)
✔ 切换运行立即清空旧入口，晚到成功不能串会话 (4.7405ms)
✔ 观测请求失败可重试，离页后晚到响应不恢复入口 (8.4149ms)
ℹ tests 4
ℹ suites 0
ℹ pass 4
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2153.9825
```

独立部署检查 `pwsh -File globalmail-agent/scripts/test-observability.ps1` 退出0；原始输出：

```text
clickhouse healthy; image locked; project isolated
langfuse-web healthy; image locked; project isolated
langfuse-worker healthy; image locked; project isolated
minio healthy; image locked; project isolated
postgres healthy; image locked; project isolated
redis healthy; image locked; project isolated
HTTP health OK; authenticated project globalmail-agent-local; anonymous rejected (401); UI login OK
```

### 编译

- 后端独立：在 `globalmail-agent/backend` 执行 `.venv/Scripts/python.exe -m compileall -q src migrations`，退出码0，**原始stdout/stderr为空**。发生在本报告所列后续传输调整之前，不能覆盖新冻结代码。
- 前端独立：`pnpm exec vue-tsc --noEmit`，退出码0，**原始stdout/stderr为空**。
- 已读取主Agent完整 [frontend-build.log](artifacts/phase11/frontend-build-before-loading-fix.log)（原始编译输出），开头及结尾：

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3356 modules transformed.
...
✓ built in 36.93s
```

已读取前端全量 [frontend-tests.log](artifacts/phase11/frontend-tests-before-loading-fix.log)，原始结尾为90 tests、90 pass、0 fail、0 skipped、15788.7825ms；本审未重复前端全量。后端448项最终全量尚未结束且即将因后续修复重冻，**本报告不写全量通过**。

## 交接

原 F11-FE-01 撤销旧链接 HIGH、Langfuse v4 重发双计与 handed_off 终态缺口在本轮相应证据中已闭合。F11-OBS-02 留存为本报告确认失败；后续按父拓扑、完整父ID核对及新的传输安全边界修复后，重新冻结、完成最终全量并从 Stage1 fresh 复审。完整清理恢复及真实模型质量继续保留给Phase12/13。
