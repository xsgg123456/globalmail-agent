// Same scoped bytes reuse their key while an upload outcome is unknown.
export class PendingImageUploads {
  private keys = new Map<string, string>()
  async prepare(file: File, target: { conversation_id?: string; sender_email?: string }) {
    const bytes = await file.arrayBuffer()
    const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))
    const hash = Array.from(digest, (value) => value.toString(16).padStart(2, '0')).join('')
    const identity = JSON.stringify([target.conversation_id, target.sender_email, file.name, hash])
    if (!this.keys.has(identity)) this.keys.set(identity, crypto.randomUUID())
    return { identity, key: this.keys.get(identity)! }
  }
  complete(identity: string) { this.keys.delete(identity) }
}
