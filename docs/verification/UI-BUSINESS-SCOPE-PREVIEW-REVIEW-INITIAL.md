# 业务收敛隔离预览独立审查

日期：2026-10-09。范围：Product-Spec v1.17 顶部本轮授权、DEC-007/008/014/016/023/024/025，AGENT-ARCHITECTURE 顶部预览边界，DEV-PLAN 当前授权及 UI-PREVIEW-IMPLEMENTATION 第9–23行。旧正式 Phase、82项产品AC和历史内部申请链路不属于本轮验收范围。

本文件保留修复前初轮审查事实与原始输出。主Agent随后报告已修复两项发现并完成81项回归；本审查者未重验该版本，最终验证交由新的独立审查实例，不覆盖本轮FAIL或改写下方原行号。

**初轮结论：Stage 1 FAIL，HIGH 1项、MEDIUM 1项；Stage 2 未执行。** 严格按 code-review skill 的 HIGH 门禁停止质量、安全扫描与邻居页面视觉比较。未修改实现、正式服务、数据库、当前浏览器或全局预览命令；未暂存、提交或启动15175服务器。

## Stage 1：问题

### S1-H01　HIGH　普通物流查不到有效状态时仍自主回复，没有转人工

- 要求：`Product-Spec.md:5`“普通咨询/排障/物流保留有据回复，安全或缺依据转人工”；`docs/planning/UI-PREVIEW-IMPLEMENTATION.md:16`要求危险、缺订单、查询失败仍可人工处理。
- 实现差异：`globalmail-agent/frontend/src/preview/advice.ts:110`物流分支只把任意 `shipment` 字符串放入事实，不记录未知/查询失败的缺口；`globalmail-agent/frontend/src/preview/run-builder.ts:21`仅以缺订单/查单失败判断 missing。因此物流记录明确为未知时，`internal=false`，第116行仍生成 `simulated_agent` 客户邮件。
- 独立复现：在单独 Node/tsx 进程中调用 `createPreviewState()`，用交付 API 允许的 `updateMockOrder(state, 'DEMO-1007', { shipment: '未知；物流接口未返回可核实的状态' })` 更新构造状态，再 `appendToState(state, 'demo-mail-07', 'Could you check the shipping status?')`。没有向15175发送变更请求。
- 原始输出摘要：

```json
{
  "result": "automatic",
  "owner": "agent",
  "mode": "automatic",
  "automaticRepliesAdded": 1,
  "review": {
    "unknowns": [],
    "recommendation": "根据适用资料或查询事实回复，无法支持下一步时交给客服。",
    "automatic_reply": true
  }
}
```

实际客户回复为：`The latest tracking status needs further verification. Our support team will review the available record before confirming the next steps.` 文案表示需要核查，但处理权依然属于Agent，也没有客服内部建议入口。修复标准：明确未知/失败的普通查询走人工建议及未发送草稿，处理权转人工，不能新增Agent客户邮件；正常可核实物流保留自动回复，补可达输入的反例回归。

### S1-M01　MEDIUM　“缺订单”不能通过交付的脚本/API进入

- 要求：`docs/planning/UI-PREVIEW-IMPLEMENTATION.md:16`包含缺订单场景，第18行规定测试数据通过脚本/API驱动；本轮无测试UI。
- 实现差异：`globalmail-agent/frontend/src/preview/fixtures.ts:84`给全部8个会话分配订单，第101行生成全部8个对应订单；`control-contract.ts:17`与第35行白名单只支持退款/物流/库存等既有字段和 `lookupError`，不能设置订单不存在或解除绑定。`advice.ts:58`虽然有 `!order` 分支，但交付入口不能触发。
- 证据：独立阅读生产入口、夹具和测试；`globalmail-agent/frontend/scripts/ui-preview-rounds.test.ts:145`的缺订单测试直接把内部 `mail.orderId` 改成 `MISSING-ORDER`，并非脚本/API可达输入。现有 `lookupError=true` 返回 `query_failed`，不等于 `not_found`。
- 修复标准：补明确构造的缺订单样例或受校验的 Mock not-found 字段，通过交付脚本/API可进入，并保持只读/人工边界。

## Stage 1：逐项覆盖

以下“完整实现”针对当前预览代码及明确列出的独立验证；不将源码存在等同于全部GUI点击已通过。

