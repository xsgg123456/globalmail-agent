<template>
  <div class="space-y-3">
    <p class="text-sm text-g-700"
      >明确选择适用型号和章节。选择整份资料，表示你确认整份都适用于该型号。</p
    >
    <div v-for="(row, index) in modelValue" :key="index" class="border-d rounded p-3 space-y-2">
      <div class="flex flex-wrap gap-2">
        <ElSelect
          v-model="row.section_id"
          filterable
          allow-create
          default-first-option
          aria-label="适用章节"
          class="!w-[220px] max-w-full"
        >
          <ElOption label="整份资料（明确绑定）" value="document" />
          <ElOption
            v-for="section in sections"
            :key="section.id"
            :label="section.label"
            :value="section.id"
          />
        </ElSelect>
        <ElSelect v-model="row.sku" filterable aria-label="精确型号" class="!w-[280px] max-w-full">
          <ElOption
            v-for="product in products.filter((p) => !brand || p.brand === brand)"
            :key="product.sku"
            :label="`${product.sku} · ${product.name}`"
            :value="product.sku"
          />
        </ElSelect>
        <ElButton @click="remove(index)">移除这条范围</ElButton>
      </div>
      <div v-if="pageRange" class="flex flex-wrap items-center gap-2">
        <span>页码</span
        ><ElInputNumber
          v-model="row.page_start"
          :min="pageRange[0]"
          :max="pageRange[1]"
          :precision="0"
          aria-label="起始页"
        />
        <span>至</span
        ><ElInputNumber
          v-model="row.page_end"
          :min="pageRange[0]"
          :max="pageRange[1]"
          :precision="0"
          aria-label="结束页"
        />
      </div>
      <ElInput
        v-model="row.basis"
        placeholder="填写判断依据，例如：原件第 3 页明确列出这个型号"
        aria-label="适用依据"
        maxlength="2000"
      />
    </div>
    <ElButton @click="add">添加型号适用范围</ElButton>
  </div>
</template>
<script setup lang="ts">
  import type { Binding, Catalog } from '@/api/knowledge-contract'
  const props = defineProps<{
    modelValue: Binding[]
    products: Catalog['products']
    brand: string | null
    pageRange: [number, number] | null
    sections: { id: string; label: string }[]
  }>()
  const emit = defineEmits<{ 'update:modelValue': [Binding[]] }>()
  function add() {
    emit('update:modelValue', [
      ...props.modelValue,
      {
        section_id: 'document',
        sku: '',
        page_start: props.pageRange?.[0] ?? null,
        page_end: props.pageRange?.[1] ?? null,
        basis: ''
      }
    ])
  }
  function remove(index: number) {
    emit(
      'update:modelValue',
      props.modelValue.filter((_, i) => i !== index)
    )
  }
</script>
