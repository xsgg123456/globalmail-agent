# Phase12 第三轮独立审查

日期：2026-10-10。基线 `b42794e`，范围为 Phase12 工作树 diff 与新增实现，排除用户 `.codex/evolution/signals.jsonl`。fresh reviewer 使用 `.agents/skills/code-review/SKILL.md`；未修改产品实现、未提交、未 spawn。

**Stage 1 FAIL：1 项 HIGH。Stage 2 未执行。** 本轮不是 Phase12 验收通过证明。主线程提出离线恢复疑点后，审查者独立核对代码并用真实临时 PostgreSQL 数据库复现；不是依据主线程判断直接采纳结论。

## Stage 1：H1 HIGH——崩溃遗留的过期任务使离线日志恢复无法执行

契约：`AGENT-ARCHITECTURE.md:400` 要求停止/隔离持有者后清理；`:404` 要求封闭状态下重放最新撤销/删除并核验后开放。`docs/planning/PHASE-12-IMPLEMENTATION.md:12` 联合恢复步骤必须可完成。`Product-Spec.md:463` AC-029、`:374` AC-060、`:561` AC-078 的晚到任务及恢复防复活依赖这条恢复路径。

生产可达条件：worker 已领取任务，删除日志已经落盘但撤销事务尚未提交，此时进程崩溃。数据库保留 running 任务和租约持有者，独立日志比事务回执新。这不是仍在线的工作进程。

阻断链及证据：

1. `globalmail-agent/backend/src/globalmail_agent/worker/leases.py:40` 的生产 `claim` 将 jobs/run 置 running 并登记租约；`:100` 的 `recover_expired` 本可回收过期任务。
2. `globalmail-agent/backend/src/globalmail_agent/application/lifecycle.py:79` append 独立日志，`:80` 才执行事务内撤销。二者之间的失败会留下意图无回执。
3. `globalmail-agent/backend/src/globalmail_agent/application/journal_gate.py:18` 比较回执与日志，不一致抛 `journal_replay_required`。`main.py:55` 将 available 设 false，`:58` 因此不启动 worker；过期恢复位于 `worker/agent_runner.py:183`，无法由正常启动触发。
4. 离线入口 `application/replay_journal.py:24` 调用 `adapters/backup_store.py:48` 的 `lock_database`。该函数虽检查其他客户端数量，但在 `:60` 又无条件拒绝 public 库中 running/leased 行，`:62` 抛 `backup_active_tasks`，没有判断租约是否过期。
5. 即使只移除上述复用函数中的拒绝，`application/replay_journal.py:26` 至 `:34` 仍无条件拒绝相同任务行及任意非空 lease_owner。用于清除继承状态的 `freeze_inherited_work` 位于 `:50`，永远到不了。

结果：在没有任何其他数据库客户端、任务租约早已过期的情况下，官方同库恢复 CLI 仍反复拒绝执行；等待更久没有作用，重启应用也不会触发过期回收。无现成备份时不能通过已提供的产品入口恢复该库；需要人工改状态或调用内部函数。未发现内容泄漏，但删除意图无法完成、应用持续封闭，属于核心恢复功能缺失。

### 独立动态证据

脚本：`tmp/phase12-review3-offline.py:17`。日志：`tmp/phase12-review3-offline.log:1`。

- 使用 `BackupRestoreTests` 创建随机独立数据库并执行真实 Alembic 迁移，不写正式库。
- 使用生产 `ConversationService.create`、`LeaseService.claim` 创建并领取任务；没有直接 SQL 伪造 running 状态。
- 只把生产租约期限推进至过去一天，模拟进程退出后等待租约到期。
- 在生产 `LifecycleService.request` 的 `_revoke` 入口注入进程失败，独立 journal append 和数据库事务回滚均走真实实现。
- 关闭本测试连接池后验证其他数据库客户端为 0，连续两次执行生产 `JournalRecovery.run`；每次执行前均确认 journal gate 仍封闭。没有启动模型、没有调用付费模型、没有访问正式 trace。

原始输出：

```text
other_database_clients= 0
production_claimed_expired_running_jobs= 1
offline_replay_attempt= 1 error= backup_active_tasks
offline_replay_attempt= 2 error= backup_active_tasks
runTest (__main__.OfflineRepro.runTest) ... ok

----------------------------------------------------------------------
Ran 1 test in 7.508s

OK
```

这里 `OK` 表示反例被成功复现，**不表示恢复成功**。

### 修复完成标准

离线恢复必须分清真正仍能写入的进程与数据库中崩溃遗留状态。先确认/隔离在途写入者、设置封闭门，再安全冻结遗留任务并重放；同时保留对真正在线客户端/写入者的拒绝。不能只删除 `JournalRecovery._offline` 或 `lock_database` 中一个判断，也不能单凭“当前没连接”忽略正在数据库外等待模型的活进程。真实回归至少包括：过期 running + 缺回执成功恢复、孤立 slot 持有者、知识任务崩溃、真正在线写入者仍拒绝、重复重放及晚到写入继续被栅栏拦截。

现有 `tests/test_backup_restore.py:231` 的测试名宣称 active worker，但 `:249` 只是直接把数据库行设 running，未启动 worker、没有保持活连接或检查过期租约；它不能证明真实在线/离线判别正确，反而把本缺陷预期化。这是本次 HIGH 的证据补充，不代表已执行 Stage2 全面测试质量审查。

## Stage 1：需求覆盖记录及停止边界

