# 显示签收但未收到查明误投后重新送达

编写的业务演练案例，不是真实客户历史；商品与金额沿用已有原型。

业务：物流查询；订单：999-7200012-8200000；商品：SP-XLLHBC02-PP；实付：USD 59.84。

资料依据与边界：依据对应SKU生产商品记录、适用SOP及项目售后政策；客户来信和业务记录为隔离资料创作，不编写厂家未确认的维修步骤。

## 首封来信

Hello, the BELEEV scooter on order 999-7200012-8200000 is marked delivered, but there is no parcel here. I checked both entrances, the side gate and with our immediate neighbours. The delivery photo is of a dark front door; ours is white. Could you investigate this please?
Thank you, Chloe

## 后续往来与处理

### 第 1 步 · Agent 应判断 · 来信后 0.2 小时

将客户未收到与物流显示已投递并存记录。

这一轮应处理：核对原订单包裹、运单及投递位置；复用客户已检查周边的事实，不让其重复同样检查；询问地址与投递照片差异所需信息，准备查件。

### 第 2 步 · 客户 · 来信后 4 小时

The order address is Chloe Bennett, 114 Cedar Road, Dayton, OH 45402, United States. That is correct. No one in our household accepted a parcel, and the photo does not show our house number. Please ask the carrier to check where it was left.

这一轮应处理：确认正确地址及查件选择，不虚构已查看照片的结果。

### 第 3 步 · 客服 · 来信后 4.1 小时

录入客户确认地址，供承运商核查投递点。

这一轮应处理：关联上一封客户确认，不扩展为补寄授权。

### 第 4 步 · Agent 应判断 · 来信后 4.3 小时

依据客户确认建立查件内部待办。

这一轮应处理：创建绑定原订单行和原包裹的查件待办；回复等待承运商核对，不承诺结果。

### 第 5 步 · 客服 · 来信后 22 小时

物流同事受理查件并向承运商提交正确门牌与照片差异描述。

这一轮应处理：必须匹配Agent实际查件申请。

### 第 6 步 · 承运商 · 来信后 50 小时

承运商核对司机路线与投递记录，确认包裹误投至相邻街道；司机已回收未拆封包裹，将按原运单重新送往正确地址。

这一轮应处理：将误投结论标记为承运商调查结果；向客户说明重新投递安排，不要求客户自行到陌生地址取件。

### 第 7 步 · 承运商 · 来信后 53 小时

承运商更新原包裹为重新运输中，原运单继续使用。

这一轮应处理：解释此前投递扫描已被误投调查纠正；不创建第二个订单或补发包裹。

### 第 8 步 · 承运商 · 来信后 77 小时

承运商完成正确地址的第二次投递，交给住户。

这一轮应处理：物流成功仍需客户确认，不自动结案。

### 第 9 步 · 客户 · 来信后 81 小时

The driver brought the scooter to our house this afternoon and explained the mix-up. We have the unopened box now and the contents are complete. You can stop the delivery investigation. Thank you for following it through.

这一轮应处理：记录客户确认收到且同意停止查件。

### 第 10 步 · 客服 · 来信后 82 小时

查件记录以误投找回并送达结案，客户已确认收货。

这一轮应处理：完结同一查件申请，无补发或赔付。

### 第 11 步 · 客服 · 来信后 84 小时

承运商确认误投、回收并重新送达，客户确认收到完整商品，客服结案。

这一轮应处理：客服核对客户确认及相关记录后人工标记已解决。

## 处理结果

承运商确认误投、回收并重新送达，客户确认收到完整商品，客服结案。

## 本例覆盖

显示签收未收到、核对原包裹、内部查件、承运商误投、重新送达
