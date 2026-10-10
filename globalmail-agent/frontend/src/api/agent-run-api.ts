import { mailRequest } from './mail-agent-request'
import type { AgentRunDetail, RunReference, ConversationAdvice } from './agent-run-contract'

export const agentRunApi = {
  advice: (id: string) => mailRequest<ConversationAdvice>({
    url: `/conversations/${encodeURIComponent(id)}/advice`, method: 'GET'
  }),
  detail: (id: string) =>
    mailRequest<AgentRunDetail>({ url: `/runs/${encodeURIComponent(id)}`, method: 'GET' }),
  reference: (runId: string, referenceId: string) =>
    mailRequest<RunReference>({
      url: `/runs/${encodeURIComponent(runId)}/references/${encodeURIComponent(referenceId)}`,
      method: 'GET'
    })
}
export type AgentRunApi = typeof agentRunApi
