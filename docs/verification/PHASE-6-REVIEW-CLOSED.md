# Phase 6 第三轮独立审查：Stage 1 FAIL

日期：2026-10-08。基线：Phase 5 `d0833a4`；审查本轮未提交实现。**Stage 1发现新增HIGH：长文后置的必要停止条件未进入操作父块与向量输入。Stage 2未执行，不能本地升级或宣称Phase 6通过。**

本期用户明确批准因线程上限复用已结束审查实例。本报告如实记录复用及重新完整读取，不称fresh。审查者不修改产品代码、不提交、不再spawn；只写本报告及`artifacts/phase6/review-closed-*`。前两轮[初审FAIL](PHASE-6-REVIEW.md)、[复审FAIL](PHASE-6-REVIEW-FINAL.md)及原false证据保持原文。

## 规划与完成标准

已重新读取AGENTS、code-review skill、Product-Spec REQ-005/AC-013–016/055–064/SCREEN-002/CMP-010–012/5.11–5.12、AGENT-ARCHITECTURE第6–8节、DEV-PLAN Phase 6、PHASE-6-IMPLEMENTATION及docs/README原文。没有Design-Brief或设计稿，UI基准是既有Art Design Pro及相邻工作台/系统页面。

| 顺序 | 目标 | 完成标准及实际状态 |
|---|---|---|
| 1 | 重建源需求矩阵；核对历史修复 | 逐项源码定位；1.0旧渲染原文、1.1关键事实、缓存指纹及之前前提/筛选修复独立重验。已完成源码与无PG反例检查 |
| 2 | 独立动态协议检查 | 等主Agent完整后端结束再取得独占PG窗口；随机schema/私有object目录。尚未开始，发现HIGH后停止 |
| 3 | 最终真实检索与页面 | 审核冻结72条原始正文结果；实际qwen/v4构建、发布、检索、引用、下架、全覆盖切换、回滚及未知响应跨关闭同body/key。尚未开始 |
| 4 | Stage 2质量与视觉 | Stage 1无HIGH后执行实际明暗/宽窄/邻居对照及安全、类型、文件大小、测试真实性。没有进入Stage 2；只保留HIGH发现前已跑准备证据 |

下文`B`=`globalmail-agent/backend/src/globalmail_agent`，`F`=`globalmail-agent/frontend/src`，`T`=`globalmail-agent/backend/tests`。行号以本轮审查代码为准。

## HIGH：长文后置停止条件被操作证据遗漏

源要求：`AGENT-ARCHITECTURE.md:325`明确“长文按章节/完整步骤切分，步骤携带必要前提/停止条件”；`Product-Spec.md:355` AC-063要求保留前提/警告/单位及原件位置，关键缺失阻止发布或明确排除。实施计划第1步也要求长文保留前提和停止条件。

实际差异：`B/knowledge/chunking.py:72`的`contexts`仅取操作组开始前的`retained[:retained.index(group[0])]`（:77），再从其中找安全块（:78）。步骤后面的“停止条件”章节不在该集合内；`:113`只合并当前组和已有prior的警告，无法补入后置停止段。

独立反例使用项目自编测试正文，**通过真实隔离本地parser子进程及生产schema**，没有PG、模型或正式数据写入：合法`globalmail.knowledge/1`排障JSON包含9段长检查步骤，随后是“停止条件”标题和完整段落：

> 出现焦味时立即停止操作，断电并交人工。此停止条件适用于上述所有检查步骤。

操作和停止段分别保留真实section，各自明确绑定同一登记SKU `H-CTD16-US-BK`与相同适用依据，未伪造document绑定覆盖。`parse_bytes`实际调用`parse_document.py`，诊断为空；生产`chunks`生成2个操作父块和5个输入，它们全部缺失上述停止条件。此输入属于已支持的受控结构JSON路径，未读编辑源替代PDF。

