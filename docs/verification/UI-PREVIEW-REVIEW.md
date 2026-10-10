# UI 交互预览独立审查

日期：2026-10-09。执行者：fresh `code-reviewer`，使用 `.agents/skills/code-review/SKILL.md`，不继承主 Agent 的实现假设。仅审查本次用户授权的预览；未修改程序、未提交 Git、未调用模型、未写正式业务 API。

**最终结论：Stage 1 PASS，Stage 2 PASS。当前无待修 HIGH / MEDIUM。** 初次 Stage 1 的一项 MEDIUM 有实际复现，主 Agent 修复后已从 Stage 1 重新核查；原失败证据保留在下文。

## 输入与审查边界

- 已读根目录 AGENTS、Product-Spec 最新授权段、AGENT-ARCHITECTURE 预览段、DEV-PLAN 预览任务、docs 索引及 SESSION-HANDOFF；已读审查 skill、角色 TOML 和 `docs/planning/UI-PREVIEW-IMPLEMENTATION.md` 全文。
- 基线为 `Product-Spec.md:5`、`AGENT-ARCHITECTURE.md:5`、`DEV-PLAN.md:3` 与实施规划第 9–17 行。用户明确允许假数据，预览不计正式解耦、真实观测采集或 Phase 11–13 验收。
- 无独立设计稿或 `docs/architecture/Design-Brief.md`，按既有 Art Design Pro 外壳及原邮件页面审查。基准：`globalmail-agent/frontend/src/views/index/index.vue:1`、`src/views/mail-agent/index.vue:1`、`src/components/mail-agent/MessageTimeline.vue:1`。
- 审查范围：`globalmail-agent/frontend/src/preview/`、`src/views/ui-preview/`、预览路由与其模式分支、Vite 配置、package scripts、预览启动脚本及 ignore 配套。其他业务代码、已有模型质量与付费运行不在本次范围。
- 以下程序路径均以 `globalmail-agent/frontend/` 为前缀；脚本路径另写全称。最后审查源码中 `src/views/ui-preview/mail/index.vue` 为 236 行，SHA-256 `0C5B93F20061FB30D12899BDEDD371696B2F38F5A8D0EE1DB67860AB9B741ED8`；最后完整构建在该文件修改之后完成。

## Stage 1：Spec Compliance

### 逐项对照

