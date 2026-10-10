# Phase12 第六轮独立两阶段审查

2026-10-10，基线 `b42794e`，审查当前未提交 Phase12 增量。fresh code-reviewer 使用 code-review、playwright skill；只审查、保存证据，没有修改实现、spawn 或 commit。已读取需求、架构4.4/7.3/9、Phase12计划/实施规划、前五轮审查及GUI/操作说明。无独立设计稿/Design Brief，继承既有页面。

**Stage1 PASS；Stage2 PASS，1项 LOW 自动化补强建议。** 本结论限定本期工程实现及下列证据范围。后台最终冻结全量在报告时仍运行，不能以本轮48项专项替代全量完成；Phase13模型语义、82项AC总验收不在本报告通过范围。真实Langfuse探针的版本边界单列，不将HTTP mock说成真实远端。

## Stage1：本期交付逐项核对

下表后台路径相对 `globalmail-agent/backend/src/globalmail_agent/`，测试路径相对 `globalmail-agent/backend/`。所有本轮专项均使用真实随机PG schema或独立临时数据库、临时对象目录；知识向量/模型为受控替身，远端清理mock处明确隔离。

| 需求与交付 | 结论、实现与验证 |
|---|---|
| REQ-010 删除前影响、取消不改变状态 | 匹配。`application/lifecycle.py:33`只读预览，`api/lifecycle.py:34`；`tests/test_lifecycle_api.py:22`实际API预览/确认/重试通过。本轮GUI显示图片5对象/1运行/1会话；会话预览→取消可返回，未触发删除。历史80表取消哈希见GUI报告，不声称本轮重做该哈希。 |
| AC-029 会话邮件、记忆、草稿及正文运行记录清理 | 匹配。`application/lifecycle_inventory.py:64`枚举持有者，`application/deletion.py:103`清理、`:151`核验；core测试覆盖正文对象、inline事件及checkpoint清空、其他会话仍可读。 |
| 删除前停任务、晚到对象/checkpoint不能复活 | 匹配。`application/lifecycle_revoke.py:28`停写，`application/content_fence.py:7`对象栅栏，`application/writer_barrier.py:10`跨进程锁；core晚到写用例通过，另独立运行真实worker在受控慢model中删除：先writer_inflight失败，释放后completed且对象清空。 |
| 模拟reset仅API/脚本、独立空分支、重复请求幂等 | 匹配。`application/lifecycle.py:53`、`:66`限制action/mode，`application/deletion.py:129`创建新分支；core reset用例验证新ID/branch、open及重试不再创建。没有产品测试控制面板。 |
| 分支售后/事件/地址等正文清理、库存额度释放、保留无正文业务防重记录 | 匹配。`application/deletion.py:49`清正文，`:129`释放占用、`:195`核验；`tests/test_lifecycle_business.py:12`真实分支快照清空、账本ID/status/amount及另一分支保留通过。未扩大为所有售后状态组合重新办理实测。 |
| 原项目、外部源准备包及其他分支不误删 | 匹配。`application/deletion.py:123`仅按注册ObjectStore ID删本地副本；`tests/test_lifecycle_sources.py:13`/`:32`真实检索后删会话、删已读A，保留共享来源和已读B；core保留另一分支。未写正式源包，未重做正式源包全目录摘要。 |
| AC-060 原件、解析、规范块、向量/cache、引用正文及运行衍生清理 | 匹配。`application/deletion.py:69`、`application/lifecycle_inventory.py:43`；knowledge专项覆盖parse/index/cache/manifest清理、已发布A删除保留B、恢复索引核验。 |
| 看过但未引用仍登记依赖；来源引用不等于会话自有对象 | 匹配。`application/lifecycle_inventory.py:59`按run依赖扩展会话、`:78`排除外部source_object_id；两项sources测试真实search_reference→删除→来源读取通过，关闭R2 H1。 |
| 普通下架与彻底删除区分、合法再次发布不被旧日志撤下 | 匹配。`application/lifecycle_replay.py:17`receipt幂等；knowledge生产withdraw→publish→replay保留合法head，关闭R2 H2。 |
| 共享PDF不能安全分离时阻断并展示关联资料 | 匹配。`application/lifecycle.py:183`重新枚举阻断；`frontend/src/components/shared/DeletionDialog.vue:11`及`DeletionStatus.vue:4`展示历史共享依赖，明确仅换新版本不能解除。共享无head用例通过；GUI阻断/重试引用历史有界证据，未宣称已提供自动分离工具。 |
| AC-078 图片原件、衍生、草稿/模拟回复/追踪清理，保留会话继续处理 | 匹配。`application/deletion.py:16`/`:103`；attachments三项通过，含删除两图之一后剩余图证据为空、后续人工回复和新来信可达。下面真实GUI独立关闭R4/R5。 |
| 浏览器正文缓存、相关ID、水位、跨标签、SSE、GET兜底、晚到请求 | 匹配。`application/content_revision.py:6`、`application/conversation_queries.py:78`撤销即隐藏旧review；`frontend/src/composables/content-invalidations.ts:2`/`:26`、`create-mail-workbench.ts:42`/`:71`、`use-agent-console.ts`失效接入。真实PG验证水位/空payload事件仍保留外层ID/无关会话不变；前端101项包含关联/无关草稿、重复水位、GET兜底、404清理503保留、晚到建议及KeepAlive运行缓存。跨标签桥接本轮为代码核验，没有另称双浏览器端到端实测。 |
| 撤销后人审为空仍可再次接管 | 匹配。`frontend/src/views/mail-agent/index.vue:8`仅现有人审open时禁用接管，`:20`仍要求合法open review才能回复；`application/human_review.py:24`创建新review。真实UI重新接管、保存、模拟发送全部通过，未用API绕过按钮。 |
| 远端trace、接受未知、在途导出/SDK缓冲、未确认不得完成 | 匹配于当前协议测试和历史真实探针边界。`observability/purge.py:28`互斥、`:105`持久pending、完整ID读回和两次空确认；13项真实PG+HTTP MockTransport专项通过，包括丢失DELETE响应及子进程持锁。真实远端证据见下文。 |
| 独立journal/事务回执、水位缺失或损坏封闭 | 匹配。`adapters/deletion_journal.py:89`签名/序列，`application/journal_gate.py:7`回执核对；并发append、缺失/损坏水位、未提交日志HTTP封闭实测通过。 |
| 联合数据库+对象+配置备份、全新目标、最新日志重放核验后开放 | 匹配。`adapters/backup_store.py:78`联合快照，`application/restore.py:36`新目标封闭、`:73`重放；本轮实际pg_dump/pg_restore覆盖旧快照缺目标、合法对象保留、篡改/水位缺失/未完成回执拒绝，关闭R1恢复反例。 |
| 离线崩溃后过期running恢复，活连接/未过期租约拒绝 | 匹配。`application/replay_journal.py:23`、`application/restore_checks.py:13`；实际生产claim→过期→日志落盘事务失败→离线重放成功；在线连接/活跃租约拒绝用例通过，关闭R3。 |
| revoked/purging/verifying/completed、失败重试、后台自动清理 | 匹配。`application/lifecycle.py:173`及`worker/cleanup_runner.py:1`；core远端失败保留重试，invalidation真实CleanupRunner自动完成。GUI隔离实例明确禁用worker，通过真实retry推进，无假造完成状态。 |
| 页面继承、引导真实性、范围漂移 | 匹配。`frontend/src/components/shared/DeletionDialog.vue:9`说明实际清理边界；`:15`说明外部副本；本期API、表、journal/备份CLI均由`DEV-PLAN.md:273`授权。未发现无需求新增产品功能；模型/评测原范围不计本期完成。 |

