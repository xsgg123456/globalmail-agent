# Phase 8 第六轮独立审查

审查日期：2026-10-09。审查角色：fresh code-reviewer。基线：`09a818fa9976c94e5c50a090620993b324b603ea`（main/HEAD），审查工作树增量与新增文件，未提交代码。

**结论：Stage 1 的本期核心工程未发现 HIGH；新增 1 项 MEDIUM，邮件时间线缺少已提交图片的缩略图，UI 为部分实现。本轮依技能的“有 HIGH 才停止”规则执行了 Stage 2，修前快照的质量、安全、测试真实性及实际邻居视觉对照通过。整体仍需补齐该 UI 缺口并另派 fresh 审查，不宣告 Phase 8 最终闭合。**

主 Agent 在发现后修改了 `frontend/src/api/attachment-api.ts` 和 `frontend/src/components/mail-agent/MessageTimeline.vue`。本报告保留修前结论，不为这两个文件的后续补丁背书。结束邻居对照时浏览器 HMR 已显示新图片元素；该观察不作为修复通过证据。

## 输入、执行边界与快照

已读取 AGENTS.md、`.agents/skills/code-review/SKILL.md`、`.codex/agents/code-reviewer.toml`、根目录 Product-Spec/AGENT-ARCHITECTURE/DEV-PLAN，docs/README、PHASE-8-IMPLEMENTATION、SESSION-HANDOFF，以及前五轮报告原文。REQ-014 的 12 项 MUST 与 AC-065–082 按原文分别映射如下，未用前轮摘要代替要求。

范围包括后端 attachments/agent/adapters/api/application/worker/observability 的变更、0007 migration 与新增测试，前端附件契约/API、工作台组件/composable/runtime 与脚本测试、隔离测试服务。新表/API/组件属于 REQ-014 与架构 4.4 的实施范围，未发现额外页面、共享图像 RAG、远程图片抓取、真实邮箱投递或额外模型 Agent 等范围漂移（`main.py` 的路由装配、`api/attachments.py:17`、`api/visual_evidence.py:15`、`adapters/attachment_schema.py:8`）。

独立 runner 用 `agent-eval/bootstrap.isolated_database_environment()` 注入隔离数据库环境，fixture 创建随机 schema、临时对象目录并清理；没有升级或写入正式数据库。真实 UI 使用主 Agent 所有的 18181/15174 隔离服务，无 worker、无模型配置。风险复验用新 TestClient/fixture 加载最新源码，未用早于风险修复启动的 UI API 证明风险逻辑。仅使用合成图片/身份，0 付费模型调用。

源码审计 [JSON](artifacts/phase8/review6/phase8-review6-audit.json) 保留基线、84 个变更/新增源码、测试及提示文件的 SHA/行数。关键修前快照：

| 文件（路径均相对项目根） | SHA-256 | 行数 |
|---|---|---:|
| `globalmail-agent/backend/src/globalmail_agent/application/risk_records.py` | `a9855997e54cf0244fcb9e7c9d3e54699f7cbeaa03fe0e703c3be768155ed3eb` | 48 |
| `globalmail-agent/frontend/src/api/attachment-api.ts` | `7c73af38d716724f591acf2e240ea57cbfaeeac1508a4fa20804f389ee8a56eb` | 20 |
| `globalmail-agent/frontend/src/components/mail-agent/MessageTimeline.vue` | `152bedc55b61517a5d908c854240bb1e1126be8e3b2ce19e1361e4e28da42230` | 90 |
| `globalmail-agent/frontend/src/components/mail-agent/ImageEvidenceDrawer.vue` | `8c35d545e6964623a62a27cdb4309328c770f5454dc1f4e7b7ea7dfce4840a65` | 119 |

前端独立构建日志最后写入 10:28:05，扫描快照 10:29:21，两个后续 UI 文件写入 10:31:19；本轮前端验证属于修前版本。后端独立 42 项与新增 1 项反例均记录 `source_changed=false`。

用户已明确先开发全项目再统一优化模型细节（`Product-Spec.md` 开头、`AGENT-ARCHITECTURE.md:5`、`DEV-PLAN.md` 开头及 Phase 8）；本轮工程通过不等于视觉模型准确率或整产品验收通过。Phase 1/7 原语义 FAIL 保留；AC-082 未执行、延期，不能标 PASS。AC-069/071 的内部售后写归 Phase 9，AC-078 完整物理清理与备份恢复归 Phase 12，均未完成；不豁免本期立即撤销、来源、权限、预算、晚到和 HITL 屏障。

