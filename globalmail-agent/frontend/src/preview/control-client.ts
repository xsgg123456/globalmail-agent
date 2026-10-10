import { demo, resetDemo, appendDemoIncoming } from './state'
import { updateMockOrder } from './behavior'
import { parsePreviewCommand, type PreviewControlEvent } from './control-contract'

if (import.meta.env.MODE === 'ui-preview' && import.meta.hot) {
  const pending: PreviewControlEvent[] = []
  let ready = false
  let lastSequence = 0
  function apply(event: PreviewControlEvent) {
    const command = parsePreviewCommand(event.command)
    if (!command || !Number.isInteger(event.sequence) || event.sequence <= lastSequence) return
    if (command.type === 'reset') resetDemo()
    if (command.type === 'incoming') appendDemoIncoming(command.conversationId, command.body)
    if (command.type === 'business_update') updateMockOrder(demo, command.orderId, command.patch)
    lastSequence = event.sequence
  }
  const receive = (event: PreviewControlEvent) => (ready ? apply(event) : pending.push(event))
  import.meta.hot.on('globalmail:preview-control', receive)
  // 先订阅再读取命令，避免首屏加载期间漏掉脚本输入；重复序号不会重复来信。
  void fetch('/__ui_preview__/events')
    .then(async (response) => {
      if (!response.ok) return
      const value: unknown = await response.json()
      if (
        typeof value === 'object' &&
        value !== null &&
        'events' in value &&
        Array.isArray(value.events)
      ) {
        for (const event of value.events as PreviewControlEvent[]) apply(event)
      }
    })
    .catch(() => {
      // 静态预览没有控制服务时仍可浏览预置案例。
    })
    .finally(() => {
      for (const event of pending.sort((a, b) => a.sequence - b.sequence)) apply(event)
      ready = true
    })
  import.meta.hot.dispose(() => import.meta.hot?.off('globalmail:preview-control', receive))
}
