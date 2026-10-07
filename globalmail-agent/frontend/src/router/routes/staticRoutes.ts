import type { AppRouteRecordRaw } from '@/utils/router'
export const staticRoutes: AppRouteRecordRaw[] = [
  {
    path: '/:pathMatch(.*)*',
    name: 'Exception404',
    component: () => import('@views/exception/404/index.vue'),
    meta: { title: '页面不存在', isHideTab: true }
  }
]
