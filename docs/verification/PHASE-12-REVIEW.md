# Phase12 初轮独立审查

日期：2026-10-10。审查基线：`b42794ec0c2aedd15290ec88e8297371d9faaadb`，范围为本期工作树改动及新增文件，排除 `.codex/evolution/signals.jsonl`。使用 `.agents/skills/code-review/SKILL.md`。只审查，不修复、不提交。

**Stage 1 不通过；Stage 2 未执行。** 审查期间主线程继续修改实现，本报告是带源码摘要的初轮发现记录，不是最终工作树验收。不得用下述 31 项测试通过替代新增修改后的 fresh 审查。

## Stage 1：缺陷

### H1 HIGH：已发布资料删除完成后，恢复核验仍访问已删除的发布条目

- 契约：`Product-Spec.md:374` AC-060；`AGENT-ARCHITECTURE.md:404`，恢复须重放删除、重建允许索引、核验后开放。
- 位置：`globalmail-agent/backend/src/globalmail_agent/application/deletion.py:94` 仅删 release manifest 中目标条目；`application/restore_checks.py:46` 仍连接 release_items/head，`:50` 对旧 build 调用 eligible；`knowledge/build_checks.py:96` 首先读取文档。
- 复现：在 `KnowledgeDeletionTests` 随机 schema/临时对象目录运行 `test_document_purge_removes_index_cache_and_manifest_body`，该用例确认删除 completed；紧接着调用生产 `verify_restored_database(engine, store.root)`。
- 原始输出：

```text
post_document_delete_restore_verify_error= ServiceError document_not_found
```

- 结果：一个合法的已完成删除使后续恢复核验失败，备份不能开放。应重建合法发布快照并检查保留资料，不能仅修改 JSON manifest。
- 复现时 SHA256：`deletion.py = 542b9ebf1c534b563209fbcf473d24c9a2d00710ef527df787216ab130d7c2de`；`restore_checks.py = 608c09c4d48456375ec483cdddf9ab194b051a52104a56e865fee0177ee89959`。
- 动态状态：主线程已开始修改相关路径，未在本轮重新验收关闭；其修改出现 H3。

### H2 HIGH：最新日志包含备份之后创建的目标时，旧备份无法恢复

- 契约：`Product-Spec.md:463` AC-029、`:561` AC-078；`AGENT-ARCHITECTURE.md:404` 最新删除日志重放。
- 位置：初次复现版 `application/lifecycle.py:113` replay 对目标无条件 `_target_locked`；`application/lifecycle_inventory.py:23` 不存在即 404；`application/restore.py:73` 重放全部最新日志。
- 真实端到端复现：复用 `BackupRestoreTests` 创建随机隔离源库/目标库；先 `BackupStore.create` 执行真实 pg_dump；再创建会话并删除 completed；用最新 journal、生产 LifecycleService.replay 执行真实 pg_restore 到全新库/目录。
- 原始输出：

```text
source_delete_status= completed
real_restore_error= ServiceError deletion_target_not_found
restore_gate= restore_closed
```

- 结果：目标本来就不在快照中，却被当作不可恢复错误。应为合法的已不存在目标记录回执，保持幂等与封闭验证。
- 复现版 SHA256：`lifecycle.py = 6caead695130c2cedfaa83efe40f0a8e334dc576a99f0439f3e78ed620c8b9db`。
- 动态状态：之后观察到 `lifecycle.py:121` 新增 absent 分支，文件摘要已变为 `df099f9fa2361293da46159991698bc53c278c5658af056b7b564a2ff8bf3303`；本轮未重跑其真实恢复链路，标记“已修改、待复验”，不假报关闭。

### H3 HIGH：审查中新增发布快照修复，使没有发布 head 的草稿删除抛异常

- 契约：`Product-Spec.md:456` 导入资料必须有删除路径；`AGENT-ARCHITECTURE.md:396` 删除状态机。
- 位置：`application/lifecycle_revoke.py:51` 调用 `releases._write`；`knowledge/releases.py:80` 访问 `old_head['id']`，空 head 不含该字段。
- 复现：运行现有 `KnowledgeDeletionTests.test_shared_source_blocks_without_deleting_other_original`，此前批次通过；动态修改后单独运行在 request 阶段失败。
- 原始输出：

```text
  File ".../application/lifecycle.py", line 80, in request
    self._revoke(conn, row, record, saved["seq"])
  File ".../application/lifecycle_revoke.py", line 51, in revoke
    releases._write(conn, current, entries, profile, 'withdraw')
  File ".../knowledge/releases.py", line 80, in _write
    ... old_head["id"] ...
KeyError: 'id'
```

