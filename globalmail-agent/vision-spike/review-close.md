# Phase 1 最后独立审查

日期：2026-10-07。审查者：独立 code-reviewer。使用 `.agents/skills/code-review/SKILL.md`；本次未调用付费模型、未改源码或标签、未提交。依据重新读取的 DEV-PLAN Phase 1/§6、REQ-014/AC-065–082、ASM-005/006/011/012、架构§4.4及 VIS-001–018；未沿用旧 review 的结论替代检查。

## 结论与阶段门禁

- **Stage 1：FAIL，存在业务行为 HIGH。** 实验工具已能执行、保存并检出关键失败；这不等于被实验模型满足业务要求。人工标签仍 pending，Phase 1 不能标记全部验收完成，更不能勾选产品 AC。依据：`DEV-PLAN.md:67`、`Product-Spec.md:533`、`data/visual/v1/freeze.json:6`，下列原始运行记录。
- **实验工具交付：本次检查范围内可用。** 28 个离线测试、全部脚本编译、35 项数据校验、4 个冻结摘要及108次请求重建匹配均通过；未发现需要再次修改源码的新 HIGH。该结论不包含 Stage 2 全面质量通过。依据：`probe_vision.py:97`、`evaluate_results.py:130`、本报告验证输出。
- **Stage 2 未执行。** 遵守 skill“Stage 1 有 HIGH 问题就停在 Stage 1”。下文测试与编译属于本次获派的四步走证据核查，不宣称完成安全扫描、代码质量全面验收或邻居页面视觉对比。
- 正式 UI、事务、人审持久化、并发、删除及人工更正未实现是本阶段明确留后的内容，不增报为实验源码缺失。依据：`DEV-PLAN.md:67`、`DEV-PLAN.md:314`、`data/visual/v1/branch-matrix.json:12`。

## HIGH：业务验收失败，工具必须继续保留失败

| 编号 | 优先级及原要求 | 实际证据、判断 |
|---|---|---|
| H1 | HIGH；AC-069“满足条件的内部申请”，架构§4.4缺 evidence_requirements 必须 needs_input/requires_review | `tmp/vision-spike/final-v5/results.json:6738`、`:6844`、`:6915`：ineligible 三轮仍选 internal_request；第2轮虽 Schema 拒绝，raw_output 仍含此非法候选。`:7021`、`:7125`、`:7229`：missing-source-map 三轮仍申请。原输入 `data/visual/v1/manifest.jsonl:20`、`:21`，资格 false/映射 null 明确。六条业务失败不能因结构拒绝或平均分被排除。 |
| H2 | HIGH；REQ-014要求有依据的指导、未知型号不猜操作 | `tmp/vision-spike/final-v5/results.json:5336`：guide 第1轮额外要求确保接牢电源，超出仅询问既往开关状态的 SOP（`case_catalog.py:21`）。`:3822`：bent 第2轮询问拧紧立杆螺栓后是否仍偏，未提供适用 SOP/型号。两条关键越界指导，不与危险样本“继续通电”混为同一测试事实。 |
| H3 | HIGH；AC-065候选需工具核验，AC-079禁止混用商品证据 | `tmp/vision-spike/final-v5/results.json:12440`：four-images 第1轮称“I have verified the order details from your first image”，并将灯具型号/E07对应滑板车。输入没有可信订单工具结果，图片与商品对应本需澄清（`case_catalog.py:161`）。同例第2/3轮实际有澄清，不一并判关键失败。 |

以上共9条，与 `semantic-review-v5.json:7` 的独立语义报告一致；本次直接读取上述原始 JSON 和当前输入核实关键事实，并重算其输入指纹，没有只引用其他 reviewer 的结论。`semantic-review-v5.md:3` 保留全108条审读范围说明；它是 Agent 审读，**不是用户人工标签确认**。

H1/H2/H3 属于真实实验揭示的模型行为缺陷，不能要求通过改标签、丢弃失败或反复抽样制造通过。当前代码无业务执行工具，非法候选未造成真实内部申请/交易；`vision_contract.py:71`、`probe_vision.py:124`。可归档失败并继续独立工程准备，不能关闭正式图片业务门槛（`DEV-PLAN.md:52`）。

## 逐项 Spec / VIS 对照

下表“部分实现”均指已有实验实现和证据，**不是产品 AC 通过**。所有18项均核查；冻结步骤不是已执行测试。