## R4/R5：独立真实GUI闭环

使用独立Playwright CLI `review6`，Web15179/API18189，schema `phase12_browser_d93cc3bf282a4a67a1a825a1d4755dbb`。上传全新600×300合成PNG，旧哨兵 `REVIEW6_IMAGE_PRIVATE_TEXT`；会话 `f80cf8e4-8959-4dee-92f5-81bae2525cdc`、图片 `45209e7f-2b7a-4b77-a573-a0fd7a0766b6`。没有写正式18080/15173、正式trace或调用付费模型。

真实点击人工接管→输入旧哨兵→保存草稿→图片Drawer→彻底删除→确认。隔离服务无worker，向已创建请求真实retry，返回 `completed / journal_seq=2`；页面Dialog显示“删除完成”，原图移除且草稿为空。关闭Dialog→点击重新启用的人工接管→新空白人审→填写 `REVIEW6_NEW_REPLY_AFTER_DELETE`→保存草稿→发送模拟回复；时间线显示新回复。完整刷新后仍无旧哨兵。

- [completed响应](artifacts/phase12/review6-image-completed.json)、[清理后review=null](artifacts/phase12/review6-server-before-resave.json)、[发送后GET](artifacts/phase12/review6-server-after-send.json)。读回断言原始输出：`old_sentinel_absent=True; new_reply_present=True; GET=200`。
- [完成状态截图](artifacts/phase12/review6-completed.png)、[新回复截图](artifacts/phase12/review6-new-reply.png)、[发送DOM](artifacts/phase12/review6-new-reply.yml)、[刷新DOM](artifacts/phase12/review6-after-reload.yml)。审查者实际查看截图，并核对DOM按钮状态。
- 本次工作台源码SHA256：`1a0d65e129a36305706e6f20826acaec164110bd20b197b3aa505e338e62645a`。上述是真实图片删除路径；知识删除关联会话状态由同一代码及前后端专项覆盖，没有另称本轮真实知识GUI全链路。

