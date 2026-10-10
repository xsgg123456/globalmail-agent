# Phase12 第五轮独立审查

2026-10-10。基线 `b42794e`，审查 Phase12 未提交实现。fresh code-reviewer 使用 code-review、playwright skill；未修产品代码、未 commit、未 spawn。已读取 AGENTS、需求对应条目、架构4.4/7.3/9、Phase12计划、实施规划、四份历史审查及GUI/操作说明。`docs/architecture/Design-Brief.md` 不存在，UI基准为 Spec 和既有页面。

**Stage1 FAIL：1项 HIGH。Stage2 未执行。** 第四轮旧草稿残留的原始反例本轮关闭，但剩余会话的人工回复入口被锁死。主线程收到本轮发现后已修改按钮条件；本报告保留修复前事实，不作为该修改的验收证明。

## Stage1：H1 HIGH——图片删除后保留会话无法再次人工接管、保存或发送

需求：`Product-Spec.md:408` 要求“将人工回复和备注写入会话”，`:444` 要求“为正常客服完成回复……提供明确操作”；`:545` 删除对象是图片及其派生内容，不能把保留的客户会话变成不可操作。`DEV-PLAN.md:276` 的客户图片删除不能破坏剩余会话的正常处理。

实现链路：

- `globalmail-agent/backend/src/globalmail_agent/application/deletion.py:12` 清理旧 `human_reviews` 并将状态设为 closed；`application/conversation_queries.py:79` 按删除manifest排除旧人审，正确返回 `review=null`。
- `globalmail-agent/backend/src/globalmail_agent/application/lifecycle_revoke.py:32` 更新输入版本、权限代次、运行门和调度状态，但保留 `human_claimed=true / processing_owner=human_review`。图片删除后会话仍 `lifecycle=open`。
- 修复前 `globalmail-agent/frontend/src/views/mail-agent/index.vue:8` 的按钮条件为 `busy || conversation.lifecycle !== 'open' || (conversation.human_claimed && conversation.processing_owner === 'human_review')`，因此不能再次接管。
- 同文件`:20` 的 `can-reply` 要求 `detail.review?.status === 'open'`；`components/mail-agent/StaffReply.vue:14` 显示“请先人工接管后回复”，`:15` 同时禁用保存和发送。用户既没有人审记录也无法创建新的记录，刷新无效。
- 后台 `application/human_review.py:24` 的 takeover 可以创建新记录，`tests/test_lifecycle_invalidation.py:50` 直接调用该方法通过；这不能证明 UI 的按钮可达。H1是正常客服核心通信链路中断，不只是文案问题。

独立真实复现：

1. 仅使用 API18189 / Web15179，合成600×300 PNG文字 `REVIEW5_IMAGE_PRIVATE_TEXT`，正常上传并创建会话 `541ac682-46f9-48e6-a733-380d948b46c9`，图片 `b985a366-f017-4ec6-8fa4-8c7655d58a01`。
2. 独立 Playwright CLI session `review5` 点击人工接管，在回复输入填写图中文字并真实保存草稿。
3. 点击图片→彻底删除图片→确认；隔离服务 `start_worker=False`，明确调用真实 retry API推进清理，没有伪造 completed。
4. 请求 `094ba904-3520-4974-88fa-4fd689ea5ae1` 返回 completed，Dialog完整显示“删除完成”，图片显示已移除，旧草稿已清空。
5. 关闭Dialog并点击邮件详情刷新，人工接管、保存草稿、发送模拟回复仍全部 disabled，提示“请先人工接管后回复”。没有使用API绕过UI来宣称用户路径成功。

实际响应关键字段：

```json
{"status":"completed","journal_seq":1,"impact":{"conversation_ids":["541ac682-46f9-48e6-a733-380d948b46c9"]}}
{"lifecycle":"open","human_claimed":true,"processing_owner":"human_review","content_revision":1,"review":null}
```

上面为响应字段摘录；完整[删除响应](artifacts/phase12/review5/api-completed.json)、[服务器详情](artifacts/phase12/review5/server-detail.json)、[完成状态截图](artifacts/phase12/review5/image-completed-locked.png)、[完成DOM](artifacts/phase12/review5/image-completed-locked.yml)、[关闭并刷新后DOM](artifacts/phase12/review5/after-refresh.yml)保留原始证据。已实际查看截图。截图中旧草稿空白、完成Dialog可见；DOM进一步证明三个按钮disabled。

