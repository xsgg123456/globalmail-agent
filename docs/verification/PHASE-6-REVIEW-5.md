# Phase 6 第五轮独立审查

日期：2026-10-08。基线 `d0833a4`（Phase 5）。**Stage 1 PASS，Stage 2 PASS，仅限 Phase 6 知识构建、发布、检索和下架层。** 本轮未发现 HIGH；保留 1 项 MEDIUM：KQ-058 多证据查询漏掉实际退货政策条件。正式 Agent、回复提交竞争、彻底删除及全部产品 AC 尚未验收。

用户明确批准本期复用已结束的审查实例，本轮不是 fresh 实例；未修改默认 AGENTS。审查者重新完整读取原文，从 Stage 1 开始，只审查、运行隔离验证和写证据，未修复产品、提交或再派生 Agent。四份历史 FAIL 原样保留：[第一轮](PHASE-6-REVIEW.md)、[第二轮](PHASE-6-REVIEW-FINAL.md)、[第三轮](PHASE-6-REVIEW-CLOSED.md)、[第四轮](PHASE-6-REVIEW-4.md)，不能用本轮绿结果改写其真实反例。

## 规划、输入与证据边界

执行前完整重读 AGENTS、[code-review skill](../../.agents/skills/code-review/SKILL.md)、Product-Spec REQ-005/AC-013–016/055–064/SCREEN-002/CMP-010–012/5.11–5.12、AGENT-ARCHITECTURE §6–8、DEV-PLAN Phase 6、[实施计划](../planning/PHASE-6-IMPLEMENTATION.md)、docs/README、当前验证及四份 FAIL；浏览器前读取 [Playwright skill](C:/Users/82358/.codex/skills/playwright/SKILL.md)。先写[本轮规划与每步完成标准](artifacts/phase6/review-5-plan.md)，再检查源码、历史反例、编译、实际返回全文、完整 GUI，Stage 1 无 HIGH 后进入 Stage 2。无设计稿和 Design-Brief，UI 基准为现有 Art Design Pro/Element Plus 工作台与系统状态页。

仅使用父 Agent 提供的全新独占测试 Web15177/API18187、schema `phase6_browser_10a2c00bd3e14d9996dcb362d03d2fb9`。初始页面为 0 资料，审查者自行通过页面建立 A/B；未导入 prepared、controller、完整场景、holdout 或评测答案。正式15173/18080未用于测试，本轮未连接正式数据库。之前15174测试库22份资料来源已由用户确认是其点击“导入准备资料”，不是产品自动 seed；父 Agent 已清理前两次 harness，并核验正式43表旧行、设置和160原件 SHA 未变，见 [isolation-check](artifacts/phase6/isolation-check.json)。

下文 `B` = `globalmail-agent/backend/src/globalmail_agent/`，`F` = `globalmail-agent/frontend/src/`，`T` = `globalmail-agent/backend/tests/`；行号以本轮冻结版本为准。[66份源码 SHA/行数](artifacts/phase6/review-5-source-scan.json)、[与第四轮版本差异](artifacts/phase6/review-5-source-version.json)证明生产后端、迁移、Embedding/parser/评测源码没有改变；差异仅 ReleaseManager 清空修复和结构测试非空断言。第四轮27项独立 PG 证据因此有明确版本适用性，但不是本轮重跑 PG。

## Stage 1：历史阻塞关闭

