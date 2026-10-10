<template>
  <ElButton @click="visible = true"
    ><ArtSvgIcon icon="ri:group-line" class="mr-2" />切换会话<span class="ml-2 text-g-700">{{
      demo.conversations.length
    }}</span></ElButton
  >
  <ElDrawer v-model="visible" title="选择客户会话" size="min(420px, 100vw)" direction="ltr">
    <div class="flex flex-wrap gap-2 mb-4">
      <ElInput
        v-model="search"
        clearable
        placeholder="搜索客户、主题或会话 ID"
        aria-label="搜索运行会话"
      />
      <ElSelect
        v-model="filter"
        placeholder="全部状态"
        aria-label="筛选运行会话状态"
        class="w-full"
      >
        <ElOption label="全部状态" value="" /><ElOption
          v-for="status in statuses"
          :key="status"
          :label="status"
          :value="status"
        />
      </ElSelect>
    </div>
    <button
      v-for="mail in filtered"
      :key="mail.id"
      type="button"
      class="history-row"
      :class="{ selected: mail.id === selectedId }"
      @click="select(mail.id)"
    >
      <div class="flex-cb gap-2"
        ><span class="text-sm font-semibold">{{ mail.customer }}</span
        ><StatusTag :status="mail.status"
      /></div>
      <p class="text-sm text-g-700 mt-2">{{ mail.subject }}</p>
      <p class="text-xs text-g-700 mt-3"
        >{{ rounds(mail.id).length }} 轮运行 · 最新 {{ rounds(mail.id).at(-1)?.startedAt }} ·
        {{ mail.brand }}</p
      >
      <p class="text-xs text-g-600 font-mono mt-1">{{ mail.id }}</p>
    </button>
    <ElEmpty v-if="!filtered.length" description="没有符合筛选的会话" :image-size="60" />
  </ElDrawer>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { demo } from '@/preview/state'
  import { conversationRuns } from '@/preview/navigation'
  import StatusTag from './StatusTag.vue'
  defineProps<{ selectedId: string }>()
  const emit = defineEmits<{ select: [id: string] }>()
  const visible = ref(false)
  const search = ref('')
  const filter = ref('')
  const statuses = ['等待客户', '待人工接管', '人工接管中', '已解决']
  function rounds(id: string) {
    return conversationRuns(demo.runs, id)
  }
  const filtered = computed(() =>
    demo.conversations.filter(
      (mail) =>
        (!filter.value || mail.status === filter.value) &&
        `${mail.customer} ${mail.subject} ${mail.email} ${mail.id}`
          .toLowerCase()
          .includes(search.value.toLowerCase())
    )
  )
  function select(id: string) {
    emit('select', id)
    visible.value = false
  }
</script>
<style scoped>
  .history-row {
    display: block;
    width: 100%;
    text-align: left;
    padding: 16px;
    margin-bottom: 12px;
    border: 1px solid var(--art-card-border);
    border-radius: 8px;
    cursor: pointer;
    overflow-wrap: anywhere;
  }
  .history-row:hover {
    background: var(--el-fill-color-light);
  }
  .history-row.selected {
    border-color: var(--el-color-primary-light-5);
    background: var(--el-color-primary-light-9);
  }
  .history-row:focus-visible {
    outline: 2px solid var(--el-color-primary);
    outline-offset: 2px;
  }
</style>
