<template>
  <section class="page-content !p-0 flex flex-col min-h-0" aria-label="执行时间线">
    <div class="flex-cb gap-3 p-5 border-b-d"
      ><div
        ><h2 class="text-sm font-semibold">执行过程</h2
        ><p class="text-xs text-g-700 mt-1">按顺序查看模型判断与实际动作</p></div
      ><span class="text-xs text-g-700">{{ steps.length }} 个节点</span></div
    >
    <div class="feed-scroll p-5">
      <div v-for="(step, index) in steps" :key="step.id" class="feed-row">
        <div class="feed-marker" :class="{ active: step.id === selectedId }"
          ><ArtSvgIcon :icon="stepIcons[step.kind]"
        /></div>
        <button
          ref="buttons"
          type="button"
          class="feed-entry"
          :class="{ selected: step.id === selectedId }"
          :aria-current="step.id === selectedId ? 'step' : undefined"
          @click="$emit('select', step.id)"
        >
          <div class="flex-cb gap-3"
            ><span class="text-sm font-semibold">{{ step.title }}</span
            ><span class="text-xs text-g-700 shrink-0">{{ step.duration }}</span></div
          >
          <p class="text-sm text-g-700 leading-relaxed mt-2">{{ step.summary }}</p>
          <p v-if="stepPreview(step)" class="feed-evidence text-xs text-g-800 mt-3">{{
            stepPreview(step)
          }}</p>
          <div class="flex items-center flex-wrap gap-2 mt-3 text-xs text-g-700"
            ><span class="font-mono">{{ String(index + 1).padStart(2, '0') }}</span
            ><span>{{ stepLabels[step.kind] }}</span
            ><span v-if="step.tool" class="font-mono text-theme">{{ step.tool }}</span
            ><span v-else-if="step.thinking === 'recorded'" class="text-theme">含演示思考</span
            ><span class="ml-auto flex items-center gap-1"
              ><ArtSvgIcon icon="ri:check-line" class="text-success" />完成</span
            ></div
          >
        </button>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
  import { nextTick, ref, watch } from 'vue'
  import type { DemoStep } from '@/preview/types'
  import { stepIcons, stepLabels, stepPreview } from '@/preview/presentation'
  const props = defineProps<{ steps: DemoStep[]; selectedId: string }>()
  defineEmits<{ select: [id: string] }>()
  const buttons = ref<HTMLButtonElement[]>([])
  watch(
    () => props.selectedId,
    async () => {
      await nextTick()
      buttons.value
        .find((button) => button.getAttribute('aria-current') === 'step')
        ?.scrollIntoView({ block: 'nearest' })
    },
    { immediate: true }
  )
</script>
<style scoped>
  .feed-scroll {
    overflow-y: auto;
    min-height: 0;
  }
  .feed-row {
    display: grid;
    grid-template-columns: 32px minmax(0, 1fr);
    gap: 12px;
    position: relative;
    padding-bottom: 14px;
  }
  .feed-row:not(:last-child)::before {
    content: '';
    position: absolute;
    left: 15px;
    top: 32px;
    bottom: 0;
    width: 1px;
    background: var(--art-card-border);
  }
  .feed-marker {
    width: 32px;
    height: 32px;
    margin-top: 10px;
    display: grid;
    place-items: center;
    background: var(--el-fill-color-light);
    border: 1px solid var(--art-card-border);
    border-radius: 50%;
    color: var(--el-text-color-secondary);
    z-index: 1;
  }
  .feed-marker.active {
    background: var(--el-color-primary-light-9);
    color: var(--el-color-primary);
    border-color: var(--el-color-primary-light-5);
  }
  .feed-entry {
    width: 100%;
    min-width: 0;
    text-align: left;
    padding: 14px 16px;
    border: 1px solid transparent;
    border-radius: 8px;
    transition:
      background 150ms,
      border-color 150ms;
    cursor: pointer;
  }
  .feed-entry:hover {
    background: var(--el-fill-color-light);
  }
  .feed-entry.selected {
    background: var(--el-color-primary-light-9);
    border-color: var(--el-color-primary-light-5);
  }
  .feed-entry:focus-visible {
    outline: 2px solid var(--el-color-primary);
    outline-offset: 2px;
  }
  .feed-evidence {
    padding: 8px 10px;
    background: var(--el-fill-color-light);
    border-radius: 4px;
    overflow-wrap: anywhere;
  }
  @media (max-width: 1050px) {
    .feed-scroll {
      max-height: 390px;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .feed-entry {
      transition: none;
    }
  }
</style>
