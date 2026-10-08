# Phase 5 独立审查：第一轮 FAIL

审查日期：2026-10-08。审查者：fresh `code-reviewer`，使用 `.agents/skills/code-review/SKILL.md`。范围：未提交的 Phase 5 知识原件、不可变版本、解析任务、人工核对及维护页面；依据 Product-Spec v1.13、DEV-PLAN Phase 5、AGENT-ARCHITECTURE 第6.2/7.1/8节及 PHASE-5-IMPLEMENTATION 原文。

**结论：Stage 1 FAIL，发现 1 项 HIGH、1 项 MEDIUM。Stage 2 未执行。** 本报告记录修复前证据，不因后续代码变化改成 PASS。主 Agent 已收到问题并开始修复；修复后的代码需要重新从 Stage 1 审查。

## 1. 审查计划与隔离

1. 读取源需求和变更，逐条对照 Phase 5，完成标准是每项都有代码位置和行为证据。
2. 独立重跑数据库/HTTP、解析进程、前端及编译验证，检查实际维护页面。数据库配置仅从 `.local-data/runtime/settings.json` 读入子进程环境，不输出连接串/密码；数据库测试创建随机 schema 和临时对象目录并自行清理。
3. Stage 1 有 HIGH 时停止 Stage 2，保留失败原文并返回主 Agent。

实际浏览器使用 `playwright-cli -s=phase5-review`，只访问隔离 `15174/18181`。正式 `15173/18080` 未作写入。浏览器已关闭，未停止主 Agent 的服务。为复现 JSON 编辑问题，仅在隔离服务创建 `d45ff95d-bd07-4273-952b-b7639ad4af34`，交由主 Agent 隔离服务收尾清理。

## 2. Stage 1 问题

### S1-001 HIGH：替换 PDF 沿用旧文件页范围，新增页被丢弃，缩页替换不能保存

- 需求原文：Product-Spec.md:331「支持……替换 PDF 原件」；:338「保留 PDF 原文件、页码与图文关联」；DEV-PLAN.md:136 要求页面上传至完整核对，保留原件内容。
- 修复前位置：`globalmail-agent/backend/src/globalmail_agent/knowledge/documents.py:108` 的 `range_value = page_range or (old["page_range"] if old else ...)` 无条件沿用旧 PDF 的逻辑范围；:109 检查旧范围是否超过新页数；:124 将其保存。`knowledge/commands.py:29` 的 VersionCommand 没有供维护者修改文档逻辑页范围的字段。
- 独立复现：随机 PG schema → 正式 HTTP 路由，分别上传真实一页/两页 PDF。先创建一页资料，再替换两页原件返回 202，新版本的 `page_range` 仍是 `[1,1]`。尝试绑定新增第2页返回422。两页换一页，即使提交的适用绑定已改为第1页，仍返回422。
- 影响：解析器即使解析完整新原件，`knowledge/cache.py:86` 按旧范围投影，新增页不进入该版本可核对内容；较短替换无法完成。准备资料的旧物理页号同样无法切换到独立的新 PDF 原件。
- 完成标准：新原件使用明确的新页范围；沿用同一原件保留合理的逻辑范围；准备共享 PDF 的原件不变时不能借此扩大到其他型号/品牌。覆盖增长、缩短、准备资料独立替换及范围摘要失效的数据库→HTTP反例。

原始复现输出（完整记录：[日志](artifacts/phase5/phase5-review-replacement.txt)）：

```text
upload 202 ok
upload 202 ok
one_to_two_pages 202 ok
stored_page_range [1, 1]
upload 202 ok
bind_replacement_page_two 422 invalid_page_scope
upload 202 ok
upload 202 ok
two_to_one_page 422 invalid_page_scope
```

### S1-002 MEDIUM：JSON/JSONL 资料只调整适用范围，也被要求重新填写 Markdown 正文

