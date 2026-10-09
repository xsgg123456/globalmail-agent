# Phase 8 第五轮工程审查

日期：2026-10-09。独立 fresh code-reviewer；Git 基线 `09a818fa9976c94e5c50a090620993b324b603ea`。范围为本期工作区全部工程增量及新增未跟踪源码，排除用户 `.idea/`、进化队列。执行 [code-review skill](../../.agents/skills/code-review/SKILL.md)。只写本报告，不修代码、不提交、不派发、不调用付费模型。

**结论：Stage 1 FAIL，1 项新增 HIGH；Stage 2 未执行。** 第四轮联合图片撤销后的证据 GET/人工更正 POST 500 已独立关闭；新发现是旧危险图片撤销后，同类新图片危险没有取得有效持久风险记录，后续可绕过风险恢复门并模拟发信。本报告保留本轮失败快照，不为主 Agent 后续修复背书。

## 输入、计划与边界

已直接读取 AGENTS、skill、code-reviewer.toml、Product-Spec REQ-014/AC-065–082、AGENT-ARCHITECTURE 第4.4节及表/API/提交契约、DEV-PLAN Phase 8、PHASE-8-IMPLEMENTATION、SESSION-HANDOFF 顶部、PHASE-8-VALIDATION、前四轮 INITIAL/FINAL/CLOSURE/ENGINEERING-FINAL 原报告、增量和新增附件源码。没有根据报告文件名推定 PASS。

审查步骤为逐条需求映射 → 接收/受控案例/绑定/授权 → 联合理解/预算/来源/风险事务 → 更正/撤销/晚到反例 → 工程验证；Stage 1 无 HIGH 才做质量、安全、测试真实性与实际邻居渲染。本轮在新增 HIGH 处停止 Stage 2。

用户原话“倒不如继续开发 到时候整个项目跑通之后再调整这种细节”“现在继续开发Phase8吧”只调整开发顺序。依据 `Product-Spec.md:5`、`AGENT-ARCHITECTURE.md:5`、`DEV-PLAN.md:7/178/191`，Phase 1/7 模型质量原 FAIL、字段/观察/分流语义和 AC-082 专项验收延期，未通过；固定模型只证明工程集成。AC-069/071 正式售后写归 Phase 9，AC-078 完整副本删除/备份恢复归 Phase 12。来源、权限、预算、危险 HITL、撤销、人工恢复及副作用门没有延期或放宽。

本轮真实测试使用 `tests/test_protocol.py:35/40/45/48/62` 的随机 PostgreSQL schema、迁移和临时对象目录，结束清理。正式库仍 0005；未升级、重启正式服务或改主 Agent CLI profile。本轮自有 IAB 只打开隔离15174工作台后关闭，没有执行 Stage 2 邻居视觉比较。

## HIGH：撤销旧危险来源后，新同类危险被旧 active 行吞掉

**位置：`globalmail-agent/backend/src/globalmail_agent/application/risk_records.py:28`，直接故障门在第29–33行；关联读取在第18–23行。**

要求：`Product-Spec.md:522/536` 要求有效危险直接持久化 HITL；`AGENT-ARCHITECTURE.md:228` 要求在同一事务保存有来源风险、下一轮加载已有有效风险时先执行安全门；第230行规定“已有有效风险”必须 active 且依据未撤销，“仅点完成回复不自动清除风险”“不能让模型自行清除未处理风险”。

实际代码：`store_risks` 仅按 conversation/kind/status=active 查既有行。旧图 A 撤销后，旧风险行仍 active，`active_risks` 根据内容撤销门将它跳过，这一步拒读正确。新图 B 再形成相同 kind 的有效风险时，`store_risks` 看到旧行直接 continue，没有登记 B 的新来源。B 本轮仍由 `agent/graph.py:116` 和 `application/commit_outcome.py:64` 正确进入人审，但数据库只剩依赖已撤销 A 的旧风险。以后 `worker/agent_runner.py:74` 加载 active_risks 得到空列表，允许模型重新决定；合法固定响应不再返回风险即可模拟发信。

独立可达步骤，没有伪造数据库风险或撤销状态：

