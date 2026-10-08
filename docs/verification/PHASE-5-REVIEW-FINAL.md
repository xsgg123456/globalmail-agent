# Phase 5 修复后独立审查

日期：2026-10-08。审查者：fresh code-reviewer；使用 `.agents/skills/code-review/SKILL.md`。本文件记录修复后的独立审查，首轮 `PHASE-5-REVIEW.md` 的 FAIL 保留原文。

## 审查规划

1. 逐条读取 REQ-005、CMP-010/011、输入/数据约束、架构租约/知识/存储契约及 Phase 5；建立本期与后续阶段映射。完成标准：每项有源码行号与行为证据。
2. 检查原件、版本、精确范围、解析、任务、核对以及首轮两项缺陷；独立重跑真实随机 PG→HTTP、真实子进程和前端回归。完成标准：替换增长/缩短/准备资料、结构化 JSON 范围维护以及配置/租约围栏有证据。Stage 1 HIGH 立即停下。
3. Stage 1 通过后扫描质量/安全/测试真实性，实际比较知识页面与邻居工作台，验证明暗/窄屏及错误路径。完成标准：源文件≤300行、无新增 any/危险 HTML，页面证据与服务状态一致。
4. 保存命令原始输出、范围/AC局限及问题清单，关闭自己的 `phase5-final-review` 浏览器。仅访问隔离15174/18181，不改正式数据库/配置、不停止共享服务、不改代码、不提交。

**结论：Stage 1 FAIL，新发现 1 项 HIGH；Stage 2 未执行。** 文件名中的 FINAL 是本次派发的报告名，不代表通过。主 Agent 收到反例后已开始修复；本报告冻结本次修复前的证据，后续修复仍须重新派 fresh 审查。

## Stage 1：问题清单

### S1-FINAL-001 HIGH：队首原件读取失败使全部知识解析停止，任务却一直显示排队

- 需求：`DEV-PLAN.md:126`「失败重试/取消及任务状态」；`:135`「失败显示真实阶段」；`AGENT-ARCHITECTURE.md:283` 可重建知识任务最多3次自动重试、退避2/10/30秒；`Product-Spec.md:331` 查询入库任务、`:349` 显示失败阶段和重试入口。本期必须实现这些任务行为。
- 修复前源码：`globalmail-agent/backend/src/globalmail_agent/knowledge/jobs.py:59` 在 `claim()` 领取事务提交前执行 `KnowledgeFiles.read(conn, v["object_id"])`。`knowledge/base.py:107`/`:109` 原件缺失或内容摘要不符会抛出 `source_unavailable`/`object_integrity_error`；整个领取事务因此回滚，没有持久任务失败或退避。
- 调度后果：`globalmail-agent/backend/src/globalmail_agent/worker/knowledge_runner.py:56` 每轮先令 `job=None`，`:60` 从 `claim()` 赋值；若其抛出异常，`:69`–`:71` 的错误处理因 `job` 为空不执行 `safe_fail`。下一轮仍选同一最早 queued 任务，正常资料不能继续。以上行号对应本次反例时的源码；收到报告后主 Agent 已移走该读取，不将新代码混作本轮 PASS。
- 真正可达的输入：通过真实 HTTP 上传/创建两份 Markdown 并提交解析；仅删除随机测试 schema 对应临时 ObjectStore 中第一份原件。没有篡改 job 状态或注入非法命令；这模拟原件副本在磁盘丢失的依赖故障，不改变 v1/v2 字节或正式对象。
- 独立行为证据：真实 `KnowledgeRunner` 跑1.4秒；再连续3次调用正式 `claim()` 都得到 `source_unavailable`。两任务 GET 均 `queued`、`stage=queued`、`attempt_no=1`、`error_code=null`、`retryable=false`，版本均 `parsing`。坏资料详情 GET 503。手动 HTTP 取消坏任务后正常资料立即解析完成，证明阻塞来自队首坏原件，而非数据库/解析器慢。
- 影响：单份原件依赖故障阻断所有后续资料解析；维护者看不到真实失败状态，而且坏资料的详情无法打开，页面不能提供该任务的重试/取消操作。该行为不满足本期入库任务的核心故障恢复契约。
- 修复验收标准：原件缺失/损坏由持久任务明确记录安全错误类别与合法重试策略，不反复占队首；后续健康资料完成；命中已有物理缓存仍核验原件；失败资料详情保留任务/错误信息；修复或替换后可继续。使用真实 PG→HTTP 与真实 runner 覆盖，不能只断言日志或 Mock 调用次数。

