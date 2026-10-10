# Phase11 fresh 最终审查：Stage 2 FAIL

日期：2026-10-10。角色：独立 code-reviewer。依据 `.agents/skills/code-review/SKILL.md`，只审查与保存去敏证据，不修复、不提交、不派 Agent。

**结论：Stage 1 的本期生产功能及安全契约通过，无新增 HIGH；Stage 2 FAIL，确认一项 MEDIUM F11-VERIFY-03：辅助验收脚本的 existing-report 模式在读回之前启动导出恢复。** 主Agent已移动启动位置，但该修改发生在本报告的独立验证之后，尚未完成新一轮 fresh 复审。本报告保留发现时 FAIL，不替刚修改的脚本出 PASS。最终后端451项全量仍在运行，不能把进行中日志记为最终通过。

旧 F11-FE-01、F11-OBS-02 与网络异常链安全调整在本轮对应独立检查中闭合；旧 FAIL 报告及污染/父图失败证据保持原样。真实 Qwen 的 `reply_citation_invalid`、`understanding_schema_invalid` 仍为业务失败，不因追踪正确转为通过。Phase12/13、七类业务及82项产品AC不在本报告的完成范围。

## 范围与审查规划

已读 `AGENTS.md`、当前 `Product-Spec.md:155,420–455,512–528`、`AGENT-ARCHITECTURE.md:447–461`、`DEV-PLAN.md:253–265`、`docs/README.md`、`docs/planning/SESSION-HANDOFF.md`、`docs/planning/PHASE-11-IMPLEMENTATION.md`；同时阅读原前端/整体 FAIL 与当前验收文档。范围为 git status/diff 中本期后端、迁移、依赖、前端独立运行台、基础设施及脚本；`.codex/evolution/signals.jsonl` 排除。

有序步骤与完成标准：

1. 逐条映射 REQ-013、AC-049–052、FT-12及本期五项交付；每条附生产调用点和行为证据。
2. 检查实际节点、白名单、唯一用量、队列/发送协议及撤销围栏；出现核心 HIGH 即停止，不进入 Stage2。
3. Stage1 无 HIGH 后独立运行真实SDK/PG恢复、前端生产交互，检查安全、类型、结构、测试真实性和实际页面渲染。
4. 核对最终全量/冻结、正式保旧及辅助验收证据；缺陷按失败 Stage 返回主Agent，修改后重新 fresh 审查。

下文 `backend/`、`frontend/`、`scripts/`、`infra/` 相对于 `globalmail-agent/`；证据相对于仓库根目录。测试使用 UUID schema/临时 objects，未向正式库写邮件，未执行新付费模型调用，未停止正式或观测服务。

## Stage 1：Spec Compliance

### 完整实现与验证

