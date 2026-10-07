# Phase 1 独立复审（运行中快照）

日期：2026-10-07。依据 `.agents/skills/code-review/SKILL.md`，重新读取 DEV-PLAN Phase 1/§6、REQ-014、ASM-005/006/011/012、架构4.4、BUSINESS-SCENARIOS VIS-001–018及初审。未调用付费模型、未修源码、未改样本、未提交。本报告不是最终模型运行验收；主 Agent 同时补文档，以下按审查时源码记录。

## 结论

未发现新增 HIGH。Stage 1 初审阻断已修，仍有评分完整性 MEDIUM；已执行 Stage 2 的代码、安全和测试真实性检查。Phase 1 **尚不能关闭验收**：完整真实运行未结束，标签人工确认及逐条语义安全复核仍 pending。正式 UI、并发、删除、业务持久化按计划仅冻结，不作为本阶段缺实现。没有产品 AC 可据本报告勾选。

## 可修问题

### M1 / Stage 1：字段“精确匹配”实际只测召回，额外错误订单漏报

- 要求：DEV-PLAN.md:67，BUSINESS-SCENARIOS.md:124，分别核对精确字段/歧义。
- 证据：`globalmail-agent/vision-spike/evaluate_results.py:20`、`:23` 使用 `expected_values <= values`。清晰单标签包含正确 FIELDS，同时再输出任意错误订单，仍为零字段错误。这不是已观察到的真实模型错误，是已复现的评分盲区。
- 离线复现：使用 `VIS-001-label` 冻结标签；合法输出包含正确 order/model/error，再添加 `999-9999999-9999999`，route=lookup_order。

```text
EXTRA_WRONG_ORDER {"fields": [], "observations": [], "routing": [], "safety_tripwires": [], "unexpected_risk_needs_review": false}
```

- 建议：对声明完整的同类字段集合检测额外候选，歧义允许集合明确单列；若保留纯召回指标，报告必须另列未检查的误报，不能称字段精确匹配通过。无需改变模型输入。

### M2 / Stage 1：多图观察评分不能发现混用商品与漏读

- 要求：Product-Spec.md:543 / AC-079；每图保留关联、覆盖，不混用商品证据。
- 证据：`evaluate_results.py:32` 将所有图观察扁平为类别集合；`case_catalog.py:138` 的 two-products 标签只有全局 damage_visible。`probe_vision.py:82` 仅验证引用是合法 ready 附件。
- 离线构造合法 Analysis：a1（实际灯）观察写“The scooter is bent”；a2不输出观察；两图coverage都称understood。来源校验接受，评分所有错误数组为空。

```text
WRONG_PRODUCT_AND_OMITTED_SECOND {"fields": [], "observations": [], "routing": [], "safety_tripwires": [], "unexpected_risk_needs_review": false}
```

- 建议：独立评估标签增加逐图允许观察/关联，保留旧标签与旧评分版本；或明确该项必须逐次人工核验、自动指标不覆盖关联正确性。不能把category命中作为两件商品均正确的证据。

### M3 / Stage 2：local矩阵与24项测试覆盖不完全对应

- 证据：`data/visual/v1/branch-matrix.json:366` 的 remote-and-alt-only 声明 local，并给出HTML/远程URL/alt文字/缺字节参数；`test_vision.py:96` 测的是顶层标签/未来字段allowlist，`:155` 测空attachments，并未构造该HTML分支。`test_boundaries.py:79` 只补PDF/MP4/MP3。
- 影响：没有远程抓取实现，不构成已发生网络泄漏；但不能用24 PASS宣称所有local矩阵均实测。补真实adapter入口HTML/alt-only/无字节用例并捕获零出站，或诚实标未执行。

### M4 / Stage 2：冻结矩阵与来源摘要被写入但未核验

- 证据：`build_fixtures.py:111`、`:112` 写入 branch_matrix_sha256、provenance_sha256；`validate_fixtures.py:16` 只核 manifest/labels。修改来源说明或分支矩阵后仍可通过当前fixture校验。当前manifest/labels/matrix摘要实际匹配，未发现已篡改内容。
- 建议：离线验证四个冻结摘要，保留原始冻结版本；无需模型重跑。

