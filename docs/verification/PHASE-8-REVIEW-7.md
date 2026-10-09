# Phase 8 第七轮独立审查

审查日期：2026-10-09。角色：fresh code-reviewer。基线：`09a818fa9976c94e5c50a090620993b324b603ea`（main/HEAD）。审查工作树增量及新增文件，未修改实现、需求或正式数据库，未提交，未调用付费模型。

**Stage 1：本期工程范围 PASS；Stage 2：PASS。没有新增 HIGH，没有待修复的 MEDIUM 工程阻塞。第六轮 CMP-002 时间线缺少缩略图的缺口，在本轮独立读码、实际浏览器解码尺寸、真实 HTTP、失败回退及撤销验证后关闭。**

这不是全部产品验收通过。AC-065–082 仍未勾选；Phase 1/7 的真实模型语义 FAIL 保留，实际字段、观察、分流、禁止动作与 AC-082 的冻结集验收按用户既有决定延后统一调整。本轮不以合成模型响应证明模型质量。Phase 9 售后写、Phase 12 彻底删除及恢复备份验证没有交付，也没有被本报告判为完成。

## 输入、范围和独立性

已读 AGENTS.md、`.agents/skills/code-review/SKILL.md`、`.codex/agents/code-reviewer.toml`，Product-Spec/AGENT-ARCHITECTURE/DEV-PLAN 全文，按 docs/README 阅读 PHASE-8-IMPLEMENTATION 与 SESSION-HANDOFF，并读前六轮原问题与边界。以下逐项从 REQ-014 和 AC 原文建立映射，不继承前轮 PASS。

需求授权见 `Product-Spec.md:5`、`AGENT-ARCHITECTURE.md:5`、`DEV-PLAN.md:178`、`DEV-PLAN.md:327`、`DEV-PLAN.md:328`；本期工程实施见 `docs/planning/PHASE-8-IMPLEMENTATION.md:5`。无设计稿和 Design-Brief，本轮按 Art Design Pro、Element Plus 与现有工作台、ReferenceDrawer、知识/系统状态页面审查 UI。

以下路径缩写仅为表格可读性：`B/` = `globalmail-agent/backend/src/globalmail_agent/`；`BT/` = `globalmail-agent/backend/tests/`；`F/` = `globalmail-agent/frontend/src/`。均为本仓库真实文件及起始行号。

独立执行使用 `agent-eval/bootstrap.isolated_database_environment()` 和现有 VisionFixture，随机私有 PostgreSQL schema、独立对象目录自动清理。真实浏览器另开 `phase8review7`，仅在主 Agent 的无 worker/无模型配置隔离服务新建 `review7-ui@example.test`；没有操作 root 的浏览器。风险验证由新 Python 进程加载当前源码，未用早于风险修复启动的 UI API 证明风险逻辑。

## Stage 1：REQ-014 的 12 项 MUST