## Stage 1：新增 MEDIUM

### M1：已提交图片的时间线没有缩略图

- 需求原文：`Product-Spec.md:573` CMP-002 要求中间邮件区“图片缩略图与逐图处理/未读取状态”。
- 修前实现：`globalmail-agent/frontend/src/components/mail-agent/MessageTimeline.vue:31` 起仅以文件名和状态按钮展示附件，没有 `ElImage`/`img`。上传草稿区 `ImageUpload.vue:8` 的缩略图在提交后清空，不能替代已提交消息的时间线展示。
- 实际操作：通过真实工作台新建 `review6-ui@example.test`，正文空、上传合成 PNG 后保存成功。时间线显示文件名与“待分析”，点按钮可打开受控原图抽屉，但消息中没有缩略图。保存了 [修前时间线](artifacts/phase8/review6/phase8-review6-timeline.jpg) 和 [原图抽屉](artifacts/phase8/review6/phase8-review6-image-drawer.jpg)。
- 优先级 MEDIUM：原图查看、附件绑定和权限可用；缺失的是明确要求的辅助 UI 展示。不能把整体 UI 一致性标为完整实现。
- 完成标准：已提交邮件展示受控缩略图及逐图真实状态；缺失/不支持/取消/撤销不伪装为成功图；失败、跨作用域与撤销沿用现有受控读取门。补丁需另轮验证，不改 Spec 放宽要求。

## Stage 1：REQ-014 每项 MUST

下表“工程已验证”只指本期确定性实现；涉及模型能否稳定读对、选对、措辞正确的部分仍延期。后端短路径 `attachments/`、`agent/` 等均位于 `globalmail-agent/backend/src/globalmail_agent/`。

