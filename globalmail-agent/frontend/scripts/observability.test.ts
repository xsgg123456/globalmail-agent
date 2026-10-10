import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ref } from 'vue'
import { validateObservability, type RunObservability } from '../src/api/observability-api'
import { useRunObservability } from '../src/composables/use-run-observability'

const trace = 'a'.repeat(32)
const value = (runId = 'run-1'): RunObservability => ({ run_id: runId, trace_id: trace,
  export_status: 'exported', trace_url: `http://127.0.0.1:3001/project/local/traces/${trace}`, reason_code: null })
const settle = () => new Promise<void>(resolve => setTimeout(resolve, 0))

test('仅接受当前运行的真实本地追踪入口，拒绝外链、凭据及伪造成功', () => {
  assert.deepEqual(validateObservability(value(), 'run-1'), value())
  for (const patch of [
    { run_id: 'other' }, { trace_id: 'bad' }, { trace_url: 'javascript:alert(1)' },
    { trace_url: `http://example.com/project/local/traces/${trace}` },
    { trace_url: `http://secret@127.0.0.1:3001/project/local/traces/${trace}` },
    { trace_url: `http://127.0.0.1:3001/project/local/traces/${trace}?token=secret` },
    { trace_url: `http://127.0.0.1:3001/project/local/traces/${'b'.repeat(32)}` },
    { trace_url: null }, { export_status: 'success' }
  ]) assert.throws(() => validateObservability({ ...value(), ...patch }, 'run-1'))
  assert.equal(validateObservability({ ...value(), export_status: 'disabled', trace_url: null }, 'run-1').export_status, 'disabled')
})

test('切换运行立即清空旧入口，晚到成功不能串会话', async () => {
  const id = ref<string | undefined>('old'), revision = ref<unknown>(0)
  let finish: ((value: RunObservability) => void) | undefined
  const model = useRunObservability(id, revision, { run: async runId => runId === 'old'
    ? new Promise(resolve => { finish = resolve }) : value(runId) })
  id.value = 'new'
  assert.equal(model.record.value, null)
  await settle()
  finish?.(value('old'))
  await settle()
  assert.equal(model.record.value?.run_id, 'new')
  id.value = undefined
  assert.equal(model.record.value, null)
  model.dispose()
})

test('观测请求失败可重试，离页后晚到响应不恢复入口', async () => {
  const id = ref<string | undefined>('run-1'), revision = ref<unknown>(0)
  let fail = true, finish: ((value: RunObservability) => void) | undefined
  const model = useRunObservability(id, revision, { run: async () => {
    if (fail) throw new Error('network')
    return new Promise(resolve => { finish = resolve })
  } })
  await settle()
  assert.equal(model.loading.value, false)
  assert.match(model.error.value, /仍可查看/)
  fail = false
  const pending = model.refresh()
  model.suspend()
  finish?.(value())
  await pending
  assert.equal(model.record.value, null)
  model.dispose()
})
