# 知识管线实验独立审查

日期：2026-10-07。审查人：fresh code-reviewer。依据：code-review skill、Product-Spec v1.10 REQ-005 及 AC-013/014/016/055–064、KNOWLEDGE-DESIGN v1.0、knowledge-spike/README。

本报告针对主 Agent 开始修复前的实现；下列行号也是该次审查快照。主 Agent 已接收问题并开始修复，修复后须 fresh 复核，本报告不提前认可未审查的修改。

结论：未发现 HIGH。当前固定输入的主要数值和隔离数据库结果可复现；发现 3 项 MEDIUM，修复前不建议关闭本轮。Stage 1 完成范围及证据核验，存在 M1/M3；因没有 HIGH，继续完成 Stage 2，发现 M2。未把缺失正式应用/UI/worker 当成本实验失败。

## Stage 1：范围与需求证据

### 逐项核对

“实验通过”只指列出的最小实验；“部分”不等于正式 AC 已验收。

| 条目 | 判定 | 文件证据与核验结果 |
|---|---|---|
| AC-013 型号隔离 | 当前固定输入通过；M1 待修 | `chunking.py:145` 根据登记 SKU—品牌、mode、rag 和完整时间判断；`lifecycle_store.py:52` SQL 在排序前过滤，`probe_lifecycle.py:86` 执行 60 条查询。离线 12 条边界均无候选；品牌冲突附加 SQL 用例通过。父正文复核缺口见 M1。 |
| AC-014 跨语言检索 | 实验部分实现 | `probe_retrieval.py:12` 必须同时命中文档 ID 和原文锚点；`:18` 实际余弦排序；`probe_evidence.py:13` 组装。两模型 8 组排序与计分从保存的真实向量重算一致；当前查询英德各 30 条。片段有正文，正式打开引用 UI 未实现。 |
| AC-016 simulation/eval 隔离 | 当前输入通过 | `chunking.py:41` 取允许模式交集，`:145` 过滤；`lifecycle_store.py:59` 过滤模式/split；`test_knowledge_contracts.py:24` 验证模式与 eval_holdout 不被放行。本次未读取 holdout。 |
| AC-055 PDF 定位及图片完整性 | 部分实现，声明边界正确 | `parse_one.py:67` 保留块 ID、bbox、页码；`probe_parsing.py:63` 仅检查页/SKU/图像存在性，`:66` 显式限定。`docs/verification/KNOWLEDGE-VALIDATION.md:27` 没有把图片对象当作维修含义验证。正式图号引用、不完整关键图片的发布门禁未实现。 |
| AC-056 共享/专属范围与停用 | 当前固定输入通过；M1 待修 | `chunking.py:43` 按逻辑文档页区间读取，`:136` 子块继承显式范围；`lifecycle_store.py:57` SKU—品牌成对登记 JOIN，`:58` 排除停用/删除。独立 DB 复跑通过。当前 22 份父子范围一致，不代表代码已拒绝不一致输入。 |
| AC-057 未核对/未就绪失败保旧 | 最小数据库契约通过；正式部分实现 | `lifecycle_store.py:139` 检查 ready/reviewed/完整行数；`probe_lifecycle.py:104` 新构建未就绪时旧发布保留；`test_lifecycle_contract.py:68` 部分 INSERT 事务回滚，`:81` 未核对拒绝发布。实际 DB 测试通过；UI/持久化任务明确未实现。 |
| AC-058 原子发布与回滚 | 数据库部分通过 | `lifecycle_store.py:139` 单事务切换 head；`:158` 单条检索语句快照；`probe_lifecycle.py:109` 两连接 REPEATABLE READ、新查询和回滚实测通过。版本标签为合成、不变真实正文/向量，`docs/verification/KNOWLEDGE-VALIDATION.md:74` 已说明；政策规则/说明原子捆绑明确未实现。 |
| AC-059 下架、缓存、回复、晚到任务 | 最小资格契约通过 | `lifecycle_store.py:80` 代次锁及删除栅栏；`:116` 完成时重查；`:165` fresh transaction 复核引用；`probe_lifecycle.py:145` 下架后的新查询、旧引用、旧代次任务均拒绝。缓存为引用资格模拟，不是正式缓存或邮件提交实现。 |
| AC-060 删除与防复活 | 数据库部分通过 | `lifecycle_store.py:176` 下架/tombstone 与删除块同事务；`probe_lifecycle.py:157` 查剩余正文/向量为零，拒绝重建/再发布。`lifecycle-results.json:94` 明确排除对象、检查点、trace、备份清理；没有把实验删除当完整产品删除。 |
| AC-061 幂等与复用 | 实验部分通过 | `lifecycle_store.py:95` 负载摘要及幂等冲突，`probe_lifecycle.py:68` 重复构建无重复行；`embedding_client.py:33` 按模型配置及完整输入寻址；`test_knowledge_contracts.py:50` 标题改变输入摘要、`:61` 过滤元数据修改保持摘要。正式增量 worker/发布联动未实现。 |
| AC-062 模型/切分切换 | 模型最小契约通过 | `probe_lifecycle.py:123` 使用两套真实 1024 维向量，失败保旧、新发布排除旧空间、旧快照保旧空间、回滚均通过；`lifecycle_store.py:58` 检查 profile。`docs/verification/KNOWLEDGE-VALIDATION.md:44` 准确说明 300/500 两档内容相同，未宣称最优参数。 |
| AC-063 困难解析、条件、单位及位置 | 部分实现，未夸大完成 | `build_fixtures.py:21` 多栏，`:37` 跨页表，`:52` 图内步骤；`probe_parsing.py:68` 21 项/16 行评分；`chunking.py:120` 为 SOP 操作保留前提和停止条件。Basic/Standard 两样本均 21/21、16/16，与报告一致；同页多型号自动适用绑定、复杂长文/完整操作语义未实现，`docs/verification/KNOWLEDGE-VALIDATION.md:25` 已限制。 |
| AC-064 无脚本知识维护 UI | 未实现、明确范围外 | `README.md:3`、`:11` 及 `docs/verification/KNOWLEDGE-VALIDATION.md:10` 明确不是正式知识应用；本次没有 UI 或死引导，不以 AC-064 缺失否定组件实验。 |

