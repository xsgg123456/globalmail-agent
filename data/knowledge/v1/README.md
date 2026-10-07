# 三品牌首批知识与业务资料 v1

版本：1.0.0；制作日期：2026-10-07。对应 Product-Spec v1.7、DATA-BUILD-PLAN。路线为 PostgreSQL + pgvector，本包是其前置数据，不是已建好的向量库。

连续业务资料补充：对应 Product-Spec v1.8。原 51 个环节样例之外，新增 **21 条完整往来（七类业务各一条主流程、两条分支）**，合计 72 个场景输入。新增故事中的邮件、地址和履约均为编写内容；商品身份与价格沿用已有原型。完整目录见 [连续售后流程](scenarios/journeys/README.md)。

**业务资料已按用户纠正重做。** 最终 PDF 使用 8 张生产订单关联的真实商品图；正文、SOP、案例卡和政策说明改为日常业务语言。技术字段保留在 JSON。客户来信中的内部测试编码已移除，51 份场景订单的单价全部取自同 SKU、同币种的生产快照原型；订单身份、库存、政策和后续事件仍是演练设定。

## 已交付

| 内容 | 数量 | 文件 |
|---|---:|---|
| 商品与产品族 | 34 SKU / 8 产品族 / 3 品牌 | products.json、families.json |
| 产品与售后参考资料册 | 17 页、8 张真实商品图 | ../../../output/pdf/product-manuals-v1.pdf |
| 排障 SOP | 8 份 | sop/ |
| 生产往来审读案例卡 | 5 份 | cases/CASE-001.md 至 CASE-005.md |
| 去标识的多轮摘要 | 5 条，每条带逐轮来源 | cases/reviewed-summaries.jsonl |
| 资料清单与明确适用关系 | 22 个逻辑文档 / 22 条绑定 | documents.json、knowledge-bindings.json |
| 模拟政策 | 1 套，三品牌、5 市场、2 渠道 | policies/policy-profile.json 与同源 MD |
| 模拟配件与兼容关系 | 53 部件 / 53 关系 | parts.json、compatibility.json |
| 模拟库存 | 34 整机 + 53 配件 | inventory.json |
| 开发场景输入 | 51 个 | scenarios/inputs.jsonl |
| 场景控制事件 | 48 行，含一次有意重放 | scenarios/controller-events.jsonl |
| 场景期望与禁止动作 | 51 组 | evaluation/scenario-assertions.jsonl |
| 英/德检索开发查询 | 16 正例 + 8 未知 SKU 例 | evaluation/retrieval-queries.jsonl |
| 视频候选目录 | 45 条 | video-directory.json |
| 连续售后流程 | 21 条：7 主流程 + 14 分支 | scenarios/journeys/inputs.jsonl、readable/ |
| 连续流程后续步骤 | 287 步 | scenarios/journeys/controller-events.jsonl |
| 连续流程客户来信 | 88 封，含首封与后续 | 初始输入及按序交付的客户事件 |
| 客服参考回复 | 50 段，仅供评测审阅 | evaluation/journey-assertions.jsonl |
| 寄回资料样本 | 11 份，包含重新签发版本 | scenarios/journeys/return-documents/ |

51 场景 = 三品牌各七类基础场景（21）+ SCN-001 至 SCN-030（30）。每个 SCN 目前选取一个具体分支作为 fixture，原场景中的其他并列变体可继续扩展；有静态输入不代表 Agent 已通过这些场景。

新增 21 条均描述到客户反馈及人工结案，覆盖退款方案被拒、支付失败对账重试、退货验收争议、附件打不开后重发、换货缺货、搬家重新确认地址、包裹误投、补件仍无效及发货前改退款。参考回复不是预填 Agent 输出，完整故事不进入 RAG。原 SCN-004 已改为先检查步骤适用证据，不再强制输出未经确认的配对方法；原退货授权占位指引已替换为具体寄回资料。