## Stage2：质量、安全、测试真实性和视觉

| 项目 | 结论与证据 |
|---|---|
| 文件大小、类型与职责 | 通过。变更/新增59个生产Python/TS/Vue文件无超过300行，前端无any；[逐文件行数与扫描](artifacts/phase12/review6-static.json)。`application/lifecycle.py:15`编排与inventory/revoke/purge/restore分层，`frontend/src/composables/mail-draft-cache.ts:5`及`conversation-commands.ts:4`分离缓存和幂等载荷。 |
| 错误处理 | 通过。`application/lifecycle.py:195`失败持久为cleanup_failed；`observability/purge.py:123`固定安全错误；`frontend/src/composables/create-mail-workbench.ts:84`区分404与503。实测失败后重试、清理未确认不报成功。 |
| 安全扫描 | 未发现本期新增HIGH/MEDIUM安全缺陷。上述59文件扫描无eval/innerHTML/dangerouslySetInnerHTML/前端密钥前缀/硬编码供应商token命中。`adapters/backup_store.py:36`数组参数且无shell；`:56`引用数据库标识符，`:60`固定表白名单；`application/writer_barrier.py:14`SQL函数名仅由固定两项选择；`application/backup_cli.py:73`数据库名由UUID生成。`backup_cli.py:17`备份配置摘要不带密钥；恢复旁置配置包含本地数据库连接信息，是本地私有产物，不应提交，未把它误判为前端泄漏。 |
| 测试真实性 | 通过本轮抽查。`tests/test_lifecycle_drain.py:15`真正运行worker并受控阻塞model，非仅改状态；`test_journal_crash_recovery.py:19`生产claim；`test_backup_restore.py:133`实际数据库archive；`test_observability_purge.py:181`跨连接发送竞争、`:227`子进程锁。`frontend/scripts/lifecycle-run-cache.test.ts:11`真实Vue renderer/KeepAlive，传输mock范围明确。没有将受控模型当真实模型质量。 |
| 邻居视觉比较 | 通过。实际打开既有邮件工作台、知识库，查看旧“人工确认结案”与新增删除Dialog/History截图。删除Dialog沿用白底、圆角、字阶、右对齐按钮，危险确认为红色；History按钮/成功提示与知识页一致。`DeletionDialog.vue:2`宽min(540px,94vw)，`:19`wrap/8px gap；`views/mail-agent/index.vue:84`既有确认作邻居。截图：[旧确认](artifacts/phase12/review6-neighbor-confirm.png)、[新删除预览](artifacts/phase12/review6-delete-preview.png)、[知识页](artifacts/phase12/review6-neighbor-knowledge.png)、[History](artifacts/phase12/review6-knowledge-history.png)。本轮实际视口929×917；两档/暗色总验收仍留Phase13。 |

