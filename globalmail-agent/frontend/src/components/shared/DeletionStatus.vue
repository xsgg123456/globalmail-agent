<template>
  <div class="space-y-3" role="status">
    <ElAlert :title="deletionLabels[record.status]" :type="record.status === 'completed' ? 'success' : failed ? 'warning' : 'info'" :closable="false" />
    <p v-if="record.status === 'blocked_dependencies'" class="text-sm">原件或历史副本与其他资料共享，当前无法安全分离。清理已暂停，共享原件禁止下载；其他不含待删内容的资料仍可使用。仅修订新版本不能解除历史副本依赖，需要维护人员处理共享内容后重试。</p>
    <p v-for="id in record.impact.blocked_document_ids" :key="id" class="text-xs break-all">关联资料：{{ id }}</p>
    <p v-if="record.status === 'cleanup_failed'" class="text-sm">部分内容尚未确认清理完成。请检查本地存储及追踪服务后重试；旧内容继续禁止使用。</p>
    <p class="text-xs text-g-700 break-all">删除记录：{{ record.id }}</p>
    <div class="flex flex-wrap gap-2">
      <ElButton v-if="record.status !== 'completed'" :loading="busy" @click="$emit('refresh')">刷新状态</ElButton>
      <ElButton v-if="failed" :loading="busy" @click="$emit('retry')">重试清理</ElButton>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { deletionLabels, type DeletionRecord } from '@/api/lifecycle-api'
const props = defineProps<{record: DeletionRecord; busy: boolean}>()
defineEmits<{refresh: []; retry: []}>()
const failed = computed(() => ['cleanup_failed', 'blocked_dependencies'].includes(props.record.status))
</script>
