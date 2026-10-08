# Phase 6 实施计划与接口

日期：2026-10-08。基线：Phase 5 `d0833a4`。依据：Product-Spec v1.13 REQ-005/AC-013–016/055–064/CMP-010–011、DEV-PLAN Phase 6、AGENT-ARCHITECTURE 第6–8节。交付切分、向量构建、显式发布/回滚、检索试查和下架；不实现正式Agent或彻底删除。

| 顺序 | 目标 | 完成标准 |
|---|---|---|
| 1 | 结构切分和不可变索引配置 | 未核对资料不能构建；短SOP/案例保持完整，长文只在相同章节/适用范围切分，保留前提/停止条件/表头单位/原件位置；完整向量输入和配置决定复用 |
| 2 | 持久索引任务与真实Embedding | 新迁移0005不改旧原件，pgvector真实1024维；知识任务复用独立槽和fence；供应商调用在隔离子进程且不持数据库事务；批次有限重试、取消/超时/晚到不得完成旧构建 |
| 3 | 发布清单和引用资格 | 完整manifest、政策规则/说明同版、单scope单模型空间、CAS发布；失败保旧、回滚创建新事件；下架立即撤销资格且旧任务/缓存不能重新生效 |
| 4 | 检索与页面 | 先精确SKU/品牌/用途/时间/撤销过滤，再PG精确余弦；最多20候选、5父证据、约4500代理tokens；页面完成构建/发布/回滚/试查/下架，沿用现有组件主题 |
| 5 | 独立验证与交付 | PG→HTTP及真实worker/子进程正反例、60条既有开发查询和事前冻结补充查询、实际页面和明暗窄屏；四步验证和独立两阶段审查，正式升级只读核对旧数据后提交 |

## 分工与已有规则

- 后端核心worker负责0005迁移、新index schema、切分/profile/cache/build/release/retrieval/reference模块、新API、现有knowledge jobs/queue/queries及knowledge_runner集成与对应测试。
- 主Agent负责frontend知识相关API/类型/composable/组件/页面及前端测试，新增ReleaseActions/SearchPreview。创建页面worker因线程数量上限失败，改由主Agent直接执行。
- 主Agent同时负责Embedding适配与隔离子进程、依赖锁、settings/main/runtime、隔离运行入口、真实评测及文档。后端子Agent fresh上下文，不再spawn、不commit；各自自检，主Agent合并及独立review。
- 新审查实例创建被线程数量上限阻止；用户明确允许本期复用已结束的code-reviewer，重新完整读取Phase6原文与代码独立审查。只属本期例外，不修改AGENTS默认隔离规则，不称fresh实例。
- 正式数据库/用户配置不用于测试；独立schema和私有对象目录。v1/v2/原PDF字节、controller、完整场景、evaluation/业务holdout不作为知识输入或修改。
- 内容版本继续保存解析/核对状态；索引构建独立记录queued/indexing/ready/failed/cancelled及失败阶段，避免新构建失败破坏旧解析和已发布版本。页面同时显示内容与构建状态；没有以旧version status伪称索引已就绪。
- 普通修订的document_fence只阻止旧构建写入，不能使已发布旧内容立即不可用；单独记录撤销代次，发布项及引用用它判断当前资格。下架保留资料可维护，不显示彻底删除；下架前构建不可直接恢复，重新构建并显式发布才重新生效。
- 当前生效内容版本禁止原地重新解析；先保存新版本再解析，避免解析代次或核对摘要变化破坏旧发布。

## 数据与后台

0005新增immutable embedding profile/切分配置、父子chunk、内容寻址向量cache、index build及完整manifest、release/items/head、引用与模型探针基线；所有内容带已有共享knowledge scope，复合FK禁止跨scope。发布头唯一workspace+purpose；当前只有simulation/rag允许资料，没有合法历史清单时返回scope_unavailable。

jobs增加索引任务标识和build关联，旧任务默认parse；同一知识槽领取解析与索引，15秒心跳/90秒租约、数据库时钟及单调fence，最大三次2/10/30秒自动重试。领取先提交，读取坏原件/SDK错误后持久失败并释放槽。每批次写staging与最终ready前检查slot、job、内容核对、文档代次、原件/解析/适用摘要；提交后再查一次租约，失效则整笔回滚。不自动发布。