| 历史问题 | 本轮源码与实际证据 | 结论 |
|---|---|---|
| 前提按整个 binding JSON 相等，章节/依据差异丢失安全前提 | `B/knowledge/chunking.py:11,72,135` 按每原块实际 SKU 资格分组，各自 section/page/basis 保留；A 专属前提与 A+B 操作分父，B 不混 A 警告 | 匹配。第四轮纯函数变体、真实结构 parser→PG 父/输入→发布试查有版本适用性，见 [结构变体](artifacts/phase6/review-4-chunking-variants.json)、[独立PG](artifacts/phase6/review-4-pg-tests.txt) |
| 长操作遗漏后置停止条件 | `chunking.py:77` 从完整 retained 收集，排除自身 group，再按实际 SKU 资格选择完整安全段；`index_profiles.py:8` structure/4 | 匹配。[后置生产反例](artifacts/phase6/review-4-stop-counterexample.json)中操作父/全部输入均包含停止条件；真实 PG 用例含输入和证据非空断言，不能以空集合绿冒充 |
| policy1.0缺客户明确金额币种接受、替代SKU选择与旧执行核验 | `policy_bundle.py:53,91,121` legacy 原文不改，1.1在对应章节补完整事实且数字仍来自规则；`build_checks.py:47` 校验存储 generator/完整 bundle，legacy 构建前409 | 匹配。旧 bundle 可读/拒付费构建→同原件新版本真实 parser→父/输入/manifest→旧记录严格不变；[政策事实核验](artifacts/phase6/review-4-policy-check.json)、[独立PG](artifacts/phase6/review-4-pg-tests.txt)。本轮重审实际返回完整 text，未用标题命中替代事实 |
| 发布状态筛选、当前v2草稿漏历史v1合格构建 | `B/api/knowledge_documents.py:43` Literal；`knowledge/release_queries.py:21` 当前 head/ready/revocation；`F/composables/useReleaseManager.ts:20` 完整分页及全版本构建 | 匹配。GUI v2草稿仍显示v1候选和旧发布；下架/生效/未发布三种真实HTTP筛选分别1/1/0，见 [筛选原始响应](artifacts/phase6/review-5-publication-filters.json)、[历史构建](artifacts/phase6/review-5-historical-build.png) |
| 第四轮真实 clear 后B被补回，未知重试改变body/key并误发布B | `F/components/knowledge/ReleaseManager.vue:48` `value-on-clear=""`，`:177` 识别已有明确空值；`useKnowledgeIndex.ts:8,66` 模块级 PendingCommands 保留原命令 | **匹配，真实组件反例关闭**。下面两次已提交请求同body/key，epoch2/2、仅A，非手工把 selected 写成空串 |

## Stage 1：本轮真实页面全流程

材料为明确自编的 simulation/rag Markdown。A：OUTON / `H-CTD16-US-BK`；B：OUTONLIFE / `F-SJ001-US-BK`（品牌从 catalog 核对）。来源文案明确“项目自编模拟资料…不是厂家说明”，各自独立绑定 SKU。安全段“先断电，焦味立即停止转人工”，操作段“检查外部连接，不拆封闭控制器”，并有各型号独立步骤。两个原件正文、保存请求、所有完整响应保存在 [GUI原始wire](artifacts/phase6/review-5-gui-wire.json)。

