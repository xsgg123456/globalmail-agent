# 技术选型探针

这是独立的组件验证工程，技术决策见项目内 `docs/architecture/TECH-SELECTION.md`。它不是邮件 Agent 后端，也不会更改知识源包。

从仓库根目录运行：

```powershell
$env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location) 'tmp/tech-selection/venv'
uv sync --project globalmail-agent/tech-spike --locked --python 3.12
& "$env:UV_PROJECT_ENVIRONMENT/Scripts/python.exe" -B -X utf8 globalmail-agent/tech-spike/probe_provider.py
& "$env:UV_PROJECT_ENVIRONMENT/Scripts/python.exe" -B -X utf8 globalmail-agent/tech-spike/probe_database.py
& "$env:UV_PROJECT_ENVIRONMENT/Scripts/python.exe" -B -X utf8 globalmail-agent/tech-spike/probe_observability.py
```

- `probe_provider.py` 从根 `.env` 读取已配置的百炼凭据，实际发送虚构邮件、已审读知识正文和 PDF 页图，会产生模型调用；不读取 `.local-data` 原始邮件。向量缓存按输入摘要复用，保存在被忽略的 `tmp/tech-selection/`。
- `probe_database.py` 依赖上一脚本的本地向量缓存，创建独立、随机名称和端口的临时 PG 容器，只绑定 127.0.0.1；使用固定镜像 digest 和临时随机密码，结束后移除自己创建的容器及环境文件。不要将这一内存卷配置用于正式数据。
- `probe_observability.py` 发起两个真实 Qwen 请求，使用本地 span exporter 核对回调、异步父子关系和合成敏感字段过滤；再用一个假模型检查 exporter 失败不抛到调用结果。不会发送 Langfuse Cloud。
- `*-results.json` 是本轮实测记录，结论限定为组件烟测。API 连通、开发查询命中不代表业务功能或独立准确率达标。
- 每次从命令行执行探针会先将报告置为运行中；失败会覆盖旧成功状态，记录脱敏错误类型并以非零退出。清理失败单独报告，仍尝试删除临时凭据。
- 前端不属于本探针的安装/构建范围。完整 Langfuse 服务、Alembic 迁移、SSE、任务 worker、正式知识索引和业务 Agent 尚未实现。

本轮测试使用 Python 3.12.10、uv 0.12.2。依赖版本固定在 pyproject.toml 与 uv.lock；Windows 上运行命令使用虚拟环境的 Scripts/python.exe。

报告与清理的 4 项故障回归可离线运行，不调用模型、不启动容器：

```powershell
tmp/tech-selection/venv/Scripts/python.exe -B -X utf8 globalmail-agent/tech-spike/test_probe_failures.py
```
