# Phase12 第二轮独立审查

日期：2026-10-10。基线 `b42794e`，范围为 Phase12 工作树实现及新增测试，排除用户 `.codex/evolution/signals.jsonl`。依据 `.agents/skills/code-review/SKILL.md` 执行；只审查，未修改产品实现或提交。

**Stage 1 不通过：2 项 HIGH。Stage 2 未执行。** 主线程收到缺陷后开始修复，本报告保留修复前事实，不能作为后续工作树的通过证明。

## Stage 1：HIGH 缺陷

### H1：会话删除把所读共享知识原件当作会话自有对象删除

- 原文要求：`Product-Spec.md:356` 区分资料下架与彻底删除；`:457` 删除客户数据清理该项目内邮件、记忆、草稿和运行记录；`AGENT-ARCHITECTURE.md:396` 共享输入不能直接删除其他文档，`:398` 共享无法安全分离应阻断。
- 真实写入路径：`globalmail-agent/backend/src/globalmail_agent/agent/tool_gateway.py:180` 登记会话运行依赖，`:182` 将知识版本原件写到 `agent_run_dependencies.source_object_id`。这是被读取来源，不是该会话拥有的副本。
- 错误枚举：修复前 `application/lifecycle_inventory.py:64` 遍历所有含 `conversation_id` 的表，`:77`–`:78` 把每个 `*object_id` 列无差别加入待删根；因此依赖表的共享来源也入选。会话路径没有文档共享阻断。
- 破坏路径：`application/lifecycle_revoke.py:65` 对这些对象写 tombstone；`application/deletion.py:123`–`:127` 按 ID 删除文件并清空对象摘要。`verify_local` 只验证既定 manifest 的清理，不能发现错误所有权，最终仍显示 completed。
- 独立审查确认上述生产路径；主线程补充真实 PG 隔离反例，审查者已读取测试和原始日志。`tests/test_lifecycle_sources.py:14`–`:30` 实际建资料、解析、构建、发布、调用 `search_reference`，确认已有一条依赖但没有最终 citation；删除会话完成后，原知识读取报 410。测试仅 mock 远端 purge，知识检索、PG、对象和删除均走生产实现。
- 原始输出来源：`tmp/phase12-source-owner-before.log`：

```text
test_case_delete_keeps_shared_knowledge_original_used_without_citation ... ERROR
  File ".../tests/test_lifecycle_sources.py", line 30, in test_case_delete_keeps_shared_knowledge_original_used_without_citation
    self.assertEqual(KnowledgeFiles(self.store).read(conn, source)[0], before)
  File ".../knowledge/base.py", line 103, in read
    check_objects(conn, scope(self.workspace), (identity,))
  File ".../application/content_fence.py", line 25, in check_objects
    raise ServiceError("content_deleted", 410)
globalmail_agent.application.conversation_lock.ServiceError: ('content_deleted', 410)

Ran 1 test in 7.075s
FAILED (errors=1)
```

- 同一枚举也用于图片删除及知识删除扩展出的受影响会话，可能连带其他所读知识。该扩展影响由代码确定，本轮动态反例仅验证会话路径，不冒充三类均已实测。
- 修复标准：区分拥有的正文副本和外部来源引用；保留知识原件、其独立合法衍生物及其他会话，清理目标会话中的复制正文。新增三类目标与多资料组合用例。

### H2：恢复重放旧下架记录，会撤下后来合法重新发布的资料

- 契约：`Product-Spec.md:355` 支持原子发布和合规版本回滚；`AGENT-ARCHITECTURE.md:404` 联合恢复重建允许索引。普通下架是可重新发布的状态，不能等同永久删除。
- 位置：`application/restore.py:73` 重放日志全部记录；`application/replay_journal.py:52` 同库恢复也逐条重放；修复前 `application/lifecycle_replay.py:18` 只看当前 `withdrawn=False` 即重新撤销，未核对该记录是否已存在事务回执。`:24` 增加撤销代次，`:31` 从当前发布 head 移除目标；`:44` 才写幂等 receipt。
- 审查者独立复现：真实 PG 随机 schema，使用 `IndexFixture` 的真实 Markdown parser、合成向量；生产发布→生产 withdraw→重新 build→生产 publish；确认已有 receipt，随后直接调用恢复使用的生产 `LifecycleService.replay`。没有直接 SQL 伪造生命周期状态。
- 原始输出：

```text
runTest (__main__.Repro.runTest) ... ok
Ran 1 test in 4.220s
OK
before_replay_withdrawn= False
committed_receipts= 1
before_replay_entries= {'release_id': 'a2cbb5ea-ac64-4992-8e06-739953b20828', 'epoch': 3, 'embedding_profile_id': '2e3dd1a3-6459-4a57-8215-f4c940f45aa0'}
replay_result= {'status': 'completed', 'action': 'withdraw', 'target_type': 'document', 'target_id': 'fbcad222-7a4c-48f7-a6a4-a4f08925f39f'}
after_replay_withdrawn= True
after_replay_current_entries= 0
```