独立复现脚本：[phase5-final-review-source-fault.py](artifacts/phase5/phase5-final-review-source-fault.py)；[完整原始日志](artifacts/phase5/phase5-final-review-source-fault.txt)：

```text
{"claim_check": 1, "error_code": "source_unavailable"}
{"claim_check": 2, "error_code": "source_unavailable"}
{"claim_check": 3, "error_code": "source_unavailable"}
{"broken_detail_http": 503, "error_code": "source_unavailable"}
{"document": "broken", "job_status": "queued", "stage": "queued", "error_code": null, "attempt_no": 1, "retryable": false, "version_status": "parsing"}
{"document": "healthy", "job_status": "queued", "stage": "queued", "error_code": null, "attempt_no": 1, "retryable": false, "version_status": "parsing"}
{"after_manual_cancel": "completed", "stage": "needs_review"}
```

## Stage 1：本期条目映射与首轮修复

本表逐项标明实际证据边界；“匹配”仅对应列明的源码/本轮测试，不关闭跨阶段 AC。因上述 HIGH 停止，尚未做的真实 UI 或最终 MinerU 复跑明确保留待验。

| 本期条目 | 结论及证据 |
|---|---|
| 原件50MiB/300页、PDF实际格式、加密/损坏/主动内容拒绝 | 匹配。`knowledge/validation.py:39`–`:67`；`tests/test_knowledge_api.py:20`、`test_knowledge_inputs.py:37` 本轮真实HTTP测试通过。 |
| Markdown/受控 JSON/JSONL，保原字节、表头单位、章节，拒绝场景/来源/用途/URL字段 | 匹配到契约及独立子进程。`validation.py:76`、`parser-worker/parse_document.py:28`–`:38`；`test_knowledge_inputs.py:45`、`test_parser_process.py:24`/`:39` 本轮通过。完整原字节与 24 V/参数表断言通过。 |
| 原件、内容及适用不可变版本，幂等/CAS、维护审计 | 匹配到服务/HTTP。`knowledge/documents.py:39`/`:57`/`:106`；`test_knowledge_api.py:47`/`:72`、`test_knowledge_migration.py:17` 本轮通过；旧版本和旧原件保持。 |
| simulation不解除、来源不提升、可用时间与整理时间分离 | 匹配。`documents.py:49`–`:51` 固定模拟，`commands.py:9` 禁额外字段、`:53` 要求带时区；`test_knowledge_api.py:47` 拒绝可信来源/用途/发布注入；本轮通过。 |
| 精确SKU/品牌、章节/一基页区间与范围摘要 | 匹配。`validation.py:21`；`commands.py:13`/`:35`；`documents.py:114`–`:131`。本轮 `test_explicit_logical_range_is_bounded_and_changes_applicability_digest`、跨品牌/范围反例通过。 |
| 首轮HIGH：PDF增长/缩短及准备资料换独立新原件 | 服务层修复匹配。`documents.py:108`–`:115` 新SHA使用新页范围、同SHA保留原范围；`:129` 新原件清旧manifestSHA；`:131` 将page_range纳入适用摘要。本轮 `tests/test_knowledge_replacement.py:44`/`:62`/`:75` 真实PG→HTTP全部通过。逻辑投影使用明确标记的合成ParserResult，不能作为最终MinerU业务解析验收。GUI替换本轮未完成。 |
| 首轮MEDIUM：JSON/JSONL仅修改范围仍沿用原件 | 源码修复已对照，GUI验收本轮未完成。`KnowledgeEditor.vue:69`/`:174`/`:182` 默认reuseSource；`:231` 不再强制Markdown；`:271` 只在不沿用时发送content。因本轮HIGH停止，不能将源码检查写成独立真页面复现通过。 |
| 独立Basic/Standard解析、保raw/页图/表/bbox/版本 | 契约与结构测试匹配；本轮最终配置真实MinerU未复跑。`parser_contract.py:6`/`:19`/`:40`；`parser-worker/parse_document.py:41`–`:60`；parser独立环境4项结构/原像素裁剪/模型摘要测试通过。未读取旧产物冒充本轮新解析。 |
| 17页物理PDF一次解析缓存、8份逻辑范围投影，不读authoring/controller/evaluation/story替代原件 | 服务/测试匹配。`prepared.py:16`–`:38` 固定允许的原件和manifestSHA，`:74`–`:80` 按SHA复用；`cache.py:13`/`:86` 按profile/fingerprint和真实页范围投影。`test_knowledge_prepared.py:16` 本轮通过，但明确是合成解析契约。共享服务真实22资料列表只作页面状态观察。 |
| 原件/资产依赖、raw和内部路径不进HTTP | 匹配到本轮HTTP。`cache.py:58`–`:68` 注册原件/解析/资产依赖；`queries.py:98`/`:138` 排除raw；`test_knowledge_prepared.py:52` 跨scope/raw访问/依赖反例通过。Stage2全安全扫描未做。 |
| 缺页/关键图阻核对，排除依赖内容并写原因 | 匹配到核对门。`cache.py:95`–`:108`、`review.py:39`–`:56`；`test_knowledge_jobs.py:131`、`test_knowledge_prepared.py:85` 本轮通过。像素保存不等于自动读懂图片含义。 |
| 核对source/parse/applicability摘要，内容/范围/解析变化失效、记录人和备注、保存未发布 | 匹配到服务/HTTP。`review.py:27`–`:65`、`queue.py:80`；`test_knowledge_jobs.py:107` 本轮通过。`KnowledgeReview.vue:104` 保留备注并要求重新核对；完整GUI交互本轮未做。 |
| 政策结构/语义校验，同次生成说明与摘要，不修改生效政策 | 匹配到本轮API。`documents.py:133` 创建policy_bundle；`test_knowledge_api.py:114` 规则/说明一致、boolean/超额度/不合规证据类型拒绝通过。Phase6政策同版发布未交付。 |
| 持久knowledge jobs、独立slot、不造Conversation/AgentRun、迁移保旧数据 | 匹配。`jobs.py:35`、`queue.py:92`；`test_knowledge_migration.py:17`、`test_knowledge_jobs.py:13`/`:33` 本轮通过。 |
| 15秒心跳/90秒租约、DBclock/fence，提交过程中失效全部回滚 | 匹配到机制与独立PG反例。`jobs.py:61`/`:72`/`:128`（反例时源码）；`parser_process.py:46` 默认15秒/900秒；`tests/test_knowledge_replacement.py:7` 在实际事务投影中令租约过期，原件衍生文件/缓存/块全部回滚，本轮通过。 |
| 最多3次自动重试/2、10、30退避；原件与依赖故障真实失败状态 | **不匹配HIGH**：常规失败重试测试 `test_knowledge_jobs.py:86` 本轮通过，但不覆盖领取前坏原件，独立反例推翻此条完整通过；见S1-FINAL-001。 |
| 取消/新版本/删除fence挡晚到，不自动发布/复活 | 匹配到本期栅栏。`queue.py:18`、`jobs.py:102`；`test_knowledge_jobs.py:41`/`:54`/`:74` 本轮通过。删除状态通过隔离DB生命周期设置，非完整删除API验收。 |
| 服务私有临时目录/独立依赖环境/本地模型/进程树终止/秘密隔离 | 匹配到机制。`knowledge_runner.py:46`、`parser_process.py:23`/`:31`/`:46`；`test_parser_process.py:17`/`:47` 真子进程秘密/加速超时/fence停止通过。没等待实际900秒、没验证生产负载。 |
| 配置fingerprint冻结，旧缓存与中途配置变化不能混用 | 部分独立证据。`knowledge_runner.py:34`/`:49`、`parser_profiles.py:23`–`:37`、`parse_document.py:62` 配置摘要检查；`test_parser_process.py:64` 缓存读取前拒绝旧摘要本轮通过。全最终配置真实PDF以及解析过程中配置变化的真实GUI本轮未验。 |
| 列表/上传/修订/PDF替换/政策/范围/差异/任务/核对页面 | 源码与列表观察，整体未通过。`KnowledgeDetails.vue:19`/`:51`/`:69`，`KnowledgeEditor.vue:238`–`:285`；实际隔离知识列表呈现准备资料/待核对/未发布及明确Phase5提示。原件故障时详情503且任务仍排队，故障路径不匹配。完整上传→核对及JSON范围GUI本轮未完成。 |
| 请求幂等、未知结果重试、输入保留、晚到响应/卸载轮询清理 | 匹配到前端契约回归。`useKnowledgeCommands.ts:13`、`useKnowledgeWorkbench.ts:61`；`scripts/knowledge-workbench.test.ts:9`/`:36`/`:59`/`:127` 本轮通过。故障GUI不能以这些composable测试替代。 |
| 沿用卡片/抽屉/表单，明暗/窄屏和邻居实际视觉对比 | 未验收。`KnowledgeDetails.vue:71` 单列至xl双列，现有El组件；HIGH出现后未完成明暗/窄屏及邻居对比，不声明视觉通过。 |