| 授权与验收条目 | 结论与代码证据 | 验证证据 |
|---|---|---|
| 独立 ui-preview 模式、15175 端口，原服务继续运行 | 完整实现。`vite.config.ts:17,33,43,57`；`package.json:11`；`globalmail-agent/scripts/start-ui-preview.ps1:6,16` | 独审实际打开 15175；只读打开 15173 原页面且 API/数据库状态为就绪。主验证记录有两服务 HTTP 结果 |
| 沿用原主布局、侧栏、顶栏、页签与主题 | 完整实现。`src/router/modules/ui-preview.ts:6` 直接加载 `/index/index`；预览未复制外壳 | 原页面与预览均实开截图；1280×720 下侧栏宽、按钮字号/圆角及卡片边框/圆角相同，数值见 Stage 2 |
| 预览只注册专属页面，生产加载器排除预览 | 完整实现。`src/router/modules/index.ts:1`；`src/router/core/ComponentLoader.ts:17`；`src/router/local-tabs.ts:2,11`；`src/router/guards/beforeEach.ts:19` | 独审直接调用 retainLocalTabs 的 preview 分支，只保留 PreviewMail/PreviewRuns；正常产物搜索未命中 demo-mail / demo-run / 预览构造 / ui-preview 页面路径 |
| 只在内存使用演示数据，不调用业务/模型 API，不写数据库 | 完整实现。`src/preview/state.ts:7`；fixtures/steps 只创建对象；邮件及实验室仅修改 demo。`vite.config.ts:18,47,94` 阻断 API 且不代理 | 独审 15175 API 探针 HTTP404，响应正文为内存演示说明。范围内请求/持久化扫描无调用；直接执行状态断言无业务/模型 API |
| 假数据单独放置，不污染生产数据或业务组件状态 | 完整实现。`src/preview/fixtures.ts:14,97`；`src/preview/steps.ts:97`；`src/preview/types.ts:1` 仅类型引用 | 三个客户为 preview.invalid 邮箱，DEMO 订单/SKU；每次 reload/reset 由新 fixture 恢复 |
| 页面持续标记演示，模型记录不冒充真实采集 | 完整实现。各页面第 3 行使用 `src/views/ui-preview/components/PreviewBanner.vue:4`；`NodeDetail.vue:14,18,31,53` | 独审邮件、运行、业务、实验室实际页面均有“交互预览 · 演示数据”；思考有明确构造提示 |
| 三个正常邮件会话与轻量 Agent 状态；邮件页无场景控制/业务面板 | 完整实现。`src/preview/fixtures.ts:14`；`src/views/ui-preview/mail/index.vue:65,75,81` | 初态 Emma/Liam/Olivia 三客户可切换；邮件区域仅状态、邮件正文与人工通信；运行/业务/实验室为独立导航 |
| 正文复用原 MessageTimeline，预览无附件 | 完整实现。`src/views/ui-preview/mail/index.vue:75,113`；`src/preview/fixtures.ts:4` | 原组件渲染纯文本来往；fixture 和演示追加均不含附件，未走 `MessageTimeline.vue:31` 的附件 API 路径 |
| 人工回复、接管及结案只影响当前预览客户 | 完整实现。`src/views/ui-preview/mail/index.vue:188,193,198` | 独审 Liam 人工回复仅新增该客户第三封，切 Emma 草稿/正文独立；结案后发送按钮禁用。主记录另有 Olivia 接管操作 |
| 邮件→运行→业务→原运行节点→邮件准确定位 | 完整实现。mail `:185`；agent `:133,136,139,142`；`NodeDetail.vue:104`；business `:164,174,180` | 独审 Emma→demo-run-01→order→DEMO-1001→demo-run-01/order→demo-mail-01，URL 参数及页面对象逐次匹配 |
| 返回保留会话、草稿、读取位置；多客户草稿隔离 | 完整实现，修后复核。mail `:132,159,163,174,183`；`src/preview/state.ts:11` | 修后 Emma scrollTop0→Liam→Emma0；再邮件→run→邮件仍0，height610/client321。Emma/Liam 两份不同草稿分别恢复；初次缺陷证据见下文 |
| 邮件搜索、状态筛选与空状态 | 完整实现。mail `:11,17,49,139` | 独审搜索 NO_SUCH_CUSTOMER 显示“没有符合筛选的会话”；正文与草稿未被破坏。状态枚举与过滤条件逐项对应 |
| 运行独立入口、搜索/状态筛选/空状态 | 完整实现。`src/router/modules/ui-preview.ts:16`；agent `:8,14,43,114` | 独审 no-run 搜索显示“没有符合筛选的运行”，未改演示数据；状态条件按 run.status 过滤 |
| 节点按运行顺序显示，输入/提示词、思考、输出与工具各自可查看 | 完整实现。agent `:70,88`；`NodeDetail.vue:16,28,51,60`；`src/preview/steps.ts:107` | 独审选择 understand / review / order，实际四个 Tab 与各节点输入、参数、结果相符；模型输入含 system/user/messages/schema；工具有参数与返回结果 |
| 开关思考真实标识，不把摘要冒充实际 reasoning | 完整实现。`src/preview/steps.ts:20,24,172`；`NodeDetail.vue:29,31,44` | understand 显示 enable_thinking=false；review 显示“构造的演示思考内容”与预览构造正文；非模型节点显示不适用 |
| 业务独立只读，订单/库存/物流/售后申请分开查看并关联 | 完整实现。business `:36,63,79,91,117,152` | 实际 DEMO-1001/1002 详情和回执匹配；页面控件只筛选或跳转，无业务修改处理器；主验证记录四 Tab 均已实际查看 |
| 实验室退款事件联动订单回执、新 run、跟进邮件且不重复 | 完整实现。simulation `:44,61,129`；`src/preview/state.ts:25,29,35,44` | 独审重置后推进一次生成唯一 demo-run-04、第三封跟进、退款回执；按钮随后禁用。直接调用第二次返回 unchanged，run/邮件数量不增 |
| 人工处理或已结案时只登记回执 | 完整实现。mail `:189,194,212`；`src/preview/state.ts:33` | 独审人工回复后等待客户期间推进：仍原3个run、原2+人工1封，无自动跟进；已解决后推进：仍2封邮件，无跟进，发送禁用，订单回执可读 |
| 新增客户来信只演示邮件，不宣称模型自动执行；输入必填 | 完整实现。simulation `:83,88,137`；mail `:91,198` | 独审空白人工回复报“请填写回复正文”；空白客户来信报“请填写演示客户来信”。主记录非空客户来信可追加且不生成模型记录 |
| 重置/刷新恢复初态、草稿只跨页内存保留 | 完整实现。`src/preview/state.ts:16`；simulation `:154`；Banner `:5` | 独审重置确认恢复三客户/三run/可推进按钮；直接状态断言恢复 refunded=false、owner=agent、等待业务。浏览器 reload 清除演示草稿 |
| 构建、回归、宽窄明暗与独立审查证据 | 完整实现。`package.json:11`；mail `:218`；agent `:149`；主验证 `UI-PREVIEW-VALIDATION.md:18` | 两模式最终构建均含 vue-tsc；现有回归64/64；独审19断言及实际交互；主记录宽窄尺寸/明暗及截图，独审已打开检查截图 |

