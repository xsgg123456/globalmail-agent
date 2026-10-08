# Phase 5 实施计划与接口

日期：2026-10-08。依据：Product-Spec v1.13 REQ-005、CMP-010/011、主架构第6.2/7.1/8节和DEV-PLAN Phase 5。只交付原件、不可变版本、解析和人工核对；不实现向量、发布、检索、Agent或删除完成。

| 顺序 | 目标 | 完成标准 |
|---|---|---|
| 1 | 原件/版本与章节范围 | UUID对象、50MiB/300页限制、来源与用途锁定、不可变内容版本、明确SKU/章节绑定；资料/版本/审计同事务，重试不重复创建 |
| 2 | 独立解析进程 | 固定MinerU4.0.10 Basic/Standard、独立环境与本地模型；保留完整中间结构/表格/图片/一基页码/诊断，实际17页物理PDF只解析一次并投影8份逻辑资料 |
| 3 | 持久任务与核对 | 复用jobs及knowledge独立槽，15秒心跳/90秒租约、单调fence；15分钟终止本次进程树；可重建任务最多3次自动重试，取消/新版本/删除栅栏挡晚到；核对绑定原件/解析/适用摘要 |
| 4 | 维护页面 | 列表/筛选、上传/Markdown修订/PDF替换/政策结构编辑、原件与解析对照、章节SKU绑定、核对、差异、任务状态/失败重试/取消；沿用既有卡片/表单/抽屉与明暗主题 |
| 5 | 证据与交付 | 隔离PG→HTTP正反例、真实解析与页面完整流程、既有会话回归、构建/依赖与fresh两阶段审查通过；同步进度/交接、清理测试、中文提交 |

## 实现边界

- 默认workspace沿用已创建的本机workspace。共享知识对象使用服务器固定的knowledge scope，不伪造客户会话。适用范围/用途与正文分别版本化；普通修订不能解除simulation或提升来源可信度。当前准备包全部只允许simulation。
- 扩展既有jobs为知识版本任务；Agent任务仍要求conversation/run/cycle完整。保留旧协议测试的knowledge占位任务兼容，知识worker只领取真实knowledge_version_id任务，旧Agent租约恢复不处理新知识任务。不能创建虚假Conversation/AgentRun来塞入解析队列。
- 新迁移0004保留旧数据，建立documents/document_versions/applicabilities/blocks/knowledge_reviews/knowledge_audits/policy_bundles及按source_sha+parser_profile寻址的解析产物缓存。内容与绑定不可变；解析状态/代次/审阅记录可推进，修改正文/范围或重解析使核对失效。
- Markdown保留原文、标题/列表与层级，不解释HTML/脚本、不抓链接。JSON/JSONL只支持明确schema的知识资料/清单；拒绝完整场景、controller、evaluation及未复核客户原文。政策用结构化JSON校验并同次生成中文说明和摘要，金额/时间窗及证据kind不能以随意JSON绕开解释器。
- PDF按真实页数/格式检查，拒绝加密/损坏/超限及伪装扩展名。临时路径仅服务器生成。原件、完整原始中间结果、规范块、页预览及图片按对象登记依赖；不将base64、任意HTML、内部路径交给浏览器。
- ParserResult保留schema_version/source_sha256/full_document/page_count、含一基page/section_id/type/text/bbox/figure_id/table_rows的blocks、assets及diagnostics/parser/model版本；缺页、结构错误、关键资产缺失阻止核对。机器提取图片不等于已核对图片含义。可明确排除不完整块及其依赖并写原因，不能静默忽略。
- 核对要求已完成解析、明确章节/页区间与精确SKU绑定、原件与当前解析及适用摘要匹配；记录本机操作者、备注与排除项。仅到reviewed，仍未建立索引或发布，不能标为Agent可用。
- 准备资料导入仅消费documents.json允许的rag文档、products/families范围、SOP/案例/政策及受控PDF。保留原可用时间、source_hash/page_range，不读取authoring产品正文代替解析，不碰v1/v2原字节。共享PDF按摘要+解析档位复用完整物理解析，再按8份逻辑区间投影；逻辑范围不能跨品牌扩大。

## API与响应约定

沿用/api/v1 envelope和安全错误类别；所有写操作Idempotency-Key+expected_version（新建0，其余目标资源row_version）；未知结果重试原body/key，冲突保留输入并刷新，GET不排任务。全量正文用于业务/后续Agent；UI预览不改变服务产物。