## AC与范围局限

- AC-055（`Product-Spec.md:347`）与 AC-063（`:355`）：本期版本/页图/结构/警告单位/精确范围及缺失核对门有本轮测试证据；最终配置真实PDF逐项核对和完整GUI尚未完成，不能关闭本期整体验收或这两条产品AC。
- AC-057/064（`:349`/`:356`）：本期上传/核对/任务/UI基础，S1-FINAL-001直接影响真实失败状态。发布、试查、下架及旧生效版本连续服务属于Phase6，仍未交付。
- REQ-005的语义检索/跨语言/引用、发布/回滚/下架、Embedding及空间切换主要由Phase6/7交付；完整删除与恢复由Phase12交付。`queries.py:15`/`:34` 版本均published=false，`review.py:65` 核对明确仍未发布。本轮不将后续计划作为已完成功能，不声称82项AC整体验收通过。
- 本次重点源码没有发现新增发布/向量/检索/Agent/完整删除入口；正式全范围漂移/安全/质量扫描属于Stage2，因HIGH未执行。

## 本轮独立验证原始输出

仅从 `.local-data/runtime/settings.json` 读取database_url到子进程环境，未打印配置。后端每测试随机schema与临时对象，自行清理。缺原件反例同样随机schema；浏览器只打开隔离15174/18181，未创建共享模拟资料、未停止共享服务；`phase5-final-review` session已关闭。

