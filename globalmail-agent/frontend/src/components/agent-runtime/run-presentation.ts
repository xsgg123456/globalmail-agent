import type { AgentRunDetail } from '@/api/agent-run-contract'
import type { AgentRun } from '@/api/mail-agent-contract'
import { formatMailTime, runLabels } from '@/components/mail-agent/mail-labels'
import type { RuntimeStep } from './presentation'

const stages: Record<string, string> = {
  understand: '理解来信', understanding: '理解来信', decide: '选择工具与动作',
  decision: '选择工具与动作', outcome_review: '核验输出依据', validation: '核验输出依据'
}
const states: Record<string, string> = {
  running: '执行中', completed: '已完成', failed: '失败', not_recorded: '未记录',
  revoked: '内容已撤回', reserved: '等待回执', executed: '已执行', rejected: '已拒绝'
}
export function duration(start: string | null, end: string | null) {
  if (!start || !end) return '未记录'
  const elapsed = new Date(end).getTime() - new Date(start).getTime()
  return Number.isFinite(elapsed) && elapsed >= 0 ? `${(elapsed / 1000).toFixed(1)}s` : '时间不可用'
}
export function executionSteps(detail: AgentRunDetail): RuntimeStep[] {
  const models: RuntimeStep[] = (detail.model_calls ?? []).map((call) => ({
    id: call.id, kind: 'model', title: stages[call.stage] ?? call.stage,
    summary: call.error_code ?? `${call.model} · ${call.request_key}`,
    status: states[call.status] ?? call.status, time: formatMailTime(call.created_at),
    duration: duration(call.created_at, call.finished_at), model: call.model,
    thinking: call.reasoning_state === 'returned' ? 'recorded'
      : call.reasoning_state === 'disabled' ? 'off' : call.reasoning_state,
    reasoning: typeof call.response?.reasoning_content === 'string' ? call.response.reasoning_content : undefined,
    input: call.request ?? { record_status: '历史调用未保存请求快照' },
    output: call.response ?? { status: call.status, error_code: call.error_code },
  }))
  const tools: RuntimeStep[] = detail.tools.map((call) => ({
    id: call.id, kind: 'tool', title: call.name, summary: call.reason_code ?? '等待工具返回',
    status: states[call.status] ?? call.status, time: formatMailTime(call.created_at),
    duration: '未记录', tool: call.name, thinking: 'none', input: call.arguments, output: call.result,
  }))
  const artifacts: RuntimeStep[] = detail.artifacts.map((item) => ({
    id: item.id, kind: 'commit', title: item.outcome === 'human_advice' || item.outcome === 'handoff'
      ? '保存内部建议' : '保存本轮处理结果', summary: item.outcome,
    status: runLabels[detail.run.status], time: formatMailTime(item.created_at), duration: '未记录',
    thinking: 'none', input: { input_revision: detail.run.input_revision }, output: {
      outcome: item.outcome, body: item.body, advice: detail.advice, citation_ids: item.citation_ids
    }
  }))
  const dates = new Map<string, string>([
    ...(detail.model_calls ?? []).map((item) => [item.id, item.created_at] as [string, string]),
    ...detail.tools.map((item) => [item.id, item.created_at] as [string, string]),
    ...detail.artifacts.map((item) => [item.id, item.created_at] as [string, string]),
  ])
  return [...models, ...tools, ...artifacts].sort((a, b) =>
    new Date(dates.get(a.id)!).getTime() - new Date(dates.get(b.id)!).getTime())
}
export function conversationRounds(runs: AgentRun[]) {
  const cycles = [...new Set(runs.map((run) => run.processing_cycle_id))]
  return cycles.map((id, index) => ({ round: index + 1, cycle: id,
    attempts: runs.filter((run) => run.processing_cycle_id === id) }))
}
