# 业务收敛隔离预览最终独立审查

日期：2026-10-09。**最终结论：Stage 1 PASS；Stage 2 PASS。本轮范围无未关闭的 HIGH/MEDIUM。**

本审查使用 [code-review skill](../../.agents/skills/code-review/SKILL.md)，fresh 从 Stage 1 开始。依据是 `Product-Spec.md:5` 的 v1.17 本轮授权及第55/56/62/64/71/72/73行，`AGENT-ARCHITECTURE.md:5`，`DEV-PLAN.md:3`，以及 `docs/planning/UI-PREVIEW-IMPLEMENTATION.md:9` 的五步和第23/25/27/29行修复标准。只验15175的构造前端预览；旧正式后端的申请/资金/履约链路、Phase11–13和82项产品AC不纳入本轮完成声明。

证据分开归属：审查者独立读取全部预览模块、路由/控制桥和相关测试，执行两次82项全量测试、两次vue-tsc、ESLint、内存反例、只读HTTP；另开自有浏览器页，只读检查15175和15173邻居页面、建议、历史节点、JSON及最终筛选。两模式构建、手动采用/确认/发送、新来信交互、明暗/多宽度及截图由主Agent执行，审查者实际读取其原始日志、[验证记录](UI-BUSINESS-SCOPE-PREVIEW-VALIDATION.md)和图片。没有把主Agent操作写成审查者独立点击。

审查期间未写15175控制API，未改15173/18080、数据库、实现代码或Git暂存区，未构建、提交或spawn。仅新增本报告。最后修复后的 `RunHistory.vue` SHA256为 `AFF4D81A287AA559C7E4AE0E9A5D7908C06D21CDB761B6D98F467783675D9762`。

## 历史失败及本轮发现的关闭

[初轮FAIL](UI-BUSINESS-SCOPE-PREVIEW-REVIEW-INITIAL.md)和[二轮FAIL](UI-BUSINESS-SCOPE-PREVIEW-REVIEW-2.md)保留原文、行号和反例。本报告没有改写历史FAIL。

| 问题 | 最终结果 | 关闭证据 |
|---|---|---|
| 初轮S1-H01：普通物流未知仍自动发信 | 已关闭 | `frontend/src/preview/advice.ts:110`依据结构状态登记物流缺口，`run-builder.ts:22`有缺口则内部处理；经交付契约的中文未知/失败/待核实回归 `scripts/ui-preview-evidence.test.ts:32`通过。 |
| 初轮S1-M01：缺订单只能改内部对象，脚本不可达 | 已关闭 | `control-contract.ts:37`及第59行接受严格布尔lookupNotFound，`advice.ts:58`及第67行返回not_found；独立经parsePreviewCommand注入后事实为空。lookupError返回query_failed，未混同两种故障。 |
| 二轮S1-H01：英文未知/否定/旧扫描含delivered或in transit仍误发 | 已关闭 | `types.ts:82`声明shipmentState，`control-contract.ts:45`严格枚举；`behavior.ts:85`仅改补充字符串即强制unknown；`advice.ts:114`及第122行只依据结构状态，`reply-drafts.ts:41`只读“物流状态”事实。三个原英文反例独立复现均新增自动邮件0；显式in_transit/delivered正例各新增1。 |
| 二轮S1-M01：已解决可通过接管隐式重开 | 已关闭 | `views/ui-preview/mail/index.vue:62`禁用闭案接管，第230行使用guard；`behavior.ts:101`拒绝闭案，发送/入站另有第51/26行屏障。独立takeover=false、send=false、incoming=recorded，run增量0；主Agent最终闭案截图支持按钮disabled。 |
| 本轮S2-M01：运行会话状态筛选遗留“等待业务” | 本轮发现并关闭 | 首见 `RunHistory.vue:61`仍为五种状态，含“等待业务”；但 `types.ts:3`只有四种，`behavior.ts:89`业务更新不唤醒run，选项永远无对应记录。主Agent删除后，审查者重新从Stage1复核并重跑82项，重读最终第61行、独立展开真实筛选，只有全部状态/等待客户/待人工接管/人工接管中/已解决。未隐藏首见差异。 |

