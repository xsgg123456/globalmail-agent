<template>
  <section class="page-content !p-0 flex flex-col min-h-0" aria-label="运行节点详情">
    <header class="p-5 border-b-d">
      <div class="flex items-center gap-2 text-xs text-g-700 mb-3"
        ><span class="node-kind"
          ><ArtSvgIcon :icon="stepIcons[step.kind]" class="mr-1 text-theme" />{{
            stepLabels[step.kind]
          }}</span
        ><span>{{ step.time }}</span
        ><span class="ml-auto flex items-center gap-1 text-success"
          ><ArtSvgIcon icon="ri:checkbox-circle-line" />已完成</span
        ></div
      >
      <h2 class="text-lg font-semibold">{{ step.title }}</h2
      ><p class="text-sm text-g-700 leading-relaxed mt-2">{{ step.summary }}</p>
      <div class="flex flex-wrap gap-3 text-xs text-g-700 mt-3"
        ><span class="font-mono">{{
          step.tool ?? (step.kind === 'model' ? 'qwen3.7-plus' : step.id)
        }}</span
        ><span>耗时 {{ step.duration }}</span
        ><span>演示节点</span></div
      >
    </header>
    <ElTabs v-model="tab" class="detail-tabs">
      <ElTabPane label="输入与提示词" name="input"><RequestView :input="step.input" /></ElTabPane>
      <ElTabPane label="模型思考" name="thinking">
        <div v-if="step.thinking === 'recorded'">
          <div class="flex items-center flex-wrap gap-2 mb-4"
            ><ElTag size="small" type="warning" effect="plain">演示思考 · 构造内容</ElTag
            ><span class="text-xs text-g-700">正式接入时读取供应商 reasoning_content</span></div
          >
          <div class="thinking-text"
            ><ArtSvgIcon icon="ri:brain-line" class="text-theme text-xl mb-3" /><p
              class="text-sm text-g-900 leading-[1.9] whitespace-pre-wrap break-words"
              >{{ step.reasoning }}</p
            ></div
          >
        </div>
        <div v-else class="thinking-empty"
          ><ArtSvgIcon icon="ri:brain-line" class="text-3xl text-g-600 mb-4" /><h3
            class="text-sm font-medium"
            >{{ step.thinking === 'off' ? '本次调用未启用思考' : '此节点没有模型思考' }}</h3
          ><p class="text-sm text-g-700 mt-2 leading-relaxed">{{
            step.thinking === 'off'
              ? 'enable_thinking = false。请求输入与输出仍可查看。'
              : '这是工具或程序执行节点，请查看输入、输出与执行结果。'
          }}</p></div
        >
      </ElTabPane>
      <ElTabPane label="输出结果" name="output"
        ><DataBlock
          :value="step.output"
          :title="step.kind === 'model' ? '模型返回' : '执行结果'"
          raw-label="查看原始输出 JSON"
      /></ElTabPane>
      <ElTabPane label="工具调用" name="tool">
        <div v-if="step.tool" class="space-y-5"
          ><div class="tool-heading flex-cb flex-wrap gap-3"
            ><div class="flex items-center gap-2"
              ><ArtSvgIcon icon="ri:tools-line" class="text-theme" /><span
                class="font-mono text-sm"
                >{{ step.tool }}</span
              ></div
            ></div
          >
          <DataBlock :value="step.input" title="调用参数" raw-label="查看参数 JSON" /><DataBlock
            :value="step.output"
            title="返回结果"
            raw-label="查看结果 JSON"
        /></div>
        <div v-else class="thinking-empty"
          ><ArtSvgIcon icon="ri:tools-line" class="text-3xl text-g-600 mb-4" /><h3
            class="text-sm font-medium"
            >此节点没有执行工具</h3
          ><p class="text-sm text-g-700 mt-2">当次工具定义可在输入与提示词中展开查看。</p></div
        >
      </ElTabPane>
    </ElTabs>
  </section>
</template>
<script setup lang="ts">
  import { ref } from 'vue'
  import type { DemoStep } from '@/preview/types'
  import { stepIcons, stepLabels } from '@/preview/presentation'
  import RequestView from './RequestView.vue'
  import DataBlock from './DataBlock.vue'
  defineProps<{ step: DemoStep }>()
  const tab = ref('input')
</script>
<style scoped>
  .node-kind {
    display: inline-flex;
    align-items: center;
    padding: 4px 7px;
    border-radius: 4px;
    background: var(--el-fill-color-light);
  }
  .detail-tabs {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .detail-tabs :deep(.el-tabs__header) {
    margin: 0;
    padding: 0 20px;
  }
  .detail-tabs :deep(.el-tabs__nav-wrap::after) {
    height: 1px;
  }
  .detail-tabs :deep(.el-tabs__item) {
    height: 48px;
    font-size: 13px;
  }
  .detail-tabs :deep(.el-tabs__content) {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
  }
  .thinking-text {
    padding: 20px;
    border-left: 3px solid var(--el-color-primary);
    border-radius: 0 8px 8px 0;
    background: var(--el-fill-color-light);
  }
  .thinking-empty {
    padding: 32px 12px;
  }
  .tool-heading {
    padding: 12px 14px;
    background: var(--el-fill-color-light);
    border-radius: 8px;
  }
  @media (max-width: 600px) {
    .detail-tabs :deep(.el-tabs__header) {
      padding: 0 12px;
    }
    .detail-tabs :deep(.el-tabs__content) {
      padding: 16px;
    }
  }
</style>
