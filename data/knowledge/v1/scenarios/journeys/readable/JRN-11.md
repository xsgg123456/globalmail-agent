# 灯具冒烟停止使用后人工安排退回并完成退款

编写的业务演练案例，不是真实客户历史；商品与金额沿用已有原型。

业务：故障排查；订单：999-7200011-8200000；商品：F-ZZZ0002-US-BK；实付：USD 56.09。

资料依据与边界：依据对应SKU生产商品记录、适用SOP及项目售后政策；客户来信和业务记录为隔离资料创作，不编写厂家未确认的维修步骤。

## 首封来信

Hello, I need help with the OUTONLIFE table lamp on order 999-7200011-8200000. Yesterday there was a burning smell and a little smoke near the light fitting. I unplugged it and have not used it again. Nobody was hurt and it is cool now. I do not want to test it again. Please tell me how this can be handled.
Regards, Emma

## 后续往来与处理

### 第 1 步 · Agent 应判断 · 来信后 0.1 小时

识别烟雾与焦味，立即安全分流。

这一轮应处理：确认继续停用断电，不要求再次通电或拆解；立即触发人工接管整个会话；保留订单及无人受伤、当前已冷却的客户报告。

### 第 2 步 · 客服 · 来信后 4 小时

安全客服核对客户陈述，确定走整件退回检查；取件前保持停用，具体包装与收运条件由本单安全审核提供。

这一轮应处理：人工接管期间业务记录只入库提示，不唤起自动回复。

### 第 3 步 · 客服 · 来信后 9 小时

Hello Emma, please leave the lamp unplugged and do not test or dismantle it. We can arrange a prepaid collection for inspection and then refund the full USD 56.09 to the original payment method. Our returns team will provide the collection and packing instructions for this unit. Please confirm that you want to return the complete lamp, and tell us where it is to be collected.

这一轮应处理：记录人工方案，安全退件仍须实际审核与标签；人工回复后等待下一封客户来信恢复。

### 第 4 步 · 客服 · 来信后 12 小时

退件负责同事确认可安排上门收运；需客户确认地址后才能发标签和预约。

这一轮应处理：人工回复后等待客户期间，仅保存业务进展；不自动回复、不预约未确认地址。

### 第 5 步 · 客户 · 来信后 26 小时

Yes, I would like to return the complete lamp for the full refund of USD 56.09. It is still unplugged and cool. Please collect it from Emma Brooks, 62 Willow Street, Raleigh, NC 27601, United States. I have the original box and accessories.

这一轮应处理：此来信恢复Agent；记录客户选择、数量1、当前状态和取件地址。

### 第 6 步 · 客服 · 来信后 26.1 小时

录入客户确认的退件取件地址。

这一轮应处理：以本封客户来信建立地址版本1。

### 第 7 步 · Agent 应判断 · 来信后 26.3 小时

客户已明确选择退回退款，等待Agent建立退货内部待办。

这一轮应处理：复用订单行、数量1及前述缺陷原因；按客户本次选择建立退货待办，先退回验收再退款；缺陷退货由商家承担标签费用。

### 第 8 步 · 仓库 · 来信后 44.3 小时

客服已出具缺陷退货标签并安排上门取件；本单数量1，备妥期限为出具标签后7个自然日，延期可先联系。该期限仅为本次安排。

这一轮应处理：必须匹配Agent实际退货待办；此时才可向客户提供已存在的标签和本次退件说明；说明仓库验收后再安排原支付渠道退款。

### 第 9 步 · 客户 · 来信后 74.3 小时

The courier collected the lamp today under the arrangements in your message. It stayed unplugged and cool, and I included the accessories in the box. I have the pickup receipt.

这一轮应处理：记录客户已交件，不把交件或承运商扫描视作仓库验收。

### 第 10 步 · 承运商 · 来信后 75.3 小时

退件运单新增承运商揽收扫描，尚未到仓。

这一轮应处理：保持退款待验收，查询退件进度时引用此记录。

### 第 11 步 · 仓库 · 来信后 170.3 小时

仓库签收一箱退件，订单与数量1匹配，尚待检查。

这一轮应处理：区分仓库收货与验收通过，不提前宣称退款已完成。

### 第 12 步 · 仓库 · 来信后 194.3 小时

仓库完成退件核对：商品与订单一致，数量1及随箱配件齐全；缺陷退货验收通过。

这一轮应处理：依据收货与验收记录才允许继续退款；安全问题不要求重新通电验证。

### 第 13 步 · Agent 应判断 · 来信后 195.3 小时

退件验收完成，核对实付与既有退款余额。

这一轮应处理：以原订单行实付USD 56.09核对可退余额；查询同一问题所有待办与执行，避免重复赔付；建立原支付渠道全额退款内部待办。

### 第 14 步 · 支付处理 · 来信后 218.3 小时

支付同事已受理全额退款，原支付渠道处理中。

这一轮应处理：匹配Agent实际退款待办；仅说明处理中，不保证到账时间。

### 第 15 步 · 支付处理 · 来信后 266.3 小时

支付渠道返回全额退款成功回执，金额与原订单行实付一致。

这一轮应处理：可依据成功回执说明已完成退款处理；不要求客户再提供银行卡信息。

### 第 16 步 · 客户 · 来信后 290.3 小时

I can see the full refund of USD 56.09 on the original payment account. Thank you for arranging collection so I did not have to use the lamp again.

这一轮应处理：记录客户确认退款及问题处理结果。

### 第 17 步 · 客服 · 来信后 296.3 小时

客户选择退回退款，仓库收货并验收通过，原支付渠道全额退款成功且客户确认，客服核对后结案。

这一轮应处理：客服核对客户确认及相关记录后人工标记已解决。

## 处理结果

客户选择退回退款，仓库收货并验收通过，原支付渠道全额退款成功且客户确认，客服核对后结案。

## 本例覆盖

安全报告、停止使用、整段人工接管、事件仅入库、下一来信恢复、退回验收退款
