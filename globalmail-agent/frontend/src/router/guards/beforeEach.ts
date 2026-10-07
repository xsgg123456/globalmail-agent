import type { Router } from 'vue-router'
import NProgress from 'nprogress'
import { useSettingStore } from '@/store/modules/setting'
import { useUserStore } from '@/store/modules/user'
import { useMenuStore } from '@/store/modules/menu'
import { useWorktabStore } from '@/store/modules/worktab'
import { setWorktab } from '@/utils/navigation'
import { setPageTitle } from '@/utils/router'
import { RouteRegistry } from '../core'
import { routeModules } from '../modules'
import { retainLocalTabs } from '../local-tabs'

// 本机单用户入口无需登录、用户接口或伪造令牌。
export function setupBeforeEachGuard(router: Router): void {
  new RouteRegistry(router).register(routeModules)
  useMenuStore().setMenuList(routeModules)
  const tabs = useWorktabStore()
  // 移除模板时期保存的演示页签（catch-all 不能当作有效业务路由）。
  tabs.opened = retainLocalTabs(tabs.opened)
  tabs.keepAliveExclude = []
  const user = useUserStore()
  user.setSearchHistory(retainLocalTabs(user.searchHistory))
  user.setToken('', '')
  user.setLockStatus(false)
  router.beforeEach((to) => {
    if (useSettingStore().showNprogress) NProgress.start()
    if (to.path === '/') return { path: '/workbench', replace: true }
    setWorktab(to)
    setPageTitle(to)
    return true
  })
}

// 保留模板工具的接口兼容；本地入口没有动态登录生命周期。
export const getPendingLoading = () => false
export const resetPendingLoading = () => {}
export const getRouteInitFailed = () => false
export const resetRouteInitState = () => {}
export const resetRouterState = (_delay: number) => {}