### 初次失败与关闭证据

**PREVIEW-001 — MEDIUM，Stage 1，已关闭：同页切换客户时，读取位置被子组件滚到底覆盖。**

初次实际流程：Emma 邮件滚动到 scrollTop=0（scrollHeight=610、clientHeight=321）→Liam→Emma，草稿恢复正确，scrollTop 却变为 289。跨页 run→邮件在该次测试仍能恢复 0；缺陷限定同页客户切换，不将其扩大成所有返回失败。

初次代码为预览 `src/views/ui-preview/mail/index.vue` 的单次 nextTick 恢复，与原 `src/components/mail-agent/MessageTimeline.vue:88` 监听 conversationId 后 `scrollToBottom(true)` 的 nextTick 竞争。主 Agent 仅修改预览恢复函数：当前 mail `:163` 等子组件滚动完成再恢复，原 MessageTimeline 未改。

修后同一独审浏览器重走：Emma0→Liam→Emma0（610/321）；不同客户草稿分别保持；再 run→返回邮件仍0且草稿相同。当前通过，不抹掉初次失败。

主 Agent 同轮另修 owner 屏障及 followup 时间：最终 `src/preview/state.ts:33` 按处理权拒自动跟进，`src/preview/followup-run.ts:35` 使用10:32节点时间。独审分别通过实际人工回复/结案事件分支以及实际 receipt 节点10:32:01；不把这些预置数据记为真实观测。

### Spec 漂移与引导真实性

未发现范围外正式功能。`src/router/modules/ui-preview.ts:32,38` 的知识/系统页面由 `src/views/ui-preview/reference/index.vue:4,28` 保留原导航位置，文案明确“知识维护功能仍以现有正式前端为准”、API未连接/模型未执行，未增加真实维护/调用能力。

人工回复、查看运行、查看关联、演示退款、追加来信、重置均有实际处理器和可见结果；新增来信旁 `simulation/index.vue:88` 明示不生成模型记录，不属于死引导。现有业务API类型及 MessageTimeline 复用不计额外正式功能。

## Stage 2：Code Quality

Stage 1 修后通过才执行本阶段。

