# Phase 6 第四轮独立审查

日期：2026-10-08。基线 `d0833a4`（Phase 5）。本期用户明确批准复用已结束的审查实例；本轮不是 fresh 实例。重新读取原文并从 Stage 1 开始，不修改产品、不提交、不再派生 Agent。三份历史 FAIL 原文与反例均保留：[初审](PHASE-6-REVIEW.md)、[第二轮](PHASE-6-REVIEW-FINAL.md)、[第三轮](PHASE-6-REVIEW-CLOSED.md)。

最终结论：**Stage 1 FAIL，Stage 2 未执行**。真实GUI发现1项HIGH：明确清空非必选资料B后，未知发布响应跨关闭重开会补回B，重试变成另一个body/key并实际意外发布B。另保留1项MEDIUM检索漏项KQ-058。独立27项PG、40项前端与编译全部绿，不能覆盖这个真实反例；Phase6尚未达到交付标准。

## 规划与范围

先重新读取 AGENTS、[code-review skill](../../.agents/skills/code-review/SKILL.md)、Product-Spec REQ-005/AC-013–016/055–064/SCREEN-002/CMP-010–012/5.11–5.12、AGENT-ARCHITECTURE §6–8、DEV-PLAN Phase 6、实施计划与文档索引；再重现历史反例、独立运行PG、审核实际返回全文、依[Playwright技能](C:/Users/82358/.codex/skills/playwright/SKILL.md)执行真实GUI，Stage 1 无HIGH后进入Stage 2。[本轮规划与逐步完成标准](artifacts/phase6/review-4-plan.md)。无设计稿或 Design-Brief，视觉基准为既有 Art Design Pro 工作台与系统页面。

仅交付当前知识入库、向量、发布、检索与下架层。正式Agent及未提交回复竞争属Phase7；完整删除、衍生正文清理和备份恢复属Phase12，均未完成。正式数据库/配置只读；测试仅随机schema/私有对象目录及主Agent隔离浏览器服务。原件/v1/v2/PDF不修改，不将controller、完整场景、保留评测及业务holdout知识化。

下文 `B` 表示 `globalmail-agent/backend/src/globalmail_agent/`，`F` 表示 `globalmail-agent/frontend/src/`，`T` 表示 `globalmail-agent/backend/tests/`，行号以本輪冻结代码为准。

## 阻塞问题 HIGH：清空候选跨关闭后补回，未知发布重试改变真实命令

对应原要求：Product-Spec:333“并发修改、重试和晚到任务不得覆盖较新发布”；5.11:593错误时保留用户文本；5.12:612防重复校验；Phase6实施计划HTTP约定明确“未知响应用同body/key”，页面整批发布须保留选择。

实际环境为全新隔离端口15176/API18186、schema `phase6_browser_d9a309ec0ed241f490b628821976e302`。独立审查者从0资料创建两个明确自编simulation/rag Markdown，A品牌OUTON/SKU H-CTD16-US-BK，B品牌OUTONLIFE/SKU F-SJ001-US-BK。两份均真实解析、人工核对及实际qwen构建；A分别500/300构建，先发布旧A500，B已构建但故意未发布。

1. 打开整批发布，A由默认最新A300改选旧A500 `cc468f18…`，使用真实清空图标清空非required B，页面确实显示“选择已完成构建”。
2. 真实POST先由 `page.route` 的 `route.fetch()` 提交成功，取得200及epoch2，再abort让页面丢失响应。页面显示“请求结果还未确认，请重试同一操作。输入已保留”；仅A生效，B未发布。
3. 关闭发布抽屉，再打开并展开整批发布。A500旧选择保留，**B自动补回默认合格构建 `d62f3ac3…`**。
4. 按同一“确认整批发布”重试，服务真实200，但命令变更、key变更、epoch变成3，清单从仅A变成B+A。B不是第一笔操作的授权选择。

