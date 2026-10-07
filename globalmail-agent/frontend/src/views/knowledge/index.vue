<template>
  <div class="page-content">
    <h1 class="text-base font-medium">知识库</h1>
    <ElEmpty description="知识管理尚未接入">
      <p class="text-sm text-g-600"
        >上传、修订和发布将在知识阶段开放；当前不查询或展示业务资料列表。</p
      >
    </ElEmpty>
  </div>
</template>
<script setup lang="ts">
  defineOptions({ name: 'Knowledge' })
</script>
