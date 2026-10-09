<template>
  <section aria-label="事项与等待" class="border-t-d pt-4 mb-5">
    <h3 class="text-sm font-medium mb-2">事项与等待</h3>
    <p class="text-xs text-g-700 mb-3">业务结果按对应订单跟进。排队表示待处理，只有本轮提交后才标为已消费。</p>
    <ElEmpty v-if="!detail.issues.length" description="尚无已保存事项" :image-size="50" />
    <ElCollapse v-else>
      <ElCollapseItem v-for="issue in detail.issues" :key="issue.id" :name="issue.id"
        :title="`${issue.order_number || '会话往来'} · ${kinds[issue.business_type ?? ''] || issue.business_type || '邮件处理'}`">
        <p class="text-sm break-words mb-2">{{ stateLabel(issue.plan_status || issue.status) }} · 第 {{ issue.version }} 版</p>
        <p v-if="issue.current_operation_id" class="text-xs text-g-700 break-all mb-2">当前申请：{{ issue.current_operation_id }}</p>
        <p v-if="!issueWaits(issue.id).length" class="text-sm text-g-700">当前没有登记的业务等待。</p>
        <article v-for="wait in issueWaits(issue.id)" :key="wait.id" class="border-d rounded p-3 mb-2">
          <p class="text-sm break-words">{{ conditions[wait.condition_type] || wait.condition_type }} · {{ stateLabel(wait.status) }}</p>
          <p class="text-xs text-g-700 break-all mt-2">{{ wait.operation_id || '客户信息' }} · 已观察业务版本 {{ wait.last_seen_business_version }}</p>
        </article>
        <p v-for="wake in issueWakes(issue.id)" :key="wake.id" class="text-xs text-g-700 break-all mt-2">
          结果版本 {{ wake.business_version }} · {{ stateLabel(wake.status) }}
          <span v-if="wake.observed_run_id"> · 消费运行 {{ wake.observed_run_id }}</span>
        </p>
      </ElCollapseItem>
      <ElCollapseItem name="events" :title="`业务事件 ${businessEvents.length}`">
        <ElEmpty v-if="!businessEvents.length" description="尚无业务事件" :image-size="50" />
        <article v-for="event in businessEvents" :key="event.id" class="border-d rounded p-3 mb-2">
          <p class="text-sm break-words">{{ conditions[event.condition_type ?? ''] || event.source }} · {{ stateLabel(event.status) }}</p>
          <p class="text-xs text-g-700 break-all mt-2">{{ event.operation_id || event.source_event_id }} · 版本 {{ event.business_version ?? '—' }}</p>
          <p v-if="event.observed_run_id" class="text-xs text-g-700 break-all mt-2">消费运行：{{ event.observed_run_id }}</p>
        </article>
      </ElCollapseItem>
    </ElCollapse>
  </section>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import type { ConversationDetail } from '@/api/mail-agent-contract'
  const props = defineProps<{ detail: ConversationDetail }>()
  const kinds: Record<string, string> = { refund: '退款', return: '退货', replacement: '换货', spare_part: '补件', logistics: '物流', product: '商品咨询', troubleshooting: '故障排查', other: '其他诉求' }
  const conditions: Record<string, string> = { manual_execution: '等待人工执行', refund_receipt: '等待退款回执', warehouse_receipt: '等待仓库结果', inventory: '等待库存', shipment_changed: '等待物流更新', customer_information: '等待客户信息', customer_feedback: '等待客户反馈' }
  const states: Record<string, string> = { active: '等待中', replaced: '已更新等待', fulfilled: '结果已观察', pending: '待消费', processed: '已消费', suppressed_by_human: '门禁关闭，仅记录', record_only: '仅记录', candidate: '待核验方案', accepted: '内部申请已受理', awaiting_execution: '等待实际执行', waiting_condition: '等待条件满足', succeeded: '已取得执行回执', cancelled: '已取消', unknown: '结果未知，须核对', failed: '执行失败，须核对', open: '处理中' }
  const stateLabel = (value: string) => states[value] || value
  const issueWaits = (id: string) => (props.detail.waits ?? []).filter(row => row.issue_id === id)
  const issueWakes = (id: string) => (props.detail.wakes ?? []).filter(row => row.issue_id === id)
  const businessEvents = computed(() => (props.detail.business_events ?? []).filter(row => row.source === 'business_wait' || row.source === 'branch_fact' || row.source === 'business_result'))
</script>