| Spec 位置与原文要求 | 实现与本轮证据 | 结论 |
|---|---|---|
| :517 JPEG/PNG/static WebP、本地/受控包、附件/CID、仅图、拒绝远程执行、缺字节不假读 | `attachments/validation.py:8/16/29/37/39` 实际 verify/load 与格式/帧/字节/像素限制；`binding.py:49/73` 有序绑定和累计上限；`importing.py:26/62/71/75/78` 元数据、包路径/字节/摘要；`api/attachments.py:17` 流式上传；test_attachment_validation/binding、test_vision_import 全部真实执行。自己 UI 仅图新建成功。 | 本期工程已验证 |
| :518 联合提取候选、原始读数/歧义/位置、业务精确核验、冲突澄清 | `attachments/understanding.py:8/42/57/68/78/96` 候选/来源/歧义/人工优先；`agent/tool_gateway.py:96` 候选来源门并调用当前会话订单查询；`adapters/model_provider.py:25` 临时 SDK 图片视图。test_vision_provider/corrections 真实服务验证，歧义读数和澄清质量未测。 | 工程已验证；语义延期 |
| :519 可见观察/位置/质量/不确定原因，五类证据分层，不否定功能报告或认定局部缺件 | `attachments/understanding.py:15` 结构化 observation/inference/quality/uncertainty；`evidence.py:42/61/69` 分层存储；`agent/understanding.py` 与视觉提示约束；人工修订独立对象。test_vision_graph:44、corrections:16/33 验证投影及优先级。 | 数据与工程已验证；视觉/措辞语义延期 |
| :520 联合诉求/业务/SOP分流，普通图不强制人审，图片不授权交易 | `agent/graph.py:82/94/116` 联合理解/校验/风险门；`agent/tool_gateway.py` 只注册既有受限工具；`application/draft_validation.py:27/40/43` 来源约束；固定图样可正常生成一封模拟出站。内部售后写未在此 Phase 实现。 | 本期工程已验证；真实分流语义及 Phase 9 写延期 |
| :521 潜在危险不等订单、HITL、不要求通电拆机、指引有据；普通缺信息针对性补问 | `agent/graph.py:116` 校验后直接危险分支；`application/commit_outcome.py:52/64` 同事务人审与风险；`worker/agent_runner.py:74` 新轮先查有效风险。test_vision_graph:69 与实际连续风险反例验证不补模型调用。停止使用措辞/无限索图属于延期语义。 | 本期风险工程已验证；语义延期 |
| :522 有效风险直接持久化；预算/技术失败不能吞风险；无图像结论不得伪造；仍服从晚到门 | `agent/guard.py:43/54/65` 提交前锁与当前权校验；`graph.py:116` 无后续模型决策；`commit_outcome.py:64` 与人审共事务；`risk_records.py:29` 只按有效风险去重。test_vision_graph:69/100 与本轮新增风险 probe。 | 工程已验证，关闭第五轮 HIGH |
| :523 逐图全部状态/覆盖/真实失败原因，关键未覆盖不抢业务结论 | `attachments/lifecycle.py:5` 中断原因；`queries.py:15` 对外状态原因；`graph.py:79` 未覆盖门；`worker/agent_runner.py:138/146` 技术失败分类；`ImageEvidenceDrawer.vue:17/27/73` 状态、覆盖、独立预览/证据加载。test_vision_corrections:88 的真实对象读取失败被记录为技术失败。 | 工程已验证；Timeline 缩略图另有 M1 |
| :524 所有视图/复核/修复/重试共用旧预算、图像计入token、未知不记零、无图不加调用 | `agent/budget.py:46/54/56/72/98` 视图/请求/token/工具账本；`graph.py:45/55/67` reserve/settle；`attachments/views.py:17/26/34` 有限图像视图；`observability/usage.py` 未知 usage 保守记账。test_vision_graph:85 每次网络失败照计成本，六视图停止，未知用量非0。 | 工程已验证 |
| :525 会话独占、不入共享RAG；调用前校验全scope/前缀/用途，不复用未来结论 | `attachments/queries.py:22/37/64/91` scope/可见前缀/完整性；`views.py:50/63` 获准引用；`evidence.py:91/106` 当前证据门；test_attachment_lifecycle:89、binding:80、vision_import:64 实际作用域与历史前缀拒绝。 | 工程已验证 |
| :526 图中文字不可信、不能扩权限/退款；观测不导出二进制/链接/敏感正文，合成测试 | `model_provider.py:25/28/33` deep-copy 临时图片调用视图；`agent/context.py:73/97` 内部上下文仅引用且 JSON 读 bytes；`observability/local_records.py`/usage 脱敏计数；test_vision_graph:44 检查 checkpoint 无 base64/image_url。无远程 fetch/HTML 渲染/交易授权新增入口。 | 工程隔离已验证；模型遵循语义延期 |
| :527 人工更正来源与修订，旧运行不得写回/发信，更正本身不自动恢复 | `attachments/corrections.py:39/45/49/51/78/86` 人工处理权、row/input/epoch、版本、修订写入；`understanding.py:78/87/96` 人工字段覆盖并剔除矛盾自动事实；test_vision_corrections:16/33、graph:100 完整服务验证。 | 工程已验证 |
| :528 草稿移除/已提交撤销/完全副本删除及所有衍生、无晚到/备份复活、账本审计 | `attachments/intake.py:67/90/127` 草稿取消/清理；`corrections.py:78` 递增栅栏；`revocation.py:10/21` 递归依赖不可读；`adapters/body_store.py:63` 撤销严格410；`checkpoint_repository.py:107` checkpoint门；混合摘要/人工回复都依赖图片。test_vision_graph:16/129 与corrections:66 本轮实际执行。 | 即时撤销工程已验证；彻底物理删除/备份恢复 Phase 12 未实现，不标完整 PASS |

## Stage 1：AC-065–082 逐条映射

