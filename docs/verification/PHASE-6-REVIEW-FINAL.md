# Phase 6 第二轮独立审查

日期：2026-10-08。基线：Phase 5 `d0833a4`；对象：本期未提交工作区。

**Stage 1：FAIL，新增HIGH 1项（政策可读依据缺关键明确同意条件）。Stage 2未执行；不构成本期PASS，不能据此进入正式升级。**

用户明确批准因线程数量上限复用已结束的code-reviewer。本轮重新读取AGENTS、code-review skill、Product-Spec REQ-005/知识AC/SCREEN-002/CMP-010–012/5.11–5.12、AGENT-ARCHITECTURE第6–8节、DEV-PLAN Phase6、实施计划和docs索引，重新从Stage1开始。**不是fresh实例**。只审查；未修复、未commit、未spawn。首轮[FAIL原文](PHASE-6-REVIEW.md)及其反例输出保留。

## 规划及完成标准

| 步骤 | 目标 | 完成标准 |
|---|---|---|
| 1 | 重建源要求和失败标准 | 逐条核对原文；HIGH即停止Stage2；不沿用Phase5或主Agent绿声明 |
| 2 | 重复生产反例与范围变体 | 原反例所有操作父块/嵌入输入带完整警告；共享操作按SKU前提分父；保留各原块章节/依据；短篇完整且满足2000/2500预算，长输入≤1000 |
| 3 | 独立协议/质量验证 | 实际PG→HTTP→真实parser子进程/worker；发布CAS/复用/撤销/晚到/政策同版；严格TS、≤300行、安全和编译 |
| 4 | 实际页面和检索 | 明暗/宽窄及邻居实图；错误、未知响应、历史候选、发布筛选；核查冻结60+12真实Embedding/PG结果和局限 |
| 5 | 记录最终结论 | 每项附代码行号、原始运行输出与截图；区分本期层和Phase7/12未完成项；保留历史失败 |

路径缩写：`B=globalmail-agent/backend/src/globalmail_agent`，`F=globalmail-agent/frontend/src`，`T=globalmail-agent/backend/tests`。引用行号按本轮工作区。

## 历史问题重验

| 首轮问题 | 二轮独立证据 | 当前结论 |
|---|---|---|
| HIGH 同SKU、不同章节/basis漏必要安全前提 | `B/knowledge/chunking.py:28,67,72,89`按原块SKU资格连接，整段及安全标题所辖块保留；原反例新输出2/2操作父、5/5输入均带警告。新增共享操作A+B、前提仅A变体中，4个操作父分别单SKU，B正文/输入无A警告；标题下非关键词段落、原章节/依据及短篇三章节全部保留 | 纯函数关闭；PG/检索重验待补 |
| MEDIUM 发布状态不能筛 | `B/knowledge/release_queries.py:21`关联当前head/ready/revocation；`queries.py:41`分published/unpublished/withdrawn，API Literal；`F/views/knowledge/index.vue:23`独立发布筛选及:133下架标签 | 源码关闭；HTTP/GUI待补 |
| 二轮MEDIUM 未确认提交关闭抽屉丢选择 | 重建ReleaseManager会默认覆盖非默认构建；第一次共享偏好补丁仍会把明确清空的非required B补回。主Agent新增`F/composables/knowledge-index-preferences.ts:1`共享内存偏好，`ReleaseManager.vue:172`保留合法旧选择及明确空值，`ReleaseActions.vue:127`按版本保留profile/chunker | 源码修正；真实丢响应→关闭重开→同body/key待补 |

[原反例二轮完整输出](artifacts/phase6/review-final-chunking-fixed.json)、[独立变体脚本](artifacts/phase6/review-final-chunking-variants.py)、[变体完整输出](artifacts/phase6/review-final-chunking-variants.json)。首轮false输出不覆盖。

