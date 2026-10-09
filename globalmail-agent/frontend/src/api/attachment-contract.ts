export interface ImageAttachment {
  attachment_id: string
  conversation_id: string
  message_id: string | null
  filename: string
  mime_type: string
  size_bytes: number
  width: number | null
  height: number | null
  status: string
  revision: number
  evidence_epoch: number
  cid: string | null
  failure_reason?: string | null
}
export interface VisualEvidence {
  evidence_id: string
  kind: string
  value?: string | null
  key?: string
  raw_text?: string
  ambiguous_characters?: string[]
  reason?: string
  coverage?: string
  quality?: string
  manual: boolean
  source_sha256: string
  location: { type: string }
}
export interface VisualEvidencePage {
  items: VisualEvidence[]
  evidence_revision: number
  coverage: string | null
  quality: string | null
}
export function imageBindings(images: ImageAttachment[] | undefined) {
  return (images ?? []).map(({ attachment_id, cid }) => ({ attachment_id, cid }))
}
export function validateImages(files: readonly Pick<File, 'size' | 'type'>[], existing: readonly ImageAttachment[]) {
  if (existing.length + files.length > 4) return '每封来信最多4张图片'
  if (files.some((file) => file.size > 10 * 1024 * 1024)) return '单张图片最多10 MiB'
  if (files.some((file) => !['image/jpeg', 'image/png', 'image/webp'].includes(file.type))) return '请选择JPEG、PNG或静态WebP图片'
  if ([...existing, ...files].reduce((sum, file) => sum + ('size' in file ? file.size : file.size_bytes), 0) > 20 * 1024 * 1024)
    return '每封来信图片合计最多20 MiB'
  return ''
}
export const imageStatusLabels: Record<string, string> = {
  ready: '待分析', processing: '分析中', understood: '已分析', partial: '部分可读',
  unreadable: '不可读', failed: '技术失败，可显式重试', missing: '缺少图片字节',
  unsupported: '不支持', revoked: '已移除', cancelled: '暂存已取消'
}