| 真实页面动作 | 当场结果与代码证据 | 独立证据 |
|---|---|---|
| 空库新建A/B→保存→解析→人工核对 | 两份保存202、local parser任务完成、核对200；未发布时不进入检索。`F/components/knowledge/KnowledgeEditor.vue:267`/`KnowledgeReview.vue:95` 沿Phase5；`B/knowledge/build_checks.py:10,19` 核对与原件重验 | [空库](artifacts/phase6/review-5-empty.png)、[A/B流程脚本](artifacts/phase6/review-5-a-pipeline.js)、[B流程](artifacts/phase6/review-5-b-pipeline.js)、原始wire |
| A qwen500、A qwen300、B qwen500 | 3个ready构建；A300相同完整输入命中1份缓存；B合格但暂未发布。`builds.py:20` 持久build；`index_worker.py:51,77` 内容寻址cache/探针；`index_profiles.py:8,24` 全配置 | [A300发布流程](artifacts/phase6/review-5-a300-publish.js)、原始wire；A500 build `4320aa51-bbb1-4248-a093-c79c8a7a102d` |
| 先发布A，再整批选较早非默认A500，并使用B真实清空图标 | epoch1仅A；B真实 `.el-select__clear` 点击后显示“选择已完成构建”。未操作组件内部状态替代 clear 事件 | [真实选择](artifacts/phase6/review-5-release-selection.png)、[未知响应脚本](artifacts/phase6/review-5-unknown.js) |
| 发布POST真实200后abort响应→关闭抽屉→重开→同按钮重试 | 第一次后端epoch2仅A，前端显示中文结果未确认；重开保留A500/空B；第二次同key、同body，仍epoch2，仅A，无B和额外发布事件 | [两次完整wire](artifacts/phase6/review-5-unknown-wire.json)、[自动比较](artifacts/phase6/review-5-unknown-summary.json)、[重开实际字段](artifacts/phase6/review-5-reopened-fields.json)、[最终重试像素](artifacts/phase6/review-5-unknown-retry.png) |
| 显式发布B、实际德文A检索、引用资格、原件入口 | epoch3包含A+B；精确A查询只返回A、144代理tokens，完整安全/操作原文，引用GET eligible=true。原件/核对抽屉可打开且有实际下载链接；已发布v1重解析按钮禁用。`retrieval.py:30,59,88`、`references.py:11,42`、`KnowledgeDetails.vue:50` | [A实际证据](artifacts/phase6/review-5-qwen-search-a.png)、[原件对照](artifacts/phase6/review-5-source-compare.png)、原始wire |
| A V4构建→尝试整批切空间，B尚缺V4 | A V4 ready，页面明确还缺1份当前生效资料、确认按钮禁用，Qwen epoch3保留。`ReleaseManager.vue:143` 覆盖门；`B/knowledge/releases.py:99` 后端全覆盖 | [真实缺覆盖](artifacts/phase6/review-5-v4-missing-b.png)、原始wire |
| B V4构建→两份完整切换→实际英文B查询 | 两份V4 ready，整批发布200成为epoch4，两份同一V4空间；英文B真实200只返回B、完整安全/操作、160代理tokens，引用有效。总计5个ready构建，真实qwen/V4调用由隔离服务端凭据完成，浏览器没有Key | [V4切换](artifacts/phase6/review-5-v4-switch.png)、[V4实际B证据](artifacts/phase6/review-5-v4-search-b.png)、原始wire |
| 试查网络错误、恢复重试、历史无截点/合法截点无manifest | 人为abort请求时出现中文服务错误，旧证据清空、问题保留；解除abort后实际200。历史模式无时间禁用按钮，填时间后200 scope_unavailable/0候选/0证据。`useKnowledgeSearch.ts:14` 条件快照/关闭晚到门 | [错误](artifacts/phase6/review-5-search-error.png)、[加载](artifacts/phase6/review-5-search-loading.png)、[历史空](artifacts/phase6/review-5-search-history.png)、原始wire |
| 恢复旧Qwen清单 | 真实200新增epoch5、两份Qwen；不原地改epoch3历史。`releases.py:112` rollback完整重验再写新事件 | [回滚后](artifacts/phase6/review-5-rollback-qwen.png)、原始wire |
| A保存新v2草稿→候选/检索 | 保存202，当前内容v2 draft，v1仍发布；整批管理显示v1合格A300/A500历史候选。再次真实A查询只返回v1，没有未核对的追加草稿文本。`queries.py:41`、`build_checks.py:95` | [历史v1构建](artifacts/phase6/review-5-historical-build.png)、[v2草稿仍v1证据](artifacts/phase6/review-5-v2-draft-v1-evidence.png)、原始wire |
| A下架确认→旧ref检查→A检索→试恢复旧清单 | 下架200成为epoch6仅B；保留在另一页的旧A ref GET eligible=false/withdrawn；真实A查询无证据；恢复含A旧清单409 build_not_eligible，仍epoch6。`releases.py:130` revocation/fence；`references.py:42` | [下架实际wire](artifacts/phase6/review-5-withdraw-wire.json)、[旧引用失效](artifacts/phase6/review-5-old-reference-disabled.png)、[空检索](artifacts/phase6/review-5-withdraw-search-empty.png)、[旧回滚拒绝](artifacts/phase6/review-5-old-rollback-rejected.png) |
| 发布状态筛选 | withdrawn只A且v2 draft+下架标签；published只B且引用当前epoch6；unpublished空。解除筛选恢复两份列表 | [真实筛选响应](artifacts/phase6/review-5-publication-filters.json)、[已下架](artifacts/phase6/review-5-filter-withdrawn.png)、[生效](artifacts/phase6/review-5-filter-published.png)、[未发布空](artifacts/phase6/review-5-filter-unpublished.png) |

未知响应的两次实际请求均为：

```json
{"expected_release_epoch":1,"build_ids":["4320aa51-bbb1-4248-a093-c79c8a7a102d"],"replace_all":true}
```

原始比较：`same_key=true`，`same_body=true`，HTTP `[200,200]`，返回epoch `[2,2]`，清单项 `[1,1]`，唯一资料均A。第一次是 `route.fetch()` 已提交真实服务器再 `route.abort()` 丢响应；不是用mock成功结果假定提交。晚到/重试与输入保留已由实际wire关闭第四轮HIGH。

## Stage 1：REQ-005逐条原文匹配