政策补丁版本 1.0.1 区分客户自付邮资与商家预付标签，原期限、20% 部分退款上限等数值不变。寄回 HTML 只供隔离演练审阅，地址/编号虚构，不是可实际寄件的承运商面单。

## 来源与真实性

本轮重新只读连接生产，取得当前商品目录与 44 个候选会话的 285 封非自动邮件。实际观察时间、源摘要和只读状态见 sources/capture.json、sources/product-snapshot.json；不是复用早期 90 会话探索包。

- **真实来源字段**：品牌、SKU、登记商品名称、登记站点、来源 ID；它们反映系统中的记录，不自动证明厂家技术规格。
- **项目模拟字段**：内部 SIM-V1 测试分支标识、53 个 SIM 配件及兼容关系、库存、政策数值和场景状态。它们不进入业务正文，不能当作真实厂家承诺。原技术稿的简图和编造按键规则已从最终资料移除。
- **真实商品图片与价格原型**：sources/production-product-images.json 记录本轮只读订单商品观察；product-photo-manifest.json 记录 8 张实物图的精确 SKU 来源、哈希与人工目视检查。同族其他 SKU 仅作外观参考。scenario-price-basis.json 记录每份模拟订单的同 SKU、同币种价格原型，不代表还原了真实税费折扣交易。
- **真实案例摘要**：审读消息后重新概括，逐条保留来源消息 ID、时间和原文本字段。客服回复中有历史 AI 清洗文本，客户附件和视频没有读取；只记录可观察陈述，未知结果保留未知。
- **视频目录**：均为 directory_only，未观看、未确认适用 SKU，不是知识步骤来源。

44 个来源候选先按稳定客户键、登记订单和首封近重复线索分组，再分为 29 个 rag_candidate、5 个 dev_candidate、10 个 eval_holdout。只审读用于 RAG 的候选，最终选入 5 个与初始 SKU 范围吻合的案例。另一个已审读滑板车案例不属于本批 34 SKU，未进入知识。分组是本批候选的准备结果，未复核的身份与近重复边界不宣称已完全消除泄漏。

原始邮件、原始身份与去标识密钥只保存在 Git 忽略的 `.local-data/knowledge-v1/`。自动清洗无法可靠识别所有自然语言姓名和地址，因此清洗副本也留在受控目录；本包只交付重新概括并检查过的摘要，不交付原文。公开分享前仍应移除内部来源 ID 并另行复核。

本批所有知识的 allowed_modes 均为 simulation。生产衍生案例并未变成模拟历史，但当前只在模拟系统中用作经验资料；不得与独立历史评测混用。

## 品牌、分类、SKU 与资料的关系

1. products.json 保存精确 SKU、品牌、产品族和 category_id。产品族是组织维度，不表示配件可以互换。
2. documents.json 描述文档版本、来源、用途、可用时间、物理路径及内容哈希。
3. knowledge-bindings.json 是知识适用范围的唯一入口，精确关联文档版本/章节与 SKU；政策另用品牌、市场、渠道、币种限制。
4. 同一 PDF 内有 8 个逻辑手册，各有自己的 page_range 和 section_id。第一页说明页不作为商品操作证据，不能将整个 PDF 的全部内容绑定给一个 SKU。
5. 每个模拟配件只有一条明确 SKU 兼容关系。现实中是否跨色、跨地区通用未知；这里保守分开，后续有依据再添加共享关系。
6. 分类、商品名称和向量相似度均不能覆盖明确的适用范围。policy_not_covered、unknown_compatibility 与技术查询失败分开表示。

路径均以本目录为基准，除非字段明确说明来源仓库相对路径。数据分工与后续加载约定见 [DATA-CONTRACT.md](DATA-CONTRACT.md)。

## 制作与后续入库边界

