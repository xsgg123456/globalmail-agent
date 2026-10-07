# 知识管线实验最终独立复核

日期：2026-10-07。fresh code-reviewer；依据 `.agents/skills/code-review/SKILL.md`。审查材料：Product-Spec v1.11 的 REQ-005、AC-013/014/016/055–064，KNOWLEDGE-DESIGN v1.1、KNOWLEDGE-VALIDATION、实验 README、初审 review-notes。源码共 14 个 Python 文件全部读取，另读现有 `tech-spike/probe_support.py`。

**结论：PASS，限定 README 声明的隔离组件与最小契约实验。M1、M2、M3 均已修复，未发现新增 HIGH / MEDIUM。Stage 1、Stage 2 均完成。本结论不将任何正式产品 AC 标记为验收完成。**

本次只写本报告。未读项目 `.env`、原始客户资料、`.local-data` 或 holdout；未调用模型 API、下载模型或重新解析。独立执行了离线测试、内存编译、来源/缓存/结果重算及失败注入；数据库采用当前报告与输入摘要核验，没有重复启动 PostgreSQL。以下相对路径默认位于 `globalmail-agent/knowledge-spike/`；根目录文档另行注明。

## Stage 1：需求与修复符合性

### 三项初审问题

| 问题 | 结论与证据 |
|---|---|
| M1 父正文扩展未重新验证 | **关闭。** `chunking.py:157` 验证父对象资格、document_id/version/parent_id、自洽身份、正文摘要和父子范围完全一致；`probe_retrieval.py:36` 与 `probe_evidence.py:26` 均复用。对 SKU、mode、品牌、version、document_id、parent_id、split、时间、正文共 9 种内存变更，两个扩展路径全部拒绝；现有 `test_knowledge_contracts.py:100` 另覆盖父对象缺失。`chunking.py:30` 当前 PDF 摘要不一致也被独立注入验证拒绝。 |
| M2 失败运行可复用旧成功产物 | **关闭。** `artifact_contract.py:12` 从当前允许源重建父/块并逐项比较；`:27` 核对成功状态、run_id、当前 query/parent/strategy 摘要、产物完整摘要、模型、向量数量与有效性。`probe_retrieval.py:65` 每次生成 UUID，`:87` 写入关联产物，`:99` 任一模型失败则顶层 failed，`:107` CLI 退出 1。`probe_evidence.py:85` 和 `probe_lifecycle.py:194` 统一使用校验入口。独立模拟“v4 成功、新模型失败、旧磁盘缓存仍存在”，证据入口在 guard 调用前拒绝、生命周期入口在 Docker 启动前拒绝。真实 `__main__` 入口经内存 mock 验证退出 1，最终报告 failed，run_id 与旧报告不同。 |
| M3 并发发布冲突的过度声明 | **关闭。** 项目内 `docs/verification/KNOWLEDGE-VALIDATION.md:72` 已准确写成“晚到任务与下架的锁竞争”。对应 `test_lifecycle_contract.py:110`：实际观察 PostgreSQL Lock 等待，提交撤销后完成任务得到 stale_epoch。没有把它当成双 publish 并发实验；`:74` 同时披露合成版本标签与合成失败向量边界。 |

### REQ-005 范围核对

已逐条读取全部需求，正式产品仍是部分实现；此次不重抄初审的完整功能清单。相关 MUST 的本次证据如下：

