# 正式后端（Phase 5）

仅本机单用户运行。会话、受控JSON历史导入、逐封回放、人审、结案/重开、停止/重试及SSE均持久化到PostgreSQL。会话自动任务当前只完成调度协议验证，准确记录 `protocol_verified_model_not_connected`，不生成模型回复、不投递真实邮件。正式Agent、客户图片上传和完整删除在后续阶段接入。

Phase 4新增白名单初始场景、scoped订单行/申请/执行/包裹/退件账本、精确适配/库存查询和只读政策预览。`0003_business_catalog`从0002增量建表，保留既有会话与对象。场景只能创建独立开发分支；查单不会创建任务或售后申请。未发布政策始终`authorized:false`，原v1场景不自动升级v2。公开接口及当前范围见[Phase4实施约定](../../docs/planning/PHASE-4-IMPLEMENTATION.md)。

Phase 5新增知识原件、不可变版本、精确适用范围、独立持久解析任务和人工核对。`0004_knowledge_content`保留旧表/数据，知识任务使用独立槽和本地parser；Markdown/政策/受控JSON在API环境，PDF用[独立MinerU环境](../parser-worker/README.md)。原件丢失/损坏记录明确失败、有限重试，不能挡住后续资料；缓存命中仍验原件。所有内容仅供模拟、未发布，未实现向量/检索/Agent知识使用；接口及安装见[Phase5实施约定](../../docs/planning/PHASE-5-IMPLEMENTATION.md)和[本机脚本](../scripts/README.md)。

表、事务、请求和响应的精确契约见 [Phase 3契约](../../docs/planning/PHASE-3-CONTRACT.md)。首次创建/导入携带 `expected_version:0`，其余写动作携带最新资源版本和 `Idempotency-Key`；人工回复额外携带最新 `expected_input_revision`。过期409保留数据库草稿。

导入只接受浏览器上传JSON的允许字段；[安全合成样例](fixtures/historical-example.json)也可从 `/api/v1/imports/example` 读取。不接受服务器路径、未来控制事件、参考答案或未经受控复核的身份授权。未验证真实身份只作为独立历史案例；`group_id`不参与身份合并。历史详情只显示真实可见前缀，人工审阅结果单独返回，不加入messages。

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
