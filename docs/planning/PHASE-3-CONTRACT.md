# Phase 3 后端集成契约

日期：2026-10-08。实现范围：持久会话、受控 JSON 导入、回放、人审、任务协议与有序 UI 事件。模型回复未接入。

## 表与事务

全部表复用 `adapters.schema.metadata`，UUID 主键及 created_at/updated_at。会话子表带 `workspace_id, mode, branch_id, customer_id, purpose`，完整作用域复合 FK 指向会话；对象引用同样完整作用域 FK。存储 mode 为 `simulation / historical_replay`，公开 mode 将前者映射 `interactive_simulation`。

可能取消不同任务种类的会话写事务，先按agent→knowledge顺序锁定双槽，再锁会话；worker只锁自身任务槽，再锁会话。双槽只在短事务持有，不占用对方的长期租约，避免knowledge完成与新来信/停止互相等待。

- conversations：scope、dataset_id(UUID)、identity_id、subject、row_version(初值1)、input_revision(初值0)、authority_epoch(初值0)、branch_generation(初值1)、case_revision、lifecycle(open/resolved/deleting/deleted)、processing_owner(agent/human_review/human_wait_customer)、auto_run_gate(open/manual_retry_required/disabled)、scheduling_state(idle/queued/running/waiting_customer/waiting_business/failed/stopped)、visible_message_seq、next_seq、received_seq、human_reply_after_seq。
- identities：workspace_id/dataset_id/mode、sender_key、verified、source_ref；同 dataset/mode 下 sender_key 唯一。服务端绑定单实例 workspace 和演示 dataset；邮箱只 trim 和域名小写，不移除本地部分加号/句点。
- data_imports：workspace_id、source_ref、source_conversation_id、split、payload_hash、conversation_id；同 workspace/source_ref/source_conversation_id 唯一；未验证身份仅创建独立历史案例，group_id仅元数据。
- messages：scope、conversation_id、seq、received_seq、source_ref/source_message_id、sender(customer/historical_staff/simulated_human)、subject、body_object_id、sent_at；seq 会话唯一，来源消息在会话内唯一。历史未来消息持久保存但详情仅 seq<=visible_message_seq。
- replay_cursors：scope/conversation_id、position、total_customer_messages、as_of、finished；只有推进 API 修改，无客户端 as_of。
- processing_cycles：scope/conversation_id、trigger_id(UUID)、trigger_message_id(UUID)、input_revision、authority_epoch、branch_generation、state(queued/running/completed/failed/stopped/interrupted/superseded)、completed_at、final_message_id；conversation/trigger 唯一。
- agent_runs：scope/conversation_id、processing_cycle_id、attempt_no、status(queued/running/completed/handed_off/failed/budget_exhausted/stopped/superseded/interrupted/cancelled)、input_revision、authority_epoch、branch_generation、trigger_id、stop_requested、checkpoint_writable(bool初值true)、error_code、outcome、started_at、finished_at；cycle/attempt 唯一。
- jobs：scope/conversation_id、run_id、cycle_id、kind(agent/knowledge)、status(queued/running/completed/failed/stopped/superseded/interrupted/cancelled)、lease_owner、lease_expires_at、slot_fence、attempt_no；run唯一。
- agent_slots：workspace_id、slot_key(agent/knowledge)、lease_owner、lease_expires_at、fence(初值0)、job_id；workspace/slot_key唯一；migration 初始化默认 workspace 双槽。
- domain_events：scope/conversation_id、source、source_event_id、kind、payload(JSONB，仅安全资源ID)、status(pending/processed/suppressed_by_human)；conversation/source/source_event_id唯一。
- ui_events：scope/conversation_id、seq、kind、payload(JSONB，仅安全状态/资源ID)；conversation/seq唯一。`append_ui_event(conn, conversation_id, kind, payload)` 重新取会话行锁递增 next_seq，事实同事务 commit。
- human_reviews：scope/conversation_id、status(open/completed/closed)、version、input_revision、reason、visible_message_seq/as_of、draft_object_id/note_object_id/reply_object_id；部分索引保证每会话最多一个open。历史审阅保留所属真实截点。
- case_issues：scope/conversation_id、issue_key、status、version；conversation/issue_key唯一，稳定主键。
- case_facts：scope/conversation_id、issue_id、source_message_id、kind(customer_report/historical_claim/visual_observation/tool_fact/human_decision/model_inference)、value_object_id、revision、visible_seq；本期从实际邮件创建customer_report/historical_claim，来源正文依赖同事务登记，当前历史事实仅来自可见真实前缀。自由人工备注保留在human_reviews及其对象依赖中，不能作为已验证human_decision授权业务；结构化事实修订入口后续接入。
- case_revisions：scope/conversation_id、revision、as_of、visible_message_seq、source；conversation/revision唯一。
- request_receipts：workspace_id、request_key、operation、payload_hash、result(JSONB)，workspace/request_key唯一；相同键同参返回原资源、异参409。