| 原要求位置 | 代码证据 | 实际验证与范围判断 |
|---|---|---|
| Product-Spec:323 白名单盘点/用途先分/不自动入库开发或保留参考 | `B/knowledge/prepared.py:22,30` 只映射rag白名单实际原件；`documents.py:52,53` 固定simulation/rag，不自动发布 | 匹配。第四轮PG整篇8SOP/5案例完整，真实评测只22份rag；本轮GUI只自编A/B，标签只评分、不入模型 |
| 324 五类售后资料，政策可读说明+可校验结构 | `policy_bundle.py:91,121`，`build_checks.py:47` 全bundle同版复算 | 匹配。生产v1/v2、动态值、legacy拒构建/新版本核对及最终返回全文；执行资格仍由程序规则，不以知识相似度授权 |
| 325 品牌/来源/版本/型号/时间，自编与厂家区分，视频标题不造步骤 | `commands.py:13,29,46`、`documents.py:52,53` 强制来源/用途；`references.py:20` 定位与适用字段；`retrieval.py:30` 用途门 | 匹配本期资料/检索层。GUI明确自编，严格精确品牌SKU；视频、附件声明最终Agent层待Phase7 |
| 326 每品牌代表族/七类业务覆盖，自编不冒充厂家 | Phase5 prepared/catalog沿用，Phase6仅建索引与发布入口 | 匹配本期。22份真实准备资料的检索覆盖不等于七类业务Agent完成 |
| 327 语义检索+精确品牌/SKU/type/跨品牌依据 | `retrieval.py:30,59,88,109` 资格过滤先于PG余弦，父每个location再验 | 匹配。独立PG越界门、16条实际边界空、A/B真实不同SKU只返回各自证据 |
| 328 外语检索中文/标注小集/不靠分数自动回复 | `embedding.py:44,55` 两个独立1024空间；`retrieval.py:88` 查询与文档同profile | 匹配本期试查。44/44单证据正例、实际德文A/英文B；显示相关性不显示“回答正确”，无正式自动回复 |
| 329 引用ID/title/version/片段/条件，案例不授权 | `references.py:11,20,42` 注册后暴露并资格重验；`SearchPreview.vue:75` 原文/来源/引用/原件 | 匹配。实际引用有效→下架失效，完整安全原文可读；没有以案例证明交易执行 |
| 330 Mock不得真实历史评测，时间截点 | `retrieval.py:30` 合法scope/mode/time门，在付费检索前过滤 | 匹配本期。实际16边界空；historical_eval四条HTTP422属于契约拒绝，GUI历史合法模式无manifest明确空，不称历史业务评测完成 |
| 331 本地维护、修订/PDF范围、版本任务、后台向量 | `ReleaseActions.vue:25,153`，`knowledge/jobs.py:43`，Phase5编辑/原件入口保留 | 匹配。完整A/B页面动作实测，结构/parser原件PG覆盖；不得要求用户写SQL构建发布 |
| 332 原件内容不可变，未核对不可检索，完整后显式发布，配置分开 | 0005:127不可变trigger；`build_checks.py:10,19,95`；`builds.py:20` 独立持久build | 匹配。未核对拒构建/GET无隐写/跨scopeFK/不可变input-cache-profile；GUI5ready→显式发布，当前发布不可原地解析 |
| 333 原子切换、失败保旧、合规回滚、并发重试晚到 | `releases.py:31,46,68,99,112` 完整CAS manifest；`index_worker.py:107` 写后guard；`useKnowledgeIndex.ts:8,66` | 匹配。PG租约/fence/撤销/失败保旧，GUI缺B阻止、同key/body未知重试、两模型全切换、新epoch回滚 |
| 334 下架立即失效、旧引用停用、区别删除 | `releases.py:130` revocation/槽→head→doc锁及旧job取消；`references.py:42` | 匹配本期。实际下架/旧ref/旧rollback/空检索；正式在途回复提交竞争Phase7、全删除Phase12 |
| 335 操作者/操作记录、保存不发布、不自动知识化Agent回复 | `releases.py:68` 不可变actor/manifest/操作；持久jobs/audit沿用 | 匹配。新草稿保旧，GUI记录1–6可查，每次回滚新事件；不存在自动升格客服回复路径 |
| 336 政策规则/说明同版、重新生成核对、真实依据与simulation界限 | `build_checks.py:47,72` rules/descriptionSHA/generator；`releases.py:46` 完整bundle | 匹配。legacy原文/记录不改，新1.1同原件新版本才构建，不能借修复解除simulation标记 |
| 337 解析/切分/模型/维度/输入摘要，仅变化重算，独立空间 | `index_profiles.py:8,24`；`index_worker.py:51,77`；`releases.py:99` | 匹配。PG纯范围复用/标题重算、不可变probe/cache；GUI A300缓存、Qwen/V4分别构建完整切换，失败保旧 |
| 338 PDF原件/页图关联，缺关键内容阻止，不绕编辑源 | `build_checks.py:19,33` 原件/parse对象重读核验；`chunking.py:135` 位置及排除绑定 | 匹配本期结构层。独立parser4项实际crop/页/表头/缺失门和PG范围，不能宣称已理解所有图意；排除图意块不作为操作证据 |
| 339 version/section/SKU与有依据共享，不扩大章节 | `chunking.py:11,72,135` 各块原资格/位置；`retrieval.py:59` 展开再验 | 匹配。前/后置警告完整保留，不同SKU分父、表单位保留，错误SKU不展开 |
| 340 说明由规则生成，SIM部件不冒充 | `policy_bundle.py:91,121` 同源动态数字和事实生成 | 匹配本期。41天/1750基点/9天等动态值回归；无新增交易执行或正式部件事实 |

