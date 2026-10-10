# Agent 运行台预览视觉重设计独立审查

日期：2026-10-09。执行者：fresh `code-reviewer`，按 [code-review skill](../../.agents/skills/code-review/SKILL.md) 做两阶段审查。仅写本报告，未改代码、未暂存/提交 Git、未调用模型、真实邮件或生产写入 API。

**结论：Stage 1 PASS；Stage 2 PASS。无待修 HIGH / MEDIUM。** 结论限于本轮 15175 内存交互预览的视觉重设计，不代表正式解耦、逐次观测采集、模型业务质量或 82 项产品 AC 通过。

## 审查输入和证据边界

- 消费根目录 AGENTS、Product-Spec 当前授权段、AGENT-ARCHITECTURE 预览契约、DEV-PLAN 当前任务、docs 索引与交接当前部分；精确验收为 [UI-PREVIEW-IMPLEMENTATION.md](../planning/UI-PREVIEW-IMPLEMENTATION.md):13–18 的四项视觉迭代要求。根契约入口为 `Product-Spec.md:5`、`AGENT-ARCHITECTURE.md:5`、`DEV-PLAN.md:3`。
- 无新设计稿或 Design Brief，基准为原 Art 外壳及 15173 邮件工作台。旧 [UI-PREVIEW-REVIEW.md](UI-PREVIEW-REVIEW.md) / [UI-PREVIEW-VALIDATION.md](UI-PREVIEW-VALIDATION.md) 只作首次版本历史。
- 本轮程序范围为下列七文件；状态/fixture、邮件/业务/实验室及隔离入口作为回归依赖读取。以下 `src/` 路径均相对 `globalmail-agent/frontend/`。
- 独审使用 CUA 新建自己的预览 tab 和原页面基准 tab，未操作主 Agent tab、未改全局 viewport。独审 tab 实际常规 viewport 为 **1920×911**；1440/1280/800/414 的 DOM 数值由主 Agent 实测并记入 [本轮验证](AGENT-RUN-PREVIEW-REDESIGN-VALIDATION.md):46–51，五张本轮截图已逐张实际打开复核。两模式构建和 64 项回归由主 Agent 执行，独审读取原始日志核对，不冒称独立重跑。

| 最后核对文件 | 行数 | SHA-256 |
|---|---:|---|
| `src/preview/presentation.ts:1` | 100 | `5C66E8E01FB59A8A1B7D94A508C4A6F6C2A89D454C3B8E4A951916D927F745F9` |
| `src/views/ui-preview/agent/index.vue:1` | 126 | `8CF6EDA0FC9179011B867AFD0001AA6602973BF1AB79B5E82417741FAAE29366` |
| `src/views/ui-preview/components/NodeDetail.vue:1` | 157 | `98DDA48C0B173DA9EFDB40BC9B1AA4AE55F65990A9FDCE7D1E76100D9A8CB9C6` |
| `src/views/ui-preview/components/DataBlock.vue:1` | 72 | `131C36B88FDE5CCEE61E781A65B53B5D99048F33CF387A58F471D5FE63E34A04` |
| `src/views/ui-preview/components/RequestView.vue:1` | 91 | `CFEA83C8607132F51E4EB6141C2408FA6E5F373849AB031FEF5E9980E6A79B8D` |
| `src/views/ui-preview/components/ExecutionFeed.vue:1` | 139 | `E4D4E879B55C3DB2CE4A4395CCD6EC1661D9205D56D6CE9EB1DB716382423258` |
| `src/views/ui-preview/components/RunHistory.vue:1` | 85 | `A16609760C497A7043AF716FD9F39B69727AC8AF3F05771A2C13C73616F941E3` |

七文件在独审初次记录和结束前再次计算的 SHA 一致，NodeDetail 最终文案“正式接入时读取供应商 reasoning_content”已在源码 `:30` 和独审实际思考 Tab 中确认。

## Stage 1：Spec Compliance

### 完整实现

