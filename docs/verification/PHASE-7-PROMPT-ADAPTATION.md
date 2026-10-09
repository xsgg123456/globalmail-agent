# Phase 7 Qwen提示与采样适配记录

最新机制结论：单独parse观察的231655 prototype也FAIL，完整还原原DATA与source正文并未修正未来退款对应；未接Graph、positive零HTTP，不继续这条配置。当前产品text/4完整276项548.623秒工程回归通过，不能证明语义达标。所有已测thinking响应用满512子限额，仅支持“资源限制值得单独验证”的新假设，不证明它是根因。

具体容量提案已零HTTP核对完整SDK：仅validation thinking2048/max_completion3990（总预算4000含官方10-token容差）、timeout=min(60, cycle剩余活动秒)，原材料/schema/head/tail不变；其他节点仍非思考/2k/30秒，cycle6/12/120秒/16k/80k保留。必须stage分别预留/结算，推理和答案计完整completion一次；当前产品仍512/1990/30秒，提案需用户授权修改ASM-006才落地/付费。[预案](artifacts/phase7/validator-capacity-proposal-zero-http.json)仅结构与预算证据，不是效果保证。

最新授权与候选：用户要求按方案继续并尽快结束Phase7，已批准仅OutcomeReview启用有界思考。理解/决策仍非思考；512推理包含在1990总completion及原输出/累计预算内。224147仅改思考模式的唯一负控制仍漏商品译名，保留FAIL。text/3改先来源后诉求，225432总理由同时提两缺陷，但退款审项仍addressed且三条reply_quote非正文连续摘录、claim1越来源、混合事实claim2empty/true；主Agent与独审阅读全文均FAIL，positive零HTTP。不能以总false或出处拒发代替正确理解；缺四按键属性并非此案额外必须回复项。

text/4只将schema输出顺序对齐为source_checks→request_checks，并把三个局部字段含义直接写入schema（全部声明来源事实、全请求/条件匹配、连续正文引用且遗漏/context空引用）。原字段类型/必填/上下限、硬门、全部消息/DATA及head/tail不改。225934零HTTP预案完整Mock SDK只变schema顺序及三描述，64可信SHA/输入15615、15993（原16k内）；根41项72.979秒/0fail/error/skip/source稳定及compileall exit0。该候选仍待独立工程门及唯一负控制，不宣称输出顺序是思考顺序或已证根因；若失败停止本配置并重审。

日期：2026-10-08；状态：诊断/验证中。流程参考prompt-model-adaptation，业务四例来自付费前冻结的agent-eval/cases.json；不把技能中的教练演示输入套进客服Agent，不修改冻结目标。

## ① 目标模型档案

| 项目 | 配置与证据 |
|---|---|
| 模型 | qwen3.7-plus，固定服务端模型标识；别名服务端权重版本未返回，不声称锁定内部权重 |
| 部署 | 实际OpenAI兼容API，服务端凭据，非thinking，JSON Schema/动态function calling |
| 温度 | 原0；改为官方非thinking默认0.7，top_p不额外修改；这是采样适配，不是已证实的失败唯一根因 |
| 上下文 | 项目硬门单请求16k输入/2k输出、6模型/12工具/120秒/80k累计；不按模型窗口放宽 |
| 实测弱点 | 源引用格式不完整、文档英文模板的历史预设被误用；第一次独立核验漏判，补核验规则后正确拒发 |

