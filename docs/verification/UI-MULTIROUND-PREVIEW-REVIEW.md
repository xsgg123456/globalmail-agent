# 多轮会话前端预览独立审查

日期：2026-10-09。执行者：fresh code-reviewer，按 [code-review skill](../../.agents/skills/code-review/SKILL.md) 完成两阶段审查。只写本报告，未改应用或其他文档，未暂存/提交 Git，未读或打印 env/密钥，未调用模型、真实邮件或生产写入 API。

**最终结论：Stage 1 PASS；Stage 2 PASS。本轮发现的展示缺口已由主 Agent 修复并独立复核；无待修 HIGH / MEDIUM。** 结论仅适用于15175浏览器内存多轮预览，不表示正式解耦、真实Agent执行/观测或82项产品AC通过。

## 范围、规划及证据归属

精确基线为 `Product-Spec.md:5,7`、`AGENT-ARCHITECTURE.md:5`、`DEV-PLAN.md:3` 与 [实施规划](../planning/UI-PREVIEW-IMPLEMENTATION.md):7–20 的四步及业务展示补充。已读 AGENTS、技能、上述原文、docs索引和当前handoff；旧运行台重设计报告仅作视觉历史。无新Brief/设计稿，继承Art/Element体系。

审查顺序：逐条需求及隔离边界 → 数据快照/导航/可达屏障 → 独立浏览器核心与故障路径 → Stage 1缺口修后重核 → Stage 2质量、安全、测试前提与实际邻居视觉 → 最终日志与源码核对。下文 `src/`、`scripts/`、`vite.config.ts` 和 `package.json` 路径均相对 `globalmail-agent/frontend/`；`agent/`、`mail/`、`simulation/`、`business/` 及 `components/` 的页面短路径均位于 `src/views/ui-preview/`，`journey.ts`、`state.ts` 等模块短名均位于 `src/preview/`。

- 独审独立执行：末次新增6项测试、补充内存断言、15175自建CUA tab实际点击/键盘/DOM数值、404探针、安全扫描及正常bundle隔离搜索。未操作主Agent tab或改变全局viewport/主题。
- 主Agent执行、独审复核原文：最终70项（原64+新6）、两模式构建、Lint、1440/1280/800/414响应式数值。五张本轮PNG已由独审逐张实际打开，未将主Agent测试冒称独立重跑。
- 独审自建15173系统状态tab只用于读取邻居视觉，没有操作正式邮件或业务；已关闭。独审自己的预览tab最终重置回Emma三封来信/四轮，未留下测试新增数据。

## Stage 1：Spec Compliance

### 完整实现

