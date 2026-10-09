# 第三轮逐项核验实际失效机制诊断

2026-10-08；只读审查、0新HTTP、0业务写入，Stage 2未执行。当前源与212036预案、212722实际SDK及最终272项全量SHA一致。范围为已授权本期复用审查，不是fresh实例。

## 确定结论

212722不是当前Graph放行反例。实际model的supported=true及三个逐claim true仍是语义误判，但 `agent/review_audit.py:59/84/86` 拒绝三处引用绑定，`agent/graph.py:202/204` 的最终AND为false，不能保存validated_hash。独立[实际审计](review-3-item-audit-negative-actual.json)核对完整request=212036 negative、51可信raw SHA、真实SDK六字段顺序、当前全文首/尾及source SHA；1HTTP/4366tokens/17702活动ms/0业务，positive及fresh06均未发。

实际source_checks的三个quote均不是当前原canonical receipt连续片段：claim0用省略号缩造订单JSON；claim1物流JSON删除同对象中间字段再拼成新的子对象；claim1另引未声明的order source，并自行重构只有product_name/sku的lines对象。当前精确绑定确实拒绝这些内容。这是新增工程门有效的具体证据，不能写成“又一次实际出站”，也不能写成“语义核验已正确识别坏稿”。

实际语义错误也已经具体化：原单位2的未来退款/not-now选择被映到无关delivery-details问题并标addressed；物流command没有商品类型，order原标签也不支持ceiling subtype，模型却把ceiling light称为合法翻译；含system状态及customer未收到两项事实的段落被称为没有事实的clarification。新数组把错误展示出来，没有让模型自动理解正确。原H12/H13真实业务FAIL尚未关闭。

## 锚定与转义的证据边界

`graph.py:191/193` 目前将完整原context、提案Understanding、draft以及tool message的content字符串放在同一user DATA。原Understanding已漏future条件且类别错；它作为不可信提案保留在验证输入中，确有影响判读的可能。但这次模型reason明确提到future refund，并非完全没有看到原诉求；它仍把无关句认成答复。现有单次材料不能证明误判由Understanding锚定造成，也不能证明删除该字段就能修好。

本次新增的伪重构JSON是引用协议不服从的直接证据。观察content已是JSON字符串，外层DATA再次序列化，业务对象因此多一层转义；它增加读/抄引用的负担是合理假设。完整字段仍在，没有字节丢失。模型也可能在更易读输入上继续主动摘要JSON，所以不能从当前quote错误直接推断双重转义是语义根因。

独立0HTTP比较只把两完整观察content字符串变成其parsed对象，保留role/tool_call_id和所有业务、source、版本、时间、limitation、数据值类型，canonical roundtrip逐字回到原字符串。其余context、错误Understanding、draft、原邮件units、首/尾、schema、timeout全部不变。当前negative代理15364→14784，positive15742→15162；各减少580代理字符。见[无损比较与机械反例](review-3-item-audit-mechanism-diagnosis.json)。这不是已发出的请求、实际token节省、当前产品变更或新质量PASS。

若主Agent选择表示层方案，最小可审查边界是仅validation DATA的观察结构化，决策transcript、原持久工具receipt、调用计账、引用依赖/撤销、来源早验、hash和Commit门全部保留。必须让audit_sources读取该表示后返回与原完整canonical来源相同的值；畸形/非对象应明确失败，不能当无资料。须以完整SOP及其引号/换行/多语言、全部receipt metadata/value types做往返并验证16k输入；不得只取orders/shipments摘录或把资料升system。当前代码 `review_audit.py:45` 仍只json.loads字符串，候选parsed对象不是现有产品可直接接受的请求。

仅移动/重命名提案Understanding的呈现可能降低权威错觉，但当前已有原文与“不得用提案代替客户”的规则，且没有独立因果实验。不要同时改两种表示再把结果归因给其中之一。删除原context、已有事实、工具资料或所有历史都不能用“减锚定”来解释成无损变更。

## 格式变好不能独立关闭HIGH

本审做了明确的非模型机械反例：在内存复制本次真实review，仅把两个quote换成当前来源完整原文、删除claim1不允许的第二来源；正文、错误unit映射、reason、kind、所有true和其他字段保持不变。当前audit_accepts便成为true。此修改只用于0HTTP诊断，原raw文件未变，不冒充真实模型结果。

这证明当前来源绑定的作用范围：如果模型在新表示上只学会抄对quote，原未来条件漏判和错误译名仍可能被放行。不能以parsed后引用正确、总true或阳性稿通过替代旧负例的实质误译/缺条件拒绝。原负控制同时有格式和语义问题，未来新对照若要隔离语义，应另冻明确的来源注解合规、正文仍坏的合成negative；恰列改动，保留原标签及全部旧失败，不能偷偷重写原202431/212036。源ID可定位事实，不能替商品类型和时态作蕴含证明。

当前不建议用关键词黑名单、自动把所有条件标context、删除完整工具资料、宽松接受伪quote或以人工填新数组去追求旧样本PASS。表示层可以成为一项受控假设，必须先完整0HTTP结构/源码/预算审计再由主Agent决定是否授权任何actual调用；本诊断没有放行付费。真实fresh06保留条件意图、实质正反核验及07–09全部原目标仍待。

## 当前修复反馈的具体缺口

`graph.py:204/209/218` 将audit_accepts=false与模型语义false合并成reply_grounding_invalid，却只把review.reason送给下一次草稿修复。对本次真实response，该reason声称“所有请求均已处理、各claim均有依据”，因此模型收到“草稿被拒”及相反的肯定理由，没有三个确定性的引用失败定位。当前协议仍安全停止，但这会浪费仅有的一次repair，且改写本来可能合格的草稿不一定能修复核验器引用格式。

可审查的工程改进是让确定性绑定函数返回有类型的失败位置/原因，并在既有repair反馈中优先报告该证据；例如unit缺项、claim来源不允许、quote非逐字。这不是再添同一语义警句，也不应靠模型reason覆盖实际程序拒绝。若进一步区分“核验格式需重做”和“草稿语义需修”，要明确原一次repair、原6请求及最后验证余量，不能新增第7请求或自动授予HITL。该反馈缺口目前只读定位，主Agent未要求本审修代码；不能据此称H12/H13已经修复。

## 验证状态

独立读取root最终backend原始末尾并逐一核对snapshot：272 tests/530.155s/OK/0skip，before=after=当前src/prompts/tests/migrations/lock。它证明当前工程测试完成，不改变本次actual语义负控制FAIL或未完成业务目标。本审17项修后PG及15项eval原始输出保留；工程Scripted helper不能补真实响应的新审计字段，更不能作语义PASS。

Stage 1仍未通过，Stage 2未执行。原202431、204212、205412、211045不合法阳性前提及212722全部证据分别保留；正式服务和用户库未操作。