## Stage 1：架构、UI与验收条件

| 原文契约 | 代码/独立证据 | 判断 |
|---|---|---|
| ARCH §6 短事务、持久任务、独立槽、DBclock租约、fence/撤销 | `index_worker.py:67` 外部SDK不持事务；`jobs.py:43,91,124,156,170` claim/source分离、90秒租约/15秒heartbeat、guard及2/10/30退避 | 匹配。第四轮真实PG过期/取消/迟到写回rollback/坏source释放槽；本轮子进程超时杀自己的process通过 |
| ARCH §7.1 不可变manifest/profile/probe/input/cache、完整政策 | 0005:127,135；`index_profiles.py:24` 配置摘要；`index_worker.py:15,77` 1024 finite/unit与probe cosine≥.9995；`build_checks.py:47` | 匹配。不可变/跨scopePG及真实供应商ready元数据；坏/漂移不能静默合格 |
| ARCH §7.2 300/500结构切分，短2000父/2500输入，长1000上限，总4500/20候选/5父 | `index_profiles.py:8`；`chunking.py:89,115`；`retrieval.py:88,94,109,123` | 匹配。代理ASCII1/非ASCII2明确；实际72最高9候选/4父/4457，短文完整、长操作警告实际保留。不把300/500同结果称最优，也不称供应商tokenizer精确 |
| ARCH §7.3 下架、完整删除与恢复 | `releases.py:130` revocation；`references.py:42`；`build_checks.py:95`恢复资格 | 下架匹配；彻底删除/衍生清理/备份防复活待Phase12，不虚构删除按钮或完成状态 |
| ARCH §8 schema/API/迁移与scope | 0005 compositeFK绑定version/doc/build/parent/profile/cache/release/ref；`index_commands.py:14,41` strict CAS/UUID/枚举/extra forbid | 匹配。0004旧资料/parse jobs迁移回归有实际PG证据；正式升级后的保留核验由父Agent执行，不冒称本轮已升级 |
| SCREEN-002/CMP-010–012 | `views/knowledge/index.vue:23` 筛选；`KnowledgeDetails.vue:50`版本/核对/原件；`ReleaseManager.vue:48,177`；`SearchPreview.vue:75` | 匹配本期。实际上传/新建/修订/解析核对/构建发布/完整模型切换/回滚/试查/引用/下架；列表内容状态和发布状态分别呈现 |
| §5.11 默认/加载/空/错误/成功/受限 | `useKnowledgeSearch.ts:14` 快照/晚到门，index/ReleaseActions busy、中文unknown与错误 | 匹配。空库、loading、网络错误、缺历史manifest、缺覆盖禁用、成功及已发布重解析受限均有真实截图；未知输入跨关闭保留经wire验证 |
| §5.12 受控document、纯文本、带时区历史、request/expected版本 | `index_commands.py:14,41`、`retrieval.py:30`、`useKnowledgeIndex.ts:66`；显示原文使用纯文本 | 匹配知识层。非法mode/缺历史时间/旧CAS拒绝；前端生成key/expected字段，用户无需填写。邮件、业务单其他输入为既有/后续阶段，不以知识页验收代替 |