取证时工作台文件SHA256为 `9c9dcb476ef7180e4dd62fac059a77ad5ffdbbd0bd30cf7ec6f5f164043a0287`。22:22取证后主线程开始加 `detail?.review?.status === 'open'` 条件，此后源码不同，不覆盖上述FAIL。

修复标准：清理完成后允许显式建立新的人审记录；保留停止自动运行和旧内容失效语义。补真实组件/浏览器“保存旧草稿→删图→完成→重新接管→保存/发送新回复”路径，不能只调用service证明。知识删除影响会话应验证同一状态组合。本轮知识路径只由共享状态逻辑推断，没有另称已实测。

## Stage1：本期全部交付逐项对照

仅覆盖 Phase12 生命周期增量，不将模型语义、检索精度、Phase13评测或其他AC列为通过。下表后台路径相对 `globalmail-agent/backend/src/globalmail_agent/`。

| 本期条目 | 本轮结论 | 代码与验证证据 |
|---|---|---|
| 三类删除影响、取消不写 | 实现匹配，部分独立验证 | `application/lifecycle.py:33` preview；真实图片GUI显示5对象/1运行/1会话；`tests/test_lifecycle_core.py:34` 只读预览与其他分支保留通过。GUI取消全表哈希本轮未重做，沿用历史有界证据 |
| AC-029 会话邮件、记忆、草稿、正文运行记录 | 独立后台用例通过 | `application/deletion.py:103` purge、`:151` verify；core的checkpoint、inline holders和删除后不可读用例通过，不能等同所有客户端组合通过 |
| 撤销停写、晚到对象和checkpoint拒绝 | 独立持久栅栏用例通过 | `application/lifecycle_revoke.py:28` invalidate；`application/content_fence.py:7`、`:28`；core late checkpoint/object测试通过。本轮未重做完整模型在途drain |
| 模拟reset、独立空分支及幂等 | 独立通过 | `application/lifecycle.py:53` action限制、`:66` simulation检查；`application/deletion.py:129` reset；core reset真实PG用例通过 |
| 分支业务清理、库存/额度释放、无正文防重账本、其他分支 | 独立用例通过，组合有界 | `application/deletion.py:49`、`:129`、`:195`；`test_lifecycle_business.py:12` 源快照/账本/其他分支保留通过；未将其扩大为所有售后重新办理组合已验 |
| 外部源准备包不变 | 静态边界匹配 | `application/deletion.py:123` 只按受管ObjectStore ID删文件；core reset保留source用例通过。未写正式源包，也未重做正式源包全量摘要 |
| AC-060 原件、解析、块、向量/缓存、引用正文 | 独立关键后台用例通过 | `application/deletion.py:69` purge_knowledge；知识删除5项包含已发布A删除保留B、无head共享阻断、parse/index/cache/manifest清理 |
| 模型读过未引用仍登记、不能误删外部共享来源 | 独立通过 | `application/lifecycle_inventory.py:59` 按run依赖扩展、`:78` 排除source_object_id；source ownership两项真实检索/删除/保留另一资料通过 |
| 普通下架与彻底删除区分、下架后合法重发布 | 独立关键用例通过 | `application/lifecycle_replay.py:17` receipt幂等；withdraw→publish→replay合法head保留用例通过 |
| 共享PDF阻断、明确关联资料 | 后台独立通过，GUI沿用旧证据 | `application/lifecycle.py:183` blocked判断；`frontend/src/components/shared/DeletionDialog.vue:11` 关联ID；共享源测试通过，未重复完整GUI阻断重试 |
| AC-078 图片原件、派生、模型/草稿/模拟回复清理 | 原R4反例独立关闭，整体人工继续路径失败 | `application/deletion.py:16`、`application/content_revision.py:6`；真实API和DOM均无旧草稿，Dialog完整完成；但H1导致会话无法继续人工通信 |
| 图片删除后剩余会话/图片、保留业务审计 | 后台通过、UI不通过 | `tests/test_lifecycle_attachments.py:14` service层后续处理通过；本轮GUI H1证明UI不可达，不以后台通过代替用户路径 |
| 远端trace清除、未知接受和缓冲/导出互斥 | 历史证据有界，本轮未独立动态重验 | `observability/purge.py:28` 锁及清理编排；已有actual探针早于最终源码，本轮不访问正式trace，未声称最终真实远端验收 |
| 独立journal、水位/事务回执、缺失封闭 | 独立崩溃核心用例通过 | `adapters/deletion_journal.py:89`、`application/journal_gate.py:7`；真实claim→过期→缺回执恢复用例通过 |
| 数据库+对象+配置备份、全新目标、最新日志重放后开放 | 存在实现与前轮动态证据，本轮未完整重跑 | `adapters/backup_store.py:78`、`application/restore.py:36`；core absent目标回执通过但不是整套dump/restore，本轮不拿它替代真实联合恢复 |
| 离线同库恢复、过期任务安全停用 | 第三轮核心反例本轮独立关闭 | `application/replay_journal.py:23`；`test_journal_crash_recovery` 真实生产claim及日志失败窗口恢复通过；在线客户端拒绝本轮未重跑 |
| content.revoked空payload、ID和水位、读取兜底 | 后台独立通过、浏览器本页独立通过 | `application/lifecycle.py:87`、`application/content_revision.py:6`；invalidation测试覆盖撤销即隐藏review、事件清理后仍有conversation_id、水位保留、另一会话0；跨标签页/外部删除/晚到详情本轮因HIGH未完整动态验收 |
| GUI确认、状态、重试、旧草稿失效 | 部分实现 | `frontend/src/components/shared/DeletionDialog.vue:37` 状态处理；本轮真实图片completed/旧草稿清空通过，H1失败；历史History错误/重试证据不扩为本轮亲测 |
| 自动cleanup worker | 独立通过 | `worker/cleanup_runner.py:1`；`tests/test_lifecycle_invalidation.py:53` 真实PG请求由runner自动完成，远端purge mock，未调用模型 |
| 仅API/脚本重置，不新增测试控制页面 | 静态匹配 | `api/lifecycle.py:14` action；`frontend/src/views/mail-agent/index.vue:25`资源删除与history。未发现明确无需求的本期产品功能 |