| 原文项与 Spec 位置 | 代码证据、独立验证 | 本期判断 |
|---|---|---|
| 1 接收 JPEG/PNG/静态 WebP、附件/CID、受控字节的仅图来信；不执行 HTML/远程图，缺字节不假识别（517） | `B/attachments/validation.py:29` 真实 PIL open/verify/load 白名单，33 像素与35动画限制，40 EXIF；`binding.py:12` 唯一 ID/CID，49 同事务绑定；`importing.py:43` 缺失/不支持，62 受控包。独立 binding/import 测试及真实 UI 空正文提交成功；自写 JPEG EXIF 测试取得真实缩略字节。 | 工程完整；真实识别语义延期 |
| 2 候选订单/SKU/错误码保留 raw/歧义/附件版本位置，精确工具核验及冲突澄清（518） | `B/attachments/understanding.py:8` raw/value/ambiguous schema，57 图像订单须无歧义且 value 在 raw 中；`evidence.py:79` 来源 SHA/location/epoch；`agent/tool_gateway.py:103` 查单来源门禁及当前客户 business.detail；`understanding.py:69` 人工订单优先。独立 provider/corrections 测试核验受控候选及人工来源。 | 工程完整；实际读数/冲突澄清质量延期 |
| 3 可见观察/位置/质量/不确定，陈述/观察/推测/核验/人工分层；不以正常外观否定功能故障或局部未见证明缺件（519） | `B/attachments/understanding.py:15` 独立 observations/hypotheses/uncertainties/quality/coverage；`agent/understanding.py:69` 图像事实不可冒充客户或业务工具；`agent/prompts/visual-understanding.md:11` 明示功能故障/反光/缺件约束；`evidence.py:79` 独立 kind。独立 graph/corrections 保存与更正断言。 | 分层工程完整；真实观察与禁止动作语义延期 |
| 4 图文、客户诉求、核验订单/SKU、SOP/政策联合分流；图片不授根因、资格或账本权（520） | `B/agent/graph.py:82` 同一请求正文与 actual images；`tool_gateway.py:126` 售后只读且 policy_authorized=False；`application/draft_validation.py:38` 指导引文、40 订单事实业务工具来源；`agent/context.py:84` 明示 Phase9 写不可用。独立 graph 联合请求及 SDK provider 测试。 | 本期工程完整；真实分流语义延期，内部申请写属 Phase9 |
| 5 潜在危险 HITL、不等订单、不要求通电拆机；缺信息针对补问（521） | `B/agent/prompts/visual-understanding.md:12` 无订单危险/安全限制；`agent/graph.py:98` 图像风险转换来源；`worker/agent_runner.py:74` 有效存量风险先转人工；`application/risk_records.py:12` 仅有效来源。独立危险1次请求、连续新风险后普通来信0次请求/0出站。 | 危险工程完整；实际危险识别、补问措辞延期 |
| 6 有效危险来源/Schema/处理权通过后程序同事务 HITL，无额外模型/预算，仍受晚到门禁（522） | `B/agent/graph.py:111` 来源校验、116 直接 risk_handoff；`application/commit_outcome.py:64` 危险理解/风险/人审终态同事务；`agent/guard.py:43` 处理权锁序；`BT/test_vision_graph.py:69` 有效危险耗尽仍人审且1请求，100 在途撤销/停止/接管/新输入不落事实。均本轮独立执行通过。 | 完整 |
| 7 每图真实状态及 coverage；技术失败不说模糊、关键图不以一图代表全部（523） | `B/attachments/understanding.py:42` 集合及数量须精确覆盖所有输入图，48 unreadable不能有观察/字段/风险；`attachments/lifecycle.py:5` interrupted→failed真实原因；`worker/agent_runner.py:146` 每图技术错误；`F/components/mail-agent/MessageTimeline.vue:43` 独立状态；drawer:17 分层与状态。独立 graph 及 corrections:88 存储失败路径。 | 完整 |
| 8 原预算6视图/6请求/12工具/120秒/16k输入/80k总，裁剪修复重试共同计费，unknown不0，无图不额外（524，ASM005/006/011） | `B/agent/budget.py:46` 文字+视觉保守输入预留、49/54/56 限制、72 实际/unknown结算；`agent/graph.py:45` 每次重试重授权及预留、55 加载受控 bytes；`attachments/views.py:31` 视觉上界。独立 `test_network_retry_charges_views_unknown_usage_and_stops_over_six`。不新增第二视觉 Agent。 | 完整 |
| 9 当前会话证据，不进入共享RAG；客户/模式/分支/用途/历史前缀，拒绝未来图/分析缓存（525） | `B/attachments/queries.py:22` 全 scope 授权、37 prefix；`views.py:34` 当前可见附件，63 SDK前再验epoch/source/run；`evidence.py:17` visible-prefix、42 scoped保存；`agent/context.py:87` 不复用联合图理解。独立 lifecycle 所有scope、import历史前缀、graph递归失效。 | 完整 |
| 10 图中文字为不可信输入，不扩大权限；观测不导原图/base64/链接/敏感正文；用合成/授权样本（526） | `B/agent/prompts/visual-understanding.md:14` 明示不可信图文；`agent/tool_schemas.py:8` 严格工具集；`adapters/model_provider.py:25` SDK临时深拷贝注入 bytes；`observability/sanitization.py:2` 有限元数据白名单；`observability/local_records.py:17` 理解进入受控对象。独立 SDK实际输入与 checkpoint无二进制断言。UI本轮只用合成PNG/JPEG。 | 工程完整；模型遵循诱导的真实语义专项延期 |
| 11 人工修订有来源，新输入/接管/更正/停止/重置/移除晚到不写回或发信，更正不恢复HITL（527） | `B/attachments/corrections.py:45` conv版本锁、49 input、51 epoch、53人工权，60逐字段保留、78invalidate、81关闭自动门；`understanding.py:78` 人工覆盖；`agent/guard.py:43` 权限/版本栅栏；`F/views/mail-agent/index.vue:219` detail刷新同步附件。独立4更正测试与在途测试通过；UI真实接管/撤销后image DOM移除。 | 完整 |
| 12 上传移除、提交撤销、彻底删除及全部派生/备份/账本边界（528） | `B/attachments/intake.py:67` 未绑定取消、90过期清理；`attachments/revocation.py:10` 递归来源判撤销；`adapters/body_store.py:63` strict bytes→410，50展示redaction；checkpoint_repository.py:107 门禁。独立取消/清理/共享证据/草稿派生/preview410。`F/components/mail-agent/ImageEvidenceDrawer.vue:41` 明示完整副本删除后续。 | 本期取消/撤销完整；Phase12物理删除/备份未实现 |

