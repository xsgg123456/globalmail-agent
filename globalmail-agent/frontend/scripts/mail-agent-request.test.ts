import { test } from 'node:test'
import assert from 'node:assert/strict'
import { reactive } from 'vue'
import { MailApiError, PendingCommands, unwrapMailEnvelope } from '../src/api/mail-agent-request'
import {
  readImportFile,
  validateHuman,
  validateIncoming,
  validateNewConversation
} from '../src/components/mail-agent/mail-inputs'

test('接受真实200/202资源，拒绝HTTP和envelope不一致以及空资源', () => {
  const envelope = (code: number, data: unknown) => ({ code, data, msg: 'ok', request_id: 'r-1' })
  assert.deepEqual(unwrapMailEnvelope(envelope(202, { conversation_id: 'c' }), 202), {
    conversation_id: 'c'
  })
  assert.deepEqual(unwrapMailEnvelope(envelope(200, { items: [] }), 200), { items: [] })
  assert.throws(() => unwrapMailEnvelope(envelope(200, {}), 202), MailApiError)
  assert.throws(() => unwrapMailEnvelope(envelope(200, null), 200), MailApiError)
  assert.throws(() => unwrapMailEnvelope(envelope(202, 'fake success'), 202), MailApiError)
  assert.throws(
    () => unwrapMailEnvelope({ ...envelope(409, null), msg: 'secret database credentials' }, 409),
    (error: unknown) =>
      error instanceof MailApiError &&
      error.message.includes('已保留') &&
      !error.message.includes('secret')
  )
})

test('未知结果重试沿用key和原payload版本，只有新参数或已完成才另建命令', () => {
  let sequence = 0
  const commands = new PendingCommands(() => `key-${++sequence}`)
  const first = commands.prepare(
    'append',
    { body: 'line1\nline2' },
    { body: 'line1\nline2', expected_version: 2 }
  )
  const retry = commands.prepare(
    'append',
    { body: 'line1\nline2' },
    { body: 'line1\nline2', expected_version: 3 }
  )
  assert.equal(first.key, retry.key)
  assert.equal(retry.payload.expected_version, 2)
  const edit = commands.prepare(
    'append',
    { body: 'changed' },
    { body: 'changed', expected_version: 3 }
  )
  assert.notEqual(edit.key, first.key)
  commands.complete('append')
  assert.notEqual(commands.prepare('append', { body: 'changed' }, edit.payload).key, edit.key)
})

test('响应式导入对象按HTTP JSON编码快照，编辑后不改变未知结果重试内容', () => {
  const source = reactive({ expected_version: 0, messages: [{ body: 'Original imported email' }] })
  const commands = new PendingCommands(() => 'import-key')
  const first = commands.prepare('import', source, { ...source })
  assert.deepEqual(first.payload, {
    expected_version: 0,
    messages: [{ body: 'Original imported email' }]
  })
  source.messages[0].body = 'Edited after sending'
  assert.equal((first.payload.messages as { body: string }[])[0].body, 'Original imported email')
  const retry = commands.prepare(
    'import',
    { expected_version: 0, messages: [{ body: 'Original imported email' }] },
    source
  )
  assert.equal(retry, first)
})

test('表单校验覆盖空白、长度、邮箱及保留换行', () => {
  assert.equal(validateIncoming({ subject: '', body: ' \n ' }).body, '请填写客户来信正文，或上传至少一张图片')
  assert.deepEqual(
    validateIncoming({ subject: '', body: '<script>unsafe</script>\nsecond line' }),
    {}
  )
  assert.ok(validateIncoming({ subject: 'a'.repeat(501), body: 'x'.repeat(20001) }).body)
  assert.ok(
    validateNewConversation({ sender_email: 'bad address', subject: '', body: 'hello' })
      .sender_email
  )
  assert.deepEqual(
    validateNewConversation({ sender_email: 'a+b@example.test', subject: '', body: 'hello' }),
    {}
  )
  assert.ok(validateHuman({ reply: '', note: '' }, true).reply)
  assert.deepEqual(validateHuman({ reply: '', note: 'saved note' }, false), {})
  assert.ok(validateHuman({ reply: 'reply', note: 'x'.repeat(5001) }, true).note)
})

test('受控文件输入读取JSON，拒绝错误扩展、非法JSON和超限文件', async () => {
  assert.deepEqual(await readImportFile(new File(['{"messages":[]}'], 'case.json')), {
    messages: []
  })
  await assert.rejects(readImportFile(new File(['{}'], 'case.txt')), /JSON 案例/)
  await assert.rejects(readImportFile(new File(['{'], 'case.json')), /有效 JSON/)
  await assert.rejects(
    readImportFile(new File([new Uint8Array(5 * 1024 * 1024 + 1)], 'case.json')),
    /5 MiB/
  )
})

test('风险明确处理或更正需非空依据；普通完成和保存草稿不推断风险决定', () => {
  for (const risk_decision of ['resolved_by_human', 'corrected_by_human'] as const) {
    assert.match(
      validateHuman({ reply: '人工回复', note: ' \n ', risk_decision }, true).note,
      /复核依据/
    )
    assert.deepEqual(
      validateHuman({ reply: '人工回复', note: '已核对证据', risk_decision }, true),
      {}
    )
    assert.deepEqual(validateHuman({ reply: '', note: '', risk_decision }, false), {})
  }
  assert.deepEqual(validateHuman({ reply: '风险已解决', note: '' }, true), {})
  assert.deepEqual(
    validateHuman({ reply: '人工回复', note: '', risk_decision: 'keep_active' }, true),
    {}
  )
})
