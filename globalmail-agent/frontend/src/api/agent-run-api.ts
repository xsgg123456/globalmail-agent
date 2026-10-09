import { mailRequest } from './mail-agent-request'
import type { AgentRunDetail, RunReference } from './agent-run-contract'

export const agentRunApi = {
  detail: (id: string) =>
    mailRequest<AgentRunDetail>({ url: `/runs/${encodeURIComponent(id)}`, method: 'GET' }),
  reference: (runId: string, referenceId: string) =>
    mailRequest<RunReference>({
      url: `/runs/${encodeURIComponent(runId)}/references/${encodeURIComponent(referenceId)}`,
      method: 'GET'
    })
}
export type AgentRunApi = typeof agentRunApi
