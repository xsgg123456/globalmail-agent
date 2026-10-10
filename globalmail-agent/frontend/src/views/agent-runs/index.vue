<template>
  <div>
    <div class="flex-cb flex-wrap gap-3 mb-4">
      <div><h1 class="text-xl font-semibold">Agent 运行台</h1><p class="text-sm text-g-700 mt-1">先选客户会话，再查看某一轮的判断与执行。</p></div>
      <div class="flex flex-wrap gap-2">
        <ElSelect :model-value="selectedId" aria-label="选择客户会话" placeholder="选择客户会话" filterable @update:model-value="selectConversation">
          <ElOption v-for="item in items" :key="item.id" :label="`${item.sender_key} · ${item.subject}`" :value="item.id" />
        </ElSelect>
        <ElButton :disabled="page <= 1" @click="paginate(false)">上一页</ElButton>
        <ElButton :disabled="!nextCursor" @click="paginate(true)">下一页</ElButton>
        <ElButton @click="openMail()">返回邮件</ElButton>
      </div>
    </div>
    <ElAlert v-if="listError || detailError || error" :title="listError || detailError || error" type="error" :closable="false" class="mb-4" />
    <ElSkeleton v-if="detailLoading && !detail" :rows="5" animated />
    <template v-else-if="detail">
      <section class="page-content !p-5 mb-4" aria-label="当前会话与运行概览">
        <div class="flex-cb flex-wrap gap-4">
          <div class="flex items-start gap-3 min-w-0"><div class="run-avatar"><ArtSvgIcon icon="ri:robot-2-line" /></div>
            <div class="min-w-0"><div class="flex items-center flex-wrap gap-3"><h2 class="text-lg font-semibold break-all">{{ detail.conversation.sender_key }}</h2><ElTag effect="plain">{{ conversationState(detail.conversation) }}</ElTag></div>
              <p class="text-sm text-g-700 mt-2 break-words">{{ detail.conversation.subject }}</p></div>
          </div>
          <ElTag :type="detail.conversation.persistent_human ? 'warning' : 'info'" effect="plain">{{ detail.conversation.persistent_human ? '客服持续主导' : '按本轮权限处理' }}</ElTag>
        </div>
        <section aria-label="会话运行历史" class="mt-4 pt-4 border-t-d">
          <div class="flex-cb flex-wrap gap-2 mb-3"><h3 class="text-sm font-semibold">会话运行历史</h3><span class="text-xs text-g-700">{{ detail.messages.filter(item => item.sender === 'customer').length }} 封客户来信 · {{ rounds.length }} 轮运行</span></div>
          <div class="round-list">
            <div v-for="round in rounds" :key="round.cycle" class="round-card" :class="{ selected: round.attempts.some(item => item.id === run?.id) }">
              <button type="button" class="w-full text-left" @click="selectRun(round.attempts.at(-1)!.id)">
                <div class="flex-cb gap-2"><span class="text-sm font-semibold">第 {{ round.round }} 轮</span><span class="text-xs text-g-700">{{ formatMailTime(round.attempts[0]!.created_at) }}</span></div>
                <p class="text-sm text-g-800 mt-2">{{ runLabels[round.attempts.at(-1)!.status] }}</p>
                <p class="text-xs text-g-700 mt-2">{{ round.attempts.at(-1)!.execution_mode === 'human_assist' ? '内部辅助 · 未发信' : '自主处理' }}</p>
              </button>
              <ElSelect v-if="round.attempts.length > 1" :model-value="round.attempts.some(item => item.id === run?.id) ? run?.id : round.attempts.at(-1)!.id" class="w-full mt-2" aria-label="选择运行尝试" @update:model-value="selectRun">
                <ElOption v-for="attempt in round.attempts" :key="attempt.id" :value="attempt.id" :label="`第 ${attempt.attempt_no} 次尝试 · ${runLabels[attempt.status]}`" />
              </ElSelect>
            </div>
          </div>
        </section>
        <div v-if="run" class="run-meta mt-4">
          <span>{{ runLabels[run.status] }}</span><span>{{ duration(run.started_at, run.finished_at) }} 耗时</span><template v-if="record"><span>{{ record.model_calls?.length ?? 0 }} 次模型 / {{ record.tools.length }} 次工具</span>
          <span>{{ tokenCount }} Tokens{{ record.model_calls?.some(item => item.input_tokens === null || item.output_tokens === null) ? ' · 仅已知用量，含未知' : '' }}</span></template><span v-else>{{ loading ? '调用记录读取中' : '调用记录不可用' }}</span>
          <ElButton v-if="run.trigger_message_id" link type="primary" @click="openMail(run.trigger_message_id)">查看触发来信 →</ElButton>
          <ElButton v-if="['queued','running'].includes(run.status) && detail.conversation.lifecycle === 'open'" :disabled="busy" @click="stop(run.id)">停止本轮</ElButton>
          <ElButton v-if="canRetry" :disabled="busy" @click="retry(run.id)">重试本轮</ElButton>
          <ElButton link @click="refreshRun">刷新记录</ElButton><span class="font-mono break-all">{{ run.id }}</span>
        </div>
        <ObservabilityStatus v-if="run" :key="run.id" :run-id="run.id" :revision="traceRevision" />
        <ElAlert v-if="run && run.id !== detail.runs.at(-1)?.id" type="info" :closable="false" class="mt-4"><template #title><div class="flex-cb flex-wrap gap-2"><span>当前保留历史轮次及所选节点。</span><ElButton link type="primary" @click="selectRun(detail.runs.at(-1)!.id)">查看最新一轮 →</ElButton></div></template></ElAlert>
        <ElAlert v-if="actionError" :title="actionError" type="error" :closable="false" class="mt-3" />
      </section>
      <ElSkeleton v-if="loading && !step" :rows="6" animated />
      <div v-else-if="step" class="execution-layout"><ExecutionFeed :steps="steps" :selected-id="step.id" @select="selectStep" /><NodeDetail :key="`${run?.id}:${step.id}`" :step="step" /></div>
      <ElEmpty v-else :description="error ? '运行记录不可用，请从上方选择有效轮次或刷新记录' : run ? '本轮尚无执行记录；排队、失败和历史未记录情况不会补造节点' : '此会话还没有 Agent 运行'" />
    </template>
    <ElEmpty v-else description="暂无可查看的客户会话" />
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import { useAgentConsole } from '@/composables/use-agent-console'
  import { conversationState, formatMailTime, runLabels } from '@/components/mail-agent/mail-labels'
  import { duration } from '@/components/agent-runtime/run-presentation'
  import ExecutionFeed from '@/components/agent-runtime/ExecutionFeed.vue'
  import NodeDetail from '@/components/agent-runtime/NodeDetail.vue'
  import ObservabilityStatus from '@/components/agent-runtime/ObservabilityStatus.vue'
  defineOptions({ name: 'AgentRuns' })
  const { work, record, error, loading, rounds, run, steps, step, traceRevision, refreshRun, selectConversation, selectRun, selectStep, openMail } = useAgentConsole()
  const { items, selectedId, page, nextCursor, paginate, listError, detailError, detailLoading, detail, busy, actionError, stop, retry } = work
  const tokenCount = computed(() => (record.value?.model_calls ?? []).reduce((total, item) => total + (item.input_tokens ?? 0) + (item.output_tokens ?? 0), 0))
  const canRetry = computed(() => run.value && ['failed','interrupted','stopped'].includes(run.value.status) && detail.value?.conversation.lifecycle === 'open' && detail.value.conversation.auto_run_gate === (detail.value.conversation.persistent_human ? 'disabled' : 'manual_retry_required') && run.value.input_revision === detail.value.conversation.input_revision && run.value.id === detail.value.runs.at(-1)?.id)
</script>
<style scoped>
  .run-avatar { display:grid; place-items:center; width:44px; height:44px; flex-shrink:0; border-radius:10px; background:var(--el-color-primary-light-9); color:var(--el-color-primary); font-size:24px; }
  .run-meta { display:flex; align-items:center; flex-wrap:wrap; gap:10px 16px; color:var(--el-text-color-secondary); font-size:12px; }
  .round-list { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }
  .round-card { padding:12px; text-align:left; border:1px solid var(--art-card-border); border-radius:8px; overflow-wrap:anywhere; }
  .round-card.selected { background:var(--el-color-primary-light-9); border-color:var(--el-color-primary-light-5); }
  .execution-layout { display:grid; grid-template-columns:minmax(330px,.9fr) minmax(400px,1.15fr); gap:16px; height:max(420px,calc(100vh - 525px)); }
  @media(max-width:1050px) { .round-list {grid-template-columns:repeat(2,minmax(0,1fr));} .execution-layout {grid-template-columns:1fr;height:auto;} .execution-layout>section:last-child {min-height:550px;} }
</style>