| 本轮条目 | 状态 | 代码位置与实际验证 |
|---|---|---|
| 最新授权限定15175预览，不推进正式商业流程 | 完整实现（源码边界） | `Product-Spec.md:5`、`DEV-PLAN.md:3`；`frontend/vite.config.ts:18`、第48行、`src/router/modules/index.ts:4`。只读15175根路径实际HTTP200。 |
| Amazon与独立站、七类业务及危险样例 | 完整实现 | `src/preview/fixtures.ts:3`、第31/39行；`advice.ts:5`。独立全量测试中的七类枚举、8会话/13run断言通过，测试 `ui-preview-rounds.test.ts:20`。 |
| 三类普通问题的有据构造回复 | 部分实现 | `advice.ts:49`、第110/113行及 `reply-drafts.ts:39`；默认咨询/排障/物流已有演示依据与回复，默认路径回归通过；未知物流不转人工，见S1-H01。本轮不验真实模型能否理解任意来信。 |
| 四类售后首轮只读核查/HITL，无自主客户邮件 | 完整实现 | `advice.ts:4`、第85/95/99/104行；`run-builder.ts:19`、第95行、第116行。独立测试 `ui-preview-rounds.test.ts:47`检查处理权、持久人工、无Agent邮件/写工具。 |
| 四类人工回复后持续客服主导，每封来信独立内部run | 完整实现 | `behavior.ts:27`、第35行、第61行；`run-builder.ts:19`、第24行。独立测试 `ui-preview-rounds.test.ts:62`逐四类验证新run、人工往来和无自动发送。 |
| Liam退款三封来信、两次人工回复、三轮独立快照 | 完整实现 | `journey.ts:40`、第46/55/61行；`run-builder.ts:10`、第32行。独立测试 `ui-preview-rounds.test.ts:77`逐轮核对无未来消息/退款事实，修改当前数据不改旧输入。 |
| Emma排障→补寄→物流仍持续人工 | 完整实现 | `journey.ts:5`、第17/23/33行；`behavior.ts:28`及 `run-builder.ts:19`。独立测试 `ui-preview-rounds.test.ts:97`检查四轮、只有第一轮自动邮件、历史无未来物流号。 |
| 不提交/取消申请、不冻结资金库存、不执行退款/发货 | 完整实现（预览记录） | `step-builders.ts:31`仅提供查询/资料工具；`run-builder.ts:69`、第89行明确 `business_writes=false`，四类最终输出到内部建议。测试第57行检查各轮无submit/cancel/reserve/execute工具。不声称正式后端写工具已关闭。 |
| 业务数据变化不主动生成run或客户邮件 | 完整实现 | `behavior.ts:79`仅更新Mock字段并使建议过期；`journey.ts:23`和第52行由后续人工回复/客户来信驱动。独立测试 `ui-preview-rounds.test.ts:126`核对run/邮件计数不变。 |
| 事实、来源、查询时间、缺口、建议与草稿分开 | 完整实现（四类及已识别故障） | `advice.ts:34`、第66/90/97/102/108行；`components/AdviceDrawer.vue:17`、第26/30/35/37行。独立测试第54行检查来源/时间；实际查看主Agent `business-scope-advice.jpg`，抽屉与邮件分开显示。未知普通物流缺口漏记见S1-H01。 |
| 已处理退款不等于到账，库存快照不等于预留 | 完整实现 | `advice.ts:90`、第102/108行；`reply-drafts.ts:24`、`journey.ts:53`。独立阅读保存输出与默认退款路径；主Agent建议抽屉截图可见“支付记录已处理…不代表客户银行已到账”。 |
| 危险/查询失败转人工，缺订单仍可人工处理 | 部分实现 | `advice.ts:39`、第58行；`run-builder.ts:22`、第95行；独立危险/查询失败/缺订单内部函数测试通过（第126/142/152行）。脚本/API缺订单不可达见S1-M01；普通物流未知见S1-H01。 |
| 正常邮件时间线不混内部建议 | 完整实现（源码及提供截图） | `mail/index.vue:89`直接复用原 `MessageTimeline`、第121行另设建议抽屉；`run-builder.ts:95`只保存建议不push客户邮件。独立四类邮件计数验证和主Agent抽屉截图支持。 |
| 显式采用草稿、已有个人草稿替换确认，人工手动发送 | 完整实现（源码） | `AdviceDrawer.vue:47`；`mail/index.vue:247`、第253/261/267行，确认后复核会话、run和建议时效；第238行手动发送。独立源码检查，交互点击证据尚由主Agent执行，不冒充独立GUI验证。 |
| 新来信/数据变化/人工回复使旧建议不可直接采用 | 完整实现 | `behavior.ts:84`、第89/92行；`run-builder.ts:96`、第100行。独立测试第126/183行核对数据更新后及人工回复后失效、新来信有新建议。 |
| 人工结案后新来信只登记，不自动重开/回复 | 完整实现（底层屏障） | `behavior.ts:26`、第51行；`mail/index.vue:233`人工标记结案。独立测试 `ui-preview-rounds.test.ts:152`确认无新run、人工发送返回false。关闭后的UI按钮状态尚未做独立点击。 |
| 沿用运行概览、轮次、执行时间线与详情，默认最新且历史不被新轮覆盖 | 完整实现（源码/回归） | `agent/index.vue:16`、第34/57/70/99/104/113行；`navigation.ts:14`保留显式/记忆选择。独立测试第110行保留历史和其他会话；真实GUI焦点与多宽度证据待主Agent交付。 |
| 输入、角色提示词、思考摘要、工具参数结果、完整原始JSON | 完整实现（源码） | `NodeDetail.vue:24`、第29/50/56行；`RequestView.vue:8`、第29/34行；`DataBlock.vue:20`。历史数据在建run时独立保存；构造思考标记可见，未宣称真实CoT。 |
| 移除业务中心/实验室页面与所有预览入口、没有测试UI | 完整实现 | `router/modules/ui-preview.ts:8`只保留邮件/运行/知识/状态；business/simulation目录实际无源码文件；`NodeDetail.vue:56`已无业务跳转，mail与agent模板没有注入来信/重置控件。独立路由枚举测试第41行通过。 |
| 启动清理旧持久化页签与搜索历史，保留有效参数 | 完整实现（源码/回归） | `router/local-tabs.ts:2`、`guards/beforeEach.ts:20`与第23行；独立 `local-tabs.test.ts:18`实际执行通过。没有在主Agent浏览器改localStorage。 |
| 仅ui-preview开发服务启用本地控制桥，来信/Mock更新/重置、校验/去重 | 完整实现（HTTP独立回归） | `vite.config.ts:92`；`scripts/preview-control.ts:11`、第22/25/33/37/50/60行；`control-contract.ts:18`；`scripts/drive-ui-preview.ps1:20`。独立测试启动随机端口与自有临时目录，真实HTTP校验403/400/413、去重200、冲突409、重置、405，测试第9行通过。 |
| 初始化历史回放、HMR新命令、无前端测试按钮 | 完整实现（源码）；新命令GUI待验 | `control-client.ts:18`先订阅，第20行GET历史，第37行按序处理；`behavior.ts:41`只追加run，保留viewedRuns。独立只读GET `/__ui_preview__/events` 实际200、scope为ui-preview-memory-only；未向此全局API写数据。 |
| 预览阻断/api；正式模式不注册预览页面/控制服务 | 完整实现（源码及预览HTTP） | `vite.config.ts:19`、第48/92行；`router/core/ComponentLoader.ts:18`；独立GET15175 `/api/v1/conversations`实际404，正文见下方。正式构建证据来源见编译段。 |
| 演示标记、不冒充真实Agent或后台观测 | 完整实现 | `PreviewBanner.vue:4`；`NodeDetail.vue:29`；`reference/index.vue:31`。独立阅读模板与保存数据、查看主Agent建议截图；本报告没有检验真实Agent业务质量。 |
| 两模式编译、明暗/窄屏/真实点击、独立两阶段通过、不提交 | 未完成整体验收 | 独立78项通过、主Agent正式构建日志已提供；预览构建和剩余GUI证据尚未交付。Stage1有HIGH导致两阶段不能通过。审查过程中未执行Git变更操作。 |

