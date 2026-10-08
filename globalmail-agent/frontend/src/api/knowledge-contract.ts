export type DocumentType = 'manual_pdf' | 'troubleshooting_md' | 'case_md' | 'policy_json'
export interface KnowledgeDocument {
  id: string
  title: string
  document_type: DocumentType
  brand: string | null
  source_kind: string
  source_reference: string
  allowed_modes: string[]
  usage_split: string
  row_version: number
  current_version_id: string
  current_version_number: number
  status: string
  published: false
}
export interface KnowledgeVersion {
  id: string
  document_id: string
  number: number
  title: string
  format: 'pdf' | 'md' | 'json' | 'jsonl'
  page_count: number | null
  row_version: number
  status: string
  source_sha256: string
  parser_profile_id: string
  parse_generation: number
  parse_sha256: string | null
  applicability_sha256: string
  page_range: [number, number] | null
  available_at: string
  published: false
}
export interface Binding {
  section_id: string
  sku: string
  page_start: number | null
  page_end: number | null
  basis: string
}
export interface KnowledgeBlock {
  id: string
  page: number | null
  section_id: string
  type: string
  text: string
  bbox: number[] | null
  figure_id: string | null
  table_rows: string[][]
  asset_ids: string[]
}
export interface KnowledgeAsset {
  id: string
  asset_key: string
  media_type: string
  kind: string
  page: number | null
  url: string
}
export interface KnowledgeJob {
  id: string
  kind: 'knowledge'
  version_id: string
  status: string
  stage: string
  row_version: number
  attempt_no: number
  error_code: string | null
  retryable: boolean
  parser_profile_id: string
}
export interface KnowledgeDiagnostic {
  code: string
  severity: string
  page: number | null
  block_ids: string[]
  asset_ids: string[]
  message: string
  blocks_review: boolean
}
export interface Catalog {
  products: { sku: string; brand: string; name: string }[]
  parser_profiles: { id: string; label: string; available: boolean }[]
}
export interface DocumentDetail {
  document: KnowledgeDocument
  versions: KnowledgeVersion[]
  audits: { id: string; version_id: string; action: string; actor: string; created_at: string }[]
}
export interface PolicyBundle {
  rules: Record<string, unknown>
  description: string
  generator_version: string
  rules_sha256: string
  schema_sha256: string
  description_sha256: string
}
export interface VersionDetail {
  version: KnowledgeVersion
  blocks: KnowledgeBlock[]
  assets: KnowledgeAsset[]
  diagnostics: KnowledgeDiagnostic[]
  applicabilities: Binding[]
  jobs: KnowledgeJob[]
  source_url: string
  source_available: boolean
  source_text: string | null
  policy: PolicyBundle | null
  review: {
    actor: string
    note: string
    excluded_block_ids: string[]
    exclusion_reason: string | null
    created_at: string
  } | null
  diff: {
    source_changed: boolean
    applicability_changed: boolean
    text_diff: string | null
    before_applicabilities: Binding[]
    after_applicabilities: Binding[]
  } | null
}
export interface KnowledgeResult {
  document_id: string
  version_id: string
  version: number
  job_id?: string
}
export interface UploadResult {
  object_id: string
  sha256: string
  size_bytes: number
  format: string
  page_count: number | null
}