| 验收项及子要求 | 代码证据 | 独审证据 / 主Agent证据复核 |
|---|---|---|
| 1：会话内多run、稳定round/title/触发与回复关联 | `src/preview/types.ts:30`、`steps.ts:7,98,160`、`journey.ts:65,113,174`；`presentation.ts:84` | 独立测试核对Emma轮次[1,2,3,4]、3封客户来信/7封总邮件，触发id为客户、输出id为simulated_agent，Liam仍单轮；浏览器同一会话四卡按顺序展示 |
| 1：三封客户来信+一次发货回执组成四轮 | `journey.ts:26,42,57,173`、`state.ts:8` | 初始模型顺序为排障→补发核验→客户确认/申请→发货回执跟进；run01旧链接保留；第4轮业务事件无触发来信时定位output邮件，不编造客户来信id |
| 1：每轮输入独立，只含当时可见消息 | `journey.ts:5,34,49,57,83,129,198`、`incoming-run.ts:14,40,47`、`followup-run.ts:36` | 独立补充断言将所有第2/3/4轮model上下文逐一解析，与原邮件seq1–3/1–5/1–6精确deepEqual；新理解节点排除候选回复，核验节点合法保留draft；新增run input含新来信但无未提交outputMessageId |
| 1：历史无未来回执、旧记录不可倒改 | `step-builders.ts:29`、`state.ts:84`；`scripts/ui-preview-rounds.test.ts:41,64,116` | 独立测试第1/2/3轮无后续消息/SHIP/TRACK，修改当前邮件body后第2轮input不变；追加/退款后旧run JSON逐字不变，其他会话run数不变。当前业务账本状态不回填模型输入 |
| 1：重置及刷新恢复预置，清除内存选择/草稿/阅读位置 | `state.ts:29`、`simulation/index.vue:176` | 独立测试reset回6run、viewedRuns清空；浏览器在真实追加来信后确认重置，再查看运行实际恢复Emma3封/4轮/latest run01-04；reload同样去除测试数据且旧run01/order仍有效 |
| 2：全局按会话搜索/状态筛选，显示轮数 | `components/RunHistory.vue:7,12,29,43,48,65` | 独审搜索无匹配显示明确空态；按demo-mail-02 ID只得Liam，Enter选择URL明确conversation_id=demo-mail-02&run_id=demo-run-02；清搜索、筛等待业务只列Liam。筛选读取mail.status而不是历史run.status |
| 2：会话内轮次、标题、触发、时间、当轮结果/最新标识 | `components/ConversationRounds.vue:10,21,25,27,29`；`agent/index.vue:36,42` | 四卡显示1–4、10:12/10:35/11:00/11:15、三封客户来信/一次补发事件，第三轮等待业务、第四轮等待客户；Enter切第3轮后URL与aria-current=true一致 |
| 2：默认最新、深链接指定轮、全局切会话最新、重入会话记忆 | `navigation.ts:3,8`、`agent/index.vue:90,96,110,117` | 空内存初进Emma选4；独立测试显式run01选1、跨会话run拒绝串用、remembered选2；浏览器“全部5轮”无run_id入口实际恢复第2轮，“查看最新运行”明确run_id选第5轮。旧run01/order深链接实际落第1轮order |
| 2：当前会话状态与历史结果分开 | `agent/index.vue:23,44`、`RunHistory.vue:39,68` | Liam经邮件UI接管后概览“人工接管中”，历史第1轮及本轮结果仍“等待业务”；人工结案后当前“已解决”、历史结果不改。后续只登记来信仍1轮 |
| 3：邮件最新与历史入口、具体关联邮件定位 | `mail/index.vue:74,77,143,177,206`、`agent/index.vue:104,140` | 历史第2轮“查看触发来信”URL带demo-emma-message-3，实际第3封articleTop324.5/containerTop309，相差15.5px；邮件最新入口明示并选新第5轮。业务触发轮退回output邮件的处理静态核对 |
| 3：run/step→业务→原节点 | `agent/index.vue:146`、`business/index.vue:161,177`；`components/NodeDetail.vue:98` | 独审第2轮stock→business URL保留DEMO-1001/run01-02/stock→“返回关联运行节点”回原stock；旧run01/order回跳同样有效 |
| 3：普通返回保持草稿及阅读位置 | `mail/index.vue:146,173,187,205`、`agent/index.vue:137` | 独审输入“QA cross-page draft keep”，从邮件历史入口往返后textarea值逐字相同，scrollTop离开/普通返回均579；显式message_id定位与普通返回分别核对 |
| 3：实验室按会话选中、追加产生独立演示run及确认回复 | `simulation/index.vue:127,162`、`state.ts:66`、`incoming-run.ts:13` | 第2轮stock→实验室query选Emma，空白点击提示“请填写演示客户来信”；输入后实际生成第5轮、4封来信和9封总邮件，模型理解history含原7封+新来信、确认回复明确本地演示/未调用模型 |
| 3：新增不抢历史节点，只提示最新 | `agent/index.vue:52,96,101,152`、`simulation/index.vue:134`、`state.ts:25` | 从第2轮stock追加后点“返回刚才查看的第2轮”，URL仍run01-02&step_id=stock，原工具详情保持，列表新增5并提示“有更新的运行：第5轮”；主动点最新才切换 |
| 3：人工/结案屏障、退款回执下一round与去重 | `state.ts:37,45,46,68,83`、`mail/index.vue:212,217`、`simulation/index.vue:65` | 独审经可达UI接管Liam→追加/退款只登记，原run1保留，推进按钮禁用；再结案→追加只登记仍1轮。补充断言human/resolved回执都不写run/自动回复，空/缺会话整个demo不变；已有新来信再退款得到[1,2,3]，第二次unchanged不增记录 |
| 3补充：新样例补发申请与回执进入业务售后页签 | `state.ts:12`、`business/index.vue:92,94,97`；`Product-Spec.md:7`、实施规划`:20` | MR-001修后独审实际页签出现DEMO-1001、DEMO-OP-01、DEMO-SHIP-01/TRACK-01，1002/1003仍保留；跳回原run/order有效。详见关闭问题 |
| 4：既有回归、新状态回归、两模式编译及独审 | `package.json:12,13,14`、`scripts/ui-preview-rounds.test.ts:13,41,58,85,98,113` | 独立6项PASS；主Agent最终70/70、0skip及两模式构建完成，原始输出在后文；本报告完成fresh两阶段审查 |
| 4：宽窄/明暗、长内容、键盘/搜索空态/新轮提示、截图地址 | `agent/index.vue:183,189`、`ConversationRounds.vue:44,64,68`、`RunHistory.vue:98` | 独审实看明暗运行台和只读邻居；轮次Enter焦点outline=rgb(93,135,255) solid2px/offset2px；搜索空态/新轮提示实测。主Agent响应式数值及五PNG已独立复核，交付地址实际可打开 |

