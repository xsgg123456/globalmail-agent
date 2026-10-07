import type { Plugin, Connect } from 'vite'

// Vite默认允许IP Host；额外白名单覆盖DNS rebinding和跨来源请求。
export function localAccess(port: number): Plugin {
  const authority = `127.0.0.1:${port}`
  const guard: Connect.NextHandleFunction = (req, res, next) => {
    if (
      req.headers.host !== authority ||
      (req.headers.origin && req.headers.origin !== `http://${authority}`)
    ) {
      res.statusCode = 403
      res.end('Local access only')
      return
    }
    next()
  }
  return {
    name: 'globalmail-local-access',
    configureServer(server) {
      server.middlewares.use(guard)
    },
    configurePreviewServer(server) {
      server.middlewares.use(guard)
    }
  }
}
