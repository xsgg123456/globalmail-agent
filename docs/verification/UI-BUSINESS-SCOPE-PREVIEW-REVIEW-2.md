# 业务收敛隔离预览独立重审

日期：2026-10-09。审查结论：**Stage 1 FAIL，1 HIGH、1 MEDIUM；Stage 2 未执行。**

冻结说明：本报告记录本次初次复审时的81项版本及上述原始反例。主Agent随后告知已改用结构化shipmentState并补闭案接管guard，82项新版回归待下一次fresh审查从Stage1重新验证；本报告不把后续修复记作已通过，也不使用旧81项作为新修复证据。

本报告使用 `.agents/skills/code-review/SKILL.md`，从 Stage 1 重新审查修复后的实现。审查范围只含 Product-Spec v1.17 顶部当前授权、DEC-016/023/024/025、AGENT-ARCHITECTURE 顶部预览边界、DEV-PLAN 当前授权及 `UI-PREVIEW-IMPLEMENTATION.md:15` 至第27行。历史正式后端申请、财务、履约及旧实验室条款不作为本轮缺失项。没有修改15173、18080、PG、实现源码、Git暂存区或提交；没有向15175全局控制接口写命令。

证据来源：审查者独立阅读实现、执行全量81项前端测试及 vue-tsc、运行自有 Node/tsx 内存反例、只读查询15175；构建日志及GUI图片由主Agent提供。不能将主Agent截图写成审查者独立点击验证。

## Stage 1 发现

### S1-H01：HIGH，未知/失败物流含英文状态词仍自动出站

要求：`Product-Spec.md:5`规定“普通咨询/排障/物流保留有据回复，安全或缺依据转人工”；`docs/planning/UI-PREVIEW-IMPLEMENTATION.md:25`明确“普通物流工具返回未知、失败或无可核实状态时，也必须保存内部建议并转人工”。

实际：`globalmail-agent/frontend/src/preview/advice.ts:113`至第117行仅识别中文未知/失败；任意字符串含 delivered/in transit 即视为可核实。英文 unknown/query_failed、否定 delivered 或历史缓存成功状态不能产生 unknowns。`run-builder.ts:22`因此进入 automatic，`run-builder.ts:116`至第125行新增客户邮件；`reply-drafts.ts:40`至第43行进一步将否定/历史状态写成当前送达或运输事实。

独立复现：自有 Node/tsx 进程创建 `createPreviewState()`；全部输入先经过交付入口 `parsePreviewCommand({type:'business_update', orderId:'DEMO-1007', patch:{shipment}})`，接受后 `updateMockOrder`，再向 `demo-mail-07` 调用 `appendToState(..., 'Could you check the shipping status?')`。没有向15175写请求。

原始输出（仅删去长回复正文，不改变字段值）：

```json
{"shipment":"Delivery status unknown; last stored scan was delivered","contractAccepted":true,"result":"automatic","owner":"agent","added":1,"unknowns":[]}
{"shipment":"query_failed: previous cached status in transit","contractAccepted":true,"result":"automatic","owner":"agent","added":1,"unknowns":[]}
{"shipment":"Not delivered; current carrier status unknown","contractAccepted":true,"result":"automatic","owner":"agent","added":1,"unknowns":[]}
```

第三个输入实际客户回复：

```text
The latest tracking record shows a delivered scan. Please let us know if you have not received the parcel so our support team can check further.
```

初轮中文未知物流分支已经修复，但核心拒发要求仍不完整，不能关闭原HIGH。修复验收应覆盖脚本/API可达的英文未知/失败、否定及旧缓存状态混合输入，全部转人工且不新增Agent客户邮件；可核实当前运输/送达正例继续可自动回复。

测试证据：`scripts/ui-preview-evidence.test.ts:27`至第46行仅覆盖中文失败及直接底层调用空字符串。空字符串被 `control-contract.ts:43`拒绝，不能当成脚本/API可达测试；可达中文反例确实有证明价值，但81项全绿不证明上述混合输入安全。

### S1-M01：MEDIUM，已结案会话仍可用“人工接管”隐式重开

要求：`Product-Spec.md:5`及 `docs/planning/UI-PREVIEW-IMPLEMENTATION.md:17`保留人工结案屏障；持续人工模式解除条件在第21行仍待对齐，没有本轮新增重开行为授权。

实际：`globalmail-agent/frontend/src/views/ui-preview/mail/index.vue:61`的“人工接管”只在状态为人工接管中时禁用；已解决仍可点击。第227至230行 `takeover()`没有结案判断，直接将已解决改成人工接管中。随后第114行发送按钮解除禁用，`behavior.ts:26`及第51行的结案门禁也失效。此结论来自页面事件绑定和状态赋值，不声称已独立执行GUI点击。

修复验收：已解决时禁用接管且handler保留结案判断；通过正常页面标记解决后，接管/人工发送不能重开，后续来信仅登记、无新run。`scripts/ui-preview-rounds.test.ts:152`只测试底层结案状态，没有覆盖页面 `takeover()`。