| AC（Product-Spec 行号） | 本期代码/独立验证 | 验收边界 |
|---|---|---|
| 065 (:531) 图片订单号/仅图、当前客户核验、不重复索取 | `attachments/understanding.py:57/96`、`agent/tool_gateway.py:96`；provider:25 人工候选号优先、binding:107 仅图、人审图来信；实际 UI 仅图新建。 | 工程路径验证；真实提取/不重复索取语义延期 |
| 066 (:532) 歧义/冲突/多订单、澄清、不越权 | `attachments/understanding.py:8/57/68` 保留 raw/ambiguity/sources，授权图片校验；订单查询仍由当前会话业务服务限定。 | 确定性门已验证；澄清语义延期 |
| 067 (:533) 可见异常/反光、观察和推测分开 | `attachments/understanding.py:15`、`evidence.py:42`、`ImageEvidenceDrawer.vue:17`；graph:44 验证逐图分层证据。 | 工程已验证；真实视觉判断延期 |
| 068 (:534) 照片不得否定功能故障、不得断言局部缺件 | `agent/understanding.py`、视觉提示与 `attachments/understanding.py:15`；没有“外观正常即解决/照片缺配件即发货”的程序写。 | 语义未验收，延期；不标该 AC PASS |
| 069 (:535) 适用依据分流、不猜操作/资格 | `agent/graph.py:94`、`application/draft_validation.py:40/43` 来源与商品依据；无自动资格/账本写入口。 | 工程门已验证；分流语义延期，内部申请 Phase 9 未实现 |
| 070 (:536) 潜在危险优先、预算/故障不能吞、无额外模型、无伪造危险 | `graph.py:116`、`commit_outcome.py:64`、`risk_records.py:29`、`agent_runner.py:74`；graph:69 与新增真实连续风险 probe，含0模型/0出站/ownerhuman。 | 确定性风险工程已验证；实际识别与安全措辞语义延期 |
| 071 (:537) 截图履约是材料，业务回执核验，不直接改账本 | `attachments/understanding.py:15`、`agent/tool_gateway.py` 受限只读业务入口；照片不存在直接写退款/发货路径。 | 本期隔离成立；回执/申请写 Phase 9 未实现 |
| 072 (:538) 缺失/坏图/不支持/模型故障原因真实，重发/重试/人审 | `validation.py:29/51`、`importing.py:26`、`agent_runner.py:146`；validation、vision_import:17/28、corrections:88 全部实际执行；抽屉 allSettled 不因原图失败丢弃证据版本（:73）。 | 本期工程已验证 |
| 073 (:539) 附件/CID/仅图、禁止HTML/远程、幂等 | `binding.py:12/37/49`、`importing.py:44/62`；binding:15/60、vision_import:28/44，本轮42项；实际仅图 UI 保存。 | 本期工程已验证 |
| 074 (:540) 跨客户/分支/用途/未来拒绝、合规前缀可分析 | `queries.py:22/37/64`、`views.py:50`、`evidence.py:106`；lifecycle:89、binding:80、vision_import:64。 | 本期工程已验证 |
| 075 (:541) 图片注入不扩权限/访问/退款 | `model_provider.py:25` 图片为 user input；`agent/tool_schemas.py` 与 `tool_gateway.py` 工具白名单；没有 URL 自动执行、任意SQL/path工具。 | 工程权限隔离成立；真实模型抵抗诱导语义延期 |
| 076 (:542) 多图/裁剪/重试全部计原预算，未知非0 | `budget.py:46/54/72/98`；`views.py:17/26`；graph:85 网络反例真实图/预算 ledger。既有6视图/6模型/12工具/120秒/16k单次输入/80k累计保持。 | 本期工程已验证 |
| 077 (:543) 在途遇新信/接管/停止/重置旧结果无效、不绕恢复 | `guard.py:43`、`corrections.py:49/51/78`、task_queue/jobs/leases 中断图状态；graph:100 模型回调内实际变更处理权，0有效分析/出站。 | 本期工程已验证 |
| 078 (:544) 立即撤销/可验证清理、备份不复活/账本不重办 | `revocation.py:10`、`body_store.py:63`、`checkpoint_repository.py:107`；graph:16/129、corrections:66、新增反例旧风险/原图410。 | 本期立即撤销验证；物理清理与备份恢复未实现，Phase 12 延期 |
| 079 (:545) 多商品/重复/超限/部分不可读逐图、不过度代表 | `binding.py:12/73` 拒重复及累计超限；`understanding.py:42/57` 逐图映射；`graph.py:79` 未覆盖门；binding:60、graph:44/85。 | 工程已验证；商品视觉配对语义延期 |
| 080 (:546) 有来源人工修订优先、旧缓存不能盖、无自动恢复 | `corrections.py:39/78/86`、`understanding.py:78/87/96`；corrections:16/33 检查字段/自动facts/SourceProjection；风险 probe 解除不会自己 claim。 | 本期工程已验证 |
| 081 (:547) 工作台预览/提取观察核验原因/Art外壳，无路径凭据 | `ImageEvidenceDrawer.vue:2/17/27/41/73/89/111`、attachment contract/API仅受控ID；真实 UI 上传与原图抽屉、邻居对照。 | AC内工程路径验证；关联 CMP-002 辅助展示 M1 未满足，UI部分实现 |
| 082 (:548) 冻结实际图片开发集、逐次模型/字段/观察/分流/禁止动作与用量 | 未跑付费专项，合成fixture/SDK烟测不代替它。 | 明确未验收、延期；不标 PASS |