[独立反例脚本](artifacts/phase6/review-closed-stop-counterexample.py)、[完整源输入/parser版本/父块/输入输出](artifacts/phase6/review-closed-stop-counterexample.json)。原始输出（exit0，false表示实测缺失）：

```json
{
  "operation_parent_count": 2,
  "operation_parents_have_required_stop": [false, false],
  "operation_inputs_have_required_stop": [false, false, false, false, false],
  "diagnostics": []
}
```

它是必要停止条件的实质遗漏，不是同义措辞或检索分数问题。`build_checks.py:33`直接用这些父块建立计划，`:95`的资格校验检查原件/核对/摘要/manifest，没有发现这种条件丢失的门。`retrieval.py:113`按文档去重，返回操作父块时不会自动再拼同文档的另一个停止父块。这里没有冒称已经实际查询模型；缺失结论直接来自生产切分结果。

**完成标准**：必要停止条件在原文位于步骤后时，相关操作父块及完整向量输入仍保留它；继续按实际SKU资格区分，不能把A专属停止条件泄漏给B，也不能无条件把无关章节全并入。保留原章节/页码/依据和1000长输入、2000父/2500短输入预算；无法安全保留时须阻止构建或明确排除相关操作。补真实parser→PG/HTTP及返回正文回归，再从Stage 1重审。

## 历史问题修复核验

| 原问题 | 本轮独立证据与状态 |
|---|---|
| 首轮HIGH 同SKU不同章节/basis漏先置前提 | `chunking.py:67,72,89`按SKU资格连接，完整警告段及安全标题所辖块保留。独立重跑生产schema/ParserBlock/Applicability变体：A独有警告、A+B共享操作分parent，B不带A警告；同SKU短三章节及独立basis完整保留。原先置反例关闭；本轮另发现后置停止遗漏 |
| 首轮MEDIUM 无发布状态筛选 | `release_queries.py:21`关联当前head/ready/revocation；`queries.py:41`及API Literal分published/unpublished/withdrawn，普通v2草稿不覆盖旧v1发布；`F/views/knowledge/index.vue:23,133`独立发布筛选及下架标签。源码存在；本轮独立HTTP/GUI未执行 |
| 二轮HIGH 可读政策缺明确退款接受等条件 | 独立生产`parse_policy`读取v1/v2实际JSON，1.1完整说明含具体金额币种明确接受、询问/不满/未回复非接受、替代SKU选择/适配/人工、查旧申请与执行及取消/补偿核对。`policy_bundle.py:91`修复实质事实；同rules/schema、不同description SHA，原件不变。纯函数关闭；本轮PG/真实返回正文待补 |
| 旧生成器/版本不可静默改写 | AST提取源码，与基线`d0833a4`逐字符比对，`render_legacy`除函数名外与旧render完全一致。`policy_bundle.py:121`支持1.0/1.1；`build_checks.py:47`按存储generator复算全部bundle，旧1.0明确409 requires_revision；`builds.py:33`在profile保存和付费worker调用前执行plan。`parser_profiles.py:28`把policy_bundle源码纳入fingerprint，旧parse cache不能跨生成器复用 |
| 二轮MEDIUM 未确认响应关闭后丢选择 | `F/composables/knowledge-index-preferences.ts:1`保每版profile/chunker及整批target/selected；`ReleaseManager.vue:172`保合格非默认选择及明确空值。`useReleaseManager.ts:20`全部分页、每文全部版本构建，历史v1合格候选不因当前v2草稿消失。源码修正；真实已提交丢响应→关闭重开同body/key尚未执行 |

[第三轮结构变体脚本](artifacts/phase6/review-closed-chunking-variants.py)、[实际重跑输出](artifacts/phase6/review-closed-chunking-variants.json)、[政策/旧render源码审查脚本](artifacts/phase6/review-closed-policy-check.py)、[实际原件SHA和完整1.1/1.0说明输出](artifacts/phase6/review-closed-policy-check.json)。不拿先置警告PASS替代本轮后置停止反例。

