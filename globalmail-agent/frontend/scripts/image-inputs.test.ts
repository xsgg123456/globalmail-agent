import { test } from 'node:test'
import assert from 'node:assert/strict'
import { validateImages, imageBindings } from '../src/api/attachment-contract'
import { PendingImageUploads } from '../src/components/mail-agent/pending-image-uploads'

test('图片限制覆盖数量、单张、总量和格式，绑定只传受控ID', () => {
  const file = { size: 10 * 1024 * 1024, type: 'image/png' }
  assert.equal(validateImages([file, file], []), '')
  assert.match(validateImages([file, file, file], []), /合计/)
  assert.match(validateImages(Array(5).fill(file), []), /4张/)
  assert.match(validateImages([{ ...file, size: file.size + 1 }], []), /单张/)
  assert.match(validateImages([{ ...file, type: 'image/gif' }], []), /静态/)
  assert.deepEqual(imageBindings(undefined), [])
})
test('未知上传结果重试同字节同客户复用键，换字节/客户或成功后不复用', async () => {
  const pending = new PendingImageUploads()
  const image = new File(['first'], 'photo.png', { type: 'image/png' })
  const first = await pending.prepare(image, { conversation_id: 'one' })
  assert.equal((await pending.prepare(image, { conversation_id: 'one' })).key, first.key)
  assert.notEqual((await pending.prepare(image, { conversation_id: 'two' })).key, first.key)
  assert.notEqual((await pending.prepare(new File(['second'], 'photo.png'), { conversation_id: 'one' })).key, first.key)
  pending.complete(first.identity)
  assert.notEqual((await pending.prepare(image, { conversation_id: 'one' })).key, first.key)
})