## AC-065–082 逐条原文映射

“工程通过”仅指本期可运行约束和来源/权限结构，不把下表转成产品 AC 勾选。

| AC 原文（Product-Spec.md:531–548） | 工程证据与验收边界 |
|---|---|
| 065：Given 订单号仅在清晰图片中或正文为空且有图，when 理解与查单，then 提取有来源的候选并核验当前客户订单，不重复索取已核实信息。 | `B/attachments/binding.py:49`、`understanding.py:63`、`agent/tool_gateway.py:103`；真实UI仅图空正文提交、独立SDK图字节/字段来源测试通过。实际读数与不重复索取语义延期，未勾选。 |
| 066：Given 0/O 等歧义、正文/图片冲突或多订单截图，when 定位对象，then 保留候选与歧义并澄清，不猜号、不跨客户查询、不擅选商品。 | `B/attachments/understanding.py:8`、57歧义拒绝、`agent/tool_gateway.py:103`客户精确工具。代码门禁和scope测试通过；真实冲突/多商品澄清延期。 |
| 067：Given 可见破损/变形或疑似反光裂纹，when 分析，then 输出对应原图的观察与不确定项，区分推测，不直接断定原因、责任或真实性。 | `B/attachments/understanding.py:15`、`evidence.py:79`、`agent/prompts/visual-understanding.md:12`；graph/evidence结构断言通过。真实观察正确率延期。 |
| 068：Given 外观正常但客户说不亮/异响，或局部照片未见某配件，when 回复，then 保留功能故障/缺件待核实，不以照片否定客户或认定缺件。 | `B/agent/prompts/visual-understanding.md:11` 有精确约束；工程支持客户陈述与观察分层，真实输出是否遵循仍延期。 |
| 069：Given 可见异常、核验商品和适用 SOP/政策，when 分流，then 选择有依据的指导、补问或满足条件的内部申请；未知型号/兼容不猜操作，图片不直接授予资格。 | `B/agent/tool_gateway.py:142` published知识检索与line授权、`application/draft_validation.py:38` 来源约束；指导工程可用。真实分流语义延期，业务申请写为Phase9，不声称本期实现。 |
| 070：Given 文字或图片提示潜在危险且可能尚无订单，when 已形成有效风险标记或此后预算耗尽/技术失败，then 程序直接持久化 HITL，不等待额外模型决策；按已核准指引提示，不要求通电/拆机，也不把疑似现象写成已证实根因；未识别的技术失败不伪造危险。 | `B/agent/graph.py:111`、`application/commit_outcome.py:64`，独立 `BT/test_vision_graph.py:69`、100与 `test_vision_risks.py:11` 真PG通过。有效标记工程完整；模型危险识别/安全措辞语义延期。 |
| 071：Given 图片标示退款成功/已发货或请求改变金额，when 判断业务状态，then 将其记录为客户材料并核验业务回执/政策/选择，不直接改账本。 | `B/agent/understanding.py:69`图像不可伪装business，`tool_gateway.py:126`只读能力，`draft_validation.py:40`订单事实工具来源。工程没有售后写工具；真实截图语义延期。 |
| 072：Given 图片缺失/损坏/模糊/不支持，或视觉服务技术失败，when 收口，then 分别显示真实原因和重发/重试/人审路径，不假装读过、不将技术失败伪装为图像质量问题。 | `B/attachments/importing.py:43`、`validation.py:29`、`lifecycle.py:5`，独立import/corrections技术失败通过；真实UI thumbnail503显示“无法预览”仍可开原图/撤销。工程完整，真实模糊识别语义延期。 |
| 073：Given 附件图、CID 内嵌图、仅图片来信或远程链接，when 接收，then 前三类在具备受控字节时可关联处理；不执行 HTML、不自动取远程图；重复接收不重复发信。 | `B/attachments/binding.py:12`及49；`importing.py:62`只读受控包、没有远程fetch；独立binding/import真实幂等、CID及原子回滚测试，真实UI仅图成功。工程完整。 |
| 074：Given 跨客户/分支/用途图片、历史截点后的重发图或缓存，when 读取/预览/复用，then 拒绝越界；可见前缀的合规图片可分析且标记分析时间，不泄漏未来结论。 | `B/attachments/queries.py:22`、`evidence.py:17`、`adapters/checkpoint_repository.py:107`。独立lifecycle全scope、import历史metadata、SDK读前再授权、自己的跨conversation404通过。工程完整。 |
| 075：Given 图片文字诱导忽略规则、访问链接或退款，when 理解，then 只记录业务内容，不扩大工具/访问权限，不将图中文字当系统指令。 | `B/agent/prompts/visual-understanding.md:14`、工具白名单、scope/精确查单来源约束、SDK仅受控对象。工程门禁通过；真正诱导输出专项不被mock测试替代，语义延期。 |
| 076：Given 多图、裁剪复核、重试或 usage 缺失，when 请求模型，then 所有视觉成本计入原单轮预算；超额显式停止/显示未覆盖范围，未知用量不记零。 | `B/agent/budget.py:46`、72、`graph.py:45`、`attachments/views.py:31`；独立 retry/views/unknown/6次限额真实PG断言通过。工程完整。 |
| 077：Given 视觉请求在途时新来信/接管/停止/重置，when 旧结果晚到，then 不写入当前有效事实、不模拟发信、不绕过人工恢复屏障。 | `B/agent/guard.py:43`、`attachments/corrections.py:78`，独立 `BT/test_vision_graph.py:100`覆盖stop/takeover/newinput/revoke，0晚到事实/出站；更正不自动启用。工程完整。 |
| 078：Given 移除/彻底删除图片及其派生内容，when 晚到任务或恢复备份，then 撤销立即生效、清理可验证、旧内容不复活；业务账本不因删除而重复办理。 | `B/attachments/revocation.py:10`、`body_store.py:63`、`intake.py:90`；独立派生410、上传cancel清理及UI410/DOM去图。撤销子集完整；彻底删除及恢复备份属Phase12，未完成本条全验收。 |
| 079：Given 多张图对应不同商品、重复图、超限或部分不可读，when 分析，then 保留逐图状态/关联和未覆盖信息，不混用商品证据、不以成功的一张代表全部已读。 | `B/attachments/binding.py:12`/73限额和有序绑定，`understanding.py:42`逐图集合严格相等，`views.py:34`6view上限/coverage；独立4图/总量/重复CID及joint graph通过。实际多商品语义延期。 |
| 080：Given 人工更正视觉观察或字段，when 后续合法运行，then 使用有来源的新修订，旧分析/缓存不覆盖人工判断；更正本身不自动恢复 HITL。 | `B/attachments/corrections.py:45`、60、78、`understanding.py:78`；独立 `BT/test_vision_corrections.py:16`、33覆盖所有字段/观察/假设及新合法运行。工程完整。 |
| 081：Given 在工作台上传、查看或移除图片，when 操作，then 可预览原图、查看提取/观察/核验状态与失败原因，复用 Art Design Pro 且不向前端暴露服务器路径或凭据。 | `F/components/mail-agent/ImageUpload.vue:9`、`MessageTimeline.vue:31`、`ImageEvidenceDrawer.vue:13`/17/40、`F/api/attachment-api.ts:4`；独立UI actual decoded512/112、503不挡原图800/详情200/撤销、DOM0/410，邻居实际页面对照。工程完整；实际提取正确率另验。 |
| 082：Given 冻结图片专项开发集，when 验收，then 使用实际图片输入并分别核对字段、观察、分流和禁止动作，保存逐次结果/模型配置/耗时/用量；参考答案不入模型，组件读图烟测不能代替此验收。 | 明确未执行、未通过。用户授权统一延期，见 `DEV-PLAN.md:328`。本轮合成图片+受限VisionModel仅证明实际字节链、权限、落盘、预算及UI，不能证明真实模型语义；不勾选。 |