## Stage 1：逐条源需求匹配

此表区分源码实现、已独立验证与待验，不把存在代码当成动态PASS。

| REQ-005原文行 | 实现及本轮结论 | 代码位置 |
|---|---|---|
| 323 新白名单/用途/未复核不自动入索引 | 固定prepared rag白名单；build必须核对，原件和parser对象重核；源码存在 | `B/knowledge/prepared.py:22`；`build_checks.py:10,19,33` |
| 324 五类政策/可读与程序条件/非相似度授权 | 新1.1关键条件独立核实；完整bundle同版校验；正式业务执行后续，PG待验 | `policy_bundle.py:91,121`；`build_checks.py:47`；`releases.py:65` |
| 325 来源/品牌/版本/型号/时间/可信度 | manifest和引用保source_kind、allowed_modes、用途与available_at；不读取视频 | `releases.py:56`；`references.py:20`；`retrieval.py:47` |
| 326 代表产品族/七类业务/自编非官方 | 保留prepared 22份simulation来源；本期不是七类正式Agent闭环 | `prepared.py:22`；`F/views/knowledge/index.vue:20` |
| 327 语义+精确品牌/SKU/类型/共享依据 | 先过滤登记SKU/品牌/类型/时间/范围，再PG精确余弦；源码存在，独立PG待验 | `retrieval.py:30,59,104`；`chunking.py:11,72` |
| 328 外语检索中文/标注集/非分数自动回复 | SDK真实Embedding接口存在，72条冻结查询/标签未改；本轮1.1全量产物未完成审核，不能认定达≥90% | `embedding.py:55`；`embedding_child.py:11`；`knowledge-eval/evaluate_retrieval.py:106` |
| 329 引用ID/标题/版本/片段/条件/案例非授权 | 返回正文前登记引用/衍生依赖，含原件页/章节/figure/profile/release；本期无交易写动作 | `references.py:11,20,35,42` |
| 330 Mock真实/历史截点隔离 | simulation/rag强过滤，history_replay必带时区时间；没有合法历史manifest则scope_unavailable | `retrieval.py:30,48`；`index_commands.py:41,55` |
| 331 页面维护/向量后台/不用SQL | 原维护入口与新构建/发布/整批切换/回滚/试查/下架均有实际API；GUI待验 | `F/components/knowledge/ReleaseActions.vue:160`；`ReleaseManager.vue:177`；`SearchPreview.vue:132` |
| 332 原件不可变/草稿失败不检索/显式发布 | reviewed门、worker只ready、发布另事务；profile/cache/manifest约束存在 | `build_checks.py:10,95`；`index_worker.py:98`；0005迁移:127 |
| 333 原子切换/失败保旧/回滚/CAS/晚到 | 完整manifest及CAS递增epoch；普通修订fence与撤销分离，已发布禁止原地重解析 | `releases.py:31,86,112`；`jobs.py:124,156`；`queue.py:80` |
| 334 下架/彻底删除区分/旧引用 | 本期下架撤销、旧任务/cache门及引用停用有实现；Agent在途提交Phase7、彻底删除Phase12 | `releases.py:130`；`references.py:50`；`ReleaseActions.vue:103` |
| 335 动作/操作者记录/保存不发布 | local_operator维护/核对/index/release审计；无客服回复自动升格知识 | `releases.py:73,106,125,147`；`builds.py:56` |
| 336 政策规则说明同版/修订重核/来源不提升 | 当前1.1完整说明与规则同源，旧1.0只读兼容并拒构建；新内容需解析/核对；动态待补 | `build_checks.py:47,95`；`policy_bundle.py:121`；`documents.py:134` |
| 337 配置/维度/摘要/复用/独立空间 | 1024独立profile、固定probe、完整输入+profile cache；replace_all必须全覆盖 | `index_profiles.py:8,24`；`index_worker.py:51,77`；`releases.py:99` |
| 338 PDF原件/页图/关键缺失门/不绕编辑源 | 重新读取实际原件/parser对象；核对排除与摘要绑定；位置随块，不能宣称全部图意理解 | `build_checks.py:19,33`；`chunking.py:135`；`B/knowledge/review.py` |
| 339 章节/版本SKU关系/不局部扩大 | 显式每块位置与SKU资格保留；先置前提独立变体PASS，但后置停止遗漏新增HIGH | `chunking.py:11,67,72,135`；`retrieval.py:59` |
| 340 模拟说明从rules生成/SIM部件 | 生产说明从实际同源JSON生成，动态数字来自规则；本期无创建部件/执行交易 | `policy_bundle.py:91,121`；`build_checks.py:47` |