| 验收项及子要求 | 代码证据 | 独审实际验证 / 复核证据 |
|---|---|---|
| 1：运行历史收入面板，可搜索、筛选、切换及显示空结果 | `RunHistory.vue:7,9,10,17,33,49,58` | 搜索 `no-such-run` 显示“没有符合筛选的运行”；搜索 `LIAM` 只显示 Liam；筛选“待人工接管”只显示 Olivia；Enter 选择后 URL 为 `run_id=demo-run-03` 且概览/节点更新 |
| 1：概览含客户、触发、结果状态、耗时和用量 | `agent/index.vue:14,20,22,29,65`；`presentation.ts:84` | run01 为 Emma/等待客户/3模型2工具/3842 Tokens；run02 为 Liam/等待业务/2模型3工具/4216 Tokens；run03 为 Olivia/待人工接管/1模型0工具/968 Tokens；事件生成 run04 后显示“退款回执与客户跟进”、1模型1工具/1560 Tokens，未把历史申请状态改成执行成功 |
| 1：主体两栏，时间线按顺序显示且说明有足够宽度 | `agent/index.vue:38,102,109`；`ExecutionFeed.vue:10,22,26,63` | 独审桌面两栏宽 `716.922/916.078px`，时间线与详情各自滚动；run01 7节点、run02 6节点、run03 2节点、run04 3节点与 fixture 顺序一致；1440/1280截图两栏，800/414截图单栏 |
| 2：默认提示词按角色分段，参数可读 | `RequestView.vue:8,19,24,46,54,63`；`DataBlock.vue:4,12,33` | run01/review 默认显示系统提示词和用户上下文两个独立块，参数显示 qwen3.7-plus、启用思考“是”、预算2048、温度0.7；tool 角色映射及内容转换由 `RequestView.vue:46–60` 静态核对，现有 fixture 只有 system/user，未冒称浏览器实测了 tool 消息角色 |
| 2：原始请求/参数/输出完整可展开 | `RequestView.vue:29,34,36`；`DataBlock.vue:20,22`；`presentation.ts:20` | Enter 展开完整请求，实际文本含 model、enable_thinking、thinking_budget、temperature、完整 system/user messages 和工具 function/properties/required；输出展开保留 `passed=true`、`unsupported_claims=[]`、`next_state=waiting_customer`；未用摘要替换请求，折叠初态正常 |
| 2：可读结构化结果及工具参数/返回保持 | `NodeDetail.vue:50,56,73`；`DataBlock.vue:4`；`presentation.ts:29,81` | review 输出字段含中文标签、原字段名和值；order 工具显示 DEMO-1001、verified/brand/sku/item/paid 全部五个返回字段。参数与结果分别有自己的原始 JSON 折叠 |
| 2：构造思考标识、未启用与非模型空态 | `NodeDetail.vue:27,29,30,39,42,44` | run01/review 有“演示思考 · 构造内容”、完整预览构造正文与未来接入说明；run03/understand 显示“本次调用未启用思考”和 enable_thinking=false；run03/risk 显示“此节点没有模型思考” |
| 2：工具/非工具关联入口真实 | `NodeDetail.vue:57,64,78,98`；`agent/index.vue:76` | order 工具能进入关联业务；未执行工具的模型节点使用空态。关联处理器带实际 DEMO 订单、run_id、step_id，没有指向未实现能力的点击引导 |
| 3：切运行、选节点、Tab、折叠及深链接同步 | `agent/index.vue:56,62,67,70`；`ExecutionFeed.vue:19,51`；`NodeDetail.vue:24,97` | Enter 切 run03、选择 risk；直接进入 run01/review 显示正确节点并滚入时间线；依次检查输入/思考/输出/工具；选 order 后 URL、aria-current=step 与详情一致，切节点默认回输入 Tab |
| 3：邮件→run→工具→业务→原节点→邮件，草稿保留 | `mail/index.vue:132,185`；`agent/index.vue:70,73`；`NodeDetail.vue:98`；`business/index.vue:180` | Emma 输入 `独审保留草稿 across pages` → 本轮run01 → order工具 → 业务URL `order_id=DEMO-1001&run_id=demo-run-01&step_id=order` → 返回原order节点 → 返回demo-mail-01，草稿实际AX值逐字保留 |
| 3：演示事件/人工屏障不回退 | `src/preview/state.ts:25,33,35,44`；`mail/index.vue:188`；`simulation/index.vue:129,154` | Liam人工接管后推进退款：提示“人工接管期间不自动跟进”，仍3个run、原demo-run-02和两封邮件；重置再正常推进一次产生run04、历史4与后续运行概览，推进按钮禁用；操作均在独审15175 tab内存 |
| 4：宽窄、长文本、明暗、键盘焦点 | `agent/index.vue:102,109,118`；`ExecutionFeed.vue:119,129`；`RunHistory.vue:7,81`；`DataBlock.vue:51,67`；`RequestView.vue:79` | 响应式复核见下表；独审实开原/新页明暗主题；order按钮Enter后 computed outline=`rgb(93,135,255) solid 2px`、offset=2px，aria-current=step；JSON折叠支持Enter。独审桌面document clientWidth/scrollWidth=1920/1920 |
| 4：64项、两构建、fresh独审；交付截图与地址 | `package.json:12,13,14`；[本轮验证](AGENT-RUN-PREVIEW-REDESIGN-VALIDATION.md):15–23,55–59 | 已复核本轮原始日志64/64及两构建末尾PASS；本报告为fresh独审。桌面/深色/三响应式截图实际打开；15175预览地址实际可打开。向用户展示截图和地址由主 Agent 最终交付，不冒称用户已确认视觉满意 |