上表除脚本入口外的源码路径以 `globalmail-agent/frontend/` 为前缀。结构状态是测试数据明确宣告的当前查询快照；补充字符串可以含旧扫描。此修复没有实现真实模型的自由文本物流理解，也不以构造枚举证明承运商事实。

## Stage 1：完整实现逐项对照

下表所有“完整实现”只适用于当前隔离演示。路径默认以 `globalmail-agent/frontend/` 为前缀；GUI证据明确区分来源。

| 本轮要求 | 状态 | 代码位置与实际验证 |
|---|---|---|
| 仅15175、Mock内存、无正式API/数据库/模型 | 完整实现 | `vite.config.ts:18`/34/48/56/92；`src/preview/state.ts:31`；独立GET15175根路径200、/api/v1/conversations 404，唯一预览fetch是 `control-client.ts:20` 的命令GET。 |
| 保留现有Art外壳和邮件视觉 | 完整实现 | `router/modules/ui-preview.ts:6`沿用layout；`views/ui-preview/mail/index.vue:4`/5/91/135使用原卡片、260px会话栏和MessageTimeline；审查者实际打开15173邻居及15175，DOM/截图对照见Stage2。 |
| 产品咨询有适用资料及演示回复 | 完整实现 | `fixtures.ts:44`；`advice.ts:49`给DEMO-FL-01资料/工具来源；`reply-drafts.ts:46`不增加无依据参数；首轮ordinary回归及独立界面会话列表。 |
| 故障排查有订单/型号资料及演示回复 | 完整实现 | `fixtures.ts:5`；`advice.ts:125`用订单SKU检索配对资料；`reply-drafts.ts:49`；`ui-preview-rounds.test.ts:97`确认Emma首轮automatic。危险优先路径另验。 |
| 普通物流有据回复，未知/失败/缺依据转人工 | 完整实现 | `advice.ts:110`/122、`run-builder.ts:22`、`reply-drafts.ts:39`；六个中英文脚本可达反例回归，三个历史失败独立复现及两个结构状态正例，原始结果见下文。 |
| 退款首轮只读、来源/缺口/建议/未发送草稿/HITL | 完整实现 | `advice.ts:85`/90/143、`run-builder.ts:95`、`reply-drafts.ts:14`；`ui-preview-rounds.test.ts:47`检查无Agent邮件、无写工具；独立实际打开Liam建议抽屉。 |
| 退货首轮只读/HITL、Amazon FBA样例 | 完整实现 | `fixtures.ts:29`/31及第115行已有平台请求，无可下载标签；`advice.ts:95`/145，规则/费用需客服核对；四类首轮与未查到记录回归均通过。 |
| 换货首轮只读/HITL、Amazon FBM样例 | 完整实现 | `fixtures.ts:37`/39/121；`advice.ts:99`/102/147核对已有记录与库存，不承诺安排；`reply-drafts.ts:29`；四类首轮及无记录草稿回归通过。 |
| 补寄首轮只读型号/适配/库存/已有记录、客服决定 | 完整实现 | `fixtures.ts:61`/123；`advice.ts:104`/108/149；`step-builders.ts:35`/37；Mia与Emma持续人工回归，适配未确认及未占库缺口保留。 |
| 危险迹象交人工，不凭陈述认定根因 | 完整实现 | `advice.ts:16`/39/46/150；`run-builder.ts:22`/105；`ui-preview-evidence.test.ts:99`使用当前客户原文并检查safety，Olivia初始无自动邮件。 |
| 缺订单/查询失败客服可处理，故障来源可查 | 完整实现 | `control-contract.ts:59`、`advice.ts:58`/67/72、`run-builder.ts:21`；独立契约注入输出分别not_found/query_failed、facts=[]。不要求补齐数据才能接管。 |
| 八客户、七类及危险，初始13run，默认Liam | 完整实现 | `fixtures.ts:3`、`state.ts:16`/18/28；`ui-preview-rounds.test.ts:20`枚举七类、8/13；主Agent最终干净邮件/运行截图显示Liam及三轮。 |
| 四类每封后续客户来信独立internalrun | 完整实现 | `behavior.ts:27`/28/30/35，`run-builder.ts:19`/24；`ui-preview-rounds.test.ts:62`逐四类产生human-assist，自动邮件计数不增。 |
| 客服持续主导，一次人工回复不恢复四类出站 | 完整实现 | `behavior.ts:61`/62、`run-builder.ts:19`/97/98；逐四类人工回复后新来信测试通过，Emma转物流仍persistentHuman；没有解除持续人工或交回Agent按钮。 |
| 普通不确定性HITL保留原恢复例外 | 完整实现 | `behavior.ts:29`、`run-builder.ts:19`/114；`ui-preview-rounds.test.ts:167`验证普通接管期间仅登记、人工回复后下一封恢复automatic；与四类持续人工分开。 |
| Liam三封客户来信、两次人工回复、三run | 完整实现 | `journey.ts:41`/47/56/62；`ui-preview-rounds.test.ts:77`核对5邮件/2人工/3轮及当时退款事实；独立GUI读第2轮只有此前3封上下文，第3轮有5封。 |
| Emma普通排障→补件→物流仍由客服主导 | 完整实现 | `journey.ts:5`/17/23/34，补寄运输显式state在第26行；`ui-preview-rounds.test.ts:97`验证4轮且仅首轮1封Agent邮件。 |
| 每轮保存当时消息/事实、包含此前人工往来、无未来反填 | 完整实现 | `run-builder.ts:10`/32/51/79；`advice.ts:35`建立本轮事实；测试第77/97/110行编辑当前数据不变旧输入。独立GUI第2轮工具仍为处理中、02:45Z；第3轮processed不污染它。 |
| 不创建/取消售后申请、不占资金库存、不执行退款/发货 | 完整实现（预览） | `step-builders.ts:31`仅八个query/search定义；`run-builder.ts:69`/89写入false，第95行仅存建议；四类所有run工具名断言通过。未把正式后端历史写工具算作已关闭。 |
| 业务更新只变可查事实，不产生事件发信/run | 完整实现 | `behavior.ts:81`/85/87/89；`ui-preview-rounds.test.ts:126`检查邮件/run计数不变且建议stale；下一封客户来信才观察新事实。 |
| 事实、来源、查询时间、未知信息、建议与草稿分开 | 完整实现 | `advice.ts:34`/35/37；`AdviceDrawer.vue:17`/26/30/35/37；独立实际抽屉可见Mock独立站来源、11:20时间、银行到账缺口及草稿。 |
| processed不等于银行到账、库存不等于预留、规则未核实不承诺 | 完整实现 | `advice.ts:90`/97/102/108，`reply-drafts.ts:24`，`journey.ts:54`/59；GUI抽屉及四类输出没有执行或到账承诺。 |
| 正常邮件时间线不混内部建议 | 完整实现 | `mail/index.vue:91`/123、`run-builder.ts:95`；四类run.outputMessageId为空、自动邮件0；独立Liam邮件5封与建议抽屉分别可见。 |
| 显式采用、个人草稿替换确认、客服手动发送 | 完整实现 | `AdviceDrawer.vue:47`/49；`mail/index.vue:238`/247/253/261/267；确认之后再查会话/run/时效。主Agent真实采用保持5邮件、取消/确认、手动发送及异步新run保护见验证记录第37–40行；审查者独立检查事件绑定与边界。 |
| 新来信/业务更新/人工回复后旧建议不能直接采用 | 完整实现 | `behavior.ts:87`/92/95；`mail/index.vue:126`/261；`ui-preview-rounds.test.ts:126`/183核对stale及最新客户消息；主Agent确认期间新来信GUI反例。 |
| 手动结案，接管/发送/新来信不能重开 | 完整实现 | `mail/index.vue:62`/66/116/230/233；`behavior.ts:26`/51/101；独立反例和 `ui-preview-evidence.test.ts:70`通过，最终闭案截图仅作为主AgentGUI补证。 |
| 运行概览、会话轮次、执行时间线及节点详情继承 | 完整实现 | `agent/index.vue:16`/34/40/70；`NodeDetail.vue:2`，继承原CSS/主题变量；独立实际看到三轮退款、两栏执行区，并与已批准多轮截图对照。 |
| 全局搜索/筛选会话、默认最新、跨页定位 | 完整实现 | `RunHistory.vue:65`/74、`agent/index.vue:120`/128/134/143，`navigation.ts:14`；独立展开会话抽屉及第2轮/工具导航，URL保留run_id/step_id；邮件返回定位代码第145行。 |
| 历史run/节点不被新记录抢占，有新轮提示 | 完整实现 | `agent/index.vue:57`/99/104/113；`behavior.ts:41`不改viewedRuns；`ui-preview-rounds.test.ts:110`核对历史及他客户不变。审查者看到“第3轮更新，保留第2轮”，主Agent第4轮注入反例见第41行。 |
| system/user提示词、思考摘要、工具参数/结果和完整JSON | 完整实现 | `RequestView.vue:8`/29/34，`NodeDetail.vue:24`/29/50/56，`DataBlock.vue:20`；独立读取role内容、工具结果和展开原JSON，完整source/queried_at/facts一致。 |
| 删除business/simulation页面、节点关联与测试UI | 完整实现 | `router/modules/ui-preview.ts:8`仅四路由；实际目录无两页，预览源码rg无/business、/simulation、PreviewBusiness/PreviewSimulation或等待业务。独立侧栏仅邮件/运行/知识/状态，没有注入/重置控件。 |
| 保留既有知识/状态支撑入口且不扩真实功能 | 完整实现 | `router/modules/ui-preview.ts:22`/28、`reference/index.vue:7`/23/31/33/34；知识明确构造、状态明确未连接API/未执行模型，未提供虚假维护按钮。 |
| 启动清理删除页签与搜索历史，保留有效查询参数 | 完整实现 | `router/local-tabs.ts:2`/5、`guards/beforeEach.ts:19`/20/23；独立local-tabs回归验证有效run/conversation参数保留、旧两页删除，没有在主Agent浏览器改存储。 |
| 脚本/API来信、Mock更新、重置；输入校验/去重 | 完整实现 | `control-contract.ts:18`/23/30/37/45/55/59；`scripts/preview-control.ts:22`/25/33/37/50/58/60；`globalmail-agent/scripts/drive-ui-preview.ps1:10`/20/21。独立随机端口HTTP覆盖403/400/413/200/409/405、reset和重复，未写15175。 |
| GET历史回放/HMR订阅，首屏不漏命令、不抢历史 | 完整实现 | `control-client.ts:18`先订阅，第20行GET历史，第11/37行按序去重，第40行卸载订阅；`behavior.ts:41`仅追加run，历史回归及主Agent新轮GUI证据。 |
| 仅ui-preview开发控制桥；正式模式无预览页面/控制入口 | 完整实现 | `preview-control.ts:11`只serve，`vite.config.ts:92`条件注册，`ComponentLoader.ts:18`/20隔离views，`router/modules/index.ts:4`选择路由；正式dist独立扫描控制标识/删除路由/售后演示标题无匹配，两模式构建成功。 |
| 所有run/提示词/思考/指标明确构造，不冒充真实质量/CoT/权限改造 | 完整实现 | `PreviewBanner.vue:4`/5、`step-builders.ts:4`、`run-builder.ts:43`/81、`agent/index.vue:44`、`NodeDetail.vue:21`/29、`reference/index.vue:33`/34；独立页面读取与最终截图支持。 |
| 全量回归、两模式编译、明暗窄屏点击、两阶段审查、不Git提交 | 完整实现（本轮） | 独立最终82/82、vue-tsc/新增修改模块lint exit0；主Agent最终两模式日志及GUI见下文；本报告完成两Stage。只读git diff --cached --stat为空，未暂存/commit。 |