## 前五轮失败与本轮关闭证据

历史 [INITIAL](PHASE-8-REVIEW-INITIAL.md)、[FINAL](PHASE-8-REVIEW-FINAL.md)、[CLOSURE](PHASE-8-REVIEW-CLOSURE.md)、[ENGINEERING-FINAL](PHASE-8-REVIEW-ENGINEERING-FINAL.md)、[5](PHASE-8-REVIEW-5.md) 原 FAIL 均保留，不因当前修复重写历史。原受控字节导入、缺字节元数据、人工覆盖、混合衍生撤销、失败原因与预览失败撤销路径分别用本轮导入/修订/撤销测试验证；没有用作者日志替代独立复验。

第五轮风险 HIGH 已独立关闭。关键改变是 `application/risk_records.py:29` 使用 `active_risks()` 得到**仍有有效依据**的风险 kind；不是查询任意旧 active 行。`:12/20` 对撤销对象排除读取，符合 `AGENT-ARCHITECTURE.md:230`“active且依据未撤销才有效”。`:40` 显式人工决定更新记录，新危险 B 必须保留新 id 与新来源，撤销 A 不恢复。

除永久 `test_vision_risks.py:9` 和 `test_agent_risks.py:31/54/70/83` 外，本 reviewer 自写 [probe](artifacts/phase8/review6/phase8-review6-risk-probe.py:36)，真实 PNG/PG/Graph/HTTP 连续执行：A fire HITL →撤销 A →keep_active →新 B fire HITL →keep_active →普通新信0模型0出站/ownerhuman →人工 `resolved_by_human` 附核验依据 →不自动 claim →下一新信可正常固定模型运行3调用1出站。旧 A 原图410、旧风险字节410，风险不复活。原输出：

```text
Ran 1 test in 6.372s

OK
REVIEW6_RISK {"new_risk_id_distinct": true, "new_source_b": true, "keep_active_models": 0, "keep_active_outbound": 0, "keep_active_owner": "human_review", "resolution_auto_run": false, "after_new_input_models": 3, "after_new_input_outbound": 1, "old_preview": 410, "old_risk_bytes": 410}
REVIEW6_PROBE_RESULT {"tests": 1, "failures": 0, "errors": 0, "skipped": 0, "source_changed": false}
```

[原日志](artifacts/phase8/review6/phase8-review6-risk-probe.txt)、[机器结果](artifacts/phase8/review6/phase8-review6-risk-probe.json)。固定模型负责构造工程输入，没有模拟数据库/提交门/风险逻辑。

共同分析撤销反例也独立通过：`test_vision_graph.py:16` 撤销 A 后另一图 B 原图仍200，但共享旧 GET evidence 与合法 POST correction 均410。`attachments/evidence.py:97/106`、`corrections.py:68`、`worker/agent_runner.py:99/123`、`application/draft_validation.py:27` 读机器 JSON 使用严格 `read_bytes`；不能对 `[REDACTED]` 文本再 json.loads 后500。风险列表 `risk_records.py:20` 主动跳过已撤销显示占位，不能把它当有效风险。

## Stage 2：质量、安全及测试真实性

**修前审查范围通过，未发现需报告的新增质量/安全问题。** 不延伸为全仓/正式发布认证。

