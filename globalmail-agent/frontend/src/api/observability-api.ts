import { mailRequest } from './mail-agent-request'

export type ExportStatus = 'disabled' | 'local_only' | 'pending' | 'exported' | 'degraded' | 'revoked'
export interface RunObservability {
  run_id: string
  trace_id: string | null
  trace_url: string | null
  export_status: ExportStatus
  reason_code: string | null
}

const statuses: ExportStatus[] = ['disabled', 'local_only', 'pending', 'exported', 'degraded', 'revoked']
export function validateObservability(value: unknown, runId: string): RunObservability {
  if (typeof value !== 'object' || value === null) throw new Error('观测响应无效，请刷新重试。')
  const row = value as Record<string, unknown>
  if (row.run_id !== runId || !statuses.includes(row.export_status as ExportStatus) ||
    !(row.trace_id === null || typeof row.trace_id === 'string' && /^[a-f0-9]{32}$/.test(row.trace_id)) ||
    !(row.reason_code === null || typeof row.reason_code === 'string') ||
    !(row.trace_url === null || typeof row.trace_url === 'string')) {
    throw new Error('观测响应与当前运行不匹配，请刷新重试。')
  }
  if (row.trace_url !== null) {
    const url = new URL(row.trace_url as string)
    if (url.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(url.hostname) ||
      url.username || url.password || url.search || url.hash || !row.trace_id ||
      !new RegExp(`^/project/[a-zA-Z0-9_-]+/traces/${row.trace_id}$`).test(url.pathname)) {
      throw new Error('观测链接无效，请检查本地观测配置。')
    }
  }
  if (row.export_status === 'exported' && row.trace_url === null) {
    throw new Error('观测链接尚不可用，请刷新重试。')
  }
  return row as unknown as RunObservability
}

export const observabilityApi = {
  async run(runId: string): Promise<RunObservability> {
    const result = await mailRequest<unknown>({
      url: `/observability/runs/${encodeURIComponent(runId)}`, method: 'GET'
    })
    return validateObservability(result, runId)
  }
}
