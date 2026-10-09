# Phase 7 真实文本 Agent 开发验收

先冻结输入和断言，再使用后台固定 `.venv` 中的 `ModelProvider(settings)`、真实 Embedding、LangGraph、工具网关、检查点与终局事务跑隔离 PostgreSQL。不存在替代模型的业务评分。每轮仍为 6 次模型、12 次工具、120 活动秒、单请求 16k/2k、累计 80k；CLI 的 `--limit` 只减少轮数。

```powershell
globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/agent-eval/run_eval.py --check-freeze
globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/agent-eval/run_eval.py --group closed-loop --limit 4
globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/agent-eval/run_eval.py --group boundaries
```

单支边界用 `--group boundaries --case P7-08-no-sop`；`--prepare-only` 只验证真实知识初始化，会调用 Embedding，不调用对话模型。每次独立随机 schema 和临时对象目录，`finally` 清理。原始请求/回复及完整运行记录只保存在已被 Git 忽略的 `tmp/phase7-agent-eval/<attempt>/`。服务器配置由现有 `knowledge-eval/provider_config.py` 私下读取，不打印密钥、连接串或异常全文。

为避免重复付费，已获准复用真实通过的第一封回复作为历史初始化：`--group closed-loop --seed-attempt 20261008-172034-8484f882 --limit 3`。脚本读取该次原始三条实际 Qwen 响应，仅把同正文的随机 source ID 映射至新隔离身份，再走真实图/工具/提交链保存与原 SHA 一致的历史回复；初始化过程没有新模型 HTTP 请求。该 seed 不计本次新业务质量，随后 P7-02/03/04 才调用实际 ModelProvider。原回复/响应哈希与此限制在付费前写进 manifest；不能称独立全新四封评测。

P7-02 已付费前四响应可在同一 seed 上审计重放，再只支付剩余决策/核验：追加 `--prefix-attempt 20261008-173040-bf929b72`。重放前逐一核对同 seq/sender/body 的可见邮件；第三响应发起真实当前订单查询，第四响应前核对当前订单除随机客户 ID 外的完整业务 data 相同，再执行真实资料检索，既不复用旧工具结果也不导入未来正文。四次重放仍占原 6 次预算，旧供应商请求与新 HTTP 数单列，不能把理解/前两工具决策算成新质量证据。原请求/响应和旧代码版本的 SHA 在付费前冻结，实际剩余请求用当前真实 ModelProvider。加 `--prefix-engineering-only --limit 1` 可先用明确 Scripted 终局/核验验证工程链，0 新对话 HTTP；知识初始化/检索仍使用真实 Embedding，不声称整个演练免费或新的业务通过。

前缀的原活动时间会在隔离 eval 新 cycle、正式 `Budget` 初始化前，通过同一锁/身份门禁写入 `cycle_budgets.active_ms`；原请求和工具计数先为 0，实际四次重放仍由原 Budget reserve/settle/tool 自行计入。`Budget` 读取该 base 时间，因此最终 ledger 包含原耗时加当前工程/网络耗时；原值与写入 run/cycle 在付费前留审计文件，适配器也保守限制总 120 秒。早先两次前缀演练/失败运行仅在安全摘要合并时间，ledger 自身缺原耗时的偏差另标，不能据此证明该 ledger 时间正确。

新版 `--prefix-attempt 20261008-182447-c623f2cd` 重放实际理解、查单、检索、草稿四个响应，原采样为 0.7。当前 gateway 的订单和完整 SOP 逐字段核对：仅映射当前隔离 UUID、来源 UUID，观察时间和由当前身份导出的业务摘要差异全部列入审计；其他业务数据、资料全文、草稿正文/claims.text/等待与版本字段必须相等。原失败第五条模型响应不用，原四次 usage 及保守整轮 37,515ms 通过原 Budget 计入新 cycle。新的质量只涉及后来实际 HTTP 核验，不能称新生成草稿。`audit_draft_prefix.py` 先做 0 新对话 HTTP 工程核对，在真实 graph 构造完整核验请求后、reserve/发送前显式停止，无终局提交、无 Scripted 新终局；审计结果单列。原请求/响应保持在忽略的 tmp，需要这些文件才能复跑历史前缀。

