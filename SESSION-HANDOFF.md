# 新会话交接

更新：2026-10-07。当前阶段：前置资料完成，下一步制定开发计划。

## 当前目标与已确认范围

- 构建准生产智能邮件售后 Agent；先在隔离环境跑通业务，真实收发、财务和履约接入另定。不要重新降格为单场景 Demo。
- 三品牌：OUTON、OUTONLIFE 灯具；BELEEV 滑板车。首批 8 个产品系列、34 个 SKU。
- 七类业务：产品咨询、故障排查、物流查询、退款、退货、换货、补寄配件，全部属于首版。
- 同一发信人保留同一会话，内部按订单及售后事项分别跟踪。订单号用于查询准确 SKU，已有信息须复用。
- Agent 自主查资料、调用工具、补问、生成内部待办和自动模拟发送。人工负责具体业务履约，控制台推进模拟执行记录，Agent 查询并跟进。
- 无可靠依据或出现安全问题等情形触发人工接管；期间只记录新信息。人工回复后，下一封客户来信才自动恢复 Agent。最终结案由客服确认。
- PostgreSQL + pgvector 路线已定；主 Agent、LangGraph、确定性业务服务、持久化任务、Langfuse 为推荐架构。不要重新发起 Neo4j 选型讨论。
- 主模型使用 qwen3.7-plus，连接与工具调用已做过验证；真实 Key 只在被 Git 忽略的本地 .env 中。Embedding 尚未实测。
- 前端基于用户指定的 D:/Work_Project/art-design-pro 副本，位于 globalmail-agent/frontend/；沿用现成组件与工程，不能回到旧邮件工作台风格。
- Git 提交标题和正文使用中文。作者：张帅，823585487@qq.com。

## 已交付的数据

入口：data/knowledge/v1/README.md。

- 22 个逻辑知识文档：8 份产品资料（合在 17 页 PDF 中）、8 篇排障说明、5 篇真实往来案例、1 份政策说明。
- 8 张真实商品照片，34 个 SKU，53 个模拟配件及适配关系，87 条库存；政策 JSON 与中文说明同源，当前政策补丁版本 1.0.1。
- 原 51 个环节样例、48 行控制事件、24 条检索问题保留。
- 新增 21 条完整流程（每类 1 主流程 + 2 分支），287 个后续步骤，88 封客户来信，50 段仅供评测的参考回复，11 份本地寄回资料。总共 72 个场景输入。
- 连续流程目录：data/knowledge/v1/scenarios/journeys/README.md；人工可读案例在 readable/，初始输入和未来事件分开，评测答案在 evaluation/。
- 退款失败对账、客户拒绝方案、退货验收争议、附件重发、缺货、地址变化、误投、补件仍无效、改退款、人工接管恢复和结案已有连续数据。

## 数据的重要边界

- 用户允许虚构，但必须贴近日常跨境售后。业务正文用自然语言，内部测试字段与客户往来分开。
- 商品身份、商品图和价格原型来自生产只读资料；新增往来、地址、政策、库存和执行记录为编写内容，不冒充真实履约。
- 44 个真实来源会话、285 封邮件保存在被忽略的 .local-data/knowledge-v1/；仅 5 个审读案例进入知识资料。未经复核的正文和独立评测组不进入 RAG。
- 45 条 YouTube 链接只是目录，未观看、未建立已验证 SKU 适用关系。未知参数和维修步骤继续保留未知。
- 只有知识正文计划做 Embedding。商品映射、订单、库存、执行记录与政策资格通过数据库/业务工具读取；完整演练故事、参考回复和未来事件不能入 RAG 或提前给 Agent 看。
- 寄回 HTML 是可审阅的虚构资料，不是承运商可实际扫描使用的标签。

## 验证与未实现部分

- 原资料 40 项检查、新增连续资料 33 项检查、8 项正反例测试通过。
- 独立审查通过，文件哈希及结论见 data/knowledge/v1/sources/journey-review.json。
- 新增资料离线重建结果一致；PDF 未在连续流程补齐时更改。
- 尚无 DEV-PLAN.md；尚未实现业务后端、知识入库器、Embedding/pgvector 检索、Agent 业务执行或前端业务适配。
- 静态检查通过不代表模型、业务状态机或真实系统通过。后续必须执行真实模型调用和逐轮业务测试。

## 新会话推荐顺序

1. 读取 Product-Spec.md v1.8、BACKEND-ARCHITECTURE.md、BUSINESS-SCENARIOS.md。
2. 读取资料 README、DATA-CONTRACT.md 和连续流程目录；无需重做业务访谈或重新造同一批数据。
3. 使用 dev-planner 制定 DEV-PLAN.md，覆盖数据库与导入、RAG、业务服务及事件控制、Agent/人工接管、前端与 Langfuse、场景验收。
4. 接入时验证依赖和模型接口，再按计划开发。不要将作者脚本里的参考回复作为 Agent 的真实输出。

单独重建新增数据可依次运行：

```powershell
python -X utf8 data/knowledge/v1/tools/complete_step_fixtures.py
python -X utf8 data/knowledge/v1/tools/build_journeys.py
python -X utf8 data/knowledge/v1/tools/validate_journeys.py
python -X utf8 data/knowledge/v1/tools/test_journey_integrity.py
```

完整资料重建入口是 tools/build_all.py，需本机受控来源目录及 PDF 依赖。该入口不会连接生产；extract_sources.py / fetch_product_photos.py 则是显式生产/来源刷新入口，不要混用。