- 白名单/来源/代表产品族/七类业务/模拟政策与 SIM 标识：沿用当前允许资料，`chunking.py:26` / `:33` / `:44` 保留元数据并约束用途；困难样本 `build_fixtures.py:23` / `:46` / `:107` 明确为 SIM、非产品事实。没有新建政策生成、视频读取或业务授权服务。
- 语义/跨语言/品牌 SKU 型号过滤/历史可用时间/引用与适用条件：`probe_retrieval.py:14` / `:20`、`chunking.py:139` / `:149` / `:157`、`lifecycle_store.py:54` / `:57` / `:60` 对应；当前实验通过。正式资料类型查询、订单精确检索、跨品牌适配维护、引用打开 UI、真实历史评测待实现。
- 原件及版本/草稿失败不可检索/原子发布与回滚/下架删除及防复活/审计与操作者：`parse_one.py:76`、`lifecycle_store.py:35` / `:47` / `:80` / `:139` / `:165` / `:176`，最小数据库契约有据。正式不可变对象、维护核对日志、身份认证、Agent 知识建议、任务与页面，以及对象/隐私副本/备份清理均未实现。
- 政策规则与说明同版/正式依据/禁止普通元数据解除 simulation：本轮没有捆绑发布或转正式入口，`probe_lifecycle.py:181` 明确限制；当前模式受 `chunking.py:44` 限制。正式业务发布仍待做。
- 解析/切分/Embedding 配置与摘要/输入变化复用/独立模型空间/PDF 页图定位/章节适用范围：`parse_one.py:67` / `:76`、`chunking.py:47` / `:124` / `:139` / `:157`、`embedding_client.py:33`、`probe_lifecycle.py:124` 对应。当前短资料、页区间和同范围父块有据；关键图片语义发布门禁、同页多型号自动绑定与正式增量 worker 待实现。

### AC 逐项结论

| AC | 本轮结论及实现证据 |
|---|---|
| AC-013 | 实验通过：`chunking.py:149`、`:157` 和 `lifecycle_store.py:57`；型号/品牌/父范围拒绝用例通过。 |
| AC-014 | 实验通过、产品部分：`probe_retrieval.py:14`、`probe_evidence.py:14`；两模型去重补父后 36/36 正例覆盖。正式打开片段 UI 未实现。 |
| AC-015（关联补查） | 无视频/发票/图像事实输出入口；`parse_one.py:67` 只保留解析结构，`probe_parsing.py:66` 不声称视觉事实核验。正式回复验收待做。 |
| AC-016 | 实验通过：`test_knowledge_contracts.py:24`、`lifecycle_store.py:59`；Mock 仍仅 simulation，没有读取 holdout。 |
| AC-055 | 产品部分：`parse_one.py:67`、`:76` 有来源/位置；关键图片发布门禁和完整图号引用未实现。 |
| AC-056 | 实验通过：`chunking.py:139`、`:157` 继承/复核范围，`lifecycle_store.py:58` 拒绝停用资料。 |
| AC-057 | 最小数据库契约通过、产品部分：`lifecycle_store.py:139`、`probe_lifecycle.py:105`；正式失败阶段/重试 UI、任务系统未实现。 |
| AC-058 | 实验部分通过：`probe_lifecycle.py:110` 两连接快照与回滚；政策规则/说明捆绑尚未实现。 |
| AC-059 | 最小资格契约通过：`probe_lifecycle.py:146`、`test_lifecycle_contract.py:110`；正式缓存与邮件提交链路未实现。 |
| AC-060 | 数据库删除契约通过、产品部分：`probe_lifecycle.py:158`；对象、隐私副本、备份清理及删除占位 UI 未实现。 |
| AC-061 | 实验通过、产品部分：`embedding_client.py:33` 输入寻址、`test_knowledge_contracts.py:50` / `:61` 输入变化/过滤字段复用，`lifecycle_store.py:95` 构建幂等。正式 worker 增量联动未实现。 |
| AC-062 | 双模型最小契约通过：`probe_lifecycle.py:124`；四档切分重算一致，300/500 实际输入相同，不能据此定最优切法。 |
| AC-063 | 产品部分：`build_fixtures.py:21` / `:37` / `:52` 覆盖多栏、跨页表、图中文字；`chunking.py:124` 保留 SOP 前提/停止条件。Basic/Standard 缓存重评分均 21/21 关键项、16/16 表行；真实复杂长文/完整图片语义门禁未实现。 |
| AC-064 | 正式未实现、实验明确范围外：README:11；没有新增 UI，因此设计稿/邻居页面视觉对比不适用。 |

## Stage 2：代码质量、测试与安全

