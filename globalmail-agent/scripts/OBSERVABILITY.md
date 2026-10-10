# 本机 Langfuse 观测服务

PowerShell 7，Docker Desktop/Compose；项目根目录执行：

```powershell
& ./globalmail-agent/scripts/init-observability.ps1
& ./globalmail-agent/scripts/start-observability.ps1
& ./globalmail-agent/scripts/test-observability.ps1
& ./globalmail-agent/scripts/stop-observability.ps1
```

默认入口为 http://127.0.0.1:3001。首次初始化可传 `-Port`，已有配置保留原端口和所有凭据；端口冲突会停止启动并报错，不结束其他进程。脚本固定只操作 `globalmail-agent-observability` Compose 项目，`stop` 保留容器、独立数据卷及配置，后台容器持续运行，关闭终端不影响服务。

私有配置位于根目录 `.local-data/observability/`，Git 忽略且文件 ACL 仅授予当前用户、SYSTEM 和管理员读取权限。`compose.env` 中 `LANGFUSE_INIT_USER_EMAIL` / `LANGFUSE_INIT_USER_PASSWORD` 是本机 UI 登录凭据，项目及组织 ID 均为 `globalmail-agent-local`；`LANGFUSE_INIT_PROJECT_PUBLIC_KEY` / `LANGFUSE_INIT_PROJECT_SECRET_KEY` 为项目 API 密钥。请从本机编辑器读取，不在终端或聊天中输出文件内容。

`backend.env` 供服务端按字段导入：`GLOBALMAIL_LANGFUSE_ENABLED`、`GLOBALMAIL_LANGFUSE_BASE_URL`、`GLOBALMAIL_LANGFUSE_PUBLIC_KEY`、`GLOBALMAIL_LANGFUSE_SECRET_KEY`、`GLOBALMAIL_LANGFUSE_PROJECT_ID`。不通过命令行参数传递密钥，不向前端传递此文件。初始化账号、组织、项目与 API 密钥使用官方 headless initialization，重启保持已有资源，不自动轮换凭据。

冻结组合见 `../infra/observability-images.lock.json` 和 `../infra/compose.observability.yaml`：Langfuse Web/Worker 4.56.0、PostgreSQL 17.11、ClickHouse 25.12.11.4、Redis 7.4.11、Chainguard MinIO RELEASE.2026-09-22T19-25-18Z。运行引用均为 `sha256`，来源标签仅用于记录，MinIO 官方原始浮动标签不参与启动。没有 Cloud 连接；Langfuse/Next 遥测关闭，新用户注册关闭。所有依赖只在独立 Docker 网络可达，唯一宿主机端口是 Web 的本机入口。媒体存储保留内部端点，应用仍须在 SDK 前阻断原图/正文上传，部署不能代替脱敏验收。

`test-observability.ps1` 验证六服务 healthy、镜像锁一致、项目及数据卷隔离、唯一端口、HTTP 健康、项目 API 凭据、匿名 401 和初始化账号实际登录。`test-observability-preservation.ps1` 需要后端已安装的 Langfuse SDK4，会通过 OTLP 写入一条无客户内容的 `infra-smoke` 合成追踪、停启整套观测服务，验证追踪仍可由 v2 observations API 读回、五个卷保留、重复初始化不改变配置、业务 PostgreSQL 未被重启；运行前避免并发观测联调。测试结束保留后台服务。

服务保持 v4 默认 `events_only` 模式，旧 `/api/public/traces` 读接口及 legacy `trace-create` 写入已被移除。读回使用带 `traceId` 和有界时间范围的 `/api/public/v2/observations`；自定义 OTLP exporter 应发送 `x-langfuse-ingestion-version: 4`，避免旧写入路径在 v2 查询中的传播延迟。

不要运行 `docker compose config` 输出全部配置（包含密钥）；检查镜像可用 `config --images`，状态用 `ps`。不要使用 `down -v`、共享业务 PostgreSQL 或全局资源清理。当前单机 Compose 无高可用或联合备份能力，完整备份/删除恢复由后续 Phase12交付。

核验来源：[官方 v4 Compose](https://langfuse.com/self-hosting/deployment/docker-compose)、[4.56.0 源文件](https://github.com/langfuse/langfuse/blob/v4.56.0/docker-compose.yml)、[发布记录](https://github.com/langfuse/langfuse/releases/tag/v4.56.0)、[Headless initialization](https://langfuse.com/self-hosting/administration/headless-initialization)。基础设施烟测只证明部署和协议可用，模型业务质量仍需专项验收。
