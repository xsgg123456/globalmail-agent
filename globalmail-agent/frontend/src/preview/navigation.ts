import type { DemoRun } from './types'

export function conversationRuns(runs: DemoRun[], conversationId: string) {
  return runs
    .filter((run) => run.conversationId === conversationId)
    .sort((a, b) => a.round - b.round)
}
export function resolvePreviewRun(
  runs: DemoRun[],
  conversationId: string,
  requestedId: unknown,
  rememberedId?: string
) {
  const scoped = conversationRuns(runs, conversationId)
  return (
    scoped.find((run) => run.id === requestedId) ??
    scoped.find((run) => run.id === rememberedId) ??
    scoped.at(-1)!
  )
}
