# 技术选型与验证

版本：v1.3；日期：2026-10-07（北京时间）。当前阶段：选型与知识专项实测已形成，Agent 架构包含 Product-Spec v1.13 的客户图片能力；[DEV-PLAN v1.0](../../DEV-PLAN.md) Phase 1图片实验已实施、验收未通过，见[专项结果](../verification/VISUAL-VALIDATION.md)。技术验证不代表应用已经实现。

知识专项实测见 [KNOWLEDGE-VALIDATION.md](../verification/KNOWLEDGE-VALIDATION.md)：补充 MinerU 解析对照、60 条双模型开发查询和隔离 PG 生命周期契约。下面“实测结果”保留第一轮 tech-spike 原始证据，新选择不会改写旧模型的成绩。

## 本轮规划与完成标准

1. 核对已有决策和官方能力。完成标准：保留 Art Design Pro、Qwen3.7-Plus、PostgreSQL + pgvector；记录新增选择的依据与版本。
2. 建立隔离技术验证环境。完成标准：依赖可解析安装并生成锁文件；使用独立临时数据库，不触碰其他项目容器和生产数据。
3. 验证模型适配、PDF、Embedding、数据库检查点和观测 SDK。完成标准：保留可复跑脚本和结构化结果；明确实测边界，不将组件烟测写成 Agent 业务验收。
4. 汇总选型和剩余验证项。完成标准：每项注明已确认、实测采用或有条件采用，并列出架构设计需要落实的约束。

## 验证范围

只使用虚构邮件、已审读知识与本地产品资料。模型请求发送至已配置的百炼接口。技术验证脚本与依赖独立放在 `globalmail-agent/tech-spike/`，临时环境、向量缓存和页面渲染放 Git 忽略的 `tmp/tech-selection/`。

第一轮 PDF 基线为 pypdf 提取逐页文字、pypdfium2 渲染页面、现有 Qwen 模型按需理解图片。知识专项实验增加独立 MinerU 解析环境；页码、图片与 SKU 绑定需保留，图片解释不能用于猜测未核准的商品参数。

数据库主版本采用 PostgreSQL 18：官方当前稳定主版本为 18，支持至 2030 年；本项目尚无既有数据库需要迁移。此前 16 是推荐初值。验证使用本机已有 pgvector/pgvector 镜像的固定 digest，运行后记录实际 PostgreSQL/扩展版本；两次拉取 16 镜像遇 Docker Hub EOF 不作为数据库不兼容证据。

依赖验证发现 Langfuse 的 LangChain 回调会导入完整 `langchain` 包，只有 `langchain-core` / `langchain-openai` 不足，需要一并锁定。

本轮验证不实现售后应用，不建立正式知识索引，不运行真实业务履约。完整 Langfuse 服务部署、生产级并发/恢复和 Agent 七类业务验收在架构及开发阶段分别安排。

## 选型结论

