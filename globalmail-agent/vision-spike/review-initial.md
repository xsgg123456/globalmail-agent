# Phase 1 独立初审

日期：2026-10-07。使用 `.agents/skills/code-review/SKILL.md`，只审实验，不要求提前实现 Phase 8/12/13。审查期间代码仍在变化；本报告是初审快照，修复后须 fresh 复审。未调用付费模型、未改冻结样本、未运行会覆写 fixture 的生成/验证入口。

## 结论

**Stage 1 不通过：1 项 HIGH，5 项 MEDIUM。Stage 2 未执行。** 人工标签 pending、语义安全复核 pending、真实运行尚在进行，均诚实保留为验收待办，不要求冒充人工 PASS。没有前端改动，不做工作台视觉验收。

## 可修复发现

### H1：核心全图/裁剪实验缺少真实字段评分，完整性检查允许整组裁剪缺席

- 需求：DEV-PLAN.md:58、67 要求全图/裁剪对照并分别核对精确字段；BUSINESS-SCENARIOS.md:120、126 要求保存实际专项结果。
- 证据：`case_catalog.py:136` 的 dense 样本未设置 expected_fields；`data/visual/v1/evaluation/labels.jsonl:31` 为 `{}`。`evaluate_results.py:18` 只遍历已有标签字段，所以完全不读出订单也通过字段检查。`evaluate_results.py:81` 从实际记录而非预期集合枚举 variant，缺失全部 crop 仍可输出两个完整性标记为 true。
- 离线复现原始输出：

```text
DENSE_NO_FIELDS {"fields": [], "observations": [], "routing": [], "safety_tripwires": [], "unexpected_risk_needs_review": false}
WITHOUT_ALL_CROPS True True
```

- 第一例输入零字段、unreadable、ask_customer；第二例生成全部 33 样本各 3 次 full，故意完全没有 crop。没有执行真实模型。
- 修复：为 dense 单列可读字段或可判定的读数/歧义对照标准；从冻结输入的 crop_compare 推导应有的 `(id, variant, repeat)` 集合，精确比较实际记录。若修改标签，应显式版本化并保留旧标签/旧评分，不能默改已冻结结果含义。

### M1：失败请求保留额度，但错误标示 usage 已知

- 需求：Product-Spec.md:522、540，AGENT-ARCHITECTURE.md:199：未知 usage 保持 unknown 与保守占用。
- 证据：`probe_vision.py:58` 只有 settle(None) 才设置 unknown；网络异常绕过 `probe_vision.py:120` 至 122，最终 `probe_vision.py:146` 仍输出 false。
- 实际 SDK + MockTransport ReadTimeout 输出：

```text
TIMEOUT {"status": "failed", "usage": null, "budget": {"calls": 1, "views": 1, "tokens_reserved_or_used": 8909, "usage_unknown": false}, "error_type": "APITimeoutError"}
```

- 修复：记录请求是否发出及是否收到完整 usage；无结算的已发请求保留预留并标 unknown。不能对请求前校验拒绝伪记供应商调用。

### M2：损坏图片分支与冻结矩阵的“无模型调用”不一致

- 需求/冻结断言：`data/visual/v1/branch-matrix.json:23` corrupt 要求 unreadable 且 no model call。
- 证据：`prepare_views.py:66` 保留 unreadable，但 `probe_vision.py:101` 只对 attachments 为空跳过，全部损坏附件仍进入 `probe_vision.py:115`。
- SDK mock 实测：

```text
CORRUPT {"outbound_requests": 1, "coverage": [{"attachment_id": "a1", "status": "unreadable", "reason": "decode_failed_or_unsupported"}], "budget": {"calls": 1, "views": 0, "tokens_reserved_or_used": 7814, "usage_unknown": false}}
```

- 修复：明确全部不可读取时走本地状态路径或正式纯文本路径的契约。当前实验应实现其 no-call 断言并测出站次数；混合有效图/损坏图继续保留逐图状态。元数据文字补问不可声称已读图。

### M3：来源校验允许模型伪造缺字节/格式/技术状态

- 需求：Product-Spec.md:521、536，逐图状态必须真实区分技术与图像问题。
- 证据：`probe_vision.py:87` 至 90 只约束非 ready 输入。ready 图可以由模型回传 missing/unsupported/failed 并被接受；这些是适配器掌握的事实，不能任由视觉模型改写。
- 离线验证：对 ready a1 构造合法 Analysis，coverage 为 missing，`validate_sources` 正常返回：`READY_CAN_BECOME_MISSING: accepted`。
- 修复：ready 来源只接受语义处理结果 understood/partial/unreadable；missing/unsupported/failed 由适配器确定。补 SDK 响应层测试：额外字段、外层数组、截断、未知引用、coverage 缺项/重复/非法转态均失败，保留原始失败输出。