### 响应式证据复核

以下尺寸是主 Agent 实测，独审没有重复改全局 viewport；独审实际打开对应本轮 PNG 并对照上述断点与换行源码。原始位置见 [本轮验证](AGENT-RUN-PREVIEW-REDESIGN-VALIDATION.md):46–51。

| viewport | 布局 / 文档宽度 | 长 JSON / 历史面板 |
|---|---|---|
| 1440×900 | 两栏，documentWidth1440，main client/scrollHeight900/900 | 桌面默认角色块截图完整，面板内滚动 |
| 1280×900 | 两栏435.938/557.062px，documentWidth1280 | raw client/scrollWidth507/507 |
| 800×900 | 单栏752px，documentWidth792 | raw710/710 |
| 414×896 | 单栏376px，documentWidth406 | raw342/342，历史Drawer宽414/left0/scrollWidth414 |

800/414截图已核侧栏折叠稳定态；长英文主题、工具名和 JSON 留在可滚动/换行容器内，没有文档级横向溢出。截图为 `tmp/ui-preview/agent-redesign-{desktop,dark-tools,1280,800,414}.png`。

### 未实现、部分实现、Spec 漂移

本轮四项的软件实现没有未实现/部分实现项。未发现新增业务页面、API、数据表、模型调用或视觉依赖超出授权。`presentation.ts:15–27,84–100` 为只读展示转换，七文件只读取 props/demo 或进行预览路由跳转，没有回写输入或扩展业务动作。用户视觉确认仍由用户看新版后给出，不由审查报告代替。

隔离边界独立复核：`vite.config.ts:17–24,33,47,94` 阻断/不代理API；`ComponentLoader.ts:18–20` 分模式加载；`router/modules/index.ts:4` 选择预览路由。实际只读探针原始输出：

```text
HTTP 404 UI preview uses in-memory demo data only
normal-bundle-preview-match-count=0
```

后者针对正常 `dist/assets` 搜索 demo-run-01、构造思考正文、新运行台说明及 ui-preview/agent，未命中。15173原邮件页独审实际打开，页面显示API可访问、数据库/数据结构/对象存储就绪；没有点击任何生产业务动作。

## Stage 2：Code Quality