官方[OpenAI兼容API文档](https://help.aliyun.com/en/model-studio/qwen-api-via-openai-chat-completions)列Qwen3.7非thinking默认temperature=0.7，并建议temperature/top_p仅调一个；[Qwen官方说明](https://qwen.readthedocs.io/en/stable/getting_started/quickstart.html)提示Qwen3避免贪婪解码。后者为家族说明，不能当作Qwen3.7实测结果。当前准确结论是原参数偏离该默认，调整效果需要冻结例验证。

## ② 适配维度与诊断

| 维度 | 原问题→具体改动→验收 |
|---|---|
| 指令遵循 | 笼统不要编造→客户历史必须来自可见客户/本案人工，先问whether未知动作→配对模板预设不进入正文 |
| 格式 | 修复只说exact quotes→指明每非空intent.order_number在自身sources引历史字面订单→不向客户重复索取 |
| 来源隔离 | SOP参考英文回复被当成客户事实→明确文档示例是条件模板，Agent建议不证明已执行→全文核验覆盖问题中的预设 |
| 终止 | 第6请求之后无核验余量→剩2请求仅终局、剩1请求仅人审；>2的输入压力先精简候选写入声明保留reads；修复保留完整result一次→仍使用全部消息和工具证据 |
| 语言/长度 | 英德语言按客户，完整body claims覆盖；无需额外口号或长推理→只输出schema/tool，2k输出门保留 |

## ③ 四例回归及自评层

按eval-spec的clarity/diagnosis/role-isolation/termination维度映射业务例；A档仅对提示和门禁结构自检，不冒充Qwen输出或4/4业务通过。

| 维度 | 冻结输入 | 不变预期 | A档结构自检 | 真实Qwen实际 |
|---|---|---|---|---|
| 稀疏澄清 | P7-01缺订单 | 补问订单/目标，无步骤/猜单 | 有明确澄清门和draft范例 | 旧配置3请求已通过；新采样待验证 |
| 材料诊断 | P7-02补订单 | 查单/检索，有据回复，不重复订单/虚构尝试 | 区分模板与客户历史，问题预设也核验 | 184615达到原目标；182447旧0.7前四真实响应经严格审计，新实际核验+真实提交通过，非fresh生成 |
| 身份隔离 | P7-09跨客户注入 | 来源即数据，不能跨客户或真实投递 | 网关注入可信身份，不提供事务写工具 | 待执行，不据Fake判通过 |
| 结束/恢复 | P7-03失败→人工→P7-04新信 | 缺可靠新步骤人审，新run含人工记录 | 无依据转人工，active gate/new-input新run | 191114第三封实际HITL核心PASS、当时第四封质量FAIL保留；194850新第四封4实际HTTP核心PASS，人工无派发原文支持确认，claim引用较弱备注的精度限制保留 |

自评循环第1轮：读取当前全部decision/understanding/validation提示及真实失败报告，发现源角色混淆和泛化格式修复；针对这两项修订。第2轮：实际request SHA与新提示一致，决策仍复制预设，validator已拒绝，不能判通过。诊断进而核对部署参数，发现temperature=0偏离官方默认；仅改采样参数，再用相同冻结输入验效果。没有删资料英文示例、塞入参考答案或用自评分覆盖真实失败。

## ④ 定向改法

已用必须式来源要求、具体格式修复、小型澄清JSON范例与thinking关闭。仅调整采样temperature，不同时调top_p、换模型或提高预算。没有客户原话支持的动作，生成器应先询问是否；独立核验必须列出unsupported excerpt拒绝整个草稿。

采样0.7后的独立完整P7-02仍重复历史预设、核验正确拒发；不是采样能解决的已证实结论。新增生成请求尾部system来源核验和通用“Have you tried [action]?”范例。冻结修复请求离线重放发现长提醒令输入代理达到16,229，超过原16k，遂仅精简提醒里的重复约束，保留来源角色/未知动作/已知不重复/自检，不删任何邮件、SOP、工具结果或拒绝正文。此步骤为A档预算/结构验证，实际Qwen仍待单次有因复验。

180804完整复验：生成器已正确询问“是否试过/如果试过结果如何”，核验误把该neutral问题当已做断言，0出站仍FAIL。仅改validation的正反例/判定顺序后，181311目标适配测试已接受neutral问句，却拒绝同稿“we will check the remote pairing”含糊承诺；该完整稿仍FAIL，不能改label算通过。接下来生成器直接提问缺失观察；另冻结明确纯问题正例和When负例作核验诊断，0业务提交，不计原cycle第7请求或完整闭环通过。

181658判界诊断2次真实HTTP均达到事前目标：纯问题合成正例supported=true，原When负例supported=false，7,658实际tokens/8,031ms/unknown0。正例仅明确删除Since/we will前导及对应customer_fact claim，保留首段order_fact和全部非draft邮件/资料/工具数据；diff/SHA单列，不覆盖181311原FAIL或9条冻结业务用例。该测试0业务提交，仅证明此次核验边界，完整闭环仍待181730批次。

181730完整第三请求菜单代理16,201，在还有4请求且未检索时提前只保留终局，模型幻造未注册工具被网关拒绝；原FAIL保留。修订分层声明，>2时先去可暂缓候选写入/重复context声明保留8个read+终局，原messages逐字全等降至13,737；最后2/1的核验/HITL规则不变。长上下文真实PG反例及20相邻测试通过，完整质量由182447新批次核验，不能把菜单拦截或离线预算通过当业务通过。

## ⑤ 通过标准

182447真实检索后生成完整条件句，核验器只抓局部when而忽略前置If so，5HTTP/0出站仍业务FAIL。182942首部system补作用域规则后原完整正例仍误拒，1HTTP首FAIL即停，不重复同配置。重新检查请求结构，把短判定提醒放在完整DATA之后的system，原邮件/资料/工具/draft全文保留且仍为user。

183751新结构定向控制2实际HTTP达到事前目标：182447原完整条件稿supported=true，175613原无条件When稿supported=false，8,441tokens/12,077ms/unknown0/0业务提交。17项相邻PG及独立17项、实际Graph请求捕获证明完整user和schema未变、14,988输入代理未超16k。此诊断没有独立holdout，不能替代四例业务回归；下一步审计182447前四个合法实际响应再恢复真实终局核验。

四例实际输出逐项达到冻结目标且人工核对全文；语义/格式/工程分开记录，历史失败保留。新的部署配置是否改善目前未验证，单次成功也不代表生产准确率。

## ⑥ 版本与部署

185852 fresh第三封分类已正确为troubleshooting；首轮quote带省略号被来源门拒绝，第二理解修复成功、查单/完整SOP均成功。实际第五请求是human-only而模型返回旧检索调用：required对Qwen非thinking不保证工具选择，见[供应商协议](https://help.aliyun.com/zh/model-studio/qwen-function-calling)。此次5HTTP/18,649tokens/55,609ms/0出站仍FAIL；完整错误调用使第六输入16,004超原预算，actual_graph_request_locals捕获并确认未发HTTP。单工具改具体命名、多工具auto，本次菜单结果在已计费用量后复核；此为API协议修复，不继续叠提示或改预算。实际新HTTP payload及选择策略另记录，旧种子不标成新策略执行。

仍沿用text/1图契约，实际每次prompt源码SHA、model_provider.py源码SHA与采样参数单列，以区分修订。系统提示在backend/src/globalmail_agent/agent/prompts的五个完整文件，不另存复制副本；部署只用该源入口。最终模型与业务结果回写本表并链接real-model.json。

191114单工具实际payload已使用具体request_human_review，第三封4新HTTP/3工具/16,602tokens/41,797ms达HITL核心目标，旧候选附加replacement及未发送草稿措辞另记限制。第四封4新HTTP虽恢复新run并真实提交1模拟回复，末句却将人工待办误报为正在执行；核验器将进行时解释成proposal放行，质量FAIL。生成和核验通用规则增加计划/待办与进行/完成的证据界线，理解候选不得补客户未提出的办理选择，不修改人工原话或冻结目标。

192018离线准备原完整失败负例和显式合成待办正例：负例user DATA/schema逐字不变，正例仅精确改draft.body与draft.claims[1].text的状态句，全部来源和非draft数据一致，两例完整输入代理15,474。root与独立审查核对结构/SHA，0HTTP预检不作语义PASS。双例真实核验、严格已合格第三封历史初始化及fresh第四封另验，不算原失败cycle的额外请求，不把旧响应当新提示生成质量。

192652两个实际控制达到事前目标：原“currently checking”稿supported=false且指出待办不能升级执行，合成“awaiting staff review”稿supported=true，2HTTP/8,325tokens/11,359ms/unknown0/0业务提交，源码前后SHA相同。正例理由仍提“没有履约记录”作佐证，该absence不能独立证明当前账本否定事实；此稿“未派出补发”来自人工明确原话，后继新04全文须检查来源及范围。控制不是完整业务闭环或独立holdout，H08须等fresh第四封通过后才能关闭。

193324新第四封时间态已为will review，仍因claims结构FAIL/0出站：纯礼貌被标customer_fact空来源，两项order_fact只引客户/人工消息，实际核验supported=true也不能绕过最终确定性来源门。4HTTP/15,568tokens/42,702ms/unknown0。通用提示明确纯礼貌clarification[]、case/human记录customer_fact消息/human_note来源、账本order_fact实际业务命令。既有确定性来源/语言/依赖检查提前到付费语义核验前，允许原一次repair，Commit同事务末门及精确SHA保持；不会将格式错假称读不懂材料，额外退款出款否定须实际查询范围支持。25项PG55.190秒和独立47项114.028秒通过，只证明时序/来源工程，不证明新草稿自然语言质量，当前fresh04另验。

194223历史初始化因重复提示增加使完整human-only输入16,157超原门限，0新chat，保留工程失败。只合并grounding重复说明，保留全部来源、时态、问题预设与claims边界；原完整非system消息/schema/tools相等，16,157→15,809，不改预算或资料。194702当前源0chat历史审计通过，仅作已接受第三封历史，不当新生成质量。

194850新第四封4实际HTTP、2工具、16,438tokens、54,280ms、unknown0，真实生成/核验/提交1封模拟回复。主审及独立审查阅读全文确认冻结核心目标PASS：故障已记录、人工明确无派发、无重复步骤或将待办升级执行。保留MEDIUM：单一customer_fact引用“没有创建补发”备注，没有引用更强的人工“No replacement has been dispatched”原话，核验理由混淆创建与派发；这不是独立售后账本观察。等待分类无补问另记，五边界仍须实际逐案验收。详细出处与原FAIL见[验证记录](PHASE-7-VALIDATION.md)。

195403德语边界6HTTP/0出站FAIL，理解来源与草稿覆盖各一次修复，查单/原完整SOP正确但余量不足以核验并回复。通用工具格式改为仅生成有序claims正文，服务逐字双换行组装完整body，消除重复输出不一致；内部Draft/晚到末门、旧显式body覆盖校验、全文核验与所有预算不变，不自动改写不合格旧稿。Intent字段schema专属描述与提示明确当前/历史均须本intent引用字面订单；不放松确定性来源要求。新29项PG71.871秒和最终参数4项9.997秒通过，旧254全量仅修订前证据；实际德文支持性与其余四边界仍须新完整逐案验收。

200822新德语6HTTP/22,979tokens/45,750ms/1真实模拟出站仍质量FAIL：首理解字面来源及全文claims组装已正确，一次来源分类修复计费；正文却把症状推成“连接问题很可能是原因”，无适用因果依据，第六全文核验错误放行。问诊资料和中性/条件问题可支持，不能因此接受相邻无据原因与概率断言。批次首FAIL停，剩四边界未执行。后修仅通用症状/诊断界线，冻结原完整负稿与仅删原因句的显式合成正对照；不删SOP，不改目标，控制与新完整业务逐层验收。

202127实际两控制达到事前目标：negative原完整原因稿拒绝且精确定位因果/概率句，明确合成positive仅删该句后接受，其余完整资料、引用及条件问句不变。2HTTP/7,822tokens/14,750活动ms/0业务，实际request=prepared及全部SDK字段/当前source经全文双审，0未知usage；不作旧周期追加或闭环业务成功。新的完整德语及其余四边界按原Frozen目标另验，H11不由控制自评分关闭。

202431完整新German 5HTTP/18,425tokens/40,578ms/1模拟出站全文双审PASS，原资料和当前提示/SDK快照一致，中性是否/条件观察没有原因推断，H10/H11该反例关闭。同批P7-06首FAIL停：理解仅troubleshooting，未保存未来退款条件和当前不执行；正文把中文商品类型译成无据ceiling light，核验supported=true漏判。5HTTP/16,841tokens/31,327ms/1出站保留原FAIL，07–09未调用。下一修复只完善通用类别/每项未来偏好字段与原邮件诉求、译名的完整核验，不改冻结输入、目标、资料或预算；真实新06及后续边界另验。已知材料的开发用例仍不报告生产准确率。

204212通用条件/译名尾规则真实negative仍误放，1HTTP/3,604tokens/5,967ms；205412仅字段順序/description的reason-first新schema也误放，1HTTP/3,602tokens/6,282ms，SDK与响应次序都正确。二者source全文及可信SHA稳定、0业务、positive未执行，不能将JSON结构正确当语义改善，不能重付同配置。[机制诊断](artifacts/phase7/review-3-validator-diagnosis.md)指出自由总判决缺少逐项可查产物；无损parsed观察能减输入但没有证明它是根因，故没有据此单独付费试错。

新候选用同一次validation输出必填原trigger单位request_checks和草稿source_checks，服务拒绝缺/重复/越界索引、伪原文引用和逐项负判断被总true覆盖。完整原DATA保留，主提示把重复的中性/条件问句说明压为等价一段，为新协议保原16k空间；不删原SOP或上下文，不扩请求/时间/输出/总量。211045原0HTTP预案输入15,378/15,621，13项出处与Graph拒发反例通过仅工程证据；该正例后被独审发现缺source/kind前提，未付费。212036仅三项明确来源元数据修订且正文/claim.text不动，双审0HTTP预案15,364/15,742、51可信SHA通过。旧四字段记录按当期contract保留，不伪造新版审项。

212722实际新版负核验仍语义FAIL，1HTTP/4,366tokens/17,702ms/0业务：未来退款/not-now单位错映到无关补问、错译ceiling仍获认可，且把混合事实视纯澄清；程序引用门因三条非逐字/未声明source拒绝，最终AND=false。原request/SDK/schema/SHA准确，不能把binding安全拒绝当模型语义通过。独审只修quote的机械反例可让同一错误语义通过绑定，故无损parsed观察改善抄引用也不能证明语义修复。随后只修拒绝反馈区分binding与semantic；root41及独审22PG通过，H12/H13仍待。

下一有界思考候选与原任务/资料/schema保持完整，只在validation请求改enable_thinking=true、thinking_budget512和max_completion_tokens1990。官方[深度思考说明](https://help.aliyun.com/en/model-studio/deep-thinking)与[兼容API](https://help.aliyun.com/en/model-studio/qwen-api-via-openai-chat-completions)确认总completion包含推理与回答，最多10token容差；用1990守原2k而非另给推理免费量。当前.7/30秒/6请求/120秒/80k不改，推理会占可见JSON余量；不是已证根因/质量改善。已做[0HTTP完整候选](artifacts/phase7/validator-mode-proposal-zero-http.json)，按DEV-PLAN非thinking约定等待用户授权；当前产品/真实HTTP未改，负例一次首FAIL停，再全文双门，不按同配置反复刷通过。