### M4：矩阵的本地边界尚未逐项执行

- 需求：DEV-PLAN.md:57、370，`branch-matrix.json:23`、24、30 声明本地分支。
- 证据：`test_vision.py:59` 仅 5 图拒绝；70 仅单文件超限；82 仅超像素/动画；105 测 6/7 视图。没有 4 图接受、10MiB 等值、20M 像素等值、独立 20MiB 总量等值/超值、同图两个独立 attachment ID 的测试。PDF/视频/音频、远程 HTML/alt-only 也未按矩阵构造并断言实际路径；15 测试通过不等于该矩阵全覆盖。
- 修复：补离线实际字节边界和请求计数测试，给每个 local 分支明确测试定位；剩余不能执行的逐项标 pending，不能把矩阵存在当已测。大文件应在临时目录创建，不改冻结输入。

### M5：评分标签没有验证冻结摘要

- 需求：DEV-PLAN.md:63、67，冻结隔离标签后评估，结果必须能定位对应标签版本。
- 证据：`evaluate_results.py:68` 只验证 manifest；70 读取 labels，89 只记录当前摘要，未对照 `data/visual/v1/freeze.json:3`。故后改标签会直接用于旧结果评分而不报冻结不一致。`build_fixtures.py:109` 冻结也未包括 branch-matrix/provenance 的摘要。
- 修复：run 或独立评估配置保存冻结 labels/矩阵版本摘要，评分前验证；人工确认后的新标签显式生成新评估版本，保留原始结果。

## Stage 1 逐项覆盖

下表“代码具备”只指本阶段实验路径，不表示对应产品 AC 验收通过。表中路径未写前缀者均在 `globalmail-agent/vision-spike/`。

| VIS / AC | 初审判定与证据 |
|---|---|
| 001 / 065 | 三格式与纯图片、已核验后追问样本具备，`case_catalog.py:47`、55；业务精确查单与跨轮复用留正式阶段，`branch-matrix.json:16`。 |
| 002 / 066 | 歧义、冲突、多订单、查空样本具备，`case_catalog.py:58` 至 67；一单多商品只冻结，`branch-matrix.json:17`。禁止模糊遍历为 prompt 约束 `vision_contract.py:59`，实验无工具，不能证明正式网关。 |
| 003 / 067 | 破损、变形、反光/阴影对照具备，`case_catalog.py:68` 至 77；已实际查看六格源图，裁剪坐标 `build_fixtures.py:49`。独立人工标签仍 pending，非本审查替代。 |
| 004 / 068 | 功能故障、局部缺件、补图具备，`case_catalog.py:78` 至 87；禁止否定故障/认定缺件见 `vision_contract.py:55`；循环收口留 `branch-matrix.json:19`。 |
| 005 / 069 | 指导/补问/合法内部申请、资格不满足、缺来源映射具备，`case_catalog.py:88` 至 109；兼容未知及证据服务留矩阵20行。本实验无业务写工具，不能宣称申请已提交。 |
| 006 / 070 | 图片/文字危险及有无订单/指引具备，`case_catalog.py:110` 至 117；确定性落库、人审栅栏与错误优先级冻结在矩阵21行，按派发不要求本阶段实现。 |
| 007 / 071 | 未执行、失败、金额冲突回执具备，`case_catalog.py:118` 至 129；提示词65行只候选查询，实际账本约束留矩阵22行。 |
| 008 / 072 | 模糊样本及缺失/损坏/超时测试具备，`case_catalog.py:130`、`test_vision.py:64`、147；部分不支持分支缺测试，损坏调用违反矩阵，见 M2/M4。 |
| 009 / 073 | CID 元数据与三入口样本具备，`case_catalog.py:132`、`build_fixtures.py:94`；没有正式 HTML/CID 导入器，同源去重/QR 留矩阵24行；本地 remote/alt-only 待测。 |
| 010 / 074 | 客户/模式/分支/用途、序号截点、撤销、隐私、路径、摘要在 `prepare_views.py:19` 至 56，离线测试30、41、50行通过；正式预览/缓存历史留矩阵25行。 |
| 011 / 075 | 图片内实际攻击文本由 `build_fixtures.py:43` 绘制；请求只 system PROMPT + user 图文，`probe_vision.py:67` 至 77；标签/未来 options sentinel 测试96行通过。实验不给工具，不等于正式工具零越权验收；回复语义安全尚待逐条复核。 |
| 012 / 076 | 6调用/6视图/120秒/16k/2k/80k预留、30秒timeout、无自动重试见 `probe_vision.py:47`、114、176；全图与裁剪同 Budget 见179行；无图零调用测试155行通过。H1/M1 尚未满足；12工具预算因实验无工具不适用。 |
| 013 / 077 | 新来信/接管/停止/重置及人工回复屏障仅冻结 `branch-matrix.json:28`，明确 not executed，符合阶段边界。 |
| 014 / 078 | 草稿移除、撤销、彻底删除、晚到/恢复/清理失败、共享依赖仅冻结矩阵29行；不要求此实验实现删除系统。 |
| 015 / 079 | 两商品与一图缺失实际样本 `case_catalog.py:138` 至 143；逐图来源/coverage `prepare_views.py:83`；状态拒绝及若干边界存在缺口 M3/M4，正式部分失败关联留矩阵30行。 |
| 016 / 080 | 更正、权限、版本和旧结果/缓存矩阵31行，待正式阶段。 |
| 017 / 081 | Art Design Pro UI、预览状态、受限导出矩阵32行，待正式阶段；标签 review.html 为实验阅卷工具，无用户业务 UI 漂移。 |
| 018 / 082 | 33个实际样本/隔离标签，`freeze.json:5`、`build_fixtures.py:99`；模型运行日志审查快照为 running、8条、无技术失败，仅过程证据。H1/M5及人工 pending 未满足最终验收。 |