1. 通过正式附件/消息服务接收实际 PNG A，正式 Graph 输出 schema/source 合法 `fire`，1次模型调用、HITL。
2. 以当前 row/input/epoch 调用正式 EvidenceService 撤销 A；人工回复使用默认 `keep_active`。
3. 新上传实际 PNG B，通过仅图片新客户来信绑定 B；正式 Graph 再输出合法 `fire`，1次模型调用、HITL。
4. 此时读取 `detail.active_risks=[]`；数据库唯一 fire 行属于第一轮 A，`status=active`，没有 B 的风险行。
5. 人工回复显式 `risk_decision=keep_active`；在下一封客户来信之前 claim 仍被屏障拒绝。下一封新客户来信合法恢复，固定模型给无风险 Understanding 和合法补问草稿。
6. 实际调用3次模型并模拟发信1封，处理权回到 agent。B 的已识别且未人工解决危险不再触发恢复安全门。

关键原始输出：

```text
test_new_valid_image_risk_after_old_risk_source_revoked_stays_active ... FAIL
REPLACEMENT_RISK {"new_risk_handoff": "human_review", "active_risks": [], "outbound": 0}
AssertionError: Lists differ: [] != ['fire']
Ran 1 test in 3.381s
FAILED (failures=1)
RISK_REPLACEMENT_RESULT {"tests":1,"failures":1,"errors":0,"skipped":0}
```

追加实际恢复/出站反例并与最终联合撤销测试共同运行：

```text
test_revoking_one_joint_image_keeps_other_preview_but_invalidates_shared_evidence ... ok
test_new_valid_image_risk_after_old_source_revoked_survives_next_human_reply ... FAIL
AssertionError: 3 != 0 : An active fresh-image risk must handoff before another model and cannot be cleared by model output
Ran 2 tests in 9.123s
FAILED (failures=1)
REPLACEMENT_RISK_EFFECT {"second_model_requests":1,"active_after_second":[],"persistent_risk_rows":[{"run_is_second":false,"status":"active","kind":"fire"}],"third_error":null,"third_model_requests":3,"agent_outbound":1,"third_owner":"agent"}
REVIEW5_STRICT_RESULT {"tests":2,"failures":1,"errors":0,"skipped":0,"source_changed":false,"changed_files":[]}
```

两项运行前后对 backend src/tests/migrations 全部 Python/Prompt 内容做 SHA256 快照，无源变化。反例使用现有 `VisionFixture.image_mail`、`VisionModel/image_output`、正式 `EvidenceService.mutate`、`ConversationService.human_reply/append` 与 `AgentRunner.execute`；识别值是固定工程输入，不涉及模型识别准确率。问题发生在已通过来源/schema 的风险之后，属于本期不得放宽的确定性安全门。

复现关键代码，置于已初始化隔离 fixture 中即可复跑：

```python
cid, rows = self.image_mail()
def risky(messages):
    value = image_output(messages)
    value["images"][0]["risk_flags"] = ["fire"]
    return value
self.execute(VisionModel(risky))
conv = self.conversation(cid)
EvidenceService(self.engine, self.store).mutate(
    UUID(rows[0]["attachment_id"]),
    EvidenceCommand(expected_version=conv["row_version"],
        expected_input_revision=conv["input_revision"], evidence_revision=0),
    uuid4().hex, revoke=True)
conv = self.conversation(cid)
self.service.human_reply(cid, HumanReply(expected_version=conv["row_version"],
    expected_input_revision=conv["input_revision"], body="Please send a fresh photo."), uuid4().hex)
fresh = self.stage(cid=cid)
self.service.append(cid, AppendMessage(expected_version=self.conversation(cid)["row_version"],
    body="", attachments=[{"attachment_id": fresh["attachment_id"]}]), uuid4().hex)
self.execute(VisionModel(risky))
conv = self.conversation(cid)
self.service.human_reply(cid, HumanReply(expected_version=conv["row_version"],
    expected_input_revision=conv["input_revision"], body="Awaiting your confirmation.",
    risk_decision="keep_active"), uuid4().hex)
self.assertIsNone(self.leases.claim("wait_customer"))
self.append_mail(cid, "I have supplied the new photo. Please continue.")
model = VisionModel(image_output, terminal("Please share more information."))
self.execute(model)
self.assertEqual(len(model.requests), 0)
```

修复标准：新风险同事务具有当前有效来源；旧撤销来源不能阻止登记新有效风险，也不能放宽旧内容禁读。keep_active 后新客户输入应先确定性 HITL，0新增模型请求、0新增 Agent 出站；显式人工风险解决/误判才使用对应有依据修订。处理重复风险还须遵守 `adapters/agent_schema.py:90` 的 run_id/kind 唯一约束，保留无正文审计。修复由主 Agent 执行，本轮没有修代码或提前关闭 HIGH。

