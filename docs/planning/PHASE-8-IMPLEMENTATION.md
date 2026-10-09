# Phase 8 图片输入实施步骤

日期：2026-10-09。用户已明确要求先继续功能开发、完整链路后统一优化模型细节；Phase7/Phase1模型质量原FAIL保留，不能阻塞本期工程开工，也不能记成通过。输入消费Product-Spec REQ-014/AC065–082、主架构4.4和DEV-PLAN Phase8，沿用既有工作台、对象存储与提交锁。

| 步骤 | 目标 | 完成标准 |
|---|---|---|
| 1 | 建图片暂存/附件/修订/视觉分析表及真实解码 | JPEG/PNG/静态WebP；10MiB/20百万像素/每封4图20MiB；坏图/动态图/伪类型/超限明确拒绝，原图和缩略图是受控对象，不接受客户端路径或外链 |
| 2 | 接图片到新建/追加来信并提供预览 | staged ID原子绑定、正文可空但须有ready图、幂等与跨客户拒绝、附件/CID映射不可变；暂存取消和24小时过期仅清无消息引用对象；HITL只收图不运行 |
| 3 | 联合正文/图片理解并持久化证据 | 同一理解请求，方向校正/受限全图视图、逐图coverage与提取/观察/推测分层；图像只在SDK适配器组装，不进Graph/checkpoint/trace；文本+视觉保守预留、实际usage含推理一次，6视图/6请求/12工具/120秒与既定stage上限保持 |
| 4 | 更正、撤销与晚到门 | 人工处理权/输入版本/证据修订冲突校验，更正不自动恢复；撤销增epoch/input_revision、关闭旧checkpoint，晚到结果不落有效事实/不发信；风险产出走现有共事务HITL |
| 5 | 工作台图片上传/逐图状态/证据抽屉 | 继承MessageComposer、MessageTimeline及ReferenceDrawer/Element Plus先例；新建和追加均可仅图来信；失败保留草稿、上传不触发模型、可预览/更正/移除，当前接口为真实数据 |
| 6 | 验证工程闭环并交给后续开发 | 真实PG→HTTP→消息/证据、SDK捕获、停止/新输入/更正竞争；后端编译、前端typecheck/单测/构建与真实隔离页面可用；记录当期工程审查。图片理解准确率/禁止动作/Phase7语义与未执行业务在完整链路后统一回归，不追加反复付费微调 |

完成记录：以上六步工程实现和四步验证通过；最终冻结后端319项、前端55项、vue-tsc/Vite及compileall通过，实际页面含仅图来信、更正、预览失败回退和撤销HTTP410。第七轮fresh独立Stage1本期工程PASS/Stage2 PASS，无待修复HIGH/MEDIUM工程阻塞。证据见[验证记录](../verification/PHASE-8-VALIDATION.md)及[最终独审](../verification/PHASE-8-REVIEW-7.md)。AC082和真实模型质量延期，下一期Phase9；正式0005库、设置及160原件未改变，自有测试数据已清理。

主Agent拥有集成、源文档、消息/Context/Graph/预算/提交门及最终验证；可隔离的附件存储/API和前端组件允许fresh worker，不能复用已结束的Phase7编码实例。worker不再派发、不提交；source目录单文件不超过300行、TS strict无any，所有运行测试用隔离schema/对象目录。

本期不扩大模型或外部交易权限、不引入图片OCR服务、不修改冻结视觉材料。售后写由Phase9接入，彻底删除仍由Phase12端到端补齐；本期撤销立即失效，UI不显示未实现的完整删除成功。

全量回归补充：没有附件元数据时，保存元数据直接返回，不查询图片表。旧数据库升级测试用0003时期的消息/事件/任务数据结构建种子，升级后再交给当前服务验证；不能用新服务在旧结构上运行，也不能为了测试放宽撤销读取门。正式应用继续由启动门要求当前head。

收尾审查补充：联合分析依赖本次全部图片，撤销其中一图会让共同派生分析失效；其余未撤销原图仍可预览，但旧共享证据必须明确返回410 image_content_revoked。JSON证据读取直接走受控字节门，不把撤销占位文本当JSON解析后返回500。

同类读取统一：corrections携带旧证据、Context工具缓存、工具幂等回执、Understanding修订、草稿来源核对和runner风险恢复等机器JSON读取均用read_bytes。只在展示正文/人工备注/事实时使用read_body的撤销占位文本；不放宽失效读取，不把占位文本作为可解析数据。

风险恢复补充：同类风险只能被当前依据仍有效的active记录去重。旧图已撤销的风险不作为当前依据，也不能挡住新图的有效同类风险落库；新风险必须持久化，人工普通回复keep_active后，后续新来信仍先命中风险门，0模型/0自动出站。验证采用旧图危险→撤销→人工回复→新图同类危险→人工回复→普通来信完整真实时序。

时间线补充：CMP-002的已提交图片必须直接显示缩略图，沿用上传区的小图卡和Element Plus Image，文件名按钮继续打开原图/证据抽屉。缩略图仅使用带conversation_id的既有受控preview接口及no-store响应，不访问图片外链或服务器路径；撤销/取消/缺字节/不支持状态不加载缩略图，加载失败显示实际不可预览但保留详情与撤销入口。验证包括真实图像加载、失败回退、撤销后移除DOM和窄面板不溢出，不修改模型链路。

## 接口与集成约定

审查补充：消息与历史导入可随正文保存`attachment_metadata`（filename、mime_type、cid），无字节明确missing或unsupported；它不能充当仅图来信。受控案例包可以用content_id关联包内`attachments/manifest.json`的相对图片路径和SHA256，路径必须落在包内attachments目录，读取大小及摘要核验后真实解码，同事务绑定，后续历史截点仍单独授权。HTTP不接收文件路径/URL。当前epoch人工修订按观察、推测或具体字段优先：模型原始分析保留审计，手工同列不再被自动有效证据覆盖，顶层候选/事实和查单门同步使用人工来源。

Phase7已提交09a818f；本期从该工程基线继续。`POST /api/v1/attachments/uploads`接受原始图片字节，query为filename及conversation_id或sender_email，Idempotency-Key控制重试。新客户上传可建立无消息的暂存会话以分配真实身份/分支；该会话在首封来信前不出现在列表、不入队、不改变输入版本。图片清单只携带attachment_id与可选cid，接受消息时整组绑定；上传失败、发送失败保留草稿。

`GET /attachments/{id}/preview?conversation_id=...&thumbnail=true`返回受控图片；`POST /attachments/{id}/cancel`仅取消未提交暂存。`GET /conversations/{id}/attachments`返回可见前缀中的逐图状态。`GET /conversations/{id}/visual-evidence?attachment_id=...`返回当前有效证据及人工修订；`POST /attachments/{id}/corrections`要求expected_version/expected_input_revision/evidence_revision与kind/value/reason，`POST /attachments/{id}/revoke`要求同版本栅栏。撤销即禁止读取，完整副本删除仍留Phase12。

全图视图使用Pillow真实解码/EXIF方向校正/受限缩放，格式白名单及像素限制先于解码。Qwen3.7官方32×32视觉patch计费采用缩放后保守上界，另保留额外图像开销；预留总输入不得超过16k，每cycle累计图像视图不超过6。SDK适配器临时构造image_url的data字节，Graph只保留受控引用；每次网络重试重新授权、重新计数。模型输出的提取/观察/推测独立记录，原图证据不能充当账本事实。联合理解默认不跨run复用，人工修订作为后续受控上下文，模型不覆盖人工内容。