| 层 | 选择与版本 | 理由 | 证据与边界 |
|---|---|---|---|
| 前端 | 现有 Art Design Pro；锁文件 Vue 3.5.22、Vite 7.1.7、TypeScript 5.6.3、Element Plus 2.11.4、Pinia 3.0.3 | 用户已指定，继续复用布局、组件与主题 | 本轮读取既有锁文件；未安装、构建或适配业务 |
| Python 环境 | Python 3.12.10、uv 0.12.2 | 现有环境可用，选定依赖支持 Python 3.12 | 隔离环境安装成功；`uv.lock` 固定完整依赖树 |
| HTTP/校验 | FastAPI 0.142.2、Pydantic 2.13.5、Uvicorn 0.54.0 | 统一 API、请求校验和 SSE 事件接口 | FastAPI TestClient 200；网络服务与 SSE 重连待实施 |
| Agent 编排 | LangGraph 1.2.14、checkpoint-postgres 3.1.2 | 用状态图管理运行，模型节点内保留自主工具循环 | PG 检查点可重连恢复；不将检查点等同业务事务 |
| 模型适配 | langchain-openai 1.6.7、langchain-core 1.6.7、langchain 1.4.3；传递依赖 openai 3.26.0 | 消息、工具、结构化输出和 Langfuse callback 同一套接口 | 百炼实际工具往返、流式工具参数合并、usage、原生 JSON Schema 已通过 |
| 主模型 | 沿用 qwen3.7-plus，北京接口 | 同一模型承担理解、决策、回复、受控知识读图及客户图片理解，不新增视觉 Agent | 显式 `enable_thinking=false`，Chat Completions 接口；客户图片专项已跑但有关键失败，不读取隐藏推理过程 |
| 业务数据库 | PostgreSQL 18.6、SQLAlchemy 2.1.3、Alembic 1.20.0、psycopg 3.3.6 | 本项目新建数据库，采用当前稳定主版本；事务和约束承载业务事实 | 独立临时容器连接与事务通过；Alembic 已安装，迁移尚未编写 |
| 向量检索 | pgvector 服务端 0.8.6、Python 客户端 0.5.0；精确余弦检索 | 现有资料量小，统一 PG；无需增加向量服务 | 使用实际模型向量在 PG 验证 24 条查询；镜像按 digest 固定 |
| Embedding | 推荐 qwen3.7-text-embedding，1024 维；text-embedding-v4 保留对照/回退配置 | 同一冻结开发集实接两模型，新模型首位证据排序更好；均需独立版本索引 | 60 条开发查询，完整短文正例 top1 为 29/36 对 18/36；小样本及调参结果不等于生产准确率 |
| PDF 解析 | 简单文本保留 pypdf 6.19.0 / pypdfium2 5.14.0；复杂/扫描 PDF 推荐独立 MinerU 4.0.10 Basic + DocVortex 0.5.9 | Basic 在本轮困难样本还原全部关键文字与表行；Standard 留作升级路径 | 17 页说明书及两份 4 页人工构造样本；不是所有图像操作含义已核准。MinerU 的 SDK 2.x 依赖与原主环境 SDK 3.x 分开 |
| 后台任务 | Agent/知识独立 Python worker + PostgreSQL 任务表；Agent 全局并发1、知识并发1 | 分离邮件处理与重型解析；任务与事件可同事务写入 | 架构已规定租约/fence与显式Agent恢复，尚未实现worker或重试执行器 |
| AI 观测 | Langfuse SDK 4.17.0 + 自托管服务路线 | 回调记录模型，手动 span 记录业务步骤；业务事实留在 PG | SDK 实测通过；完整服务、镜像组合、UI 和实际网络故障降级尚未部署验证 |
| 本地部署 | Docker Compose；前端和 Python 可宿主开发 | 业务数据库与观测基础设施隔离启动 | Docker 可用；本轮临时数据库已移除，未修改现有项目容器 |

首版不用七个业务 Agent 分工；沿用“单主 Agent + 受控业务工具”。是否拆能力须由后续业务评测证明需要。LangChain 安装只为消息/工具适配及观测依赖，不再叠加另一套 create_agent 状态机。

### 客户图片三项能力的选型增量

