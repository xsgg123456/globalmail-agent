import { mailAgentRoutes } from './mail-agent'
import { previewRoutes } from './ui-preview'
export const routeModules = [
  import.meta.env.MODE === 'ui-preview' ? previewRoutes : mailAgentRoutes
]