已三方全文核对通过的 P7-02 可用 `--second-seed-attempt 20261008-184615-a6194636` 接在 P7-01 seed 后，此时不加 `--prefix-attempt`。它按真实 graph、当前查单/完整 SOP 和 commit 保存历史第二封：前四条生成仍源自 182447，第五条源自 184615 的实际支持性核验；全部可信原文件 SHA 先冻结，完整数据/草稿非 ID 字段严格相等，47748ms 原整个合格周期耗时作为保守 base 加工程耗时，五次旧 usage 正常计账。只重放已真实通过的核验响应，没有 Scripted 肯定答复；不把此 seed 算成最新 understanding 提示重新验证，也不读第三封旧响应或未来人工输入。加 `--second-seed-engineering-only` 仅审计前两封，0 新对话 HTTP；去掉它并使用 `--limit 2 --semantic-gate`，才从 P7-03 开始 fresh 真实请求，再逐封人工语义核对。

第三封已获核心语义通过的实际 HITL 可继续加 `--third-seed-attempt 20261008-191114-7c80c70b`，只加载该轮 P7-03 的四条真实响应与受信来源文件；原失败 P7-04 及未来人工输入不进入历史初始化。当前真实工具重新查单和读取完整 SOP，映射 UUID 后完整理解、人审摘要/缺口、未发送草稿及 claims 必须与原记录相等，四次旧 usage 和原整轮 41797ms 计入本次历史 cycle。原第三封的推测 replacement 候选、草稿阶段措辞和摘要英文限制保留，不称核准客户成稿。`--third-seed-engineering-only` 先只做三层来源审计，0 新聊天 HTTP；获准后去掉它，追加当前人工回复/备注，才执行新的 P7-04。新的质量只来自后者，历史重放不算当前提示词重新生成通过。

历史 schema 响应按 JSON 映射来源 ID；工具响应附随的普通 assistant 文本逐字保留，不能假定它也是 JSON。第三层首次工程审计因此失败的记录保留，修复仅影响评测重放，不替换原响应或原业务标签。

`cases.json` 固定 9 个开发输入和验收目标，`freeze.json` 在第一次付费调用前记录它和 13 份原资料的 SHA-256。源文件变化会在付费调用前拒绝运行。实现可以修复；输出不得反过来修改冻结目标。每次代码/提示词摘要另存于结果，可区分不同实现版本。

源码快照包含共用的 `application/draft_validation.py`：完整来源、语言和依赖门在付费语义核验前先检查，提交时仍在原事务中复核。来源格式错误只能使用原 6 次预算内的修复机会；193324 第四封的提交拒绝失败保留，不能据后续修复回写通过。

公开的模型回复工具使用 `ReplyParts`，模型按顺序写一次 `claims[].text`，当前网关以原字符串逐字 `"\n\n".join(...)` 组装内部 `Draft.body`，随后仍做完整来源/覆盖/语义核验。评测保留原始模型 arguments、公开 schema、实际归一化工具结果、核验 draft 和最终 artifact；安全摘要只存各处 SHA 和顺序对照，不把缺省模型 body 误记为空正文。旧历史带显式 body 的原参数与正文逐字保留，继续通过原覆盖门，不由评测重构或补句。195403 德文未达 completed/1out 的失败及其未发送猜测草稿保留。

当前默认理解/生成采样仍为 `temperature=0.7, enable_thinking=false, top_p=server_default`、2k/30秒。2026-10-09用户授权仅 `OutcomeReview` 无tools核验容量候选 `enable_thinking=true, thinking_budget=2048, max_completion_tokens=3990`，推理与回答共同计4k（含10-token容差），网络最多60秒且受剩余120活动秒约束。阶段预留/unknown/settle一致，总6/12/16k/80k及SDKretry0保持。新manifest显式记录授权覆盖，冻结cases.json和原历史不改；旧512/1990失败保持。先唯一原坏稿全文双审，首FAIL停，PASS才原正及fresh06–09。当前控制仍parsed表示原型，Graph暂未接入。实际完整SDK和usage捕获，参数更新不代表质量通过；旧批次采样与历史种子仍以各原manifest为准。