## Stage 1 逐项对照

下列“实现”仅指隔离实验；真实模型稳定性取决于完整结果与人工复核。源码路径省略前缀 `globalmail-agent/vision-spike/`。

| VIS / AC | 判定及证据 |
|---|---|
| 001 / 065 | 实验输入完整：三格式、空正文、verified-followup，case_catalog.py:47；prepare_views.py:58 解码。真实查单/跨轮复用按矩阵留正式阶段。 |
| 002 / 066 | 歧义、冲突、多订单、查空样本完整，case_catalog.py:58；vision_contract.py:52 明确不修复字符。评分尚有M1。 |
| 003 / 067 | 破损、变形、反光/阴影样本完整，case_catalog.py:68；Observation与hypotheses分栏vision_contract.py:20、:38；人工视觉标签pending。 |
| 004 / 068 | 功能故障、局部未拍配件、补角度完整，case_catalog.py:78；禁止以照片否定故障见vision_contract.py:68。持续业务循环留后续。 |
| 005 / 069 | 指导、未知型号、资格满足/不满足、缺映射完整，case_catalog.py:88；可信状态是明示合成快照，非真实工具。正式资格服务留Phase 9。 |
| 006 / 070 | 图像危险、客户报告危险、订单/指引有无完整，case_catalog.py:110；正式风险事务/失败优先级仅冻结，branch-matrix.json:233。 |
| 007 / 071 | 未执行/失败/金额冲突截图完整，case_catalog.py:118；vision_contract.py:77 禁止截图认定交易成功。正式账本不在实验执行。 |
| 008 / 072 | 模糊样本、缺失/损坏/不支持、SDK超时/鉴权完整；case_catalog.py:130、prepare_views.py:47、:67；test_vision.py:135、:143 真实SDK MockTransport通过。 |
| 009 / 073 | CID/附件/仅图片清单完整，case_catalog.py:132、:49；输入无远程fetch代码。HTML/alt-only实测缺口M3；正式入口去重延期。 |
| 010 / 074 | scope四维、序号、撤销、隐私、路径、摘要拦截已测，prepare_views.py:20、:27；test_vision.py:30、:41、:50。正式预览/缓存延期。 |
| 011 / 075 | 注入图片样本case_catalog.py:134；请求只allowlist，probe_vision.py:68；标签/未来字段sentinel测试通过。无业务工具，不能替代正式工具越权验收；自然语言安全pending。 |
| 012 / 076 | 请求/视图/token/time共用预算probe_vision.py:48、:200；usage未知保留占用:58、:149；无图/全不可读零请求:102、:105；dense字段及预期crop完整性评分已补evaluate_results.py:18、:88。 |
| 013 / 077 | 仅冻结晚到、停止、接管和HITL恢复屏障，branch-matrix.json:554；按计划不要求实验数据库实现。 |
| 014 / 078 | 仅冻结删除、派生清理、晚到/备份、共享依赖，branch-matrix.json:594；没有宣称删除完成。 |
| 015 / 079 | 两商品/缺一图/4图/损坏混合样本完整，case_catalog.py:138；4图、10/20MiB精确字节、20M像素、6/7视图离线通过，test_boundaries.py:28、:37、:53及test_vision.py:105；语义关联评分M2。 |
| 016 / 080 | 仅冻结人工修订、权限/版本及旧缓存，branch-matrix.json:722；正式阶段验收待办。 |
| 017 / 081 | 仅冻结Art Design Pro、预览/状态/权限，branch-matrix.json:774；实验阅卷页不充当工作台。 |
| 018 / 082 | 35 AI样本、108期望调用、labels隔离及manifest/labels摘要校验具备，freeze.json:2、evaluate_results.py:75、:88；完整运行/人工确认pending，冻结校验有M4。 |

