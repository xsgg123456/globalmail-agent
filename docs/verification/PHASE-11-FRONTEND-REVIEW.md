# Phase11 Task3 前端独立初审

日期：2026-10-10。结论：**Stage 1 FAIL，1 项 HIGH；Stage 2 未执行。**

本次只审 Task3 的前端 UI、HTTP 合同校验和异步失效，不审后端/部署交付，不宣称整个 Phase11 完成。真实浏览器页面、Langfuse 链接打开、后台联调及邻居页面渲染对比留本期总审，均未记为通过。审查只读源码，只新增本报告，无修复、提交或环境启停。

## 审查规划与材料

1. 读取需求、正式运行八契约、第9节和实施计划；完成标准为 Task3 条目逐项映射，不把历史商业写权限恢复规则用作当前要求。
2. 对照五个前端变更文件并追踪实际调用方、SSE 与生命周期；完成标准为链接来源、状态、撤销、切换与晚到响应有代码及验证证据。
3. 独立执行定向测试/类型检查和故障复现；Stage1 有 HIGH 即停止，不进入 Stage2。

已读取 `.agents/skills/code-review/SKILL.md`、`AGENTS.md`、`docs/README.md`、`docs/planning/SESSION-HANDOFF.md`、`Product-Spec.md:436–449,512–528`、`AGENT-ARCHITECTURE.md:27–38,447–457`、`DEV-PLAN.md:253–265`、`docs/planning/PHASE-11-IMPLEMENTATION.md:3–24`；源码证据以以下路径为准，均在 `globalmail-agent/frontend/` 下。

## Stage 1：Spec Compliance

### 必须修复

**HIGH F11-FE-01：SSE 撤销时，调用记录持续读取失败会让旧 trace 入口永久保留。**

- 要求：实施计划 Task3 要求“API作用域/撤销检查；在现有独立运行台展示真实trace入口与未启用/排队/失败状态”（`docs/planning/PHASE-11-IMPLEMENTATION.md:11`）；正式运行契约要求“撤销/作用域仍生效”和“正式界面来自真实API/执行”（`AGENT-ARCHITECTURE.md:34,36`）。本次派发明确要求验证 SSE 撤销状态。
- 实际代码：`src/views/agent-runs/index.vue:48` 将观测刷新 revision 绑定到 `record`。`src/composables/use-agent-console.ts:18` 的 record 来自加载的调用记录；失败时 `:33–35` 把它设成 null。SSE 回调 `:68–70` 只串行刷新会话、列表、调用记录，没有独立观测失效信号。`src/composables/use-run-observability.ts:25` 只 watch runId/revision；同 run 的 record 原来为 null、再次失败仍为 null，watch 不会触发。
- 复现前提可达：本地运行详情 GET 超时/503/410 与此前成功读到的观测入口可以同时存在；观测 API 的独立 GET 不依赖调用详情。生产 composable 的失败处理没有移除所选 run，运行台仍渲染观测组件（`src/views/agent-runs/index.vue:40–48`）。
- 独立实证：使用 Vue 自定义 renderer、memory router、生产 `useAgentConsole`/`useRunObservability`、替身 HTTP 方法和 EventSource，先令调用记录持续报错、观测返回 exported；随后投递合法作用域 `attachment.revoked` SSE，观测服务的下一响应已切为 revoked。事件后观测 GET 次数仍为 1，旧 exported URL 仍存在。完整最小脚本及原始输出见附录。
- 影响：撤销后的入口不因该 SSE 被清除，也不会自动复核；手动“刷新记录”在相同失败/null 情况下同样不触发观测刷新。没有证据表明发生了正文泄漏，本问题的实证是已撤销入口持续展示。
- 修复标准：SSE 到达和手动刷新必须给观测独立失效信号，在等待其他接口之前清旧入口并拒绝此前晚到响应；即使其他 GET 报错或已有 refreshPending，也必须生效。增加走生产 console/SSE 链路的回归用例，不能只测试孤立组合函数。