- 影响：删除不能进入 revoked；由于外部 journal 已 append、业务事务回滚，后续 API 会按水位差进入封闭，影响超过该资料。
- 复现后读取 SHA256：`lifecycle_revoke.py = 5508a2c531e07f61ab19dac94563bfcf6cd3f4595bba84c58de9fa70604a321f`。已通知主线程修复；本轮不预先判定新修复通过。

### M1 MEDIUM：共享内容阻断的引导缺少可执行依据和影响列表

- 契约：`AGENT-ARCHITECTURE.md:398` 要显示 blocked_dependencies 和影响列表；skill 要求提示对应真实行为。
- 位置：`frontend/src/components/shared/DeletionStatus.vue:4` 指示“替换其他资料的原件…再重试”；`backend/src/globalmail_agent/application/lifecycle_inventory.py:44` 枚举所有不可变历史版本，`:50` 其他未 deleted 文档任一历史 object/cache 引用仍构成阻断。`knowledge/documents.py:60` revise 只新增版本，不移除旧版本。
- 证据：即使其他资料新增合规原件版本，历史版本引用仍存在，文案承诺的解除机制未实现。两份分别进入 deleting 也仍满足 `lifecycle != 'deleted'`，不能自动解除相互阻断。前端 DeletionDialog 的 counts 只读数字字段，DeletionStatus 未渲染 API 的 blocked_document_ids，用户不知道具体关联资料。
- 验证范围：代码路径已核对；追加“共享后换新版本再重试”实测被 H3 提前阻断，未声称已跑通此路径。

## Stage 1：需求逐项覆盖与证据界限

以下覆盖本期 REQ-010 生命周期部分、AC-029/060/078 与架构约定；REQ-010 评测隔离/质量报告是既有范围及 Phase13，不以本轮结果替代其验收。

| 本期要求 | 结论 | 证据与验证方式 |
|---|---|---|
| 删除前显示影响、取消不改状态 | 部分实现 | `application/lifecycle.py:32` preview 只读；`tests/test_lifecycle_api.py:22` 经过真实 PG API 验证；共享影响列表见 M1；GUI 未实测 |
| 会话删除清理邮件、记忆、草稿、运行正文 | 当前已有实现，有限验证通过 | `application/lifecycle_inventory.py:59` 遍历会话持有者；`application/deletion.py:103` purge；`tests/test_lifecycle_core.py:25` 其他分支与对象验证。并非全库任意字段残留扫描证明 |
| 删除前停止任务，晚到 checkpoint/对象不可复活 | 部分实现 | `application/lifecycle_revoke.py:33` invalidate；`tests/test_lifecycle_core.py:108` 晚到检查点/对象拒绝。主线程告知 parser/模型 drain 正在实现，本轮未验证新增 writer_barrier |
| reset 为脚本/API 路径，生成独立空分支 | 当前已有实现，有限验证通过 | `api/lifecycle.py:14` action reset；`application/deletion.py:125` reset_branch；`tests/test_lifecycle_core.py:72` 新 conversation/branch 不同，重试不再新建。无页面 reset 入口 |
| 分支业务、事件、地址/库存/额度与无正文防重记录 | 当前已有实现，有限验证通过 | `application/deletion.py:44` scrub_business、`:125` reset_branch；`tests/test_lifecycle_business.py:15` 核验源快照清空、ledger ID/status/amount 不变、其他分支不变。未覆盖所有售后状态组合 |
| 原项目与源准备包不改 | 代码范围匹配，未做源包前后全量 hash | 删除只使用注册对象及 scope 表；`application/lifecycle_inventory.py:86` 对象范围；测试验证其他分支，不冒充源包 hash 证据 |
| 知识原件、解析、块、向量、缓存、引用正文 | 部分实现 | `application/deletion.py:69` 清理；`tests/test_lifecycle_knowledge.py:19` 真实 PG/本地解析/合成向量验证。已发布删除的恢复见 H1，无 head 删除见 H3 |
| 知识共享原件须阻止读取且不能连带删除 | 部分实现 | `application/lifecycle_inventory.py:49` 共享枚举、`lifecycle_revoke.py:58` 对象撤销；`tests/test_lifecycle_knowledge.py:33` shared-source 阻断且原件保留。解除路径见 M1 |
| 模型看过但未引用内容也纳入依赖清理 | 代码实现已核对，端到端组合未验证 | `application/lifecycle_inventory.py:60` 根据 agent_run_dependencies 扩至整个会话；`application/content_dependencies.py:7` 登记依赖并检查写门；本轮未额外执行“看过但没引用再复制到后轮”的模型协议组合 |
| 图片原件/派生/检查点/草稿和模拟回复清理 | 当前已有实现，有限验证通过 | `tests/test_lifecycle_attachments.py:32` 真实 PG 图片删除；`application/lifecycle_inventory.py:40` 图片根及会话派生持有者；物理清理同 purge_local |
| 图片删除不抹已发生操作，不导致重复办理 | 部分实现 | scrub_business 保留无正文主键/状态；分支账本测试通过；未实测“图片删除后重复提交同一售后动作”的完整链路 |
| 状态区分 revoked/purging/verifying/completed 与失败重试 | 当前已有实现，API 有证据 | `application/lifecycle.py:26` 输出；`api/lifecycle.py:51` 状态/重试；`frontend/src/api/lifecycle-api.ts:17` 标签；`tests/test_lifecycle_api.py:22` 覆盖确认/重试。GUI 待验 |
| Langfuse 在途导出/接受未知/异步删除确认 | 协议实现已测，真实远端未验 | `observability/purge.py:29` revoke+export_lock；`:110` 删除前完整 ID 接收核对、两次空读取；`tests/test_observability_purge.py:72` 等 HTTP transport 用例。本轮不访问正式 trace，不将 mock HTTP 当真实自托管验收 |
| 独立 journal、崩溃缺回执封闭 | 当前已有实现，有限验证通过 | `adapters/deletion_journal.py:89` HMAC/水位校验；`application/journal_gate.py:7` receipts 对比；`tests/test_lifecycle_api.py:41` 未提交 tombstone 后 HTTP 封闭 |
| 联合备份与全新库/目录恢复、最新日志防复活 | 不通过 | `adapters/backup_store.py:89` 联合快照与摘要；`application/restore.py:36` 新目标及默认封闭；真实 PG archive 正常链路测试通过，但 H1/H2 反例成立 |
| 普通 withdraw/revoke 与彻底删除不同 | 动态修改待验 | `application/lifecycle.py:127` 新增 replay_revocation 分支在审查过程中写入；未以最初测试结果替它背书 |
| 页面继承既有组件、删除后清草稿、刷新状态/重试 | 静态接入已确认，渲染与交互未验 | `frontend/src/views/mail-agent/index.vue:25`、`views/knowledge/index.vue:187`、`components/mail-agent/ImageEvidenceDrawer.vue:47` 接入；`components/shared/DeletionDialog.vue:1` 复用 ElDialog。未取得隔离 GUI 地址，未进行截图/邻居页面对比 |