### 已关闭问题及原失败证据

**MR-001 / MEDIUM / Stage 1 / 独审发现，已关闭。** 新Emma样例已有补发DEMO-OP-01及SHIP-01，修前 `business/index.vue:93` 却按DEMO-1001 ID排除该订单。实际售后页签只列1002/1003，详情却显示Emma发货回执，两个展示面不一致。主Agent先补 `Product-Spec.md:7` 和实施规划`:20`，再将当前 `business/index.vue:92` 绑定改为filtered。独审实际复核三条均显示、Emma申请/回执完整且原节点回跳保持。原发现不因修复而抹去。

**MR-002 / MEDIUM / 主Agent自检发现，独审复核关闭。** 连续来信会使startedAt带30秒，旧helper将节点秒数拼为01/02，显示早于开始。最终 `step-builders.ts:97` 按完整起始总秒递增，`followup-run.ts:46` 复用；独审fresh读两helper并独立重跑末次6项。新增 `ui-preview-rounds.test.ts:85` 真实调用追加两次+回执，逐个run断言首节点晚于开始、节点时间严格递增，输入可由实验室达到。

初次69项日志 `.local-data/runtime/ui-rounds-tests-initial.log` 保留 **68 PASS / 1 FAIL**，失败断言为：

```text
assert.ok(!inputs(newRun.id).includes('Thanks for the update.'))
```

这个断言把理解history与核验draft混为同一集合。核验节点必须读取当轮候选回复（`incoming-run.ts:47`）；最终 `ui-preview-rounds.test.ts:79` 分别限制理解节点无候选回复、全部input无未提交回复id。独审解析实际上下文证明没有未来消息，不仅凭修后的总PASS认定测试真实；主Agent说明初次修正只改断言，报告不把其错误前提当应用缺陷。

### 未实现、部分实现、Spec漂移与隔离

本轮最终没有未实现/部分实现的软件条目，没有新增正式API/表/服务/依赖或真实模型/邮件能力。程序数据与交互在 `src/preview/state.ts:20` 的内存对象内；新增回复是 `incoming-run.ts:20` 的固定文本，有 `simulation/index.vue:93,173` 的明确演示标记。

模式隔离由 `vite.config.ts:17,47,94`、`router/modules/index.ts:4`、`router/core/ComponentLoader.ts:18` 保持；独立GET探针原始响应：

```text
HTTP 404 UI preview uses in-memory demo data only
normal-bundle-preview-match-count=0
```

正常bundle搜索了demo-run-01-04、demo-emma-message-3及多轮页面说明，未命中。预览借用 `mail/index.vue:84` 调用原 `src/components/mail-agent/MessageTimeline.vue:29,30` 只渲染邮件文本，fixture无附件，没有借原组件发出生产附件请求。用户是否满意视觉仍待其查看，不由PASS代替。

## Stage 2：Code Quality

| 检查 | 结论及证据 |
|---|---|
| 类型/命名/职责/文件大小 | PASS，限本轮preview源码。types `:30` 定义round/邮件关联；`navigation.ts:3` 独立会话排序/选择；`journey.ts:5` 值快照，builders拆出；`incoming-run.ts:13` 与 `followup-run.ts:5` 各管触发；单文件最大mail260行、journey215行、agent206行，均≤300。本轮源码未引入any；系统ComponentLoader旧any不冒称已重构 |
| 测试真实性 | PASS于限定范围。6项覆盖真实initial/reset、追加/回执、快照/选择/屏障，关键断言方向与可达输入逐项核对；补充精确消息前缀、整体空输入无变更和human/resolved回执断言；真实浏览器补上纯函数不能证明的UI点击、筛选、键盘、草稿/滚动与返回。70项总数里原64项属于既有工程回归，不冒称70项全是新多轮UI测试 |
| 自动化覆盖边界 | `scripts/ui-preview-rounds.test.ts:3` 导入state/navigation，属于状态测试，没有新组件挂载自动测试。新交互已按Stage1表实际走到，人工/结案由邮件UI设置后进入实验室，补证其前提可达；不将这些证据扩大为真实后台故障或模型语义测试 |
| 安全扫描 | PASS，限preview源码/新测试；eval、innerHTML、dangerouslySetInnerHTML、v-html、凭据前缀/暴露变量、password赋值、绝对用户路径、fetch/axios、local/sessionStorage未发现危险命中；“any further help”是 `state.ts:60` 普通回复文本。任意输入经Vue插值/JSON字符串化展示（`src/components/mail-agent/MessageTimeline.vue:30`、`step-builders.ts:29`），不执行邮件/请求内容；未读取env/密钥 |
| 引导真实性/错误处理 | PASS。`simulation/index.vue:163` 空输入实际提示，`mail/index.vue:223` 空回复提示，reset确认取消保持状态（`:187`），人工/结案实际只登记；抽屉没有匹配的会话明确空态（`RunHistory.vue:48`）。新增确认回复、工具/思考记录均为演示，页面未声称真实AI运行 |
| 运行时错误与Git约束 | PASS于已走路径。独审最后CUA warn/error日志为[]；`git diff --check` exit0，仅LF/CRLF提示；`git diff --cached --name-only`无输出。没有暂存或提交。主Agent程序Lint原始退出结果见编译证据；未把UI过渡期间的旧AX快照当缺陷 |

