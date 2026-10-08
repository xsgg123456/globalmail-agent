# Phase 4 实施计划

日期：2026-10-08。输入：Product-Spec v1.13 REQ-002/004/005/011/014、DEV-PLAN Phase 4、AGENT-ARCHITECTURE 第2/5/6/7/8节、v1 DATA-CONTRACT。本文细化本阶段集成，不重复维护主架构授权契约。

| 顺序 | 目标 | 完成标准 |
|---|---|---|
| 1 | 受控资料装载与账本迁移 | 仅装载商品、配件、精确适配、库存、政策和两份场景 inputs 的初始业务数据；保存摘要/来源；订单行、操作、执行、包裹、退件同一套 scoped 表；禁止事件、答案、完整故事进入查询 |
| 2 | 身份与截点限定的查询 | 服务器从会话确定身份/分支/模式/时钟；可从工作台创建独立资料场景；只读查询区分查无记录、历史不可用、未知、技术失败；多商品未选目标时要求澄清；手动会话不因同名或订单号串到资料客户 |
| 3 | 版本化政策与资格预览 | v1保持原字节；v2独立生成规则/中文说明/摘要并声明替代关系与用途；保持已批准数值；核对数量、货币整数、客户选择、地址版本、适配、库存、既有补偿和证据kind；未发布版本不得授权执行 |
| 4 | 工作台业务详情 | 沿用现有卡片、折叠区、表单和抽屉；同SKU的商品行以第几项区分，申请/执行/包裹/退件严格归到对应行；展示服务器已取得的客户选择、地址确认版本及缺失条件；提供只读资格试查；加载、空、错误、窄屏均可用 |
| 5 | 验证与交付 | 隔离PG/API覆盖越权、未来快照、多商品、金额/数量/同意/地址/证据边界；真实浏览器核对现有会话、人审与新查询；编译/构建通过；fresh code-reviewer 两阶段通过；回写进度及验证报告，中文提交 |

执行分工：后端资料/账本/查询、政策/v2/资格、前端组件可以隔离并行；主 Agent 管接口文档、集成、实际运行、审查和提交。各执行者不再派子 Agent，不提交、不覆盖他人修改。

生产盘点当前没有可授权到运行会话的真实客户订单快照。不得从案例摘要、候选 group_id 或商品 listing 拼造真实订单；未取得可信快照的历史/手动会话明确显示缺口。SCN-029仅为合成历史边界案例，不能当真实历史评测。

本阶段不创建售后申请、不扣库存、不推进模拟物流/支付、不调用模型。可读政策与程序规则只是未发布的管理预览，正式同版本发布属于 Phase 6；售后写入属于 Phase 9，事件推进属于 Phase 10。

## 集成接口

均使用既有 /api/v1 响应包裹。内部mode沿用 simulation/historical_replay，前端会话mode沿用 interactive_simulation/historical_replay。请求禁止额外字段，不能携带身份、分支、政策版本、时钟、证据或业务成功状态。

系统状态同步为phase=4，features增加business_queries=true；conversations=true、knowledge/agent=false仍对应当前实际能力。前后端契约及检查同步，不能留下phase3写死校验。

- `GET /business/scenarios` → `{items:[{scenario_id,label,mode,brand,business_categories}]}`。仅展示允许开发用途的初始场景目录，不展示未来结果。
- `POST /business/scenarios/{scenario_id}/conversations`，`{expected_version:0}`+Idempotency-Key → Phase 3 ActionResult。每次新命令创建独立dataset/身份/分支和当前初始来信；同键重试复用。此操作只创建基线，不提供事件推进。
- `GET /conversations/{id}/business?order_number=&order_line_id=` → BusinessResult。
- `GET /conversations/{id}/availability?order_line_id=&item_id=` → BusinessResult，精确商品/配件与地区/硬件适配；不合范围拒绝、不按SKU前缀猜适配。
- `POST /conversations/{id}/eligibility` → BusinessResult，纯只读预览，不落申请或调度。参数：`action`为refund/return/replacement/spare_part/logistics，`order_line_id`可空（此时需明确目标）、`quantity`正整数默认1、`amount_minor`可空非负严格整数、`currency`可空、`item_id`可空；客户同意、地址确认、缺陷等只能取服务器已验证来源，不能由请求制造。