## CMP-002 / CMP-003 / CMP-013 与真实 UI

`Product-Spec.md:573` 要求时间线“图片缩略图与逐图状态”。`F/api/attachment-api.ts:4` 共用 previewPath，15 thumbnailUrl 仅由受控attachment/conversation ID组成；`F/components/mail-agent/MessageTimeline.vue:31` w-28卡片，34 contain，35 native lazy/h-20，36加载中/37无法预览，39完整title文件名按钮，41 max-w-20 truncate，43状态独立文字。revoked/cancelled/missing/unsupported没有图片请求，撤销文件名禁用。

本轮实际经上传控件提交 800×500 合成 PNG，长文件名172字符，正文和主题为空。真实浏览器 timeline 图像已解码 `naturalWidth=512`，实测 `width=112,height=80`；这是浏览器加载图像后的尺寸，不是仅数节点。1440/1280/900宽度下卡片仍112px，邮件容器 `scrollWidth=clientWidth`（531/731/785的首次测量；900刷新稳定后为517），全title保留文件名。布局切换及固定 composer 占用使时间线是独立滚动区域，截图有纵向裁切，未将其说成整张卡片始终同时可见。[真实测量/请求结果](artifacts/phase8/review7/ui-finish.json)、[1280渲染](artifacts/phase8/review7/timeline-stable-1280.png)、[900渲染](artifacts/phase8/review7/timeline-stable-900.png)。自己的HTTP测试取得实际EXIF缩略JPEG并用PIL再解码为256×512，scope404与no-store均有断言。

