# 补件未出库前改为退款并撤销旧待办

编写的业务演练案例，不是真实客户历史；商品与金额沿用已有原型。

业务：补寄配件；订单：999-7200020-8200000；商品：H-CTD16-US-BK；实付：USD 54.99。

资料依据与边界：依据OUTON-01 SOP、精确SKU适配清单和项目售后政策；客户及外部履约记录为隔离资料创作，不模拟Agent已发送的答复或已提交的申请。

## 首封来信

Hello, my OUTON lamp from order 999-7200020-8200000 arrived without the remote. I have checked all the packaging and the lamp works from its own buttons. Could you send the missing remote, please?
Regards, Simon

## 后续往来与处理

### 第 1 步 · Agent 应判断 · 来信后 0.2 小时

核对缺遥控问题及可用补件方案。

这一轮应处理：复用订单、核对缺一只遥控器、精确适配及库存；确认补件选择与收件地址。

### 第 2 步 · 客户 · 来信后 4 小时

Yes, please send one matching remote to Simon Reed, 315 Oak Lane, Boise, ID 83702, United States. That is the address for the lamp order.

这一轮应处理：记录补件选择与地址。

### 第 3 步 · 客服 · 来信后 4.1 小时

录入客户确认的补件地址。

这一轮应处理：保留地址版本与客户来信依据。

### 第 4 步 · Agent 应判断 · 来信后 4.3 小时

补件条件齐备，等待Agent创建内部申请。

这一轮应处理：精确适配、库存、客户选择与地址确认后提交补件待办；不得提前宣称发货。

### 第 5 步 · 客服 · 来信后 18 小时

履约同事建立遥控器补发单，尚未拣货，未创建面单。

这一轮应处理：关联实际补件申请，仅记录建单状态。

### 第 6 步 · 客户 · 来信后 23 小时

I am sorry to change the plan, but I would now rather return the lamp for a full refund. If the remote has not left the warehouse, please cancel it. The lamp and the original packing are here. I do not want both a remote and a refund.

这一轮应处理：记录客户改变选择，保留旧申请和执行历史；先确认能否取消，不立即并行退款。

### 第 7 步 · Agent 应判断 · 来信后 23.2 小时

查旧补件申请及最新出库、面单和揽收状态。

这一轮应处理：识别同一问题方案变更；请求人工履约同事暂停并核对取消；在取消回执前不创建新的补件或退款；确认退回数量1、原缺件原因，说明先退回验收。

### 第 8 步 · 仓库 · 来信后 27 小时

仓库与履约同事核对无拣货、无面单、无出库、无承运商交接；补发执行单已取消，释放预留的一只遥控器，原补件待办同步关闭为取消。

这一轮应处理：将取消结果关联原补件申请与原执行号；保留取消审计记录，不删除历史；旧补件停止后才允许切换退货退款。

### 第 9 步 · Agent 应判断 · 来信后 27.2 小时

旧补件取消已确认，告知可转退货退款。

这一轮应处理：明确退回灯具1件及实际收到的配件，缺少的遥控器不要求补齐；给出全额USD 54.99及原支付渠道、验收前提；取得客户对完整方案的确认。

### 第 10 步 · 客户 · 来信后 32 小时

Thank you for confirming the remote was cancelled. I agree to return the lamp with the accessories I received for a refund of USD 54.99 after it is checked. There is no remote in the box because it was missing from the delivery. Please send the prepaid return instructions.

这一轮应处理：记录客户接受金额、数量和退件清单，缺件事实延续。

### 第 11 步 · Agent 应判断 · 来信后 32.2 小时

创建退货内部待办，继续同一问题。

这一轮应处理：确认旧补件为取消且无出库；复用客户确认地址，创建缺件原因的退货待办；待实际标签出具后才提供寄回资料。

### 第 12 步 · 仓库 · 来信后 50 小时

退货同事出具预付标签并安排上门取件，清单已注明原包装缺遥控器；本单请于标签发出后7个自然日内备妥，无法按时可联系调整。

这一轮应处理：必须关联Agent实际退货待办；只提供本单已出具的退件资料。

### 第 13 步 · 客户 · 来信后 76 小时

The courier collected the lamp today. I included the accessories that came with it and the return paperwork, and I kept the collection receipt. Please let me know once it has been checked.

这一轮应处理：记录客户交件，等待仓库验收。

### 第 14 步 · 承运商 · 来信后 77 小时

退件已有承运商揽收扫描，正在运回仓库。

这一轮应处理：不把揽收当作仓库收货。

### 第 15 步 · 仓库 · 来信后 172 小时

仓库收到一件灯具退货，待核对内容。

这一轮应处理：仅记录收货，仍未满足验收条件。

### 第 16 步 · 仓库 · 来信后 196 小时

仓库完成验收：灯具1件及实际随箱配件一致，原缺遥控记录已核实；退货通过，无补件外寄。

这一轮应处理：原缺件不构成退货缺配件扣款；再次确认取消补件未产生出库。

### 第 17 步 · Agent 应判断 · 来信后 196.2 小时

退款条件齐备。

这一轮应处理：复查旧补件取消、退件通过、可退金额USD 54.99；只建立一份全额退款待办，不恢复补件。

### 第 18 步 · 支付处理 · 来信后 216 小时

支付同事受理原支付渠道全额退款。

这一轮应处理：查询真实退款申请，记录处理中。

### 第 19 步 · 支付处理 · 来信后 264 小时

支付渠道返回退款成功回执，金额等于原订单行实付。

这一轮应处理：可说明退款处理已成功。

### 第 20 步 · 客户 · 来信后 289 小时

The refund of USD 54.99 has appeared on my original payment account. I have not received a remote separately. Thank you for stopping that shipment and arranging the return.

这一轮应处理：确认客户已收到退款且未出现补件双赔。

### 第 21 步 · 客服 · 来信后 294 小时

补件待办与执行在出库前取消，退件验收通过后完成全额退款；客户确认到账且无另寄遥控器，客服结案。

这一轮应处理：客服核对客户确认及相关记录后人工标记已解决。

## 处理结果

补件待办与执行在出库前取消，退件验收通过后完成全额退款；客户确认到账且无另寄遥控器，客服结案。

## 本例覆盖

补件申请后改退款、查询已有执行、撤销待办、确认无出库、退回验收后退款
