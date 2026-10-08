import { mailRequest } from './mail-agent-request'
import type {
  Catalog,
  DocumentDetail,
  KnowledgeDocument,
  KnowledgeResult,
  UploadResult,
  VersionDetail
} from './knowledge-contract'
export const knowledgeApi = {
  catalog: () => mailRequest<Catalog>({ url: '/knowledge/catalog' }),
  list: (filters: Record<string, string>) =>
    mailRequest<{ items: KnowledgeDocument[]; next_cursor: string | null }>({
      url: '/knowledge/documents',
      params: Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== ''))
    }),
  document: (id: string) =>
    mailRequest<DocumentDetail>({ url: `/knowledge/documents/${encodeURIComponent(id)}` }),
  version: (id: string) =>
    mailRequest<VersionDetail>({ url: `/knowledge/versions/${encodeURIComponent(id)}` }),
  command: (path: string, body: Record<string, unknown>, key: string) =>
    mailRequest<KnowledgeResult>({
      url: path,
      method: 'POST',
      data: body,
      headers: { 'Idempotency-Key': key }
    }),
  upload: (file: File, key: string) =>
    mailRequest<UploadResult>({
      url: '/knowledge/uploads',
      method: 'POST',
      params: { filename: file.name, expected_version: 0 },
      data: file,
      headers: { 'Content-Type': 'application/octet-stream', 'Idempotency-Key': key }
    })
}
export type KnowledgeApi = typeof knowledgeApi
