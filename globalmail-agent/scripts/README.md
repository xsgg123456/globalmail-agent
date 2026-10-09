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

后端只从服务端环境取得连接串；根.env允许读取LLM_MODEL/LLM_BASE_URL/LLM_API_KEY及可选GLOBALMAIL_EMBEDDING_API_KEY/BASE_URL。Embedding专用配置为空时沿用LLM连接配置；构建与试查实际调用Embedding。Phase7工作台接入Qwen3.7-Plus文本Agent，接收模拟客户来信会实际调用模型并经核验后模拟回复/等待或转人工，单轮预算6模型/12工具/120活动秒；运行详情显示真实调用与未知费用。前端子进程不继承这些配置，VITE变量不得放密钥。日志和进程登记位于`.local-data/runtime`。这只是本地单用户入口，没有公开网络认证能力。

工作台已接会话、受控历史JSON、逐封回放、人工处理，以及初始场景/订单/适配/库存/既有账本/只读政策核对。点击“初始业务场景”创建独立资料会话，在处理详情展开商品行和核对区。

知识入口`http://127.0.0.1:15173/#/knowledge`支持上传、不可变版本、解析、适用范围和人工核对、索引构建、显式发布/回滚、模型整体切换、检索试查和下架。准备包22份资料仅供模拟，导入/核对/构建均不自动发布；文本Agent只读取当轮固定的适用发布资料，完整删除尚未接入。页面操作写入本机数据，开发测试请用下方隔离入口。

启动脚本默认安装API、前端及独立parser冻结环境，升级数据库至0006，保留旧数据/配置。PDF需要已核验的本地模型，详见[parser安装](../parser-worker/README.md)；`setup-parser.ps1`检查已有环境，首次下载显式加`-DownloadModels`，Standard另加`-Standard`。正常启动不会自动下载模型；缺少模型的档位如实显示未就绪。Markdown/受控知识JSON/JSONL和政策使用API环境解析；构建/试查另走服务端付费Embedding。

浏览器验收用`phase3-test-server.py`：必须提供服务端`GLOBALMAIL_TEST_DATABASE_URL`，自动创建随机schema和临时对象目录，默认隔离页面15174/API18181；用`tmp/phase3-browser.stop`停止并清理。`phase3-network-check.py`仅对该隔离默认端口检查真实SSE/历史隔离，不可对正式用户数据运行。实际结果与范围见[Phase3验收](../../docs/verification/PHASE-3-VALIDATION.md)。

Phase4沿用同一隔离入口，加`--phase 4`，停止文件改为`tmp/phase4-browser.stop`。对象与日志临时目录位于仓库`tmp/`，正常关闭自动清理自己的schema、进程和临时目录，不向正式库写测试场景。

Phase5加`--phase 5`，使用`tmp/phase5-browser.stop`停止并清理。实际解析/故障/页面范围见[Phase5验证](../../docs/verification/PHASE-5-VALIDATION.md)。

Phase6加`--phase 6`，停止文件为`tmp/phase6-browser.stop`。若需实际Embedding，应只向后端注入上述服务端配置。vector扩展尚未装入正式库时，临时schema会自行安装并在清理时撤销；数据库测试、实际评测和隔离页面依次运行，避免互相撤销扩展。实际评测入口见[knowledge-eval](../knowledge-eval/README.md)。`verify-preservation.py before/after`只保存旧表/原件/设置的摘要，用于正式迁移前后核对，不输出业务正文或凭据。

实现依据：[Compose健康检查](https://docs.docker.com/compose/how-tos/startup-order/)、[PG18卷布局](https://hub.docker.com/_/postgres)、[Phase 2验证记录](../../docs/verification/PHASE-2-VALIDATION.md)。

Phase7加`--phase 7`，停止文件为`tmp/phase7-browser.stop`。未配置Qwen时任务如实失败并可显式重试；已经识别的active文本风险直接人审，普通人工回复不清除，只有明确处理/更正并记录依据才能解除。真实模型验收使用[agent-eval](../agent-eval/README.md)的冻结输入和独立schema；只验证文本及既有查询，不冒充售后写入或图片能力。正式升级摘要使用`verify-preservation.py before --phase 7`和`after --phase 7`，不覆盖Phase6历史报告。

只验页面协议时可加`--manual-agent`，仅限Phase7：禁止自动worker，由测试驱动显式工程响应且清空服务端模型配置；不能用这类样本证明真实Qwen质量。已运行的隔离服务可执行`backend/.venv/Scripts/python.exe scripts/phase7-network-check.py`验证真实SSE顺序、心跳及游标拒绝；该脚本仅访问18181/15174，在独立schema创建并停止自己的会话，0模型调用。