| Spec / 交付条目 | 结论、代码位置与验证证据 |
|---|---|
| REQ-013:516 / SCOPE-017：自托管、run/trace与同模式分支会话 | 完整实现。`infra/compose.observability.yaml:1,53–170` 为独立六服务、五卷、唯一 loopback Web入口；`infra/observability-images.lock.json:1–77` 固定服务4.56.0及全部digest；`backend/src/globalmail_agent/worker/agent_runner.py:44–50,72–95,138–144` 关联实际run；`backend/src/globalmail_agent/observability/sdk_export.py:87–99` 建立同trace、按workspace/mode/branch/conversation派生session。独立六服务部署检查及真实UI均通过，见 [部署原始日志](artifacts/phase11/final-review-deployment.log)、[图文追踪](artifacts/phase11/phase11-final-review-langfuse-image.png)、[文本追踪](artifacts/phase11/phase11-final-review-langfuse-text.png)。 |
| REQ-013:516：理解/模型/检索/工具/规则/回复/提交/结果及HITL实际阶段 | 完整实现，按实际发生记录。`backend/src/globalmail_agent/agent/context.py:37`、`agent/graph.py:63,82–91,208`、`agent/tool_gateway.py:32,146,166`、`application/commit_outcome.py:47` 和 `observability/tracing.py:32–35` 为生产调用点；`application/risk_handoff.py:5–10` 共用 commit_outcome。独立真实PG/Graph检索探针确认 retrieval 的父节点为 search_reference，HITL终态为handed_off/handoff；本期保持只读/持续人工权限，不补造商业执行。见 [AC052/检索日志](artifacts/phase11/final-review-ac052-retrieval.log)、`backend/tests/test_observability.py:55–80,123–135`。 |
| REQ-013:517：模型/Prompt/知识/政策版本、来源、结果/错误/耗时及usage | 完整实现。`backend/src/globalmail_agent/observability/snapshot.py:17–53` 从当前context/节点/usage账本投影ID、版本hash、真实时间和终态；`agent/budget.py:48–69,82–101` 保留唯一预留/结算路径，导出器不新增用量账本；`observability/usage.py:7–10` 费用null。真实两run的7个generation与本地账本精确一致，见 `actual-qwen-observation.json:1` 及 `backend-hierarchy-single-restore.json:20–76`。 |
| REQ-013:518：业务持久化、前端恢复与观测职责 | 完整实现。`backend/src/globalmail_agent/application/commit_outcome.py:105–118` 保存业务artifact、run、job、cycle及事件；`observability/records.py:76–98` 在业务事务后保存安全缓冲，失败只标观测降级；`api/observability.py:9–19` GET只读。独立故障/恢复验证只产生一次合法回复，模型数及usage不增加，见 [恢复日志](artifacts/phase11/final-review-sdk-recovery.log)、[四竞态日志](artifacts/phase11/final-review-faults.log)。 |
| REQ-013:519 / AC-050：字段控制、SDK前正文/媒体禁出站，正常与异常隐私 | 完整实现。`backend/src/globalmail_agent/observability/media_filter.py:4–65` 仅允许UUID、固定枚举、hash及非负计数；`tracing.py:24–30,39–59` 不复制原模型输入/返回或异常正文；`sdk_export.py:82–86` 在任何SDK包装器/媒体遍历前复核；`:91–108` 使用隔离Context，不继承第三方传播内容。`transport.py:36–72` 仅向SDK返回固定安全Response，原reason/body/异常对象留在传输边界内。独立真实SDK测试覆盖原图bytes、data URL、外链、邮箱/假密钥、原异常及HTTP服务body哨兵，见 `backend/tests/test_observability_sdk.py:113–151,160–190` 与 [17项日志](artifacts/phase11/final-review-sdk-recovery.log)。真实图文UI I/O为空，见 [attachment receipt](artifacts/phase11/phase11-final-review-langfuse-child.png)。 |
| REQ-013:520 / AC-051 / FT-12：失败不阻塞/回滚业务，不重跑，不双计 | 完整实现。`backend/src/globalmail_agent/observability/exporter.py:13–16,23–32,35–97,124–144` 有界run ID队列、有限重试和受限flush；`settings.py:26–29` 设队列/HTTP/尝试/flush上限。独立真实SDK/PG故障恢复与四竞态通过。额外实际PG/Graph/官方SDK/loopback503的FT12明确为ScriptedModel工程fixture：reply_and_wait完成、SDK POST=1、模型3次及usage不变、ack_unknown/degraded且无trace链接，见 `ft12-actual-app.json:1–30` 及 [独立真实故障页面](artifacts/phase11/phase11-final-review-runtime-light.png)。 |
| 主架构:457：v4不可变观测、单发送/接受未知恢复 | 完整实现。`backend/src/globalmail_agent/observability/records.py:116–128` 在发送前持久CAS登记ack_unknown；`exporter.py:48–97` 仅确定未发送/明确拒收有限重试，未知则核对；`sdk_export.py:150–192` 通过有界时间v2 observations确认完整唯一ID集合；`transport.py:41–72` 阻断SDK自动重试并兼容events_only JSON及protobuf partial rejection。独立503/429每次仅一POST、ReadTimeout/ConnectTimeout、接受后响应丢失、重复/不完整集合、接受后mark失败、并发均通过；原重复FAIL仍保留。该协议符合 [官方不可变观测说明](https://langfuse.com/faq/all/tracing-data-updates)。 |
| REQ-013:521 / Phase11任务1：独立配置、凭据、卷及镜像 | 完整实现。`scripts/init-observability.ps1:6–27,36–47` 随机私有凭据并保旧；`observability-common.ps1:14–35,54–73` 限制ACL及项目/端口；`start-observability.ps1:1–7`、`stop-observability.ps1:1–8` 只操作独立项目且保卷。本轮独立test-observability检查六服务healthy、digest、项目/卷/端口、匿名401与实际登录；已有停启证据 `observability-preservation.json:1–18` 核对凭据/5卷/trace/业务PG不变。本审没有为重测保留而停止服务。 |
| REQ-013:522：业务断言/人工核对，不以模型自评替代；新run独立trace | 完整实现本期工程要求。`backend/tests/test_observability.py:1` 明确scripted outputs；`scripts/verify-observability.py:102–140` 核对真实远端ID、父关系、usage与敏感标记，不采用模型自评。真实Qwen两次业务失败保留，本审只验证其实际观测。`observability/snapshot.py:14–24` 保存历史parent_run关联；独立AC052探针证明新run/trace及最新事实，不能据观测PASS勾选82AC。辅助readback-only保证的缺口另见F11-VERIFY-03。 |
| AC-049：多工具、意图/检索/模型/工具/结果关联，无重复累计 | 工程关联完整。实际Qwen文本5模型/4工具、18观测/5generation、16798输入/1253输出；图文2模型、7观测/2generation、6850输入/1862输出。`actual-qwen-observation.json:1` 的ID唯一、父关系逐项匹配与usage_projection均true；独立真实检索探针补检索分支，`agent/tool_gateway.py:143–149`。父图修复后仅清理本期两个隔离trace至v2零确认并由原safe buffer单次恢复，7usage及五业务表hash完全不变（`backend-hierarchy-single-restore.json:1–76`）。 |
| AC-052：HITL后新客户来信、最新事实、新trace、不重放 | 完整工程验证。独立重跑真实PG探针：人审期间来信/人工回复不排新job，下一来信取最新人工回复/备注/客户事实，新trace不同、parent_run为旧run、conversation相同，仅新增一次合法Agent回复。代码 `worker/agent_runner.py:72–95`、`observability/snapshot.py:14–24`、`application/commit_outcome.py:66–118`；[独立2项原始日志](artifacts/phase11/final-review-ac052-retrieval.log)。 |
| 任务2–3：作用域/撤销/删除/knowledge/generation围栏与清理依赖入口 | 完整实现本期入口。`backend/src/globalmail_agent/observability/records.py:18–54` 校验workspace、完整scope、生命周期、branch_generation、对象祖先deletion_journal、图片撤销及knowledge epoch；`:85–92` 登记安全缓冲及来源依赖，`:146–148` 提供停写入口。`migrations/versions/0011_observability.py:12–26` 为export_object_id建立复合作用域FK。独立generation/revoke/knowledge撤回验证通过；完整远端删除与联合恢复仍属Phase12。 |
| 任务3 / REQ-009：独立运行台入口、真实六状态与异步失效 | 完整实现。`frontend/src/views/agent-runs/index.vue:48,66–69` 仅给当前run加入状态行；`api/observability-api.ts:12–41` 校验run、hex trace及本机合法路径，拒外链/凭据/query/hash；`ObservabilityStatus.vue:2–10,19–25` 展示六状态并处理KeepAlive。`use-agent-console.ts:13,24,72` 独立traceRevision；`useConversationEvents.ts:26` 在去重刷新前同步失效；`use-run-observability.ts:12–28` sync watcher/generation拒晚到。独立production Vue/Router/KeepAlive4项通过，实际成功链接点击后打开正确本机trace；[去敏成功概览](artifacts/phase11/phase11-final-review-runtime-exported-safe.png)。未恢复旧AgentRunPanel或测试页面。 |
| 任务5：0010→0011正式保旧及当前源码启动 | 已有增量迁移/正式保旧证据。`migrations/versions/0011_observability.py:12–26` 只新增五列和作用域FK；`adapters/database.py:9` 要求0011。`formal-backup.json:1–11` 为pg_restore-list实证、465744bytes、70对象及受限ACL；`formal-preservation.json:1–85` 为77旧表既有列/行hash、objects/settings不变且无排除列；`formal-final-ready.json:1–6` API/proxy/预览/Langfuse均200。本审读取最终启动/保旧证据，没有重启或添加正式测试邮件。任务5的最终全量和fresh审查门尚未完成。 |

### 部分实现 / 未完成边界

- **F11-VERIFY-03的辅助readback-only行为待修复后重审**。生产观测功能已有上述证据；辅助验证脚本在审查时没有达到“只读取、不导出”的保证。位置与影响见Stage2。
- **451项最终全量未完成**：本报告读取 `docs/verification/artifacts/phase11/backend-full-tests.log` 仍为逐项进行日志，未见最终summary/source-freeze，不给整体交付PASS。
- **真实业务语义未通过**：`actual-qwen-observation.json:8–10` 的文本reply_citation_invalid及该文件图文understanding_schema_invalid保持；本期没有新模型调用替换其结果。
- **Phase12/13未实施**：`observability/records.py:146–148` 只提供停读/停写入口；完整删除、联合恢复、全业务及模型质量验收继续延期。本期没有确认新增交易/履约范围。

## Stage 2：Code Quality

### 确认问题

**MEDIUM F11-VERIFY-03：验收脚本的 existing-report 分支在读取既有报告前启动异步导出恢复，不能保证readback-only。**

- 要求：本期材料及验收文档要求只读核对既有真实run，不发送新span、不重新执行业务/模型；当前 `docs/planning/PHASE-11-IMPLEMENTATION.md:26` 已补明确合同。
- 审查时原 `scripts/verify-observability.py:164–165` 执行顺序为 `observer.start()` → `if args.existing_report:`。`backend/src/globalmail_agent/observability/service.py:16–17` 启动TraceExporter；`exporter.py:99–104` 启动时枚举pending并调用 `export_one(..., recovering=True)`；`:35–82` 可对尚未发送的pending缓冲实际POST。
- 实际差异：已有报告模式虽不进Graph，但仍可能导出同schema中其他pending run，超出只读验证范围。当前两真实trace已exported，没有证据表明本次已发生额外发送；问题是代码保证不成立，不将其描述成已发生重复计量或业务重跑。
- 修前代码片段：

```python
try:
    observer.start()
    if args.existing_report:
        # Read local receipts and remote observations.
        ...
```

- 主Agent确认并先补源合同，再把start移动到新run的else分支；当前 `scripts/verify-observability.py:164–183` 可见修改。**这次修改在本轮独立验证之后，未在本报告重验，不给新版脚本PASS。**
- 闭合标准：fresh从Stage1核对只读分支，并以真实既有run读回；对ObservabilityService.start、Graph/模型调用和SdkExport.send设置fail-fast，确保均未调用；编译改后脚本；最终451全量和source-freeze也必须完整结束。修复由主Agent执行，本审不修改源码。

### 已检查且没有新增阻塞问题

| 维度 | 本次结论与证据 |
|---|---|
| F11-OBS-02父树修复 | 已闭合本轮独立检查。`backend/src/globalmail_agent/observability/sdk_export.py:124–145` 按父依赖拓扑，时间只排序可创建节点；缺父/循环/重复或低64碰撞拒绝。`tests/test_observability_sdk.py:87–111` 真实HTTP/protobuf验证child-first同起点仍挂实际父；独立 [低64碰撞探针（18–35行）](artifacts/phase11/final-review-identity-probe.py) 在SDK media traversal前拒绝。`scripts/verify-observability.py:112–122` 核对metadata父UUID对应actual parent span ID，真实图文截图显示attachment_prepare位于understanding内。原 `PHASE-11-REVIEW.md` 和 `actual-qwen-parent-failure.json` 仍FAIL。 |
| 原传输异常链隐私边界 | 已闭合本轮独立检查。`transport.py:36–72` 向SDK返回新建固定safe Response，没有原响应对象、reason/body、request、raw异常context；`tests/test_observability_sdk.py:178–190` 独立实跑验证原异常/服务body哨兵未进入返回对象；`:160–176` 验SDK日志无哨兵且只一次调用。 [17项原始日志](artifacts/phase11/final-review-sdk-recovery.log) 全部通过。 |
| F11-FE-01前端撤销链接 | 已闭合本轮独立检查。`useConversationEvents.ts:26` 在业务读取挂起/失败前独立失效；`use-run-observability.ts:12–28` 与组件KeepAlive处理阻止旧入口复活。独立 `frontend/scripts/observability-events.test.ts:18–105` 用生产composable、Vue renderer、memory router及KeepAlive，覆盖连续SSE、业务读取挂起/异常、离页及晚到恢复；[4项日志](artifacts/phase11/final-review-frontend.log)。 |
| 命名、结构、类型、文件大小 | 本期生产观测按recorder/snapshot/scoped records/transport/exporter拆分；`sdk_export.py:1–199`、`records.py:1–148`、`agent/graph.py:1–276` 均≤300行。新TS入口从unknown显式校验（`api/observability-api.ts:14–34`），没有新增any。未发现新的重复计量路径或多职责大文件；git diff --check退出0，仅既有换行格式提示。 |
| 测试真实性 | 真实SDK用本机HTTP/protobuf而非只断言mock构造参数；真实PG覆盖持久CAS、作用域和撤销；新前端测试用生产Vue生命周期，不只测纯函数。四额外PG探针核验generation变更、HTTP中撤销、接受后mark失败及并发单发送，全部通过。FT12实际SDK503页面有真实业务完成，明确为engineering fixture。辅助readback-only缺少行为防护/反例由F11-VERIFY-03确认，故本维度整体仍FAIL。 |
| 安全扫描 | 新观测/API/前端及观测脚本中未发现eval、危险HTML、前端KEY/SECRET/TOKEN变量、硬编码真实凭据。`settings.py:32–48` 和 `frontend/api/observability-api.ts:23–28` 限本机路径；`scripts/local-common.ps1:40–54` 白名单导入私有env，`start-local.ps1:43–52` 启Vite前移除模型/观测凭据；git check-ignore确认三个私有env/gui-state文件忽略。测试固定合成标识不作真实密钥泄漏。 |
| Spec漂移 | 仅新增只读观测GET（`api/observability.py:9–19`）、既有trace表五列、安全buffer依赖和独立运行台状态行，对应REQ013与任务1–3。`application/commit_outcome.py:66–83` 持续人工/只读权限仍在；没有新增测试控制台、在线prompt替换或交易写工具。新readback-only合同是澄清既有验证范围，修复待fresh核验。 |
| 实际视觉与邻居对比 | 已独立实际打开1440亮色、1280暗色运行台和邮件邻居并查看截图：[亮色运行台](artifacts/phase11/phase11-final-review-runtime-light.png)、[亮色邮件](artifacts/phase11/phase11-final-review-mail-light.png)、[暗色运行台](artifacts/phase11/phase11-final-review-runtime-dark.png)、[暗色邮件](artifacts/phase11/phase11-final-review-mail-dark.png)。相同Art侧栏、顶栏、字体、主题/卡片、按钮及间距；新增状态行可读，日志未混入邮件。`ObservabilityStatus.vue:2–10` 使用现有组件/主题变量；本结论以渲染图为证，不按类名数量判断。 |

## 独立验证与编译原始结果

### SDK / PG恢复

命令：`globalmail-agent/backend/.venv/Scripts/python.exe tmp/run-refactor-tests.py test_observability_sdk test_observability_recovery`。完整 [原始日志](artifacts/phase11/final-review-sdk-recovery.log)，退出0：

```text
----------------------------------------------------------------------
Ran 17 tests in 31.160s

OK
SUMMARY 17 failures 0 errors 0 skipped 0
```

独立补充AC052/检索探针完整 [日志](artifacts/phase11/final-review-ac052-retrieval.log)，退出0：

```text
test_human_reply_and_new_input_have_new_trace_and_latest_facts ... ok
test_actual_search_receipt_and_withdrawal_export_fence ... ok
----------------------------------------------------------------------
Ran 2 tests in 10.566s

OK
```

独立四竞态探针完整 [日志](artifacts/phase11/final-review-faults.log)，退出0：

```text
test_generation_revokes_pending_without_rerun ... ok
test_revoke_during_send_wins_over_http_success ... ok
test_crash_after_acceptance_resolves_existing_receipt_without_resend ... ok
test_concurrent_export_claim_sends_once ... ok
----------------------------------------------------------------------
Ran 4 tests in 13.591s

OK
```

独立低64bit UUID碰撞探针，退出0，完整 [输出](artifacts/phase11/final-review-identity.log)：

```text
PASS: distinct UUIDs with identical low64 are rejected before SDK media traversal
```

### 前端生产交互

命令：`pnpm exec tsx --test --test-concurrency=1 scripts/observability*.test.ts`，退出0，完整 [日志](artifacts/phase11/final-review-frontend.log)：

```text
✔ 生产SSE撤销在其他读取失败或挂起时立即清追踪；KeepAlive离页拒绝晚到 (683.4216ms)
✔ 仅接受当前运行的真实本地追踪入口，拒绝外链、凭据及伪造成功 (3.2271ms)
✔ 切换运行立即清空旧入口，晚到成功不能串会话 (6.3847ms)
✔ 观测请求失败可重试，离页后晚到响应不恢复入口 (1.1193ms)
ℹ tests 4
ℹ suites 0
ℹ pass 4
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 1820.853
```

### 部署

独立 `pwsh -File globalmail-agent/scripts/test-observability.ps1`，退出0，完整 [日志](artifacts/phase11/final-review-deployment.log)：

```text
clickhouse healthy; image locked; project isolated
langfuse-web healthy; image locked; project isolated
langfuse-worker healthy; image locked; project isolated
minio healthy; image locked; project isolated
postgres healthy; image locked; project isolated
redis healthy; image locked; project isolated
HTTP health OK; authenticated project globalmail-agent-local; anonymous rejected (401); UI login OK
```

### 编译与已有全量证据

- 独立后端：在backend执行 `.venv/Scripts/python.exe -m compileall -q src migrations`，退出0；**原始stdout/stderr为空**。没有覆盖本报告后续改动的验收脚本。
- 独立前端：`pnpm exec vue-tsc --noEmit`，退出0；**原始stdout/stderr为空**。
- 独立依赖：`uv pip check --python .venv/Scripts/python.exe`，退出0，原始输出：

```text
Checked 70 packages in 2ms
All installed packages are compatible
```

- 已读取主Agent [前端构建完整原始输出](artifacts/phase11/frontend-build-before-loading-fix.log)，开头/结尾如下；本审独立补跑vue-tsc，没有重复Vite全量：

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

- 已读取主Agent [前端90项完整日志](artifacts/phase11/frontend-tests-before-loading-fix.log)，原始结尾为90 tests、90 pass、0 fail、0 skipped、15788.7825ms。
- **后端451项全量尚未结束**，本报告不提供最终通过或source_changed=false结论。F11-VERIFY-03修复后还需脚本编译/只读行为验证及fresh审查，不能由上述通过项代替。

## 交接与清理

独立浏览器仅使用 `phase11-final-review`，已关闭；不再读取或使用私有gui-state。本审的UUID测试schema/objects由fixture清理，自己的 `tmp/phase11-final-review-*` 及8张重复output截图已精确清理；去敏截图及探针/原始日志保存于本报告引用的artifacts。共享15178/18188隔离服务仍交主Agent保留，正式15173/18080、15175预览及3001观测未被本审停止。

主Agent按Stage2辅助缺陷完成修复及验证，然后重新派fresh reviewer从Stage1起闭环；新报告保留本报告FAIL。最终451项/冻结、正式保旧、清理和本地Git仍由主Agent负责。真实模型质量及完整删除/恢复继续归Phase13/12，不提前关闭产品AC。