### 逐项对照

| 条目 | 本次结论 | 代码与验证证据 |
|---|---|---|
| REQ-009 第1项：沿 Art Design Pro/批准布局，运行独立成页 | 增量代码符合既有结构；渲染未验 | `src/views/agent-runs/index.vue:17–51` 仍使用原概览区，只新增一行 ObservabilityStatus 和 import（本次 git diff 仅2行）；`src/components/agent-runtime/ObservabilityStatus.vue:2–10` 使用原主题文字、ElTag/ElButton。没有真实视觉通过结论。 |
| REQ-009 第2项：可辨模式、会话、来信、状态 | 本次没有改动既有实现 | `src/views/agent-runs/index.vue:20–23,31–32,40–46`；增量未替换这些标签/触发来信操作。此处只核对变更影响，非重新验收历史功能。 |
| REQ-009 第3项：真实轮次/节点、用量与邮件分离 | 观测 GET 与当前 run 绑定；撤销路径不符合 | `src/api/observability-api.ts:16–20,36–41` 校验 run_id 并只读 GET；运行页 `:48` 独立展示。F11-FE-01 阻止当前状态真实性通过。历史新轮仅提示的原控件仍在 `src/views/agent-runs/index.vue:49`。 |
| REQ-009 第4项：文字/图标区分来源 | 新观测状态有文字；既有来源区未改 | `src/components/agent-runtime/ObservabilityStatus.vue:6–8,19–21` 为六状态提供文字，并用“本轮 Langfuse 追踪”说明入口；不只以颜色表达状态。 |
| REQ-009 第5项：明确操作，不恢复测试 UI/旧链路 | 本次增量符合 | 新控件只调用观测 GET（`src/api/observability-api.ts:38–41`），刷新按钮只调用 refresh（`src/components/agent-runtime/ObservabilityStatus.vue:10,18`）；无测试、发送、业务重跑操作。原停止/重试仍在运行页 `:44–45`。 |
| REQ-009 AC-027/028/032 | 不在此次 Task3 重验范围；本次增量无对应功能改写 | `src/views/agent-runs/index.vue:48,66` 是全部已跟踪增量；历史回放、人审及真实明暗主题/首屏依赖验收留已有14–16证据及本期 GUI 总审，未在此宣称 AC 通过。 |
| REQ-013 第1项 / AC-049：run/trace 关联 | 前端合同部分已实现；实际多工具导出及 usage 关联待总审 | `src/api/observability-api.ts:16–17,25–26,39` 要求当前 run_id、32位小写hex trace_id、路径中的相同 trace_id；独立定向测试第1项通过。前端未创建 trace 或重计 usage；真实事件层级不由本次证明。 |
| REQ-013 第2项：版本、错误、耗时、实际 usage | 新增入口未实现/改写计量；后端与实际内容待总审 | 观测接口仅保存五字段（`src/api/observability-api.ts:4–10`），运行页原 token 汇总 `:70` 未改；不能据此宣称 provider 去重或版本导出通过。 |
| REQ-013 第3项：业务持久化与观测分工 | 前端增量保持只读边界；业务持久化不在本审范围 | `src/api/observability-api.ts:36–41` 无业务命令；`src/composables/use-run-observability.ts:9–23` 的失败只影响观测局部状态。 |
| REQ-013 第4项 / AC-050：安全摘要、脱敏 | 前端不显示原始异常/理由；实际 trace payload 脱敏待总审 | `src/composables/use-run-observability.ts:19–20` 捕获失败并使用固定文案；`src/components/agent-runtime/ObservabilityStatus.vue:3–10` 不渲染 reason_code/原始响应。链接禁止外网、非HTTP、用户凭据、query/hash（`src/api/observability-api.ts:23–28`），定向恶意链接测试通过。未读取私有配置。 |
| REQ-013 第5项 / AC-051：观测失败不影响业务且不重跑 | 前端错误隔离/人工刷新已实现；SSE 真实状态失败 | `src/composables/use-run-observability.ts:19–23` 和组件 `:4,8,10` 提供错误/降级/只读重试；独立定向第3项验证错误提示、离页晚到丢弃。实际业务持久化与 Langfuse 故障不重跑需后台联调；F11-FE-01 为本次必修。 |
| REQ-013 工程推荐：自托管独立部署 | 本次前端只允许本机 HTTP 链接，实际部署不在范围内 | `src/api/observability-api.ts:24–26`；本次没有以 Cloud 或演示 fixtures 替代实际部署验收。 |
| REQ-013 第7项 / AC-052：新 run/trace 不重放旧动作 | 切 run 的前端入口失效通过定向测试；新trace创建与实际业务待总审 | `src/views/agent-runs/index.vue:48` key 为 run.id；`src/composables/use-run-observability.ts:12–18,25–28` generation/runId 校验，独立第2项验证切 run 立即清空、旧响应不串会话。 |
| Task3 六状态 disabled/local_only/pending/exported/degraded/revoked | 六状态映射/导出链接条件已实现；SSE 撤销实时刷新失败 | `src/api/observability-api.ts:3,12,30–31`，组件 `:6–8,19–21`；仅 exported 且校验通过的 URL 显示链接，其他不补造入口。F11-FE-01 可使 revoked 无法及时呈现。 |
| Task3 离页/KeepAlive 晚到 | 独立组合逻辑通过；真实组件生命周期仍待GUI总审 | `src/components/agent-runtime/ObservabilityStatus.vue:23–25` 注册 activate/suspend/dispose；组合 `:18,26–28` 校验 active/generation；定向第3项直接执行 suspend，不等同于验证浏览器 KeepAlive 生命周期。 |

