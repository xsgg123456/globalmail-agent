import type { AppRouteRecord } from '@/types/router'

export const previewRoutes: AppRouteRecord = {
  path: '/',
  name: 'PreviewLayout',
  component: '/index/index',
  meta: { title: 'GlobalMail Agent', icon: 'ri:mail-line' },
  children: [
    {
      path: '/workbench',
      name: 'PreviewMail',
      component: '/ui-preview/mail/index',
      meta: { title: '邮件工作台', icon: 'ri:mail-line', fixedTab: true }
    },
    {
      path: '/agent-runs',
      name: 'PreviewRuns',
      component: '/ui-preview/agent/index',
      meta: { title: 'Agent 运行台', icon: 'ri:robot-2-line' }
    },
    {
      path: '/knowledge',
      name: 'PreviewKnowledge',
      component: '/ui-preview/reference/index',
      meta: { title: '知识库', icon: 'ri:book-open-line' }
    },
    {
      path: '/system-status',
      name: 'PreviewSystem',
      component: '/ui-preview/reference/index',
      meta: { title: '系统状态', icon: 'ri:server-line' }
    }
  ]
}