首次后端命令未设置PYTHONPATH，报 `ModuleNotFoundError: No module named 'globalmail_agent'`。这是审查命令环境错误，补齐 `PYTHONPATH=src` 后重新全跑，最终记录如下，不将该首次错误列为应用缺陷。

### 后端

命令：`PYTHONPATH=src; uv run python -m unittest discover -s tests -v`。日志：[phase5-final-review-backend-tests.txt](artifacts/phase5/phase5-final-review-backend-tests.txt)。当前119项测试启动时未包含主 Agent 后续新增的source_fault测试；全部绿不覆盖上述独立反例。

```text
----------------------------------------------------------------------
Ran 119 tests in 146.149s

OK
```

本轮无skip。原始警告：

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

### 前端

命令：`pnpm exec tsx --test scripts/*.test.ts`。[完整日志](artifacts/phase5/phase5-final-review-frontend-tests.txt)。

```text
ℹ tests 33
ℹ suites 0
ℹ pass 33
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2383.5641
```

### Parser独立环境

命令：`uv run python -m unittest discover -s tests -v`、`uv pip check`。[完整日志](artifacts/phase5/phase5-final-review-parser-tests.txt)。

```text
test_figure_crop_is_the_original_pdf_region_and_invalid_geometry_blocks_review (test_structure.StructureTests.test_figure_crop_is_the_original_pdf_region_and_invalid_geometry_blocks_review) ... ok
test_missing_pages_and_unknown_schema_do_not_become_complete (test_structure.StructureTests.test_missing_pages_and_unknown_schema_do_not_become_complete) ... ok
test_model_mismatch_is_detected_before_sdk_can_download (test_structure.StructureTests.test_model_mismatch_is_detected_before_sdk_can_download) ... ok
test_pages_figures_tables_keep_unit_headers_caption_and_location (test_structure.StructureTests.test_pages_figures_tables_keep_unit_headers_caption_and_location) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.124s

OK
Checked 115 packages in 6ms
All installed packages are compatible
```

### 编译与真实渲染

本轮出现Stage1 HIGH后停止，未执行vue-tsc、production build或compileall，不引用主 Agent /首轮的编译PASS冒充本轮输出。实际打开隔离知识列表并快照；由于HIGH停止，未完成结构化编辑、最终配置PDF、明暗/窄屏和邻居视觉对比，不把DOM快照当成像素比较通过。首次列表快照：`.playwright-cli/page-2026-10-08T04-21-17-513Z.yml`；后续snapshot呈现真实知识列表与未发布状态，非应用编译证据。

## Stage 2

**未执行。** code-review skill原文：「Stage 1 有 HIGH 问题就停在 Stage 1」。文件大小、命名/类型、完整安全扫描、测试真实性专项与实际邻居渲染比较不得凭本轮119/33/4测试通过代替。修复S1-FINAL-001后，应重新派fresh审查，从Stage1开始并补齐本轮未完成的GUI/真实解析/编译证据。