| 检查 | 结论和证据 |
|---|---|
| 类型、命名、职责与文件大小 | PASS。`presentation.ts:1,15`、`NodeDetail.vue:95`、`DataBlock.vue:30`、`ExecutionFeed.vue:48` 使用明确 props、DemoStep/unknown/Record；七文件 `any` 扫描无命中，最大157行。数据展示、请求阅读、时间线、历史和路由协调拆分；模型请求原件由只读 props保留 |
| 安全扫描 | PASS，限七文件。eval、innerHTML、dangerouslySetInnerHTML、v-html、密钥前缀/变量、password赋值、绝对用户路径、字符串SQL、fetch/axios、local/sessionStorage扫描无命中。文本用Vue插值（`DataBlock.vue:12,22`、`RequestView.vue:19,31,36`），没有执行请求/结果内容。未读/打印env或凭据 |
| 测试真实性 | PASS于本轮范围。64项是既有正式工作台/composable回归，不能证明新组件渲染；抽查 `scripts/agent-run.test.ts:31` 起的晚到响应/权限/错误恢复及 `scripts/local-tabs.test.ts:5` 的真实输入与断言。新展示层通过上表实际浏览器核心/空态/键盘/跨页/屏障检查补证；没有把纯函数回归冒称完整UI测试 |
| 自动化覆盖边界 | 本轮七展示文件没有新增挂载型UI自动测试，tool角色消息在现有fixture不可达。已在Stage1明确静态验证和实际验证的区别；这不影响已实际验证的隔离视觉预览，也不扩称真实后台/流式/思考采集测试 |
| 工程/源码稳定性 | PASS。主Agent七文件ESLint exit0无输出（[验证](AGENT-RUN-PREVIEW-REDESIGN-VALIDATION.md):20）；独审 `git diff --check` exit0，仅LF/CRLF提示。结束前七文件SHA与首次记录一致。独审 `git diff --cached --name-only`无输出，没有暂存/提交 |
| 运行时错误 | PASS。独审覆盖上述所有流程后 CUA `reviewTab.dev.logs({levels:['warn','error']})` 返回 `[]`。未将过渡中的AX旧快照当作应用错误，后续DOM/URL/字段已确认落定 |

### 原页面实际视觉对比

独审实际打开 **15173/#/workbench** 与新15175运行台，分别查看明/暗渲染；不是仅数复用了多少组件。基准源码为 `src/views/mail-agent/index.vue:6`、`src/components/mail-agent/ConversationList.vue:37–38`、`src/assets/styles/core/app.scss:85`，新页为 `agent/index.vue:14,26,39`、`NodeDetail.vue:2`。

| 渲染指标 | 原邮件工作台 | 新运行台 | 结论 |
|---|---|---|---|
| 同类普通ElButton：原“导入案例”/新“返回邮件” | 14px、height36、padding8px 15px、radius6px | 数值相同 | 匹配 |
| 按钮字体 | ui-sans-serif/system-ui及现有系统emoji回退 | 数值相同 | 匹配，无新字体 |
| page-content明色卡片 | rgb(255,255,255)、边框rgba(0,0,0,.08)、radius8px | 数值相同 | 匹配 |
| page-content暗色卡片 | rgb(22,22,24)、边框rgba(255,255,255,.08)、radius8px、文字rgb(255,255,255) | 数值相同 | 匹配 |
| 外壳、卡片间距与主题变体 | 原侧栏/顶栏/页签及El主题 | 同一外壳，主体gap16px、内边距20px，新节点有选中态和角色层级 | 符合本轮重设计且继承既有体系 |

按钮数值由独审DOM computed style读取；明/暗卡片数值也独立读取。两tab主题验证后均恢复初始明色（documentElement.className为空），测试tab没有保留用户交付标记。

## 编译与回归原始输出

本节来自主Agent当次日志，独审已读取原文并核对，不是摘要推算。完整日志位于 `.local-data/runtime/`，主Agent验证记录给出退出0；下面保留命令/汇总/构建末行的原始片段。

`agent-redesign-tests.log`：

```text
ℹ tests 64
ℹ suites 0
ℹ pass 64
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2852.9602
```

`agent-redesign-normal-build.log`：

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3374 modules transformed.
rendering chunks...
✓ built in 26.22s
```

`agent-redesign-preview-build.log`：

```text
$ vue-tsc --noEmit && vite build --mode ui-preview
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for ui-preview...
transforming...
✓ 3374 modules transformed.
rendering chunks...
✓ built in 17.85s
```

没有待修HIGH/MEDIUM或暂停Stage。可由主Agent向用户交付新版截图和可点击15175地址；用户“先不要Git提交”的限制继续生效。