当前正式八契约的变更影响：第1–5/7项权限、人工回复/建议/结案和只读工具没有本次源码增量；第6/8项的真实记录与撤销要求由 F11-FE-01 失败。证据：正式八契约 `AGENT-ARCHITECTURE.md:29–36`，本次运行页 git diff 仅在 `:48,66` 增加观测行/import，其余新文件仅 GET/展示局部状态。

## Stage 2

**未执行。** Stage1 存在 HIGH，按 skill 停止。命名/类型/文件大小/单一职责、安全扫描、测试完整性和邻居页面实际视觉对比均不在此报告中作 Stage2 通过结论。Stage1 中的恶意链接拒绝属于入口合同验证。

## 独立测试与编译原始结果

工作目录：`globalmail-agent/frontend`。本次未重复全量 Vite build。

命令 `pnpm exec tsx --test scripts/observability.test.ts`，退出码0，原始输出：

```text
✔ 仅接受当前运行的真实本地追踪入口，拒绝外链、凭据及伪造成功 (1.6662ms)
✔ 切换运行立即清空旧入口，晚到成功不能串会话 (5.2972ms)
✔ 观测请求失败可重试，离页后晚到响应不恢复入口 (0.9482ms)
ℹ tests 3
ℹ suites 0
ℹ pass 3
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 558.3089
```

测试源码：`scripts/observability.test.ts:12–57`；这三个用例没有走 `useAgentConsole` 的生产 SSE/null record 链路，故全部通过不能反证 HIGH。

命令 `pnpm exec vue-tsc --noEmit`，独立执行结束，退出码0，原始 stdout/stderr **为空**。类型检查通过不代表运行行为通过。

已读取主Agent全量前端测试原始日志 `docs/verification/artifacts/phase11/frontend-tests.log:98–106`，其记录为89项/89通过/0失败、13837.1114ms；本次独立只重跑上述3项。未获取主Agent Vite build 的完整原始输出，本报告不根据声明补写构建通过证据。

## 附录：F11-FE-01 最小复现

