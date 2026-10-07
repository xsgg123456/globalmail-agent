# Phase 2 最终独立审查

日期：2026-10-07。审查角色：fresh code-reviewer；依据 `.agents/skills/code-review/SKILL.md` 两阶段执行。结论：**Stage 1 通过；Stage 2 通过，未发现本阶段阻塞缺陷。** 该结论只覆盖运行基础及前端外壳，不代表产品 82 项 AC 或 Phase 1 图片业务通过。

审查范围：`globalmail-agent/backend/`、本轮前端变更、`infra/`、`scripts/`。下表路径均相对仓库根目录；`B` 表示 `globalmail-agent/backend`，`F` 表示 `globalmail-agent/frontend`，`S` 表示 `globalmail-agent/scripts`。审查未改源码、未提交、未调用模型、未重启服务。主线程负责进度及索引文档同步。

## Stage 1：Spec Compliance

逐项依据：`DEV-PLAN.md:71` 的全部 Phase 2 交付及验收条件，`Product-Spec.md:705` 的密钥/访问条件、`:765` 的 ASM-008，`AGENT-ARCHITECTURE.md:301`、`:339`、`:384`，以及 `PHASE-2-VALIDATION.md:5` 的四项实施标准。

| 条目 | 结论及代码证据 | 验证证据 |
|---|---|---|
| 正式 FastAPI 工程、固定依赖 | 完整实现：B/pyproject.toml:1；B/src/globalmail_agent/main.py:15 | 独立运行后端导入/12 测试及依赖兼容检查通过 |
| 迁移、独立 PG 持久卷 | 完整实现：B/migrations/versions/0001_runtime_foundation.py:67；B/migrations/env.py:10；globalmail-agent/infra/compose.yaml:1 | 6 个真实 PG 测试逐次建立随机 schema；重复升级成功。Compose 项目名、127.0.0.1 绑定和命名卷已核对 |
| 安全状态接口、参数校验、统一错误 | 完整实现：B/src/globalmail_agent/api/system.py:10；api/envelope.py:4；main.py:30 | 三接口直连及代理共 6 次 HTTP 200，code 均为 200；缺 DB/缺表/对象目录故障返回 503；422/404/500 不回显秘密标记 |
| 密钥只在服务端读取 | 完整实现：B/src/globalmail_agent/settings.py:31；api/system.py:24；S/start-local.ps1:35 | runtime 仅返回 model_configured；前端子进程启动前清除模型及 DB 环境；API 测试秘密标记不泄漏 |
| 既有前端锁、布局和主题 | 完整实现：F/vite.config.ts:32；F/src/router/modules/mail-agent.ts:3；F/src/App.vue:1 | pnpm-lock.yaml 与 Git 基线无差异；vue-tsc + Vite 实际构建通过；独立浏览器查看三页，见视觉记录 |
| 本地入口、导航、消除模板登录依赖 | 完整实现：F/src/router/guards/beforeEach.ts:13；F/src/router/routes/staticRoutes.ts:1；F/src/components/core/layouts/art-header-bar/widget/ArtUserMenu.vue:1 | 打开根 URL 直接进入 workbench；菜单只有邮件工作台、知识库、系统状态；页签清理测试通过，不注入伪 Token |
| 真实空态及引导 | 完整实现：F/src/views/mail-agent/index.vue:8；F/src/views/knowledge/index.vue:3 | 页面明确“尚未接入”“将在会话/知识阶段开放”；没有假邮件、业务单或假成功操作 |
| 对象存储、来源及作用域 | 完整实现：B/src/globalmail_agent/adapters/object_store.py:17、:62、:92 | 服务端 UUID；50 MiB 上限；原子落盘、摘要/长度校验；五个 scope 维度逐项测试读拒绝与派生写拒绝 |
| 内容依赖原子登记 | 完整实现：B/src/globalmail_agent/application/content_dependencies.py:8；adapters/object_store.py:78；adapters/schema.py:37 | 元数据及依赖同一事务；复合 FK 覆盖来源和目标；跨 scope 故障后对象行和文件未残留；真实 PG 断言通过 |
| 删除 journal 基础 | 完整实现本阶段基础：B/src/globalmail_agent/adapters/schema.py:50 | 表含 scope、目标、正 generation、状态约束与唯一性；schema readiness 检查包含该表。没有上传或删除完成 API |
| 页面显示真实运行状态 | 完整实现：F/src/hooks/core/useRuntimeStatus.ts:25；F/src/components/business/runtime-status.vue:11；F/src/api/runtime-contract.ts:10 | 实际页面显示 DB/schema/object 就绪及“模型已配置，未验证连接”；503 严格契约测试通过；错误清空旧状态并给重试 |
| 重启持久数据 | 完整实现：Compose:11；S/check-runtime.py:26 | 本审独立测试引擎重新连接后读回；另核读 tmp/phase2-runtime-check.json 的实际容器重启 PASS 及对应脚本：随机 schema 中写 ObjectStore，重启后读回正文和登记元数据，最终清理。容器重启由主线程执行，本审未重复 |
| 本机绑定及 Host/Origin | 完整实现：B/src/globalmail_agent/api/security.py:21；F/scripts/local-access.ts:4；S/start-local.ps1:33 | 独立实际请求：API 非法 Host 400、非法 Origin 403；前端两者 403；源码无默认公网绑定 |
| 冲突提示及隔离停止 | 完整实现：S/local-common.ps1:15、:50；S/stop-local.ps1:3 | 独立占用端口测试明确拒绝；错误创建时间不终止进程；真实 JSON 往返后正确停止独立 Node 测试进程；只操作本项目 Compose，不 down -v |
| 不修改原前端、其他项目 | 本轮源码路径及脚本均在本仓库；S/local-common.ps1:22 固定 Compose 项目；F/FRONTEND-BASELINE.md:3 声明独立副本 | 本审未访问修改源项目或其他容器；未把“未现场比较源目录全部哈希”写成已验证 |

