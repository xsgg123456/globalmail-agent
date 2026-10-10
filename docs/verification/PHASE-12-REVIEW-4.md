# Phase12 第四轮独立审查

2026-10-10。基线 `b42794e`；范围为 Phase12 工作树改动和新增文件，排除用户 `.codex/evolution/signals.jsonl`。使用 code-review 和 playwright skill，只审查及写证据，没有修复、spawn 或 commit。

**Stage 1 不通过：1 个 HIGH。Stage 2 未执行。** 前三轮的关键后台反例已在本轮独立回归通过，但图片删除仍漏清浏览器持有的人工草稿，不能宣布完整删除完成。

## Stage 1：H1 HIGH，图片删除完成后仍显示含被删图片正文的个人草稿

需求原文：`Product-Spec.md:545` 要求“同步处理……草稿/模拟回复及追踪衍生内容。删除完成需验证无残留/晚到复活”；`:561` AC-078 要求旧内容不复活。`AGENT-ARCHITECTURE.md:396` 将 Draft 纳入正文衍生清理。

实现差异与根因：

- `globalmail-agent/frontend/src/components/mail-agent/ImageEvidenceDrawer.vue:47` 将删除撤销交给 clearDeleted；`:61` 只清图片 Drawer 自身的页面、URL、更正输入和 pending，然后发送 changed。
- `globalmail-agent/frontend/src/views/mail-agent/index.vue:28` 的 changed 只调用 `:80` refreshCurrent，未清受影响会话的个人草稿。
- `globalmail-agent/frontend/src/composables/create-mail-workbench.ts:69` 仅在 humanInputs 不存在时初始化；`:86` 明确保留已有非空草稿，服务器 review 变 null 也不清理。`:265` 的 forget 清理仅由会话删除接入，图片删除没有调用。共享实例由 `useMailWorkbench.ts:8` 保存，导航不会自然消除此正文。

独立真实复现，未 mock 删除或数据库：

1. 隔离 API 18189 上传600×300合成PNG，图中唯一文字 `REVIEW4_IMAGE_PRIVATE_TEXT`；正常创建带图会话 `d3b96611-88e4-4d84-ae83-4233d99120c3`，附件 `a311b048-478b-4b59-afff-d73f1142b199`。
2. 独立 Playwright CLI session `review4` 在15179打开该会话；真实点击“人工接管”，把图中文字填入“人工回复正文”，点击“保存草稿”。
3. 打开图片 Drawer，点击“彻底删除图片”并确认。由于隔离服务关闭自动worker，向该请求真实 retry API 推进清理。
4. API返回 completed；会话 GET 返回 `review: null`。浏览器已通过轮询显示“删除完成”，图片显示“已移除”，人工回复输入仍为 `REVIEW4_IMAGE_PRIVATE_TEXT`；关闭两个对话框之后依然保留。

关键原始输出：

```json
{"id":"2dcd1849-5c6f-408f-a51c-582e3fadcc98","status":"completed","target_type":"attachment","target_id":"a311b048-478b-4b59-afff-d73f1142b199","impact":{"objects":5,"runs":1,"conversations":1,"versions":0,"blocked_document_ids":[],"external_copies_included":false,"business_ledger_retained":true,"branch_reservations_released":false},"error_code":null}
{"server_review":null}
```

上述第一行摘取实际响应的相关字段，完整原始响应见[API响应](artifacts/phase12/review4-image-completed.json)。[服务器详情](artifacts/phase12/review4-server-detail.json)、[完整DOM快照](artifacts/phase12/image-completed-draft-residue.yml)、[完成状态截图](artifacts/phase12/image-completed-draft-residue.png)、[关闭后仍残留草稿](artifacts/phase12/draft-after-close.png)共同证明服务端已清理、客户端仍持有正文。快照同时显示 completed 和输入框哨兵。没有执行重新保存或发送，因此不宣称已实测正文重新写回数据库。

复现源码 SHA256：ImageEvidenceDrawer.vue=`60f57aa1eb643cf3595ad11630cd5bdc5a222f530c49fbb1224d3b8b1ca65357`；create-mail-workbench.ts=`10855116cd67fbbb71333650907dcbc1f182ffb035692a3cb8546a50fdc68aff`。

环境边界：该隔离API仍加载两轮后台修复前代码，本例不涉及知识来源枚举或 journal recovery；实际验证的是当前HMR前端与正常图片删除路径。不能用此实例证明那些后台修复。未操作正式18080/15173或原观测3001；未调用付费模型。

