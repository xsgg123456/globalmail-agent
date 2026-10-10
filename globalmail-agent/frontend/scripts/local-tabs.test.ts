import { test } from 'node:test'
import assert from 'node:assert/strict'
import { retainLocalTabs } from '../src/router/local-tabs'

test('清理已持久化的模板页签，保留业务页签和其参数', () => {
  const business = { name: 'Knowledge', path: '/knowledge', query: { tab: 'draft' } }
  const previous = [
    { name: 'Console', path: '/dashboard/console' },
    business,
    { name: 'Login', path: '/auth/login' },
    { path: '/unknown' }
  ]
  assert.deepEqual(retainLocalTabs(previous), [business])
  assert.equal(previous.length, 4)
  assert.deepEqual(retainLocalTabs(retainLocalTabs(previous)), [business])
})

test('预览启动清理已删除的业务/实验室页签与搜索历史，保留有效会话参数', () => {
  const keep = { name: 'PreviewRuns', path: '/agent-runs', query: { run_id: 'demo-run-02-02' } }
  const saved = [
    keep,
    { name: 'PreviewBusiness', path: '/business' },
    { name: 'PreviewSimulation', path: '/simulation' },
    { name: 'PreviewKnowledge', path: '/knowledge' }
  ]
  assert.deepEqual(retainLocalTabs(saved, true), [keep, saved[3]])
  assert.deepEqual(retainLocalTabs(retainLocalTabs(saved, true), true), [keep, saved[3]])
  assert.equal(saved.length, 4)
})
