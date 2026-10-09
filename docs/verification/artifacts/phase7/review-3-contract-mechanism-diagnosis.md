# 230652 后独立只读机制诊断

本次仍为 Stage 1 FAIL，H12/H13 未关闭，Stage 2 未开始。未改产品、未调用模型、未改原目标。依据为[完整实际检查](review-3-contract-negative-actual.json)与当前 `globalmail-agent/backend/src/globalmail_agent/agent/review_audit.py:58`、`graph.py:194`。

## 已有证据能说明什么

- 实际 SDK 使用当前 source-first 顺序及三局部描述、完整原来信、三原句单位、两完整业务回执、旧错误 Understanding；当前参数/输入预算/供应商 usage 可靠。不是没有传入条件或模型读到另一版 schema。
- 模型 unit2 的 quote 是草稿真实片段，却只是物流补问；与未来条件退款及现在不退款没有语义对应。精确字符绑定不能证明请求被承接。总理由这次也称未来请求已满足，H12 没有匹配。
- claim1=false 的理由认可 ceiling 翻译，只因没重复来源全部四按键/地区/颜色而拒绝。这是另一错误前提；不要求在普通物流回复复述全部商品属性。H13 的类型来源问题没有被正确解释。
- claim2 的事实内容被当作 clarification 空证据接受，显示模型仍可能凭整体用途豁免段内事实。
- 三 source quote 拼出带空格的多个 JSON 字段，均不是 canonical 来源的连续片段；另有越 claim 声明来源。这里确有表示/引用协议缺陷。request1 把相邻段落用空格拼接，仍有独立正文引用问题。
- 程序正确拒绝错误绑定，首码 `request_unit_1_reply_quote_not_in_draft`。0业务/总 false/runner 全检查 true 均不能证明两个业务缺陷已修复。

## 不能由现有证据推出什么

不能把 source-first 输出理解为内部检查顺序已正确，也不能把总 false 当作拒绝理由正确。512 推理子限额、顺序与措辞的变化均未使冻结反例完整匹配，不建议继续同类型微调后随机重付。

错误 Understanding 有潜在锚定风险，但本次原来信/trigger_units 已在完整输入内；没有隔离实验能证明它造成误判。不能据此删除完整材料或假定重命名即可修好。

无损 parsed observations 有直接的引用格式动机：模型反复重构 escaped JSON。先前 0HTTP 比较已经证明两个回执可完整 roundtrip 且省580代理字符。然而 225432 的六条 source quote 曾全部精确，条件映射与类型仍错；因此表示修复不会自动解决语义，最多是值得单独验证的另一机制假设。

## 下一项最小可审任务

如主Agent继续该机制实验，先只做 observations 表示的一项无损变换预案：保留 role/tool_call_id 和完整解析对象的全部字段、Unicode、数值、null、所有限制/来源标志；状态、当前来源ID、business digest 与 canonical 审计来源精确等原回执。原来信、错 Understanding、草稿、schema、首尾指令、模式和全部预算保持，不同时改提示、标签或补正确译名/条件答案。

0HTTP 必须证明每个回执 parse→canonical 等值、其他 DATA 逐字段和原正文单位拼合原样、全部来源索引仍来自同一当前 scoped 数据；实际 request/SDK及预算分别冻结。模型引用可以使用真实字符串值的短连续摘录，不能为它自动修错 quote 或借用别的 claim 来源。

若后续实际负控制获授权，门仍要求模型具体判原未来条件遗漏及无据类型，各项与理由一致。未声明来源与混合事实空证据亦不能掩盖。合法泛称与条件是否问句仍允许；不强求所有来源属性都进入成稿。首 FAIL 停，不能用程序绑定拒绝或新理由的额外错误抵偿原目标。

若表示单项仍失败，应保留未达标范围并考虑缩小已验证能力或另行调整架构/资源契约；这属于产品决策，不能由QA把条件案例改成仅“不执行退款”或把业务目标换成HITL来完成Phase7。