失败快照 SHA256：

| 文件，backend/src/globalmail_agent/ 下 | SHA256 |
|---|---|
| `application/risk_records.py` | `1be9fb4da083c342631c282a08fc2fa3cebfb01478003469c90744120306b2e7` |
| `attachments/corrections.py` | `397597754c222e21160267ba882205fc674b9c7ef48eb83833e561b286ab4ce8` |
| `attachments/evidence.py` | `1391d829a2a49e1ea453957fb5e159633cd7fdfddf4993e524aa8dcb543256a9` |

报告收口时主 Agent 已修改 risk_records.py，当前 SHA256 为 `a9855997e54cf0244fcb9e7c9d3e54699f7cbeaa03fe0e703c3be768155ed3eb`。上面的行号与失败判断绑定修前SHA；本轮没有重跑该修后源码，不将修复声明改写为本轮PASS。

## Stage 1：完整工程映射

下表 PASS 仅指明确列出的本期工程部分，不代表整条产品 AC 已勾选。语义延期均未通过。后端位置统一前缀 `globalmail-agent/backend/src/globalmail_agent/`，前端位置统一前缀 `globalmail-agent/frontend/src/`，测试位置统一前缀 `globalmail-agent/backend/tests/`。

| 需求/AC | 本期工程结论及延期范围 | 代码与实际证据 |
|---|---|---|
| REQ-014 接收格式/限额；AC-065 图片候选/仅图 | 工程 PASS；真实字段准确率及不重复补问语义延期 | `attachments/validation.py:8/16/29/33/35/37/39` 真 JPEG/PNG/静态WebP、10MiB、20Mpix、verify+load；`intake.py:22/43` 不生成消息；`binding.py:49/73` 原子绑定/20MiB。`test_attachment_validation.py:29/45/55` 与 `test_attachment_intake.py:53` 在开发者最后68项稳定专项通过；本轮实际 image_mail/Graph 真 PNG 输入通过。 |
| AC-066 歧义/精确对象/客户范围 | 工程门 PASS；冲突/多订单澄清语义延期 | `attachments/understanding.py:8/59/63/69` 保留歧义、raw读数，歧义不取得查单资格；`agent/tool_gateway.py:96` 有来源号码并沿用当前客户精确查询。本轮四字段完整更正 Graph 中旧 order_number 不再有效，人工号码独占候选资格。 |
| AC-067 观察/推测/来源位置 | 分层与引用工程 PASS；识别/根因/责任/鉴真语义延期 | `attachments/understanding.py:15/20/21/22/23/24` 分层；`evidence.py:61/79/81` analysis/source hash/view hash/epoch/kind；`views.py:50/55` 明确实际整图与校正尺寸。本轮联合两图检查点/逐图证据测试通过，不伪造精确框。 |
| AC-068 外观正常不否定功能、局部不认缺件 | 规则接入 PASS；模型遵守与否延期，未验收 | `agent/prompts/visual-understanding.md:11/12` 明确规则；`agent/graph.py:82/85` 送入同次联合理解请求。Prompt 存在不证明语义正确。 |
| AC-069 图文/SOP/政策分流 | 本期来源/权限接入 PASS；内部售后申请 Phase9，分流语义延期 | `agent/graph.py:82` 联合请求；`agent/tool_gateway.py:96` scoped业务查询；`application/draft_validation.py:35/38/40` 适用资料和业务工具门；`agent/context.py:84` 明示售后写不可用。没有新增资格授权工具。 |
| AC-070 危险直接人审/持续有效风险 | **部分实现、FAIL，HIGH**；危险识别准确率/安全话术语义仍延期 | `agent/graph.py:116`、`application/risk_handoff.py:5`、`commit_outcome.py:64/74` 本轮单次合法危险输出共事务HITL通过；`risk_records.py:29` 新来源同类风险被旧撤销 active 行吞掉，实际后续3模型/1出站反例见上。延期不覆盖这个确定性缺陷。 |
| AC-071 截图不改账本 | 来源/工具工程门 PASS；Phase9真实业务动作和截图语义延期 | `agent/understanding.py:69/73` 图片不能冒充 human/customer/tool事实；`draft_validation.py:40` order_fact必须业务工具；`agent/prompts/visual-understanding.md:14/15` 图像履约声明为不可信客户内容，现有工具白名单无售后交易效果。 |
| AC-072 缺失/不支持/损坏/技术失败 | 工程 PASS | `attachments/importing.py:26/41/43` missing/unsupported保存；`validation.py:29/35/51` 真格式/动画/坏图；`worker/agent_runner.py:146` 逐图真实 failure_reason；`queries.py:15` 公开安全原因。本轮缺字节preview503/evidence200/correction422/revoke200，原件损坏0模型请求并failed/attachment_integrity_error。 |
| AC-073 附件/CID/仅图/远程/幂等 | 工程 PASS | `domain/conversation.py:25/43` 受控ID和元数据且metadata不能替代仅图；`binding.py:12/37/49/78` 固定顺序CID清单、重复ID/CID拒绝和重放一致；`application/conversations.py:25/43/54` 共事务接受。开发者68项含 `test_attachment_binding.py:15/39/60/80/107`；本轮metadata幂等和仅图Graph通过。API无客户端路径/URL入参，`MessageTimeline.vue:29` 按文本显示正文。 |
| 受控案例真字节；AC-073/074 | 工程 PASS | `application/fixture_conversations.py:40` 正式入口；`attachments/importing.py:44/62/71/75/78` 包内manifest content_id/resolve/限额/SHA/实际解码后入库。本轮实际PNG原图读回、包外路径拒绝、历史完整Graph仅1可见图/0未来图/0出站通过。 |
| AC-074 scope/用途/历史截点/缓存 | 工程 PASS；默认无跨run联合缓存 | `attachments/queries.py:22/37/44/51/64/91` 逐次全scope/可见prefix/原件与缩略图摘要/journal授权；`evidence.py:17/30` 人工版本也需可见且当前epoch；`views.py:63` 网络前重新授权。开发者68项含逐SCOPE_KEYS及复合FK反例，本轮真实历史未来图/正文不进模型。 |
| AC-075 图中文字不授工具权 | 工程权限边界 PASS；模型注入语义专项延期 | `agent/prompts/visual-understanding.md:14/15` 数据规则；`agent/graph.py:169/171` 未声明工具拒绝；`api/security.py:38` 原Host/Origin/类型门；`attachments/importing.py:62` manifest白名单不取外链。没有额外视觉Agent/OCR/真实邮箱/外部交易权限。 |
| AC-076 预算/未知usage/重试 | 工程 PASS；真实视觉usage/时延和语义延期 | `attachments/views.py:17/26/31` EXIF/非生成式1024全图/保守patch上界；`agent/budget.py:46/54/56/72/98` 原6请求、6视图、12工具、120秒、16k输入、80k累计；`agent/graph.py:45/55/67` 每次网络重试重新授权计数，unknown保守占用；`adapters/model_provider.py:10/38` validation3990+10/2048thinking保持。本轮4图第二次网络前超6视图被拒、未知不记零通过。 |
| 原图不入Graph/checkpoint/trace/RAG | 本期工程 PASS；正式Langfuse导出Phase11 | `adapters/model_provider.py:25/28/33` deepcopy后临时SDK data字节；`views.py:50` Graph只refs；`attachments/evidence.py:43` private raw在有效Understanding落盘前pop；`observability/local_records.py:19` 受控对象/安全事件。本轮真实SDK参数捕获/原messages不变和实际checkpoint无base64/image_url通过；无共享图片RAG写路径。 |
| AC-077 晚到/停止/接管/新输入/更正/重置 | 本期提交栅栏 PASS | `agent/guard.py:43/54/65/68` slot→branch→conversation→排序attachment→head→run/task/cycle并检fence；`worker/leases.py:23` qualified校验input/authority/generation/stop；`attachments/corrections.py:45/49/51/78` row/input/epoch修订关旧run；`application/task_queue.py:15`/`worker/jobs.py:58`/`worker/leases.py:128` 中断processing。本轮stop/takeover/input/revoke真实回调和过期租约均0有效分析/0出站；更正/人工回复本身不能claim，下一客户输入才恢复。 |
| AC-078 即时撤销/衍生内容/清理 | 即时禁读工程 PASS；完整副本物理删除/backup恢复未实现，Phase12 | `attachments/revocation.py:10` 递归dependencies禁读；`body_store.py:50/63` 展示redaction/字节410；`run_records.py:40`/`checkpoint_repository.py:107` run/checkpoint拒读；`agent/memory.py:14/30` 混合来源事实登记原图；`human_review.py:16/76/90` 人工note/draft/reply依赖。本轮混合marker不可读、人工派生隐藏、原分析/checkpoint拒读，联合B preview200/GET410/POST410且无版本副作用通过。新有效风险登记FAIL另见AC070，不以撤销旧内容正确抵消它。 |
| AC-079 多图/重复/超限/部分未读 | 工程 PASS；跨商品视觉映射语义延期 | `binding.py:12/73` 四图/总20MiB/重复拒绝；`views.py:34/37` 有界选图；`agent/graph.py:79` 显式未覆盖；`attachments/understanding.py:42/48` 每图恰一分析、unreadable不得产字段/观察/风险。本轮两图真字节/逐图证据、missing保存及4图预算路径通过。 |
| AC-080 人工有效优先/修订/屏障 | 本期更正工程 PASS | `attachments/understanding.py:78/87/89/96/102` 移除同字段自动facts/candidates/intent并加入有来源人工事实；`agent/graph.py:103/104/111` 重投影有效source；`evidence.py:69/77` 不覆盖人工同列；`corrections.py:45/49/51/78` CAS/supersedes/增epoch且不自动恢复。本轮四字段正式Graph旧值均不有效、人工值有效、原raw仅审计；正常观察更正/幂等/过期epoch/人工回复屏障通过。 |
| AC-081 工作台上传/预览/证据/失败/更正/撤销 | 代码与既有真实页面工程证据 PASS；本轮未进行新的视觉一致性验收 | 前端 `ImageUpload.vue:37/51/66/79` 防串scope/失败保稿/同bytes重试key；`pending-image-uploads.ts:4`；`ConversationDialog.vue:42/175` 与 `MessageComposer.vue:55` 仅图；`ImageEvidenceDrawer.vue:73/89/111` allSettled独立预览/证据、fallback epoch与危险确认；`api/attachments.py:47` no-store/nosniff。明确历史真实证据 [browser-api](artifacts/phase8/browser-api.json)、[保存503保稿](artifacts/phase8/send-failed-retains-image.png)、[900抽屉](artifacts/phase8/evidence-drawer-900.png)；本轮实际HTTP故障/撤销复跑通过，不把旧图片称为本轮新UI操作。 |
| AC-082 真实冻结专项 | **延期，未执行，未通过** | `DEV-PLAN.md:178/191/328` 与实施步骤6；本轮全部工程固定输出/SDK捕获均0付费模型，不作为视觉字段/观察/分流/禁止动作质量证据。Phase1/7原FAIL保留。 |
| 草稿取消/24h暂存清理 | 工程 PASS；不是完整删除 | `attachments/intake.py:67/90/104/126` 只清无消息引用的取消/过期对象、再次锁定并复查FK/dependencies；`worker/agent_runner.py:165` 定期扫描；开发者稳定68项含 `test_attachment_lifecycle.py:16/40/56/76/89` 真PG引用保留/过期/磁盘失败/journal。 |