政策JSON生成说明按独立条款结构切分，`build_checks.py:41`传`safety_context=False`；其完整规则/schema/生成器/说明摘要仍在`:90`重新校验，并由`releases.py:65`同版写manifest。它不将退款/库存等独立条款中的“安全”字段复制到每条输入；工程手册/SOP完整前提规则仍启用。本期需求仍要求同版政策及程序授权，未改成语义授权。

## Stage 1：逐条源需求匹配

以下为本期实现映射；发现新增HIGH后按skill停止，未提前勾选全部产品AC。

| REQ-005原文行 | 实现及边界 | 位置 |
|---|---|---|
| 323 新白名单/用途/未复核不自动入索引 | 固定prepared rag白名单；build必须核对；输入来自实际原件与parser产物 | `B/knowledge/prepared.py:17,30`；`build_checks.py:10,19,33` |
| 324 五类政策/程序条件/非相似度授权 | 部分实现：完整policy bundle同版，但当前prepared v1可读退款依据缺明确同意条件，新增HIGH；正式业务执行后续 | `build_checks.py:90`；`releases.py:65`；`policy_bundle.py:61,67` |
| 325 来源/品牌/版本/型号/时间/可信度 | manifest记录source_kind/allowed_modes/usage_split/时间；不读取视频 | `releases.py:56`；`references.py:20`；`retrieval.py:47` |
| 326 代表产品族/七类业务/自编非官方 | 保留22份prepared；当前simulation，不升级来源；七类Agent闭环不属本期 | `prepared.py:17,25`；`F/views/knowledge/index.vue:20` |
| 327 语义+精确品牌/SKU/资料类型/共享依据 | 先过滤精确登记品牌SKU及父块每个位置，再PG精确余弦；不推前缀兼容 | `retrieval.py:30,59,104`；`chunking.py:11,72` |
| 328 外语检索中文/标注集/非分数自动回复 | 真实Embedding接口与冻结60旧+12新查询；初轮运行至40，KQ030–036严格正文未命中，41非法历史mode导致脚本退出。结果保留，不能只按doc ID或改标签给PASS | `embedding_child.py:11`；`knowledge-eval/evaluate_retrieval.py:106`；初轮progress产物 |
| 329 引用ID/标题/版本/片段/条件/案例非授权 | 先登记证据正文依赖，含页/章节/figure/来源/范围/profile/发布代次；无业务写动作 | `references.py:11,20,35` |
| 330 Mock真实/历史截点隔离 | simulation/rag强过滤；as_of时区必填；缺合法历史manifest返回scope_unavailable，不退当前 | `retrieval.py:31,48`；`index_commands.py:55` |
| 331 页面维护/向量后台/不用SQL | 保留原件修订核对；新构建、发布、整批模型切换、回滚、试查、下架入口 | `F/components/knowledge/ReleaseActions.vue:160`；`ReleaseManager.vue:177`；`SearchPreview.vue:132` |
| 332 原件/不可变版本/显式发布/索引配置独立 | draft/failed/unreviewed无资格；worker只到ready，发布另事务；输入及manifest不可变 | `build_checks.py:10,76`；`index_worker.py:98`；0005迁移:127 |
| 333 原子切换/失败保旧/回滚/CAS/晚到 | 完整manifest+head CAS；新release递增epoch；revision fence与撤销代次分离；已发布禁止原地重解析 | `releases.py:31,86,112`；`jobs.py:124,156`；`queue.py:80` |
| 334 下架/彻底删除区分/新用阻断/旧引用 | 下架立即撤销、停止旧任务、旧引用停用；正式Agent在途提交Phase7、彻底删除Phase12 | `releases.py:130`；`references.py:50`；`ReleaseActions.vue:103` |
| 335 动作/操作者审计/保存不发布 | 本机local_operator，维护/核对/index/release审计；没有回复自动升格知识 | `releases.py:73,106,125,147`；`builds.py:56` |
| 336 政策规则说明同版/修订再核对/标签不提升 | 摘要/生成器/版本绑定有实现；可读说明遗漏核心条件，不能因重生成同一个不完整说明就认定语义一致 | `build_checks.py:90`；`releases.py:65`；`policy_bundle.py:61,67,73` |
| 337 配置/维度/完整输入摘要/复用/独立空间 | 1024维profile、固定probe、完整输入+profile cache；切换须覆盖全部生效doc且单profile | `index_profiles.py:8,24`；`index_worker.py:51,77`；`releases.py:99` |
| 338 PDF原件/页码图文/关键图缺失门/不绕编辑源 | 实际原件及解析对象重新核验；排除项绑定核对摘要；位置随块；本期不宣称理解全部图意 | `build_checks.py:19,33`；`chunking.py:135`；`B/knowledge/review.py` |
| 339 显式版本/章节SKU关系/不局部扩整文 | 保留每块原绑定及每位置；不同SKU前提分别parent；检索重新核验每位置资格 | `chunking.py:11,67,72,135`；`retrieval.py:59` |
| 340 模拟政策生成说明/SIM部件 | 说明从规则生成；本期未开放部件创建或执行 | `B/knowledge/policy_bundle.py:52`；`build_checks.py:90` |

