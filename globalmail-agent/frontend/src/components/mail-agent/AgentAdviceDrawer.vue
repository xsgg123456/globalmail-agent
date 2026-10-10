<template>
  <ElDrawer v-model="open" title="Agent 给客服的建议" size="min(520px, 100vw)" destroy-on-close>
    <ElAlert title="仅内部可见 · 草稿未经客服发送不会进入邮件往来" type="info" :closable="false" class="mb-5" />
    <ElAlert v-if="error" :title="error" type="error" :closable="false" class="mb-4" />
    <ElSkeleton v-if="loading" :rows="5" animated />
    <template v-else-if="snapshot?.advice">
      <p class="text-sm font-medium mb-2">{{ snapshot.advice.summary }}</p>
      <p class="text-xs text-g-700 mb-5 break-all">{{ snapshot.run_id }} · {{ formatMailTime(snapshot.advice.queried_at) }} · 输入版本 {{ snapshot.advice.input_revision }}</p>
      <h3 class="text-sm font-medium mb-3">查到的事实</h3>
      <ElEmpty v-if="!observations.length && !snapshot.advice.facts.length" description="尚无可核实的业务事实" :image-size="50" />
      <div v-for="fact in snapshot.advice.facts" :key="fact.key" class="mb-3 p-3 rounded-md bg-active-color"><p class="text-xs text-g-700 mb-1">{{ fact.key }} · {{ fact.kind }}</p><p class="text-sm break-words">{{ fact.value }}</p><p v-for="source in fact.sources" :key="source.message_id + source.quote" class="text-xs text-g-700 mt-2 break-words">来信 {{ source.message_id }}：“{{ source.quote }}”</p></div>
      <BusinessObservation v-for="tool in observations" :key="tool.id" :tool="tool" />
      <h3 class="text-sm font-medium mt-5 mb-3">尚未确认</h3><ul class="text-sm text-g-700 space-y-2 list-disc pl-5"><li v-for="gap in snapshot.advice.gaps" :key="gap">{{ gap }}</li><li v-if="!snapshot.advice.gaps.length">没有额外缺口；商业决策仍由客服完成。</li></ul>
      <h3 class="text-sm font-medium mt-5 mb-3">处理建议</h3><ul class="text-sm space-y-2 list-disc pl-5"><li v-for="item in snapshot.advice.recommendations" :key="item">{{ item }}</li><li v-if="!snapshot.advice.recommendations.length">{{ snapshot.advice.summary }}</li></ul>
      <h3 class="text-sm font-medium mt-5 mb-3">可选回复草稿</h3><p class="text-sm leading-relaxed whitespace-pre-wrap p-3 rounded-md bg-active-color">{{ snapshot.advice.draft || '本轮未生成草稿' }}</p>
      <p v-if="!canAdopt" class="text-xs text-g-700 mt-3">本轮已人工回复、信息有更新或已结案，请先核对最新往来。</p>
    </template>
    <ElEmpty v-else description="本轮尚无内部建议" />
    <template #footer><ElButton @click="open=false">关闭</ElButton><ElButton type="primary" :disabled="loading || !canAdopt || !snapshot?.advice?.draft" @click="$emit('adopt')">采用草稿，交由我发送</ElButton></template>
  </ElDrawer>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import type { ConversationAdvice } from '@/api/agent-run-contract'
  import { formatMailTime } from './mail-labels'
  import BusinessObservation from './BusinessObservation.vue'
  const open = defineModel<boolean>({default:false})
  const props = defineProps<{ snapshot:ConversationAdvice|null; canAdopt:boolean; loading:boolean; error:string }>()
  defineEmits<{adopt:[]}>()
  const observations = computed(() => props.snapshot?.observations.filter(item => !['request_human_review','create_reply_draft','update_case_state','revise_understanding','get_case_context'].includes(item.name)) ?? [])
</script>
