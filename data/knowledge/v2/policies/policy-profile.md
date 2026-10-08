# 三品牌隔离试运行售后政策 2.0.0

政策编号：SIM-AFTERSALES-2026-10-V2。来源：项目拟定模拟规则。状态：未发布，内容核对待完成。
本修订拟生效时间：2026-10-08T00:00:00+08:00；正式同版本发布前只供管理预览，不能授权申请或履约。
替代关系：SIM-AFTERSALES-2026-10-V1 / 1.0.1；原场景继续固定 v1。
这是独立政策修订包，不是完整知识包。技术检查通过不表示业务负责人已经核准。

## 适用范围

品牌：OUTON、OUTONLIFE、BELEEV。市场：US、GB、DE、CA、AU。
渠道：amazon、brand_store；币种：USD、GBP、EUR、CAD、AUD。
隔离模拟环境的项目规则，不是品牌承诺、销售平台现行政策或地区法律结论。超出声明范围返回 policy_not_covered；不得自动换算货币。

## 订单、选择与数量

先由业务工具核验订单、准确商品、受影响数量和实付金额。多商品或数量份额不明确先补问。
客户接受必须来自可见的客户消息，明确动作；退款须明确接受金额和币种。地址确认须与当前选择版本一致。
客户材料和图片不改变业务账本。金额用最小货币单位整数，不换汇；比例上限用整数向下取整。

## 退货与退款

退货窗口为签收后 30 天，含边界日；窗口外交人工审查。需原因、数量；非质量退货须未使用且完整。
质量问题由商家承担寄回费用；非质量退货由客户自行安排邮资，商家不报价额外标签费。
寄回指引前须有退货授权、地址、包装和邮资说明；商家付费时须有预付标签。
部分退款上限为受影响份额实付的 20%（2000 基点），客户须明确接受金额和币种。
全额退款前须有仓库收件和质检记录，数量须覆盖此次受影响份额。例外仅由人工审查。
可退余额扣除已成功退款和处理中、结果未知占用；同一申请与执行记录只扣一次，未知结果先查原操作。
退款回原支付渠道；内部申请不等于退款成功。成功须来自关联执行回执，不承诺固定到账天数。

## 换货与补件

质量换货和售后补件窗口为签收后 365 天；售后补件为 365 天。
换货默认原准确 SKU；需库存、当前地址确认、寄回收件与质检，不先发后退。替代型号须明确选择、核对兼容后交人工。
补件须准确部件与 SKU、地区和硬件版本适配、数量、库存、客户选择及当前地址确认。安全关键部件交人工。
购买备用件不表示免费售后资格。同订单行同份额的退款、换货和补件跨事项核对，不能换事项编号重复补偿。

## 物流与人工审查

轨迹超过 7 天未更新可进入查件；显示签收但未收到先核对包裹，不保证到达日期。
建标签不等于发货；查无记录、当时不可用、查询失败和未知结果分开显示。
安全风险、规则冲突、未知兼容、反复失败或例外诉求交人工；人审中业务事件只记录，人工回复后的下一封客户来信才恢复。结案由人工确认。

## 每项条件的证据要求

图片可支持规则明确允许的客户申报或可见外观条件；订单、金额、选择、兼容和履约仍须各自核验。v1 无映射时不将视觉观察升级为工具事实。

| 条件 | 允许来源 kind | 核验要求 | 缺失处理 |
|---|---|---|---|
| 准确订单商品（order_identity） | tool_fact, verified_fixture, human_decision | 业务工具核验客户范围、准确订单行和SKU | needs_input |
| 受影响数量与份额（quantity） | tool_fact, verified_fixture, human_decision | 正整数；部分数量必须有明确单位份额及金额分摊 | needs_input |
| 实付金额（paid_amount） | tool_fact, verified_fixture, human_decision | 订单行实付最小货币单位整数与币种；不得换汇 | needs_input |
| 客户明确选择（customer_choice） | customer_statement, verified_fixture, human_decision | 可见客户消息明确接受动作、数量；退款还须金额和币种 | needs_input |
| 当前地址确认（address） | customer_statement, verified_fixture, human_decision | 可见选择的地址版本必须等于当前已确认版本 | needs_input |
| 客户问题申报（reported_problem） | customer_statement, visual_observation, verified_fixture, human_decision | 准确商品已核验；视觉仅支持可见外观，不确定或未拍到不得确认为缺件或根因 | needs_input |
| 未使用且完整（return_condition） | customer_statement, verified_fixture, human_decision | 明确客户申报或人工核对；图片未拍到不证明完整或缺件 | needs_input |
| 仓库已收件（warehouse_receipt） | tool_fact, verified_fixture, human_decision | 仓库回执关联订单行，收件数量覆盖受影响份额；客户声明不替代 | needs_input |
| 仓库质检通过（warehouse_inspection） | tool_fact, verified_fixture, human_decision | 仓库质检回执关联收件记录，合格数量覆盖受影响份额 | requires_review |
| 准确适配（compatibility） | tool_fact, verified_fixture, human_decision | 准确部件/SKU、硬件版本、地区规格适配记录；无记录不猜兼容 | requires_review |
| 可用库存（inventory） | tool_fact, verified_fixture, human_decision | 当前范围库存以on_hand减reserved；当前有货不保证未来履约 | needs_input |
| 已有补偿与占用（compensation_ledger） | tool_fact, verified_fixture, human_decision | 跨事项查同订单行同份额；成功退款与处理中/未知按同一operation只扣一次 | requires_review |
| 签收与政策窗口（delivery_date） | tool_fact, verified_fixture, human_decision | 可信签收时间与当前截点比较，未知不使用购买日代替 | needs_input |
| 安全风险（safety） | customer_statement, visual_observation, verified_fixture, human_decision | 有效安全风险交人工，不凭未看清或技术失败伪造风险 | requires_review |