REQ-014其余横向要求对应：本地受控静态字节、无远程加载见 `prepare_views.py:19`、58；字段/观察/推测/客户陈述分栏见 `vision_contract.py:10` 至43；图中文字不可信与无自动业务动作见46至75；原图/派生来源和坐标见 `prepare_views.py:83`；观测未接入外部回调且记录剔除data_url见 `probe_vision.py:100`。正式持久化、撤销、共享RAG隔离及API边界按矩阵留后续阶段。未发现当前范围新增产品功能；图片/实验阅卷页不是正式工作台。

ASM-005/006/011工程限制：配置 `prepare_views.py:10` 至12、Budget限制代码47至64存在；官方视觉说明确认Qwen3.7在低分辨率模式按32×32像素/token以及max_pixels约束，当前计算没有将base64长度当图像token：[百炼视觉理解](https://help.aliyun.com/zh/model-studio/vision/)。实际预算适配仍须完整真实请求结果，不能仅由静态公式断言。

## 实测与编译原始输出

命令：`tmp/tech-selection/venv/Scripts/python.exe -B -m unittest discover -s globalmail-agent/vision-spike -p test_vision.py -v`。15项离线测试均为真实执行；SDK出站使用 MockTransport，不访问付费端点。

```text
test_actual_png_decode_and_coordinate_provenance ... ok
test_all_scope_dimensions_and_history ... ok
test_auth_and_server_failure_no_error_body_leak ... ok
test_byte_limits_using_real_files ... ok
test_call_time_and_token_boundaries ... ok
test_count_boundary_never_silently_truncates ... ok
test_crop_is_bounded_and_shares_view_budget ... ok
test_missing_and_corrupt_are_distinct ... ok
test_no_image_no_added_request ... ok
test_payload_allowlist_never_labels_or_faults ... ok
test_pixel_limit_and_animation ... ok
test_revocation_and_privacy ... ok
test_timeout_is_technical_not_image_quality ... ok
test_traversal_and_hash_change ... ok
test_unknown_usage_keeps_reservation ... ok
----------------------------------------------------------------------
Ran 15 tests in 0.448s

OK
```

为不写 pyc，执行内存编译 `compile(f.read_text(encoding='utf-8'), str(f), 'exec')`，遍历实验目录全部 Python。评估器出现后再次编译的完整原始输出：

```text
PASS: 8 Python files compiled in memory
```

Stage 2 代码风格/安全扫描/测试真实性全面审查未执行；以上测试用于 Stage 1 行为核验。`docs/verification/VISUAL-VALIDATION.md:3` 诚实标实施中；README/结果汇总尚待主 Agent 完成（DEV-PLAN.md:62、64、65），不将运行中的工作提前记 PASS。
