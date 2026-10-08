import type { ConversationDetail, ConversationPage, ActionResult } from './mail-agent-contract'
import { mailRequest } from './mail-agent-request'

export const mailApi = {
  list: (mode: string, state: string, cursor?: string) =>
    mailRequest<ConversationPage>({
      url: '/conversations',
      method: 'GET',
      params: { mode: mode || undefined, state: state || undefined, cursor, limit: 20 }
    }),
  detail: (id: string) =>
    mailRequest<ConversationDetail>({
      url: `/conversations/${encodeURIComponent(id)}`,
      method: 'GET'
    }),
  example: () => mailRequest<Record<string, unknown>>({ url: '/imports/example', method: 'GET' }),
  command: (path: string, payload: Record<string, unknown>, key: string, method = 'POST') =>
    mailRequest<ActionResult>({
      url: path,
      method,
      data: payload,
      headers: { 'Idempotency-Key': key }
    })
}
export type MailApi = typeof mailApi
