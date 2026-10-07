const localNames = new Set(['MailWorkbench', 'Knowledge', 'SystemStatus'])

export function retainLocalTabs<T extends { name?: unknown }>(tabs: T[]): T[] {
  return tabs.filter((tab) => localNames.has(String(tab.name)))
}