- `POST /knowledge/uploads?filename=`：原始bytes流，最多50MiB；服务检查扩展名/实际内容/页数，返回`{object_id,sha256,size_bytes,format,page_count}`。相同key/body不重复对象；不接受路径/URL。
- `GET /knowledge/catalog`：`{products:[{sku,brand,name}],parser_profiles:[{id,label,available}]}`。SKU取现有精确目录；档位不可用如实显示，不静默换解析器。
- `GET /knowledge/documents`：type/brand/sku/status可选筛选、cursor分页，`{items,next_cursor}`；每项`{id,title,document_type,brand,source_kind,allowed_modes,usage_split,row_version,current_version_id,current_version_number,status,published:false}`。
- `POST /knowledge/documents`：`{expected_version:0,title,document_type,brand,source_reference,available_at,object_id?,content?,applicabilities:[]}`。类型`manual_pdf/troubleshooting_md/case_md/policy_json`；text新建可用content，上传可用object_id，不能二者同时。请求不能制造发布或可信来源。
- `GET /knowledge/documents/{id}`：`{document,versions,audits}`。
- `POST /knowledge/documents/{id}/versions`：`{expected_version,title?,object_id?,content?,parser_profile_id?,applicabilities:[]}`创建新不可变版本；元数据/适用变更也新建，保留旧版。
- `GET /knowledge/versions/{id}`：`{version,blocks,assets,diagnostics,applicabilities,review,jobs,source_url,source_text,policy?,diff}`；version含id/document_id/number/row_version/status/source_sha256/parser_profile_id/parse_generation/parse_sha256/applicability_sha256/page_range/available_at。diff与前版真实正文/范围差异，不伪造修改。
- `GET /knowledge/versions/{id}/source`：受scope检查的原文件，安全Content-Type/Disposition/no-store；`GET /knowledge/assets/{object_id}`只允许登记的知识资产，无任意路径和跨workspace读取。
- `POST /knowledge/versions/{id}/parse`：`{expected_version,parser_profile_id}`，返回`{document_id,version_id,job_id,version}`，202；重新解析递增代次且使旧核对失效。
- `POST /knowledge/versions/{id}/review`：`{expected_version,source_sha256,parse_sha256,applicability_sha256,note,excluded_block_ids:[],exclusion_reason?}`，记录明确人工核对；不接受界面伪造解析成功。关键缺失未解决则拒绝，保存不发布。
- `GET /jobs/{id}`：`{job}`包含id/kind/version_id/status/stage/row_version/attempt_no/error_code/retryable/parser_profile_id；`POST /jobs/{id}/retry|cancel`含`{expected_version}`返回相同动作结果。
- `POST /knowledge/prepared-import`：`{expected_version:0}`，只加载允许的已准备22份逻辑资料、复用同一原件，返回`{document_ids,version_ids,job_ids,version:1}`；不自动核对/发布。

applicabilities每项`{section_id,sku,page_start?,page_end?,basis}`，basis非空；`document`代表明确绑定整份，不作为跨品牌通配。PDF初始页区间来自上传整份或准备manifest，审核页面可明确排除块；新范围必须新版本，不能直接修改旧绑定。创建/修订PDF可传`page_range:[start,end]`明确资料投影范围；更换原件默认取新原件全部页码，沿用原件默认保留旧区间。范围不能超出当前原件，变更范围同步影响解析/适用摘要并撤销旧核对。准备资料替换为独立新PDF时同样重选范围，不沿用共享17页PDF的旧页号。

## 分工与验证

后端负责人拥有知识表/迁移、上传/CRUD/政策/核对/任务服务/API及数据库回归；解析负责人拥有parser-worker、ParserResult/进程适配和knowledge_runner及解析测试；前端负责人拥有knowledge页面、组件/API/composable及测试。主Agent拥有本计划/运行契约进度、main/settings/runtime/旧协议兼容集成、启动脚本、真实运行/GUI和审查收尾。各执行者fresh独立实例，只编码自检、不再spawn、不commit、不覆盖他人修改。

解析worker通过`KnowledgeJobService.claim(owner)`取得job（含version_id、source_sha256、object_id、parser_profile_id、parse_generation、slot_fence），`heartbeat(job,owner,fence)`续租；`complete(job,result,artifact_dir)`复核栅栏/摘要后保存完整物理缓存并按当前逻辑范围投影；`fail(job,error_code,retryable)`安排有限重试；`cached_result(job)`读取同source/profile已核验缓存。service在`knowledge/jobs.py`，runner在`worker/knowledge_runner.py`。profile使用`markdown/policy/mineru_basic/mineru_standard`，后两者15分钟限额且本地SDK与API环境隔离。

领取事务仅登记租约和运行状态，不在事务提交前读取原件。领取成功后先按登记的scope/字节数/SHA核验原件，再使用缓存或调用解析器。原件丢失/损坏必须进入持久失败与有限退避，释放知识槽让后续资料继续；缓存命中也不能绕过原件完整性。恢复原件后可重试，不能默默继续使用无法核对的缓存内容。

原件暂不可用时，版本详情仍返回任务、元数据和明确的阻断诊断，`source_available:false`、`source_text:null`，供维护者查看失败/取消/重试/替换；下载原件继续返回实际503。上一版原件不可用只阻止正文差异展示，不阻止维护当前新版本。人工核对提交再次核验原件，不允许用先前缓存的摘要绕过当前原件丢失或损坏。

受控结构知识原件：JSON 使用 `{schema_version:"globalmail.knowledge/1",document_type:"troubleshooting_md"|"case_md",blocks:[{section_id,type,text,table_rows?}]}`；JSONL 每行使用相同schema_version/document_type及一个section_id/type/text/table_rows块，同一文件类型必须一致。type仅heading/paragraph/list/table，校验器生成稳定块ID，不接受page、asset、bbox、URL、来源标签、用途或任意额外字段；原始完整字节保留，markdown profile直接读取结构。单文件最多10000块，无静默截断。普通JSON政策仍走同源规则语义校验；场景、controller、evaluation、故事及未复核客户原文没有允许schema。共享验证器`knowledge/json_structure.validate_knowledge_structure(content,format)`返回document_type与规范blocks，上传校验和独立解析进程复用。

官方用法核对：[MinerU固定4.0.10](https://github.com/opendatalab/MinerU/releases/tag/mineru-4.0.10-released)、[SDK](https://opendatalab.github.io/MinerU/usage/sdk_api/)、[输出契约](https://opendatalab.github.io/MinerU/reference/output_files/)、[固定许可](https://github.com/opendatalab/MinerU/blob/mineru-4.0.10-released/LICENSE.md)。保留固定版本许可及所用权重清单，外部模型/Embedding消费不属于本期。
