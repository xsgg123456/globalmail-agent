import type { RiskDecision } from '@/api/mail-agent-contract'
import type { ImageAttachment } from '@/api/attachment-contract'

export interface IncomingInput {
  subject: string
  body: string
  attachments?: ImageAttachment[]
}
export interface HumanInput {
  reply: string
  note: string
  risk_decision?: RiskDecision
}
export interface NewConversationInput extends IncomingInput {
  sender_email: string
}

export function validateIncoming(input: IncomingInput): Record<string, string> {
  const errors: Record<string, string> = {}
  if (input.subject.length > 500) errors.subject = '主题最多 500 字符'
  if (!input.body.trim() && !input.attachments?.some((image) => image.status === 'ready')) errors.body = '请填写客户来信正文，或上传至少一张图片'
  else if (input.body.length > 20000) errors.body = '正文最多 20,000 字符'
  return errors
}
export function validateNewConversation(input: NewConversationInput): Record<string, string> {
  const errors = validateIncoming(input)
  if (
    input.sender_email.length > 320 ||
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.sender_email.trim())
  ) {
    errors.sender_email = '请输入有效演示邮箱，例如 customer@example.test'
  }
  return errors
}
export function validateHuman(input: HumanInput, completion: boolean): Record<string, string> {
  const errors: Record<string, string> = {}
  if (completion && !input.reply.trim()) errors.reply = '完成回复前请填写正文'
  if (input.reply.length > 20000) errors.reply = '人工回复最多 20,000 字符'
  if (input.note.length > 5000) errors.note = '备注最多 5,000 字符'
  else if (
    completion &&
    input.risk_decision &&
    input.risk_decision !== 'keep_active' &&
    !input.note.trim()
  )
    errors.note = '请填写风险已处理或误判的复核依据'
  return errors
}

export async function readImportFile(file: File): Promise<unknown> {
  if (!file.name.toLowerCase().endsWith('.json')) throw new Error('请选择 JSON 案例文件')
  if (file.size > 5 * 1024 * 1024) throw new Error('导入文件不能超过 5 MiB')
  try {
    return JSON.parse(await file.text()) as unknown
  } catch {
    throw new Error('文件不是有效 JSON，请按样例检查格式')
  }
}
