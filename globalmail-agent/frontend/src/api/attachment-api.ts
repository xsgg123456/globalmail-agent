import { mailRequest, mailBlob } from './mail-agent-request'
import type { ImageAttachment, VisualEvidencePage } from './attachment-contract'

const previewPath = (image: ImageAttachment) =>
  `/attachments/${encodeURIComponent(image.attachment_id)}/preview`

export const attachmentApi = {
  upload: (file: File, target: { conversation_id?: string; sender_email?: string }, key: string) =>
    mailRequest<ImageAttachment>({ url: '/attachments/uploads', method: 'POST',
      params: { ...target, filename: file.name }, data: file,
      headers: { 'Content-Type': 'application/octet-stream', 'Idempotency-Key': key } }),
  preview: (image: ImageAttachment, thumbnail = true) => mailBlob({
    url: previewPath(image),
    params: { conversation_id: image.conversation_id, thumbnail } }),
  thumbnailUrl: (image: ImageAttachment) => `/api/v1${previewPath(image)}?${new URLSearchParams({
    conversation_id: image.conversation_id, thumbnail: 'true' })}`,
  cancel: (id: string) => mailRequest({ url: `/attachments/${encodeURIComponent(id)}/cancel`,
    method: 'POST', data: { expected_version: 0 } }),
  evidence: (image: ImageAttachment) => mailRequest<VisualEvidencePage>({
    url: `/conversations/${encodeURIComponent(image.conversation_id)}/visual-evidence`,
    params: { attachment_id: image.attachment_id } }),
  mutate: (id: string, action: 'corrections' | 'revoke', body: Record<string, unknown>, key: string) =>
    mailRequest({ url: `/attachments/${encodeURIComponent(id)}/${action}`, method: 'POST',
      data: body, headers: { 'Idempotency-Key': key } })
}
