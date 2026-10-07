# 补寄错版遥控器后人工核对并纠正送达

编写的业务演练案例，不是真实客户历史；商品与金额沿用已有原型。

业务：补寄配件；订单：999-7200021-8200000；商品：H-CTD16-US-BK；实付：USD 54.99。

资料依据与边界：依据OUTON-01 SOP、精确SKU适配清单和项目售后政策；客户及外部履约记录为隔离资料创作，不模拟Agent已发送的答复或已提交的申请。

## 首封来信

Hello, the remote was missing from the OUTON lamp on order 999-7200021-8200000. I have the black lamp with controls on the pole, and it works from those controls. Please could you send the remote that belongs with this version? I have already checked the packaging.
Thank you, Hannah

## 后续往来与处理

### 第 1 步 · Agent 应判断 · 来信后 0.2 小时

先核对原订单黑色灯具和对应遥控器。

这一轮应处理：使用精确SKU适配关系确认目标配件；核对库存，确认客户补一只遥控器的选择与完整地址。

### 第 2 步 · 客户 · 来信后 5 小时

Yes, please send one matching remote to Hannah Moore, 84 Pine Street, Albany, NY 12207, United States. I would like to keep the lamp as long as I can use the remote with it.

这一轮应处理：记录一只遥控器的选择和地址。

### 第 3 步 · 客服 · 来信后 5.1 小时

录入本次确认收件地址。

这一轮应处理：地址证据来自客户本封来信。

### 第 4 步 · Agent 应判断 · 来信后 5.3 小时

按正确适配配件建立补件内部待办。

这一轮应处理：选择SIM-OUTON-01-REMOTE-01与H-CTD16-US-BK精确适配；确认库存和地址后仅创建一份申请；不预知后续仓库错发。

### 第 5 步 · 客服 · 来信后 24 小时

履约同事依补件申请建单并安排仓库拣货。

这一轮应处理：关联Agent实际补件申请。

### 第 6 步 · 承运商 · 来信后 26 小时

第一件补件包裹面单已创建。

这一轮应处理：面单不等于揽收。

### 第 7 步 · 承运商 · 来信后 48 小时

第一件补件包裹已被承运商揽收。

这一轮应处理：跟进原申请对应包裹。

### 第 8 步 · 承运商 · 来信后 120 小时

第一件补件包裹显示投递。

这一轮应处理：等客户确认内容和适用情况。

### 第 9 步 · 客户 · 来信后 127 小时

The remote arrived, but it looks different from the one shown for my lamp. The sticker on its bag mentions the grey version rather than the black version I ordered, and it does not operate the lamp. I have not tried opening anything or changing the lamp. Could you check whether the wrong part was packed?

这一轮应处理：记录疑似错件，不让客户反复配对；核对申请目标配件与外部实际拣货。

### 第 10 步 · Agent 应判断 · 来信后 127.2 小时

补件疑似不适配，转人工核对。

这一轮应处理：对整个会话触发人工接管；保留原申请及包裹证据，避免再次盲目建相同申请；不提供未经核实的通用配对方法。

### 第 11 步 · 仓库 · 来信后 145 小时

仓库复核拣货记录：申请要求黑色款适配件SIM-OUTON-01-REMOTE-01，实际错取灰色款SIM-OUTON-01-REMOTE-02。差错由仓库确认；正确件可用8只。纠正发货关联原补件申请，不新增第二项赔付。

这一轮应处理：记录仓库确认的错件原因与正确配件；人工接管期间仅入库，不自动发送客户回复。

### 第 12 步 · 客服 · 来信后 150 小时

Hello Hannah, our warehouse has confirmed that the wrong version of remote was packed. We are sorry about that. We can correct the original replacement arrangement and send the version matched to your black lamp at no charge. You do not need to test the incorrect remote again. Please keep it aside; we are not asking you to post it back. May we use the same delivery address for the correct one?

这一轮应处理：人工已明确错件处理和纠正方案；人工回复后等待客户来信恢复，不直接安排Agent自动跟进。

### 第 13 步 · 客户 · 来信后 170 小时

Yes, please send the correct remote to the same address: Hannah Moore, 84 Pine Street, Albany, NY 12207, United States. I have put the incorrect one aside and will not use it. Thank you for checking what happened.

这一轮应处理：恢复Agent，记录客户接受纠正发货与地址再确认。

### 第 14 步 · 客服 · 来信后 170.1 小时

客户再次确认地址未变，保留版本1并刷新本次确认依据。

这一轮应处理：只据最新来信确认纠正发货地址。

### 第 15 步 · Agent 应判断 · 来信后 170.3 小时

将人工确认的纠正动作提交为原补件待办的跟进。

这一轮应处理：查询原申请及错发执行后复用原申请，登记需纠正的工作项；重新核对正确件精确适配、库存与地址；保持原错误执行可查，不以删除历史制造首次发货。

### 第 16 步 · 客服 · 来信后 192 小时

履约同事复核正确件后在原申请下建立纠正补发执行单，并标注替代先前错发。

这一轮应处理：使用不同执行号但关联同一个真实补件申请；原错件不增加退款金额或另立赔付。

### 第 17 步 · 承运商 · 来信后 194 小时

正确遥控器包裹已创建独立面单。

这一轮应处理：清楚区分首次错发与此次纠正包裹。

### 第 18 步 · 承运商 · 来信后 216 小时

承运商揽收纠正补件包裹。

这一轮应处理：回复此次正确补件的运输状态。

### 第 19 步 · 承运商 · 来信后 288 小时

纠正补件包裹显示投递完成。

这一轮应处理：等待客户确认遥控实际可用。

### 第 20 步 · 客户 · 来信后 296 小时

The second parcel has arrived. This remote works with the lamp: I can switch it on and change the brightness. I have kept the incorrect one separate as you asked. The problem is resolved now. Thanks for putting it right.

这一轮应处理：记录正确件收到并有效，错件处理已获客户确认。

### 第 21 步 · 客服 · 来信后 302 小时

仓库确认首次错取配件后，在原申请下补发正确件；客户确认遥控可用及错件保留安排，客服结案。

这一轮应处理：客服核对客户确认及相关记录后人工标记已解决。

## 处理结果

仓库确认首次错取配件后，在原申请下补发正确件；客户确认遥控可用及错件保留安排，客服结案。

## 本例覆盖

补件错发、禁止跨SKU猜兼容、人工核对、原申请纠正执行、正确配件到达解决