| 真实请求 | body | 实际结果 |
|---|---|---|
| 第一次，成功后丢响应 | `{"expected_release_epoch":1,"build_ids":["cc468f18-d7a1-4f6d-bb65-c949d3b87e51"],"replace_all":true}` | 200，epoch2，仅A |
| 关闭重开后的“重试” | `{"expected_release_epoch":2,"build_ids":["d62f3ac3-2d7b-49a2-9e56-732b28972497","cc468f18-d7a1-4f6d-bb65-c949d3b87e51"],"replace_all":true}` | 200，epoch3，B+A |

`same_key=false`、`same_body=false`，两次完整真实请求/响应及key：[原始wire](artifacts/phase6/review-4-unknown-wire.json)。[第一次空B选择](artifacts/phase6/review-4-release-selection.png)、[未知响应提示](artifacts/phase6/review-4-unknown-first.png)、[重开后补回B](artifacts/phase6/review-4-unknown-reopened.png)、[第二次实际发布](artifacts/phase6/review-4-unintended-publication.png)；对应yml快照同名前缀均保留。已实际查看截图，空B与自动选回B均可直接辨认。

根因已只读确认：`F/components/knowledge/ReleaseManager.vue:45–47` 的ElSelect仅 `clearable`，未统一clear返回值；`:176` 只保留明确空串，`:181` 对undefined重新选默认，`:190–194` 关闭后reload触发此路径。本机已安装Element Plus `es/hooks/use-empty-values/index.mjs:9` 的clear默认值是undefined，`es/components/select/src/useSelect.mjs:367,374` 清空时emit该值；组件支持明确配置清空返回值，见[官方Select空值说明](https://element-plus.org/en-US/component/select.html#empty-values)。`ReleaseManager.vue:207–210` 重建body，`F/composables/useKnowledgeIndex.ts:66–67` 的命令身份包含build_ids，所以B补回后创建不同key。故障时源码独立保留：[ReleaseManager副本](artifacts/phase6/review-4-ReleaseManager-at-failure.txt)。

这不是未确认输入的纯显示问题，实际新增了一次完整发布并扩大了生效资料，因此等级为HIGH。发现后立即通知主Agent并停止Stage1后续流程、未执行Stage2。后续V4全覆盖切换/回滚、下架引用、明暗窄屏邻居对照均没有假PASS。

## Stage 1：历史问题与当前源码

| 历史问题 | 本轮独立证据 | 当前结论 |
|---|---|---|
| 前提按完整binding JSON相等，跨章节/依据不同丢警告 | `B/knowledge/chunking.py:11,72` 按各原块真实SKU资格联结，保留各自section/page/basis；A独有前提与A+B共享操作分别建立父证据，B不混入A警告 | 纯函数变体与PG通过；全文/位置而非关键词布尔：[变体](artifacts/phase6/review-4-chunking-variants.json)、`T/test_knowledge_index_structure.py` |
| 后置停止条件未传播到长操作 | `chunking.py:77` 从完整retained收集，排除自身group后按SKU分contexts；`index_profiles.py:8` 为structure/4 | 原生产JSONparser反例2个操作父块/5个输入全部包含后置停止条件，[实际输出](artifacts/phase6/review-4-stop-counterexample.json)；新合法controlled JSON→PG父/输入→发布试查用例通过，含集合非空断言 |
| policy1.0生成说明实质缺失明确接受/替代SKU选择/旧申请核验 | `B/knowledge/policy_bundle.py:53,91,121` 保持legacy render精确原文，1.1在对应章节完整补齐；`build_checks.py:47` 复算存储generator及整个bundle，1.0构建前409 | 实际v1/v2规则、可编辑数字及legacy AST原文独立通过；PG验证旧bundle可查看/零付费构建→同原件新版本真实parser→完整父/输入/manifest→旧记录严格不变；[事实核验](artifacts/phase6/review-4-policy-check.json)、[PG日志](artifacts/phase6/review-4-pg-tests.txt) |
| 发布状态筛选缺失/修订后旧发布遗漏 | `B/api/knowledge_documents.py:43` Literal枚举；`knowledge/release_queries.py:21` 当前head/ready/revocation关联；`knowledge/queries.py:41` | 独立实际HTTP published/unpublished/withdrawn，v2草稿保留v1已发布筛选通过；GUI待验 |
| 未知响应关闭后非默认选择或显式空B丢失 | 页面内存偏好保留了A旧构建，但 `ReleaseManager.vue:176` 未识别真实清空的undefined | 真实已提交但丢响应→关闭重开→B补回→第二笔真实发布，HIGH未关闭；详见原始wire与截图 |

## REQ-005逐条匹配

| 原文位置与要求 | 代码证据及本期实现 | 验证/边界 |
|---|---|---|
| Product-Spec:323，生产盘点白名单/先划分用途/不自动入库开发或保留参考 | `B/knowledge/prepared.py` 只导入rag白名单及实际原件；维护命令保存simulation/rag，不自动发布 | PG固定8份SOP/5份案例整篇原文完整；本轮160份源字节SHA一致；评测标签只用于评分，未进入production search或索引 |
| 324，五类售后资料/可读说明+可校验政策 | `policy_bundle.py:91,121`；`build_checks.py:47` 同版整bundle验证 | v1/v2真实JSON与动态数字、明确接受/币种/替代SKU/旧执行核验通过；正式执行授权沿Phase4程序规则，不以相似度授权 |
| 325，品牌来源版本型号时间/真实自编模拟区别/视频标题不造步骤 | `B/knowledge/documents.py`、`commands.py` 不变原件与来源字段；`references.py:20` 全部定位/适用字段；`retrieval.py:30` 用途门 | 精确过滤PG通过；GUI只自编模拟，不称厂家或生产准确率；正式Agent看视频声明未实现 |
| 326，每品牌代表产品族/七类业务/自编不冒充厂家 | 已有prepared清单沿Phase5；Phase6新增索引层，不新增厂家知识 | 实际评测22份当前白名单资料；业务覆盖不等于七类业务Agent完成 |
| 327，语义检索+精确品牌/SKU/type/跨品牌依据 | `retrieval.py:30,59,88,109` 先资格过滤再PG cosine，父块每个location独立验证 | PG错误SKU/品牌/type/mode/time及错误父展开均通过；真实模型检索待最终评测与GUI |
| 328，外语检索中文/已标注小集/不靠分数自动回复 | `embedding.py:44,55` 两个独立1024空间；`retrieval.py:88` 同profile查询；页面仅相关性 | 固定60+12实际返回全文待审核；无对话模型/正式Agent/邮箱调用 |
| 329，引用ID/title/version/片段/适用条件/经验不授权 | `references.py:11,20,42` 登记后暴露；`F/components/knowledge/SearchPreview.vue:75` 真实片段/引用资格/原件入口 | PG引用字段和停用门通过；GUI待验 |
| 330，Mock不可真实历史评测/历史时间 | `retrieval.py:30` 仅合法scope/mode/时间；无合法历史manifest返回scope_unavailable | PG调用供应商前资格过滤，边界无证据；旧historical_eval四条422明确为输入契约拒绝，非模型拒答 |
| 331，最小页面/本地上传修订PDF范围版本任务/后台向量 | Phase5维护入口保留；`ReleaseActions.vue:25,153` 业务选模型/切分构建，jobs原入口取消重试 | PG实际HTTP、真实parser、worker通过；完整页面操作待GUI |
| 332，原件/内容不可变/未核对不可检索/完整后显式发布/内容与配置分开 | 0005不可变trigger；`build_checks.py:10,19,95`；`builds.py:20` 新持久构建；`releases.py:86` | 独立PG未核对拒构建、GET无隐写、不可变input/profile/cache/跨scopeFK、当前发布不能原地重解析均通过 |
| 333，原子切换/失败保旧/合规回滚/并发重试晚到 | 后端CAS完整manifest、写后guard存在；前端输入身份仍有HIGH | 独立PG协议通过，但GUI未知发布重试扩大清单，整体不匹配 |
| 334，下架立即失效/旧引用停用/区别全删除 | `releases.py:130` revocation/fence并移除manifest；`references.py:42` 当前资格核验 | PG下架旧任务/cache/ref/rollback、其他原件坏仍可下架通过；正式回复提交竞争及全删除未实现 |
| 335，操作者/动作记录/保存不发布/Agent不自动知识化 | `releases.py:68` immutable operation actor/manifest；知识audit/持久jobs沿现有机制 | 每次回滚为新epoch，非改历史事件；无自动升格客服回复路径 |
| 336，政策规则说明同版/重新生成核对/正式真实依据/simulation不解标 | `build_checks.py:47,72` bundle rules/descriptionSHA+generator；`releases.py:46` 完整项 | PG政策manifest全hash一致/旧bundle不改、source/mode不可提升；policy1.1不意味着正式业务批准 |
| 337，解析切分模型维度输入摘要/仅变化重算/独立空间切换 | `index_profiles.py:8,24`；`index_worker.py:51,77` 内容寻址cache；`releases.py:99` replace_all须覆盖当前所有资料 | PG纯范围修订复用、标题变化重算、同维模型全切换/回滚通过；GUI待验 |
| 338，PDF原件/页图关联/关键缺失阻止/不绕编辑源 | `build_checks.py:19,33` 重验实际原件及parse对象；`chunking.py:135` 原块位置；review摘要/排除绑定 | parser独立4项实际像素crop、页/表头/缺失门通过；实际评测未覆盖图意块明确排除，不称图意全懂 |
| 339，明确version/section/SKU/有依据共享/不扩大 | `chunking.py:11,72,135` 各原块资格及位置；`retrieval.py:59` 展开再验 | 前后置A专属警告/共享操作分父、表格单位、错误SKU不展开通过 |
| 340，说明从规则生成/SIM部件不冒充 | `policy_bundle.py:91,121` 动态说明同源规则 | 独立实际v1/v2、41天/1750基点/9天变化核验通过；本期无部件创建或交易执行新增 |

## 架构、界面与AC范围

| 原文要求 | 代码/动态证据 | 当前判断 |
|---|---|---|
| ARCH6短事务/独立槽/DBclock租约/单调fence/晚到撤销 | `index_worker.py:67` 外部SDK不持事务；`knowledge/jobs.py:43,91,124,156` 90秒/15秒guard；PG取消/迟到/过期回滚/坏source释放槽 | 本期协议通过 |
| ARCH7.1完整manifest/probe/cache不可变/同版政策 | 0005:127,135 update triggers与scopedFK；`index_profiles.py:24` full config SHA；`index_worker.py:15` finite1024/unit+探针cosine≥.9995 | PG不可变/跨scope拒腐化、独立子进程8项通过；真实供应商结果待审核 |
| ARCH7.2短2000父/2500输入、长300/500目标/1000最大，总4500，20候选5证据 | `index_profiles.py:8` 代理估算明示ASCII1/其他2；`chunking.py:89,115` 完整短文/结构边界；`retrieval.py:88,94,109,123` | 本轮纯函数/PG通过；最终实际返回预算待核验，不能宣称供应商tokenizer一致 |
| ARCH7.3撤销/删除/恢复 | revocation门与新build显式恢复；Phase12 purge未实现 | 部分实现，明确范围，不伪装全删除 |
| ARCH8 schema/API/scope | 0005 version/doc/build/parent/cache/release/ref compositeFK；`index_commands.py:14,41` strict CAS/UUID/枚举/extra forbid | 0004旧资料与parse jobs迁移PG回归通过，正式迁移不在本轮审查内 |
| SCREEN-002/CMP-010–012 | 内容/发布状态分开；自编新建/核对/500与300构建/单资料发布实际完成 | 整批未知响应HIGH，其余UI未完成验证 |
| 5.11加载/空/错误/成功/受限 | busy及中文未知响应提示实际可见 | 提示宣称输入保留但B关闭后丢失，HIGH；不以40项绿关闭 |
| 5.12写入/时间/纯文本 | HTTP strict及CAS后端协议通过 | 前端明确空B变更导致body/key变化，实际防重复要求未满足 |

| AC | 当前Phase6层 | 尚未完成的全产品部分 |
|---|---|---|
| 013/014/016 | 精确过滤PG通过；真实72条审核完成，44/44单证据正例，16/16边界空 | 历史Agent模型输入全链路Phase7 |
| 015 | 不以知识试查证明看过视频/客户图像 | 最终Agent声明Phase7及REQ-014后续 |
| 055/056/063 | 原页/表头/范围/关键缺失门、前后置安全与SKU分父通过 | 图像所含全部操作含义不作承诺 |
| 057/058 | 新稿/失败保旧、完整显式发布与同版政策后端协议通过 | 整批发布未知重试存在HIGH，不关闭整个AC |
| 059 | 下架后检索/cache/迟到job/旧ref资格通过 | 正式在途回复提交竞争Phase7 |
| 060 | 下架与删除文案区分 | 彻底删除/衍生正文清理/恢复防复活Phase12 |
| 061/062 | 完整输入cache/标题重算/同维模型独立空间全切换协议通过 | 实际GUI两模型待验 |
| 064 | GUI新建/人工核对/实际qwen500与300/单资料发布已完成 | 明确空B未知发布重试HIGH；试查/下架/全覆盖模型切换后续未验 |

## 已完成的独立命令与原始输出

```powershell
# frontend
pnpm exec tsx --test scripts/*.test.ts
pnpm build
# backend
$env:PYTHONPATH='src'
uv run --frozen python ../../docs/verification/artifacts/phase6/review-4-pg-runner.py
uv run --frozen python -m unittest discover -s tests -p test_embedding_process.py -v
uv run --frozen python -m compileall -q src
uv pip check
# parser-worker
uv run --frozen python -m unittest discover -s tests -v
uv pip check
```

```text
ℹ tests 40
ℹ pass 40
ℹ fail 0
ℹ skipped 0
ℹ duration_ms 2504.5795
$ vue-tsc --noEmit && vite build
✓ built in 30.43s
exit_code=0
Ran 27 tests in 94.862s
OK
{"tests_run":27,"errors":0,"failures":0,"skipped":0,"actual_provider_calls":false}
Ran 8 tests in 1.636s
OK
compileall_exit=0
Checked 32 packages in 1ms
All installed packages are compatible
Ran 4 tests in 0.103s
OK
Checked 115 packages in 4ms
All installed packages are compatible
```

[前端日志](artifacts/phase6/review-4-frontend-tests.txt)、[vue-tsc/build](artifacts/phase6/review-4-build.txt)、[独立27项PG](artifacts/phase6/review-4-pg-tests.txt)、[Embedding子进程8项](artifacts/phase6/review-4-embedding-tests.txt)、[编译/32依赖](artifacts/phase6/review-4-compile.txt)、[parser4项/115依赖](artifacts/phase6/review-4-parser-tests.txt)。PG使用实际数据库、HTTP路由、真实local parser与worker；`T/index_helpers.py:18` 明确合成1024向量只证明协议，不能证明相关性。供应商实际运行来源另记。

独立PG进程明确exit0后释放窗口，fixture注册的随机schema/私有临时对象cleanup已完成，未启动正式app。[runner](artifacts/phase6/review-4-pg-runner.py)。160份源字节与用户settings SHA一致，仅hash文件、不连接正式DB：[核验](artifacts/phase6/review-4-preservation-check.json)。

## 实际模型评测独立审核及MEDIUM限制

实际运行由主Agent执行生产PreparedImport/local parser、structure/4+policy1.1、真实qwen1024与PG余弦，22份rag白名单原件，固定60旧+12新查询；不是本审查者又跑了一次模型。主Agentexec32101明确exit0，结果记录owned schema/对象清理。审查者独立按冻结标签对完整返回text重算，[只读审计脚本](artifacts/phase6/review-4-eval-audit.py)、[完整审计结果](artifacts/phase6/review-4-eval-audit.json)，与原结果所有evidence_at5零差异。

| 检查 | 原policy1.0历史结果 | 最终policy1.1+structure/4 |
|---|---|---|
| 44单证据正例 | 37/44 | 44/44 |
| 6多证据查询全部预期 | 3/6（9/12事实） | 5/6（11/12事实） |
| 16边界查询 | 16/16无证据 | 16/16无证据 |
| 6缺事实查询 | 返回相关资料 | 仍返回相关资料，不能证明最终拒答 |

两份结果的查询SHA均与freeze及当前原文件一致（旧60条 `6621dd696c3c7a89bd32044cd479c17dfc0a90a2dcf99a22ded2faae4fd5dad3`，新12条 `5006d918ee99ca261766057f1df1c9f419a70823eddeb66a2e150ced6dd1df73`）。最终72条候选均≤20、证据均≤5、父正文代理预算均≤4500，最高4457；不是供应商tokenizer计数。KQ-041–044 frozen historical_eval实际HTTP422，是输入契约拒绝，非模型拒答或成功历史检索。

独立阅读完整返回段落：KQ-056退货退款段明确具体金额/币种/客户明确同意，并明确问金额、不满、无回复不算接受；KQ-033/034/036换货补件段包含替代SKU明确选择+适配+人工、改方案先查旧执行/能否取消/是否产生补偿、避免两份补偿。修复后的真实返回包含这些事实，不再仅凭POL-SIM-V1标题判通过。

**MEDIUM：KQ-058多证据漏掉实际退货政策。** 虽返回POL-SIM-V1，但完整text只有“物流和人工”段，没有质量问题退货标签商家承担，也没有30天边界；SOP安全停止事实已返回。根因路径为 `B/knowledge/retrieval.py:109–116` 排序后每份文档只选一个父证据，当前选择了其他政策章节。这是实际缺失，不能以同义或标题命中改成PASS。相关开发集指标达到当前≥90%门槛，保留漏项；不声称查询全对、生产业务准确率或Agent可据此授权。全部返回text与原严格失败仍保留于 `globalmail-agent/knowledge-eval/retrieval-results.json`、`retrieval-results-policy-1.0.json`。

## GUI窗口与停止状态

首个15174/18181窗口被用户手动点击“导入准备资料”；主Agent已向用户确认来源，22份只创建在隔离schema。正式43表原行摘要、配置及160原件SHA全一致（[主Agent只读核验](artifacts/phase6/isolation-check.json)）。该窗口不算来源未明或产品隔离缺陷；保留中断截图与只读请求清单，不拿这22份作本审查者GUI产物。主Agent已清理旧harness并创建新15176/18186空库，审查者从零创建A/B。旧RuntimeStatus Phase5文案由主Agent先更新计划再修，最终新端口已实际渲染Phase6；主Agent更新后前端40/40（2384.5058ms）、build26.52s，来源明确不是本审查者独立再次编译。

新窗口中的A/B均实际POST202、真实parser→人工核对200，A500实际嵌入1片段，A300完整输入未变复用1向量，B500实际嵌入1片段；先单资料A500发布200，随后真实unknown-response反例。全部可见操作对应网络响应：[GUI wire](artifacts/phase6/review-4-gui-wire.json)、[初始创建/构建请求](artifacts/phase6/review-4-gui-initial-posts.json)。两份测试资料不代表业务资料准确率；本轮没有真实v4构建、试查、引用/下架、回滚或完整模型切换GUI通过证据。

发现HIGH后不修改产品、不回滚测试资料、不继续Stage2。自己的 `phase6-review-4` 浏览器session已经明确closed；两笔真实发布均结束200，三个构建均ready，我方无待运行模型请求。主Agent随后确认其自有harness15983已exit0，测试schema/对象/服务清理完成；未将其清理声明冒充本审查者独立数据库检查。

## Stage 2未执行与交接

本轮HIGH前的准备扫描：[source scan](artifacts/phase6/review-4-source-scan.json) 65个变更新增源均≤300行，TS/Vue无any/动态HTML执行/前端秘密变量；匹配项为固定migration表名、自有随机schema和明确测试假密钥。该准备结果不构成Stage2安全/质量/视觉PASS。真实明暗、宽窄与工作台/系统邻居视觉对比未执行；不以组件复用或本轮发布截图冒充完成。

主Agent应修复真实清空值与默认回填边界，补真实ElSelect清空/重开未知响应回归；保留本报告HIGH及原始wire，从Stage1重新审查。需要重新补全未完成的V4覆盖阻止→完整切换→回滚、当前v2草稿仍有v1候选、下架旧ref与回滚资格、试查空/错态及Stage2实际明暗窄屏邻居。不能以本轮27/40绿或最终44/44正例推翻该发布反例。
