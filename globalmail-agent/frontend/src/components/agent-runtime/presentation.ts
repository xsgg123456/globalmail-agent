export const stepIcons = {
  model: 'ri:brain-line',
  tool: 'ri:tools-line',
  check: 'ri:shield-check-line',
  commit: 'ri:mail-send-line'
}
export const stepLabels = {
  model: '模型调用',
  tool: '工具执行',
  check: '程序校验',
  commit: '状态提交'
}
export function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}
export function pretty(value: unknown): string {
  return JSON.stringify(value, null, 2) ?? String(value)
}
export function displayValue(value: unknown): string {
  if (value === true) return '是'
  if (value === false) return '否'
  if (value === null) return '暂无'
  return typeof value === 'string' ? value : pretty(value)
}
const fieldLabels: Record<string, string> = {
  order_id: '订单号',
  operation_id: '申请编号',
  sku: '商品型号',
  brand: '品牌',
  item: '商品',
  paid: '实付金额',
  quantity: '数量',
  intent: '客户诉求',
  observations: '已知事实',
  passed: '核验通过',
  verified: '订单已核验',
  state: '当前状态',
  next_state: '后续状态',
  amount: '金额',
  currency: '币种',
  executed: '已执行',
  actual_execution: '实际执行',
  wait_for: '等待事件',
  received: '已收货',
  inspected: '已质检',
  result: '结果',
  evidence: '依据',
  document: '资料名称',
  section: '章节',
  version: '版本',
  action: '下一步动作',
  next: '后续处理',
  cite: '引用',
  draft: '回复草稿',
  model: '模型',
  temperature: '采样温度',
  enable_thinking: '启用思考',
  thinking_budget: '思考预算',
  risk: '风险迹象',
  reason: '原因',
  source: '来源',
  queried_at: '查询时间',
  facts: '查询事实',
  unknowns: '尚未确认',
  recommendation: '处理建议',
  target: '保存位置',
  business_writes: '业务写入',
  human_review_required: '需要人工审核',
  automatic_reply: '自动回复',
  root_cause: '根因',
  unsupported_claims: '无依据内容',
  input_revision: '输入版本',
  authority: '处理权',
  stale: '输入已过期',
  validated: '校验通过',
  message_id: '回复编号',
  delivery: '投递范围',
  wait: '等待事件',
  receipt_id: '回执编号',
  received_at: '收货时间',
  choice: '客户选择'
}
export function fieldLabel(key: string): string {
  return fieldLabels[key] ?? key
}

export interface RuntimeStep {
  id: string
  kind: 'model' | 'tool' | 'check' | 'commit'
  title: string
  summary: string
  status: string
  time: string
  duration: string
  model?: string
  tool?: string
  thinking: string
  reasoning?: string
  input: unknown
  output: unknown
}
export function stepPreview(step: RuntimeStep) {
  return typeof asRecord(step.output).reason_code === 'string'
    ? String(asRecord(step.output).reason_code) : ''
}
export function thinkingNotice(step: RuntimeStep) {
  if (step.kind !== 'model') return '此节点没有模型思考'
  if (step.thinking === 'off') return '本次调用未启用思考'
  if (step.thinking === 'not_recorded') return '历史调用未保存请求记录'
  if (step.thinking === 'failed') return '调用失败，未取得思考内容'
  return '供应商未返回思考内容'
}