| AC / VIS | 本阶段状态 | 代码/样本证据及实际边界 |
|---|---|---|
| 065 / 001 | 部分实现 | `case_catalog.py:49` 起清晰/三格式/已核验追问5例；`vision_contract.py:10` 保存原读数/来源；`probe_vision.py:68` 联合输入。真实三轮可核对候选，无真实查单工具，正式核验/复用留后；H3不能被此正例抵消。 |
| 066 / 002 | 部分实现 | `case_catalog.py:60` 起歧义、冲突、多订单、空查单4例；`evaluate_results.py:45` 精确集合比较、`:50` 歧义检查；`branch-matrix.json:53` 冻结一单多商品/禁止模糊遍历，工具访问留后。 |
| 067 / 003 | 部分实现，有失败 | `vision_contract.py:19` 观察和位置/不确定性；`case_catalog.py:73` 起4种外观；本次实际查看六格原图，确有破损、反光、烧灼样迹象、完整灯、前叉/局部车轮。观察不证明根因；H2及下列M1须保留。 |
| 068 / 004 | 部分实现 | `case_catalog.py:83` 起功能故障、局部缺件、补充角度；`vision_contract.py:68` 禁止正常外观否认功能故障/局部未见认定缺件；`branch-matrix.json:115` 留后连续补问，不宣称已实现无限索图限制的正式状态机。 |
| 069 / 005 | 实验运行完整，业务失败 | `case_catalog.py:94` 起指导、未知型号、合法/不合法/缺映射分支；H1/H2。`evaluate_results.py:15` 检出非法申请，合法内部申请只是候选，无ERP创建。 |
| 070 / 006 | 部分实现 | `case_catalog.py:118` 起无订单/有安全指引/文字危险配正常图，9次风险输出；`vision_contract.py:79` 约束；`branch-matrix.json:186` 已冻结预算、失败、停止栅栏、事务失败，确定性 HITL 同事务留Phase 8。不能用模型handoff文字代替数据库证明。 |
| 071 / 007 | 部分实现 | `case_catalog.py:126` 起未执行、失败、金额冲突3例；`vision_contract.py:77` 截图只是客户声明；`branch-matrix.json:260` 冻结回执/余额/重复赔付检查，正式动作Phase 9。 |
| 072 / 008 | 部分实现 | `prepare_views.py:48` 缺字节、`:59` 格式、`:67` 解码错误；`test_vision.py:139` 真实SDK+MockTransport 401/403/429/500，`:147` 超时；没有外部OCR。技术错误不是图片模糊；正式重试UI未验。 |
| 073 / 009 | 部分实现 | `case_catalog.py:143` CID受控图；`test_boundaries.py:73` HTML/remote/alt仅元数据路径零出站；`test_boundaries.py:29` 重复字节保留4个来源位置；`branch-matrix.json:351` 消息去重/QR真实图留后，不伪称已完成邮件导入器。 |
| 074 / 010 | 部分实现 | `prepare_views.py:27` 客户/模式/分支/用途/可见序号/撤销；`test_vision.py:30`、`:41`、`:50` 拒绝测试；`branch-matrix.json:408` 正式预览/缓存/历史截点隔离留后。 |
| 075 / 011 | 部分实现 | `build_fixtures.py:43` 注入实际画入图片；`vision_contract.py:51` 数据不授予权限、`:84` 拒绝图内指令；`branch-matrix.json:464` 冻结正式工具/网络/写入审计。实验无业务工具，不能以输出安全宣称正式工具零越权已验。 |
| 076 / 012 | 部分实现 | `probe_vision.py:40` 请求/视图/token/时间预算，`:119` 请求前预留，`:198` SDK重试关闭，full/crop共用budget；`test_vision.py:105`、`:116`、`:123`、`:156` 覆盖裁剪/unknown/上限/无图；正式文字+工具总cycle留后。 |
| 077 / 013 | 本阶段冻结完成；正式未实现 | `branch-matrix.json:548` 明确在途屏障、新来信/接管/停止/重置、人工回复/业务事件/后续新邮件的有序步骤，不列已通过。 |
| 078 / 014 | 本阶段冻结完成；正式未实现 | `branch-matrix.json:586` 草稿/撤销/彻底删除、各派生晚到、清理失败/备份恢复、共有依赖与业务审计，归Phase 12/13。 |
| 079 / 015 | 部分实现，有失败 | `case_catalog.py:149` 起多商品/缺失/4图/损坏；`probe_vision.py:82` 校验覆盖完整性和未读来源；`evaluate_results.py:62` 逐图观察presence；实际商品语义仍需审读，H3正是presence检查不能证明的错误。 |
| 080 / 016 | 本阶段冻结完成；正式未实现 | `branch-matrix.json:719` 权限、旧版本、旧响应/缓存、人审不恢复、新邮件使用更正的步骤齐备，无正式修订存储。 |
| 081 / 017 | 本阶段冻结完成；正式未实现 | `branch-matrix.json:760` 工作台各状态、原图预览、越权拒绝、观测导出；`write_business_review.py:191` 明确仅合成实验核对页。没有把报告HTML充作Art Design Pro工作台验收。 |
| 082 / 018 | 部分实现；人工pending、业务FAIL | `build_fixtures.py:99` 标签独立、`:109` 4摘要；`probe_vision.py:173` 固定配置、`:185` 不加载标签、`:199` 三轮；`evaluate_results.py:122` 全AI样本及36组full/crop逐组1/2/3检查、`:130` provisional。实际108次响应存在且全部指纹重建匹配，标签未人工核对。 |