修复验收标准：任何来源彻底删除都要使受影响会话的客户端正文持有者失效，包括人工草稿/备注、建议快照、运行详情及晚到请求；保留会话本身和无关分支。至少补图片删除与知识删除影响会话、跨页面驻留、删除前详情晚到的真实交互回归。知识删除同类草稿风险由代码判断，本轮只动态证明图片路径，不将其另列已实测缺陷。

## Stage 1：本期条目逐项对照

仅核对 DEV-PLAN Phase12 分配的生命周期增量；不把 REQ-005 检索质量、REQ-008 原运行台、REQ-010 模型评测、REQ-013 全部既有观测及 REQ-014 图片理解质量归为本轮已验收。

下表后台相对路径均位于 `globalmail-agent/backend/src/globalmail_agent/`。

| 本期条目 | 结论 | 证据与边界 |
|---|---|---|
| REQ-010 三类影响预览、取消不变 | 实现匹配，GUI部分独立验证 | `application/lifecycle.py:33` 只读枚举；`api/lifecycle.py:34`；本轮真实会话预览→X关闭→再次打开成功，旧GUI取消80表哈希证据见 PHASE-12-GUI.md，不冒称本轮重做哈希 |
| REQ-010 / AC-029 会话正文、记忆、检查点、运行清理 | 后台路径匹配；整体客户端清理不通过 | `application/deletion.py:103`、`:151`；本轮真实备份删除恢复及来源保留通过；跨来源客户端缺口见H1 |
| REQ-008 停写、晚到checkpoint与对象拒绝 | 静态匹配，过期崩溃独立验证 | `application/lifecycle_revoke.py:28`、`application/content_fence.py:7`、`worker/agent_runner.py:59`；真实claim过期崩溃重放通过；本轮未重跑完整模型在途/解析器组合 |
| REQ-010 reset仅模拟、独立空分支、幂等 | 实现存在，未本轮完整动态重验 | `application/lifecycle.py:53`、`application/deletion.py:129`；`tests/test_lifecycle_core.py:74` 有对应真实PG用例 |
| REQ-010 业务清理、释放预留、防重和其他分支 | 实现存在，未本轮完整动态重验 | `application/deletion.py:49`、`:129`、`:195`；`tests/test_lifecycle_business.py:12` 覆盖源快照及账本ID保留 |
| REQ-010 源包不变 | 路径范围匹配，未重做源包摘要 | `application/deletion.py:123` 只删ObjectStore ID路径；本轮未读写正式源包 |
| REQ-005 / AC-060 原件、解析、向量、缓存、引用、运行衍生清理 | 后台关键反例通过；客户端全部持有者未通过 | `application/deletion.py:69`；独立已发布A删除保留B并恢复核验通过；H1显示客户端清理设计仍不完整 |
| REQ-005 模型读过未引用仍纳入、跨scope来源不误删 | 本轮独立回归通过 | `application/lifecycle_inventory.py:59`、`:78`；真实search_reference后删除会话、同case读取A/B删A保留B均通过 |
| REQ-005 下架与彻底删除区分、合法重新发布 | 本轮关键回归通过 | `application/lifecycle_replay.py:17` receipt幂等；独立生产withdraw→重新publish→replay仍保留head |
| REQ-005 共享PDF阻断及影响ID | 静态及既有GUI证据匹配 | `application/lifecycle.py:179`、`frontend/src/components/shared/DeletionStatus.vue:4`；历史GUI已真实blocked，本轮未再次处理共享PDF |
| REQ-014 / AC-078 图片及草稿衍生清理 | **部分实现，不通过** | 原图已移除、服务端review为空，客户端草稿仍残留，H1真实GUI证明 |
| REQ-014 撤销后继续处理、保留无正文账本 | 代码存在，未本轮完整动态重验 | `application/human_review.py:16`、`attachments/evidence.py:40`；`tests/test_lifecycle_attachments.py:14`覆盖后续会话，未以用例存在当整体通过 |
| REQ-013 远端trace、在途/未知确认和缓冲互斥 | 已读协议实现，动态边界未扩大 | `observability/purge.py:28`、`:61`、`:105`持久pending；既有actual证据早于最后lost-response硬化，本轮没有操作真实远端 |
| 独立journal、回执、水位缺失封闭 | 独立崩溃回归通过 | `adapters/deletion_journal.py:89`、`application/journal_gate.py:7`；append后事务故障、过期claim恢复实际通过 |
| 联合备份、全新目标、最新日志重放核验开放 | 本轮关键真实PG恢复通过 | `adapters/backup_store.py:78`、`application/restore.py:36`；新目标不存在于旧快照的真实dump/restore用例通过 |
| 离线同库重放、活跃任务/连接拒绝 | 第三轮反例独立关闭 | `application/replay_journal.py:23` 只拒绝未过期lease；本轮真实claim后过期恢复成功，在线连接/未过期lease拒绝通过 |
| GUI危险确认、失败重试、浏览器草稿清理 | 部分实现 | 对话框X→重新打开独立通过；后台completed真实可见；草稿H1失败。History错误/重试沿用已有GUI证据，没有重复冒称独立完成 |
| 不新增产品测试控制面板 | 检查范围匹配 | `api/lifecycle.py:14` reset为API action，UI只有资源删除与清理记录；未发现本期明确无需求产品功能 |