本期三表/API/组件均属于 REQ-014/Phase8：`adapters/attachment_schema.py:9/34/43`、`migrations/versions/0007_visual_evidence.py:114`、`api/attachments.py:20`、`api/visual_evidence.py:9`、前端图片组件。`ImageEvidenceDrawer.vue:41` 明确完整副本删除留后续，没有未实现的删除成功入口。未发现新增scope creep或指向未实现交易工具的引导。旧0001–0006迁移未改；新0007仅在隔离schema验证。

## 旧发现独立关闭与工程原始输出

第四轮唯一 MEDIUM：联合两图→撤销A→合法更正B，原先解析REDACTED为JSON得到500。本轮读过正式 `test_vision_graph.py:16` 的实际PG/Graph/HTTP前提与完整断言，独立执行两次：

```text
B preview: 200, original PNG (thumbnail=false)
B visual-evidence: 410 image_content_revoked
B corrections: 410 image_content_revoked
conversation.row_version unchanged
B evidence_epoch = 0 unchanged
processing_owner = human_review
claim("no_automatic_resume") = None
```

对应严读代码 `attachments/evidence.py:32/69/97/106` 与 `attachments/corrections.py:68` 已用 read_bytes；失败不扩大权限、不重建旧共同分析。最后6类机器JSON路径 `agent/context.py:97`、`agent/tool_gateway.py:52`、`application/understanding_revisions.py:28/35/45/50`、`application/draft_validation.py:27`、`worker/agent_runner.py:99/123` 均走严格字节门。显示正文仍用read_body；`risk_records.py:20` 与 `run_records.py:47` 在JSON解析前明确检查REDACTED，不把占位符当JSON。