- 需求原文：Product-Spec.md:331「维护明确适用关系」；:609 支持知识 JSON/JSONL；CMP-010（:579）要求明确 SKU/章节范围。
- 修复前位置：`globalmail-agent/frontend/src/components/knowledge/KnowledgeEditor.vue:140` 仅对 `format === 'md'` 初始化已有正文；:199 对所有非PDF/政策资料强制要求新文件或非空 Markdown；:226 随后把该 Markdown 当作新内容。
- 实际页面复现：受控 `globalmail.knowledge/1` JSON 上传202、创建202；打开“修订正文 / 适用范围”，原文件正文已在详情显示，但编辑器显示空的“Markdown 正文（必填）”。仅改“适用依据”并保存，出现「请提供完整正文或原文件。」；没有产生新版本。适用依据输入保留。
- 证据：[实际截图](../../output/playwright/phase5-review-json-scope-blocked.png)，Playwright 快照 `.playwright-cli/page-2026-10-08T04-12-40-928Z.yml`。后端 `knowledge/documents.py:77` 已允许缺少新内容时沿用原件，问题位于前端流程。
- 完成标准：受控 JSON/JSONL 可以沿用当前原件，仅修订范围/标题，生成不可变新版本；需要替换正文时明确选择新结构原件或转换为 Markdown，不静默清空/强制改格式。

## 3. Phase 5 逐项对照

下表的“匹配”仅指列明的证据，不代表整条跨阶段产品 AC 已关闭。位置相对仓库根目录；后续修复可能移动行号，以上问题按修复前快照记录。

