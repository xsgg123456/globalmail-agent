<template>
  <section
    class="box-border shrink-0 p-4 border-r-d flex flex-col min-h-0"
    aria-label="客户会话列表"
  >
    <h1 class="text-base font-medium mb-4">客户会话</h1>
    <ElForm label-position="top" class="mb-3">
      <ElFormItem label="查看模式">
        <ElSelect
          :model-value="mode"
          @update:model-value="$emit('mode', $event)"
          aria-label="查看模式"
        >
          <ElOption label="全部模式" value="" />
          <ElOption label="交互模拟" value="interactive_simulation" />
          <ElOption label="历史回放" value="historical_replay" />
        </ElSelect>
      </ElFormItem>
      <ElFormItem label="处理状态">
        <ElSelect
          :model-value="state"
          @update:model-value="$emit('state', $event)"
          aria-label="处理状态"
        >
          <ElOption label="全部状态" value="" />
          <ElOption label="待人审" value="human_review" />
          <ElOption label="人工已回复 · 待客户" value="human_wait_customer" />
          <ElOption label="排队中" value="queued" />
          <ElOption label="运行中" value="running" />
          <ElOption label="失败" value="failed" />
          <ElOption label="已停止" value="stopped" />
          <ElOption label="已人工结案" value="resolved" />
        </ElSelect>
      </ElFormItem>
    </ElForm>
    <div class="flex flex-wrap gap-2 mb-4">
      <ElButton type="primary" :disabled="busy" @click="$emit('create')">新建模拟</ElButton>
      <ElButton :disabled="busy" @click="$emit('import')">导入案例</ElButton>
      <slot name="scenario" />
    </div>
    <ElAlert v-if="error" :title="error" type="error" :closable="false" show-icon class="mb-3" />
    <ElButton v-if="error" :loading="loading" @click="$emit('refresh')" class="mb-3"
      >重试列表</ElButton
    >
    <ElSkeleton v-if="loading && !items.length" :rows="5" animated />
    <ElEmpty
      v-else-if="!items.length"
      :description="error ? '暂时无法读取会话' : '没有符合条件的会话'"
      :image-size="70"
    />
    <div v-else class="flex-1 overflow-y-auto min-h-0" :aria-busy="loading">
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        class="w-full text-left p-3 rounded-lg mb-2 hover:bg-hover-color cursor-pointer"
        :class="{ 'bg-active-color': selectedId === item.id }"
        :aria-pressed="selectedId === item.id"
        @click="$emit('select', item.id)"
      >
        <div class="flex-c gap-2 mb-2">
          <ElAvatar :size="32" class="shrink-0">{{
            item.sender_key.slice(0, 1).toUpperCase()
          }}</ElAvatar>
          <span class="text-sm font-medium break-all min-w-0">{{ item.sender_key }}</span>
        </div>
        <p class="text-sm text-g-800 break-words mb-2">{{ item.subject || '（无主题）' }}</p>
        <div class="flex flex-wrap gap-1 mb-2">
          <ElTag size="small" type="info">{{ modeLabel(item.mode) }}</ElTag>
          <ElTag
            size="small"
            :type="item.processing_owner === 'human_review' ? 'warning' : 'info'"
            >{{ conversationState(item) }}</ElTag
          >
        </div>
        <p class="text-xs text-g-700">{{ formatMailTime(item.updated_at) }}</p>
        <p v-if="!item.identity_verified" class="text-xs text-g-700 mt-1"
          >客户身份未验证 · 独立案例</p
        >
      </button>
    </div>
    <div class="flex-cb gap-2 pt-3 border-t-d mt-2">
      <ElButton :disabled="!hasPrevious || loading" @click="$emit('previous')">上一页</ElButton>
      <span class="text-xs text-g-700">第 {{ page }} 页</span>
      <ElButton :disabled="!hasNext || loading" @click="$emit('next')">下一页</ElButton>
    </div>
  </section>
</template>
<script setup lang="ts">
  import type { Conversation } from '@/api/mail-agent-contract'
  import { conversationState, formatMailTime, modeLabel } from './mail-labels'
  defineProps<{
    items: Conversation[]
    selectedId: string
    mode: string
    state: string
    loading: boolean
    busy: boolean
    error: string
    page: number
    hasPrevious: boolean
    hasNext: boolean
  }>()
  defineEmits<{
    select: [id: string]
    mode: [value: string]
    state: [value: string]
    create: []
    import: []
    refresh: []
    previous: []
    next: []
  }>()
</script>
<style scoped>
  button:focus-visible {
    outline: 2px solid var(--el-color-primary);
    outline-offset: -2px;
  }
</style>
