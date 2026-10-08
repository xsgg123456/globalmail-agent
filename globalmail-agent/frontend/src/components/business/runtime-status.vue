<template>
  <ElCard class="mb-5" aria-live="polite">
    <template #header>
      <div class="flex-cb gap-3 flex-wrap">
        <span class="font-medium">本机运行状态</span>
        <ElButton :loading="loading" @click="refresh">{{
          errors.length ? '重试' : '刷新状态'
        }}</ElButton>
      </div>
    </template>
    <ElSkeleton v-if="loading" :rows="2" animated />
    <template v-else>
      <div class="flex flex-wrap gap-3">
        <ElTag :type="live ? 'success' : 'danger'">API：{{ live ? '可访问' : '未确认可用' }}</ElTag>
        <ElTag :type="readiness?.database === 'ready' ? 'success' : 'warning'"
          >数据库：{{ label(readiness?.database) }}</ElTag
        >
        <ElTag :type="readiness?.schema === 'ready' ? 'success' : 'warning'"
          >数据结构：{{ label(readiness?.schema) }}</ElTag
        >
        <ElTag :type="readiness?.object_store === 'ready' ? 'success' : 'warning'"
          >对象存储：{{ label(readiness?.object_store) }}</ElTag
        >
        <ElTag type="info"
          >模型：{{
            runtime ? (runtime.model_configured ? '已配置，未验证连接' : '未配置') : '配置未知'
          }}</ElTag
        >
      </div>
      <ElAlert
        v-for="error in errors"
        :key="error"
        class="mt-3"
        :title="error"
        type="error"
        :closable="false"
        show-icon
      />
      <ElAlert
        v-if="readiness?.status === 'degraded'"
        class="mt-3"
        title="运行依赖未全部就绪，请检查本地服务后重试。"
        type="warning"
        :closable="false"
        show-icon
      />
      <p class="mt-3 text-sm text-g-700"
        >本机单用户 · Phase 5 知识维护与人工核对 · 资料尚未发布，Agent 暂未接入</p
      >
      <p v-if="detailed && checkedAt" class="mt-3 text-sm text-g-600">检查时间：{{ checkedAt }}</p>
      <p v-if="detailed && requestIds.length" class="mt-2 text-xs text-g-600 break-all"
        >请求标识：{{ requestIds.join(' / ') }}</p
      >
    </template>
  </ElCard>
</template>
<script setup lang="ts">
  import { useRuntimeStatus } from '@/hooks/core/useRuntimeStatus'
  defineProps<{ detailed?: boolean }>()
  const { loading, live, readiness, runtime, errors, requestIds, checkedAt, refresh } =
    useRuntimeStatus()
  const label = (value?: string) =>
    value === 'ready' ? '就绪' : value === 'unavailable' ? '不可用' : '未知'
</script>