人工只注入 `thumbnail=true` 的503，页面显示“无法预览”，文件名按钮仍可用；实际点击打开原图抽屉，原图解码 `naturalWidth=800`、evidence HTTP200。`ImageEvidenceDrawer.vue:73`显式请求 `preview(image,false)`，故真实800px原图并非缩略图。继而经现有“人工接管”与“确认撤销”真实UI完成撤销，时间线 `img=0`、filename disabled、文字“已移除”；浏览器显式thumbnail、默认preview及evidence均HTTP410 `attachment_revoked`、`Cache-Control: no-store`，自己的新TestClient另行明确 `thumbnail=false` 原图HTTP410。原始UI脚本把不带thumbnail参数的preview记录命名为original，而接口默认true；报告不将这个命名错误当作额外原图HTTP证明。[失败不挡原图的实际渲染](artifacts/phase8/review7/original-on-thumbnail-error.png)、[撤销DOM/HTTP](artifacts/phase8/review7/ui-revoke.json)、[撤销页面](artifacts/phase8/review7/after-revoke-900.png)。本轮不以 API 直接撤销冒充按钮流程。

CMP-003 对照 `Product-Spec.md:574`：`F/components/mail-agent/ConversationDialog.vue:42`、`MessageComposer.vue:20`支持图片上传、原图草稿与仅图有效来信；`ImageUpload.vue:75`晚到/切范围取消、82移除，失败不清空草稿；`useMailWorkbench.ts:202`仅成功才清空追加输入。独立binding测试包括人工接管状态仅图追加不自动模型。真实UI创建和上传见原始[执行脚本](artifacts/phase8/review7/phase8-review7-ui-create.js)。