`OK` 仅指反例脚本执行成功；实际业务结果是合法发布被错误撤下。此反例验证生产重放函数，未另跑整套 pg_restore；整套恢复的调用位置见上文。

- 修复标准：已落事务回执的普通撤销不得覆盖其后的合法状态；无回执意图仍须补执行。永久删除仍须完成清理核验，不能一概按 receipt 跳过。补备份在重新发布之后和撤销之前两种恢复测试。

## 初审问题复验

| 初审项 | 本轮结论 | 证据 |
|---|---|---|
| H1 发布资料删除后恢复访问旧 head | 该反例关闭 | `application/lifecycle_revoke.py:44`–`:52` 写新合法 head；`tests/test_lifecycle_knowledge.py:14` 实测删除一份、保留另一份且运行恢复核验通过；单份删除用例也通过 |
| H2 旧快照没有新目标即恢复失败 | 该反例关闭 | `application/lifecycle.py:119`–`:123` absent 写 receipt；`tests/test_backup_restore.py:169` 真实 pg_dump/pg_restore、生产 replay、第二次幂等回放通过 |
| H3 无 head 草稿删除 KeyError | 该反例关闭 | `application/lifecycle_revoke.py:47` 检查 head ID；`tests/test_lifecycle_knowledge.py:52` 无发布 head 的共享原件用例进入 blocked_dependencies，无 KeyError |
| M1 共享提示误称替换版本即可解除、缺关联 ID | 关闭 | `frontend/src/components/shared/DeletionStatus.vue:4` 明示历史依赖需维护处理；`:5` 渲染 ID。已查看 `artifacts/phase12/shared-blocked.png` 实际截图，显示诚实提示及关联资料 ID；预览也显示列表，`DeletionDialog.vue:11` |

## Stage 1：本期需求逐项对照

以下仅覆盖 DEV-PLAN Phase12 分配的生命周期增量；REQ-005 的检索质量、REQ-008 原有运行台、REQ-010 评测质量、REQ-013 原有观测和 REQ-014 图片语义质量不在本期重新验收，不能据本报告勾选这些需求的全部 AC。

| 本期条目 | 实现状态 | 代码及证据 |
|---|---|---|
| REQ-010 会话/资料/图片删除前影响、取消无写入 | 完整实现，有限验证匹配 | `application/lifecycle.py:32` preview；`api/lifecycle.py:34`；`tests/test_lifecycle_api.py:22`。GUI 证据 `artifacts/phase12/cancel-db-result.txt:1` 为 `cancel_database_unchanged=True`；非审查者亲手重做 |
| REQ-010 / AC-029 清理客户邮件、记忆、草稿、运行正文 | 部分实现 | `application/deletion.py:103` 清理及 `:151` 验证；`tests/test_lifecycle_core.py:26` 其他分支保留。错误跨 scope 来源删除见本轮 H1 |
| REQ-008 / AC-029 停任务、拒绝晚到 checkpoint/对象 | 已实现，模型在途实测匹配 | `application/lifecycle_revoke.py:28` invalidate；`content_fence.py:7` 对象栅栏；`worker/agent_runner.py:59` / `worker/knowledge_runner.py:39` writer barrier。独立执行 `test_lifecycle_drain`：实际 AgentRunner + 线程阻塞模型，未排空时失败、排空后完成。parser drain 本轮未独立动态重做 |
| REQ-010 reset 仅模拟、独立空分支且幂等 | 已实现 | `application/lifecycle.py:48` 限定 action、`:65` 限定 simulation；`application/deletion.py:130` reset；`tests/test_lifecycle_core.py:74` 存在真实 PG 用例。本轮未独立重跑此用例 |
| REQ-010 分支业务清理、释放占用、其他分支及防重保留 | 已实现，完整组合仍有限验证 | `application/deletion.py:49` scrub_business、`:134` 释放预留；`tests/test_lifecycle_business.py:12` 比较源快照与账本 ID。未以此宣称图片删除后所有售后重复办理组合已测 |
| REQ-010 源准备包保持不变 | 路径范围匹配，证据仍有界限 | `application/deletion.py:124` 只操作 ObjectStore ID 路径，没有外部源包写路径；本轮无源包全量前后摘要实测，不将其他分支测试替代此项 |
| REQ-005 / AC-060 原件、解析、块、向量、缓存、引用和运行衍生内容 | 部分实现 | `application/deletion.py:69` purge_knowledge；独立知识删除4项通过。跨来源所有权 H1 尚不通过，不能确认整体删除边界 |
| REQ-005 模型看过但未引用也清理 | 部分实现 | `application/lifecycle_inventory.py:59` 按 run dependency 扩至整个 case；本轮 H1 的真实检索未引用场景证明依赖存在，也暴露清理过宽 |
| REQ-005 普通下架与彻底删除、共享原件阻断 | 删除状态及提示匹配，恢复语义不匹配 | `lifecycle_revoke.py:40`、`lifecycle.py:179` blocked 路径；shared 测试及实际截图通过；普通下架恢复见 H2 |
| REQ-014 / AC-078 图片原件/派生/模型记录/草稿/模拟回复及业务审计 | 部分实现 | `lifecycle_inventory.py:39` 图片根、`:68` 保留客户来源邮件；`deletion.py:16` 图片字段清理；`tests/test_lifecycle_attachments.py:14` 后续继续处理覆盖。H1 同类外部来源边界未关闭 |
| REQ-014 撤销后剩余会话可以继续，旧依赖不读取 | 代码修正匹配，动态证据有限 | `application/human_review.py:16`–`:23` 过滤不可读依赖；`attachments/evidence.py:40` 过滤已撤销分析；`tests/test_lifecycle_attachments.py:14` 真实 takeover→human_reply→append 路径存在，本轮未独立重跑 |
| REQ-013 远端追踪删除、在途/接受未知及 SDK 缓冲互斥 | 协议及实际远端有证据，最终源码实际远端未全重做 | `observability/purge.py:29` export lock、`:110` 完整接收后删除及两次空读；`artifacts/phase12/observability-actual.json:7` 记录独立 trace 无模型删除成功。该文件明确真实远端探针早于最后恢复加固，不能抹去此证据边界 |
| 独立 journal、事务回执、缺水位封闭 | 已实现，故障路径已有测试 | `adapters/deletion_journal.py:89` 认证校验；`application/journal_gate.py:7` receipts 对照；`api/restore_gate.py:12`；`tests/test_lifecycle_api.py:41` 外部意图未提交时封闭 |
| 联合备份、全新库/目录、最新日志重放后核验开放 | 部分实现 | `adapters/backup_store.py:86` 联合快照；`application/restore.py:36` 新目标及封闭检查；独立真实旧快照 absent 用例通过，但 H2 说明合法状态恢复错误 |
| 离线同库重放与重试 | 部分实现 | `application/replay_journal.py:36` 离线门禁、`:59` receipts完整性、`:61` 内容核验；同样受 H2 影响 |
| API/GUI 危险操作、状态、失败重试、草稿清除 | 实现及提交证据匹配 | `frontend/src/views/mail-agent/index.vue:25`、`views/knowledge/index.vue:187`、`components/mail-agent/ImageEvidenceDrawer.vue:47`；三类 completed JSON、shared/history截图及取消哈希证据已检查。GUI 证据来自同轮隔离验收，不冒称审查者执行；本轮不做 Stage2 邻居页面视觉审查 |
| 不新增产品测试控制界面 | 匹配 | `api/lifecycle.py:14` reset只为API action，三类 UI 均是资源操作；`frontend/src/components/shared/DeletionHistory.vue:1` 是真实清理记录，不是样例控制台 |