| 其他源要求 | 实现及当前结论 | 位置/验证 |
|---|---|---|
| SCREEN-002/CMP-010–012 | 发布/内容分开；当前/历史构建及完整清单，试查实际条件/引用位置；真实视觉与全部交互未验 | `F/views/knowledge/index.vue:23,175`；`KnowledgeDetails.vue:89`；`ReleaseManager.vue:92`；`SearchPreview.vue:58` |
| 5.11加载/空/错误/成功/受限 | busy防重复、未知响应保存命令、请求条件快照/关闭晚到门；40项独立前端测试绿，真实错误UI待验 | `useKnowledgeIndex.ts:30,64`；`useKnowledgeSearch.ts:14,44`；`SearchPreview.vue:123` |
| 5.12写入约束/时间/纯文本 | UUID/枚举/strict CAS/extra forbid/时区；纯文本渲染 | `index_commands.py:14,41`；`F/api/mail-agent-request.ts:67` |
| 架构6.1–6.3短事务/租约/锁序 | 外部SDK不持事务；DBclock90秒/15秒心跳，写完guard后整笔回滚；slot→head→doc；源码存在 | `index_worker.py:43,67,96,107`；`jobs.py:43,91,170`；`releases.py:138` |
| 架构7.1不可变入库/发布 | profile/probe/parent/cache/release/item更新触发器，job默认parse；同版政策 | 0005:127,135；`build_checks.py:72,95` |
| 架构7.2预算/结构/快照/漂移 | 20候选/5文档/4500代理tokens；short2000/2500、long1000；前后head变化返回stale，无v4静默回退；后置必要停止丢失HIGH | `retrieval.py:88,94,109,116,123`；`index_profiles.py:8`；`chunking.py:72` |
| 架构7.3撤销/删除/恢复 | 下架门存在；物理purge及备份恢复演练未实现，不虚构已删除 | `releases.py:143`；`references.py:50`；DEV-PLAN Phase12 |
| 架构8持久化/API/scope FK | build/version/doc、父子块、profile/cache、release/items/ref均有scoped FK；独立迁移旧数据回归待验 | 0005:17,38,66,80,104,116；`B/adapters/knowledge_index_schema.py:109` |
| DEV-PLAN Phase6交付/四步验证 | 结构切分新增HIGH，独立PG、1.1实测结果审核与GUI未完成；不得凭已有编译绿认定完成 | `DEV-PLAN.md:139,152`；本报告证据 |

| AC | 本期层与尚未完成项 |
|---|---|
| AC-013/014/016 | 精确过滤/跨语言/用途隔离属于本期；独立实际1.1检索待验，不提前验整个历史Agent模型输入 |
| AC-015 | 最终Agent回复真实性Phase7；本期未实现 |
| AC-055/056/063 | 原件/页图/SKU结构门已有实现；本轮后置停止丢失HIGH，不能关闭AC-063 |
| AC-057/058 | 失败保旧、显式发布、同版政策和一致manifest路径存在；独立PG/GUI待验 |
| AC-059 | 检索/cache/晚到任务/旧引用资格属于本期；正式在途回复提交竞争Phase7补验 |
| AC-060 | 全删除/衍生正文清理/恢复防复活Phase12，未实现；不显示删除完成 |
| AC-061/062 | 输入复用/标题重算、完整同维模型切换及回退源码存在；独立动态待验 |
| AC-064 | 实际知识维护至发布/试查/下架GUI未完成，不关闭产品AC |

