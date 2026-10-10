<template>
  <aside class="mail-sidebar shrink-0 border-r-d flex flex-col min-h-0" aria-label="客户会话">
    <div class="p-4 border-b-d">
      <div class="flex-cb mb-3"><h2 class="text-sm font-medium">客户会话</h2><ElButton link :loading="loading" @click="$emit('refresh')">刷新</ElButton></div>
      <ElInput v-model="search" clearable placeholder="搜索本页客户、邮件主题" aria-label="搜索客户会话" />
      <ElSelect :model-value="state" class="w-full mt-3" placeholder="全部状态" aria-label="筛选会话状态" @update:model-value="$emit('filter', $event)">
        <ElOption label="全部状态" value="" /><ElOption label="人工处理中" value="human_review" /><ElOption label="人工回复后待客户" value="human_wait_customer" /><ElOption label="等待客户" value="waiting_customer" /><ElOption label="已解决" value="resolved" />
      </ElSelect>
    </div>
    <ElAlert v-if="error" :title="error" type="error" :closable="false" class="m-3" />
    <div v-loading="loading" class="overflow-y-auto flex-1">
      <button v-for="item in filtered" :key="item.id" type="button" class="w-full p-4 border-b-d text-left hover:bg-active-color transition-colors" :class="item.id === selectedId ? 'bg-theme/10' : ''" @click="$emit('select', item.id)">
        <div class="flex-cb gap-2"><span class="font-medium text-sm truncate">{{ item.sender_key }}</span><span class="text-xs text-g-600 shrink-0">{{ formatMailTime(item.updated_at).split(' ').at(-1)?.slice(0,5) }}</span></div>
        <p class="text-xs text-g-700 mt-2 truncate">{{ item.subject }}</p><div class="mt-3"><ElTag size="small" effect="plain">{{ conversationState(item) }}</ElTag></div>
      </button>
      <ElEmpty v-if="!loading && !filtered.length" description="没有符合筛选的会话" :image-size="60" />
    </div>
    <div class="p-3 border-t-d flex-cb gap-2 text-xs"><ElButton size="small" :disabled="page <= 1 || loading" @click="$emit('previous')">上一页</ElButton><span>{{ page }}</span><ElButton size="small" :disabled="!hasNext || loading" @click="$emit('next')">下一页</ElButton></div>
  </aside>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue'
  import type { Conversation } from '@/api/mail-agent-contract'
  import { conversationState, formatMailTime } from './mail-labels'
  const props = defineProps<{ items: Conversation[]; selectedId: string; state: string; loading: boolean; error: string; page: number; hasNext: boolean }>()
  defineEmits<{ select: [id:string]; filter:[state:string]; refresh:[]; previous:[]; next:[] }>()
  const search = ref('')
  const filtered = computed(() => props.items.filter(item => `${item.sender_key} ${item.subject}`.toLowerCase().includes(search.value.toLowerCase())))
</script>
<style scoped>
  .mail-sidebar {width:260px;}
  @media(max-width:850px) {.mail-sidebar {width:100%;max-height:340px;border-right:none;}}
</style>