- **质量通过。** 14 个 Python 文件均内存编译成功，最大 `probe_lifecycle.py` 243 行。新增产物契约集中在 `artifact_contract.py:12` / `:27`，两个父展开入口共用 `chunking.py:157`；未发现本轮重复实现或超 300 行文件。
- **新增回归有效。** `test_artifact_contract.py:29` / `:34` / `:41` / `:48` 分别覆盖失败状态、run/source/payload 不符、下游停止、比较整体失败；`:26` 有合法输入正例。`test_knowledge_contracts.py:100` 对当前真实候选父对象变更，不依赖不可达前提。本次另外实际走通 CLI 和两个下游失败路径，弥补仅 mock 校验入口不能独自证明跨入口接线的盲点。
- **普通测试 19 通过、5 跳过，不称 24 全通过。** DB 五项按 `test_lifecycle_contract.py:50` 跳过。数据库当前保存报告记录七组检查和完整八项契约测试通过；核对 `probe_lifecycle.py:195` 记录的输入文件摘要/内容摘要全部匹配，清理标志为 true，临时凭据文件不存在。本次未重跑数据库，不能将该保存结果写成此次独立执行结果。
- **安全扫描未见阻塞问题。** 对实验 `.py/.json/.jsonl/.md/.lock` 扫描 eval、危险 HTML、前端敏感变量、provider key 前缀和带凭据 URL，匹配为空。`lifecycle_store.py:107`、`:131`、`:161` 对数据使用 SQL 参数；动态 SQL 仅固定片段。`embedding_client.py:18` 限定 HTTPS/北京域名。`probe_lifecycle.py:199` 随机临时凭据、`:202` 回环地址和所有权标签；`tech-spike/probe_support.py:33` 独立清凭据并先查标签再停容器。`common.py:37`、`probe_lifecycle.py:228` 不输出原异常响应/DSN。合成 PDF 使用已声明 Windows 字体路径（`build_fixtures.py:83`），不属于敏感用户绝对路径。
- **无新增 Spec 漂移。** README:3 / :11 明确实验性质；项目内 `docs/verification/KNOWLEDGE-VALIDATION.md:44` / `:48` / `:58` / `:74` 分别限制相同切分输入、小候选集、开发调参和数据库删除范围。正式 API/UI/worker 缺失未被包装为完成。
- **视觉范围准确。** 本次实际查看 `tmp/knowledge-spike/fixture-preview.png`，四页无可见文字裁切或表行重叠；来源为 `build_fixtures.py:101`。没有新页面，不适用邻居 UI 对比；样本渲染不证明维修图意或真实产品内容正确。

## 可复现证据

离线命令（仓库根目录）：

```powershell
& tmp/knowledge-spike/mineru-venv/Scripts/python.exe -B -m unittest discover -s globalmail-agent/knowledge-spike -p 'test_*.py' -v
uv pip check --python tmp/knowledge-spike/mineru-venv/Scripts/python.exe
```

实际原始结尾：

```text
----------------------------------------------------------------------
Ran 24 tests in 1.046s

OK (skipped=5)
Using Python 3.12.10 environment at: tmp\knowledge-spike\mineru-venv
Checked 115 packages in 5ms
All installed packages are compatible
```

内存编译：同一 Python 对每个 `.py` 执行 `compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec')`，不写 pyc。原始输出：

```text
artifact_contract.py: compile PASS (51 lines)
build_fixtures.py: compile PASS (124 lines)
chunking.py: compile PASS (190 lines)
common.py: compile PASS (45 lines)
embedding_client.py: compile PASS (77 lines)
lifecycle_store.py: compile PASS (186 lines)
parse_one.py: compile PASS (91 lines)
probe_evidence.py: compile PASS (136 lines)
probe_lifecycle.py: compile PASS (243 lines)
probe_parsing.py: compile PASS (118 lines)
probe_retrieval.py: compile PASS (108 lines)
test_artifact_contract.py: compile PASS (62 lines)
test_knowledge_contracts.py: compile PASS (125 lines)
test_lifecycle_contract.py: compile PASS (164 lines)
```

