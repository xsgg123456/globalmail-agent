import { mailRequest } from './mail-agent-request'
import type {
  IndexProfiles,
  IndexStatus,
  ReleaseListing,
  IndexCommandResult,
  SearchInput,
  SearchResult,
  EvidenceReference
} from './knowledge-index-contract'

export const knowledgeIndexApi = {
  profiles: () => mailRequest<IndexProfiles>({ url: '/knowledge/index-profiles' }),
  status: (id: string) => mailRequest<IndexStatus>({ url: `/knowledge/versions/${id}/index` }),
  releases: () => mailRequest<ReleaseListing>({ url: '/knowledge/releases' }),
  command: (path: string, data: Record<string, unknown>, key: string) =>
    mailRequest<IndexCommandResult>({
      url: path,
      method: 'POST',
      data,
      headers: { 'Idempotency-Key': key }
    }),
  search: (data: SearchInput) =>
    mailRequest<SearchResult>({ url: '/knowledge/search', method: 'POST', data, timeout: 55000 }),
  reference: (id: string) =>
    mailRequest<{ reference: EvidenceReference; eligible: boolean; reason: string }>({
      url: `/knowledge/references/${id}`
    })
}
export type KnowledgeIndexApi = typeof knowledgeIndexApi
