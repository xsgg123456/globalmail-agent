import type { Plugin } from 'vite'
import { randomUUID } from 'node:crypto'
import { parsePreviewCommand, type PreviewControlEvent } from '../src/preview/control-contract'

export function previewControl(): Plugin {
  const events: PreviewControlEvent[] = []
  const seen = new Map<string, { digest: string; event: PreviewControlEvent }>()
  let sequence = 0
  return {
    name: 'ui-preview-script-control',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/__ui_preview__/events', async (req, res) => {
        const send = (status: number, value: unknown) => {
          res.statusCode = status
          res.setHeader('Content-Type', 'application/json; charset=utf-8')
          res.setHeader('Cache-Control', 'no-store')
          res.end(JSON.stringify(value))
        }
        if (req.method === 'GET') return send(200, { events, scope: 'ui-preview-memory-only' })
        if (req.method !== 'POST') return send(405, { error: 'method_not_allowed' })
        if (req.headers['x-preview-control'] !== 'local-script')
          return send(403, { error: 'preview_control_header_required' })
        const origin = req.headers.origin
        if (origin && origin !== 'http://127.0.0.1:15175' && origin !== 'http://localhost:15175')
          return send(403, { error: 'invalid_origin' })
        try {
          const chunks: Buffer[] = []
          let bytes = 0
          for await (const chunk of req) {
            const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
            bytes += buffer.length
            if (bytes > 65536) return send(413, { error: 'request_too_large' })
            chunks.push(buffer)
          }
          const input: unknown = JSON.parse(Buffer.concat(chunks).toString('utf8'))
          const command = parsePreviewCommand(input)
          if (!command) return send(400, { error: 'invalid_preview_command' })
          const candidate = input as Record<string, unknown>
          if (
            'id' in candidate &&
            (typeof candidate.id !== 'string' || !candidate.id.trim() || candidate.id.length > 100)
          )
            return send(400, { error: 'invalid_command_id' })
          const id =
            typeof candidate.id === 'string' && candidate.id.length <= 100
              ? candidate.id
              : randomUUID()
          const digest = JSON.stringify(command)
          const prior = seen.get(id)
          if (prior)
            return send(
              prior.digest === digest ? 200 : 409,
              prior.digest === digest
                ? { event: prior.event, duplicate: true }
                : { error: 'id_reused_with_different_command' }
            )
          if (seen.size >= 500)
            return send(429, { error: 'restart_preview_to_clear_control_history' })
          if (command.type === 'reset') events.length = 0
          const event = { sequence: ++sequence, id, command }
          events.push(event)
          seen.set(id, { digest, event })
          server.ws.send('globalmail:preview-control', event)
          send(200, { event, scope: 'ui-preview-memory-only' })
        } catch {
          send(400, { error: 'invalid_json' })
        }
      })
    }
  }
}