## Stage 1 逐项覆盖

下表源码路径默认以 `globalmail-agent/frontend/` 为前缀；“完整实现”仅指已列明的源码与独立回归证据，不替代所有GUI点击。

| 本轮要求 | 状态 | 证据与验证 |
|---|---|---|
| 仅15175构造预览，不推进正式业务或改后端 | 完整实现 | `vite.config.ts:18`、第34/48/92行；预览无代理、阻断/api，独立只读HTTP200/404见下文；当前Git状态未把历史未提交源码误记本轮改后端。 |
| Amazon与独立站、七类及危险样例 | 完整实现 | `src/preview/fixtures.ts:3`、第31/39/48/56/64行；`types.ts:4`，独立 `ui-preview-rounds.test.ts:20`断言8会话/13run及七类枚举。 |
| 普通咨询、排障及物流有据回复，缺依据交人工 | 部分实现 | `advice.ts:49`、第110/119行；默认资料和运输正例通过，未知混合物流失败见S1-H01。本报告不验任意客户原文的真实模型理解。 |
| 四类商业售后首轮只读核查及HITL | 完整实现 | `advice.ts:4`、第85/95/99/104行；`run-builder.ts:19`、第95行；独立测试第47行逐四类检查无Agent客户邮件及写工具。 |
| 后续每封来信独立内部run，人工回复后持续客服主导 | 完整实现 | `behavior.ts:27`至第41行；`run-builder.ts:19`、第24行；独立测试第62行逐四类核对run模式、人工往来及自动邮件计数。 |
| Liam退款三封来信/两次人工回复/三run | 完整实现 | `journey.ts:40`至第65行，独立测试第77行核对5封邮件与三轮。 |
| Emma普通排障→补寄→物流仍持续人工 | 完整实现 | `journey.ts:5`至第37行；独立测试第97行核对四轮及只有第一轮有Agent回复。 |
| 每轮保存当时往来和事实、无未来信息 | 完整实现 | `run-builder.ts:10`、第32/51/79行；独立测试第77行修改当前邮件和订单后旧run输入仍一致，Emma第二轮没有未来补寄物流。 |
| 无申请创建/取消、资金/库存冻结、退款或发货执行 | 完整实现（预览） | `step-builders.ts:31`只列只读工具；`run-builder.ts:69`、第89行明确无写入；独立四类每轮工具断言第57行。未证明正式后端写工具关闭。 |
| 业务更新不产生run、执行回执或客户邮件 | 完整实现 | `behavior.ts:80`至第88行仅更新Mock字段及建议时效；独立第126行计数断言。 |
| 内部事实、来源、时间、缺口、建议与草稿分开 | 完整实现（已识别故障） | `advice.ts:34`至第37行、`AdviceDrawer.vue:17`/26/30/35/37；独立四类来源/时间断言，查看主Agent `business-scope-advice.jpg`。未知英文物流遗漏仍见S1-H01。 |
| processed不表示银行到账，库存仅快照 | 完整实现 | `advice.ts:90`、第102/108行；`reply-drafts.ts:24`；`journey.ts:53`。独立阅读事实/草稿与退款回归。 |
| 危险、查询失败、缺订单可交人工 | 完整实现（构造路径） | `advice.ts:39`、第58行；`control-contract.ts:36`/51；`ui-preview-evidence.test.ts:8`经过契约设置lookupNotFound，工具返回not_found且facts为空；lookupError单独回归为query_failed。 |
| 正常邮件时间线不混内部建议 | 完整实现 | `mail/index.vue:89`复用MessageTimeline，建议另设第121行抽屉；`run-builder.ts:95`只保存建议；独立四类邮件计数回归与主Agent截图。 |
| 显式采用、个人草稿替换确认、人工手动发送 | 完整实现（源码） | `AdviceDrawer.vue:47`；`mail/index.vue:238`、第247/253/261/267行，确认后复核会话/run/时效。主Agent真实点击验收需在验证文档明确来源。 |
| 新来信、数据变化、人工回复使过时建议不可采用 | 完整实现 | `behavior.ts:85`、第90/94行；`run-builder.ts:96`/100；独立第126/183行校验。 |
| 手动结案屏障 | 部分实现 | `behavior.ts:26`、第51行底层拒发和仅登记通过；页面人工接管可重开见S1-M01。 |
| 沿用Art外壳、运行概览/轮次/时间线/详情 | 完整实现（源码及主Agent截图） | `mail/index.vue:4`/89、`agent/index.vue:16`/34/70、`NodeDetail.vue:2`；实际查看 `business-scope-desktop.jpg`运行布局。未做本轮邻居页面独立视觉对照。 |
| 默认最新、历史选择/节点跨新轮保留、跨页定位 | 完整实现（源码/回归） | `navigation.ts:14`、`agent/index.vue:99`/104/113/128/143；独立第110行测试历史选择；GUI执行证据由主Agent维护。 |
| 角色提示词/思考摘要/工具参数结果/原始JSON | 完整实现（源码） | `RequestView.vue:8`/29/34、`NodeDetail.vue:24`/29/50/56、`DataBlock.vue:20`；逐项阅读模板和run数据。 |
| 删业务中心/场景实验室及入口，不移入测试UI | 完整实现 | `router/modules/ui-preview.ts:8`仅四路由；mail/agent模板无来信注入、重置、样例选择测试控件；NodeDetail已无业务跳转，独立路由枚举测试通过。 |
| 旧持久化页签/搜索历史清理，保留有效参数 | 完整实现（源码/回归） | `router/local-tabs.ts:2`、`guards/beforeEach.ts:20`/23；独立local-tabs迁移测试通过。没有修改主Agent浏览器存储。 |
| 仅ui-preview开发服务本地脚本/API，校验与去重 | 完整实现（独立HTTP回归） | `vite.config.ts:92`、`scripts/preview-control.ts:11`/22/25/33/37/50/60；独立测试实际启动随机端口验证403/400/413/200/409/405/重置。 |
| 初始化历史回放/HMR新命令不抢历史run焦点 | 完整实现（源码/回归） | `control-client.ts:18`/20/37；`behavior.ts:41`不写viewedRuns；独立历史选择回归。未向15175写事件。 |
| 正常模式不含预览路由/控制服务，预览/api阻断 | 完整实现（源码/HTTP/构建日志） | `vite.config.ts:18`/48/92、`router/modules/index.ts:4`；独立15175/api实际404；构建来源见下文。 |
| 所有run/提示词/思考/指标明确构造 | 完整实现 | `PreviewBanner.vue:4`、`step-builders.ts:4`、`agent/index.vue:44`、`NodeDetail.vue:29`、`reference/index.vue:31`至第34行明确未连接/未执行。 |
| 全量测试、两模式编译、明暗窄屏点击及两阶段审查 | 未完成整体验收 | 独立81项/类型通过，主Agent两模式构建日志已读取；Stage1有HIGH，不能宣布两阶段通过。GUI图已生成但本轮Stage2停留。 |