REQ-005 的本轮相关 MUST 已对应上表：输入白名单/用途（`chunking.py:25`）、显式绑定（`:34`）、跨语言（`probe_retrieval.py:18`）、引用与版本（`lifecycle_store.py:54`、`:130`）、发布/撤销（`:139`、`:176`）、模型隔离与输入摘要（`embedding_client.py:33`）。订单/政策执行授权、完整来源维护入口、真实业务发布及对象清理不在 README 的实验承诺内。

### M1 · MEDIUM：父正文扩展没有重新验证父范围、版本及快照

- 要求：`docs/architecture/KNOWLEDGE-DESIGN.md:142` 明确“父块及邻块也必须重新验证 SKU/用途/版本”；`README.md:9` 承诺适用范围优先、同版来源关联。
- 实现：`probe_evidence.py:18` 只过滤缓存子块，`:26` 从另一个 `documents-normalized.json` 取得父正文，`:28` 直接替换为父全文，返回值仍带旧子块元数据。`probe_retrieval.py:31` 的父扩展也只以注释假定父子相同。
- 复现：仅在内存中将当前 parents 的 `skus`、`allowed_modes` 清空，并把正文改为合成标记；保持缓存子块/向量不变，调用 `assemble(data, 0, parents)`。

```text
{'experiment': 'parent_scope_revalidation', 'parent_count': 4, 'all_parent_objects_ineligible': True, 'blocked_parent_text_returned': True, 'returned_child_scope_still_eligible': True}
```

- 影响：重建父正文/收窄绑定后，用旧检索中间结果复跑可把已不适用正文带入模型，并用旧引用元数据伪装其资格。当前实际 22 份父子范围和源快照一致，未发现本次发布报告发生该泄漏，因此定为 MEDIUM，未推翻本次数值。
- 最小修复：两个扩展路径共用父子校验，检查 `parent_id/document_id/version`、SKU/品牌/模式/用途/时间及不可变正文摘要；不一致时明确失败或排除。测试同时覆盖已撤销父范围、版本/正文变更，不能只对返回的子元数据调用 eligible。

### M3 · MEDIUM：并发发布冲突的声明没有对应实验

- `docs/verification/KNOWLEDGE-VALIDATION.md:72` 写“并发发布冲突”；唯一双线程回归 `test_lifecycle_contract.py:110` 是 `finish()` 等待下架事务的锁后复核代次，`:125` 锁 head，`:126` 下架，`:141` 断言 stale_epoch。`probe_lifecycle.py:109` 是快照观察；`:152` 是串行旧代次发布拒绝。
- 8 项测试确实在真实 DB 通过，但没有两个并发 `publish()` 争抢同一代次的测试。不能把现有证据说成这种测试已经做过。
- 最小修复：将该词改为“晚到任务与下架的锁竞争”。若要保留原声明，另做两个真实连接同时发布、且只有一个成功的用例；本实验无需扩范围即可用文案修正。

## Stage 2：质量、复跑可靠性与安全

### M2 · MEDIUM：下游可把失败运行前的旧缓存重新报告为通过

