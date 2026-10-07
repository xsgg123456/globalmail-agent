# 客户搬家使旧地址确认失效并确认新地址后换出

编写的业务演练案例，不是真实客户历史；商品与金额沿用已有原型。

业务：换货；订单：999-7200019-8200000；商品：H-SJJ0001-EU-WD；实付：EUR 59.66。

资料依据与边界：德国市场、欧规原木色商品及EUR实付沿用SCN-017；地址均为编写内容，未使用真实客户隐私。故障退回资料仅供隔离审阅。 客户、地址、单号、仓库和支付记录均为内部演练编写，不是真实客户资料或实际履约；参考回复只供评测。

## 首封来信

Hello, I would like to proceed with a replacement for the natural wood OUTON tripod floor lamp on order 999-7200019-8200000. Your colleague has already confirmed the faulty lamp and recommended a return. Please keep the same model and finish. I can send the complete lamp back this week.

## 后续往来与处理

### 第 1 步 · Agent 应判断 · 来信后 1 小时

确认同SKU库存、先退回规则及当前完整地址。

客服参考回复：

We can continue with the same model and natural wood finish. The original lamp must be returned and inspected before the replacement is sent. Please confirm the full delivery address for the replacement.

这一轮应处理：查询原木色欧规同SKU有库存，询问完整收货地址并明确先退回验收。。

### 第 2 步 · 客户 · 来信后 4 小时

I agree to return the complete lamp first. Please send the replacement to Robin Keller, Lindenbogen 16, Apartment 2, 04999 Lindenhafen, Germany. I have checked that address and confirm it is correct at the moment.

这一轮应处理：客户明确确认地址版本1及退回先行。。

### 第 3 步 · 客服 · 来信后 5 小时

依据客户明确确认保存本版收货地址。

这一轮应处理：地址确认绑定具体版本；发货前须核对最新版本。。

### 第 4 步 · Agent 应判断 · 来信后 6 小时

提交故障退货内部待办。

客服参考回复：

I have requested the return arrangements. Return postage is covered. Please wait for the return document before handing over the parcel.

这一轮应处理：记录同型号同外观及地址1，先建立退货申请等资料。。

### 第 5 步 · 客服 · 来信后 10 小时

客服提供德国退回资料：RT-10419、完整收件人和地址、商家邮资、包装与保留凭据要求。

这一轮应处理：查询对应退货申请及当前仓库记录；客户寄回或承运商签收不代替验收。；授权资料到达后，向客户交代本记录的退货编号、收件人及完整地址、邮资承担、包装和寄件凭据保留要求；引用实际存在的附件，不编造链接。。

### 第 6 步 · 客户 · 来信后 28 小时

I handed the original lamp over today and kept the receipt. One important change: our move has been brought forward, so please do not send the replacement to Lindenbogen 16. The new address is Robin Keller, Eichenbogen 72, Apartment 5, 04999 Lindenhafen, Germany. Please update it and let me check the saved details before anything is dispatched.

这一轮应处理：记录搬家指令并立即阻止旧地址出库；客户要求核对保存详情，尚非本版最终确认。。

### 第 7 步 · 客服 · 来信后 29 小时

客户提出搬家地址，本版尚未确认；先前地址确认失效。

这一轮应处理：地址确认绑定具体版本；发货前须核对最新版本。。

### 第 8 步 · Agent 应判断 · 来信后 30 小时

展示新地址并要求明确确认，保持出库暂停。

客服参考回复：

The replacement is on hold, and the old address will not be used. I have saved: Robin Keller, Eichenbogen 72, Apartment 5, 04999 Lindenhafen, Germany. Please confirm that these exact details are correct for delivery.

这一轮应处理：明确旧地址确认失效、地址2未确认；重述保存的新地址并征求确认。。

### 第 9 步 · 客户 · 来信后 34 小时

Yes, the delivery details in your reply are correct: Robin Keller, Eichenbogen 72, Apartment 5, 04999 Lindenhafen, Germany. The postcode and apartment number are right. Please send the replacement to this new address and not Lindenbogen 16.

这一轮应处理：客户明确确认地址版本2，保留禁止使用旧址的指令。。

### 第 10 步 · 客服 · 来信后 35 小时

依据客户明确确认保存本版收货地址。

这一轮应处理：地址确认绑定具体版本；发货前须核对最新版本。。

### 第 11 步 · 仓库 · 来信后 105 小时

仓库完成故障原件实物收货和验收，换出前置条件成立。

这一轮应处理：查询对应退货申请及当前仓库记录；客户寄回或承运商签收不代替验收。。

### 第 12 步 · Agent 应判断 · 来信后 106 小时

复核同SKU库存、原件验收及新地址确认后提交换货申请。

客服参考回复：

The return has passed inspection. I have submitted the same-model replacement using the new address you confirmed on Eichenbogen 72, Apartment 5.

这一轮应处理：使用版本2地址创建唯一同SKU换货内部待办；核对旧地址没有已出库包裹。。

### 第 13 步 · 客服 · 来信后 110 小时

人工确认原件验收通过、同一商品有库存、客户本版地址已确认后建立换出履约单。

这一轮应处理：仅在真实换货内部待办存在后关联人工履约记录。；保持与原问题唯一补偿关系；此时尚未发货。。

### 第 14 步 · 承运商 · 来信后 120 小时

承运商返回当前包裹物流状态。

这一轮应处理：根据关联包裹及承运商状态回复；客户确认收货前保持会话开放。。

### 第 15 步 · 客户 · 来信后 180 小时

The replacement reached our new apartment today. It is the correct natural wood lamp, everything was included, and it now works as expected. Nothing went to the old address. Thank you for catching the change before dispatch.

### 第 16 步 · 客服 · 来信后 182 小时

人工核对地址版本2明确确认、出库地址快照及客户新址收货反馈，确认原故障解决后结案。

这一轮应处理：由人工核对客户确认、业务回执及未结待办后标记已解决。。

## 处理结果

客户搬家使旧确认失效；新地址经明确核对后绑定换出记录，客户在新址收到正确商品，人工结案。

## 本例覆盖

客户搬家、旧地址确认失效、新地址二次明确确认、发货绑定新版本、同SKU换货