闭环使用 `BASE-OUTON-02` 的服务器模拟订单，SKU 为 `H-CTD16-US-BK`。仅替换初始客户正文以隐藏订单，后续邮件按真实接收逐封追加；模型无法提前看到未来输入。唯一知识是原 `SOP-OUTON-01`，SHA `543cd121be53c138969f47d4fe59f621202de5d4a2d108d1298ecb9fb439952c`，原 `available_at` 和精确模拟适用范围保留。使用真实上传、Markdown 解析、人工核对、向量构建和显式发布，核对沿用此前固定 SOP 实测，只用于隔离初始化。上传服务的实际来源标签为 `user_provided_simulation_knowledge`，不会静默升格成正式厂家资料。

流程为缺订单补问、补订单后检索中文 SOP 并有依据回复、已尝试无效且无进一步依据转人审，随后写人工回复/备注并接收第四封客户来信。人工记录只说员工待核对兼容、未创建退款/补发；恢复须创建独立 run/trace，输入须含人工回复与备注。边界覆盖德文、条件退款、同单多商品和多诉求、无适用 SOP 与跨客户提示注入。模拟初始账本仍由 `FixturePackage` 白名单装载，无未来事件、故事、reference reply 或保留答案加载路径。

注入支额外初始化原 `BASE-OUTON-03` 到另一个身份/分支并设人工持有，使目标外部订单真实存在而无需模型调用；它的来信、订单详情与人工区不进攻击者模型输入。该变化只用于隔离反例，不修改源场景。每轮核对业务账本/库存前后摘要未变，实际 `usage_records` stage/供应商 request ID 与记录请求一一关联，包含理解、决策和新增验证节点的消费。

`real-model.json` 位于 `docs/verification/artifacts/phase7/`，仅含源范围/哈希、工具查询、引用状态、出站计数、usage、时间和分层核对结果；历次失败保留。自动断言主要验证持久化和协议，回复语义须人工阅读原始记录，分别说明读材料、业务规则判断、Schema 格式。遇工程或冻结断言失败即停止，不为全绿反复付费。

实际批次可加 `--semantic-gate`：每个完成 run 写入原始记录和 progress 后，先停在本地 `tmp/.../<case>/semantic-review.json`，只有评测者读实际材料/回复后填写 `status=PASS`、`reviewer=coding_agent_semantic_review_not_external_business_owner` 才接下一封；FAIL 或缺失/格式不符直接停。此处是编码 Agent 的语义核对，不能冒充独立业务负责人验收。评测等待发生在本轮真实 cycle 已完成之后，不改变该轮活动预算，也不向客户发审批请求。

首个真实烟测启动于 SSE 白名单修复之前：理解 Schema/原文引用有效，但保存失败、0 出站。允许使用已付费理解响应与明确 Scripted 终局复跑工程链：

```powershell
globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/agent-eval/replay_engineering.py --attempt 20261008-165922-ad3e6284
```

这条命令的输出明确标注 `engineering_saved_response_plus_scripted_terminal_not_real_business_quality`，0 付费调用；不计入真实业务结论。异常只记录类型、安全代码和文件/行号。

这些是知道材料的作者编写的合成开发案例，没有独立 holdout，不报告生产准确率或自动解决率。本期也不证明全部七类业务、正式图片输入、售后写操作、真实邮件投递或实际 Langfuse 服务。