本轮独立20项定向：全部vision graph、正常更正/人工派生撤销/存储故障、SDK捕获、4项导入、四字段正式Graph、missing HTTP、lease、历史和混合事实。原始结果：

```text
Ran 20 tests in 60.567s
OK
MANUAL_GRAPH {"key":"sku","old_effective":false,"manual_effective":true,"raw_audit_preserved":true,"automatic_resume":false}
MANUAL_GRAPH {"key":"model","old_effective":false,"manual_effective":true,"raw_audit_preserved":true,"automatic_resume":false}
MANUAL_GRAPH {"key":"error_code","old_effective":false,"manual_effective":true,"raw_audit_preserved":true,"automatic_resume":false}
MANUAL_GRAPH {"key":"order_number","old_effective":false,"manual_effective":true,"raw_audit_preserved":true,"automatic_resume":false}
MISSING_HTTP {"preview":503,"evidence":200,"correction":422,"revoke":200,"status":"revoked"}
LATE_LEASE {"error":"lease_expired","analysis_count":0,"outbound_count":0}
HISTORICAL_GRAPH {"visible_images":1,"future_images":0,"actual_image_decode":true,"outbound":0}
MIXED_FACT_REVOKE {"previously_readable":true,"marker_readable_after_revoke":false}
REVIEW5_RESULT {"tests":20,"failures":0,"errors":0,"skipped":0,"seconds":63.032,"source_changed":true,"snapshot_files":568,"changed_files":["globalmail-agent/frontend/src/types/import/components.d.ts"]}
```