## 原始验证输出及边界

独立运行仓库venv，`PYTHONPATH=src;tests`，仅将本地配置database_url注入测试环境变量，未打印凭据。随机schema/临时对象；崩溃恢复为测试独立数据库。知识/来源用例使用真实PG、解析与合成向量，远端purge使用mock；不是付费模型或真实Langfuse验收。完整原始输出见[21项日志](artifacts/phase12/review5/targeted.txt)。

```text
.venv/Scripts/python.exe -m unittest test_lifecycle_invalidation test_lifecycle_core test_lifecycle_attachments test_lifecycle_business test_lifecycle_knowledge test_lifecycle_sources test_journal_crash_recovery -v

----------------------------------------------------------------------
Ran 21 tests in 107.755s

OK
```

后端编译实际运行及原始输出：

```text
globalmail-agent/backend/.venv/Scripts/python.exe -m compileall -q globalmail-agent/backend/src
compileall exit=0
```

本轮没有前端build新结果，也没有把主线程正在跑的全量或旧fixture日志当成最终冻结PASS。初次浏览器交互遭HMR导致旧ref失效，重新snapshot并成功保存草稿后才进行删除取证；未用失败交互宣称功能失败。正式18080/15173、观测3001、原资料和既有页面服务未动。

## Stage2 与交接

Stage1有HIGH，按skill停止Stage2；没有进行完整安全扫描、命名/类型/300行质量检查、整体测试真实性和邻居页面视觉比较，不输出这些维度通过结论。本轮仅为H1核对service测试与实际UI可达性，不冒称Stage2完成。

主线程按Stage1失败修复人工通信路径，补真实交互回归，冻结后重新派fresh reviewer从Stage1开始。本报告和前四份FAIL保留。review5浏览器及合成样本保留给主线程，不停止隔离或正式服务。
