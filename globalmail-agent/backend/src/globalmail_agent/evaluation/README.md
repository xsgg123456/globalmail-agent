# 连续流程驱动器

`ScenarioDriver(FixturePackage(), callbacks, state_directory=...)` 建立原 51 输入和 21 JRN 的独立驱动。构造与报告不调用 Agent、不改业务账本。初始报告为 72 项 `not_run`；这不是业务或模型验收结果。

运行顺序：`start(scenario_id)` 提交白名单初始资料；`advance(scenario_id, now, ...)` 每次最多交付一个当前事件。`now` 为显式、带时区的模拟时间；不自动跳到未来。所有事件完成后，再调用一次 `advance` 读取末尾观察并完成报告。无后续事件的输入也必须有实际 run 和 outcome 才完成。

controller 只从两个固定 `controller-events.jsonl` 读取。初始资料来自 FixturePackage 的允许字段；可读故事、编辑源、manifest 预期结果及评测参考回复均不加载。`apply` 只收到当前外部事实，不收到 gate、后续事件或 checkpoint 文字。Checkpoint 不创建邮件，也不调用 `apply`。

回调实现负责调用现有实际服务，方法如下：

- `create(scenario_id, initial, command_id) -> CommitResult`：用白名单初始资料创建隔离分支；返回已提交消息/领域事件证据、真实 `conversation_id` 及 source-to-runtime 资源映射。
- `observe(scenario_id, resources) -> dict`：读同一真实账本；包含 fixture 源 `branch_id/customer_id`、真实 `conversation_id`、当前 `revision`、`evidence_refs`、`ledger_resource_ids`。`run` 含真实 `id/status/outcome/observed_steps`；`observed_steps` 用 `initial_message` 或完整已交付事件 ID 证明当前输入已被实际运行观察。可用 `runs` 携带实际历史完成运行，支持原资料的 initial-turn 触发条件。
- `verify_gate(name, current_event, observation, resources) -> GateResult`：针对当前 gate 查询现有业务服务/账本，返回具名 `status/reason/evidence_refs/resource_ids/run_id`。业务 gate 的 passed 必須同时含证据引用和实际资源编号；缺处理器或证据均阻塞。24 个原 JRN gate、三种原触发条件都有具名分支，未知 gate 永远 blocked。
- `apply(delivery, resources, command_id, authorization) -> CommitResult`：把当前客户、人工或业务事实提交给真实服务。事务资格、版本、scope、状态转换及去重仍由服务复核。`command_id` 在恢复/重试时保持稳定；服务必须幂等，覆盖“业务已提交、cursor 尚未保存”窗口。不可用时返回未提交与原因，不能生成虚假资源。

`CommitResult` 字段：`committed`、`evidence_refs`、`resources`、`run_ids`、`reason`。只有真实已提交且证据非空的收据才推进 cursor；`resources` 必须是字符串到非空字符串 ID 的平面映射，嵌套业务对象会拒绝，不建立订单/库存/退款影子账本。原 SCN-027 的显式 `replay_same_event:true` 行保留报告，引用首次提交证据并标 `duplicate_suppressed`，不二次交付；这不代替业务服务自身幂等测试。

81 个文字 checkpoint 默认 `awaiting_checkpoint`。检查者先查实际 run、回复与工具证据，再显式提供 `CheckpointVerification(event_id, staff_id, run_id, revision, evidence_refs, passed, reason)`；检查必须绑定当前快照和真实 run。失败保存 failed，未来步骤仍 not_run。人工结案另需显式 `staff_id` 与 `resolution_reason`，场景中的结案文字不会默认当成人工授权。

库存规格/快照、地址来源等缺失前提保留未知；业务服务拒绝后报告 blocked。需要补齐时通过有来源、显式的模拟事实入口准备，不能在驱动器暗填。报告含每一步所有 gate 的状态/证据、真实 run/outcome、账本资源、事务收据、失败原因及所有未运行步骤；不报告模型语义通过率。

隔离纯单测：

```powershell
$env:PYTHONPATH = 'src'
.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_*driver.py' -v
```

单测回调是内存契约夹具，仅证明 gate、事件隔离、恢复和报告行为。实际 Graph/HTTP/账本运行与 21 JRN 最终人工检查需要主流程的服务适配器和隔离数据库；付费模型语义与最终验收留 Phase 13。
