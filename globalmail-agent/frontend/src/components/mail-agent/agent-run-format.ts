import type { AgentRun, ConversationDetail } from '@/api/mail-agent-contract'
import type { RunUsage } from '@/api/agent-run-contract'

const errorLabels: Record<string, string> = {
  model_not_connected: '历史协议记录：当时未接入模型。',
  model_not_configured: '模型未配置，请配置本地服务后显式重试。',
  authentication_error: '模型鉴权失败，请检查本地凭据后显式重试。',
  model_authentication: '模型鉴权失败，请检查本地凭据后显式重试。',
  timeout: '模型请求超时，已保存本轮材料与用量。',
  model_timeout: '模型请求超时，已保存本轮材料与用量。',
  model_parse_error: '模型结果解析失败，本次没有提交回复。',
  understanding_invalid: '理解结果校验失败，本次没有继续执行业务。',
  lease_expired: '任务租约失效，运行已中断。',
  process_interrupted: '本地进程中断，需显式重试。',
  worker_interrupted: '本地进程中断，需显式重试。',
  stopped_by_user: '用户已停止任务，未提交的回复不会出站。',
  user_stopped: '用户已停止任务，未提交的回复不会出站。',
  budget_exhausted: '本轮预算已耗尽；等待新来信，不通过重试重置预算。',
  no_progress: '工具结果没有新增信息，已停止重复调用。',
  stale_context: '输入或依据已变化，本次未提交过期回复。'
}
export const runError = (code: string) =>
  errorLabels[code] ?? `处理未完成（${code}），请核对本轮记录。`
export const outcomeLabels: Record<string, string> = {
  reply_and_wait: '模拟回复已提交 · 等待客户',
  historical_comparison: 'AI 本轮对照 · 未加入历史邮件',
  handoff: '已转人工 · 草稿未发送',
  wait_business: '等待业务条件',
  no_material_update: '没有新的可处理信息',
  protocol_only: '历史任务协议验证 · 当时未接入模型',
  protocol_verified_model_not_connected: '历史任务协议验证 · 当时未接入模型'
}
export const outcomeLabel = (outcome: string) => outcomeLabels[outcome] ?? `本轮结果：${outcome}`
export function retryableRun(detail: ConversationDetail): AgentRun | null {
  const latest = detail.runs.at(-1)
  if (!latest || !['failed', 'stopped', 'interrupted'].includes(latest.status)) return null
  const conversation = detail.conversation
  return conversation.lifecycle === 'open' &&
    conversation.processing_owner === 'agent' &&
    conversation.auto_run_gate !== 'disabled' &&
    latest.input_revision === conversation.input_revision
    ? latest
    : null
}
export const usageTokens = (usage: RunUsage) =>
  `${usage.input_tokens.toLocaleString('zh-CN')} 输入 / ${usage.output_tokens.toLocaleString('zh-CN')} 输出`
export const usageCost = (usage: RunUsage) => (usage.cost === null ? '未知' : String(usage.cost))
export const jsonText = (value: unknown) => JSON.stringify(value, null, 2)
export const waitLabels: Record<string, string> = {
  customer_information: '等待客户补充信息',
  customer_reply: '等待客户回复',
  customer_feedback: '等待客户反馈',
  customer_input: '等待客户补充信息',
  human_execution: '等待人工执行',
  refund_receipt: '等待退款回执',
  return_receipt: '等待退货收件',
  inspection: '等待仓库质检',
  inventory: '等待库存',
  shipment: '等待包裹变化',
  human_review: '等待人审'
}