## 前三轮修复与本轮独立原始测试

已独立关闭：发布head保留合法资料、旧备份缺目标receipt、跨scope来源误删、已提交withdraw覆盖后续publish、离线过期running永久卡死。无head草稿和共享PDF文案为静态核对加前轮真实证据，本轮不重复称独立动态关闭。

使用仓库 `.venv/Scripts/python.exe`、`PYTHONPATH=src;tests`；连接配置仅赋环境变量，随机schema/全新临时库及对象目录，fixture负责清理。来源所有权/知识用例仅mock远端purge，实际检索/数据库/对象/发布均真实；CrashRecovery实际调用生产LeaseService.claim，非凭空造不可达状态。

原始输出（[完整日志](artifacts/phase12/review4-targeted.txt)）：

```text
test_expired_claim_after_process_crash_is_fenced_and_replayed (test_journal_crash_recovery.CrashRecoveryTests.test_expired_claim_after_process_crash_is_fenced_and_replayed) ... ok
test_case_delete_keeps_shared_knowledge_original_used_without_citation (test_lifecycle_sources.SourceOwnershipTests.test_case_delete_keeps_shared_knowledge_original_used_without_citation) ... ok
test_deleting_read_document_cleans_case_outputs_but_keeps_other_read_document_original (test_lifecycle_sources.SourceOwnershipTests.test_deleting_read_document_cleans_case_outputs_but_keeps_other_read_document_original) ... ok
test_deleting_one_published_document_preserves_other_eligible_release_entry (test_lifecycle_knowledge.KnowledgeDeletionTests.test_deleting_one_published_document_preserves_other_eligible_release_entry) ... ok
test_replaying_applied_withdraw_does_not_undo_later_legal_republication (test_lifecycle_knowledge.KnowledgeDeletionTests.test_replaying_applied_withdraw_does_not_undo_later_legal_republication) ... ok
test_recovery_refuses_live_connection_and_active_worker (test_backup_restore.BackupRestoreTests.test_recovery_refuses_live_connection_and_active_worker) ... ok
test_newer_deleted_target_absent_from_old_backup_has_receipt (test_backup_restore.BackupRestoreTests.test_newer_deleted_target_absent_from_old_backup_has_receipt) ... ok

----------------------------------------------------------------------
Ran 7 tests in 59.739s

OK
```

第一次误写配置相对路径导致7 skipped，随后修正并运行以上0 skipped真实结果；第一次不算通过。本轮不重复全量suite，也不把旧代码进程的日志作为最终冻结结果。

## Stage 2、编译与交接

按 skill 的 Stage1 HIGH 停止规则，**Stage2未执行**。没有输出整体质量、300行规则、安全扫描、测试真实性全覆盖或邻居页面视觉对比的通过结论。已阅读 `frontend/scripts/lifecycle-drafts.test.ts:7`：只验证会话forget，未覆盖图片/知识删除保留会话的草稿边界，H1证明该盲区存在。

本轮未运行编译，无新编译原始输出；主线程此前前端92/92及build结果不能代替本轮H1修复后的重验。未将先前全量测试或真实Langfuse探针扩展为当前最终源码通过。

交接：修H1后冻结，再fresh reviewer从Stage1开始，之后执行Stage2、邻居视觉及完整四步验证。review4浏览器及该合成样本留给主线程定位；仅新增本报告、证据和tmp复现脚本，没有修改产品实现。正式服务未动。