- `probe_retrieval.py:89` 吞入单模型失败；`:93` 只要求旧模型成功，`common.py:34` 将顶层状态置为 completed。失败模型的既有 `WORK/retrieval-<model>-structured500.json` 没有失效。
- `probe_evidence.py:79`、`:83`、`:97` 直接读父文档与两套旧中间结果；既不检查当前上游模型状态，也不绑定本次 query/父正文/切块摘要。`probe_lifecycle.py:191` 虽记录所读文件摘要，也未检查它们属于当前成功上游运行。
- 违反 `README.md:20` 的“不得留下误导性的旧通过结果”。失败状态写到一个报告，不足以让其他入口知道缓存已陈旧。
- 已用全内存 mock 重现：v4 使用现有向量成功，新模型抛合成异常；保留旧磁盘缓存，替换报告写入为内存，guard 使用旧记录返回，不调用 API、不改磁盘。随后执行 evidence.main()。

```text
{'experiment': 'failed_model_replay_with_old_cache', 'retrieval_top_status': 'completed', 'new_model_status': 'failed', 'evidence_guard_passed': 18, 'evidence_guard_total': 18, 'prior_retrieval_report_checked': False, 'disk_changes': False, 'api_calls': 0}
```

- 最小修复：上游输出 run_id 与输入清单/摘要；每个中间产物绑定同一 run_id、query、父正文、切块和 profile；下游要求所需模型成功且全套一致，失败时停止并产生明确阶段。可以保留旧缓存作历史证据，但不可静默作为当前运行输入。新增“旧缓存存在 + 当前新模型失败”和“query/parents 更新后直接跑下游”的离线回归。

### 其余质量与安全检查

- 12 个 Python 文件全部内存编译成功，最大 `probe_lifecycle.py` 242 行，未超过 300；源码职责基本分离。原始编译输出见下。
- `embedding_client.py:65` 验证响应索引，`:28` 验证维度/有限数值/非零，`:61` 有限次重试；模型失败没有静默换模型。缺口为 M2 的旧产物状态，而不是当前两模型调用真实性。
- `lifecycle_store.py:107`、`:131`、`:161` SQL 数据使用参数，动态 SQL 只拼固定语句片段。扫描新增 `.py/.json/.jsonl/.md/.lock` 未发现硬编码 provider key、URL 内嵌凭据、eval、raw HTML 或用户目录绝对路径。
- `probe_lifecycle.py:198` 随机密码仅在内存/临时 env 文件；`:201` 回环地址随机端口、固定摘要镜像；`:233` 按本次 nonce 所有权清理。依赖的 `tech-spike/probe_support.py:33` 先校验 label，再停止容器，凭据清理独立执行。测试 `test_lifecycle_contract.py:22`、`:36` 覆盖 daemon 故障与不属于本次的容器。实际复跑清理成功。
- `common.py:37`、`probe_lifecycle.py:227` 错误报告只保留类型/安全栈位，不把原异常响应/DSN 放入报告；通用报告还可在 M2 修复时补上失败阶段字段。
- `mineru-requirements.lock:1` 共 115 包，独立环境 `uv pip check` 通过。`python -m pip check` 不可用是该 uv 环境未装 pip；随即使用 uv 验证，不据此判依赖失败。
- 无新增正式 UI，邻居页面视觉比较不适用。查看 `tmp/knowledge-spike/fixture-preview.png`，四页合成样本未见文字裁切/表格重叠；生成依据 `build_fixtures.py:101`。此查看不代表真实维修图片语义审查。
- 无发现范围膨胀。`docs/verification/KNOWLEDGE-VALIDATION.md:3`、`:44`、`:48`、`:58`、`:74` 正确限定组件实验、相同切分内容、小候选库、开发调参及数据库删除范围。`README.md:24` 的“尚未完成运行”应在关闭时更新（低优先级文档清理）。

## 独立复核证据

本次没有调用 Embedding/LLM、下载模型、重新解析 PDF；只读取已允许知识和已保存实验产物。未读取项目 `.env`、raw、`.local-data` 或 holdout；生命周期临时凭据由已授权 probe 自行生成/清除，未输出其值。除本报告，未改源码或已有报告。

当前全部 4 档切块由允许源重新构建，与缓存及 chunking-results 摘要一致；两模型 8 组排序/计分和查询完全匹配。48 项目标证据、96 个逐字锚点均存在且适用。两模型各 256 去重输入、26 批，usage/耗时加总与文档一致。18 个修订 guard 输出的引用全部能在当前组装源找到；初版保留 13/18 结果，16/18 引用检查通过。生命周期报告记录的两份向量文件 SHA-256 与当前文件匹配。静态当前文件不能独立证明“首次调用前冻结”的历史先后，已确认的是当前冻结查询摘要未发生偏离。

