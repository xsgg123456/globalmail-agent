# 正式邮件与Agent运行台改造

日期：2026-10-09。授权：按当前业务收敛预览重新拆任务并改造现有前后端；继续不暂存、不Git提交。

## 任务与完成标准

保留15175已批准的Art外壳、邮件布局、运行概览/会话轮次/时间线/节点详情。七类、知识维护和图片能力保留；四类商业售后只读查询及内部建议、客服持续主导；业务中心后置，不做场景实验室或测试界面。

| 顺序 | 开发任务 | 完成标准 |
|---|---|---|
| 1 / Phase14 | 持久权限、入站调度和终局收敛 | 四类有源意图进入持续人工；首轮及后续只能提交内部建议，人工回复不恢复自动发送；新邮件/接管/停止/结案阻止旧结果覆盖；商业写工具/业务事件自动唤起退出默认链路；迁移保留原数据 |
| 2 / Phase15 | 逐次真实模型记录和独立建议资源 | 实际system/user/tool文本、Schema、参数、返回内容/供应商reasoning、用量和失败逐次保存；历史快照不反填；未返回思考/旧未采集记录明确空态；建议来源/缺口/草稿/时效可查，读取不执行模型 |
| 3 / Phase16 | 正式邮件与独立运行台接入 | 邮件仅往来、接管、建议、人工草稿/发送/结案；运行台会话→轮次→节点、深链接和历史新轮提示；真实加载/空/错误态，无预置run/指标；个人草稿跨页保留、采用需确认、旧建议拒用；删除测试UI和旧缓存入口 |
| 4 / Phase16验收 | 脚本/API回归和本机交付 | 隔离PG/对象目录实测四类多轮、普通回复、错误/未知/危险和晚到结果；全量工程回归、编译、真实GUI及fresh两阶段独审通过；正式迁移前备份，给运行地址和限制 |

原Phase1–10结论保留历史，不能称旧售后执行符合新目标；原11–13未开始，改为10→14→15→16→11→12→13。Langfuse、删除/备份恢复及完整模型语义验收保留，不新增微服务或ERP。

## 关键文件

后端源码路径以`globalmail-agent/backend/src/globalmail_agent/`为前缀，前端以`globalmail-agent/frontend/src/`为前缀。

- Phase14：`adapters/conversation_schema.py`、`agent_schema.py`；`globalmail-agent/backend/migrations/versions/0010_human_assistance.py`；`application/conversation_base.py`、`human_review.py`、`task_queue.py`、`commit_outcome.py`及新`human_assistance.py`；`worker/leases.py`、`jobs.py`、`agent_runner.py`；`agent/graph.py`、`tool_menu.py`、`tool_gateway.py`、`tool_schemas.py`及prompts；`application/business_events.py`、`waits.py`及默认API注册。
- Phase15：新`observability/model_records.py`、`agent/budget.py`、`adapters/model_provider.py`、`application/run_records.py`、`conversation_queries.py`、`api/runs.py`；前端`api/agent-run-contract.ts`、`agent-run-api.ts`、`mail-agent-contract.ts`。复用已有对象存储和运行账本。
- Phase16：`views/mail-agent/index.vue`、新`views/agent-runs/`、`components/agent-runtime/`、`composables/use-agent-console.ts`、`use-conversation-advice.ts`及既有`useMailWorkbench.ts`/子模块；`router/modules/mail-agent.ts`、`local-tabs.ts`、相关标签/API。复用`MessageTimeline.vue`、Art主题和批准的展示结构，正式页面不依赖preview fixtures/control。
- 验证：新`backend/tests/test_human_assistance.py`、`test_model_records.py`、`test_formal_boundary.py`、`test_human_assistance_migration.py`，前端对应契约/导航/草稿测试；脚本置`globalmail-agent/scripts/`，报告置`docs/verification/`。

## 强制运行契约

运行契约由[主架构当前正式运行契约](../../AGENT-ARCHITECTURE.md#当前正式运行契约v118)统一维护；本规划消费该契约，不另设权限规则。

## 依赖与隔离

复用锁定FastAPI/SQLAlchemy/Alembic、LangGraph和Qwen兼容SDK，不升级依赖。已核对[LangGraph持久化](https://docs.langchain.com/oss/python/langgraph/persistence)、[Alembic增量迁移](https://alembic.sqlalchemy.org/en/latest/ops.html)、[百炼reasoning字段](https://help.aliyun.com/zh/model-studio/deep-thinking)。先用持久记录/既有SSE，逐字供应商流式不纳入本轮，实际返回全文在完成后可查。

自动测试用独立schema/对象目录/端口，正式库不塞测试会话。正式迁移前完整备份，增量升级并核对旧表/对象保留；已有预览及用户`.idea/`不回滚。全过程不暂存、不提交。

2026-10-10执行收口：四步工程验收及fresh独审通过，正式0010迁移保旧、15173/18080已启动；422后端/86前端与具体GUI/API证据见[本期验证](../verification/FORMAL-WORKBENCH-REFACTOR-VALIDATION.md)。脚本入口为`start-workbench-test.ps1`及`mail-test-api.py --session`，没有测试UI。用户页面验收及11–13模型/观测/恢复任务保持后续；原失败报告保留。
