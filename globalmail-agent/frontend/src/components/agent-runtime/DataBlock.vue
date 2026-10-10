<template>
  <div class="min-w-0">
    <h4 v-if="title" class="text-sm font-medium mb-3">{{ title }}</h4>
    <dl v-if="fields.length" class="record-grid">
      <div v-for="[key, fieldValue] in fields" :key="key" class="record-field">
        <dt class="text-xs text-g-700 mb-1"
          >{{ fieldLabel(key)
          }}<span v-if="fieldLabel(key) !== key" class="ml-2 text-g-500 font-mono">{{
            key
          }}</span></dt
        >
        <dd class="text-sm text-g-900 whitespace-pre-wrap break-words leading-relaxed">{{
          displayValue(fieldValue)
        }}</dd>
      </div>
    </dl>
    <pre v-else class="text-sm whitespace-pre-wrap break-words leading-relaxed">{{
      displayValue(value)
    }}</pre>
    <ElCollapse v-model="expanded" class="mt-3 raw-collapse">
      <ElCollapseItem :title="rawLabel" name="raw">
        <pre class="raw-code">{{ pretty(value) }}</pre>
      </ElCollapseItem>
    </ElCollapse>
  </div>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { asRecord, displayValue, fieldLabel, pretty } from './presentation'
  const props = withDefaults(defineProps<{ value: unknown; title?: string; rawLabel?: string }>(), {
    rawLabel: '查看原始 JSON'
  })
  const fields = computed(() => Object.entries(asRecord(props.value)))
  const expanded = ref<string[]>([])
</script>
<style scoped>
  .record-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1px;
    border: 1px solid var(--art-card-border);
    border-radius: 8px;
    overflow: hidden;
    background: var(--art-card-border);
  }
  .record-field {
    min-width: 0;
    padding: 12px 14px;
    background: var(--el-bg-color);
  }
  .raw-code {
    padding: 16px;
    background: var(--el-fill-color-light);
    border-radius: 6px;
    font:
      12px/1.7 ui-monospace,
      SFMono-Regular,
      Consolas,
      monospace;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .raw-collapse {
    --el-collapse-header-height: 38px;
    border-top: none;
  }
  @media (max-width: 600px) {
    .record-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