**部分实现：本轮范围无。未实现：本轮范围无。** 正式后端收敛、真实Agent/邮件/ERP、持续人工解除条件及数据中心未来CRUD按源文档留后续，不能用上述PASS替代它们的验收。

## Stage 2：代码质量、测试真实性、安全和视觉

| 审查项 | 结论 | 证据 |
|---|---|---|
| 命名、类型、结构、大小 | 通过本轮范围 | `types.ts:19`及第28/59/74行分别定义建议/会话/run/订单；behavior、advice、run-builder、control-contract和展示组件职责分开。逐文件计数最大 `mail/index.vue:290`，其次测试231、agent193，均≤300；对新增preview/views/control/router的类型any、ts-ignore/nocheck、eslint-disable扫描无匹配。 |
| 既有类型边界 | 保留基线限制 | `router/core/ComponentLoader.ts:13`/26/51/58/65/77仍有模板原有Promise<any>，git diff仅改第18–20行glob；不能宣称全仓无any。这不是本轮新增类型退化。 |
| 错误处理与异步草稿 | 通过 | `preview-control.ts:66`非法JSON400、输入/超限/来源分别校验；`control-client.ts:33`静态浏览降级，`mail/index.vue:257`取消保留草稿、第261行二次核对会话/run/时效；`behavior.ts:51`/101双门禁。手动确认/发送由主Agent真实GUI补证，不仅凭纯函数测试。 |
| 测试输入真实性 | 通过本轮范围 | `ui-preview-evidence.test.ts:15`/44真实调用交付parsePreviewCommand；六条未知物流均是非空≤1000的可达字符串，断言owner/mode/邮件计数/缺口；第59行显式in_transit为对照。独立额外delivered正例证明并非一律拒发。旧直接改orderId的测试第145行只算底层补充，缺订单可达性由新契约用例及独立输出证明。 |
| 状态/历史/权限真实性 | 通过 | `ui-preview-rounds.test.ts:62`逐四类复用实际人工往来；第91行修改真实当前数据检查旧输入；第126行同时检查run/邮件不增；`ui-preview-evidence.test.ts:75`直接调用页面使用的takeoverConversation而非假guard。页面disabled由第62行与主AgentGUI补证。 |
| HTTP故障与清理 | 通过 | `preview-control.test.ts:11`真正启动自有Vite随机端口，第38/48/49/50/54/63/67行验证拒绝、超限、成功、冲突、重置及405；finally第69–72行关服并核对临时路径。测试不调用15175/正式API。 |
| 测试边界 | 明确限制 | Node套件不等于已挂载Vue的端到端回归；草稿替换确认、当前run变化及手动发送采用主AgentGUI证据。审查者独立GUI只读复核抽屉、历史、JSON与筛选，不宣称复验全部交互。 |
| 硬编码密钥、危险执行和注入 | 本轮扫描未发现 | 对preview、views、控制桥、驱动/启动脚本扫描eval、innerHTML/v-html/dangerouslySetInnerHTML、VITE秘密前缀、密钥样式、密码及用户绝对路径均无匹配；`RequestView.vue:19`、`DataBlock.vue:12`/22和 `AdviceDrawer.vue:38`均Vue文本插值；无SQL拼接或命令执行器，脚本第20行JSON编码。 |
| 控制接口安全边界 | 通过本机演示契约 | `vite.config.ts:47`/56禁跨域、仅127.0.0.1；`preview-control.ts:22`/25要求header/允许Origin，第33行64KB，第50行ID去重/冲突，第58行500命令上限；`control-contract.ts:23`/30限制demo资源、白名单拒绝额外写字段和无效枚举。该本地脚本桥不作为生产鉴权设计。 |
| Spec漂移 | 无新增未授权功能 | `router/modules/ui-preview.ts:8`仅四页，`control-contract.ts:3`仅reset/incoming/business_update，`step-builders.ts:31`只读工具；售后写工具、业务事件发信、ERP/CRUD或解除人工模式均未新增。遗留“等待业务”辅助选项本轮已关闭。 |
| 邻居实际渲染对照 | 通过继承标准 | 审查者实际打开15173/#/workbench和15175运行/邮件页并截图、只读DOM量测；两页卡片radius=8px、主色=#5D87FF、同一ui-sans-serif/system-ui/emoji字体栈。原 `views/mail-agent/index.vue:6`/11与新 `mail/index.vue:4`/5均page-content/260px会话栏；全局 `assets/styles/core/el-ui.scss:13`为36px标准控件。最终两张浅色图与已批准multiround-desktop.png对照，运行概览→轮次→两栏时间线/详情顺序、按钮/主题/卡片风格保持。 |
| 响应式与主题 | 通过所列实测 | 审查者1280视口实际DOM：预览和邻居documentWidth=1280；运行卡片深色rgb(22,22,24)，邻居浅色rgb(255,255,255)，共同主题变量/字体/圆角一致。主Agent另实测1440/1280/800/414，DOM宽度≤视口并切换明暗；源码 `mail/index.vue:276`、`agent/index.vue:176`/185、`ConversationRounds.vue:68`有对应折叠。 |