本轮读取了 REQ-005/008/010/013/014 相关原文、AC-029/060/078、架构 7.3 和恢复实现、Phase12 规划及前两份审查。下表逐项列明本期要求；发现 HIGH 后停止，未完成的核验明确标注，不能把“代码存在”视作“完整实现通过”。非本期检索语义质量、图片语义质量及 Phase13 评测不重复验收。

| 本期要求 | 本轮状态 | 证据/待核验范围 |
|---|---|---|
| REQ-010 删除影响预览、取消无写 | 已读实现，未独立动态验收 | `application/lifecycle.py:32`；GUI 取消证据未在本轮亲自复验 |
| REQ-010/AC-029 会话邮件、记忆、草稿及运行正文 | 已读清理链，未判整体通过 | `application/lifecycle_inventory.py:64`、`application/deletion.py:103`；完整持有者逐字段审查因 HIGH 停止 |
| REQ-008 停写和晚到结果栅栏 | 已读撤销路径，未独立动态验收 | `application/lifecycle_revoke.py:27` 停止关联任务；真实 writer drain 不引用主线程口头声明作本轮证明 |
| REQ-010 reset、独立分支与幂等 | 已读实现，未独立动态验收 | `application/lifecycle.py:48`、`application/deletion.py:130` |
| REQ-010 分支业务清理/占用释放/防重保留 | 已读实现，未判组合完整通过 | `application/deletion.py:49`、`:130`；业务后续重办组合未在本轮重做 |
| REQ-010 源准备包不变 | 静态路径有限匹配，未独立做摘要对照 | `application/deletion.py:124` 仅删除受管对象路径 |
| REQ-005/AC-060 原件、解析、块、向量、缓存及引用 | 已读实现，未判整体通过 | `application/deletion.py:69`；恢复路径受本轮 H1 影响 |
| REQ-005 模型读过但未引用/跨 scope 所有权 | 第2轮修复静态匹配，未独立重跑 | `application/lifecycle_inventory.py:77` 明确排除依赖来源对象；`tests/test_lifecycle_sources.py:13`、`:32` 有反例回归 |
| REQ-005 普通下架与永久删除、共享原件阻断 | 已读关键路径，未判整体通过 | `application/lifecycle_replay.py:17` receipt 幂等；`application/lifecycle.py:179` 阻断处理 |
| REQ-014/AC-078 图片及派生内容清理 | 已读目标枚举，完整交互/账本组合未验 | `application/lifecycle_inventory.py:39`、`application/deletion.py:16` |
| REQ-014 撤销后继续处理剩余会话 | 未完成独立动态核验 | 存在 `tests/test_lifecycle_attachments.py`，不能用用例存在当通过 |
| REQ-013 远端追踪、SDK 缓冲及在途导出 | 未完成本轮核验 | `observability/purge.py` 存在；未重做真实远端，不冒用既有探针为本轮证明 |
| 独立 journal、无回执封闭 | 独立实测匹配 | `application/journal_gate.py:18`，本轮两次确认 `journal_replay_required` |
| 联合备份/最新日志重放/核验开放 | 部分实现，恢复闭环不通过 | `application/restore.py:73` 有重放；同库离线恢复 H1 实测失败 |
| 离线同库重放和失败重试 | 不通过 | `application/replay_journal.py:23`、`adapters/backup_store.py:60`，本轮两次相同拒绝 |
| API/GUI 状态、危险确认、清草稿与重试 | 本轮未完成动态核验 | Stage1 HIGH 后停止；没有执行对话框 X→重开，不宣称已覆盖 |
| UI 继承既有组件/无产品测试控制界面 | 本轮未完成渲染核验 | Stage2 邻居视觉对照未执行 |

## 前两轮修复状态

- 第2轮 H1：`application/lifecycle_inventory.py:78` 排除 `agent_run_dependencies.source_object_id`，能对应之前的误删根因；本轮未重跑其动态用例，不给整体所有权审查通过结论。
- 第2轮 H2：`application/lifecycle_replay.py:17` 查询 receipt，`:22` 校验 seq，`:24` 返回 already_applied；`tests/test_lifecycle_knowledge.py:13` 覆盖合法重新发布。永久删除仍走 `application/lifecycle.py:131` 的独立处理链，未按普通撤销 receipt 一概跳过。静态匹配修复目的，本轮未另跑联合备份再发布组合。
- 初审 H1/H3：`application/lifecycle_revoke.py:47` 检查 head 后创建保留条目的新发布快照；初审 H2：`application/lifecycle.py:121` absent 写 receipt。已读修改，但不把前轮结果替换为本轮新实测。

## 未执行部分、编译与交接

按 skill 的“Stage1 有 HIGH 即停止”要求，**Stage2 未执行**：无代码质量/命名/类型/300行规则总体结论，无安全扫描通过结论，无实际邻居页面视觉对比，也未执行 X 关闭后重开。完整 Spec 漂移扫描未完成，不能宣称不存在 scope creep。

本轮未运行编译，故没有新的编译原始输出；未重跑全量 suite。主线程正在运行的冻结三分片没有被本报告判为通过；旧源码加载的全量日志和此前配置错误日志均未用于通过结论。反例唯一原始运行输出完整附于上文。

交接：先修复 Stage1 H1，并补真实可达的崩溃/过期/在线写入者回归；冻结后 fresh reviewer 从 Stage1 重审，再做 Stage2 与独立 GUI X/邻居视觉验证。不得以第三轮报告宣称 Phase12 完成。