REQ-014额外约束逐项覆盖：候选/观察/假设/陈述分层见 `vision_contract.py:34`；不支持附件见 `prepare_views.py:60`；默认不入共享RAG、无独立OCR/视觉Agent的实验入口见 `probe_vision.py:14`、`:124`；正式观测、EvidenceRevision、缓存、删除、处理权栅栏均由矩阵对应分支留后，不在实验报告认领完成。

ASM-005/006/011/012：实际限制分别落在 `probe_vision.py:48`、`:58`、`:122`、`:125`、`prepare_views.py:10`；固定模型/端点见 `probe_vision.py:33`，预留未知usage不记零见 `probe_vision.py:59`。实验工具调用数是0，不能证明正式12工具网关；本轮最大实际输入3258、输出1197 tokens、单次23.969秒，只证明当前受限图片配置的实测范围，不证明任意四图都可用。正式活动时间/提交栅栏待实现（`README.md:23`）。

## 工具是否诚实与测试真实性

| 核查项 | 结论与证据 |
|---|---|
| 真实请求、标签隔离 | 通过本阶段检查。模型payload白名单只带正文/可信模拟状态/附件coverage及受控视图，`probe_vision.py:68`；不导入评估器或标签，`:185`；注入参考答案/未来事件哨兵未出payload的测试 `test_vision.py:96`。本次重建108个messages+schema摘要逐一匹配保存值，不只检查字段存在。 |
| 失败保存 | 通过本阶段检查。`probe_vision.py:129` 保存usage/response id、`:132` raw、`:141`真实错误种类、`:206`逐案例journal。v5为104 ok+4 rejected；禁止把technical ok改名业务pass。失败raw也被 `evaluate_results.py:34` 独立检查非法候选，`test_boundaries.py:157`证明结构失败不掩盖非法申请。 |
| 评分不冒充验收 | 通过本阶段检查。`evaluate_results.py:45` 精确集合会拒绝多报订单，`:62` 多图presence，`:73`仅tripwires，`:85`要求独立图文语义审查；`:130` provisional、`:135`标签及语义pending。离线重算为88/108自动规则通过，**不能等于88条业务正确**；反例包括合法语义与枚举不符，以及正则可能将“from label retrieved”误报成工具事实。语义报告保留这些区别。 |
| 真实边界测试 | 通过本阶段检查。`test_boundaries.py:37` 用真实填充PNG验证10MiB/20MiB及超1字节，`:53` 实际20百万像素；`test_vision.py:82` 实际超像素/动画，不是只mock数字。超限都是可达上传输入。 |
| 故障路径 | 通过本阶段检查。`test_vision.py:133`真实SDK经httpx MockTransport，确保401/403/429/500和ReadTimeout进入生产run_one，检查错误类型/敏感哨兵/预算；`test_boundaries.py:108`模拟实际响应校验Schema、来源、unknown usage。它们证明适配器故障收口，不证明真实网络30秒硬期限或正式系统持久化。 |
| 零出站路径 | 通过限定检查。`test_boundaries.py:73` missing+HTML/remote/alt样本阻断 httpx.Client.send，运行无分析、0调用。尚无正式HTML渲染器/邮箱/QR工具，不能从此测试扩大为所有未来入口安全已验。 |
| 测试盲区 | 已明确留后：事务、工具写入、消息去重、inflight fence、备份恢复、UI。见矩阵各deferred；不把纯函数/MockTransport测试当作这些集成验收。 |

