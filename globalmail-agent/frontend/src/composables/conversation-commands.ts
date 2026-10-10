import { PendingCommands } from '@/api/mail-agent-request'

/** A revoked conversation must not retain a retry payload or clear another case's retry. */
export class ConversationCommands extends PendingCommands {
  private owners = new Map<string, string>()
  prepareFor(id: string, path: string, identity: unknown, payload: Record<string, unknown>) {
    this.owners.set(path, id)
    return this.prepare(path, identity, payload)
  }
  override complete(path: string) {
    this.owners.delete(path)
    super.complete(path)
  }
  forget(id: string) {
    for (const [path, owner] of this.owners) if (owner === id) this.complete(path)
  }
}

export const mailErrorMessage = (error: unknown) =>
  error instanceof Error ? error.message : '本地服务请求失败，请重试。'
