import { ref, onMounted } from 'vue'
import { getSystemEnvelope } from '@/utils/http'

type DependencyState = 'ready' | 'unavailable'
interface Readiness {
  status: 'ready' | 'degraded'
  database: DependencyState
  object_store: DependencyState
  schema: DependencyState
}
interface RuntimeConfig {
  mode: 'local_single_user'
  phase: 6
  features: { conversations: true; business_queries: true; knowledge: true; agent: false }
  model_configured: boolean
}
export function useRuntimeStatus() {
  const loading = ref(false)
  const live = ref(false)
  const readiness = ref<Readiness | null>(null)
  const runtime = ref<RuntimeConfig | null>(null)
  const errors = ref<string[]>([])
  const requestIds = ref<string[]>([])
  const checkedAt = ref('')
  async function refresh() {
    if (loading.value) return
    loading.value = true
    live.value = false
    readiness.value = null
    runtime.value = null
    errors.value = []
    requestIds.value = []
    const results = await Promise.allSettled([
      getSystemEnvelope<{ status: 'ok' }>('/health/live'),
      getSystemEnvelope<Readiness>('/health/ready'),
      getSystemEnvelope<RuntimeConfig>('/runtime-config')
    ])
    const [livenessResult, readyResult, configResult] = results
    if (livenessResult.status === 'fulfilled')
      live.value = livenessResult.value.data.status === 'ok'
    if (readyResult.status === 'fulfilled') readiness.value = readyResult.value.data
    if (configResult.status === 'fulfilled') runtime.value = configResult.value.data
    const labels = ['API存活检查', '依赖就绪检查', '运行配置']
    results.forEach((result, index) => {
      if (result.status === 'rejected')
        errors.value.push(`${labels[index]}失败，请确认本地后端已启动后重试。`)
      else requestIds.value.push(result.value.request_id)
    })
    checkedAt.value = new Date().toLocaleTimeString('zh-CN')
    loading.value = false
  }
  onMounted(refresh)
  return { loading, live, readiness, runtime, errors, requestIds, checkedAt, refresh }
}