调用方式另与 [Vite官方server→client事件文档](https://vite.dev/guide/api-plugin#client-server-communication)及 [unplugin-auto-import官方custom imports配置](https://github.com/unplugin/unplugin-auto-import#configuration)核对：`preview-control.ts:64`/`control-client.ts:18`使用有前缀的自定义事件，`vite.config.ts:115`显式保留既有ElMessage/ElLoading导入。外部文档仅验证调用方式，实际能否编译/处理HTTP由本地证据判断。

安全扫描结论只覆盖列明路径和模式，不把“未发现”写成全产品安全保证。主Agent高DPI截图存在右侧截取误差；图片仅证明其可见布局，不能独立证明完整视口或像素逐点相等。1280无文档横向溢出使用审查者DOM测量，其他宽度使用主AgentDOM实测与源码，来源不混。

## 独立反例原始结果

以下在自有Node/tsx进程创建新state，business_update先经过交付parsePreviewCommand，再updateMockOrder及appendToState；未向15175写事件。三个字符串与第二轮失败原文相同。

```json
{"shipment":"Delivery status unknown; last stored scan was delivered","contractAccepted":true,"state":"unknown","result":"assisted","mode":"handoff","owner":"human","added":0,"unknowns":["物流工具未提供可核实的当前状态，需客服核对承运商记录"]}
{"shipment":"query_failed: previous cached status in transit","contractAccepted":true,"state":"unknown","result":"assisted","mode":"handoff","owner":"human","added":0,"unknowns":["物流工具未提供可核实的当前状态，需客服核对承运商记录"]}
{"shipment":"Not delivered; current carrier status unknown","contractAccepted":true,"state":"unknown","result":"assisted","mode":"handoff","owner":"human","added":0,"unknowns":["物流工具未提供可核实的当前状态，需客服核对承运商记录"]}
{"shipmentState":"in_transit","contractAccepted":true,"result":"automatic","owner":"agent","added":1,"reply":"Hi Sophia,\n\nThe latest shipping record shows that your parcel is in transit. An exact delivery date has not been confirmed.\n\nBest regards,\nCustomer Support"}
{"shipmentState":"delivered","contractAccepted":true,"result":"automatic","owner":"agent","added":1,"reply":"Hi Sophia,\n\nThe latest tracking record shows a delivered scan. Please let us know if you have not received the parcel so our support team can check further.\n\nBest regards,\nCustomer Support"}
{"field":"lookupNotFound","contractAccepted":true,"tool":{"source":"Mock · 订单接口","status":"not_found","queried_at":"2026-10-09T02:19:00.000Z"},"facts":[]}
{"field":"lookupError","contractAccepted":true,"tool":{"source":"Mock · 订单接口","status":"query_failed","queried_at":"2026-10-09T02:19:00.000Z"},"facts":[]}
{"closedTakeover":false,"closedSend":false,"incoming":"recorded","status":"已解决","runsAdded":0,"messagesAdded":1}
```

## 测试、编译及原始输出

审查者在frontend独立执行 `pnpm test`，初次82/82（2788.58ms），筛选修复后再次执行退出码0，最终原始汇总：

```text
$ tsx --test scripts/*.test.ts
ℹ tests 82
ℹ suites 0
ℹ pass 82
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2936.5855
```

两次独立 `pnpm exec vue-tsc --noEmit` 均退出码0、stdout为空。独立ESLint覆盖新增preview/views、预览和模式路由、local-tabs、ComponentLoader、vite.config、控制/预览/local-tabs测试，退出码0、stdout为空。

扩展lint到既有beforeEach整文件时退出码1，原始输出保留：

```text
D:\Work_Project\globalmail-agent\globalmail-agent\frontend\src\router\guards\beforeEach.ts
  40:34  error  '_delay' is defined but never used  @typescript-eslint/no-unused-vars

✖ 1 problem (1 error, 0 warnings)
```

`git diff`确认该第40行未改，本轮仅第19/20/23行页签/历史过滤；不把基线lint问题写成本轮新增缺陷，也不声明全仓lint通过。测试还保留既有知识模块Vue生命周期警告，例如：

```text
[Vue warn]: onUnmounted is called when there is no active component instance to be associated with. Lifecycle injection APIs can only be used during execution of setup(). If you are using async setup(), make sure to register lifecycle hooks before the first await statement.
```

两模式最终构建由主Agent执行，审查者读取最终原始文件，未并行启动新build。[production日志](../../tmp/ui-preview/business-scope-production-build.log)首尾原文摘录：

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3380 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 30.51s
```

[ui-preview日志](../../tmp/ui-preview/business-scope-preview-build.log)首尾原文摘录：

```text
$ vue-tsc --noEmit && vite build --mode ui-preview
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for ui-preview...
transforming...
✓ 3380 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 19.37s
```

两构建包含vue-tsc；成功摘录不等于零警告，既有Sass警告留在完整日志。主Agent最终全量测试原始[日志](../../tmp/ui-preview/business-scope-tests.log)是82/82/0fail/0skip、3043.5014ms，与审查者独立执行数值分开。

独立只读HTTP原始输出：

```text
GET http://127.0.0.1:15175/ => 200
GET http://127.0.0.1:15175/api/v1/conversations => 404
UI preview uses in-memory demo data only
GET http://127.0.0.1:15175/__ui_preview__/events => 200
scope=ui-preview-memory-only events=1
```

主Agent[健康证据](../../tmp/ui-preview/business-scope-ready.json)另显示15173和18080的 `/api/v1/health/ready` 为200，15175为404；正式15173控制路径的200 SPA HTML不能作为控制API可用证明。

## GUI证据与交付限制

审查者独立实际检查：Liam邮件5封、建议抽屉的事实/来源/缺口/草稿；运行最新第3轮system/user及此前人工往来；第2轮→query_refund_records→工具调用→结果JSON展开，仍显示“处理中”和2026-10-09T02:45:00.000Z；第3轮更新提示未改历史节点；最后状态筛选的四个真实选项。邻居工作台只读GET并实际渲染，未创建正式会话或执行业务动作。

主Agent真实点击证据见 [验证记录](UI-BUSINESS-SCOPE-PREVIEW-VALIDATION.md:35)。审查者实际查看 [最终干净邮件](../../tmp/ui-preview/business-scope-final-mail.jpg)、[最终干净运行台](../../tmp/ui-preview/business-scope-final-agent.jpg)、[最终闭案](../../tmp/ui-preview/business-scope-closed.jpg)、[英文未知深色](../../tmp/ui-preview/business-scope-english-unknown-dark.jpg)、[414布局](../../tmp/ui-preview/business-scope-414.jpg)及既有 `multiround-desktop.png`。最终两图用于8客户/13run交付状态与外观，早期第4轮截图仅用于历史/新轮交互，不混作初始13run样例。

本次PASS只表示已授权的可点击构造预览满足所列业务/交互边界。不能证明真实模型业务质量、真实CoT、正式后台权限精简、真实业务数据/ERP/支付/邮箱接入或82项产品AC通过；持续人工解除条件、正式后端精简和未来工具数据CRUD仍按源文档另行对齐。
