import { reactive } from 'vue'
// Retain command inputs when drawers close while a response remains unconfirmed.
const builds = reactive<Record<string, { profile: string; chunker: string }>>({})
export const releasePreferences = reactive({
  target: 'qwen3.7-text-embedding',
  selected: {} as Record<string, string>
})
export function buildPreferences(id: string) {
  return (builds[id] ||= { profile: 'qwen3.7-text-embedding', chunker: 'structure_v1_500' })
}
