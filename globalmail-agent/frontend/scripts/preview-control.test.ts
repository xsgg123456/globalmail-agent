import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, dirname, basename, resolve } from 'node:path'
import { previewControl } from './preview-control'

test('本地预览控制HTTP：校验、去重、冲突、重置和来源隔离', async () => {
  const root = await mkdtemp(join(tmpdir(), 'globalmail-preview-api-'))
  const server = await createServer({
    configFile: false,
    root,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: 0 },
    plugins: [previewControl()]
  })
  try {
    await server.listen()
    const address = server.httpServer!.address()
    assert.ok(address && typeof address !== 'string')
    const url = `http://127.0.0.1:${address.port}/__ui_preview__/events`
    const command = {
      type: 'incoming',
      id: 'same-request',
      conversationId: 'demo-mail-02',
      body: 'Status update?'
    }
    const post = (
      value: unknown,
      headers: Record<string, string> = { 'X-Preview-Control': 'local-script' }
    ) =>
      fetch(url, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify(value)
      })
    assert.equal((await post(command, {})).status, 403)
    assert.equal(
      (
        await post(command, {
          'X-Preview-Control': 'local-script',
          Origin: 'https://untrusted.invalid'
        })
      ).status,
      403
    )
    assert.equal((await post({ ...command, conversationId: 'other-customer' })).status, 400)
    assert.equal((await post({ ...command, body: 'x'.repeat(70000) })).status, 413)
    assert.equal((await post(command)).status, 200)
    const duplicate = await post(command)
    assert.equal(duplicate.status, 200)
    assert.equal((await duplicate.json()).duplicate, true)
    assert.equal((await post({ ...command, body: 'Different body' })).status, 409)
    const snapshot = await (await fetch(url)).json()
    assert.equal(snapshot.events.length, 1)
    assert.equal(snapshot.scope, 'ui-preview-memory-only')
    assert.equal(
      (await post({ type: 'business_update', orderId: 'DEMO-1002', patch: { refund: '已处理' } }))
        .status,
      200
    )
    assert.equal((await post({ type: 'reset', id: 'reset-one' })).status, 200)
    const reset = await (await fetch(url)).json()
    assert.equal(reset.events.length, 1)
    assert.equal(reset.events[0].command.type, 'reset')
    assert.equal((await fetch(url, { method: 'DELETE' })).status, 405)
  } finally {
    await server.close()
    assert.equal(dirname(resolve(root)), resolve(tmpdir()))
    assert.ok(basename(root).startsWith('globalmail-preview-api-'))
    await rm(root, { recursive: true, force: true })
  }
})