此20项同时对backend与frontend做快照；独立IAB打开Vite页面产生自动组件类型声明变化，只有该生成文件发生变化，后端未变。因此shell exit1是源快照门拒绝，不能称完整冻结源20项通过。随后对关键联合反例/新危险恢复反例做后端完整快照，2项运行 source_changed=false，但其中新风险反例FAIL，不能把20绿覆盖新增失败。

主 Agent 已归档稳定受影响模块68项，并保存全量317项source_changed=true。已直接读取 [focused-tests.json](artifacts/phase8/focused-tests.json)、[focused原日志](artifacts/phase8/focused-tests-final.txt)、[全量结果](artifacts/phase8/backend-tests.json)、[regression-scope](artifacts/phase8/regression-scope.json)。它们证明既有专项，未覆盖本轮新风险替换前提：

```text
Ran 68 tests in 156.133s
OK
tests=68 failures=0 errors=0 skipped=0 source_changed=false
Ran 317 tests in 677.333s
OK
tests=317 failures=0 errors=0 skipped=0 source_changed=true
```

317项不能称最终冻结全量；运行中8个JSON读取/测试改动由最后68项定向覆盖，映射记录在regression-scope。本轮不追加无差别全量或付费质量测试。旧316项迁移种子错误、原图/缩略图错误断言及前四轮FAIL原证据保留。

本轮独立编译/类型检查原始输出（stdout/stderr无编译诊断）：

```text
# backend/.venv/Scripts/python.exe -m compileall -q src tests migrations
compileall_exit=0
# frontend/pnpm exec vue-tsc --noEmit
vue_tsc_exit=0
```

主 Agent [前端测试](artifacts/phase8/frontend-tests.txt)、[构建日志](artifacts/phase8/frontend-build.txt) 原始输出，本轮未冒充新独立Vite构建：

```text
ℹ tests 55
ℹ pass 55
ℹ fail 0
ℹ skipped 0
ℹ duration_ms 2520.6163
✓ built in 30.45s
```

## Stage 2 与收口

Stage 1 存在新增 HIGH，按 skill **Stage 2 未执行**：本轮没有新的全面安全扫描、代码质量/文件长度最终判定、测试真实性专项或邻居渲染PASS。第三、四轮的扫描/实际人审与知识库邻居截图属于明确历史范围，不能替代第五轮质量审查。本轮编译和实际反例是Stage1工程证据，不改变停止规则。

第五轮工程收尾仍FAIL。主 Agent 需修新风险来源被旧撤销active行吞掉的问题，并在真实PG/Graph中验证新风险持久化、keep_active后0模型/0出站、显式人工解决路径和旧来源继续410，再派fresh reviewer从Stage1重新审。本报告不更新需求、取消延期、不勾82项AC；Phase1/7原语义FAIL、AC082、Phase9售后写、Phase12完整删除继续保留原边界。
