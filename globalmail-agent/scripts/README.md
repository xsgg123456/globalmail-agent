# 本机运行

前置：Windows PowerShell 7、Docker Desktop、Python 3.12/uv、Node >=20.19及pnpm。使用项目已锁依赖；本目录不发布生产服务。

在仓库根执行：

```powershell
pwsh -File globalmail-agent/scripts/start-local.ps1
# 已装依赖可加 -SkipInstall
pwsh -File globalmail-agent/scripts/stop-local.ps1
# 同时停止本项目数据库（保留卷）
pwsh -File globalmail-agent/scripts/stop-local.ps1 -StopDatabase
```

默认页面127.0.0.1:15173、API127.0.0.1:18080、PG127.0.0.1:15432。首次运行生成随机数据库密码并保存在根`.local-data/runtime/`，不进入Git。`init-local.ps1`可在首次创建时指定三个不同端口；已有配置保留，不自动轮换密码。之后更改端口需要同步本机settings.json、compose.env，停止旧服务后重启。

脚本先检查端口，再启动独立`globalmail-agent` Compose数据库、执行Alembic迁移、启动后端及现有前端。重复启动遇占用明确报错，不杀其他程序；停止只处理登记PID且创建时间相符的本项目进程及其子进程。PG18卷挂载`/var/lib/postgresql`，不执行`down -v`。安装使用冻结锁文件，前端安装禁用生命周期脚本，避免改变仓库Git hooks。

后端只从服务端环境取得连接串；根.env仅允许读取LLM_MODEL/LLM_BASE_URL/LLM_API_KEY作为配置标志，本阶段不调用模型。前端子进程不继承这些配置，VITE变量不得放密钥。日志和进程登记位于`.local-data/runtime`。这只是本地单用户入口，没有公开网络认证能力。

工作台会话及知识维护尚未接入；页面状态应显示实际就绪和明确未开放功能，不能据启动成功声称后续业务已实现。

实现依据：[Compose健康检查](https://docs.docker.com/compose/how-tos/startup-order/)、[PG18卷布局](https://hub.docker.com/_/postgres)、[Phase 2验证记录](../../docs/verification/PHASE-2-VALIDATION.md)。