### 实际视觉对比与响应式

独审真实打开15175运行台及15173系统状态基准页查看渲染。普通ElButton的14px字号、36px高度、8px 15px内边距、6px圆角及同一系统字体完全匹配；新轮次卡片使用 `ConversationRounds.vue:52,61,65` 的Art边框/Element主色及可见键盘焦点。实际外壳、顶部页签、卡片与按钮沿既有体系；两栏/轮次信息层级符合本次授权，没有新字体或视觉依赖。独审常规1280视口document clientWidth/scrollWidth=1280/1280，明暗实际渲染都已查看。

以下数值由主Agent实测，独审复核对应PNG与断点代码，没有重复改全局viewport：

| 视口 | 文档宽度 / 轮次卡 / 执行布局 | 原始JSON与抽屉 |
|---|---|---|
| 1440×1000 | width1440；轮卡272.25px四列；两栏502.672/642.328px，main client/scrollHeight1000/1001 | 桌面完整截图，默认四轮 |
| 1280×900 | width1280；轮卡232.25px四列；两栏432.438/552.562px | raw client/scrollWidth503/503 |
| 800×900 | width792；轮卡350px两列；执行单栏752px | raw710/710 |
| 414×896 | width406；轮卡162px两列；执行单栏376px | raw342/342、卡片client/scroll160/160；Drawer414/414、left0 |

已逐张实际打开 `tmp/ui-preview/multiround-{desktop,1280,800,414,dark}.png`。宽屏四轮与双栏明确；800/414换两列与单栏，长主题/标题换行；暗色边框/选中/状态可读；主Agent实测选中轮卡背景rgb(9,13,25)、边框rgb(46,67,127)、白字。截图为本轮真实初始四轮，没有用测试新增第五轮冒充交付场景。

## 原始测试与编译输出

独审末次命令 `pnpm exec tsx --test scripts/ui-preview-rounds.test.ts`，exit0：

```text
✔ 同一会话四轮顺序、触发及邮件关联一致 (1.7921ms)
✔ 历史上下文没有后来消息或未来发货回执，且不共享可变邮件 (0.8924ms)
✔ 默认最新、显式历史和记忆选择按会话隔离，新轮不抢历史 (16.3591ms)
✔ 连续来信及退款回执的节点不会早于本轮开始 (1.4519ms)
✔ 人工和结案屏障只追加来信，空输入不改状态 (0.3549ms)
✔ 退款回执在已有新来信后形成下一轮且重复推进不增加记录 (1.2183ms)
ℹ tests 6
ℹ suites 0
ℹ pass 6
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 342.8005
```

独审补充内存断言，exit0原始输出：

```text
独审补充：人工/结案回执屏障、全部状态旧run/邮件增量、空/无效输入无变更、2/3/4轮精确1–3/1–5/1–6消息前缀 PASS
```

主Agent最后全量日志 `.local-data/runtime/ui-rounds-tests.log`，独审读取原文：

```text
ℹ tests 70
ℹ suites 0
ℹ pass 70
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2744.7447
```

最终两模式编译及Lint由主Agent执行、独审复核日志，原始末行：

```text
.local-data/runtime/ui-rounds-normal-build.log
$ vue-tsc --noEmit && vite build
✓ built in 26.70s

.local-data/runtime/ui-rounds-preview-build.log
$ vue-tsc --noEmit && vite build --mode ui-preview
✓ built in 18.09s

.local-data/runtime/ui-rounds-eslint.log
（空输出，主Agent记录exit0）
```

最后源码标识：`step-builders.ts:97` SHA256=`8B4B35F104655CA0650529E911A860F9A1DA37E344705A1F1B63A72A7356B9BD`；`followup-run.ts:46`=`F3D513DA8DF6C5893626237DF15E3114837EFFACCD7F9B130D3FF0DCC693CE1E`；`business/index.vue:92`=`93585F5C1BF15E9861D055FB3184E6342466A04EAED187FB57173A5E6346A4CD`。末次时序修正后6项再次独跑，旧run/预置数据生成逻辑保持。向用户交付同会话四轮可点击地址及截图由主Agent完成。
