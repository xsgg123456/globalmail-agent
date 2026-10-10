import type { DemoStep } from './types'

const systemPrompt =
  '【隔离预览构造提示词】你是邮件客服助手。根据当时可见往来与只读工具结果判断。退款、退货、换货、补寄必须客服主导；仅给内部事实、来源、缺口、建议及未发送草稿，不创建售后申请、不执行资金或履约、不自动给客户承诺或发信。人工回复后仍保持此边界。查询失败也交人工。普通咨询、排障、物流可有据回复；危险迹象转人工。客户语言用于草稿，内部记录不进入客户邮件。'
export function model(
  id: string,
  title: string,
  summary: string,
  context: unknown,
  output: unknown,
  reasoning?: string
): DemoStep {
  return {
    id,
    title,
    kind: 'model',
    time: '10:12:02',
    duration: '1.8s',
    summary,
    thinking: reasoning ? 'recorded' : 'off',
    reasoning,
    input: {
      model: 'qwen3.7-plus',
      enable_thinking: Boolean(reasoning),
      ...(reasoning ? { thinking_budget: 2048 } : {}),
      temperature: 0.7,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: JSON.stringify(context, null, 2) }
      ],
      tools: [
        'query_order',
        'query_refund_records',
        'query_return_records',
        'query_replacement_records',
        'query_compatible_part',
        'query_stock',
        'query_shipment',
        'search_knowledge'
      ].map((name) => ({
        type: 'function',
        function: {
          name,
          description: '仅查询本会话关联的Mock业务资料，不修改交易或履约',
          parameters: {
            type: 'object',
            properties:
              name === 'search_knowledge'
                ? { sku: { type: 'string' }, query: { type: 'string' } }
                : { order_id: { type: 'string' } },
            required: name === 'search_knowledge' ? ['sku', 'query'] : ['order_id']
          }
        }
      }))
    },
    output
  }
}
export function tool(
  id: string,
  name: string,
  title: string,
  input: unknown,
  output: unknown
): DemoStep {
  return {
    id,
    title,
    kind: 'tool',
    time: '10:12:04',
    duration: '120ms',
    tool: name,
    summary: `执行 ${name}，结果用于下一步判断`,
    thinking: 'not-applicable',
    input,
    output
  }
}
export function check(id: string, title: string, summary: string, output: unknown): DemoStep {
  return {
    id,
    title,
    summary,
    kind: 'check',
    time: '10:12:08',
    duration: '12ms',
    thinking: 'not-applicable',
    input: { source: '当前可见来信与本轮工具结果' },
    output
  }
}
export function commit(id: string, summary: string, output: unknown): DemoStep {
  return {
    id,
    title: '保存本轮结果',
    kind: 'commit',
    time: '10:12:10',
    duration: '34ms',
    summary,
    thinking: 'not-applicable',
    input: { validated: true },
    output
  }
}
export function timeSteps(run: { startedAt: string; steps: DemoStep[] }) {
  const [hour = 0, minute = 0, second = 0] = run.startedAt.split(':').map(Number)
  const start = hour * 3600 + minute * 60 + second
  run.steps.forEach((step, index) => {
    const elapsed = start + index + 1
    step.time = [Math.floor(elapsed / 3600) % 24, Math.floor(elapsed / 60) % 60, elapsed % 60]
      .map((value) => String(value).padStart(2, '0'))
      .join(':')
  })
}