| AC | 当前Phase6层证据 | 未完成的全产品部分 |
|---|---|---|
| 013 | 精确SKU/品牌过滤PG、A/B实际查询及16边界空 | 正式Agent完整工具输入链Phase7 |
| 014 | 冻结德文查询实际中文片段前5命中、可打开原件；本轮德文A实际返回 | 不是生产业务准确率 |
| 015 | 视频目录/元数据不产生内容；本期不调用chat/vision | 最终回复不虚构读图/看视频Phase7及REQ-014后续 |
| 016 | simulation/rag保持标签，保留参考不入库，时间/模式门在检索前 | 真实历史Agent运行及完整模型输入链Phase7 |
| 055 | PDF页/表/资产定位、缺关键门、原件摘要重验；parser/PG证据 | 全部图片含义不能仅凭结构解析宣称通过 |
| 056 | 原块SKU前提分父、停用后新检索空、旧ref无效 | 正式Agent工具接入后补全链路 |
| 057 | v2草稿不进检索，v1仍服务；失败/任务入口可见，PG坏source有限重试 | 当前GUI自编MD未重复付费注入供应商异常，失败细节由子进程/PG用例证明 |
| 058 | 同一head一致查询、完整CAS切换、新事件回滚、政策全bundle同版 | 不把该AC数字与开发查询KQ-058混淆；KQ-058漏项仍记录 |
| 059 | 下架提交后cache/job/ref/回滚资格失效，GUI真实验证 | 在途正式回复提交竞争Phase7 |
| 060 | 准确下架状态且不冒充删除 | 彻底删除/衍生正文清理/恢复防复活Phase12 |
| 061 | input摘要/cache不可变，范围仅过滤复用、正文标题变动重算；A300实际cache | 非整包原件改写或重复生效块 |
| 062 | Qwen/V4独立1024空间、缺B拒换、完整切换、真实V4查询、回滚Qwen | 无自动静默降级模型 |
| 063 | 结构/警告/停止条件/单位/原位置与SKU联结PG/parser通过 | 图片语义未知时明确排除，不称全图意能力完成 |
| 064 | 全部本期页面动作无需SQL，当前/草稿/历史构建/操作记录/错误可见 | 彻底删除入口在Phase12开放；不关闭82项整体AC |

## Stage 2：类型、结构、安全与测试真实性

对本期66份新增/改变源文件逐一计数及摘要：全部≤300行，新增和改变源文件均无超限。TS strict启用（`frontend/tsconfig.json:6`），本期改变TS/Vue无`any`、动态HTML/eval；不把模板中未改的旧`any`说成全仓消失。[扫描脚本](artifacts/phase6/review-5-source-scan.py)、[完整结果](artifacts/phase6/review-5-source-scan.json)。

扫描14处候选均逐项看源：0005:133/134/154/155插值来自固定表名清单；migration tests:18/21、隔离harness:58/127来自其自建UUID schema，不接受用户SQL。test_api:15、test_embedding_process:19是明确假Key；Embedding/parser测试VITE变量用于证明子进程不继承秘密，不是前端生产配置。没有发现本期实际密钥硬编码、任意SQL/路径执行、VITE凭据或原始供应商错误泄露。

`B/knowledge/embedding_process.py:19,30` 子进程只获所需供应商配置，不继承DB/LLM/VITE秘密；45秒总界限/15秒heartbeat终止自己进程；`embedding_child.py:11`真实OpenAI SDK、1024维、timeout30/max_retries0、finite及模型核验，失败返回受控类别。`index_worker.py:67`不持事务调用供应商，`:107`写回后再次guard。原件/parse资产路径经scope+SHA检查，缓存不绕过缺原件。`scripts/phase3-test-server.py`随机schema/私有对象、localhost严格端口、前端剥离服务端模型配置，没有自动seed。

独立SHA核对160份v1/v2/PDF等源和settings均一致：[保存核验](artifacts/phase6/review-5-preservation-check.json)。受控authoring/story/controller/evaluation文件仅算字节SHA、不解释正文、不送入知识或模型；`production_database_accessed=false`。父Agent正式43表核对另有归属，不用本轮hash代替数据库保留验收。

| 本轮独立命令 | 原始结果 | 证据 |
|---|---|---|
| frontend `pnpm exec tsx --test scripts/*.test.ts` | 40/40，0fail/skip，2432.2885ms | [完整日志](artifacts/phase6/review-5-frontend-tests.txt) |
| frontend `pnpm build`（脚本先vue-tsc --noEmit） | typecheck通过，Vite27.21s，exit0 | [完整编译输出](artifacts/phase6/review-5-build.txt) |
| backend `uv run --frozen python -m unittest discover -s tests -p test_embedding_process.py -v` | 8项/1.599s，OK；实际独立child/超时/秘密边界，未调用付费模型 | [日志](artifacts/phase6/review-5-embedding-tests.txt) |
| backend `uv run --frozen python -m compileall -q src ../scripts ../knowledge-eval`；`uv pip check` | compileall exit0；32依赖兼容 | [日志](artifacts/phase6/review-5-compile.txt) |
| parser-worker `uv run --frozen python -m unittest discover -s tests -v`；`uv pip check` | 4项/0.109s，OK；115依赖兼容 | [日志](artifacts/phase6/review-5-parser-tests.txt) |

原始关键输出（不是根据父Agent声明推断）：

