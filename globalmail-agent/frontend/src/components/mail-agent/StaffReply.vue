<template>
  <div class="p-4 border-t-d">
    <div class="flex-cb flex-wrap gap-2 mb-3"><span class="text-sm font-medium">{{ historical ? '人工审阅回复' : '人工回复' }}</span><span class="text-xs text-g-700">草稿跨页保留 · {{ historical ? '独立保存审阅' : '本机模拟发送' }}</span></div>
    <ElAlert v-if="resolved" title="已解决；后续来信只登记，不自动重开或执行" :closable="false" class="mb-3" />
    <ElAlert v-else-if="stale" title="已有新输入，草稿仍保留。请核对最新邮件再发送。" type="warning" :closable="false" class="mb-3"><template #default><ElButton link @click="$emit('acknowledge')">我已核对最新邮件</ElButton></template></ElAlert>
    <ElAlert v-if="risks?.length" title="本轮仍有安全风险，需人工核对" type="warning" :closable="false" class="mb-3" />
    <ElInput :model-value="modelValue.reply" type="textarea" :rows="3" resize="vertical" :maxlength="20000" :disabled="busy || resolved" placeholder="输入给客户的回复…" aria-label="人工回复正文" @update:model-value="update('reply',$event)" />
    <ElCollapse class="mt-2">
      <ElCollapseItem title="人工备注与风险复核" name="note">
        <ElSelect v-if="risks?.length" :model-value="modelValue.risk_decision ?? 'keep_active'" :disabled="busy || resolved" aria-label="本次风险决定" @update:model-value="$emit('update:modelValue', { ...modelValue, risk_decision:$event })"><ElOption label="保持风险，继续人工核对" value="keep_active" /><ElOption label="风险已由人工处理" value="resolved_by_human" /><ElOption label="人工复核为误判" value="corrected_by_human" /></ElSelect>
        <ElInput :model-value="modelValue.note" type="textarea" :rows="2" :maxlength="5000" :disabled="busy || resolved" aria-label="人工备注与风险复核依据" placeholder="选择已处理或误判时，填写复核依据" class="mt-2" @update:model-value="update('note',$event)" />
      </ElCollapseItem>
    </ElCollapse>
    <div class="flex-cb flex-wrap gap-3 mt-3"><span class="text-xs text-g-700">{{ canReply ? '核对后由客服发送' : '请先人工接管后回复' }}</span>
      <div class="flex flex-wrap gap-2"><ElButton :disabled="busy || resolved || !canReply || stale" @click="$emit('save')">保存草稿</ElButton><ElButton type="primary" :loading="busy" :disabled="resolved || !canReply || stale || !modelValue.reply.trim()" @click="$emit('send')">{{ historical ? '保存本轮审阅' : '发送模拟回复' }}</ElButton></div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import type { HumanInput } from './mail-inputs'
  import type { ActiveRisk } from '@/api/mail-agent-contract'
  const props = defineProps<{ modelValue:HumanInput; busy:boolean; resolved:boolean; canReply:boolean; stale:boolean; historical:boolean; risks?:ActiveRisk[] }>()
  const emit = defineEmits<{ 'update:modelValue':[input:HumanInput]; acknowledge:[]; save:[]; send:[] }>()
  function update(field:'reply'|'note', value:string) {emit('update:modelValue',{...props.modelValue,[field]:value})}
</script>
