# 原包裹长时间无更新经查件恢复运输并收货

编写的业务演练案例，不是真实客户历史；商品与金额沿用已有原型。

业务：物流查询；订单：999-7200003-8200000；商品：H-CTD16-US-BK；实付：USD 54.99。

资料依据与边界：依据对应SKU生产商品记录、适用SOP及项目售后政策；来信和业务进展为隔离资料创作，技术缺口不补写厂家参数。

## 首封来信

Hello, could you check the OUTON lamp on order 999-7200003-8200000? The parcel was last scanned at a sorting depot on 29 September and there has been no movement since. It has not reached us. We will be home for deliveries this week.
Thank you, Rachel

## 后续往来与处理

### 第 1 步 · Agent 应判断 · 来信后 0.2 小时

查询原包裹及最后有效扫描。

这一轮应处理：确认订单尚无客户收货事实；核对超过7天无更新，建立查件内部待办；回复已有状态及查件安排，不保证到货日。

### 第 2 步 · 客服 · 来信后 4 小时

物流同事已受理查件，向承运商查询停滞包裹的分拣情况。

这一轮应处理：仅有真实查件待办才登记外部受理；告知查件处理中，不推断已恢复运输。

### 第 3 步 · 承运商 · 来信后 29 小时

承运商回复：包裹在分拣中心滞留，已找到并交给下一班干线；尚未进入本地派送。

这一轮应处理：关联原查件记录；说明找到包裹与妥投不同，不给确定到货日。

### 第 4 步 · 承运商 · 来信后 31 小时

承运商新增离开分拣中心的扫描，原运单继续有效。

这一轮应处理：更新原包裹，不创建第二份补发。

### 第 5 步 · 客户 · 来信后 47 小时

I can see the new scan now. Thank you for finding out what happened. The delivery address on the order is correct; please keep me updated if the carrier needs anything from us.

这一轮应处理：保持查件和原包裹关联，继续等待派送。

### 第 6 步 · 承运商 · 来信后 72 小时

原包裹已有投递扫描，签收位置记为门口。

这一轮应处理：可以通知物流显示投递并询问是否收到；不能据此将会话标记已解决。

### 第 7 步 · 客户 · 来信后 77 小时

The lamp was delivered this afternoon. We brought the box inside, checked it and have everything we ordered. There is no delivery problem left to follow up. Thanks.

这一轮应处理：记录客户实际收货且物品齐全。

### 第 8 步 · 客服 · 来信后 78 小时

物流同事依据找回记录和客户收货确认完成查件。

这一轮应处理：完结同一查件申请，不新增赔付。

### 第 9 步 · 客服 · 来信后 80 小时

承运商找回滞留包裹，客户确认完整收到，查件完成后由客服结案。

这一轮应处理：客服核对客户确认及相关记录后人工标记已解决。

## 处理结果

承运商找回滞留包裹，客户确认完整收到，查件完成后由客服结案。

## 本例覆盖

原包裹、物流停滞、内部查件待办、承运商新扫描、客户收货确认