初轮缺订单不可达项已关闭：新增 `lookupNotFound`可通过交付契约进入，与 `lookupError`分开。初轮物流项仅中文分支关闭，其英文混合分支继续FAIL。

## 独立验证与编译结果

审查者在frontend独立执行 `npm test`，退出码0，原始汇总：

```text
> art-design-pro@0.0.0 test
> tsx --test scripts/*.test.ts
ℹ tests 81
ℹ suites 0
ℹ pass 81
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2802.2294
```

原始测试输出同时含既有知识模块生命周期警告，例如：

```text
[Vue warn]: onUnmounted is called when there is no active component instance to be associated with. Lifecycle injection APIs can only be used during execution of setup(). If you are using async setup(), make sure to register lifecycle hooks before the first await statement.
```

独立执行 `npx vue-tsc --noEmit`，退出码0，原始stdout为空。

独立只读HTTP：

```text
GET http://127.0.0.1:15175/ => 200
GET http://127.0.0.1:15175/api/v1/conversations => 404
UI preview uses in-memory demo data only
GET http://127.0.0.1:15175/__ui_preview__/events => 200
scope: ui-preview-memory-only
```

构建均由主Agent执行；审查者读取原始日志，未再启动构建。`tmp/ui-preview/business-scope-production-build.log`原始首尾摘录：

```text
$ vue-tsc --noEmit && vite build
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for production...
transforming...
✓ 3380 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 36.60s
```

`tmp/ui-preview/business-scope-preview-build.log`原始首尾摘录：

```text
$ vue-tsc --noEmit && vite build --mode ui-preview
🚀 API_URL = /api/v1
🚀 VERSION = 0.2.0
vite v7.1.7 building for ui-preview...
transforming...
✓ 3380 modules transformed.
rendering chunks...
computing gzip size...
✓ built in 19.17s
```

`tmp/ui-preview/business-scope-lint.log`内容为空；调用成功由主Agent说明，空日志本身不能证明退出码。

GUI：实际读取主Agent `tmp/ui-preview/business-scope-advice.jpg`、`business-scope-desktop.jpg`、`business-scope-missing-order.jpg`。这些只支持抽屉/布局/缺订单显示证据；不替代审查者独立点击、明暗窄屏或邻居对照。

## Stage 2

**未执行。** Stage 1存在HIGH，按skill停止。无any、300行、安全扫描、测试真实性专项、邻居基准页面视觉对比均不作本轮PASS声明。修复后需要从Stage1重审，再决定是否进入Stage2。

本报告仅验证明确构造的隔离前端演示，不证明真实模型/业务质量、真实CoT、正式后端权限精简、正式API接入或产品82项AC通过。
