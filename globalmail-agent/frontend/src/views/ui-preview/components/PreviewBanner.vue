<template>
  <div class="mb-4 flex-cb flex-wrap gap-2 text-xs text-g-700">
    <div class="flex items-center flex-wrap gap-2">
      <ElTag size="small" type="warning" effect="plain">交互预览 · 演示数据</ElTag>
      <span>沿用现有前端 · 运行与工具记录均为构造演示</span>
    </div>
    <span>{{ note }}</span>
  </div>
</template>
<script setup lang="ts">
  defineProps<{ note?: string }>()
</script>
