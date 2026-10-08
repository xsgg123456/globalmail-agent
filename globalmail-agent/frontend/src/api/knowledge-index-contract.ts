import type { Binding, DocumentType } from './knowledge-contract'

export interface EmbeddingProfile {
  key: string
  label: string
  model: string
  dimensions: number
  available: boolean
  endpoint_config_id: string
}
export interface IndexProfiles {
  items: EmbeddingProfile[]
  chunkers: { key: string; label: string; target_tokens: number; max_tokens: number }[]
}
export interface IndexBuild {
  id: string
  version_id: string
  job_id: string
  status: string
  stage: string
  row_version: number
  profile_id: string
  profile_key: string
  chunker_key: string
  chunk_count: number
  embedded_count: number
  cache_hits: number
  eligible: boolean
  usage: Record<string, unknown>[]
  error_code: string | null
  retryable: boolean
  manifest_sha256: string | null
}
export interface ReleaseHead {
  release_id: string | null
  epoch: number
  embedding_profile_id: string | null
}
export interface Publication {
  release_id: string
  release_epoch: number
  build_id: string
  version_id: string
  embedding_profile_id: string
}
export interface IndexStatus {
  builds: IndexBuild[]
  publication: Publication | null
  document_row_version: number
  revocation_epoch: number
  withdrawn: boolean
}
export interface ReleaseEntry {
  document_id: string
  version_id: string
  build_id: string
  title: string
  version_number: number
  profile_id: string
  document_type: DocumentType
}
export interface KnowledgeRelease {
  id: string
  epoch: number
  operation: string
  embedding_profile_id: string | null
  profile: EmbeddingProfile | null
  entries: ReleaseEntry[]
  manifest_sha256: string
  effective_at: string
  created_at: string
  actor: string
}
export interface ReleaseListing {
  head: ReleaseHead
  items: KnowledgeRelease[]
}
export interface IndexCommandResult {
  head?: ReleaseHead
  release?: KnowledgeRelease
  build_id?: string
  job_id?: string
  document_id?: string
  version_id?: string
  version?: number
}
export interface EvidenceReference {
  evidence_id: string
  release_id: string
  release_epoch: number
  document_id: string
  version_id: string
  version_number: number
  build_id: string
  embedding_profile_id: string
  chunk_id: string
  parent_id: string
  title: string
  text: string
  score: number
  page: number[]
  section: string
  figure: string[]
  source_sha256: string
  content_hash: string
  source_kind: string
  completeness: string
  available_at: string
  observed_at: string
  applicability_revision: string
  applicability: Binding[]
  allowed_scope: Record<string, string>
  allowed_modes: string[]
}
export interface SearchInput {
  query: string
  sku: string
  mode: 'simulation' | 'history_replay'
  as_of?: string
  types?: DocumentType[]
  expected_release_epoch?: number
  release_id?: string
}
export interface SearchResult {
  reason:
    | 'ok'
    | 'empty'
    | 'scope_unavailable'
    | 'incomplete_source'
    | 'stale_release'
    | 'provider_error'
  head: ReleaseHead
  candidate_count: number
  evidence: EvidenceReference[]
  usage: { context_proxy_tokens?: number; estimator?: string } | null
  diagnostics: { code: string }[]
}
