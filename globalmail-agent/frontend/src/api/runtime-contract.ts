export interface ApiEnvelope<T> {
  code: number
  msg: string
  data: T
  request_id: string
}
const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

export function validateSystemEnvelope<T>(
  body: unknown,
  status: number,
  path: string
): ApiEnvelope<T> {
  if (
    !record(body) ||
    body.code !== status ||
    typeof body.msg !== 'string' ||
    typeof body.request_id !== 'string' ||
    !body.request_id ||
    !record(body.data)
  ) {
    throw new Error('状态接口响应格式异常')
  }
  const data = body.data
  let valid = false
  if (path === '/health/live') valid = status === 200 && data.status === 'ok'
  if (path === '/health/ready') {
    const states = [data.database, data.object_store, data.schema]
    valid =
      states.every((state) => state === 'ready' || state === 'unavailable') &&
      ((status === 200 && data.status === 'ready' && states.every((state) => state === 'ready')) ||
        (status === 503 && data.status === 'degraded' && states.includes('unavailable')))
  }
  if (path === '/runtime-config') {
    const features = data.features
    valid =
      status === 200 &&
      data.mode === 'local_single_user' &&
      data.phase === 2 &&
      typeof data.model_configured === 'boolean' &&
      record(features) &&
      features.conversations === false &&
      features.knowledge === false &&
      features.agent === false
  }
  if (!valid) throw new Error('状态接口数据不符合运行契约')
  return body as unknown as ApiEnvelope<T>
}
