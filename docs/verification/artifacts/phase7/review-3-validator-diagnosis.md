# 第三轮只读核验机制诊断

日期：2026-10-08；不改产品、不付费、不执行Stage 2。H12/H13未关闭。当前源码依据：`agent/outcome_validation.py:9`、`agent/graph.py:176/190/200/219/225`、`application/draft_validation.py:11/19/35`（均位于backend/src/globalmail_agent）。本诊断是候选机制评估，不是新质量PASS。

## 已证事实

- 202431原P7-06实际查单/物流后，唯一出站遗漏未来条件退款、添加无据ceiling light；旧理解只有troubleshooting/null/none且无修订。完整语义review误放。
- 204212在全文DATA后增原邮件完整性/译名规则，actualrequest/SDK/21可信SHA全部正确，仍误放；positive未发。
- 205412仅更换同四字段schema顺序和description，actualSDK、required及actual响应都reason-first，34可信SHA和完整messages正确，仍误放。输出理由泛化、把不立即执行等同保留未来条件，且误称citation_ids来自工具。positive未发。
- 因而“总判决先输出true导致事后合理化”没有成为已证根因；仅变顺序没有修好此反例。现有引用ID/全文覆盖/hash证明送审及提交对象一致，不能证明自然语言蕴含。

## 最小可审查结构

1. 服务端给已有draft.claims分配索引；新review要求每索引恰一项，不允许缺项、重复或越界。正文仍以原normalized Draft为准，不再次生成/补删正文。程序继续既有覆盖检查，不信提案kind将一句话免审。短字段引用索引，避免复制最多8000字body使2k输出耗尽。
2. 每项分别给出语义判定与来源定位。quote必须在服务提供的当前原文中精确存在；message/human_note身份、scoped成功当前run business command、当前依赖reference各自限制角色/范围。最好定位具体字符串字段或完整句，而非任意JSON子串。不得在全局库/客户资料中按模型ID搜索补证；metadata ID、旧failed receipt、source ID本身不作事实。
3. 原邮件检查独立从原trigger/当前可见客户正文开始，不能从initial/current Understanding生成期望请求清单，否则H12被固化。可程序赋完整文本单位ID，要求逐单位检查，保留原文；单位只表示文字范围，不能冒充程序已理解“业务诉求”。条件、未来选择和拒当前执行要独立映射到回复相关claim；历史、撤回及纯背景可以有明确处置依据，不能强迫重复全部历史请求。
4. 最终由程序校验数组完整性、quote原文/所属范围、判定字段和语言后AND所有项；任一不支持/缺失/无效就拒绝，模型的顶层supported不能覆盖负项。继续原预算内一次repair、原最后额度门、当前guard/业务摘要/RAG撤销/hash及Commit同事务复验。新审项不可作为交易权限或自动清风险。

这比再加一段自由reason更可追溯。但边界必须写清：真正quote“朝天灯”仍可能被模型误认能支持ceiling light；把整段原信标成背景或把无关draft句映射为“已回答”仍可能形式合法。精确字符覆盖只证明每段文字被列入检查，不能证明请求语义分解完整、条件被准确承接或译名正确。不能把模型自报的逐项kind/支持标志升级成形式证明。新协议只有在完整旧负例、明确正对照、真实新06及其余业务逐案验证后，才能按已测范围关闭当前HIGH。

## 避免伪前提和过约束

- 期望claim索引来自服务端真实草稿；期望文本单位来自原邮件，不由待审模型自由缩减。空/缺/重复数组默认拒绝，不回退旧总supported。quoted来源不得混用收款/执行事实与customer report。
- 不要求模型数Unicode偏移，也不以关键词判断refund或英语问句；用服务端ID+精确quote校验。相同quote多次出现时用确定的消息/字段定位，不能用find首次命中伪造范围。
- 不要求事实之外的纯礼貌/未知信息补问拥有虚构证据，也不能让提案模型把事实标clarification免查。关于其是否属于事实、是否问句的判断仍由独立语义审项负责，真实恶意clarification回归继续。
- 单条claim可含多个事实，不能以有一个真quote就批准全部句子。证据需覆盖该项涉及的每一事实；有限工程测试应包含真quote但错误译名/时间态、半句支持、多来源、错消息/旧版本/外客户及quoted指令注入。
- 不机械要求回复逐字抄原客户文本；翻译、简短确认、等待/人审及明确已撤回请求有合法表达。不得把“不立即退款”测试偷换成“未来偏好消失也通过”。
- schema和审项会增加输入及输出成本。当前最多30claims/12intents，2k输出若每项复述正文与长quote可能必超。要按索引引用、小而足够的原文证据，保原边界；确实不能容纳须明确失败，不隐删原邮件/SOP、加第7调用或自动伪造HITL。原无订单补问、条件问句、人工plan及无SOP也需正对照，不能仅测旧负例拒绝。

## parsed observations比较

当前`graph.observations`返回tool message，其中content已是canonical JSON字符串；构造validation user DATA再canonical一次，于是观察作为转义字符串嵌在外层JSON中。它没有丢掉工具字段/完整SOP，但可读性较差。可仅在validation DATA中把该content解析成JSON对象，保持role/tool_call_id/command_source_id、完整data/evidence/observed_at/resource_versions及知识正文全部值。不能把材料升system或改成真实ChatAPI tool-role消息。

本审对205035negative的两条真实观察做了0HTTP独立转换：每条parsed值canonical roundtrip精确等原content字符串，其他全部DATA/schema/system/tools/timeout不变；输入代理14128→13548，减少580，见`review-3-observation-shape-diagnosis.json`。这里只证明无损形状变化和代理大小，不是实际token节省，更不是三次漏判根因或改后语义会正确的证据。

若实施，需严格解析程序生成JSON，畸形/非对象明确失败，不能当“无资料”；不改变原持久receipt、引用依赖/撤销/hash门。对有完整SOP、嵌入引号/多语言/转义换行、业务值类型和scope metadata做逐字段往返，并检查输入界。格式变化是较小独立假设；与新逐项schema同时改变时不能将改善单归因于其中一个。当前不建议据此直接重新付同一业务配置或宣布已修复；先冻结具体源及0HTTP全字段对照，再按主Agent授权进行相应验证。

结论：结构化逐项审计可加强可追溯拒绝门，parsed对象可无损减轻嵌套转义；二者都没有消除语义判断的不确定性。当前Stage 1仍FAIL，Stage 2未执行。
