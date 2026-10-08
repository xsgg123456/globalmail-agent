<template>
  <ElButton :disabled="disabled" @click="open">初始业务场景</ElButton>
  <ElDialog
    v-model="visible"
    title="从初始业务资料创建会话"
    width="min(560px, 94vw)"
    :close-on-click-modal="false"
    :close-on-press-escape="!busy"
    :show-close="!busy"
  >
    <ElAlert
      title="只加载初始来信和当前业务资料"
      type="info"
      :closable="false"
      show-icon
      description="每次创建使用独立客户身份和分支。不会加载后续事件、完整故事或参考答案。"
      class="mb-4"
    />
    <ElAlert v-if="error" :title="error" type="error" :closable="false" show-icon class="mb-3" />
    <ElButton v-if="error" :loading="loading" :disabled="busy" @click="load" class="mb-3"
      >重试场景目录</ElButton
    >
    <ElForm label-position="top" :disabled="busy || loading">
      <ElFormItem label="选择初始场景" required :error="inputError">
        <ElSelect
          v-model="selectedId"
          filterable
          aria-label="选择初始场景"
          placeholder="请选择业务场景"
        >
          <ElOption
            v-for="item in scenarios"
            :key="item.scenario_id"
            :value="item.scenario_id"
            :label="`${item.label} · ${item.brand} · ${scenarioMode(item.mode)}`"
          />
        </ElSelect>
      </ElFormItem>
    </ElForm>
    <ElSkeleton v-if="loading" :rows="2" animated />
    <ElEmpty
      v-else-if="!scenarios.length && !error"
      description="暂无允许使用的初始场景"
      :image-size="60"
    />
    <p class="text-xs text-g-700">网络结果未知时，重试相同场景会沿用原命令，避免重复创建。</p>
    <template #footer>
      <div class="flex justify-end flex-wrap gap-2">
        <ElButton :disabled="busy" @click="visible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="busy"
          :disabled="loading || !scenarios.length"
          @click="submit"
          >创建场景会话</ElButton
        >
      </div>
    </template>
  </ElDialog>
</template>
<script setup lang="ts">
  import { ref } from 'vue'
  import { useBusinessScenarios } from '@/composables/useBusinessScenarios'
  defineProps<{ disabled: boolean }>()
  const emit = defineEmits<{ created: [id: string] }>()
  const visible = ref(false),
    inputError = ref('')
  const { scenarios, selectedId, loading, busy, error, load, create } = useBusinessScenarios()
  const scenarioMode = (mode: string) =>
    mode === 'historical_replay' ? '合成历史边界' : '交互模拟'
  async function open() {
    visible.value = true
    await load()
  }
  async function submit() {
    inputError.value = selectedId.value ? '' : '请选择一个初始业务场景'
    if (inputError.value) return
    const id = await create()
    if (!id) return
    emit('created', id)
    visible.value = false
  }
</script>