**部分实现/未实现的合法延期**：架构 §7 的知识解析、发布、撤销、彻底删除/联合恢复，§8 的会话/人审/业务 API，以及 §9 的 Langfuse/worker 未在 Phase 2 交付；依据 DEV-PLAN.md:85 起的后续阶段及 :316 的“Phase 2 提供运行基础”归属，不作为本次缺失。UI/API 能力标志准确为 false（api/system.py:28）。完整删除 journal 外置最新副本、孤儿清理任务仍在后续生命周期阶段，不声称本阶段完成删除。

**Spec 漂移**：未发现新增未授权业务。系统状态详情页对应架构 §8.2 系统状态；空工作台三栏对应 ASM-008。保留模板源码不是开放模板业务，路由仅导出本地三页（F/src/router/modules/index.ts:1）。

## Stage 2：Code Quality

| 检查 | 结论与证据 |
|---|---|
| 类型、职责、规模 | 新增后端源文件最大 107 行（ObjectStore），脚本最大 96 行（check-runtime.py）；三新增页面 28/13/5 行。新增 TS 使用 unknown/接口而非 any（F/src/api/runtime-contract.ts:7）；路由、HTTP、UI hook 与状态组件分开。既有模板超长文件不作为新增质量缺陷 |
| 安全扫描 | 针对本轮后端、脚本、运行契约/hook/页面扫描 eval、innerHTML、密钥前缀、VITE 密钥和 any，无命中。SQL 值使用 SQLAlchemy 参数化（adapters/object_store.py:79、:97），schema DDL 的插值仅来自测试内部 uuid4().hex（B/tests/test_postgres.py:23），不含用户输入 |
| 错误与资源清理 | main.py:30、security.py:57 返回安全分类；对象失败回滚清理见 object_store.py:85；数据库会话由 context manager 管理；启动脚本 finally 还原父环境（S/start-local.ps1:62） |
| 测试真实性 | 真实 PG 测试使用生产迁移、真实 FK 与生产 ObjectStore（B/tests/test_postgres.py:20），没有 SQLite 替身；检查每个 scope 维度及失败后文件/行清理。停止测试现覆盖 JSON 持久化前提（S/test-local.ps1:28），修正了仅内存对象测试的盲点 |
| 前端契约回归 | F/scripts/runtime-contract.test.ts:10 明确验证 200 成功、503 降级、code=0 错配拒绝；与实际六次 HTTP 结果相互印证。旧初审 code=0 问题已关闭（B/src/globalmail_agent/api/envelope.py:6） |
| 视觉与邻页对比 | 独立 CUA 打开 1280×720 工作台、知识库、系统状态并查看截图；共享左侧导航、顶栏、页签、浅色背景、圆角白色容器及空态风格一致。工作台三栏无重叠，状态详情请求 ID 换行可读。对应 F/src/views/mail-agent/index.vue:4、knowledge/index.vue:2、components/business/runtime-status.vue:2。无独立设计稿/Brief，也未启动原 Art Design Pro 基线，因此结论为当前相邻页面与保留组件一致，不宣称原版逐像素一致 |

