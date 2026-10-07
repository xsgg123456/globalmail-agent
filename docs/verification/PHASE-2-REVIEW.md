# Phase 2 独立代码初审

日期：2026-10-07。范围：DEV-PLAN.md:71–84 的运行基础与前端外壳；基线为 Phase 1 提交 `68de83f` 后正在集成的工作区。审查使用 `.agents/skills/code-review/SKILL.md`，未改业务代码、未提交、未启动其他项目。

**初审结论：Stage 1 发现 1 项 HIGH，Stage 2 未执行。** 主线程要求保留本次初审后结束，由 fresh 实例在完整实现后重新审查。结束时已观察到后端成功码修正，但尚未进行修正后的真实浏览器集成复验，不能凭改动关闭问题。本报告不是最终实现验收。

## Stage 1 — Spec Compliance

### HIGH-01：成功响应码不一致，真实正常状态被前端当作失败

- 要求：DEV-PLAN.md:84，“启动后页面可访问并显示 API/数据库实际状态”；PHASE-2-VALIDATION.md:8 要求加载、故障、重试及真实未接入状态可见。
- 初审证据：`globalmail-agent/backend/src/globalmail_agent/api/envelope.py:6` 当时为 `"code": 0 if status < 400 else status`；`globalmail-agent/frontend/src/utils/http/index.ts:22` 要求 `body.code === response.status`。因此 HTTP 200 / code 0 必然在前端抛错。`src/hooks/core/useRuntimeStatus.ts:41` 至 :48 将这三个拒绝显示为状态请求失败，正常 API/数据库不能显示就绪。
- 修正建议：统一并文档化成功码，加入成功与 503 响应的前后端契约测试；真实页面检查三个状态接口成功、数据库故障和重试恢复，不能只用各端独立测试证明集成成功。
- 结束时状态：后端同位置已改为 `"code": status`。**待 fresh 复审验证关闭**，保留以上原始发现。

### 逐项覆盖

| Phase 2 条目 | 初审结果与证据 |
|---|---|
| FastAPI 正式工程与锁依赖 | 已实现基础工程：`backend/pyproject.toml:1`、`backend/src/globalmail_agent/main.py:14`；后端 10 项测试成功导入并运行。依赖冻结安装本次未重新执行，不声称已独立验证安装。 |
| live / ready / runtime-config | 后端已实现：`backend/src/globalmail_agent/main.py:43`、`:47`、`:58`；测试证明 live、无数据库降级、schema 缺失/不可写对象目录降级。前后端集成不通过，见 HIGH-01。 |
| 参数校验、统一安全错误和 request_id | 已实现：`backend/src/globalmail_agent/main.py:29`、`backend/src/globalmail_agent/api/envelope.py:4`；`backend/tests/test_api.py:55` 实测 422 / 404 / 500 不返回秘密标记。 |
| Host / Origin 与跨源写保护 | 后端已实现：`backend/src/globalmail_agent/api/security.py:21`；`backend/tests/test_api.py:40`、`:46` 验证非法 Host/Origin、无 Origin 写入及非 JSON 拒绝。前端有 guard：`frontend/scripts/local-access.ts:4`，其真实 HTTP 验证待集成复审。 |
| Key 仅服务端读取、不返回连接串 | 已实现配置分离：`backend/src/globalmail_agent/settings.py:10` 与 `main.py:58` 仅投影配置标志；`backend/tests/test_api.py:24` 秘密标记未返回。`scripts/start-local.ps1:35` 启动前端前清除已导入的后端凭据。完整安全扫描属于未执行的 Stage 2。 |
| PostgreSQL 迁移与独立持久卷 | 迁移已实现：`backend/migrations/versions/0001_runtime_base.py:69`；独立项目及卷：`infra/compose.yaml:1`、`:11`、`:13`。真实 PG 隔离 schema 测试通过，重复升级和重新建立连接后对象仍可读（`backend/tests/test_postgres.py:52`）。**测试中的 restart 是 engine.dispose 后重连，并非容器重启；容器重启持久性仍待主线程实测。** |
| 受控对象、摘要、来源与完整 scope | 已实现：`backend/src/globalmail_agent/adapters/object_store.py:17`、`:26`、`:62`、`:92`；真实 PG 测试证明越界客户读取失败、路径输入拒绝及内容篡改拒绝。源码在审查中继续修改，行号取初审末读取位置。 |
| 内容依赖同 scope 与原子登记 | 已实现数据库约束：`backend/src/globalmail_agent/adapters/schema.py:41`、`:44`；`backend/tests/test_postgres.py:64` 证明跨客户依赖的直接 SQL 被 FK 拒绝，派生对象失败时无文件/对象登记残留。其余 scope 维度的新测试于初审结束前加入，未计入本次 10 项结果。 |
| 删除 journal 基础表 | 基础表已实现：`backend/src/globalmail_agent/adapters/schema.py:50`，含 scope、generation、state 与唯一约束。没有提前开放删除 API；Phase 12 删除流程不纳入本次缺陷判断。 |
| 既有前端锁文件、布局和主题 | `frontend/package.json:12` 执行类型检查+构建，本次构建退出 0。`scripts/start-local.ps1:24` 使用 `--frozen-lockfile --ignore-scripts`；本次未重新安装。布局经 `frontend/src/router/modules/mail-agent.ts:6` 指向既有容器。视觉是否匹配尚未实际截图核对。 |
| 本地单用户入口、无演示登录/用户依赖 | 静态实现完整：`frontend/src/router/guards/beforeEach.ts:14` 注册三页并清理旧页签/令牌，`:26` 首页进入工作台；`frontend/src/router/routes/staticRoutes.ts:2` 仅保留 404。浏览器网络验证待完成，不将静态检查写成实测通过。 |
| 工作台 / 知识 / 系统状态导航 | 静态实现完整：`frontend/src/router/modules/mail-agent.ts:9`、`:15`、`:21`；状态页受 HIGH-01 阻塞。 |
| 未接业务的引导真实性 | 匹配阶段范围：`frontend/src/views/mail-agent/index.vue:9`、`:15`、`:19` 与 `frontend/src/views/knowledge/index.vue:4` 明确尚未接入，无假成功动作。Phase 3–13 业务缺失不计缺陷。 |
| 仅本机监听、端口冲突 | `scripts/start-local.ps1:13`、`:14`、`:17` 检查端口；`:34`、`:44` 只绑定本机；`infra/compose.yaml:11` 同样只发布本机。`scripts/local-common.ps1:15` 的冲突路径独立实测通过。 |
| 停止仅本项目 PID、保留持久数据 | `scripts/local-common.ps1:50` 校验 PID 与创建时间再终止；`scripts/stop-local.ps1:10` 使用 Compose stop，未删除卷。独立测试证明错误创建时间不终止进程、正确记录可终止；完整应用停止/启动集成待验。 |
| 不触碰其他项目 / 原前端目录 | `scripts/local-common.ps1:22` 固定本项目 Compose 名称，安装路径为本项目子目录（`scripts/start-local.ps1:4`、`:5`）。审查命令仅操作本项目测试 schema、临时目录与副本构建，未重启数据库或操作源 Art Design Pro。跨项目运行前后快照由主线程补证。 |

