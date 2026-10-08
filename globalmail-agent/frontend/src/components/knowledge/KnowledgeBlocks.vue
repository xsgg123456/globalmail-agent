<template>
  <div class="space-y-3">
    <ElEmpty v-if="!blocks.length" description="尚无解析内容，请先运行解析" :image-size="70" />
    <article v-for="block in blocks" :key="block.id" class="border-d rounded p-3 break-words">
      <div class="flex flex-wrap justify-between gap-2 mb-2 text-xs text-g-700">
        <span
          >{{ block.page ? '原件第 ' + block.page + ' 页 · ' : ''
          }}{{
            block.type === 'figure'
              ? '图片'
              : block.type === 'table'
                ? '表格'
                : block.type === 'heading'
                  ? '标题'
                  : '正文'
          }}<span v-if="block.figure_id"> · 图号 {{ block.figure_id }}</span></span
        >
        <ElCheckbox
          v-if="selectable"
          :model-value="excluded.includes(block.id)"
          @update:model-value="toggle(block.id)"
          >排除此段</ElCheckbox
        >
      </div>
      <h3 v-if="block.type === 'heading'" class="font-medium whitespace-pre-wrap">{{
        block.text
      }}</h3>
      <p v-else class="whitespace-pre-wrap">{{
        block.text || '此块没有可读取的文字，请对照图片。'
      }}</p>
      <div v-if="block.table_rows.length" class="overflow-x-auto mt-2">
        <table class="w-full text-sm"
          ><tbody
            ><tr v-for="(row, i) in block.table_rows" :key="i"
              ><td v-for="(cell, j) in row" :key="j" class="border-d p-2 whitespace-pre-wrap">{{
                cell
              }}</td></tr
            ></tbody
          ></table
        >
      </div>
      <figure
        v-for="asset in assets.filter((a) => block.asset_ids.includes(a.id))"
        :key="asset.id"
        class="mt-3"
      >
        <img
          :src="asset.url"
          :alt="`原件第 ${asset.page} 页的图片或表格`"
          class="max-w-full h-auto border-d rounded"
          loading="lazy"
        />
      </figure>
    </article>
  </div>
</template>
<script setup lang="ts">
  import type { KnowledgeBlock, KnowledgeAsset } from '@/api/knowledge-contract'
  const props = withDefaults(
    defineProps<{
      blocks: KnowledgeBlock[]
      assets: KnowledgeAsset[]
      excluded?: string[]
      selectable?: boolean
    }>(),
    { excluded: () => [], selectable: false }
  )
  const emit = defineEmits<{ 'update:excluded': [string[]] }>()
  function toggle(id: string) {
    emit(
      'update:excluded',
      props.excluded.includes(id)
        ? props.excluded.filter((value) => value !== id)
        : [...props.excluded, id]
    )
  }
</script>
