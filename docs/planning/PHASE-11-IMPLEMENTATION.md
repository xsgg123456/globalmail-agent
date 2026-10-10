# Phase 11：自托管观测与实际运行追踪

日期：2026-10-10。用户授权继续 Phase11；依据 Product-Spec v1.18、主架构第9节、DEV-PLAN Phase11、AC-049–052 与 FT-12。保留14–16的只读权限、持续人工及邮件/运行台分离契约，不推进12/13，不把工程替身测试算真实模型语义验收。

## 有序任务与完成标准

| 任务 | 范围 | 完成标准 |
|---|---|---|
| 1 | 独立 Langfuse 自托管环境 | 核对官方 v4 Compose；独立项目、库、卷及随机私有凭据，入口仅127.0.0.1；实际启动并冻结全部镜像digest；启停不修改业务数据或其他项目 |
| 2 | 正式运行的安全观测导出 | 同run关联context/图片准备/理解/模型/检索/工具/规则/提交/结果的实际事件；官方SDK手动观测或安全回调只接收白名单数据，原正文/异常/媒体不进入SDK；真实usage仅来自既有唯一账本；有界异步队列、有限重试和受限flush，失败不影响业务 |
| 3 | 本地关联、降级与运行台入口 | 本地持久化真实trace/export状态及清理依赖，API作用域/撤销检查；独立运行台真实入口与状态、加载/空记录和跨页返回无渲染异常，继承Art组件和主题，不恢复旧AgentRunPanel页面 |
| 4 | 实际集成和故障验收 | 独立PG schema/对象目录/端口跑真实应用；真实Qwen文本多工具与图文run进入自托管UI；敏感哨兵、媒体、HTTP/队列失败及FT-12验证不泄漏、不重跑、不双计usage；已有全量工程回归及编译通过 |
| 5 | fresh两阶段审查与交付 | code-reviewer从Stage1开始独立核对证据；缺陷修复重验；正式环境先备份再增量升级并保旧，启动观测与正式服务；回写验证、索引、交接和计划，只提交已验证范围到本地Git，不推送 |

## 文件责任与执行

主Agent先规划、核对源文档并负责独立运行台、联调、验收、审查和提交。基础设施与后端观测是可隔离任务，可显式派fresh执行Agent；执行Agent不再派Agent、不提交，不覆盖他人改动。

- 基础设施：`globalmail-agent/infra/compose.observability.yaml`、镜像锁与观测启停/配置脚本。
- 后端：`observability/`、`api/observability.py`、settings/main/worker及实际节点接入，必要增量迁移，观测后端测试。
- 前端：既有`views/agent-runs/`及`components/agent-runtime/`、相关API契约和测试。
- 证据：`docs/verification/PHASE-11-VALIDATION.md`、独立审查及`artifacts/phase11/`。

不读取或输出密钥；测试不向正式库塞邮件。Langfuse的显示内容默认为无正文ID、状态、版本摘要及用量；图片/base64/可访问URL在SDK处理前阻断。实际工具与理解内容继续由应用受控本地记录提供，不把自托管当作解除隐私规则。Phase12仍负责完整删除和联合恢复。

验收脚本的`--existing-report`只读模式不得启动恢复队列或导出器，也不得发送新span、运行Graph或调用模型；仅核对既有本地记录与远端观测。待导出的其他run不能由只读核对隐式触发。

## 完成结果

2026-10-10五项任务已验收：后端451/451、前端91/91、编译/真实应用故障及明暗GUI通过；[第4轮fresh独审](../verification/PHASE-11-REVIEW-4.md)Stage1/2均PASS。正式0011升级保旧、服务就绪、专用服务/schema/对象精确清理完成；私有GUI登录状态文件因工具策略拒绝删除而保留，不纳入Git，见[完整证据及清理例外](../verification/PHASE-11-VALIDATION.md)。本期工程完成，真实Qwen业务两项失败保留，剩余12–13。

## 核验来源

[官方Compose](https://langfuse.com/self-hosting/deployment/docker-compose)、[Python SDK](https://langfuse.com/docs/observability/sdk/overview)、[脱敏](https://langfuse.com/docs/observability/features/masking)、[无界面初始化](https://langfuse.com/self-hosting/administration/headless-initialization)已在本轮核对；服务完整版本/digest以实际部署后锁定清单为准。