表中的源码路径均以 `globalmail-agent/frontend/` 为前缀，脚本入口 `scripts/drive-ui-preview.ps1` 以 `globalmail-agent/` 为前缀。

## 独立实测与编译证据

独立命令：在 `globalmail-agent/frontend` 执行 `npm test`。退出码0，原始汇总如下；共78项，含真实随机端口HTTP测试，临时Vite服务及目录按测试finally清理，不占15175。

```text
> art-design-pro@0.0.0 test
> tsx --test scripts/*.test.ts
ℹ tests 78
ℹ suites 0
ℹ pass 78
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3042.8275
```

独立只读HTTP输出：

```text
GET http://127.0.0.1:15175/ => 200
GET http://127.0.0.1:15175/api/v1/conversations => 404
UI preview uses in-memory demo data only
GET http://127.0.0.1:15175/__ui_preview__/events => 200
scope: ui-preview-memory-only
```

正式模式编译：**主Agent执行，审查者读取原始日志，不是独立执行。** 日志 `tmp/ui-preview/business-scope-production-build.log` 第1行及末行摘录：

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

预览模式编译：本初轮报告冻结时尚未读取完成日志，**未验证**。实际查看的当前GUI材料仅主Agent `tmp/ui-preview/business-scope-advice.jpg`；其截图表示页面构成，不能替代独立点击、明暗/窄屏或邻居对照。未把历史预览截图当成本轮新证据。

## Stage 2

**未执行。** Stage 1 的 S1-H01 达到 HIGH；无any、300行、注入/密钥扫描、测试真实性专项及邻居基准页面实际视觉对比均未作本轮PASS声明。待主Agent修复后，从 Stage 1 重新派发审查。

本报告只验本轮隔离构造预览，不证明真实Agent决策质量、正式后端权限精简、真实模型思考采集、正式API接入或产品82项AC通过。