**安全问题：本阶段未发现 HIGH/MEDIUM。** 此结论不涵盖尚未开放的业务上传、模型工具与生命周期授权。

测试边界：前端自动测试当前覆盖契约/页签纯逻辑，没有完整组件交互自动测试；本审补了实际三页导航及渲染，主线程另做 API/DB 停机、重试恢复。该人工故障证据应由主线程写入阶段验证报告。1440×900、完整键盘与所有主题矩阵属于后续完整 UI 验收，本报告不提前标通过。

## 独立命令和原始输出

后端执行：从忽略的本地 settings 读取 URL 到 GLOBALMAIL_TEST_DATABASE_URL（不输出），PYTHONPATH=src；`uv run python -m unittest discover -s tests -v`、`uv pip check`、`uv run python -m compileall -q src migrations`。原始输出：

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
test_bad_hosts_and_origins_rejected (test_api.ApiTests.test_bad_hosts_and_origins_rejected) ... ok
test_live_and_safe_runtime (test_api.ApiTests.test_live_and_safe_runtime) ... ok
test_non_local_config_rejected (test_api.ApiTests.test_non_local_config_rejected) ... ok
test_preflight_and_write_protection (test_api.ApiTests.test_preflight_and_write_protection) ... ok
test_readiness_degraded_without_database (test_api.ApiTests.test_readiness_degraded_without_database) ... ok
test_validation_and_exceptions_are_sanitized (test_api.ApiTests.test_validation_and_exceptions_are_sanitized) ... ok
test_database_failure_and_missing_table_are_degraded (test_postgres.PostgresTests.test_database_failure_and_missing_table_are_degraded) ... ok
test_every_scope_dimension_is_enforced (test_postgres.PostgresTests.test_every_scope_dimension_is_enforced) ... ok
test_migration_repeat_restart_and_ready (test_postgres.PostgresTests.test_migration_repeat_restart_and_ready) ... ok
test_missing_schema_and_unwritable_store_degraded (test_postgres.PostgresTests.test_missing_schema_and_unwritable_store_degraded) ... ok
test_path_and_digest_protection (test_postgres.PostgresTests.test_path_and_digest_protection) ... ok
test_source_dependency_and_scope_database_constraint (test_postgres.PostgresTests.test_source_dependency_and_scope_database_constraint) ... ok
----------------------------------------------------------------------
Ran 12 tests in 3.094s
OK
Checked 24 packages in 1ms
All installed packages are compatible
```

compileall 无输出，退出码 0。弃用提示来自锁定的测试工具组合，未改变依赖。

前端执行 `pnpm exec tsx --test scripts/runtime-contract.test.ts scripts/local-tabs.test.ts`、`pnpm build`，均退出码 0。以下为原始输出的摘要摘录（省略逐资产大小列表）：

```text
✔ 清理已持久化的模板页签，保留业务页签和其参数 (1.0222ms)
✔ 接受实际HTTP200存活与503依赖故障 (1.0674ms)
✔ 拒绝假成功、失配状态及非法配置 (0.27ms)
✔ 运行配置仅接受当前阶段实际能力标志 (0.1182ms)
ℹ tests 4
ℹ suites 0
ℹ pass 4
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 240.2917
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3235 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 25.89s
```

修复停止时间比较后再次独立执行 `pwsh -File globalmail-agent/scripts/test-local.ps1`：

```text
本机配置已存在，保留原密码及端口。
PASS 重复初始化保留凭据
PASS 端口冲突明确拒绝
PASS 进程创建时间校验、JSON登记往返及停止
```

独立实际 HTTP：18080 与 15173 各自 live/ready/runtime-config 均 200；ready 数据均为 `{status:"ready",database:"ready",schema:"ready",object_store:"ready"}`；runtime 均为 `{mode:"local_single_user",phase:2,features:{conversations:false,knowledge:false,agent:false},model_configured:true}`。每次均带非空 request_id，未返回连接串/Key。非法访问原始结果：

```text
http://127.0.0.1:18080 Host 400
http://127.0.0.1:18080 Origin 403
http://127.0.0.1:15173 Host 403
http://127.0.0.1:15173 Origin 403
```

## 交接

无需源码修复。主线程在阶段关闭前同步 DEV-PLAN、主架构实现状态、文档索引、SESSION-HANDOFF 与 PHASE-2-VALIDATION 的最终命令/人工故障证据；它们在本审读取时部分仍写“未开始/待填”，本次派发已明确由主线程负责。不得改写历史初审结论或把本报告转译为后续业务验收通过。

