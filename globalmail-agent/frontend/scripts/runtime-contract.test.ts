import { test } from 'node:test'
import assert from 'node:assert/strict'
import { validateSystemEnvelope } from '../src/api/runtime-contract'
const envelope = (code: number, data: unknown) => ({
  code,
  msg: 'status',
  data,
  request_id: 'test-1'
})
test('接受实际HTTP200存活与503依赖故障', () => {
  assert.equal(
    validateSystemEnvelope(envelope(200, { status: 'ok' }), 200, '/health/live').code,
    200
  )
  const degraded = {
    status: 'degraded',
    database: 'unavailable',
    schema: 'unavailable',
    object_store: 'ready'
  }
  assert.deepEqual(
    validateSystemEnvelope(envelope(503, degraded), 503, '/health/ready').data,
    degraded
  )
})
test('拒绝假成功、失配状态及非法配置', () => {
  assert.throws(() => validateSystemEnvelope(envelope(0, { status: 'ok' }), 200, '/health/live'))
  assert.throws(() =>
    validateSystemEnvelope(
      envelope(200, {
        status: 'ready',
        database: 'unavailable',
        schema: 'ready',
        object_store: 'ready'
      }),
      200,
      '/health/ready'
    )
  )
  assert.throws(() => validateSystemEnvelope(envelope(200, {}), 200, '/runtime-config'))
})
test('运行配置仅接受当前阶段实际能力标志', () => {
  const config = {
    mode: 'local_single_user',
    phase: 5,
    model_configured: false,
    features: { conversations: true, business_queries: true, knowledge: true, agent: false }
  }
  assert.deepEqual(
    validateSystemEnvelope(envelope(200, config), 200, '/runtime-config').data,
    config
  )
  assert.throws(() =>
    validateSystemEnvelope(envelope(200, { ...config, phase: 2 }), 200, '/runtime-config')
  )
  assert.throws(() =>
    validateSystemEnvelope(
      envelope(200, { ...config, features: { ...config.features, agent: true } }),
      200,
      '/runtime-config'
    )
  )
})