| 本期要求 | 结论 | 代码位置与独立验证 |
|---|---|---|
| 原件50MiB、真实PDF最多300页，拒绝伪装/损坏/加密/路径/URL | 匹配 | `knowledge/validation.py:36`、`:47`；`api/knowledge_documents.py:30` 流式限额。`tests/test_knowledge_api.py:20` 真实HTTP验证50MiB+1、301页、加密及伪装；本轮重跑PASS。 |
| PDF主动内容，包括注释动作、附件、RichMedia | 匹配 | `knowledge/pdf_checks.py:6`、`:11` 有界递归遍历；`tests/test_knowledge_inputs.py:37` 向真实上传路由提交JavaScript/Launch/AA/RichMedia/EmbeddedFiles，均422且不登记原件。 |
| Markdown保原文、层级、列表、表头/单位，不抓链接或执行HTML | 匹配 | `parser-worker/markdown_structure.py:6`、`:30`；`tests/test_parser_process.py:24` 真实子进程保留24 V、警告、代码围栏、完整raw及缺图诊断。页面纯文本插值见 `KnowledgeBlocks.vue:27`。 |
| 明确schema的知识JSON/JSONL；拒绝场景/controller/evaluation/来源/用途注入，完整保留 | 匹配 | `knowledge/json_structure.py:8`、`validation.py:74`；`tests/test_knowledge_inputs.py:45` HTTP拒绝scope/URL/page/asset/答案/场景字段；`test_parser_process.py:39` 真实JSONL子进程保表头和单位。修订UI例外见S1-002。 |
| 不可变内容/适用版本、同事务原件/资料/审计，幂等重试 | 匹配 | `knowledge/documents.py:39`、`:57`、`:106`；`migrations/versions/0004_knowledge_content.py:162` UPDATE触发器；`tests/test_knowledge_api.py:47`、`:72` 验证重复不新建、旧原件保留、旧版本写入拒绝。 |
| simulation和来源不能普通修订解除 | 匹配 | `knowledge/documents.py:50` 固定simulation；`commands.py:9` 禁额外字段；迁移 `0004_knowledge_content.py:180` 固定来源/用途；`test_knowledge_api.py:47` 验证客户端可信来源/发布/scope注入422、DB用途更新失败。 |
| 原可用时间与整理时间分开，准备来源摘要保留 | 匹配 | `knowledge/documents.py:69`、`:122`；`prepared.py:91` 消费manifest available_at/source_hash；`commands.py:53` 拒绝无时区时间。版本响应展示available_at，实际PDF详情显示原2026-10-07时间。 |
| 精确SKU、品牌、章节和一基页区间，不扩大局部范围 | 基础匹配；PDF替换不匹配 | `validation.py:20`、`review.py:51` 明确SKU/章节/页区间；HTTP跨品牌422、未绑定章节不能核对。原件替换改变页范围失败见S1-001。 |
| PDF替换、不可变旧原件和新原件完整核对 | **不匹配 HIGH** | S1-001，真实增长/缩短替换反例已复现；旧内容不可变本身不补足替换能力。 |
| 规范ParserResult保raw、page/section/bbox/figure/table、parser/model版本和诊断 | 匹配到已有产物；最终配置未复跑 | `knowledge/parser_contract.py:6`、`:39`；`parser-worker/mineru_structure.py:36`；`parse_document.py:41`。独立读取真实17页Basic result：full=true、274blocks、26assets、页1–17、MinerU4.0.10/DocVortex0.5.9。该磁盘产物早于adapter_fingerprint增量，不能替代最终配置重跑。 |
| 17页物理原件一次缓存，8份逻辑资料按原页投影；不用authoring正文绕过解析 | 匹配 | `knowledge/prepared.py:19`、`:32`、`:77`；`cache.py:13`、`:81`。`tests/test_knowledge_prepared.py:16` 隔离PG验证8范围/1原件/1缓存（parser结果明确为合成契约）；实际隔离HTTP有22份needs_review、8份PDF、published=0；抽查第8–9页32blocks/3assets，仅返回该范围。 |
| 原页预览/图片裁剪依赖登记，图片机器保存不冒充含义已核对 | 匹配 | `parser-worker/pdf_assets.py:12`、`:37` 保原像素/图号；`knowledge/cache.py:58` 登记source及资产依赖。parser实际裁剪测试PASS；真实树形灯详情显示第8–9页原页和「图片中的操作含义仍需人工对照」提示。 |
| 缺页/关键图缺失不能核对；明确排除连带步骤并写原因 | 匹配到本期核对门 | `knowledge/cache.py:96` 扩展整section依赖、`:107` 缺页诊断；`review.py:39`–`:54`。`tests/test_knowledge_jobs.py:131` 只排figure拒绝、整section及原因接受；`test_knowledge_prepared.py:85` 不完整全文拒绝。真正发布门属Phase6。 |
| 核对绑定source/parse/applicability摘要；解析变化失效，记录操作者和备注；保存未发布 | 匹配 | `knowledge/review.py:27`–`:65`、`queue.py:80` 清旧摘要/代次；`test_knowledge_jobs.py:107` 假摘要/过期版本拒绝，重解析核对不可复用且published=false。前端 `KnowledgeReview.vue:103` 变化后要求重新确认。 |
| 政策结构/语义校验，同次生成中文说明与摘要，不修改生效政策 | 匹配 | `knowledge/policy_bundle.py:21`、`:51`、`:89`；`documents.py:129` 同事务policy_bundle。`test_knowledge_api.py:114` 45天/1250基点输出与规则一致，boolean/10001/视觉仓库证据拒绝，源v2原字节保持。 |
| 知识持久jobs独立slot，无假Conversation/AgentRun，迁移保旧数据 | 匹配 | `knowledge/queue.py:92`、`jobs.py:35`；迁移 `0004:147` 扩jobs目标复合FK；`tests/test_knowledge_migration.py:17` 从0003含Agent数据升级；`test_knowledge_jobs.py:13` Agent槽仍独立、GET不排任务。 |
| DB时钟、15秒心跳/90秒租约、单调fence | 匹配 | `worker/leases.py:14` DBclock；`knowledge/jobs.py:61`、`:72` 90秒；`parser_process.py:46` 15秒；`test_knowledge_jobs.py:33`、`:86` 验证并发唯一领取、过期不能提交、新fence递增。 |
| 最多3次自动重试，2/10/30退避，不自动发布 | 匹配 | `knowledge/jobs.py:137`–`:150` 初始attempt1至自动attempt4；`test_knowledge_jobs.py:86` 最多3次重试后failed。代码明确2/10/30；测试推进DBclock使等待可达，没有真实等待全部42秒。 |
| 取消、新版本、删除栅栏阻晚到完成/心跳/重试 | 匹配到栅栏 | `knowledge/jobs.py:22`、`:102`、`queue.py:16`；`test_knowledge_jobs.py:41`、`:54`、`:74` 验证删除/取消/新版本后无新块缓存、不能复活。删除通过DB生命周期注入测试，完整删除API/清理属Phase12。 |
| 服务端私有临时目录、独立环境、本地模型、15分钟进程树终止、秘密隔离 | 匹配到机制 | `worker/knowledge_runner.py:46`、`parser_process.py:23`、`:31`、`:46`；`parser-worker/model_integrity.py:15` SHA校验；parser独立锁。`test_parser_process.py:17`/`:47` 真实子进程秘密隔离及0.25秒加速超时/fence终止；未等待真实900秒，也未声称大型生产负载验证。 |
| 原件/资产scope和安全响应，raw/内部路径不进HTTP | 匹配 | `knowledge/base.py:24`、`:98`；`queries.py:134`、`api/knowledge_documents.py:61` no-store/nosniff/sandbox；`test_knowledge_prepared.py:52` 资产可访问、raw404、HTTP无内部raw和路径；跨workspace及复合FK反例PASS。 |
| 页面列表/上传/正文修订/PDF替换/范围维护/核对/版本差异/任务失败重试取消 | 部分匹配 | `views/knowledge/index.vue:25`、`KnowledgeDetails.vue:25`/`:97`、`KnowledgeEditor.vue:181`；实际打开22份列表、PDF对照、版本/范围/任务控件。PDF替换和JSON范围维护失败分别见S1-001/002；本轮没有把全部GUI流程记为通过。 |
| 202/幂等未知结果重试、错误输入保留、晚到响应和卸载轮询清理 | 匹配到测试及已观察输入 | `useKnowledgeCommands.ts:13`、`:31`；`useKnowledgeWorkbench.ts:61`、`:164`；`frontend/scripts/knowledge-workbench.test.ts:9`、`:36`、`:59`、`:127` 本轮PASS。实际JSON失败后适用依据保留。 |
| 明暗/窄屏及邻居基准页面真实渲染对比 | **本轮未完成验证** | 代码复用既有ElCard/ElDrawer/表单和主题变量，详情 `KnowledgeDetails.vue:73` 采用单列至xl双列。实际980px截图已打开；发现Stage1 HIGH后停止，本轮未完成明暗/900px交互矩阵，Stage2邻居对比未执行，不能声明视觉验收通过。 |

