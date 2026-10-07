<template>
  <div>
    <RuntimeStatus />
    <div class="page-content flex !p-0 max-lg:flex-col">
      <section
        class="box-border w-64 shrink-0 p-5 border-r border-g-300 max-lg:w-full max-lg:border-r-0 max-lg:border-b"
      >
        <h1 class="text-base font-medium">客户会话</h1>
        <ElEmpty description="会话功能尚未接入" :image-size="80" />
      </section>
      <section
        class="box-border flex-1 min-w-0 p-5 border-r border-g-300 max-lg:border-r-0 max-lg:border-b"
      >
        <h2 class="text-base font-medium">邮件往来</h2>
        <ElEmpty description="导入和添加来信将在会话阶段开放" :image-size="100" />
      </section>
      <section class="box-border w-72 shrink-0 p-5 max-lg:w-full">
        <h2 class="text-base font-medium">Agent 处理记录</h2>
        <ElEmpty description="Agent 与人审尚未接入" :image-size="80" />
        <p class="text-sm text-g-600">当前仅验证本机运行基础，未执行模型调用或发送邮件。</p>
      </section>
    </div>
  </div>
</template>
<script setup lang="ts">
  import RuntimeStatus from '@/components/business/runtime-status.vue'
  defineOptions({ name: 'MailWorkbench' })
</script>