| 检查 | 结论与证据 |
|---|---|
| 命名、类型、职责 | PASS。`src/preview/types.ts:3,4,16,30,40` 使用具体接口/联合类型及 unknown；视图、fixture、状态、节点细节分别组织。新范围扫描未命中显式 any；Vue 类型检查已通过 |
| 文件大小 | PASS。15个新增程序文件实数12–276行；最大 `src/preview/steps.ts:1` 276行；邮件236、运行177、业务187、实验室169、NodeDetail110、启动脚本27行。未放宽300行门 |
| 错误处理 | PASS。mail `:199` 和 simulation `:138` 对空白输入拒绝且保留可编辑输入；筛选空状态均有明确文案；simulation `:155` 取消重置不修改状态；独审浏览器 warn/error 日志为 `[]` |
| 测试真实性 | PASS（限定预览）。读取主回归原日志64/64；其测试为已有前端回归，不能单独证明新预览。独审直接导入当前 state/local-tabs 做19断言，正常事件、去重、UI可到达的human+等待客户/human+已解决状态、重置与预览页签均检查；同时实际UI走回复、空白、跳转、读取位置、人工/结案屏障及事件联动。没有用真实模型质量结论替代交互证明 |
| 密钥/注入/危险函数 | PASS（本次变更扫描）。范围内无硬编码Key、eval、innerHTML、SQL拼接、暴露VITE_KEY/SECRET/TOKEN或持久化API调用；`NodeDetail.vue:25,38,57,71,75` 与 MessageTimeline `:30` 为Vue文本插值。MessageTimeline `:56` 导入的附件API在无附件预览数据下不触发；15175 API另有阻断 |
| 本地隔离 | PASS。`vite.config.ts:55,90` 复用127.0.0.1与原localAccess；`globalmail-agent/scripts/start-ui-preview.ps1:11,16,24` 启动子进程不传LLM/GLOBALMAIL环境并恢复当前进程环境，不启动后端；`:17` 使用Hidden |
| 生产/预览配套 | PASS。`vite.config.ts:72` 分dist/dist-ui-preview；`package.json:11` 增专属命令；`.gitignore:4` 忽略预览产物；正常glob排除和预览页签过滤见Stage1；`git diff --check`退出0，仅原换行转换提示 |
| 实际视觉对比 | PASS。独审实际打开15173原邮件页和15175预览并截图，在1280×720读取DOM样式；两页sidebar231px、按钮字体14px/圆角6px、page-content圆角8px/边框rgba(0,0,0,.08)、内容padding0均相同。原外壳 `src/views/index/index.vue:1` 原样复用；列表/正文使用原p-4/边框/主题先例，参照 `src/components/mail-agent/ConversationList.vue:3` 与 MessageTimeline `:26` |
| 明暗及窄屏证据 | PASS（主Agent实际操作＋独审图片复核）。已打开检查 `tmp/ui-preview/agent-desktop.png`、`business-dark.png`、`mail-narrow.png`；运行四Tab/节点、深色业务表、窄屏换行/回复区可读。`UI-PREVIEW-VALIDATION.md:20` 记录1440×900、800×900、414×896及实测scrollWidth；这些尺寸操作由主Agent完成，不冒称独审独立操作 |

## 编译、回归与独审原始输出

主 Agent 最后完整构建日志均晚于最后程序修改；独审读取原文件，未重复完整build。以下为原始输出摘录，完整产物清单位于所列本地日志。

正常构建：`.local-data/runtime/ui-preview-normal-build.log`。

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3360 modules transformed.
dist/assets/index-DIMLX7C0.js                                                       1,373.98 kB │ gzip: 457.50 kB
✓ built in 27.14s
```

预览构建：`.local-data/runtime/ui-preview-build.log`。

```text
$ vue-tsc --noEmit && vite build --mode ui-preview
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for ui-preview...
transforming...
✓ 3360 modules transformed.
dist-ui-preview/assets/index-C_I_Kz1P.js                                              1,328.02 kB │ gzip: 443.26 kB
✓ built in 18.30s
```

前端回归：`.local-data/runtime/ui-preview-tests.log`。

```text
ℹ tests 64
ℹ suites 0
ℹ pass 64
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2813.0518
```

独审以 Node/tsx 导入最终源码执行19断言，退出码0；与实际UI同样使用human处理权，未使用不可达前提替代人工/结案路径。

```text
UI preview independent review: 19 assertions PASS; no business or model API imports
```

独审只读API阻断探针：

```text
HTTP 404
UI preview uses in-memory demo data only
```

## 审查结论与限制

当前授权的内存交互预览可交付，Stage 1/2均PASS。首次读取位置MEDIUM已用相同操作与实际滚动数值复核关闭；当前无待修HIGH/MEDIUM或范围外正式实现。

本报告证明上述预览行为、构建和隔离。`Product-Spec.md:5` 与 `AGENT-ARCHITECTURE.md:5` 明确的真实逐次采集、流式生成、思考持久化、真实邮箱/ERP、模型业务质量及82项AC未由本预览验证；不因此改变原Phase状态。