## 4. 范围与产品 AC 状态

- **AC-055（Spec:347）**：本期版本/页码/图号、资产及不完整核对门已有上述证据；PDF替换丢新增页影响其完整性，本期仍FAIL。没有把图片像素保存当作图片含义自动识别；生产资料人工核对及完整操作依据尚不能宣布通过。
- **AC-063（Spec:355）**：本期结构/表头单位/原位置/章节范围及排除依赖已有证据；PDF替换范围缺陷未关闭。后续切分及发布拒绝属于Phase6，未实现也未提前关闭整条AC。
- Phase6主负责 AC-013/014/016/030/056/057/058/059/061/062/064，本期仅提供其中原件/版本/来源/核对/任务/UI基础。向量、语义检索、发布/回滚/下架、检索试查未实现；`knowledge/queries.py:15` 所有版本published=false，API `knowledge_documents.py:21` 只有维护路由。
- Phase7正式Agent及在途回复、Phase12完整删除/恢复（AC-060）未交付。本期删除fence测试不等于删除完成。其余AC按 `DEV-PLAN.md:303` 唯一主交付阶段保留，82项不作总体验收。
- 未发现本期新增发布/检索/Agent/下架/删除完成入口的范围漂移；正式全库安全扫描、命名/大小/类型/测试真实性质量审查属于Stage2，本轮未执行。