```text
ℹ tests 40
ℹ pass 40
ℹ fail 0
ℹ skipped 0
ℹ duration_ms 2432.2885
$ vue-tsc --noEmit && vite build
✓ built in 27.21s
Ran 8 tests in 1.599s
OK
Checked 32 packages in 1ms
All installed packages are compatible
Ran 4 tests in 0.109s
OK
Checked 115 packages in 4ms
All installed packages are compatible
```

版本适用而未在第五轮重跑的独立PG：第四轮27项94.862s，0fail/error/skip，fixture cleanup；[原始日志](artifacts/phase6/review-4-pg-tests.txt)、[runner](artifacts/phase6/review-4-pg-runner.py)。用真实PG、实际HTTP、local parser和thread worker；`T/index_helpers.py:18` ExplicitFakeGateway合成1024只验证协议，不证明语义相关性。最终全套158项284.276s/0skip及隔离脚本3项由父Agent执行，见 [backend-tests](artifacts/phase6/backend-tests.txt)、[local-script-tests](artifacts/phase6/local-script-tests.txt)，明确不是审查者独立重跑。纯绿测试不能推翻真实GUI或返回正文反例。

## Stage 2：真实视觉与邻居对照

在同一实际浏览器分别切换明/暗主题、1440×1000和900×1000，打开知识/工作台/系统状态三页；等待实际业务内容、路由动画结束及字体就绪后截图。审查者实际查看全部12张像素，未仅计组件。`window.innerWidth`/`scrollWidth`均为对应1440或900，字体同为模板ui-sans-serif；dark class仅实际暗主题出现。[明主题测量](artifacts/phase6/review-5-visual-light.json)、[暗主题测量](artifacts/phase6/review-5-visual-dark.json)、[PNG实际IHDR尺寸](artifacts/phase6/review-5-image-dimensions.json)。

| 实际主题/宽度 | 知识页 | 相邻工作台 | 相邻系统状态 |
|---|---|---|---|
| 明1440 | [像素](artifacts/phase6/review-5-knowledge-light-1440.png) | [像素](artifacts/phase6/review-5-workbench-light-1440.png) | [像素](artifacts/phase6/review-5-system-status-light-1440.png) |
| 明900 | [像素](artifacts/phase6/review-5-knowledge-light-900.png) | [像素](artifacts/phase6/review-5-workbench-light-900.png) | [像素](artifacts/phase6/review-5-system-status-light-900.png) |
| 暗1440 | [像素](artifacts/phase6/review-5-knowledge-dark-1440.png) | [像素](artifacts/phase6/review-5-workbench-dark-1440.png) | [像素](artifacts/phase6/review-5-system-status-dark-1440.png) |
| 暗900 | [像素](artifacts/phase6/review-5-knowledge-dark-900.png) | [像素](artifacts/phase6/review-5-workbench-dark-900.png) | [像素](artifacts/phase6/review-5-system-status-dark-900.png) |

卡片背景/边框、字号、主蓝按钮、状态Tag、页签及间距继承邻居；900筛选换行、侧栏响应收起，无body横向溢出，动作仍可见。`F/components/business/runtime-status.vue:48`实际显示Phase6知识发布检索、正式Agent尚未接入，与当前状态一致。

抽屉也实际看像素：[深色检索1440](artifacts/phase6/review-5-search-dark-1440.png)/[900](artifacts/phase6/review-5-search-dark-900.png)、[发布暗1440](artifacts/phase6/review-5-release-dark-1440.png)/[暗900](artifacts/phase6/review-5-release-dark-900.png)/[明900](artifacts/phase6/review-5-release-light-900.png)、[原件暗900](artifacts/phase6/review-5-source-dark-900.png)/[明900](artifacts/phase6/review-5-source-light-900.png)。900抽屉正文换行、选择和按钮可用；原件/核对纵向布局和可滚动发布记录无裁掉操作。初次暗发布900文件误仍1440，审查者发现并补拍，父Agent只读IHDR也指出；最终文件实测900×1000，dark width/scrollWidth=900，见 [测量](artifacts/phase6/review-5-drawer-dark-width.json)与[实际重拍日志](artifacts/phase6/review-5-release-dark-narrow-log.txt)。不以文件名代替尺寸，不把初次动画空页当最终渲染。

默认、空、加载、未知响应、真实网络错误、历史无manifest、成功、缺覆盖/已发布不可解析等状态在上文分别附真实截图。浏览器错误中人为abort和409属于已记录错误测试；初始远程Iconify加载连接关闭属于继承模板资源，最终截图图标已显示，没有本期未处理JS运行异常证据。