`application.task_queue.enqueue(conn, conv, event)`：调用方已持会话锁，原子新 cycle/run/job，返回 `{processing_cycle_id, run_id, job_id}`。只由新有效来信/回放调用；GET/SSE没有排队副作用。`invalidate(conn, conversation_id)`：旧queued任务取消、running任务superseded，关闭checkpoint写资格，释放相关slot并递增fence，保留cycle和事件事实。worker直接导入以上表与event_store。旧queued事件合并为最新上下文任务，pending事件不会因取消丢失。

`event_store.record_business_notification(conn, conv, source_id)` 是Phase 3内部记账与竞争验证入口，不开放HTTP操作注入。新事件递增input_revision/row_version；人审/人工等待/结案/gate关闭时记录suppressed_by_human；重复事件不重复处理；本期不实现Phase 10业务等待匹配与唤醒。

正文写由 `adapters.body_store.BodyWriter` 在调用方数据库事务登记 objects 与依赖，不通过 ObjectStore.put 的第二连接；事务失败清理新文件。读正文依相同scope在已有连接核验摘要。

## 服务/API

`ConversationService(engine, store, workspace_id=DEFAULT_WORKSPACE_ID)` 暴露 create/list/detail/append/import_case/next/takeover/save_review/human_reply/close。worker的 stop/retry由parent独立run router集成。

统一200或202 envelope `{code,msg,data,request_id}`。所有写动作 Idempotency-Key(UUID或非空<=160字符串) + expected_version，首次create/import的expected_version=0；人审回复另 expected_input_revision。安全错误409/422/503，正文/凭据不进入错误。

- GET /conversations?mode=&state=&limit=50&cursor=UUID → `{items:[conversation],next_cursor}`；游标按创建时间/id稳定排序；state支持人审owner、resolved及调度状态。
- POST /conversations `{expected_version:0,sender_email,subject?,body}` →202 `{conversation_id,version,...task_ids}`；同邮箱同dataset追加至原simulation会话。
- POST /imports `{expected_version:0,source_ref,source_conversation_id,split,group_id?,sender_key?,identity_verified:false,identity_source_ref?,messages:[{source_message_id,sender:customer|historical_staff,sent_at(时区),subject?,body}]}` →202 同上。禁止额外字段、未来事件、参考答案和任何路径；来自浏览器的 identity_verified=true 不被视为受控复核，拒绝。
- GET /conversations/{id} → `{conversation,messages,review,human_history,comparisons,runs,issues,facts,replay}`；messages/facts只含真实可见前缀，review草稿/备注独立字段；historical completed审阅另由comparisons返回，不进入真实前缀。conversation带sender_key/identity_verified及完整scope，公开mode映射为interactive_simulation。
- POST /conversations/{id}/messages `{expected_version,subject?,body,source_message_id?}` →202资源与任务ID；仅simulation。
- POST /conversations/{id}/replay/next `{expected_version}` →202；当前未终止run或未完成人审时409；推进至下一customer并含其之前历史客服消息；结束返回finished=true且不结案。
- POST /conversations/{id}/takeover `{expected_version,reason?}` →202 `{conversation_id,review_id,version}`；仅生命周期为open时允许接管，已结案返回409；新客户来信按原会话重开。
- PATCH /human-reviews/{id} `{expected_version,expected_input_revision,draft,note}` →200 `{review_id,version}`；expected_version对应review资源，expected_input_revision为这份草稿已经核对的输入版本，保存不自动绑定最新来信。
- POST /conversations/{id}/human-replies `{expected_version,expected_input_revision,body,note?}` →202；simulation正式人工出站；historical只保存独立审阅结果，不入messages。
- POST /conversations/{id}/close `{expected_version,note?}` →202；人工结案撤销旧任务，新来信重开原conversation。
- GET /conversations/{id}/events?after_seq=（也支持Last-Event-ID）→ SSE，15秒 heartbeat；event:update，id:seq，data=`{conversation_id,workspace_id,branch_id,mode,seq,kind,payload}`；仅安全状态和ID，重新连接不创建任务。负数或无效Last-Event-ID为422，超过当前已提交序号为409。

错误/409时数据库状态与已有草稿保持；前端保留输入。界面统一注明本地模拟/模型尚未接入。

前端幂等命令按实际HTTP JSON编码保存不可变快照，支持Vue响应式导入对象；未知请求结果重试时沿用同一快照与key，不能直接structuredClone响应式Proxy。

邮件更新前按容器实际滚动距离判断是否在底部，不用初值为true的缓存标记；首次打开溢出会话静止阅读与上翻阅读均保留位置。用户主动提交/推进可明确滚到最新邮件。

导入样例：`globalmail-agent/backend/fixtures/historical-example.json`，与GET `/imports/example`内容相同。公开包只接受未复核身份，真实受控sender_key复核接入及订单历史快照查询仍未实现；当前as_of与真实消息前缀已实现，不表示AC-006已验证。
