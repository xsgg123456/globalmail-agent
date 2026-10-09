# 本机后端（Phase 9）

仅本机单用户运行。会话、受控JSON历史导入、逐封回放、人审、结案/重开、停止/重试及SSE均持久化到PostgreSQL。Phase7/8已接入文本及图文Agent、受控图片预览、更正与撤销；Phase9增加内部售后申请与人工模拟执行。模型语义质量按用户决定留完整链路后统一验收，完整删除在Phase12交付。回复仅在本机模拟。

Phase 4新增白名单初始场景、scoped订单行/申请/执行/包裹/退件账本、精确适配/库存查询和只读政策预览。`0003_business_catalog`从0002增量建表，保留既有会话与对象。场景只能创建独立开发分支；查单不会创建任务或售后申请。未发布政策始终`authorized:false`，原v1场景不自动升级v2。公开接口及当前范围见[Phase4实施约定](../../docs/planning/PHASE-4-IMPLEMENTATION.md)。

Phase 9在同一账本增加退款、退货、换货、补件、查件内部申请，以及独立人工模拟执行控制台。Agent仅能核对、申请、取消和查询；控制台按真实模拟回执推进执行、物流和退件质检。未知结果保留占用，确认原尝试未执行才释放；当前政策版本与执行同事务核验。接口和约束见[Phase9实施步骤](../../docs/planning/PHASE-9-IMPLEMENTATION.md)，实测范围见[工程验证](../../docs/verification/PHASE-9-VALIDATION.md)。

当前源码迁移入口为`0008_after_sales_ledger`，Phase9验证只运行私有测试schema。用户正式库保持`0005_knowledge_index`；正式升级属于后续部署步骤，不能直接在该库跑本期控制台测试。

Phase 5新增知识原件、不可变版本、精确适用范围、独立持久解析任务和人工核对。`0004_knowledge_content`保留旧表/数据，知识任务使用独立槽和本地parser；Markdown/政策/受控JSON在API环境，PDF用[独立MinerU环境](../parser-worker/README.md)。原件丢失/损坏记录明确失败、有限重试，不能挡住后续资料；缓存命中仍验原件。导入和核对不会发布，见[Phase5实施约定](../../docs/planning/PHASE-5-IMPLEMENTATION.md)。

Phase 6用`0005_knowledge_index`增加结构切分、真实1024维Embedding、pgvector检索、完整发布清单/回滚和下架。核对后先构建，再确认发布；失败保留原生效版本。模型切换必须覆盖全部生效资料。试查先按SKU/用途/时间过滤，返回完整父证据和可核验引用；下架后旧引用立即停用。供本机模拟Agent使用，彻底删除留在Phase12，见[Phase6实施约定](../../docs/planning/PHASE-6-IMPLEMENTATION.md)、[实际评测](../knowledge-eval/README.md)和[本机脚本](../scripts/README.md)。

政策说明生成器1.1补齐明确同意/替代适配/旧事项核对条件。既有1.0版本保留原件和说明，可查看但不可构建发布；页面会提示保存新版本，再解析核对。数据库升级不自动修订或发布你的政策资料。

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
当正式库尚未安装vector扩展时，隔离测试会在自己的schema安装并清理扩展；数据库测试、实际评测和隔离页面必须依次运行，不能并发创建这类schema。

```powershell
$env:PYTHONPATH = 'src'
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q src migrations tests
uv pip check
```

对象服务只接受 UUID，以不可变摘要校验内容，登记完整来源/scope；派生对象及依赖同事务入库，跨 scope 依赖由数据库拒绝。`deletion_journal` 仅建基础表，完整撤销、清理和独立备份水位留在 Phase 12。
