import type { KnowledgeApi } from '../src/api/knowledge-api'
import type { DocumentDetail, VersionDetail } from '../src/api/knowledge-contract'
export const makeDocument = (id = 'd1', vid = 'v1'): DocumentDetail => ({
  document: {
    id,
    title: '安装说明',
    document_type: 'troubleshooting_md',
    brand: 'OUTON',
    source_kind: 'simulation',
    source_reference: '自编模拟',
    allowed_modes: ['simulation'],
    usage_split: 'rag',
    row_version: 1,
    current_version_id: vid,
    current_version_number: 1,
    status: 'needs_review',
    published: false
  },
  versions: [makeVersion(vid).version],
  audits: []
})
export const makeVersion = (id = 'v1'): VersionDetail => ({
  version: {
    id,
    document_id: 'd1',
    number: 1,
    title: '安装说明',
    format: 'md',
    page_count: null,
    row_version: 2,
    status: 'needs_review',
    source_sha256: 'a'.repeat(64),
    parser_profile_id: 'markdown',
    parse_generation: 1,
    parse_sha256: 'b'.repeat(64),
    applicability_sha256: 'c'.repeat(64),
    page_range: null,
    available_at: '2025-01-01T00:00:00Z',
    published: false
  },
  blocks: [],
  assets: [],
  diagnostics: [],
  applicabilities: [],
  jobs: [],
  source_url: '/source',
  source_available: true,
  source_text: '完整正文',
  policy: null,
  review: null,
  diff: null
})
export function makeApi(): KnowledgeApi {
  return {
    catalog: async () => ({ products: [], parser_profiles: [] }),
    list: async () => ({ items: [], next_cursor: null }),
    document: async (id) => makeDocument(id),
    version: async (id) => makeVersion(id),
    command: async () => ({ document_id: 'd1', version_id: 'v1', version: 2 }),
    upload: async () => ({
      object_id: 'o1',
      sha256: 'a'.repeat(64),
      size_bytes: 10,
      format: 'md',
      page_count: null
    })
  }
}