- 含图 PDF 是手册导入原件，authoring/product-content.json 是编辑源，不得用它替代 PDF 解析测试。
- assets/photos/ 保存实际生产订单商品图片，最终 PDF 只使用这些图片。旧的线条示意图不是交付资产。图片版权归原权利人，当前仅作内部资料参考；未据图推断尺寸、接线和兼容关系。
- SOP 与案例先核对适用范围和语义完整性：短文完整保留，长文才按章节/完整步骤切分并补齐前提和警告；片段继承对应范围和来源。当前策略见 [知识设计](../../../docs/architecture/KNOWLEDGE-DESIGN.md)，案例不能充当退款政策或执行回执。
- 政策 canonical 文件是 authoring/policy-profile.json；policies/ 内 JSON 是发布副本，MD 是同源生成的中文业务说明，不堆字段名。业务正文源为 authoring/business-copy.json，生成器在最终修订步骤覆盖技术初稿。
- scenarios/ 和 evaluation/ 不进入 RAG。控制事件、预期结果、fault injection 均由测试程序持有，不作为 Agent 邮件上下文。
- 订单、库存和履约状态由业务服务读取；不要将这些瞬时记录切块后作为“当前状态”检索。

## 重建与验证

脚本只使用 Python 标准库及 ReportLab、Pillow、pypdf；依赖本机 Codex 随附运行时，无新增后端依赖。

1. extract_sources.py 是显式生产只读刷新入口，会更新受控来源，不能当成普通离线重建命令运行。更换源批次必须重新审读并复核分组，不能沿用旧验收签名。
2. fetch_product_photos.py 是显式只读刷新商品图和价格原型入口；会下载真实商品图片，不是离线重建步骤。
3. 离线重建运行 tools/build_all.py：基础数据 → 场景结构 → 业务资料修订 → PDF 渲染 → 检查。不要只跑 build_materials.py 后交付中间技术稿。当前内部重建需要受控来源目录。
4. validate_materials.py 检查数据关系和生成逐页检查图；视觉检查签名绑定最终 PDF 哈希，内容改动后必须重做。整个离线构建不调用模型、生产或业务系统。

检查结果见 validation-report.json：40 项离线检查；最终 PDF 17 页已逐页查看渲染。已确认商品图来源、业务正文无测试术语、客户邮件无内部编码、数据关联等。这份资料制作报告不包含向量化、pgvector 检索、PDF 图片理解、Agent 场景回归或独立历史评测；后续组件实验另见下文，不改写原报告结论。

连续资料检查见 journey-validation-report.json：33 项离线检查及 8 项正反例测试，包含先验收后退款/换货、部分退款明确接受、地址版本和新版寄回附件关联。检查的是编写的数据，不是业务执行器、状态机或模型实测。可用现有 Python 环境依次运行 tools/complete_step_fixtures.py、tools/build_journeys.py、tools/validate_journeys.py、tools/test_journey_integrity.py，单独重建本次补充；完整重建仍用 tools/build_all.py。

## 后续实验进展与应用剩余工作

- 已完成 PDF/模型输入、Embedding 及原24条开发查询的组件验证，并扩展为60条双模型查询和临时PG生命周期实验，见 [技术选型](../../../docs/architecture/TECH-SELECTION.md) 与 [知识实测](../../../docs/verification/KNOWLEDGE-VALIDATION.md)。实验索引独立存在，不修改本包 prepared_not_indexed 状态，也不代表正式应用已入库。
- 按已确定的解析与切分方案实现正式入库、发布、更新和移除；使用未参与调参的新查询验收应用检索，不重复把已完成实验列为首次验证。
- 实现模拟业务适配器与场景控制台，先运行新增 21 条连续流程，再回归原 51 个环节样例；数据中的 gate 和事实前提须由执行器落实，不能只按顺序自动播放成功结果。
- 保留评测组尚未进行完整隐私复核和合理动作标注，不报告独立准确率。
- 商品真实额定参数、结构修订和视频适用性仍未知，本包的 SIM 设定不能覆盖这些未知事实。
