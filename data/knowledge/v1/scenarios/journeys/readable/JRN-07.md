# 缺少遥控器核对后补寄并确认有效

编写的业务演练案例，不是真实客户历史；商品与金额沿用已有原型。

业务：补寄配件；订单：999-7200007-8200000；商品：H-CTD16-US-BK；实付：USD 54.99。

资料依据与边界：依据对应SKU生产商品记录、适用SOP及项目售后政策；来信和业务进展为隔离资料创作，技术缺口不补写厂家参数。

## 首封来信

Hello, my OUTON lamp from order 999-7200007-8200000 arrived without a remote. I checked the small cardboard sleeves and all the packing material before throwing anything away. The lamp itself works from the buttons. Could you send the correct remote?
Best, Laura

## 后续往来与处理

### 第 1 步 · Agent 应判断 · 来信后 0.2 小时

核对订单、包装缺遥控的描述与适配清单。

这一轮应处理：确认需补一只精确适配遥控器及可用库存；复用订单号，确认客户愿意补件并确认完整地址；在条件齐备前不创建履约成功状态。

### 第 2 步 · 客户 · 来信后 6 小时

Yes, please send one replacement remote for this lamp. The correct address is Laura Ellis, 418 Maple Avenue, Apt 2B, Columbus, OH 43215, United States. This is where the lamp was delivered.

这一轮应处理：依据此来信记录补一只遥控器的选择和地址。

### 第 3 步 · 客服 · 来信后 6.1 小时

客服录入客户本次确认的完整收件信息，版本1。

这一轮应处理：地址确认须关联上一封客户来信，不沿用种子默认确认。

### 第 4 步 · Agent 应判断 · 来信后 6.3 小时

补件前提齐备，等待Agent实际创建内部申请。

这一轮应处理：查询精确SKU与遥控器适配、库存及地址版本1；为同一订单行和问题创建一份补件内部待办；回复已提交安排，等待业务同事执行。

### 第 5 步 · 客服 · 来信后 24 小时

负责同事在履约系统建立一只遥控器的补发单，仓库等待打包。

这一轮应处理：关联Agent实际补件待办；普通履约操作不触发整段会话人工接管。

### 第 6 步 · 承运商 · 来信后 25 小时

已创建补件面单，尚无承运商揽收扫描。

这一轮应处理：区分面单创建与已经发货。

### 第 7 步 · 客户 · 来信后 33 小时

Thanks. The tracking page only says a label has been created. Has the remote actually left your warehouse yet?

这一轮应处理：查询本补件包裹，不引用原灯具签收状态。

### 第 8 步 · Agent 应判断 · 来信后 33.2 小时

按现有回执回答发货进度。

这一轮应处理：说明目前仅创建面单，尚无揽收记录；继续跟进原申请，不重复建补发单。

### 第 9 步 · 承运商 · 来信后 48 小时

承运商完成补件揽收，首个运输扫描已回传。

这一轮应处理：可以说明补件已交承运商并提供此包裹运单。

### 第 10 步 · 承运商 · 来信后 120 小时

补件包裹显示已投递。

这一轮应处理：询问客户是否收到及遥控是否可用，保持会话开放。

### 第 11 步 · 客户 · 来信后 126 小时

The remote arrived today. I have tried switching the lamp on and adjusting the brightness, and both work. Thank you for sorting out the missing item.

这一轮应处理：记录配件收到且主要控制功能有效。

### 第 12 步 · 客服 · 来信后 132 小时

补件经历建单、面单、揽收与投递，客户确认遥控可用，客服核对后结案。

这一轮应处理：客服核对客户确认及相关记录后人工标记已解决。

## 处理结果

补件经历建单、面单、揽收与投递，客户确认遥控可用，客服核对后结案。

## 本例覆盖

缺件识别、客户明确选择、地址确认、内部申请与发货区分、补件到货有效