| 维度 | 代码与实证 |
|---|---|
| 长度/结构/类型 | 本轮独立 [扫描](artifacts/phase8/review6/phase8-review6-audit.py) 84文件，最大300行、超限0；职责分为接收/验证/绑定/授权/证据/修订/撤销，运行/提交仍走既有服务。`frontend/tsconfig.json:6` strict=true；变更TS/Vue未发现 any，实际 vue-tsc 通过。生成 components.d.ts 不作为源缺陷或人工改动。 |
| 安全静态扫描 | 检查硬编码凭据、eval/exec/shell=True/pickle、HTML注入、SQL字符串、用户绝对路径、VITE秘密前缀与TS any。7个命中人工分类：`tests/test_api.py:15` 是 `SECRET_MARKER` 合成脱敏断言；`test_attachment_migration.py:20/22/25`、`test_knowledge_migration.py:21/23/26` 的schema名称来自固定前缀+uuid4().hex；`scripts/phase3-test-server.py:35/53/61/131` 来自受限phase整数+uuid hex。无客户/模型输入进入这些DDL标识符。官方 [Python UUID文档](https://docs.python.org/3/library/uuid.html)确认hex性质，业务值继续使用 [SQLAlchemy 参数化表达式](https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.text)。这是结合代码输入来源的判断，非“text()自动防注入”。 |
| 图片输入/访问/输出 | `validation.py:16/29/37/39` 按真实解码而非MIME/扩展名猜测；`queries.py:22/64` 请求时scope与哈希重核；`importing.py:71/75/78` 拒绝坏路径并核包字节摘要；`api/security.py:38` 仅图片上传获准raw body，仍保持Origin限制；原图/thumbnail受控预览，不向前端返回磁盘路径。SDK图片dataURL只在deep-copy临时请求中出现（`model_provider.py:25`）。 |
| 真实边界测试 | `test_attachment_validation.py:55` 使用实际可解码JPEG加尾部字节达到精确10MiB，再+1拒绝；实际生成5000×4001 PNG触发20M像素。不是只mock文件长度。:45 实际坏图/伪类型/动PNG/WebP/SVG/路径拒绝；:39 EXIF方向校准与缩略图剥离元数据。 |
| 真实事务/故障测试 | fixture通过实际Alembic/PG/ObjectStore/TestClient；intake:77并发首次上传收敛、lifecycle:56真实存储失败回滚，binding:39/60非法绑定整事务无消息/对象；migration:19保留0006旧行并升级0007默认图预算0、:73组合scope FK真实拒绝。没有仅测纯函数而忽略交互层。 |
| 风险/晚到/修订真实性 | graph:100 在模型调用回调中真实停止/接管/新输入/撤销，不靠不可达手工state；corrections:16/33校验后续有效字段/facts/sourceprojection及无自动恢复；独立新probe延长永久反例至显式人工解除和旧来源410。 |
| 测试与观测限度 | graph/provider使用固定模型输出，只能证明协议/门/SDK调用视图；不能证明实际 OCR、反光判断、正确补问、禁止危险操作语义或 AC-082。低风险UI缩略图缺口未被55项单测捕获，已用真实页面发现 M1。 |

## Stage 2：实际视觉邻居对照

没有 Design-Brief/设计稿，按现有 Art Design Pro + Element Plus 先例。本人创建独立后台 IAB，1280×720，实际操作上传、仅图保存、打开新图片证据抽屉；再打开既有人审抽屉、知识库页面与新建知识资料表单，未提交知识资料。

| 对照 | 文件/截图与实际结论 |
|---|---|
| 新证据抽屉 vs 既有人审抽屉 | `ImageEvidenceDrawer.vue:2` ElDrawer受限宽度、统一按钮/tag/表单/空态，真实原图可见；[图片抽屉](artifacts/phase8/review6/phase8-review6-image-drawer.jpg) 与 [人审邻居](artifacts/phase8/review6/phase8-review6-human-neighbor.jpg) 的白底、字体、遮罩、右侧布局、边距与蓝色操作继承同套主题，无新视觉系统。原图为空/不可读的消息仍留独立证据路径（:73），不会把网络失败误写模糊。 |
| 上传/业务区 vs 知识库先例 | `ImageUpload.vue:8/37/51/79` 复用Element操作与限制提示；[知识库基准](artifacts/phase8/review6/phase8-review6-knowledge-neighbor.jpg)、[既有编辑表单](artifacts/phase8/review6/phase8-review6-knowledge-drawer.jpg) 可见同外壳、按钮、留白与表单气质。新组件未引入硬编码独立配色。 |
| UI缺口 | 修前时间线确实只有filename/status按钮，M1保留。原图详情入口成功不抵消缩略图要求。 |

本轮没有独立重跑900×900与暗色全流程，不将主 Agent 此类截图冒充自己的验证。源组件使用现有主题类/变量；本轮实际视觉结论仅覆盖上述1280×720亮色邻居场景。自建tab已关闭、viewport override已reset，服务未由reviewer停止；合成UI会话仅在主 Agent 的隔离schema，已告知其清理。

## 独立编译与功能验证原始输出

### 后端：42项受影响模块，冻结通过

项目根命令（PowerShell）：

```powershell
& globalmail-agent/backend/.venv/Scripts/python.exe -X utf8 tmp/phase8-review6-tests.py test_attachment_validation test_attachment_intake test_attachment_binding test_attachment_lifecycle test_attachment_migration test_vision_import test_vision_provider test_vision_graph test_vision_corrections test_vision_risks test_agent_risks *> tmp/phase8-review6-tests.txt
```

```text
----------------------------------------------------------------------
Ran 42 tests in 80.509s

OK
```

[原始日志](artifacts/phase8/review6/phase8-review6-tests.txt)、[结果/前后SHA](artifacts/phase8/review6/phase8-review6/independent-tests.json)：tests42、failures0、errors0、skipped0、successful=true、source_changed=false，runner墙钟80.579秒。新增risk probe另1项/6.372秒，不伪装成原永久测试总数。

### 后端编译及依赖

backend目录执行：

```powershell
& .venv/Scripts/python.exe -m compileall -q src tests migrations *> artifacts/phase8/review6/phase8-review6-compile.txt
```

stdout/stderr为空，原命令结果 `compileall_exit=0`。[日志](artifacts/phase8/review6/phase8-review6-compile.txt)。先尝试 `python -m pip check` 得到 `No module named pip`，随后使用此仓库实际uv环境验证，不安装pip、不把运行器缺pip报成项目缺陷：

```powershell
uv pip check --python globalmail-agent/backend/.venv/Scripts/python.exe *> tmp/phase8-review6-dependencies-uv.txt
```

```text
Using Python 3.12.10 environment at: globalmail-agent\backend\.venv
Checked 58 packages in 3ms
All installed packages are compatible
uvcheck_exit=0
```

[原始uv输出](artifacts/phase8/review6/phase8-review6-dependencies-uv.txt)。

### 前端测试与构建（修前）

frontend目录执行 `pnpm test *> artifacts/phase8/review6/phase8-review6-frontend-tests.txt` 与 `pnpm build *> artifacts/phase8/review6/phase8-review6-build.txt`，命令返回0。测试原输出：

```text
ℹ tests 55
ℹ suites 0
ℹ pass 55
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2472.7596
frontend_test_exit=0
```

构建原输出关键段（完整逐资源大小见日志）：

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3325 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 30.68s
build_exit=0
```

[55项原日志](artifacts/phase8/review6/phase8-review6-frontend-tests.txt)、[完整构建原日志](artifacts/phase8/review6/phase8-review6-build.txt)。没有用raw tsc跳过Vue识别、没有添加any垫片、未改工程设置。

## 收口与未完成事项

本期工程核心的独立42项及自写1项真实连续风险反例通过，旧风险去重 HIGH、共同分析撤销410与人工修订的旧失败有当前实证。Stage 2 已执行并记录安全扫描、测试真实性和新旧页面实际对照。唯一新增 MEDIUM 是修前 CMP-002 时间线缺缩略图；主 Agent 已修补，但本轮不将审查中的源码变更改写成通过，需 fresh 第七轮从 Stage 1 复核。

主 Agent 的旧317全量含 `source_changed=true`，不能称最终冻结全量；68项旧冻结、最终风险16项属于开发者证据。收口时另直接读取最终 [JSON](artifacts/phase8/backend-tests-final.json)/[原日志](artifacts/phase8/backend-tests-final.txt)：实际319项、0fail/error/skip、`source_changed=false`，unittest787.719秒、runner787.828秒；此前估计318不能代替真实数量。这是主 Agent 运行所得，未冒充 reviewer 独立全量，也不替代本轮独立42+1判断。原前五轮FAIL及Phase1/7语义FAIL保留，AC-082/Phase9/Phase12仍真实标延期或未实现，没有整产品82AC通过声明。

reviewer没有修改源码/需求、运行付费模型、提交Git、启动/停止共用服务或写正式数据，仅输出本报告及自用tmp产物。下一步由主 Agent 合并发现、保持冻结边界并派 fresh 审查。
