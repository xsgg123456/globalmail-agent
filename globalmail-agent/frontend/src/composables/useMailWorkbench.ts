import { mailApi, type MailApi } from '@/api/mail-agent'
import { createMailWorkbench } from './create-mail-workbench'

let shared: ReturnType<typeof createMailWorkbench> | undefined
// Staff drafts survive navigation between the two workbenches; injected test APIs stay isolated.
export function useMailWorkbench(api: MailApi = mailApi) {
  if (api !== mailApi) return createMailWorkbench(api)
  return (shared ??= createMailWorkbench(api))
}