CMP-013 对照 `Product-Spec.md:584`：`F/components/mail-agent/ImageEvidenceDrawer.vue:13`原图、17按观察/字段/假设分组、20 raw与21歧义、23 coverage、27人工修订、40提交撤销，73 allSettled使原图/证据故障独立，82刷新scope防晚到URL，118释放objectURL。未伪称完整副本已删；drawer说明后续阶段。数据由 `B/attachments/evidence.py:90`受控来源，业务核验仍由原订单/处理抽屉显示，图片不充当正式订单/账本。

## 历史失败的复验与保留

前六报告原结论不改写：[INITIAL](PHASE-8-REVIEW-INITIAL.md)、[FINAL](PHASE-8-REVIEW-FINAL.md)、[CLOSURE](PHASE-8-REVIEW-CLOSURE.md)、[ENGINEERING-FINAL](PHASE-8-REVIEW-ENGINEERING-FINAL.md)、[第5轮](PHASE-8-REVIEW-5.md)、[第6轮](PHASE-8-REVIEW-6.md)。

- 前1/2轮元数据/受控包/人工覆盖/预览失败无法撤销：本轮独立执行import、全部manual字段覆盖和存储失败，以及真实thumbnail503仍原图/详情/撤销；相应代码 `B/attachments/importing.py:62`、`understanding.py:78`、`F/components/mail-agent/ImageEvidenceDrawer.vue:73`。工程复验通过。
- 第3/4轮联合图来源撤销：本轮执行 `BT/test_vision_graph.py:16`，A撤销后B自己的preview200，共享analysis GET与合法correction POST严格410。`B/attachments/evidence.py:32`/97/106、`corrections.py:68` 用read_bytes解析JSON，未把展示REDACTED当JSON；来源递归作用于整份联合分析是保守失效，不是泄漏。复验通过。
- 第5轮撤销旧A危险后同类新B风险被吞：本轮新进程执行 `BT/test_vision_risks.py:11`，旧A危险→撤销→人工keep_active→新B同类fire→人工keep_active→普通新邮件；B风险新ID及有效B source，后续0模型/0出站/人审，`B/application/risk_records.py:29`只以active_risks有效来源去重。复验通过。人工显式解决逻辑仍由 `human_review.py:77` 与`risk_records.py:39`校验有据决定，人工回复后停在human_wait_customer，新输入才推进；本轮没有把代码阅读说成额外真实解除风险测试。
- 第6轮 CMP-002 原缺口：本报告只对当前两个补丁文件及冻结SHA背书，第6轮修前缺口保留。当前工程复验通过。

## Stage 2：质量、安全、测试真实性、视觉对照