## Spec 漂移、安全及质量

新增迁移、生命周期 API、独立日志、恢复脚本、cleanup worker 和删除历史均能对应 `docs/planning/PHASE-12-IMPLEMENTATION.md:9`–`:16`，未发现明确无需求产品功能。由于 Stage1 HIGH，**Stage2 未执行**：不输出安全扫描、命名/类型/文件大小、测试质量整体或邻居视觉对比通过结论。

## 本轮独立测试与编译原始输出

隔离：仅将本地配置中的 database_url 注入 `GLOBALMAIL_TEST_DATABASE_URL`，未打印凭据。随机 schema / 临时对象目录，备份用例为随机独立数据库。未连接正式 UI 18080/15173，未访问正式 trace，无付费模型。

命令：

```text
.venv/Scripts/python.exe -m unittest test_lifecycle_knowledge test_backup_restore.BackupRestoreTests.test_newer_deleted_target_absent_from_old_backup_has_receipt test_lifecycle_drain -v
```

原始输出：

```text
test_deleting_one_published_document_preserves_other_eligible_release_entry ... ok
test_document_purge_removes_index_cache_and_manifest_body ... ok
test_replay_withdraw_restores_fence_without_deleting_retained_original ... ok
test_shared_source_blocks_without_deleting_other_original ... ok
test_newer_deleted_target_absent_from_old_backup_has_receipt ... ok
test_inflight_model_drains_before_deleted_content_can_complete ... ok

----------------------------------------------------------------------
Ran 6 tests in 32.828s

OK
```

独立编译命令 `.venv/Scripts/python.exe -m compileall -q src`，原始输出：

```text
compileall exit=0
```

读取主线程预览构建日志 `tmp/phase12-preview-build.log`，末尾原始输出：

```text
✓ built in 26.16s
```

完整后端回归 `tmp/phase12-backend-full.log` 在本轮读取时没有最终汇总，本报告不判定其通过。前端92项及正式构建的口头声明不替代本轮未读取的完整原始结果。

## 交接

按 Stage1 失败路由修复 H1、H2；补跨来源所有权和撤销后重新发布恢复的真实回归，冻结实现后重新派 fresh reviewer 从 Stage1 开始。上述初审反例关闭及6项通过只覆盖其具体前提，不覆盖本轮新增反例。
