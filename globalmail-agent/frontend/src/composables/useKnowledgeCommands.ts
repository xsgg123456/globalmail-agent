import { MailApiError, PendingCommands } from '@/api/mail-agent-request'
import { knowledgeApi, type KnowledgeApi } from '@/api/knowledge-api'
export function useKnowledgeCommands(api: KnowledgeApi = knowledgeApi) {
  const pending = new PendingCommands()
  const uploads = new Map<
    string,
    { key: string; result?: Awaited<ReturnType<KnowledgeApi['upload']>> }
  >()
  async function command(path: string, payload: Record<string, unknown>) {
    const { expected_version: _revision, ...identity } = payload
    const frozen = pending.prepare(path, identity, payload)
    try {
      const result = await api.command(path, frozen.payload, frozen.key)
      pending.complete(path)
      return result
    } catch (error) {
      if (error instanceof MailApiError && error.status >= 400 && error.status < 500)
        pending.complete(path)
      throw error
    }
  }
  async function upload(file: File) {
    if (file.size > 50 * 1024 * 1024) throw new Error('文件不能超过 50 MiB。')
    const hash = Array.from(
      new Uint8Array(await crypto.subtle.digest('SHA-256', await file.arrayBuffer())),
      (byte) => byte.toString(16).padStart(2, '0')
    ).join('')
    const id = JSON.stringify([file.name, hash])
    const entry = uploads.get(id) || { key: crypto.randomUUID() }
    uploads.set(id, entry)
    if (!entry.result) entry.result = await api.upload(file, entry.key)
    return entry.result
  }
  return { command, upload }
}