| 项目 | 独立证据与结论 |
|---|---|
| 文件大小/类型/职责 | 自己枚举84个变更/新增源码、测试与prompt，源最大300行，0超限，frontend any匹配0；额外1个相对root83列表是prompt等审计口径差异。`globalmail-agent/frontend/tsconfig.json:6` strict=true，实际vue-tsc成功，没有any/.vue垫片放宽。附件校验/接收/绑定/读/视图/证据/修订/撤销各有模块。完整[current-source-audit](artifacts/phase8/review7/current-source-audit.json)。PASS。 |
| 安全扫描 | 对本期代码扫描硬编码密钥、eval/v-html/innerHTML、危险前端变量及机器绝对路径，结果0，完整模式/匹配保存[audit](artifacts/phase8/review7/audit.json)。进一步读 `B/attachments/importing.py:63`resolve/path containment/SHA、`validation.py:16`filename规则、`api/security.py:19`localhost/Origin、`api/attachments.py:28`流量上限、47no-store/nosniff/CSP。SQLAlchemy参数化；隔离launcher schema字符串由自身uuid生成，不来自输入。未发现需报告的安全缺陷，未对没有疑点的代码虚构外部漏洞结论。PASS。 |
| 原图/观测/检查点 | `B/adapters/model_provider.py:25`临时深拷贝SDK bytes注入，Graph/context持有受控refs；`observability/sanitization.py:2`白名单不含imageURL/base64/text；`body_store.py:63`与checkpoint_repository.py:107递归撤销。独立SDK及joint checkpoint测试实际断言无原图/base64，非仅接口mock名称。PASS。 |
| 测试真实性 | selected tests是真随机PG schema、真实PIL图字节、实际事务+对象存储+AgentRunner/TestClient，VisionModel只替付费provider并记录请求。抽查 `BT/test_vision_graph.py:16`每个合法scope、44 checkpoint、85未知usage、100真实在途callback，`test_vision_risks.py:11`实际服务逐步状态变化且 no_model.configured=False证实危险门禁先于provider配置。自己补EXIF/HTTP200真实解码/404/410。浏览器测试走实际上传、文件名、接管、确认撤销，故障只替thumbnail网络请求。PASS；真实模型语义仍是明示盲区。 |
| 新表/API/范围漂移 | `B/adapters/attachment_schema.py:8`与0007 migration仅3合并物理表（message_attachments、image_views、visual_evidence），来源/关系接现有内容表；`main.py:70`装配附件/视觉API，契约对应架构:378。本期没有新增共享图片RAG/远程链接抓取/真实邮箱投递/自动售后写/第二模型Agent。正式schema升级不属于此审查执行。PASS。 |
| 视觉实际邻居 | 独立打开 `#/knowledge` 和 `#/system-status`，真正截图及查看，不只读取源码。[知识库实渲染](artifacts/phase8/review7/neighbor-knowledge-real.png)、[系统状态实渲染](artifacts/phase8/review7/neighbor-system-real.png)、[页面文字](artifacts/phase8/review7/ui-neighbor.json)。新drawer原图截图同样使用现成抽屉头部/关闭、ElTag/ElEmpty/按钮；时间线与上传区同w28/contain卡，原有page-content、border-d/rounded、灰蓝提示及主色按钮保持先例。`F/components/mail-agent/ReferenceDrawer.vue:2`与ImageEvidenceDrawer:2同ElDrawer，`F/views/knowledge/index.vue:4`同ElCard/按钮先例。PASS。 |

首次邻居 `page.screenshot` 在页面过渡期取得空白截图，原始产物保留，但不作为视觉通过证据；之后单独执行CLI截图，实际知识/系统内容已渲染并由本 reviewer查看，报告链接的是 `*-real.png`。UI console 的2条错误对应本轮故意注入的thumbnail503，未将其当成生产成功响应。

## 独立执行、原始编译输出与 SHA

本轮未再跑无差别319项。自己的28项运行含27项现有生产路径测试及1项自写HTTP测试，0fail/error/skip，77.731秒；before/after后台源码SHA完全相同。自写测试首次无关的额外Graph调用产生 `agent_dependency_error` 日志，未对那次调用作成功断言，不能算Graph成功证据；因此移除该无关调用，改为明确人工接管后单独重跑同一EXIF/HTTP测试，1/0fail/error/skip、2.283秒，源码仍不变。首次原始日志保留而未覆盖；当前自写脚本与第二份输出为干净HTTP验证依据。27项生产Graph/风险等自身均有其独立断言，未受该诊断调用影响。

[28项原始输出](artifacts/phase8/review7/phase8-review7-tests.txt)、[第一次冻结源JSON](artifacts/phase8/review7/independent-tests.json)、[自写测试干净重跑](artifacts/phase8/review7/phase8-review7-thumbnail-tests.txt)、[干净重跑JSON](artifacts/phase8/review7/thumbnail-tests.json)。