BusinessResult：`status`为ok/empty/needs_input/denied/conflict/unavailable/unknown/error，`reason_code`、`data`、`evidence_refs`、`observed_at`、`resource_versions`、`source_kind`、`simulation`、`retryable`。错误返回不泄露其他范围事实或数据库信息。

业务详情data：`scenario_id`可空、`as_of`可空、`orders`数组、`selected_line_id`可空、`shipments/operations/executions/returns`数组、`missing_fields`字符串数组、`policy`可空。orders沿用已准备字段，lines含line_id/sku/quantity/paid_minor/hardware_revision并补product_name及unknown_fields；source_kind/snapshot_at/is_realtime明确。policy展示policy_id/version/publication_status/description/available_at/source_kind；原场景固定v1，不能自动换v2。

详情增加`customer_choices`（仅可见消息中的选择，白名单字段action/accepted/quantity/amount_minor/currency/order_line_id/item_id/part_id/address_version/source_message_id/source_message_seq/source_kind/evidence_ref）和`address_confirmation`（可空，仅confirmed/version/market/source_kind/evidence_ref）。界面用“第几封来信”标示选择出处；不公开地址token或原客户身份；多商品未明确绑定的选择保留未绑定，不能默认第一项。表单中的候选方案与已取得的选择分别展示，不能把用户试填当作客户同意。

审查修复标准：每条历史商品行与账本单独过滤Mock来源，不能沿用父订单的可信来源；退件投影保留`inspected_quantity/inspected_unit_ids`，资格判断以实际质检份额为准。补数据库→统一查询→资格服务集成回归，覆盖收件2件但仅质检1件、多商品同SKU、不可见选择及历史混合来源。

最新客户选择以服务器持久消息的seq为准，不使用资料数组排列顺序；较新的拒绝或改动作不能被旧同意覆盖。同一消息对同一目标有多条无法区分的选择、或新选择未明确目标时保持待澄清，不默认选一条。

资格与库存查询使用同一时间标准：只有来源已核验、地区/硬件明确且快照时间存在并不晚于会话截点的库存才能作为可发货条件；缺时间或未来库存不因数量充足而放行。纯函数测试也必须提供实际会出现的快照时间，不能用缺字段的假前提掩盖上游缺口。

来源包装仅可将受控Mock业务事实标为verified_fixture；其他证据kind保留原类型，图片观察、客户陈述不能因经过查询服务就变成仓库或交易事实。地址若明确关联消息，必须属于当前可见前缀；未提供消息关联的已核对初始地址仍按场景事实展示。

availability.data：item_id、order_line_id、compatible（true/false/null）、available_quantity（整数或null）、on_hand/reserved、source_kind、snapshot_at、missing_fields。

eligibility.data：`outcome`为eligible/needs_input/wait/requires_review/ineligible，`conditions`为[{code,label,status,fulfilled_by:[]}]，`policy_id/version`、`decision_id`（摘要，只作本次预览标识）、`authorized:false`、`publication_status:'unpublished'`、`remaining_refund_minor`（整数或null）、`missing_fields`。未发布不等于符合资格：分别展示计算结论与不能执行的发布门禁；将来写操作必须重算，不能把decision_id当通行证。

后端集成约定：`BusinessQueries(engine).detail(id, order_number=None, order_line_id=None)`、`.availability(id, order_line_id, item_id)`为公开查询；`.eligibility_context(id, order_line_id=None)`返回服务内部统一BusinessResult，data包含`order`、`line`（都可空）、`as_of`、`state`（仅已过滤初始事实与可见选择/地址/收件/库存/适配/操作）、`policy`（规则字典）、`policy_metadata`（摘要与未发布状态）、`product`、`parts`、`compatibility`。历史不能返回Mock政策/库存或未来订单信息；统一查询必须在一次一致读取中完成。

框架依据：[SQLAlchemy 2.1 一致事务与隔离级别](https://docs.sqlalchemy.org/en/21/core/connections.html)、[Pydantic严格类型](https://docs.pydantic.dev/latest/concepts/strict_mode/)；金额/数量使用严格整数校验，数据库查询在开启事务前确定隔离级别。