原始关键输出：

```text
query_fingerprint_matches: True
query_distribution: {'positive': 36, 'boundary': 12, 'unanswerable': 6, 'multi_evidence': 6}
normalized_parents_match_current_sources: True
whole current_matches_cache: True fingerprint_matches_report: True
fixed500 current_matches_cache: True fingerprint_matches_report: True
structured300 current_matches_cache: True fingerprint_matches_report: True
structured500 current_matches_cache: True fingerprint_matches_report: True
text-embedding-v4 whole scores_match: True queries_match: True
text-embedding-v4 fixed500 scores_match: True queries_match: True
text-embedding-v4 structured300 scores_match: True queries_match: True
text-embedding-v4 structured500 scores_match: True queries_match: True
embedding_calls: text-embedding-v4 256 26 42676 63.8
qwen3.7-text-embedding whole scores_match: True queries_match: True
qwen3.7-text-embedding fixed500 scores_match: True queries_match: True
qwen3.7-text-embedding structured300 scores_match: True queries_match: True
qwen3.7-text-embedding structured500 scores_match: True queries_match: True
embedding_calls: qwen3.7-text-embedding 256 26 44317 44.17
assembly: text-embedding-v4 document_ids_match: True actual_parent_scope_matches: True
assembly: qwen3.7-text-embedding document_ids_match: True actual_parent_scope_matches: True
evidence-initial-results.json reported_pass: 13 recomputed_quote_valid: 16 total: 18
evidence-results.json reported_pass: 18 recomputed_quote_valid: 18 total: 18
lifecycle_input_file_hashes_match: True
labels: 48 phrases: 96 all_exact_source_phrases: True all_target_scopes: True
language_distribution: {'en': 30, 'de': 30}
security_scan_matches: []
```

编译命令为独立 Python 逐文件 `compile(source, path, 'exec')`，只在内存生成代码，不写 pyc。原始输出：

```text
build_fixtures.py: compile PASS (124 lines)
chunking.py: compile PASS (170 lines)
common.py: compile PASS (45 lines)
embedding_client.py: compile PASS (77 lines)
lifecycle_store.py: compile PASS (186 lines)
parse_one.py: compile PASS (91 lines)
probe_evidence.py: compile PASS (132 lines)
probe_lifecycle.py: compile PASS (242 lines)
probe_parsing.py: compile PASS (117 lines)
probe_retrieval.py: compile PASS (100 lines)
test_knowledge_contracts.py: compile PASS (113 lines)
test_lifecycle_contract.py: compile PASS (164 lines)
```

独立离线测试命令：`tmp/knowledge-spike/mineru-venv/Scripts/python.exe -B -m unittest discover -s globalmail-agent/knowledge-spike -p test_*.py -v`。10 个知识测试和 3 个非 DB 生命周期测试通过，5 个 DB 测试按设计跳过；不能称离线 18 个全部通过。原始结尾：

```text
----------------------------------------------------------------------
Ran 18 tests in 0.906s

OK (skipped=5)
```

依赖检查原始输出：

```text
Using Python 3.12.10 environment at: tmp\knowledge-spike\mineru-venv
Checked 115 packages in 4ms
All installed packages are compatible
```

另调用授权的 `probe_lifecycle.main()`，仅将 REPORT 替换成内存接收器以保留主 Agent 原始报告；真实 Docker/PG、真实现有向量和所有断言正常执行。原始输出：

```text
{"check": "initial_publish_real_vectors_and_idempotent_build", "passed": true}
{"check": "sql_scope_before_vector_ranking", "passed": true}
{"check": "unready_replacement_preserves_previous_release", "passed": true}
{"check": "atomic_publication_rollback_and_two_connection_snapshot", "passed": true}
{"check": "real_same_dimension_profile_switch_failure_and_rollback", "passed": true}
{"check": "disable_invalidates_new_search_cache_reply_and_late_task", "passed": true}
{"check": "content_vectors_deleted_tombstone_blocks_rebuild_and_republish", "passed": true}
{"passed": true, "postgresql": "18.6 (Debian 18.6-1.pgdg13+2)", "pgvector": "0.8.6", "contract_tests": {"tests_run": 8, "passed": true, "failures": [], "errors": [], "skipped": []}, "temporary_container_removed": true, "temporary_credentials_removed": true}
Review lifecycle report retained in memory; tracked reports unchanged.
```

审查局限：模型响应及解析性能来自已保存真实运行，不做联网重演；德文未做母语审校；合成样本与小候选集不能代表生产。未审查正式 API/UI/worker、完整隐私清理、备份恢复、政策原子捆绑和业务输出质量，这些已被正确列为后续工作。
