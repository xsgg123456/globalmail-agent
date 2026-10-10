<template>
  <ElTag :type="type" size="small" effect="light">{{ status }}</ElTag>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  const props = defineProps<{ status: string }>()
  const type = computed(() => {
    if (props.status.includes('人工')) return 'warning'
    if (props.status.includes('失败')) return 'danger'
    if (props.status.includes('业务')) return 'primary'
    if (props.status.includes('解决') || props.status.includes('执行')) return 'success'
    return 'info'
  })
</script>