对应 Product-Spec v1.13 REQ-014：图片文字提取、可见产品异常理解、有依据的售后分流。Qwen3.7-Plus 北京接口官方支持图片输入和结构化输出，沿用现有模型适配器；能力表与单页产品资料烟测不证明客户缺陷识别、图文结构化联合请求或高密度截图字段准确率。[官方能力](https://help.aliyun.com/zh/model-studio/qwen3-7-plus)

- 首选图文联合Understanding，普通无图邮件沿用文本路径；OCR用于辅助读字的价值待实验决定，首版不新增默认OCR服务/第二模型，也不自动回退到其他供应商。MinerU继续解析受控知识PDF，不让客户故障照片绕入知识发布/向量化链。
- 接收JPEG/PNG/静态WebP以及有受控字节的CID图；仅图来信可处理，客户PDF/视频/音频仍按OUT-004未读取。每封4图/每张10MiB及20百万像素/合计20MiB、每轮6视图是应用初值，非供应商限额；图像预处理及预算适配需测清晰度、漏读和实际token消耗。
- 观察、原因推测、客户陈述、业务核验分开；图片证据经订单、适用SOP/政策和客户选择校验后才能支持业务动作。根因、责任、真实性和交易成功不能由VLM图片判断替代。
- Phase 1已冻结VIS-001至VIS-018分支及35个合成AI样本，完成图文联合Schema真实请求108次；独立语义审阅9次关键失败，人工标签待核对，不报生产准确率。正式隐私清理、并发、UI仍按Phase 8/12/13验证，不能用实验替代。
- 固定模型/Prompt/预处理配置与图片来源/摘要，仍消耗6请求/12工具/120秒以及16k输入/2k输出/80k总预算；final-v5单次最大输入3,258、输出1,197 tokens，仅证明本开发集受限视图用量，不能声称任意4张大图必定一次成功。真实未复核客户图片不出站。

### 已比较的替代方案

- 编排：纯 SDK 自写循环减少依赖，但检查点、运行状态和追踪需自己维护；当前业务有长期等待和人工接管，选 LangGraph。多 Agent 首版增加上下文移交和账本协调，暂不采用。
- 存储：独立向量数据库暂不解决本批规模的实际问题，且用户已确认 PG；先用精确检索。HNSW、reranker、关键词融合在评测出现明确缺口时单独加入。
- PDF：轻量解析在扫描与图片步骤上确有缺失；专项比较后复杂资料推荐 MinerU Basic。Standard 在本组样本未增加关键覆盖且更慢，Docling 保留备选但未安装横评。解析器必须可替换。
- 向量模型：第一轮用 v4；知识专项新增 qwen3.7-text-embedding 对照后推荐新模型。两者同为 1024 维仍不能混用，切换使用独立发布清单；新模型别名不等于已锁定供应商权重版本。

## 实测结果

### 模型与 PDF

- 原生 `json_schema + strict` 能提取订单、查物流诉求和条件退款，样例没有将条件诉求写成即刻退款授权。这是一个语义烟测，不是七类意图准确率。
- `ChatOpenAI.bind_tools` 在未强制指定工具的请求中选择查单工具；合并 19 个流式片段取得完整参数；工具结果回传后，回复区分创建面单与实际发货；两次请求均有 usage。
- pypdf 从交付 PDF 提取 17 页、8,716 个字符，找到全部 34 个 SKU 和 8 张嵌入图片；没有用编辑源替代 PDF。
- pypdfium2 渲染第 2 页后，Qwen 成功读取灯具类型和可见 SKU。只证明图片输入链路；尚未逐图验证描述准确度、图文切块或维修依据。

证据：[provider-results.json](../../globalmail-agent/tech-spike/provider-results.json)。

### 向量与检索

- 真实向量接口返回 1024 维；本轮 22 个中文逻辑文档 + 24 个查询生成 46 个向量，分 5 批请求，报告 11,513 embedding tokens。
- 不加 SKU 过滤时，16 个正例中首位命中 14 个；2 个德文问题把其他型号资料排在首位。这个结果直接支持“先限定适用范围，再排序”的方案。
- 按显式 SKU 绑定限定结果，16 个正例都有目标资料进入前 5，8 个未知 SKU 均为空；在 Python 基线和真实 pgvector SQL 中各验证 24/24。
- 这是整篇文档、小样本开发基线；候选范围很小，不能据此声称检索准确率 100%。正式切块、页图语义、模式/时间/split 过滤、停用更新和独立评测仍需实现。

### 检查点与交易

- SQLAlchemy/psycopg 与 PG 连接通过，pgvector 实际版本为 0.8.6。
- 模拟节点在业务行提交后抛错，关闭检查点连接，使用新 saver 和新图加载未完成节点；重放共尝试 2 次，唯一约束使业务行仍为 1 条。
- 该试验说明所选组件能支持幂等恢复模式；只重建连接，没有杀进程、模拟并发退款或实现实际售后状态机。
- 镜像固定为 `pgvector/pgvector@sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff`，运行报告记录 PG 18.6 / vector 0.8.6。当前官方仓库另有 vector 0.8.7，尚未纳入这次实测锁定组合。

证据：[database-results.json](../../globalmail-agent/tech-spike/database-results.json)。临时数据库使用内存卷，完成后容器自动移除；正式应用数据仍未导入。

### 观测

- 两个真实 Qwen 异步调用分别关联两个 root trace；模型回调和手动业务 span 均挂在正确的 root 下，共 6 spans、2 generations。
- 两次模型请求分别报告 69 tokens；回调记录对应模型名及用量。
- 导出层移除了测试属性中的虚构邮箱标记；合成 exporter 返回失败后，调用结果仍正常返回。
- exporter 使用本地内存收集，未发送 Langfuse Cloud，也没有启动自托管 Langfuse。测试不覆盖真实 HTTP 超时、服务入库/展示、队列饱和和完整隐私清洗。
- 失败导出用的是 FakeListChatModel，SDK 的“无法识别模型名”警告来自该合成步骤；真实 Qwen 的模型名和 usage 已记录。

证据：[observability-results.json](../../globalmail-agent/tech-spike/observability-results.json)。

### 探针可靠性复核

独立审查发现并已修复两个故障路径：容器清理异常跳过凭据删除，以及观测失败重跑保留旧绿色报告。所有探针的命令行入口现统一初始化报告并记录失败；容器与凭据清理分别尝试、分别报告。4 项离线故障回归通过，数据库探针修复后重新运行通过并移除临时资源。组件成功结果与故障回归分别计数，不增加业务验收完成项。

修复后独立复审 Stage 1 / Stage 2 均通过，无剩余 HIGH / MEDIUM；复审还独立注入 inspect 与 stop 失败，确认凭据删除、失败报告及退出码 1。归档见 `globalmail-agent/tech-spike/review-results.json`。

## 架构契约及后续实现约束

以下要求已映射至 [AGENT-ARCHITECTURE.md](../../AGENT-ARCHITECTURE.md) 和 [AGENT-ACCEPTANCE.md](../verification/AGENT-ACCEPTANCE.md)，设计完成不等于已通过应用验证。

1. 明确会话、一次运行和业务操作三个状态边界，以及各自数据库真相源。
2. 将 SKU/权限/模式/时间过滤放在知识服务端；未知型号不自动降级到相似型号步骤。
3. 所有写工具进入统一业务服务；幂等键之外还要验证同一事项、金额、数量、库存、地址版本与客户选择，不能把探针的唯一键示例照搬成完整防重方案。
4. 规定正常业务等待、整段人工接管和人工回复后待新来信的触发差异；等待时不持续调用模型。
5. 定义版本失效、停止、超时、检查点和账本部分成功的恢复行为；技术重试与业务自动恢复分开。
6. 定义 PDF 文本/图像处理状态、引用片段和知识更新失效，建立跨语言检索的正式验收。
7. 设计观测字段白名单、不可用时的行为及独立部署；Langfuse 服务镜像版本在完整部署验证后单独固定，不能用 SDK 版本代替服务版本。

后续按DEV-PLAN的阶段与验收实施。当前没有应用后端、正式运行数据库或可运行的售后Agent；本轮官方能力与固定版本元数据复核记录于开发计划，不改写上述实验结果。

## 官方依据与版本来源

核对日期均为 2026-10-07；Python 版本从 [PyPI JSON 元数据](https://pypi.org/pypi/langgraph/json) 及实际安装读取，完整解析结果在 `uv.lock`。

- [Qwen3.7-Plus 能力](https://help.aliyun.com/zh/model-studio/qwen3-7-plus)、[结构化输出](https://help.aliyun.com/zh/model-studio/qwen-structured-output)：北京接口的视觉、工具和 JSON Schema 能力；适配组合另由本项目实测。
- [向量同步 API](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api/)：模型维度和批大小；本轮使用 v4、1024 维、每批最多 10 条。
- [LangGraph 持久化](https://docs.langchain.com/oss/python/langgraph/persistence)、[PostgresSaver](https://reference.langchain.com/python/langgraph.checkpoint.postgres/PostgresSaver/setup)：检查点能力和初始化入口。
- [PostgreSQL 版本支持](https://www.postgresql.org/support/versioning/)、[pgvector](https://github.com/pgvector/pgvector)：稳定主版本、支持周期、向量能力和镜像发布。
- [pypdf 文本提取](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)、[pypdfium2](https://pypdfium2-team.github.io/pypdfium2/readme.html)：文本解析和页面渲染能力；单纯文本提取不能理解图片。
- [Langfuse 回调](https://langfuse.com/integrations/frameworks/langchain)、[导出过滤](https://langfuse.com/docs/observability/features/masking)、[自托管 Compose](https://langfuse.com/self-hosting/deployment/docker-compose)：SDK 接入、过滤范围与服务部署要求。