LOW：R5按钮模板条件目前主要由本次真实浏览器路径证明；`frontend/scripts/lifecycle-content-invalidation.test.ts:22`验证composable，未挂载`views/mail-agent/index.vue:8`的按钮disabled表达式。建议把本轮删除→接管→保存/发送做成持久组件或浏览器回归，避免未来仅service通过再次漏检；当前路径已实测正确，不作为阻断。

## 原始测试及编译输出

独立命令：设置 `PYTHONPATH=src;tests`，只从私有配置读取database_url到 `GLOBALMAIL_TEST_DATABASE_URL`，不打印；运行仓库venv。

```text
.venv/Scripts/python.exe -m unittest test_lifecycle_invalidation test_lifecycle_attachments test_lifecycle_sources test_lifecycle_core test_lifecycle_business test_lifecycle_knowledge test_journal_crash_recovery test_backup_restore test_lifecycle_api test_observability_purge -v
----------------------------------------------------------------------
Ran 47 tests in 225.870s

OK

.venv/Scripts/python.exe -m unittest test_lifecycle_drain -v
test_inflight_model_drains_before_deleted_content_can_complete (test_lifecycle_drain.WriterDrainTests.test_inflight_model_drains_before_deleted_content_can_complete) ... ok
----------------------------------------------------------------------
Ran 1 test in 6.281s

OK

globalmail-agent/backend/.venv/Scripts/python.exe -m compileall -q globalmail-agent/backend/src
compileall exit=0
```

完整原始日志：[47项](artifacts/phase12/review6-targeted.txt)、[drain](artifacts/phase12/review6-drain.txt)，无skip。另读取主线程最终前端原始日志（非本reviewer重复执行），均覆盖最后按钮修复：

```text
# frontend-tests.log
ℹ tests 101
ℹ suites 0
ℹ pass 101
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 23373.8849

# frontend-build.log: pnpm build
✓ built in 51.00s

# frontend-preview-build.log: pnpm build:ui-preview
✓ built in 34.05s
```

[前端原始测试](artifacts/phase12/frontend-tests.log)、[构建](artifacts/phase12/frontend-build.log)、[preview构建](artifacts/phase12/frontend-preview-build.log)。Vite大chunk提示不等同编译失败。

## 证据边界与交接

- 真实远端[observability-actual.json](artifacts/phase12/observability-actual.json)记录独占合成trace真实export→先未确认→最终purged，未碰旧trace。该探针早于最终lost-delete-response恢复硬化；最终硬化有本轮真实PG+MockTransport13项通过，**没有最终源码真实远端重跑证据**，不扩大措辞。
- 本轮报告时`backend-final-summary.json`尚不存在，主线程最终3分片仍运行；`before-final-mixed-source/`旧496失败日志未作通过依据。主线程须等最终总结果及前后源码摘要一致，才能宣布完整Phase12四步验收完成。
- 当前未发现未实现的Phase12产品交付或新增HIGH/MEDIUM。保留本报告LOW建议及上述测试范围限制；不能由本报告推导“所有模型语义/82项AC通过”。
- 独立review6浏览器已执行CLI close并确认关闭；合成case及隔离API/Web保留，由主线程统一stopfile清理。本轮没有提交、修改产品代码、改写历史FAIL或写正式数据。
