<template>
  <ElDrawer
    :model-value="Boolean(selection)"
    title="本轮引用与资料"
    size="min(600px, 100vw)"
    append-to-body
    @update:model-value="!$event && $emit('close')"
  >
    <div class="space-y-4 min-w-0">
      <ElButton :loading="loading" @click="refresh">重新检查引用</ElButton>
      <ElAlert v-if="error" :title="error" type="error" :closable="false" show-icon />
      <ElSkeleton v-if="loading" :rows="5" animated />
      <template v-else-if="result">
        <ElAlert
          :title="result.eligible ? '当前仍可引用' : '引用已停用或不适用于当前运行'"
          :description="reasonLabels[result.reason] || result.reason"
          :type="result.eligible ? 'success' : 'warning'"
          :closable="false"
          show-icon
        />
        <h3 class="font-medium break-words"
          >{{ result.reference.title }} · 第 {{ result.reference.version_number }} 版</h3
        >
        <p class="text-sm text-g-700 break-words"
          >{{
            result.reference.page.length ? `原件第 ${result.reference.page.join('、')} 页 · ` : ''
          }}{{ result.reference.section }}</p
        >
        <p class="text-sm break-words"
          >适用型号：{{
            [...new Set(result.reference.applicability.map((binding) => binding.sku))].join('、') ||
            '未提供'
          }}</p
        >
        <p class="text-sm text-g-700"
          >来源：{{ result.reference.source_kind }} · {{ result.reference.completeness }}</p
        >
        <p class="text-sm text-g-700"
          >可用时间：{{ formatMailTime(result.reference.available_at) }}</p
        >
        <pre
          v-if="result.eligible"
          class="text-sm leading-relaxed font-inherit whitespace-pre-wrap break-words"
          >{{ result.reference.text || '没有可读片段' }}</pre
        >
        <p v-else class="text-sm text-g-700">已停用内容不作为当前依据展示。</p>
        <details class="text-xs text-g-700 break-all">
          <summary>来源与发布凭证</summary>
          <p class="mt-2">引用：{{ result.reference.evidence_id }}</p>
          <p>发布：{{ result.reference.release_id }} · {{ result.reference.release_epoch }}</p>
          <p>原件 SHA：{{ result.reference.source_sha256 }}</p>
          <p>内容 SHA：{{ result.reference.content_hash }}</p>
        </details>
      </template>
    </div>
  </ElDrawer>
</template>
<script setup lang="ts">
  import { onScopeDispose, toRef } from 'vue'
  import { useRunReference, type ReferenceSelection } from '@/composables/useRunReference'
  import { formatMailTime } from './mail-labels'
  const props = defineProps<{ selection: ReferenceSelection | null }>()
  defineEmits<{ close: [] }>()
  const { result, loading, error, refresh, dispose } = useRunReference(toRef(props, 'selection'))
  onScopeDispose(dispose)
  const reasonLabels: Record<string, string> = {
    ok: '已核验本轮关联、版本与适用范围。',
    revoked: '资料已撤销。',
    withdrawn: '资料已下架。',
    stale_release: '发布资料已变化。',
    deleted: '资料已删除。',
    scope_unavailable: '当前用途或范围不可读取。',
    reference_ineligible: '当前资料不满足引用条件。'
  }
</script>