| 其他源要求 | 匹配及未完成范围 | 位置/验证 |
|---|---|---|
| SCREEN-002/CMP-010–012 | 发布状态与内容状态分开；构建/生效/历史候选/完整清单；试查记录实际请求条件、原件/引用位置 | `F/views/knowledge/index.vue:23,175`；`KnowledgeDetails.vue:89`；`ReleaseManager.vue:92`；`SearchPreview.vue:58` |
| 5.11共用加载/空/错误/受限/成功 | 真实API空与provider错误不同；busy禁止重复；未知响应保原body/key；迟到结果不覆盖条件；实际GUI待补 | `useKnowledgeIndex.ts:30,64`；`useKnowledgeSearch.ts:14,44`；`SearchPreview.vue:123` |
| 5.12写入输入与历史时间 | 服务生成key/CAS；extra forbid/UUID/枚举/时区校验；纯文本渲染 | `index_commands.py:14,41`；`F/api/mail-agent-request.ts:67` |
| 架构6.1–6.3租约/短事务/锁序 | 外部SDK在事务外；DB时钟90秒、15秒心跳；staging和ready后二次guard；slot→head→doc锁序；正式Agent最终提交后续 | `index_worker.py:43,67,96,107`；`jobs.py:43,91,170`；`releases.py:138` |
| 架构7.1不可变构建/发布 | profile/probe/input/cache/releases不可变；政策同版；内容状态不被失败构建破坏 | 0005:127,135；`build_checks.py:53,76`；`index_worker.py:96` |
| 架构7.2预算/一致快照/漂移 | 最多20候选、5文档父证据、4500代理tokens；short2000/2500、long1000；head改变返回stale_release，无临时v4回退 | `retrieval.py:88,94,109,116,123`；`index_profiles.py:8`；`embedding.py:74` |
| 架构7.3撤销/删除/恢复 | 本期撤销及旧引用门；物理purge、备份恢复演练未实现 | `releases.py:143`；`references.py:50`；DEV-PLAN Phase12 |
| 架构8持久化/API/scoped FK | build/version/document、父子块、profile/cache、release/item/head/ref均有scope关系；0004旧数据默认parse | 0005:17,38,66,80,104,116；`B/adapters/knowledge_index_schema.py:109` |
| DEV-PLAN Phase6实施1–5 | 实现结构/后台/发布/检索路径；动态、真实评测、实际视觉与正式升级保护待补 | 本报告后续证据 |

| 产品AC | 本期验收层与保留项 |
|---|---|
| AC-013/014/016/030 | 精确过滤、跨语言检索、来源用途隔离和本期索引更新；实际动态待补；不提前验整个历史Agent模型输入 |
| AC-015 | 正式Agent回复真实性Phase7，本期未实现最终回复 |
| AC-055/056/063 | 原件定位、关键缺失门、结构/前提/单位/SKU范围；原反例已修，PG/实际引用待补 |
| AC-057/058 | draft/ready/发布分离、失败保旧、原子CAS、回滚源码路径存在；政策摘要同版但语义缺关键条件HIGH，动态未完成 |
| AC-059 | 本期检索/缓存/旧任务/旧引用撤销；在途正式Agent提交竞争Phase7补验 |
| AC-060 | 完整删除/衍生正文/恢复防复活Phase12，未实现且页面不显示删除完成 |
| AC-061/062 | 输入+profile复用、标题重新算、完整模型覆盖、失败保旧和回退；动态待补 |
| AC-064 | 页面维护至发布/试查/下架本期闭环；实际GUI待补 |