```text
----------------------------------------------------------------------
Ran 28 tests in 77.731s

OK
REVIEW7_TEST_RESULT {"tests": 28, "failures": 0, "errors": 0, "skipped": 0, "duration_seconds": 77.76500000001397, "source_changed": false}

----------------------------------------------------------------------
Ran 1 test in 2.283s

OK
REVIEW7_REAL_THUMBNAIL {"decoded_size": [256, 512], "scope_denied": 404, "cache_control": "no-store", "after_revoke": {"true": 410, "false": 410}}
```

独立 `python -m compileall -q` 对backend/src、migrations、tests，exit0；静默成功原始[输出文件](artifacts/phase8/review7/phase8-review7-compileall.txt)。独立 `npm run test` exit0，以及 `npm run build`（包含项目适用vue-tsc+Vite）exit0；生成components.d.ts不是人工源码变更，不使用raw tsc不认识.vue的基线问题追加any垫片。[前端单测全部原文](artifacts/phase8/review7/phase8-review7-frontend-tests.txt)、[编译全部原文](artifacts/phase8/review7/phase8-review7-frontend-build.txt)：

```text
ℹ tests 55
ℹ suites 0
ℹ pass 55
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2538.1949

> art-design-pro@0.0.0 build
> vue-tsc --noEmit && vite build

🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
✓ built in 28.35s
```

主 Agent 全量证据只作为额外历史覆盖：`artifacts/phase8/backend-tests-final.json/txt`为319/0fail/error/skip、冻结源；原 `backend-tests.json`/`backend-tests-full.txt`为317且source_changed=true，不能冒充final。本轮未声称自己执行319。主 Agent修后55/build-final与旧frontend-tests/build文件也是不同快照；上列为本轮自己重跑的修后输出。主 Agent正式库只读与清理结果见 `artifacts/phase8/formal-readonly-and-cleanup.json`，不是本 reviewer新增写库或实测生产升级的结论。

自己最终重算84文件SHA，`source_changed_since_independent_audit=false`，与root final-code-audit.json的83个现代码SHA逐一比对差异0；aggregateSHA `b9282f55af9d7bd5c54308422166bf2c021c3fe2655b08304fdc9f7fd5da8497`。所有路径/行数/逐文件SHA及关键截图脚本原样归档在review7目录；[证据字节SHA](artifacts/phase8/review7/evidence-sha256.json)。

| 关键源码 | 本轮SHA-256 |
|---|---|
| `globalmail-agent/frontend/src/api/attachment-api.ts` | `fa7f7e8b267c7e9889131872066be8edd2a5c1f7aa8e12daf23c9d405ae4f6cd` |
| `globalmail-agent/frontend/src/components/mail-agent/MessageTimeline.vue` | `fef85f370b7958d23c9eff95db65f04d9fea22167d94a6183d52e14a4d26870f` |
| `globalmail-agent/backend/src/globalmail_agent/application/risk_records.py` | `a9855997e54cf0244fcb9e7c9d3e54699f7cbeaa03fe0e703c3be768155ed3eb` |
| `globalmail-agent/backend/src/globalmail_agent/attachments/corrections.py` | `397597754c222e21160267ba882205fc674b9c7ef48eb83833e561b286ab4ce8` |
| `globalmail-agent/backend/src/globalmail_agent/agent/graph.py` | `0e2ee1d404f1545a5a5e7b2843654569d29e1b6069b6fe11235ac1bcdcaf7c62` |
| `globalmail-agent/backend/migrations/versions/0007_visual_evidence.py` | `c15fc3c367739bd9bf9fef277f4f0f4e6020aabf9bc288a75541945c53edf19d` |

## 交接

本期工程 Stage1/Stage2 均 PASS，无 HIGH、无未关闭 MEDIUM 阻塞，前述延期产品条件保持未验收。自有浏览器 `phase8review7` 已close/delete-data，已通知root不再需要18181/15174；服务/schema/对象目录由root唯一所有者清理，本 reviewer不重复清理共享服务。正式数据库及对象目录未写入。本报告与review7证据交主 Agent收口，未修改需求或代码。