## 实际评测独立审计与保留的MEDIUM

父Agent实际运行 production PreparedImport/local parser、structure/4+policy1.1、真实qwen1024和PG余弦，22份rag白名单原件、固定60旧+12新查询，exec32101 exit0、owned schema/对象cleanup。不是本审查者又跑付费模型。本轮独立重读完整返回text并按冻结标签重新计算：[审计脚本](artifacts/phase6/review-5-eval-audit.py)、[完整输出](artifacts/phase6/review-5-eval-audit.json)、[最终原始结果](../../globalmail-agent/knowledge-eval/retrieval-results.json)。

| 固定查询分类 | 原policy1.0（失败保留） | 最终policy1.1+structure/4 |
|---|---|---|
| 44单证据正例 | 37/44 | 44/44 |
| 6多证据全部预期事实 | 3/6，9/12事实 | 5/6，11/12事实 |
| 16边界 | 16/16无证据 | 16/16无证据 |
| 6缺事实 | 返回相关资料 | 仍返回相关资料，不证明最终拒答 |

冻结字节/标签一致，72条重新计算与原evidence_at5零差异。旧60 SHA `6621dd696c3c7a89bd32044cd479c17dfc0a90a2dcf99a22ded2faae4fd5dad3`、新12 SHA `5006d918ee99ca261766057f1df1c9f419a70823eddeb66a2e150ced6dd1df73`。50正例中49完整，98%达到DEV-PLAN:152 ≥90%项目目标，但数据为开发小集且新增12作者已知资料，不是独立业务holdout/生产准确率。真实最大9候选/4父/4457代理tokens，全72符合20/5/4500；22真实build、27向量cache、build12936/query4830实际usage来自父Agent该次运行。旧policy1.0完整 [失败结果](../../globalmail-agent/knowledge-eval/retrieval-results-policy-1.0.json)保留，不用同义评分器或更改required_any翻成成功。

实际返回事实核验：KQ-056的退款段含具体金额/币种/客户明确同意，问金额/不满/无回复均不算接受；KQ-033/034/036含替代SKU客户选择+适配+人工，改方案先查旧申请执行/可否取消/是否已补偿，避免两份补偿。KQ-041–044 frozen historical_eval输入实际HTTP422，是合法契约拒绝，不称模型拒答或成功历史检索。

**MEDIUM KQ-058：多证据漏退货政策。** 原标签要求安全SOP及签收30天/质量退货标签等政策条件；实际返回安全SOP和POL-SIM-V1的物流章节，完整text不含预期退货事实。`B/knowledge/retrieval.py:109–116`每文档仅选一个父证据，不能把政策标题命中当事实成功。[审计结果](artifacts/phase6/review-5-eval-audit.json)保存required_any及所有返回全文；原标签未改。这是当前检索质量限制，剩余49/50达到已写目标，因此本轮不升级为阻塞HIGH；正式Agent遇缺事实仍需Phase7工具/拒答验收，不能据本期相关资料宣称已经正确退款/售后。

## 结束状态

Stage 1 功能/原文匹配与完整真实GUI通过；Stage 2 类型/文件大小/安全/编译/测试真实性及邻居明暗窄宽实际像素通过。没有因测试绿忽略历史反例，也没有关闭未开始的Phase7–13或整体82项AC。唯一保留问题为上述MEDIUM检索漏项。

审查者释放窗口后，父Agent确认harness62056 exit0、测试服务/schema/对象cleanup，随后正式本地0004→0005升级。审查者只读查看其[迁移保留证据](artifacts/phase6/formal-preservation.json)与[实际HTTP结果](artifacts/phase6/formal-http.json)：旧42业务表全部原列行摘要一致，settings/160源字节一致；旧22资料/22版本保留，index_builds/release/cache均0、head epoch0；API18080六项GET200、ready、runtime phase6/agent=false、两个profile可用，前端与代理也200。正式总表43→54均包含alembic_version，对应业务表42→53；不是把metadata53误记为总表或声称意外多表。正式升级及数据库读操作由父Agent执行，本审查者没有向正式库写入测试资料。

最后实际检索已200返回，五个构建均ready；没有审查者待运行请求或模型调用。自有 PlaywrightCLI `phase6-review-5`已关闭，两tab同关，CLI list原始输出为：

```text
Browser 'phase6-review-5' closed
  (no browsers)
```

[关闭确认](artifacts/phase6/review-5-browser-closed.txt)。已向父Agent释放GUI窗口，harness停止及测试schema/对象清理由其完成；审查者未停止共享正式服务、未删除旧目录或模型缓存。