## HIGH：当前prepared v1可读政策丢失明确同意前提

源要求：Product-Spec.md:324要求政策同时具有可读说明及程序可校验条件，:336要求规则与说明同版，:340要求说明从规则生成；DEV-PLAN.md:153以政策说明/规则同版及关键证据Recall@5为本期门槛。冻结KQ-032和KQ-056明确检验“询问金额是否等于接受”，不是单纯命中政策标题。

实际：`data/knowledge/v1/policies/policy-profile.json:69`设置`partial_requires_explicit_amount_currency_acceptance=true`；受控原MD明确写出具体金额币种的明确同意后才提交，以及询问/不回复不算接受。`B/knowledge/prepared.py:37`实际导入规则JSON，再由`policy_bundle.py:52`生成可读说明。`:61`仅写“选择须来自可见客户消息；退款需明确金额和币种”；`:67`仅生成20%上限，**未生成对具体方案明确接受的必要前提**。查询金额这一可见消息不等价于接受退款；说明中没有这项区别。

`build_checks.py:90`校验的是从同一个render重生成的说明；因此当前原件/摘要/manifest检查会接受这份缺关键条件的说明。它不是向量排序或旧原句措辞差异，不能将“命中POL-SIM-V1”计成KQ-056的同意证据。`:73`的替代SKU也只有“交人工核对”，没有JSON要求的明确客户选择与兼容前提，需一并逐条对照生成器。

独立运行生产`parse_policy`读取受控v1/v2原件，经真实schema/语义校验后获得完整生产说明；**无PG、无模型、未修改原件**：[脚本](artifacts/phase6/review-final-policy-counterexample.py)、[完整原件SHA/生成器/说明/输出](artifacts/phase6/review-final-policy-counterexample.json)。原始关键结果（exit0）：

```json
[
  {
    "policy_version": "1.0.1",
    "partial_requires_explicit_amount_currency_acceptance": true,
    "description_explicit_consent_present": false,
    "description_question_is_not_consent_present": false,
    "description_sha256": "e874d434e8b8c0a2533b9842280f50f0c727120414c344fdd04bf907cad0f919"
  },
  {
    "policy_version": "2.0.0",
    "partial_requires_explicit_amount_currency_acceptance": true,
    "description_explicit_consent_present": true,
    "description_question_is_not_consent_present": false
  }
]
```

v2全文的逐项证据要求含“可见客户消息明确接受动作、数量；退款还须金额和币种”，所以不能把v2全篇误称完全没有明确接受。HIGH以当前实际prepared v1为主；需保证长政策返回的退款父块也携带必要条件，不能靠另一父块中尚未返回的说明补洞。

主Agent实际Embedding/PG初轮产物`knowledge-eval/retrieval-progress-initial.json`显示KQ030–036都有POL-SIM-V1候选但`evidence_at5=false`；本轮独立检查其生成说明。KQ-056尚未在这份初轮产物执行，报告没有冒称已实际跑该条。KQ030退货边界/邮资、031收件质检/申请非成功、034备用购买非免费、035轨迹/标签主体事实属于同义措辞；严格原句miss仍应保留。032/056明确接受与033替代SKU、036查原申请/已执行和方案冲突不能整体直接给“同义全覆盖”。

完成标准：生成器从规则完整表达涉及授权/金额/选择的关键前提，既有政策版本/生成器兼容与重新核对有明确处理，不能静默让已发布旧版本失效；对修复前缺失保留失败。冻结查询字节/原strict标签不改，严格指标保留；若另报人工事实同义覆盖，逐条展示实际返回正文和审核依据，并明确它是另一口径。修复后重新从Stage1审查。