## Spec 漂移与未执行部分

新增 lifecycle API、journal、cleanup worker、联合备份/恢复脚本均有本期规划依据，未发现明确的无需求新增产品功能。原文依据为 `docs/planning/PHASE-12-IMPLEMENTATION.md:9`–`:16`。这不代表已完成 Stage2 全量质量审查。

Stage1 已有 HIGH，按 skill 停止 Stage2：不提供命名/复杂度/300行规则、安全扫描通过结论，不进行 Stage2 邻居页面视觉对比。真实 Langfuse 删除、所有来源字段残留扫描、在途模型/解析 drain、新增修复后的完整测试和 GUI 均不得标为已验收。

## 测试与编译原始输出

隔离方式：只读取 `.local-data/runtime/settings.json` 的 database_url 注入 `GLOBALMAIL_TEST_DATABASE_URL`，不打印值；`PYTHONPATH=src;tests`。ProtocolFixture 使用随机 schema/临时目录；BackupRestoreTests 使用随机独立数据库。未写正式业务表，未调用付费模型或正式远端 trace。

命令：

```text
.venv/Scripts/python.exe -m unittest test_lifecycle_core test_lifecycle_business test_lifecycle_attachments test_lifecycle_knowledge test_lifecycle_api test_backup_restore test_observability_purge
```

原始输出：

```text
...............................
----------------------------------------------------------------------
Ran 31 tests in 110.958s

OK
```

这是运行开始时 Python 加载的版本，随后 H3 证明工作树已发生变化，不能视为最终 31 项回归通过。

后端命令 `.venv/Scripts/python.exe -m compileall -q src`，原始输出：

```text
compileall exit=0
```

前端命令 `pnpm exec vue-tsc --noEmit`，原始输出为空，退出码 `0`。本轮未运行 Vite 产物构建，不把类型检查等同完整构建。

## 交接

主 Agent 按 Stage1 失败处理；修复 H1/H2/H3、共享阻断引导后，冻结本期工作树并重新派 fresh code-reviewer 从 Stage1 开始。H1/H2/H3 的动态修订不在本轮自动判为关闭。