## 已跑准备证据：不构成Stage 2 PASS

以下在HIGH发现前执行，按事实保留。65个变更新增/修改源均≤300行，TS/Vue无any、v-html/innerHTML/eval或秘密前端变量；`F/../tsconfig.json:6`strict=true。安全匹配只包含固定migration表名、自有随机schema、测试假密钥/假VITE变量；没有生产秘密正文进入日志。[完整扫描](artifacts/phase6/review-closed-source-scan.json)及[脚本](artifacts/phase6/review-closed-source-scan.py)。因未进入Stage 2，不给综合安全/视觉通过结论。

独立仅做文件byte SHA核验，160份data/outputPDF与formal-before基线全部一致，用户settings字节一致；未连接正式DB。[脚本](artifacts/phase6/review-closed-preservation-check.py)、[结果](artifacts/phase6/review-closed-preservation-check.json)。没有把controller/完整场景/evaluation/业务holdout知识化。冻结旧60及新12查询仅读为验收预期，不作为知识输入。

命令与原始输出：

```powershell
# frontend
pnpm exec tsx --test scripts/*.test.ts
pnpm build
# backend：没有PGschema/真实供应商调用
$env:PYTHONPATH='src'
uv run --frozen python ../../docs/verification/artifacts/phase6/review-closed-policy-check.py
uv run --frozen python ../../docs/verification/artifacts/phase6/review-closed-chunking-variants.py
uv run --frozen python ../../docs/verification/artifacts/phase6/review-closed-stop-counterexample.py
uv run --frozen python -m unittest discover -s tests -p test_embedding_process.py -v
uv run --frozen python -m compileall -q src
uv pip check
```

```text
ℹ tests 40
ℹ pass 40
ℹ fail 0
ℹ skipped 0
ℹ duration_ms 2581.3481
$ vue-tsc --noEmit && vite build
✓ built in 26.86s
exit_code=0
Ran 8 tests in 1.677s
OK
compileall_exit=0
Checked 32 packages in 1ms
All installed packages are compatible
dependencies_exit=0
```

[前端40项原始日志](artifacts/phase6/review-closed-frontend-tests.txt)、[vue-tsc和build日志](artifacts/phase6/review-closed-build.txt)、[Embedding8项日志](artifacts/phase6/review-closed-embedding-tests.txt)、[编译/依赖输出](artifacts/phase6/review-closed-compile.txt)。Embedding测试实际启动自有子进程，覆盖超时、撤销/迟到、维度/有限值/归一化/漂移、超大/错误输出及环境秘密隔离；不调用供应商。协议`T/index_helpers.py:24`明确合成向量，不能证明相关性。

主Agent旧policy1.0完整72条实测结果原样保留`globalmail-agent/knowledge-eval/retrieval-results-policy-1.0.json`，其strict原句失败不被本轮纯函数结果覆盖。KQ041–044 frozen historical_eval输入由HTTP422拒绝，是输入契约拒绝，不是模型拒答。本报告没有将尚未完成的1.1重跑或主Agent全套测试当成独立PASS。

## 交接

Stage 1 FAIL，新增HIGH已即时报主Agent；Stage 2未执行。尚未取得PG或18181/15174浏览器窗口，未启动app/Playwright session，因此没有本轮实际页面明暗、窄屏、邻居或unknown-response截图，不能以组件复用数量替代这些证据。修复后保留本报告，重新从Stage 1执行独立审查，再补独立PG、真实检索完整正文与GUI。