## 5. 独立验证与原始输出

所有测试均由审查者独立执行。下面为原始输出摘录；完整后端、前端、构建日志分别为 [后端](artifacts/phase5/phase5-review-backend-tests.txt)、[前端](artifacts/phase5/phase5-review-frontend-tests.txt)、[构建](artifacts/phase5/phase5-review-build.txt)。本轮114测试在主Agent新增replacement回归之前执行，不能覆盖S1-001；全部绿不推翻独立反例。

### 后端真实PG/HTTP与进程回归

```text
----------------------------------------------------------------------
Ran 114 tests in 137.334s

OK
```

无skip。原始警告保留：

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

### 前端契约/交互回归

```text
ℹ tests 33
ℹ suites 0
ℹ pass 33
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2411.7404
```

原始Vue警告出现在没有组件实例时直接调用composable的测试中，完整日志保留；本轮因Stage1 HIGH未作Stage2测试设计判断。

### Parser独立环境

```text
test_figure_crop_is_the_original_pdf_region_and_invalid_geometry_blocks_review (test_structure.StructureTests.test_figure_crop_is_the_original_pdf_region_and_invalid_geometry_blocks_review) ... ok
test_missing_pages_and_unknown_schema_do_not_become_complete (test_structure.StructureTests.test_missing_pages_and_unknown_schema_do_not_become_complete) ... ok
test_model_mismatch_is_detected_before_sdk_can_download (test_structure.StructureTests.test_model_mismatch_is_detected_before_sdk_can_download) ... ok
test_pages_figures_tables_keep_unit_headers_caption_and_location (test_structure.StructureTests.test_pages_figures_tables_keep_unit_headers_caption_and_location) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.101s

OK
Checked 115 packages in 3ms
All installed packages are compatible
```

### 编译/依赖

后端 `uv run python -m compileall -q src tests` exit0，无错误输出；`uv pip check`原文：

```text
Checked 25 packages in 2ms
All installed packages are compatible
```

前端 `pnpm build`（包含vue-tsc）原文：

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3293 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 30.25s
```

### 实际页面/真实解析证据与限制

- [PDF原件实际页面](../../output/playwright/phase5-review-pdf-compare.png)：树形带灯书架第8–9页原件下载、原页预览、人工核对/未发布/解析成功及版本/范围/差异/操作记录控件。HTTP读取 `needs_review`、`range=8,9`、`blocks=32`、`assets=3`、`pages=8,9`、figure=1。
- 实际隔离列表：`documents=22`、`needs_review=22`、`published=0`、`pdf=8`。
- 独立读取 `tmp/phase5-parser/basic/result.json`：`full_document=True`、`page_count=17`、`blocks=274`、`assets=26`、完整页1–17，source_sha256 `d91001bbf34a5a0d217c4943cec3495b6352bd71ec81ba89a26c5f4e2b370265`。这是已有真实解析产物检查，没有声称审查者重新跑了一遍最终配置MinerU。
- `tmp/phase5-parser/difficult-summary.json` 记录Basic native/scanned及Standard scanned三次4页/36块/2表产物；本轮只读取已有记录，未独立完成与原件逐页业务语义核验，不将该记录当作本轮完整困难PDF验收。

## 6. Stage 2

**未执行。** code-review skill要求「Stage 1 有 HIGH 问题就停在 Stage 1」。质量、安全全扫描、测试真实性专项与邻居页面实际视觉对比不得用本轮编译/测试PASS替代。主 Agent 修复S1-001/002后应派fresh审查者，从Stage1重新验证，再决定进入Stage2。
