# 换货缺货且拒绝其他颜色后等待同款补库存

编写的业务演练案例，不是真实客户历史；商品与金额沿用已有原型。

业务：换货；订单：999-7200018-8200000；商品：SP-SLHBC12-PU；实付：USD 69.99。

资料依据与边界：同SKU库存变化为外部仓库记录；已有故障服务记录避免编造危险维修步骤。质量退回附件仅供隔离审阅，不能在真实物流使用。 客户、地址、单号、仓库和支付记录均为内部演练编写，不是真实客户资料或实际履约；参考回复只供评测。

## 首封来信

Hello, this is about the purple BELEEV A9 scooter on order 999-7200018-8200000. Your colleague confirmed the faulty folding catch and told us to stop using it. I want the same purple model as a replacement. Could you check that exact one is available before we send this one back?

## 后续往来与处理

### 第 1 步 · Agent 应判断 · 来信后 1 小时

核对同SKU缺货，说明可等待并征询客户选择。

客服参考回复：

The same purple A9 is currently out of stock. I do not have a confirmed replenishment date. You can wait for that exact model and colour, or we can discuss returning it for a refund. I will not change the colour without your agreement.

这一轮应处理：查询相同紫色A9库存为0，不建立可执行换出申请；说明补库时间未知。；提出等待同款或讨论退回退款，由客户选择，不能替换颜色。。

### 第 2 步 · 客户 · 来信后 4 小时

Please do not send black, pink or any other colour. We would like to wait for the same purple A9 for now. I do not want a refund at this stage. Please let me know when that exact model is back in stock so we can arrange the return.

这一轮应处理：记录明确拒绝其他颜色、等待同款及暂不退款；保持问题开放。。

### 第 3 步 · 仓库 · 来信后 48 小时

仓库确认紫色A9同SKU新到货2件，未占用。

这一轮应处理：查询最新同SKU可用库存，并向客户确认仍按同款退回换货。。

### 第 4 步 · Agent 应判断 · 来信后 49 小时

补库后再确认换货选择和完整收货地址。

客服参考回复：

The same purple A9 is now available. If you still want to proceed, please confirm that you will return the faulty scooter first and provide the full address for the replacement.

这一轮应处理：告知同款可用，请客户确认仍同意先退回验收再换出及完整收货地址。。

### 第 5 步 · 客户 · 来信后 52 小时

Yes, please continue with one purple A9, and I agree to return the faulty one first. The replacement address is Alex Morgan, 936 Alder Quay, Apartment 6, Bellford, OH 43000, United States. I have checked it and confirm that this is the correct address.

这一轮应处理：明确同SKU选择、先退回及完整地址。。

### 第 6 步 · 客服 · 来信后 53 小时

依据客户明确确认保存本版收货地址。

这一轮应处理：地址确认绑定具体版本；发货前须核对最新版本。。

### 第 7 步 · Agent 应判断 · 来信后 54 小时

创建故障退货待办，暂不执行换出。

客服参考回复：

I have requested the return arrangements for the faulty scooter. Please keep it out of use while we complete the exchange.

这一轮应处理：创建一件故障原车的退货申请；同款库存应在实际换出前再次校验。。

### 第 8 步 · 客服 · 来信后 58 小时

客服提供RT-10418完整寄回资料，说明商家承担邮资及包装、收件、保留凭据事项。

这一轮应处理：查询对应退货申请及当前仓库记录；客户寄回或承运商签收不代替验收。；授权资料到达后，向客户交代本记录的退货编号、收件人及完整地址、邮资承担、包装和寄件凭据保留要求；引用实际存在的附件，不编造链接。。

### 第 9 步 · 客户 · 来信后 76 小时

I have sent the whole scooter back using the return document for RT-10418. I kept the receipt. Please remember that I am waiting for the purple A9 only, at the address I confirmed.

这一轮应处理：客户寄回陈述不替代仓库收货；再次维持原SKU和地址。。

### 第 10 步 · 仓库 · 来信后 148 小时

仓库对同一退件完成实物收货与开箱验收，记录两项事实均成立。

这一轮应处理：查询对应退货申请及当前仓库记录；客户寄回或承运商签收不代替验收。。

### 第 11 步 · Agent 应判断 · 来信后 149 小时

复查库存后创建同SKU换货内部待办。

客服参考回复：

The returned scooter has passed inspection, and the same purple A9 is still available. I have submitted the replacement request to the address you confirmed.

这一轮应处理：核对原车验收通过、紫色A9剩余可用库存与地址1确认，创建唯一同SKU换货申请。。

### 第 12 步 · 客服 · 来信后 152 小时

人工确认原件验收通过、同一商品有库存、客户本版地址已确认后建立换出履约单。

这一轮应处理：仅在真实换货内部待办存在后关联人工履约记录。；保持与原问题唯一补偿关系；此时尚未发货。。

### 第 13 步 · 承运商 · 来信后 162 小时

承运商返回当前包裹物流状态。

这一轮应处理：根据关联包裹及承运商状态回复；客户确认收货前保持会话开放。。

### 第 14 步 · 承运商 · 来信后 220 小时

承运商返回当前包裹物流状态。

这一轮应处理：根据关联包裹及承运商状态回复；客户确认收货前保持会话开放。。

### 第 15 步 · 客户 · 来信后 224 小时

The purple A9 arrived today. It is the same model and colour we asked for, and the folding catch no longer has the problem we reported. Everything was in the box. We are happy to keep this one, thank you.

### 第 16 步 · 客服 · 来信后 226 小时

人工核对客户拒绝其他颜色的选择一直被尊重、原件验收通过且同SKU换出，客户确认问题解决后结案。

这一轮应处理：由人工核对客户确认、业务回执及未结待办后标记已解决。。

## 处理结果

同款缺货期间客户选择等待并拒绝其他颜色；补库后完成原件退回验收、同SKU换出及人工结案。

## 本例覆盖

同SKU缺货、拒绝其他颜色、等待补库存、重新核对库存、先退回验收
