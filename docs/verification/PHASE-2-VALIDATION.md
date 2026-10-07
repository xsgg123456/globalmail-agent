# Phase 2 本机运行基础

状态：四步技术验证及独立两阶段审查通过，待用户查看；2026-10-07。依照DEV-PLAN Phase 2，不接入模型或实现会话/知识业务。

## 执行规划与完成标准

1. 后端基础：FastAPI安全状态API、Alembic与PostgreSQL、受控对象和内容依赖/删除journal基础。标准：迁移可重跑，状态反映真实依赖，存取有scope隔离、非法路径拒绝，重启持久数据保留。
2. 前端外壳：继承Art Design Pro布局/主题，工作台、知识库和系统状态页面，本地单用户入口无模板登录请求。标准：冻结锁文件安装、类型检查/构建通过，加载/故障/重试/真实未接入状态可见，不显示假业务成功。
3. 运行集成：独立Compose项目、持久PG卷及启动/停止脚本，端口冲突检测。标准：仅127.0.0.1绑定，非法Host/Origin拒绝，响应不含密钥/连接串，不触碰其他容器或原前端项目。
4. 独立审查与验收：真实PG/API测试、浏览器页面检查及代码两阶段审查；发现问题修复后复验，证据回写。

## 本阶段接口约定

- API `http://127.0.0.1:18080/api/v1`；开发页面`http://127.0.0.1:15173`；本项目PG发布`127.0.0.1:15432`。启动参数可改端口，但两端Origin/代理须一致。
- `GET /health/live`、`/health/ready`、`/runtime-config`。JSON envelope为`{code,msg,data,request_id}`；就绪失败HTTP503，错误仅安全类别，所有响应带request_id。
- live data `{status:'ok'}`；ready data `{status:'ready'|'degraded', database:'ready'|'unavailable', object_store:'ready'|'unavailable', schema:'ready'|'unavailable'}`。
- runtime data `{mode:'local_single_user', phase:2, features:{conversations:false, knowledge:false, agent:false}, model_configured:boolean}`；只返回已配置标志，不读出密钥值供前端。
- 对象、依赖和删除journal仅服务层与基础表，不提前开放上传/删除业务API。对象必须服务端UUID、内容摘要、来源与workspace/mode/branch/customer/purpose作用域；访问复验范围，依赖两端同范围。尚未实现的删除流程不返回完成。
- PG默认复用已验证pgvector镜像digest，独立Compose项目名`globalmail-agent`，使用本项目独立持久卷；密码首次生成至忽略的本地配置，不进Git。正式依赖复用tech-spike已锁版本，新增最小后端锁文件，不升级。

## 验证记录

### 已执行

| 项目 | 命令/方式 | 实际结果 |
|---|---|---|
| 后端API/PG | 后端环境`python -m unittest discover -s tests -v`，设置GLOBALMAIL_TEST_DATABASE_URL | 12 tests / 3.055s / OK；其中6项连接真实PG，随机schema与临时对象目录清理 |
| 编译 | 后端`compileall`检查src/migrations及运行验证脚本；前端`pnpm build`含vue-tsc | Python退出0；前端3235模块、25.39秒构建成功，类型检查零错误 |
| 前端契约/已有状态迁移 | `pnpm exec tsx --test scripts/*.test.ts` | 4 tests / 4 pass；清除旧演示页签，拒绝code0/HTTP错配和错误状态结构 |
| 启停保护 | `pwsh -File globalmail-agent/scripts/test-local.ps1` | 3项PASS：重复初始化不覆盖凭据、端口冲突拒绝、PID及JSON创建时间校验停止 |
| 真实HTTP与PG重启 | 后端Python执行`scripts/check-runtime.py --restart-database` | 直连/前端代理各3接口HTTP200；非法Host/Origin拒绝；真实容器重启后同一正文及对象登记读回；测试数据清理 |
| 实际重复启动 | 服务已起时执行`start-local.ps1 -SkipInstall` | 退出1，明确“端口18080已被占用”；原服务仍ready，未杀其他进程 |
| 冻结依赖 | `uv pip check`；`pnpm-lock.yaml`与Phase1提交diff | 24个后端包兼容；前端锁文件无改动，不修改原Art Design Pro目录 |

真实迁移已对本项目新数据库连续`alembic upgrade head`两次。四张基础表为workspaces、objects、content_dependencies、deletion_journal；依赖两端scope复合外键覆盖workspace/mode/branch/customer/purpose。ObjectStore使用服务生成UUID、原子文件替换、摘要校验、失败孤儿清理。journal仅基础，没有对外删除API或“已删除”结果。

运行时HTTP证据保存在`tmp/phase2-runtime-check.json`；容器重启证据单独保存`tmp/phase2-runtime-restart-check.json`，普通检查不会覆盖重启结果。测试中只重启本项目`globalmail-agent-postgres-1`；原有it-project-console的PG与MinIO保持运行、端口不变。

### 浏览器实测

通过本地真实Vite前端访问三页，未经过登录或模板用户接口。工作台展示三栏未接入状态；知识库明确上传/修订/发布尚未开放；系统页实际显示API、数据库、迁移结构、对象存储及仅模型配置标志。没有模型调用、业务邮件或假业务数据。

主线程实际停止数据库后刷新：API仍可访问、数据库/结构不可用、页面提示依赖未就绪；启动数据库后刷新恢复ready。实际停止API后刷新：三项请求失败、状态为未知、显示“重试”；停止/重启整套服务后恢复。加载时刷新按钮禁用。桌面宽度下工作台、知识、系统页沿用同一外壳/主题，未发现水平溢出；未把手机精细适配算作本阶段验收。

原模板源目录不运行也不修改；视觉对照限复制后保留的布局组件和当前相邻页面，不能声称已做原源工程运行截图的逐像素比较。

### 已定位并修复的问题

- 初审发现后端成功code0与前端HTTP200契约不一致，导致成功接口显示失败。修正后后端、前端负例测试与真实代理链验证均通过；[初审报告](PHASE-2-REVIEW.md)保留原结论。
- 实际停机暴露PowerShell7.5将ISO时间读成DateTime，使字符串比较漏停进程。现按UTC ticks核对PID创建时间，增加JSON登记往返测试，实际停止API及整套重启通过。
- 初始HTML标题仍为上游模板名，已改GlobalMail Agent；LICENSE与原复制摘要保留。

### 边界与后续

本机地址：[工作台](http://127.0.0.1:15173/#/workbench)。入口/停止/更改端口见[运行说明](../../globalmail-agent/scripts/README.md)。开发运行的API和Vite为后台进程，PG为独立持久卷。关闭后数据保留；未发布公网服务。

Phase3才实现会话、消息、历史回放、人审和任务；Phase5/6才开放知识维护/发布。Phase2通过不表示82项产品AC整体通过。锁环境Starlette测试客户端提示httpx弃用，测试与运行未失败，按既定版本不临时升级。

实现依据：[FastAPI中间件](https://fastapi.tiangolo.com/advanced/middleware/)、[Alembic环境配置](https://alembic.sqlalchemy.org/en/latest/tutorial.html)、[Vite服务配置](https://vite.dev/config/server-options)、[Compose健康等待](https://docs.docker.com/compose/how-tos/startup-order/)、[PG18持久卷](https://hub.docker.com/_/postgres)。

独立[最终审查](PHASE-2-REVIEW-FINAL.md)：Stage 1 PASS、Stage 2 PASS，无阻塞问题；复验包含12后端、4前端、3脚本测试、类型/构建和真实页面。Phase 2实现技术验收通过，不替代后续业务与产品总验收。
