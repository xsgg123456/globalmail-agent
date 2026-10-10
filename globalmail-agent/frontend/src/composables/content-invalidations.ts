/** Only opaque conversation IDs and deletion watermarks cross browser tabs. */
export function createContentInvalidations() {
  const generations = new Map<string, number>()
  const revisions = new Map<string, number>()
  const listeners = new Set<(id: string) => void>()
  function invalidate(ids: string[], revision?: number) {
    for (const id of new Set(ids)) {
      if (revision !== undefined && revision <= (revisions.get(id) ?? 0)) continue
      if (revision !== undefined) revisions.set(id, revision)
      generations.set(id, (generations.get(id) ?? 0) + 1)
      for (const notify of listeners) notify(id)
    }
  }
  return {
    invalidate,
    observe: (id: string, revision: number) => invalidate([id], revision),
    generation: (id: string) => generations.get(id) ?? 0,
    revision: (id: string) => revisions.get(id) ?? 0,
    subscribe(callback: (id: string) => void) {
      listeners.add(callback)
      return () => { listeners.delete(callback) }
    }
  }
}
export const contentInvalidations = createContentInvalidations()
const channel = typeof window !== 'undefined' && typeof BroadcastChannel !== 'undefined'
  ? new BroadcastChannel('globalmail-content-revoked') : null
if (channel) channel.onmessage = ({ data }: MessageEvent<unknown>) => {
  if (typeof data !== 'object' || !data) return
  const message = data as { ids?: unknown; revision?: unknown }
  if (!Array.isArray(message.ids) || !message.ids.every(id => typeof id === 'string')) return
  if (message.revision !== undefined && (!Number.isSafeInteger(message.revision) || Number(message.revision) < 1)) return
  contentInvalidations.invalidate(message.ids, message.revision as number | undefined)
}
export function revokeConversationContent(ids: string[], revision?: number) {
  contentInvalidations.invalidate(ids, revision)
  channel?.postMessage({ ids, revision })
}