### Spec 漂移与 UI

未发现运行导航额外开放业务页面：只注册三页（`frontend/src/router/modules/index.ts:1`、`modules/mail-agent.ts:8`）；系统状态属于架构 `AGENT-ARCHITECTURE.md:376` 的明确接口分组。保留模板源文件本身不等于开放范围外业务。

本轮没有实际打开浏览器；原始 Art Design Pro 没有可访问基准实例，且不能为对比修改源目录。未给出 UI 一致性通过结论。复审应打开当前工作台、知识、状态与继承的主题/设置组件对照，并明确缺少原始页面渲染基准的限制。

## 原始验证输出

后端命令：在 `globalmail-agent/backend` 设置 `PYTHONPATH=src`，从忽略配置读取数据库 URL 到 `GLOBALMAIL_TEST_DATABASE_URL`（未输出凭据），执行 `.venv/Scripts/python.exe -m unittest discover -s tests -v`。随机 schema 自动清理，未重启 PG。退出码 0。

```text
D:\Work_Project\globalmail-agent\globalmail-agent\backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_bad_hosts_and_origins_rejected (test_api.ApiTests.test_bad_hosts_and_origins_rejected) ... ok
test_live_and_safe_runtime (test_api.ApiTests.test_live_and_safe_runtime) ... ok
test_non_local_config_rejected (test_api.ApiTests.test_non_local_config_rejected) ... ok
test_preflight_and_write_protection (test_api.ApiTests.test_preflight_and_write_protection) ... ok
test_readiness_degraded_without_database (test_api.ApiTests.test_readiness_degraded_without_database) ... ok
test_validation_and_exceptions_are_sanitized (test_api.ApiTests.test_validation_and_exceptions_are_sanitized) ... ok
test_migration_repeat_restart_and_ready (test_postgres.PostgresTests.test_migration_repeat_restart_and_ready) ... ok
test_missing_schema_and_unwritable_store_degraded (test_postgres.PostgresTests.test_missing_schema_and_unwritable_store_degraded) ... ok
test_path_and_digest_protection (test_postgres.PostgresTests.test_path_and_digest_protection) ... ok
test_source_dependency_and_scope_database_constraint (test_postgres.PostgresTests.test_source_dependency_and_scope_database_constraint) ... ok

----------------------------------------------------------------------
Ran 10 tests in 0.764s

OK
```

脚本命令：`pwsh -File globalmail-agent/scripts/test-local.ps1`，退出码 0。

```text
本机配置已存在，保留原密码及端口。
PASS 重复初始化保留凭据
PASS 端口冲突明确拒绝
PASS 进程创建时间校验及停止
```

编译命令：在 `globalmail-agent/frontend` 执行 `pnpm build`，退出码 0。以下为原始关键输出；中间产物体积列表省略，未改写为全量日志。

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3234 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 28.59s
```

## Stage 2

**未执行**：初审发现 Stage 1 HIGH，按技能停在 Stage 1。代码质量、完整安全扫描、测试真实性专项和实际视觉对比均不得据本报告标为通过。主线程修复后重新派 fresh code-reviewer，从 Stage 1 开始检查最终实现。

