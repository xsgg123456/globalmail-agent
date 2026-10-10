import { revokeConversationContent } from '../composables/content-invalidations'
import { mailRequest } from './mail-agent-request'

export type DeletionKind = 'conversation' | 'document' | 'attachment'
export type DeletionState = 'revoked' | 'purging' | 'verifying' | 'completed' | 'cleanup_failed' | 'blocked_dependencies'
export interface ImpactCounts extends Record<string, unknown> {
  conversation_ids: string[]
  blocked_document_ids: string[]
}
export interface DeletionImpact {
  expected_version: number
  impact: ImpactCounts
}
export interface DeletionRecord {
  id: string
  journal_seq: number
  target_type: DeletionKind
  target_id: string
  status: DeletionState
  impact: ImpactCounts
  error_code?: string | null
}
export const deletionLabels: Record<DeletionState, string> = {
  revoked: '已停止使用，等待清理', purging: '正在清理', verifying: '正在核验',
  completed: '删除完成', cleanup_failed: '清理失败，可重试', blocked_dependencies: '共享内容阻止删除'
}
function notify(record: DeletionRecord) {
  revokeConversationContent(record.impact.conversation_ids ?? (record.target_type === 'conversation' ? [record.target_id] : []), record.journal_seq)
  return record
}
export const lifecycleApi = {
  impact: (kind: DeletionKind, id: string) => mailRequest<DeletionImpact>({url: `/lifecycle/${kind}/${id}/impact`}),
  create: (kind: DeletionKind, id: string, expectedVersion: number) => mailRequest<DeletionRecord>({
    url: `/lifecycle/${kind}/${id}`, method: 'POST', data: {expected_version: expectedVersion, action: 'delete'}}).then(notify),
  get: (id: string) => mailRequest<DeletionRecord>({url: `/lifecycle/requests/${id}`}).then(notify),
  retry: (id: string) => mailRequest<DeletionRecord>({url: `/lifecycle/requests/${id}/retry`, method: 'POST', data: {}}).then(notify),
  list: () => mailRequest<{items: DeletionRecord[]}>({url: '/lifecycle/requests'}).then(result => { result.items.forEach(notify); return result })
}