重算方法：`current_inputs()` 对照当前允许源；用 `verify_dataset()` 核对全部八份中间产物，再调用 `evaluate()` 重算排序/覆盖（只排除测时字段），调用 `assemble()` 核对每条返回文档与 token 总量。按完整输入/profile 寻址独立 Embedding 缓存并逐条比较向量；按 guard v2/qwen3.7-plus/实际组装 prompt 寻址 guard 缓存核对输出，并逐字检查引用、预期来源及 supported/insufficient。解析评分仅从已保存解析文本/表格与当前原件摘要重算，没有重新调用解析器。

关键原始输出：

```text
current_sources_parents_chunks_and_query_fingerprints: PASS
query_distribution: {'positive': 36, 'boundary': 12, 'unanswerable': 6, 'multi_evidence': 6}
query_languages: {'en': 30, 'de': 30}
chunks: whole 22 933
chunks: fixed500 50 375
chunks: structured300 124 428
chunks: structured500 124 428
structured300_and_500_identical_embedding_inputs: True
retrieval_recompute: text-embedding-v4 whole PASS
retrieval_recompute: text-embedding-v4 structured500 PASS
retrieval_recompute: qwen3.7-text-embedding whole PASS
retrieval_recompute: qwen3.7-text-embedding structured500 PASS
assembly_recompute: text-embedding-v4 positive 36/36 multi 6/6 boundary 12/12 PASS
assembly_recompute: qwen3.7-text-embedding positive 36/36 multi 6/6 boundary 12/12 PASS
max_context_proxy_tokens: 2525
guard_quotes_expected_decisions_and_sources: 18 /18 PASS; cached responses only
M1_both_expansion_paths_reject_9_parent_mutations: PASS
stale_parsed_pdf_source_hash_rejected: PASS
changed_queries_parents_and_stale_derived_inputs_rejected: PASS
M2_actual_failed_rerun_with_old_disk_cache: top_failed evidence_blocked_before_guard lifecycle_blocked_before_docker PASS
M2_cli_failure_exit_code: 1; final_status: failed; new_run_id: True
independent_embedding_cache_matches: text-embedding-v4 256 unique_inputs PASS
independent_embedding_cache_matches: qwen3.7-text-embedding 256 unique_inputs PASS
independent_guard_cache_matches: 18/18 PASS
saved_lifecycle_verified: 7/7 checks 8/8 tests inputs_match cleanup_flags_true no_credentials_files
security_scan_locations: []
```

首次检索报告加总核对：v4 为 26 批 / 256 唯一输入 / 42676 tokens / 63.80 秒；新模型为 26 批 / 256 唯一输入 / 44317 tokens / 44.17 秒。当前重跑两模型新增输入和 usage 均为零。上述为保存证据的独立一致性核验，不声称再次观察网络调用；静态文件也不能独立证明“冻结在首次调用之前”的历史先后。

审查快照：retrieval run_id 为 `dcf53493-6912-4962-8623-884858cbc3e3`。14 源码文件逐文件 SHA-256 映射经 `common.fingerprint` 计算为 `4623f82b7b6ccd6a2024007b67ae4a462378bb82cae26283d026bf31cecac024`。

| 报告 | 本次读取的文件 SHA-256 |
|---|---|
| retrieval-results.json | `5ab81c648ba22e73e099b7e8bdcf801cad277401f7949b30d16cfaed2d3ffda5` |
| evidence-results.json | `66a97688414f1059a7eb731772bd31d4cd48d336a226ff6f0ffbafb31da23d73` |
| lifecycle-results.json | `6c8786ccd0f00c54ba0feb716d3fbacba9703c57a3db55cd5f6510a96329c895` |

未覆盖且已明确排除：真实业务资料发布、独立未调参测试集、德文母语审校、正式服务与 UI、对象/隐私衍生物/备份清理、政策同版捆绑和客户回复质量。这里的 PASS 不扩大到这些能力。
