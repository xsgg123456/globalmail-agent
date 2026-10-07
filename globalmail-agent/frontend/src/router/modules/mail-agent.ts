import type { AppRouteRecord } from '@/types/router'

export const mailAgentRoutes: AppRouteRecord = {
  path: '/',
  name: 'MailAgentLayout',
  component: '/index/index',
  meta: { title: 'GlobalMail Agent', icon: 'ri:mail-line' },
  children: [
    {
      path: '/workbench',
      name: 'MailWorkbench',
      component: '/mail-agent/index',
      meta: { title: '邮件工作台', icon: 'ri:mail-line', fixedTab: true }
    },
    {
      path: '/knowledge',
      name: 'Knowledge',
      component: '/knowledge/index',
      meta: { title: '知识库', icon: 'ri:book-open-line' }
    },
    {
      path: '/system-status',
      name: 'SystemStatus',
      component: '/system-status/index',
      meta: { title: '系统状态', icon: 'ri:server-line' }
    }
  ]
}