## Stage 2未执行：发现HIGH前已有准备证据

以下命令在本轮新增HIGH发现前执行，只如实保留已有输出，**不给Stage2通过结论**。未取得独立PG或浏览器窗口，未启动app/Playwright session，未调用真实供应商。

逐文件预扫描63个变更源文件，新增和修改源均≤300行，当前最大KnowledgeDetails.vue 286行；TS/Vue没有any、v-html/innerHTML/eval或前端秘密环境变量。`F/../tsconfig.json:6`严格模式启用。[扫描脚本](artifacts/phase6/review-final-source-scan.py)和[全部路径/行数/分类命中](artifacts/phase6/review-final-source-scan.json)。

SQL插值命中逐个复核：0005:133/134/154/155均为源码固定表名；migration测试:18/21和隔离入口:58/127均为固定前缀+uuid4生成的自有schema，没有用户SQL输入。API/Embedding测试中的unit-test假密钥和VITE假变量用于证明隔离；没有生产秘密。`embedding_process.py:18,32`只传供应商凭据、隐藏孩子stdout/stderr，错误安全分类，取消/超时只终止自有进程树。原件/资产仍由scoped KnowledgeFiles逐次授权并no-store。

独立只读核验正式升级前基线的160个原件SHA，全部一致：[结果](artifacts/phase6/review-final-source-preservation.json)。未把controller/fullstories/evaluation/businessholdout正文用作知识；未修改正式DB或配置。实际SDK使用方式与[供应商官方同步接口](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api/)及[pgvector官方客户端](https://github.com/pgvector/pgvector-python)核对。

### 已跑命令和原始输出

```powershell
# frontend
pnpm exec tsx --test scripts/*.test.ts
pnpm build
# backend（不创建PGschema/不调用供应商）
$env:PYTHONPATH='src'
uv run --frozen python ../../docs/verification/artifacts/phase6/review-final-chunking-variants.py
uv run --frozen python -m unittest discover -s tests -p test_embedding_process.py -v
uv run --frozen python -m compileall -q src
uv pip check
```

独立原始输出：

```text
ℹ tests 40
ℹ pass 40
ℹ fail 0
ℹ skipped 0
ℹ duration_ms 2663.0046
✓ built in 1m 7s
build_exit=0
Ran 8 tests in 1.620s
OK
compileall_exit=0
Checked 32 packages in 1ms
All installed packages are compatible
dependency_exit=0
```

[偏好修复后独立40项原始日志](artifacts/phase6/review-final-frontend-tests-preferences.txt)、[偏好修复后构建完整日志（含vue-tsc）](artifacts/phase6/review-final-build-preferences.txt)、[Embedding八项原始日志](artifacts/phase6/review-final-embedding-tests.txt)。二轮第一次前端39项中1项文案regex不匹配，旧[38/39日志](artifacts/phase6/review-final-frontend-tests.txt)保留；主Agent修正regex为/未确认/并补历史候选后独立40/40。它是测试文字前提，不拿来掩盖产品行为。

Embedding8项实际启动自有子进程，覆盖超时、撤销/迟到、错误/超大输出、环境秘密隔离、维度/归一化/漂移；**不调用真实供应商**。核心IndexFixture明确合成1024维单位向量，用于真实PG/HTTP/worker协议，不证明模型相关性。prepared测试使用实际固定SOP/案例字节和真实本地parser孩子。

### 未执行及最终交接

独立PG、真实eval最终产物、真实GUI明暗/宽窄/邻居、unknown-response后相同body/key及模型完整候选实际交互均未完成。按code-review skill，Stage1有HIGH就停止Stage2。本轮以Stage1 FAIL返回；已跑前端/编译/子进程绿结果不能推翻可读政策缺关键依据的反例。修复后保留本报告，另建复审报告，从Stage1重新执行。
