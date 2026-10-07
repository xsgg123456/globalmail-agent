# 正式后端（Phase 2）

仅本机单用户运行。提供 `/api/v1/health/live`、`health/ready`、`runtime-config`，不开放上传、删除、会话或模型执行 API。

使用项目启动脚本注入服务端配置。手动执行时先设置 `.env.example` 中的环境变量；模块不自动读取 `.env`。

```powershell
uv sync --frozen
$env:PYTHONPATH = 'src'
uv run alembic upgrade head
uv run uvicorn globalmail_agent.main:app --host 127.0.0.1 --port 18080
```

`GLOBALMAIL_TEST_DATABASE_URL` 指向专用本项目 PostgreSQL。测试创建随机 schema 并在结束后删除，文件使用临时目录；未配置时数据库测试明确跳过。

```powershell
$env:PYTHONPATH = 'src'
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q src migrations tests
uv pip check
```

对象服务只接受 UUID，以不可变摘要校验内容，登记完整来源/scope；派生对象及依赖同事务入库，跨 scope 依赖由数据库拒绝。`deletion_journal` 仅建基础表，完整撤销、清理和独立备份水位留在 Phase 12。