向量输入为标题+章节路径+必要前提/警告+完整块正文，不加入SKU列表或用途过滤字段。向量cache包含完整输入SHA和profile SHA。修改标题/正文重新算；纯适用修订可复用同向量，但生成新构建/发布。使用明确代理估算（ASCII字符1、其余字符2），记录方法，不宣称与供应商tokenizer相同；长文目标300/500、最大1000代理tokens，总检索上下文4500。固定准备SOP实测1255–1627、案例726–1171代理tokens；为满足原计划“短SOP/案例整篇单块”，同适用关系的短文阈值与父块上限取2000代理tokens，完整嵌入输入不超过2500。较长文仍按结构切分，不裁掉步骤或警告。

默认qwen3.7-text-embedding、1024维；保留text-embedding-v4独立可选配置，仅已完整构建并显式切换才能回退。profile记录北京配置ID/模型别名/修订未知/维度/输入格式/float32单位归一化/估算及切分配置，不保存秘密。固定探针作为每次实际调用的一部分，存首个合格基线并检查漂移；变化显式失败，不悄悄把相同维度当相同空间。

使用既定openai3.26.0、pgvector0.5.0，已核对[供应商官方接口](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api/)、[pgvector客户端](https://github.com/pgvector/pgvector-python)及PyPI固定版本。每批最多9正文+1固定探针，两模型统一限额10；SDK显式30秒timeout/max_retries=0，自动重试由持久任务负责。查询与文档同profile，服务失败、无证据、缺资料和发布变化分开。

主Agent提供`EmbeddingGateway(settings)`：

- `profiles()`返回安全配置列表，key为`qwen3.7-text-embedding`或`text-embedding-v4`，含label/provider/region/endpoint_config_id/model/dimensions/normalization/input_format/query_format/tokenizer/provider_weight_revision/available。
- `embed(profile, texts, *, current=None, stopped=None)`每次最多9条正文，返回`{vectors, probe_vector, usage, request_id, seconds}`。profile可包含`probe_vector`基线；无基线时返回首个探针供核心持久保存；有基线则校验漂移。返回有限1024维、float32单位向量。SDK异常为安全ServiceError，不泄漏响应/凭据。
- 索引worker传租约检查current/stopped；查询传发布头检查。孩子仅收到Embedding配置与必要凭据，不继承DB/LLM/VITE变量；不把凭据写文件，取消/超时只终止自有子进程树。
- `KnowledgeRunner(engine,store,workspace_id,embedding_gateway=None)`由main注入gateway；新API工厂`knowledge_releases_router(database,store,gateway)`、`knowledge_search_router(database,store,gateway)`由main挂载。

## HTTP和页面约定

沿用/api/v1 envelope；命令Idempotency-Key和目标资源版本/CAS，未知响应用同body/key。检索POST是只读试查，不创建后台任务；引用和内容依赖按确定ID去重登记。GET不创建任务或修改发布。

| 路径 | 请求/响应 |
|---|---|
| GET /knowledge/index-profiles | `{items:profiles[],chunkers:[{key,label,target_tokens,max_tokens}]}`，切分key `structure_v1_500`、`structure_v1_300` |
| POST /knowledge/versions/{id}/build | `{expected_version,embedding_profile_key,chunking_profile_key}`→202`{document_id,version_id,build_id,job_id,version}` |
| GET /knowledge/versions/{id}/index | `{builds:Build[],publication:Publication|null,document_row_version,revocation_epoch,withdrawn}` |
| GET /knowledge/releases | `{head:{release_id:null|UUID,epoch,embedding_profile_id:null|UUID},items:Release[]}`；Release含完整entries、profile、manifest SHA/有效时间/操作类型 |
| POST /knowledge/releases | `{expected_release_epoch,build_ids:UUID[],replace_all:false}`→`{head,release}`；普通发布合并其他现行项且必须同profile。换空间replace_all须覆盖所有仍生效资料，不能逐条混空间 |
| POST /knowledge/releases/{id}/rollback | `{expected_release_epoch}`→`{head,release}`；重新校验全部资格，生成新事件，拒绝已下架/不完整/不兼容旧构建 |
| POST /knowledge/documents/{id}/withdraw | `{expected_version,expected_release_epoch}`→`{head,document_id,document_row_version,revocation_epoch,withdrawn:true}`；确认下架，取消旧任务资格，更新清单和撤销代次 |
| POST /knowledge/search | `{query,sku,brand?,types?:[],mode:'simulation'|'history_replay',as_of?,expected_release_epoch?,release_id?}`→`{reason,head,candidate_count,evidence:EvidenceRef[],usage,diagnostics}` |
| GET /knowledge/references/{id} | `{reference,eligible,reason}`；旧引用下架标停用，不能从cache还原当前资格 |

`Build`含id/version_id/job_id/status/stage/row_version/profile_id/profile_key/chunker_key/chunk_count/embedded_count/cache_hits/usage/error_code/retryable/manifest_sha256、当前是否合格。任务取消/重试沿用/jobs/{id}/{cancel|retry}，索引任务不得清掉parse_sha或内容核对。

`EvidenceRef`含原架构全部来源定位/摘要/发布/索引字段与title/text/score、SKU适用和完整性；父块展开仍验证scope/章节/摘要/页区间。返回reason取ok/empty/scope_unavailable/incomplete_source/stale_release/provider_error，不将异常包装成确无资料。查询外部调用前后比较head，变化返回stale_release，不能内部切换模型混返回。

页面读取profile/build/release真实数据：核对后可构建；完成后待发布；显示当前生效版本和候选构建/差异/记录。发布/回滚/下架明确确认与影响范围，未知响应保留命令以同key重试。切换空间提供完整覆盖的候选清单，缺任何资料拒绝。试查必须明确SKU和用途，允许设置历史截点；未配置或provider失败显示原因，不造成功。

独立审查修正：必要前提按原块的实际SKU资格联结，不能因章节名或依据文字不同而遗漏；引用保留每个原块自身章节/页范围。不同SKU所需前提不同则分别建立父证据，禁止混入无资格警告。资料列表增加publication=published/unpublished/withdrawn精确筛选，与内容状态分开。
政策说明按政策章节/表格切分，完整规则和说明仍在同版发布bundle中。工程排障的跨段安全前提传播不套到政策的退款/库存等独立规则；不把整套政策重复塞进每个片段，不以检索代替规则核验。

## 证据边界

新增不参与调参的查询先冻结文本/预期资料，再实际运行。60条既有开发集保留原标签与失败，生产/未见资料精度不作承诺。测试含稿/失败/撤销/错误SKU/模式/时间、单位表头和父块范围、失败保旧、发布CAS竞争、相同维换模型、部分批失败、原件故障、取消/晚到/租约过期、回滚资格、下架缓存及引用门。运行中Agent回复竞争在Phase7接入后验证，完整删除在Phase12；本期不提前关闭82项AC。

实际评测发现旧政策标签引用原Markdown措辞，而Phase5正式政策资料使用同源JSON生成说明。保留原句匹配失败；另由独立审查核对返回正文是否实际包含相同事实，不修改冻结查询、不把同义核验冒充原句匹配通过。旧historical_eval模式由HTTP422拒绝，记为输入契约层的拒绝，不换成受支持模式重跑、也不计为模型拒答。

二轮独立审查发现现有政策说明实质遗漏明确接受退款金额/币种、替代SKU的客户选择与适配、改方案先查旧执行等条件。生成器升为knowledge-policy/1.1，在对应章节补齐规则事实；保留1.0渲染以核验旧不可变bundle，旧资料仍可查看，但不完整旧说明禁止构建/发布并明确提示保存新版本再解析核对。不迁移重写旧bundle、旧解析或原件。新版本携带新生成器和摘要；对应回归验证原件复用/旧记录未变/新说明完整及真实检索，历史FAIL保留。

三轮独立审查的后置停止条件反例：必要警告按完整已保留原文及原块SKU资格收集，不依赖出现在操作之前；前置与后置都进入操作父证据及嵌入输入，位置仍指向各自原章节。切分配置修订为structure/4；不同SKU前提继续分开，政策关闭工程警告传播的规则不变。增加真实parser→PG父块/输入→检索的后置警告用例，重跑全套及固定评测。

实际页面检查补正共享RuntimeStatus的静态Phase5说明，改为Phase6知识发布与检索、正式Agent尚未接入；与真实runtime phase6一致，避免发布后仍显示“资料尚未发布”。只改提示，不变更业务接口。新端口/空schema重新进行独占页面验收，前端全套/构建及独立审查重新核验。

第四轮真实GUI发现明确清空未发布候选后，Element Plus实际返回undefined，defaults只识别空字符串，重开时自动补回该资料，改变未知命令的body/key。按[官方Select清空值接口](https://element-plus.org/en-US/component/select.html#empty-values)显式指定空字符串，并在恢复选择时区分“没有选过”和“已明确清空”，兼容已有内存空值。保留第四轮FAIL/两次真实请求/意外发布证据；重新从Stage1审查并用真实组件清空、已提交丢响应、关闭重开、严格同body/key和发布头不增加验证，不以手工字符串测试替代真实清空事件。