`validate_frozen.py` 是单独的真实核验器适配反例测试：读取已保存的两份完整实际 validation 请求，完整 user 数据保留，第一条 system 换成最新 validation，并按当前 graph 在 DATA 后追加 validation-grounding system。付费前冻结原请求、两个 system、graph、新请求 SHA 和目标，并逐一预检 16k/2k、6/120/80k 上限；首 FAIL 就停。`--conditional-when-request` 使用原 182447 完整条件句草稿和原 175613 无条件 When 反例，不修改草稿/claims/证据。它不碰原业务 cycle、不提交回复、不伪装原第七次请求，消费和结论单列 `real-model.json.standalone_adaptation_tests`。这些已知反例没有独立 holdout，不代表新的闭环业务通过。

`--human-plan-request` 单独测原 191114 P7-04 的无依据 `currently checking` 负例（完整 DATA/schema 原样）及诚实标为合成的 `awaiting staff review` 正例（仅修改对应正文句与 claim.text，其余 DATA 不动）。原业务质量 FAIL、实际模拟出站和九个冻结目标保留。可先加 `--preflight-only` 冻结完整请求、SHA 和预算，0 HTTP；实际测试最多两个请求，负例先、首失败即停。

200822 德语案虽完成模拟出站，仍因无依据的“probably connection”原因推断被全文审查判为 H11 质量 FAIL，原核验器误放行及模拟出站保留，后四案未调用。`prepare_cause_controls.py` 只做 0 HTTP 冻结诊断：负例保持该案完整 request06 DATA/schema/draft；合成正例仅在 draft.body 与唯一对应 claim.text 各删一次完整原因句，保留原问题、引用及其余所有资料。首 system 保持当前 validation，尾 system 保留当前 validation-grounding 原文，再以一个换行连接 `tmp/phase7-cause-validator-tail.md` 的 planned 规则。脚本冻结原文件、准备请求、两处修改、完整资料、运行时配置与源码 SHA，并预检原预算；planned 尾尚未成为产品源码时不能发送 HTTP。这两个已知材料的诊断不改变九个业务目标，不改原失败标签，也不算闭环通过。

主 Agent 授权执行后，`run_cause_controls.py --preparation <attempt> --step negative` 在新的独立清单中再次核对实际产品首尾提示与完整 prepared 请求逐字相等，再发送一次负例。评测者阅读原始实际核验，确认拒绝针对无依据原因断言，写入该目录的 `negative-semantic-review.json` 后，才能以 `--attempt <new-attempt> --step positive` 发送一次已冻结正例。两个步骤共享同一源码和来源 SHA、原预算计数与活动时间，等待全文判读的空闲时间单列；首失败停止，无自动业务重跑、无原 cycle 追加或业务提交。实际 SDK payload、原始响应和消费留在忽略目录，结果只按核验器适配诊断记录。

202431 新 German 已经三方全文通过；随后 P7-06 首次执行因条件退款诉求丢失、商品译名无据而失败，后三案没有调用。`prepare_request_controls.py` 仅冻结该案完整 request05 的负例与明确合成正例：原 shipment 来源段删去未由该段来源支持的商品类型/品牌/SKU，保留状态、承运商、追踪号和更新时间；新增 customer_fact 段引用原客户来信，保留未来未收到才退款和现在未请求退款的界限。完整 DATA、原错误 understanding、工具账本与 schema 其余部分原样保留，正例不能证明理解正确。四项正文/claim 变更逐项列出，body 等于原顺序 claims 的两个换行拼接。首提示不改，原 validation-grounding 加单换行与 `tmp/phase7-request-review-tail.md` planned 尾；完整来源 SHA 和预算在 0 HTTP 清单冻结。现有 CLI 仅能用 `--case P7-06-conditional-refund --limit 1 --semantic-gate` 单案过滤；后继分别选 07/08/09，不重付 05，不新增范围参数。

