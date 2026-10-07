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
