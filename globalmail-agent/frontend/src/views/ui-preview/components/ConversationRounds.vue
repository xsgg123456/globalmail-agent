<template>
  <section aria-label="会话运行历史" class="mt-4 pt-4 border-t-d">
    <div class="flex-cb flex-wrap gap-2 mb-3">
      <h3 class="text-sm font-semibold">会话运行历史</h3>
      <span class="text-xs text-g-700"
        >{{ customerMails }} 封客户来信 · {{ runs.length }} 轮运行</span
      >
    </div>
    <div class="round-list">
      <button
        v-for="run in runs"
        :key="run.id"
        type="button"
        class="round-card"
        :class="{ selected: run.id === selectedId }"
        :aria-current="run.id === selectedId ? 'true' : undefined"
        @click="$emit('select', run.id)"
      >
        <div class="flex-cb gap-2"
          ><span class="text-sm font-semibold"
            >第 {{ run.round }} 轮
            <span v-if="run.id === runs.at(-1)?.id" class="text-xs font-normal text-theme ml-1"
              >最新</span
            > </span
          ><span class="text-xs text-g-700">{{ run.startedAt.slice(0, 5) }}</span></div
        >
        <p class="text-sm text-g-800 mt-2 leading-relaxed">{{ runTitle(run) }}</p>
        <div class="flex-cb flex-wrap gap-2 mt-2"
          ><span class="text-xs text-g-700">{{ run.trigger }}</span
          ><StatusTag :status="run.status"
        /></div>
      </button>
    </div>
  </section>
</template>
<script setup lang="ts">
  import type { DemoRun } from '@/preview/types'
  import { runTitle } from '@/preview/presentation'
  import StatusTag from './StatusTag.vue'
  defineProps<{ runs: DemoRun[]; selectedId: string; customerMails: number }>()
  defineEmits<{ select: [id: string] }>()
</script>
<style scoped>
  .round-list {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }
  .round-card {
    padding: 12px;
    text-align: left;
    border: 1px solid var(--art-card-border);
    border-radius: 8px;
    cursor: pointer;
    overflow-wrap: anywhere;
  }
  .round-card:hover {
    background: var(--el-fill-color-light);
  }
  .round-card.selected {
    background: var(--el-color-primary-light-9);
    border-color: var(--el-color-primary-light-5);
  }
  .round-card:focus-visible {
    outline: 2px solid var(--el-color-primary);
    outline-offset: 2px;
  }
  @media (max-width: 1050px) {
    .round-list {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  @media (max-width: 450px) {
    .round-card {
      padding: 10px;
    }
  }
</style>
