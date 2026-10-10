const localNames = new Set(['MailWorkbench', 'AgentRuns', 'Knowledge', 'SystemStatus'])
const previewNames = new Set(['PreviewMail', 'PreviewRuns', 'PreviewKnowledge', 'PreviewSystem'])

export function retainLocalTabs<T extends { name?: unknown }>(tabs: T[], preview = false): T[] {
  return tabs.filter((tab) => (preview ? previewNames : localNames).has(String(tab.name)))
}
