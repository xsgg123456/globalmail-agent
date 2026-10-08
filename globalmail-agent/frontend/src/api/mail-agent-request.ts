import axios, { type AxiosRequestConfig } from 'axios'

export class MailApiError extends Error {
  constructor(
    public status: number,
    public category: string,
    public requestId: string
  ) {
    super(messageForError(status, category))
  }
}

export function messageForError(status: number, category: string): string {
  if (status === 409) return '会话内容或状态已更新，请核对最新邮件后再提交。未提交的输入已保留。'
  if (status === 422) return '输入未通过校验，请检查邮箱、正文长度和导入文件格式后重试。'
  if (status === 404) return '记录已不存在，请刷新会话列表。'
  if (status === 503) return '本地服务依赖暂不可用，请检查运行状态后重试。输入已保留。'
  if (category === 'timeout') return '请求超时，结果尚未确认。请重试相同操作，输入已保留。'
  if (category === 'network') return '无法连接本地服务，请确认后端已启动后重试。输入已保留。'
  return '本地服务请求失败，请重试或查看运行状态。输入已保留。'
}

const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

export function unwrapMailEnvelope<T>(body: unknown, status: number): T {
  if (
    !record(body) ||
    body.code !== status ||
    typeof body.msg !== 'string' ||
    typeof body.request_id !== 'string' ||
    !body.request_id
  ) {
    throw new MailApiError(status, 'invalid_response', '')
  }
  if (status < 200 || status >= 300) throw new MailApiError(status, body.msg, body.request_id)
  if (!record(body.data)) {
    throw new MailApiError(status, 'invalid_response', body.request_id)
  }
  return body.data as T
}

const client = axios.create({ baseURL: '/api/v1', timeout: 15000, withCredentials: false })
export async function mailRequest<T>(config: AxiosRequestConfig): Promise<T> {
  try {
    const response = await client.request<unknown>({ ...config, validateStatus: () => true })
    return unwrapMailEnvelope<T>(response.data, response.status)
  } catch (error) {
    if (error instanceof MailApiError) throw error
    if (axios.isAxiosError(error)) {
      throw new MailApiError(0, error.code === 'ECONNABORTED' ? 'timeout' : 'network', '')
    }
    throw new MailApiError(0, 'invalid_response', '')
  }
}

// 结果未知时重用完整命令，快照更新不能静默改变重试的版本或幂等键。
export class PendingCommands {
  private pending = new Map<
    string,
    { identity: string; key: string; payload: Record<string, unknown> }
  >()
  constructor(private makeKey = () => crypto.randomUUID()) {}
  prepare(action: string, identity: unknown, payload: Record<string, unknown>) {
    const fingerprint = JSON.stringify(identity)
    const previous = this.pending.get(action)
    if (previous?.identity === fingerprint) return previous
    const command = {
      identity: fingerprint,
      key: this.makeKey(),
      payload: JSON.parse(JSON.stringify(payload)) as Record<string, unknown>
    }
    this.pending.set(action, command)
    return command
  }
  complete(action: string) {
    this.pending.delete(action)
  }
}