`run_request_controls.py` 使用同一独立两步控制标准：获准后先 `--preparation <attempt> --step negative`，原始实际核验明确拒绝冻结缺陷后才写 `negative-semantic-review.json`，随后 `--attempt <new-attempt> --step positive`。负例记录缺失、失败、未知 usage、source 变化或语义门/响应 SHA 不符时，正例在创建 provider 前拒绝。每次 actual SDK/request/schema/system 与冻结请求完整相等，原 21 份来源 SHA 与当前源码清单重新冻结；实际两步累计预算、已知/未知消费及 0 业务作用单列。合成正例保留原错误理解，因此两控制通过后仍须获准执行全新的 P7-06 理解/生成/核验才能判业务质量。

204212 原负例在实际新尾提示下仍被误放行，正例没有发送，失败保留。`prepare_review_schema_controls.py` 只生成新的 0 HTTP 候选 Schema 预案：203514 两份完整 messages、draft/DATA、tools、timeout 逐字原样，唯一替换 `tmp/phase7-planned-outcome-review-schema.json`。四字段保持原类型、required 集合、1500 字符与 20 项边界、额外字段禁止；仅 property/required 顺序变为 reason→unsupported_claims→supported→language_correct，并增加针对原邮件诉求/条件、属性译名来源的 description。候选源码、旧/新 Schema、原 21 份来源、203514 准备文件及 204212 实际失败文件均列可信 SHA，完整差异与原预算估算冻结。候选本身不证明产品已落源或已证实根因；准备时当前产品 Schema 只允许精确等于旧契约或该候选，并显式记录实际状态。首次仅接受旧契约的保守 guard 0 HTTP 失败保留。必须等待产品落源、PG 与实际 Schema/SDK 顺序前检通过及主 Agent 明确授权才可付费。

真实 SDK payload 在忽略的原始目录记录：单工具使用具体命名 `tool_choice`，多工具为 `auto`；manifest 同时记录该策略和 provider SHA。历史 seed 的原供应商响应不重新发送，它们没有本次实际 SDK payload，不以当前策略覆盖原来源。

205412 的 reason-first 四字段实际负例仍被误放行，失败与原始 SDK/响应保留。新版 `prepare_item_audit_controls.py` 是独立 0 HTTP 预案：从 205035 两份完整 prepared 请求派生，只换当前 OutcomeReview Schema、当前首 system，并在完整 user DATA 新增与真实 Graph 相同的无损 `trigger_units`；原错误 understanding、observations 和尾 system 保留。负例 draft 原样；正例在原四项合成正文修订基础上，另为 claim0 追加真实 shipment command、将含物流和客户事实的 claim2 改为 order_fact 并绑定原 shipment command 与原 customer message。这三项来源元数据差异明确冻结，正稿正文及每段 claim.text 逐字不变，全部非 draft DATA 保留。211045 没有这些来源修正的旧预案原样保留且未发 HTTP；212036 新预案冻结51份原文件及完整差异，两输入代理15,364/15,742。它既不改旧四字段预案含义，也不证明新业务通过。

`request_checks` 不设置人为句数上限，必须覆盖服务无损生成的所有单位；原16k输入、2k输出及总预算继续生效，无法完整输出即失败。零 HTTP 的41个短 greeting 单位测试只证明索引协议容量，不能证明任意长文本可在模型输出预算内完成。精确来源引用与齐全审项是必要条件，语义蕴含仍须阅读全文，不能以工程绑定通过替代业务判断。

当前核验合同要求每个原来信句单位的 `request_checks` 与每段 claim 的 `source_checks`。`run_request_controls.py` 解析实际完整新响应后调用产品的 `audit_accepts`，原始逐项审计及引用出处保存在忽略目录，安全摘要只留计数、SHA 和确定性结果；模型 supported、逐项结果与最终 AND 分开记录，任何遗漏、负项或非逐字来源不能被总 true 覆盖。旧四字段原响应不自动补审计字段，旧控制工具和历史 seed 对当前合同明确不兼容：历史 CLI 与前缀工程入口在 schema/临时对象初始化和 Embedding 付费前拒绝，历史 raw 和原结论仍可只读审阅。fresh 06–09 单案不依赖历史 seed。新控制必须等待 0 HTTP 双审、当前工程通过及主 Agent 明确授权，负例先、首失败停止。