无需新建文件。以下 JavaScript 在前端目录通过 PowerShell here-string 管道至 `pnpm exec tsx --input-type=module` 执行。替身只在该独立进程内替换方法，不修改源码、不访问业务库、不给真实后端发送撤销请求。

```javascript
import { createRenderer, defineComponent, computed, h } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useAgentConsole } from './src/composables/use-agent-console.ts'
import { useRunObservability } from './src/composables/use-run-observability.ts'
import { mailApi } from './src/api/mail-agent.ts'
import { agentRunApi } from './src/api/agent-run-api.ts'
import { runContext } from './scripts/agent-run-fixture.ts'
import assert from 'node:assert/strict'

const context = runContext('conversation-1')
mailApi.list = async () => ({ items: [context.conversation], next_cursor: null })
mailApi.detail = async () => context
agentRunApi.detail = async () => { throw new Error('run record unavailable') }
const sources = []
globalThis.EventSource = class {
  onopen = null; onerror = null; listener = null
  constructor() { sources.push(this) }
  addEventListener(type, callback) {
    if (type === 'update') this.listener = callback
  }
  close() {}
}
let calls = 0, revoked = false, model
const trace = 'a'.repeat(32)
const api = { run: async runId => {
  calls++
  return {
    run_id: runId, trace_id: trace,
    trace_url: revoked ? null :
      `http://127.0.0.1:3001/project/local/traces/${trace}`,
    export_status: revoked ? 'revoked' : 'exported',
    reason_code: revoked ? 'trace_revoked' : null
  }
} }
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/agent-runs', component: { render: () => null } }
] })
await router.push('/agent-runs?conversation_id=conversation-1&run_id=run-1')
const renderer = createRenderer({
  patchProp() {}, insert() {}, remove() {}, createElement: () => ({}),
  createText: () => ({}), createComment: () => ({}), setText() {},
  setElementText() {}, parentNode: () => null, nextSibling: () => null
})
const app = renderer.createApp(defineComponent({ setup() {
  const consoleModel = useAgentConsole()
  model = useRunObservability(
    computed(() => consoleModel.run.value?.id), consoleModel.record, api
  )
  return () => h('div')
} }))
app.use(router); app.mount({})
const settle = async () => {
  for (let n = 0; n < 8; n++)
    await new Promise(resolve => setTimeout(resolve, 0))
}
await settle()
assert.equal(model.record.value?.export_status, 'exported')
const before = calls
revoked = true
sources.at(-1).listener({ data: JSON.stringify({
  conversation_id: 'conversation-1', workspace_id: 'w', branch_id: 'b',
  mode: 'simulation', seq: 2, kind: 'attachment.revoked', payload: {}
}) })
await settle()
console.log(JSON.stringify({
  recordDetail: 'unavailable', event: 'attachment.revoked',
  beforeObservabilityGets: before, afterObservabilityGets: calls,
  displayedStatus: model.record.value?.export_status,
  displayedTraceUrl: model.record.value?.trace_url
}))
assert.equal(calls, before)
assert.equal(model.record.value?.export_status, 'exported')
model.dispose(); app.unmount()
```

原始输出，退出码0（该脚本断言缺陷确实存在，故退出0不是产品通过）：

```text
[Vue Router warn]: No active route record was found when calling `onBeforeRouteLeave()`. Make sure you call this function inside a component child of <router-view>. Maybe you called it inside of App.vue?
{"recordDetail":"unavailable","event":"attachment.revoked","beforeObservabilityGets":1,"afterObservabilityGets":1,"displayedStatus":"exported","displayedTraceUrl":"http://127.0.0.1:3001/project/local/traces/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
```

此 renderer 将 console 放在应用根组件，因此产生 route-leave 注册警告；没有调用路由离开，所复现的 SSE 订阅、调用详情读取与观测 watch 均为生产代码。修复后的永久测试应把组件挂在 RouterView 下，并覆盖 KeepAlive 停用/激活和刷新挂起时第二个撤销事件，保留真实生产链路。
