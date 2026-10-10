import type { Conversation, ConversationMode, RunStatus } from '@/api/mail-agent-contract'
export const modeLabel = (mode: ConversationMode) =>
  mode === 'historical_replay' ? '历史回放' : '交互模拟'
export const runLabels: Record<RunStatus, string> = {
  queued: '排队中',
  running: 'Agent 处理中',
  completed: '本轮完成',
  handed_off: '已转人工',
  failed: '失败',
  budget_exhausted: '预算耗尽',
  stopped: '已停止',
  superseded: '被新输入替代',
  interrupted: '运行中断',
  cancelled: '已取消'
}
export function conversationState(conversation: Conversation): string {
  if (conversation.lifecycle === 'resolved') return '已人工结案'
  if (conversation.processing_owner === 'human_review') return conversation.human_claimed ? '人工接管中' : '待人工接管'
  if (conversation.processing_owner === 'human_wait_customer') return '人工已回复 · 待客户'
  const labels = {
    idle: '未处理',
    queued: '排队中',
    running: 'Agent 处理中',
    waiting_customer: '等待客户',
    waiting_business: '等待业务',
    failed: '处理失败',
    stopped: '已停止'
  }
  return labels[conversation.scheduling_state]
}
export function formatMailTime(value: string | null): string {
  if (!value) return '未记录'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? '时间不可用'
    : date.toLocaleString('zh-CN', { hour12: false })
}