初审修复：H1 dense有FIELDS且expected_keys来自冻结全量；M1请求异常设unknown；M2无可读图零请求；M3 ready不能伪missing/failed；M4增精确边界但仍有本次M3；M5 labels摘要已核。证据见evaluate_results.py:18、:75、:88，probe_vision.py:93、:105、:149，test_boundaries.py:37。

ASM及横向要求：prepare_views.py:10限制4图/10MiB/20MiB/20M像素与受限视图；probe_vision.py:48限制6模型/6视图/120秒/16k/2k/80k，:125设≤30秒传输timeout，:200全图裁剪共享Budget；12工具因零业务工具不适用。当前快照实际prompt最大2477、completion最大825，所有prompt低于估算。HTTP timeout不证明完整事务活动时限，README.md:25已诚实区分。无OCR、共享RAG或生产写工具，未发现scope creep。实验不导出原图base64到结果，probe_vision.py:102；原始合成回复在tmp保存，非外部观测。

## Stage 2

- 代码结构：10个Python均不超过300行，最大probe_vision.py 225行。模块分为输入、schema、调用、离线评分及阅卷；异常不记录供应商body/Key，probe_vision.py:137。部分函数缺静态类型，LOW，不阻断实验。
- 测试真实性：24项实际执行，故障用SDK+MockTransport，字节边界用真实填充PNG、像素用真实图片，无付费调用；未将MockTransport冒充供应商成功。M3为剩余覆盖盲区。
- 安全扫描：源码搜索eval、innerHTML/dangerouslySetInnerHTML、前端敏感变量、硬编码key/password无命中；唯一模型端点与模型名白名单probe_vision.py:33，路径限制prepare_views.py:20；未发现明确密钥泄漏/执行注入。request_payload无labels导入，测试sentinel通过；trusted为实验显式合成工具快照，不是评分标签。
- 视觉比较：没有正式页面改动；本次未打开正式邻居页面，不声称UI一致性通过。实验阅卷页用于人工确认，正式UI延期有计划依据DEV-PLAN.md:67。该项不构成已完成产品UI验收。

## 实测原始输出

命令：`tmp/tech-selection/venv/Scripts/python.exe -B -m unittest discover -s globalmail-agent/vision-spike -p 'test_*.py' -v`。24项分别为全部不可读、4图重复来源、外层数组、usage缺失、评分负例、来源及coverage、10/20MiB、20M像素、不支持格式、PNG解码、scope/历史、HTTP故障、超字节、预算、5图、共享裁剪预算、缺失/损坏、无图、allowlist、超像素/动画、撤销/隐私、超时、路径/摘要、unknown保留。

```text
----------------------------------------------------------------------
Ran 24 tests in 1.186s

OK
```

内存编译避免写pyc，逐文件执行`compile(read_text(encoding='utf-8'), path, 'exec')`，原始输出：

```text
COMPILE build_fixtures.py 118
COMPILE case_catalog.py 150
COMPILE evaluate_results.py 111
COMPILE prepare_views.py 96
COMPILE probe_vision.py 225
COMPILE test_boundaries.py 134
COMPILE test_vision.py 164
COMPILE validate_fixtures.py 35
COMPILE vision_contract.py 89
COMPILE write_business_review.py 195
PASS: 10 Python files compiled in memory
```

真实运行仅只读检查，不自行付费。审查快照原始输出：

```text
FINAL_SNAPSHOT running 45
FAILED [('VIS-001-png-only', 3, 'full', 'ValidationError'), ('VIS-002-multiple-orders', 1, 'full', 'ValidationError'), ('VIS-002-multiple-orders', 3, 'full', 'ValidationError'), ('VIS-002-lookup-empty', 2, 'full', 'ValidationError')]
ACTUAL_USAGE_MAX 2477 825
PROMPT_LESS_THAN_ESTIMATE True
```

对应 `tmp/vision-spike/final-v4/results.json:272`、`:2235`、`:2431`、`:3037`。这些技术失败被正确保留并拒绝；不得擦除后改称108次全部有效。当前仅抽读45条结果及18条客户回复，不构成全量语义安全审查；完整108次与人工pending须主Agent最终汇总。