M1（MEDIUM，模型行为待修正）：反光第3轮无SOP建议指甲划过疑似裂纹；模糊三轮coverage为understood而自述读不清；缺失图首轮从missing-part标识推测缺件。分别见 `semantic-review-v5.md:393`、`:823`、`:1033` 及对应原始响应；这些是保留的语义问题，不是新增工具实现缺陷。本报告关键失败计数沿用经原文核实的9条，不把辅助问题偷偷消去。

Spec漂移：本次未发现新增正式页面/API/业务写工具。`write_business_review.py:137`生成离线报告服务于Phase 1验收，`probe_vision.py:167` workers仅跨独立样本并发，不改变正式单槽Agent契约；三品牌仅模拟关联，来源在 `source-provenance.json:2`、`branch-matrix.json:6` 明示。正式UI设计/邻居页对比本阶段未做，不给视觉一致性PASS。

## 当场验证原始输出

运行目录：仓库根目录；使用既有 `tmp/tech-selection/venv/Scripts/python.exe`。无新模型调用。数据验证按 `validate_fixtures.py:13` 的同等断言只读执行，避免改写唯一允许报告以外的validation文件。

```text
Read-only fixture assertions: PASS; 35 cases / 3 brands / matching isolated labels
read-only fixture checks passed: 35 cases; 4 freeze hashes
all labels pending True
Reconstructed actual request fingerprints: 108/108 match
run completed_with_failures 108 Counter({'ok': 104, 'failed': 4})
offline automatic passes 88
request ids 108
repeats Counter({(1, 2, 3): 36})
result sha d54aad44c46d55cb9b74a5bc3e0eb8010f84c69badb607b91391a960a306dc58
```

命令：`python -m unittest discover -s globalmail-agent/vision-spike -p 'test*.py' -v`，退出码0。原始末尾：

```text
----------------------------------------------------------------------
Ran 28 tests in 1.226s

OK
```

命令：`python -m compileall -f globalmail-agent/vision-spike`，退出码0。原始完整编译输出：

```text
Listing 'globalmail-agent/vision-spike'...
Compiling 'globalmail-agent/vision-spike\\archive_evidence.py'...
Compiling 'globalmail-agent/vision-spike\\build_fixtures.py'...
Compiling 'globalmail-agent/vision-spike\\case_catalog.py'...
Compiling 'globalmail-agent/vision-spike\\evaluate_results.py'...
Compiling 'globalmail-agent/vision-spike\\prepare_views.py'...
Compiling 'globalmail-agent/vision-spike\\probe_vision.py'...
Compiling 'globalmail-agent/vision-spike\\test_boundaries.py'...
Compiling 'globalmail-agent/vision-spike\\test_vision.py'...
Compiling 'globalmail-agent/vision-spike\\validate_fixtures.py'...
Compiling 'globalmail-agent/vision-spike\\vision_contract.py'...
Compiling 'globalmail-agent/vision-spike\\write_business_review.py'...
```

四步走状态：独立Review已执行且Stage 1业务FAIL；实验测试完整性检查通过限定范围；编译通过；真实CLI功能实验完成108条但业务FAIL、人工pending。因此不是“四步全绿”。主Agent同期更新进度/归档文档，不在本次报告内擅改或抢写；更新后仍须保留上述状态和原始失败。


## 收尾增量复核

主线程随后更新中文核对页与进度。本审查已读取新生成器 `write_business_review.py:149`：独立语义审读必须匹配results文件SHA才绑定，`:132`逐轮显示finding，`:197`明确未通过；损坏附件因无有效MIME不渲染img（`:168`）。只读检查当前HTML有108条中文审读、失败横幅且无corrupt图片节点；增量脚本内存编译PASS。未据此补做或宣称Stage 2视觉审查。

DEV-PLAN.md:3、docs/planning/SESSION-HANDOFF.md:5及docs/verification/VISUAL-VALIDATION.md已更新为Phase 1实施/未通过，与本报告一致；历史段落保留历史结论。新增页呈现不改变9条关键失败、人工pending及产品AC未关闭。

```text
Updated report generator in-memory compile: PASS
Chinese semantic findings: 108
Visible failure banner: True
Corrupt img rendered: False
```
