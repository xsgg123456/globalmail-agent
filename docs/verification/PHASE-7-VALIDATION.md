# Phase 7 文本 Agent 验证记录

2026-10-09提交决定：用户明确要求先Git提交Phase7，保存工程实现和全部真实FAIL/未执行项，后续继续Phase8。该提交不是本期质量验收通过；Stage1仍未通过、Stage2未执行，needs_review保留，正式库未升级。提交前当场重跑编译、依赖检查、前端测试/构建，记录见下方“提交前验证”。

## 提交前验证（2026-10-09）

- `pnpm test`：53项通过、0失败/跳过，4864.9182ms；[本次输出](artifacts/phase7/commit-frontend-tests.txt)。
- `pnpm build`（`vue-tsc --noEmit && vite build`）：exit0，Vite40.13秒；[本次输出](artifacts/phase7/commit-frontend-build.txt)。
- `python -m compileall -q src tests ../agent-eval`：exit0；`uv pip check --python .venv/Scripts/python.exe`：57包全部兼容。
- [提交源码核对](artifacts/phase7/commit-source-check.json)：当前后端180文件与已通过92项的快照完全一致，评测工具41文件与已通过43项的快照完全一致；未新增付费请求、未将历史276项冒充当前全量重跑。新Phase8代码未纳入提交。
- 源码与说明文档的暂存差异空白检查通过；三份历史原始日志/旧diff含行尾空白，保留原字节。静态自检未发现失效文档链接、超过300行源码、TS any或实际配置密钥泄漏。[检查记录](artifacts/phase7/root-final-check.json)。原Stage1 FAIL与Stage2未执行状态保持。

2026-10-09最新用户决定：本期模型局部优化停止，工程开发转入Phase8，完整项目链路跑通后统一回归。以下FAIL和未执行项全部保留；当前状态为“工程已实现、质量与最终验收延期”，不再作为后续工程开工门槛，不等于本期已验收。既有拒发和安全/数据一致性规则保持。原正控制/新06–09/Stage2及模型来源/事实核验问题纳入最终回归，不再为本期追加付费候选。

2026-10-09容量候选结论：唯一原负控制074740-90d0b3da[根全文审计](artifacts/phase7/root-capacity-negative-audit.json)与[独立全文审计](artifacts/phase7/review-3-capacity-negative-actual.json)均FAIL，停止本配置付费。1HTTP/6279tokens（3542+2737含2048推理、只计一次）/49062活动ms/0业务；75原SHA、actual完整request/SDK/schema顺序/原source正文、paid前后/当前源码全相同，原机检11true保持。unit2正确omitted/空quote，总reason指出未来条件遗漏；claim1正确拒绝其声明shipment来源没有商品/SKU，不再错误要求复述四按键/美规/黑色，但这不证明补订单来源就能将ceiling翻译核准。仍有claim0只引订单号认可“checked shipment”、claim2带物流/客户事实却空证据true，两owned来源quote均为重写JSON而非连续原文，首typed码claim_0_quote_not_in_source。总false和准确程序拒发不能替代完整语义核验PASS。已保存实际response SHA对应FAIL gate，实际positive入口只读调用证明在HTTP前拒绝。正控制/表示接Graph/fresh06–09/Stage2仍未执行，不重复当前配置，也不把控制局部进展写作fresh06 Understanding已修。

独立[18项19.541秒](artifacts/phase7/review-3-capacity-stage-tests.txt)/[稳定快照](artifacts/phase7/review-3-capacity-stage-tests-snapshot.json)及[完整付费前检查](artifacts/phase7/review-3-capacity-authorized-preflight.json)工程PASS，compileall0。最新[正式库只读核验](artifacts/phase7/formal-current-readonly.json)保持0005/54表/旧53业务表列行SHA、设置与160原件；知识22/22、build/release/cache0、formal-before字节不变。正式及隔离四端口未监听、旧隔离schema/对象不存在，无正式升级/重启，needs_review且暂存为空。旧276全量属于容量前，保留原字节；本期四步仍未全过，Phase7未完成。

2026-10-09最新授权：用户“好的那你继续”批准核验容量方案，Spec v1.14/主架构v1.2/DEV-PLAN及text/5产品源码已同步。仅validation4k总输出（3990+10）/thinking2048/最多60秒且受剩余活动时间约束，其他2k/30秒及总6/12/120秒/16k输入/80k保持。工程专项与当前完整零HTTP预案复核中；旧276全量原字节归档before-capacity-276，不当新源最终验收。原parsed表示仍只在eval，负正及后续业务尚未新增HTTP；语义HIGH与Stage2未开始保持。

容量工程专项[92项84.176秒](artifacts/phase7/review-capacity-tests.txt)/[前后稳定快照](artifacts/phase7/review-capacity-tests-snapshot.json)0失败/错误/跳过；所有backend源码、测试、迁移及锁SHA与当前一致。首次92项有1个fixture FAIL：模拟租约失效后未恢复导致下一subcase无任务可领，原日志/快照保留initial-fixture-fail；修测试恢复并以Event控制活动钟，不将其称产品修复。之后只更3个eval文件：明确旧34448预留为历史元数据、第二次控制timeout按剩余活动时间计算完整实际预期、其离线测试；[最终eval43项0.757秒](artifacts/phase7/review-capacity-eval-tests-final.txt)/[当前稳定快照](artifacts/phase7/review-capacity-eval-tests-final-snapshot.json)通过，compileall exit0。当前[完整0HTTP预案](artifacts/phase7/review-capacity-preparation.json)074344-66a5c470，输入15035/15413，双控制按授权4k预留38448；231517原完整messages/DATA/Schema/source不变，完整SDK仅3990/2048及请求timeout60。首版、元数据澄清版和timecap修后各原预案保留，不覆盖私有原件；当前仍0HTTP，待独立前检。

最新状态：text/4产品当前完整后端276项548.623秒/0fail/error/skip/source_changed=false，独审确认179文件before/after/current原SHA一致；旧274原日志与快照已逐字归档为backend-tests-before-thinking-workflow-contract-274。评测工具当前42项0.791秒/0fail/error/skip/source稳定、compileall通过。前端未改，沿用已核53项及vue-tsc/Vite工程证据。工程通过不能关闭真实语义HIGH。

231655唯一无损parsed表示prototype仍完整双审FAIL：1HTTP/4892tokens（3542+1350，含512推理）/25780活动ms/0业务出站；70可信SHA、actual request/SDK、完整DATA还原及原source正文全部一致。未来退款仍错映物流补问并被称addressed，混合事实空证据被认可；商品译名有歧义缺核准的局部认识，但错误地把未复述四按键/美规/黑色属性当主要否决理由，不能算两原缺陷通过。程序准确因非原文引用拒绝，不当语义PASS。该表示假设停止，不接Graph；所有positive及fresh06–09仍0HTTP，Stage1仍HIGH/Stage2未开始、正式库未升级、needs_review、不提交。

待用户确认的具体下一方案：仅validation将输出预算2k→4k（SDK3990+10容差、thinking2048为其子限额），网络30→60秒且取cycle剩余活动时间更小值；其他节点仍2k/30秒，原6请求/12工具/120活动秒/16k输入/80k累计不变。服务须按stage预留/unknown保留/settle计完整推理+答案一次，过限及length拒发；候选不是已证根因或改善。见[零HTTP完整SDK与预算方案](artifacts/phase7/validator-capacity-proposal-zero-http.json)：完整parsed prototype正负材料/schema/prompts逐字保留、输入15035/15413、两次保守预留38448、0HTTP/产品配置未改。授权后先同步ASM-006/架构/计划及stage工程回归，原负正逐案全文双审，再接同一表示/新业务，不降低冻结语义目标。

最新text/3工程回归：根41项73.542秒、独审4项10.136秒，均0失败/错误/跳过、源码稳定，compileall exit0。225009零HTTP完整预案双审保59可信SHA、非首system消息/schema/采样/预算不变，输入15406/15784。唯一负控制225432-d2f20860为1HTTP/5032tokens（3577+1455，输出内含512推理）/31358活动ms/0业务出站；实际SDK等于计划，原预算内/source稳定，runner检查通过，完整双审待完成。总reason提两原缺陷，但退款unit仍addressed且quote非正文、claim1越用未声明source、claim2混合事实仍empty/true，不能只据总false称语义通过。正确正控制及新06–09仍0HTTP；当前源全量尚未重跑，旧274属于改动前。

日期：2026-10-08。状态：验收中；真实模型连续闭环、最终独立审查及正式升级尚待完成。对应 [DEV-PLAN](../../DEV-PLAN.md) Phase 7 和 [实施步骤](../planning/PHASE-7-IMPLEMENTATION.md)，不勾选82项产品AC。

最新授权：用户要求按已呈现方案继续调整并尽快结束Phase7，核验专属thinking512/总输出1990已按源合同落地；理解/生成仍false/.7/30秒/retry0及原完整输入/所有预算保持。此前“待用户许可”记录按当时状态保留，当前许可已取得。新[0HTTP准备](artifacts/phase7/review-thinking-authorized-preparation.json)223750完整SDK与已批准候选相等，原两份prepared请求原字节不变，54可信SHA、输入15,364/15,742；完整实际总参数及reasoning-inclusive usage捕获已补。[73项39.747秒](artifacts/phase7/review-thinking-tests.txt)/[稳定快照](artifacts/phase7/review-thinking-tests-snapshot.json)、独审[10项6.828秒](artifacts/phase7/review-3-thinking-profile-tests.txt)/[稳定快照](artifacts/phase7/review-3-thinking-profile-tests-snapshot.json)0失败/0skip，compileall exit0；原274全量属思考模式之前，不冒充当前源码最终验收。

224147恰一次实际negative仍FAIL并停该候选，positive/fresh06–09均0HTTP。1HTTP/4,870tokens（3,571输入、1,299输出，含512reasoning）/25,030活动ms、适配器24.875秒；finish=stop、全文SDK=planned、54SHA/源码稳定、原预算内。模型总supported=false，unit2=changed_condition且reason明确说明未来退款/not-now被漏，有局部进展；但claim1仍true、无据ceiling subtype没有被指出，claim2混合事实仍称空evidence/true，unsupported_claims为空。quote为重构label:value、并有未声明source，binding仍正确拒绝；该拒绝不证明双语义缺陷修复。原坏稿、旧FAIL、正稿和九业务目标均不改，不重付同配置；继续独立诊断最小任务安排调整。实际记录保Git忽略tmp/phase7-agent-eval/20261008-224147-cf5c680c，安全汇总见[real-model.json](artifacts/phase7/real-model.json)。尚未正式升级。

最新完整业务批次202431：P7-05德语完整业务全文双审PASS，5新HTTP/3工具/18,425tokens/40,578ms/unknown0/唯一模拟出站；未知配对先问是否，Falls ja限定灯闪/红灯观察，原客户与完整SOP有据，无诊断/步骤/履约承诺。raw有序claims逐字组装、全文送审、artifact与出站SHA一致，SDK与付费前source快照已独立核对。同批P7-06首FAIL停，5新HTTP/3工具/16,841tokens/31,327ms/unknown0/1实际出站：物流读取有据，但最终理解丢失未来有条件退款/当前不执行选择，且将中文商品类型误译为ceiling light，全文核验漏判。07–09尚无HTTP，临时schema/对象均清理；工程completed和不执行退款不能替代原条件保留目标。该失败及旧195403/200822保留，后修另验，详见[独立完整业务判读](artifacts/phase7/review-3-business-semantic-checks.json)。

最新逐项审计机制尚未获得真实质量PASS。旧四字段实际响应不补写新审项；当前同一次核验要求来信单位与claim索引完整、引用逐字属于该claim实际来源，并把逐项结果与总判决共同AND。索引/原文绑定不能证明语义蕴含。修前[271项524.878秒全量](artifacts/phase7/backend-tests-before-courtesy-capacity.txt)/[稳定快照](artifacts/phase7/backend-tests-before-courtesy-capacity-snapshot.json)保留；独审发现“礼貌”夹具还含物流事实，已换为真正greeting/纯courtesy，并移除新加的40单位限制。第一次41单位夹具仍引用旧customer_fact，按来源门正确拒绝的[失败](artifacts/phase7/item-audit-courtesy-capacity-fixture-fail.txt)保留；修后[14项5.369秒](artifacts/phase7/item-audit-courtesy-capacity-fixed.txt)、独审[17项11.416秒](artifacts/phase7/review-3-item-audit-fixed-tests.txt)/[稳定快照](artifacts/phase7/review-3-item-audit-fixed-tests-snapshot.json)、评测工具[38项0.867秒](artifacts/phase7/eval-tests-item-audit-source-repaired.txt)均0失败/0skip，compileall exit0。该版272项最终后端全量随后通过，530.155秒/0skip/SHA稳定；后续反馈修复另列，不能把修前全量当最新源验收。

211045预案只有0HTTP，独审指出合成正例claim0漏shipment出处、claim2混合物流与客户事实却标clarification且无来源，故未付费。212036新0HTTP预案完整冻结51份原文件，负稿不改；正稿在原四项正文修订基础上仅做三项来源元数据修订：claim0追加原shipment命令，claim2改order_fact并绑定原shipment命令和原客户来信。正文及每段claim.text逐字不变，全部非draft DATA、原错误understanding、资料及原预算保持；两输入代理15,364/15,742。见[主审完整重构预检](artifacts/phase7/root-item-audit-preflight.json)和[独审预检](artifacts/phase7/review-3-item-audit-source-repaired-preflight.json)，双方0HTTP结构预检通过。该付费前记录不将合成正例称为理解正确或业务通过；随后唯一负例实际结果另列，未执行正例和fresh06。

212722新逐项机制实际负例仍语义FAIL：1HTTP/4,366tokens/17,702活动ms/0业务。原未来退款/not-now单位被误映到物流补问，ceiling译名仍被认可，混合事实段仍称无来源澄清。但三条证据均非原文片段、其中一条不属于该claim声明来源，程序audit_accepts及最终AND均false，不能称当前Graph已放行。原请求/完整SDK/schema/51SHA均准确稳定，见[主审全文判读](artifacts/phase7/root-item-audit-negative-observation.json)、[独审实际核对](artifacts/phase7/review-3-item-audit-negative-actual.json)和[机制诊断](artifacts/phase7/review-3-item-audit-mechanism-diagnosis.md)。在内存只修引用便可使同一错误语义判决通过绑定的机械反例说明，引用门不能替代H12/H13语义达标；positive及fresh06–09仍0新HTTP。

随后只修实际失败反馈：typed区分绑定错误与模型语义否决，前者优先传实际错误代码、后者保留具体reason；原全文、schema/prompt、一次repair及预算不变。原[272项530.155秒全量](artifacts/phase7/backend-tests-before-audit-feedback.txt)/[稳定快照](artifacts/phase7/backend-tests-before-audit-feedback-snapshot.json)按修前版归档。初版root[40项71.048秒](artifacts/phase7/audit-feedback-first-regression.txt)未覆盖语义reason分支，独审[21项23.899秒2FAIL](artifacts/phase7/review-3-audit-feedback-tests.txt)明确发现语义负项解释丢失，原FAIL保留。typed第一批41项的claim_false夹具把omitted改addressed却没补reply_quote，按绑定规则拒绝的[错误前提FAIL](artifacts/phase7/audit-feedback-invalid-premise.txt)保留；只修夹具后[41项70.487秒](artifacts/phase7/audit-feedback-regression.txt)/[稳定快照](artifacts/phase7/audit-feedback-regression-snapshot.json)、独审[22项22.997秒](artifacts/phase7/review-3-audit-feedback-final-tests.txt)/[稳定快照](artifacts/phase7/review-3-audit-feedback-final-tests-snapshot.json)0失败/0skip，compileall exit0/57包兼容。反馈工程缺口关闭，语义HIGH尚未关闭。当前修后最终后端全量274项542.232秒、0失败/0错误/0skip、source_changed=false，见[完整输出](artifacts/phase7/backend-tests-final.txt)与[源码稳定快照](artifacts/phase7/backend-tests-final-snapshot.json)，不能把工程通过当作模型语义达标。

下一候选仅核验阶段开启有界思考，见[0HTTP完整预案](artifacts/phase7/validator-mode-proposal-zero-http.json)：qwen3.7-plus/.7、完整messages/schema/原错理解/正文及资料逐字不变，thinking_budget512、max_completion_tokens1990含推理和回答，以官方最多10token容差仍守原2k；16k/6请求/12工具/120秒/80k/30秒及SDKretry0不变。原控制两输入15,364/15,742、保守预留35,106，0HTTP/当前产品仍非思考。该方案修改DEV-PLAN固定非thinking约定，已向用户请求许可；尚未授权、落产品或实际验证，不保证可见JSON放得下或语义改善。仅原负例一次、首FAIL停，全文双门后才正例和新业务；不静默改参数或把思考扣除使用量。

候选另获[独立0HTTP重构预检](artifacts/phase7/review-3-thinking-proposal-preflight.json)PASS：两个SDK候选全文、51旧来源/current typed源码、1990+10总限额与512子限额逐项吻合；仅限候选结构，不代表用户授权或实际模式改善。当前源码274项最终全量已通过，backend继续冻结；正式数据仍Phase6，Stage1仍HIGH、Stage2未执行。用户的核验模式选择仍待答复，尚无新配置或新HTTP。

## 交付与范围

固定 `qwen3.7-plus`、LangGraph动态工具循环接入工作台。RunContext由数据库构建，逐封读取可见邮件/人工记录；历史对照不进入后继真实前缀，未来消息/快照不可读取。Understanding保存语言、多诉求、条件、订单候选和有来源的事实；成功本轮工具或人工来源可以修订候选，保留初版和修订过程。

工具仅包括既有身份范围内的业务查询、已发布知识检索、案件候选修订、回复/人审提案。产品步骤引用当前SKU适用依据，所有暴露知识登记正文依赖；下架/发布头变化会阻止旧结果提交，最多在原预算内重建一次。模型不能选择身份、模式、时间、发布头或任意SQL。

理解危险后风险与人审同事务持久化；普通人工回复保留风险，人工解决/更正须当前版本及依据。同一旧消息换合法quote不会复活已处理风险，新危险来源仍接管。最终草稿全文claims覆盖，另用原预算内的模型核验全文来源、语言及问题预设，再按规范化SHA核对最终提交。SOP模板、历史客服声称和建议不能变成已做操作或执行凭证。

每cycle仍为6模型请求、12工具调用、120活动秒，单请求16k输入/2k输出、累计80k。理解修复、网络重试、语义核验都计入；未知usage保守保留，显式retry不重置。剩2次只暴露终局工具、剩1次只转人工；修复完整工具结果去等价副本，不截断业务/知识原文。

固定SDK PostgreSQL checkpointer的put/pending-writes与输入、租约、权限、资料栅栏共事务连接；严格JSON序列化不启用pickle。终局原子保存本地模拟回复/历史对照、人审或业务等待、案件修订、凭证和SSE事件；重复终局查原凭证，每cycle最多一封自动回复。早到业务版本排唯一后继，只有观察并成功提交的版本才消费wake。

工作台继承现有Art Design Pro/Element Plus。正常已提交回复进入时间线；历史AI对照、工具、引用、理解修订、案件记忆、用量及run/cycle独立显示。trace关联保存于后台记录，当前页面未单独显示trace_id。加载/错误/空态、停止/同cycle重试、人审风险决定/备注和旧请求代际隔离有实际验证。

本期仍没有正式图片输入、售后写操作、真实邮箱投递、Langfuse服务及完整删除；分别按后续Phase交付。本地用量和trace不能称实际Langfuse追踪。

## 四步验证

204212通用条件/译名尾规则的真实negative控制仍FAIL：1HTTP/3,604tokens/5,967ms/0业务，source/SDK请求与原预案精确一致，但supported=true，理由把“没有退款执行”代替了未来条件保留，也漏看商品类型。原目标false、原出站和原失败不改；positive/新06/07–09零调用，见[独立失败出处](artifacts/phase7/review-3-request-control-negative-failure.json)。字段顺序/描述的审核机制正在离线重审，工程通过不宣布质量改善。

当前通用类别/条件/译名修订前的全量258项773.268秒/0失败/0skip/源码快照一致已完整完成，保存[原版全量](artifacts/phase7/backend-tests-before-request-rules.txt)与[源码快照](artifacts/phase7/backend-tests-before-request-rules-snapshot.json)。理解/schema描述后3项真实PG7.111秒通过，见[来源及条件协议](artifacts/phase7/request-understanding-regression.txt)；通用生成/核验尾后38项真实PG88.048秒/0skip通过，见[相邻完整输出](artifacts/phase7/request-regression.txt)。该专项快照被固定文件名的下一次runner覆写，不能再声称保有其原始before/after文件；同版源码另有[独立31项快照](artifacts/phase7/review-3-request-rules-tests-snapshot.json)及随后[258项515.871秒全量](artifacts/phase7/backend-tests-before-verdict-schema.txt)/[全量源码快照](artifacts/phase7/backend-tests-before-verdict-schema-snapshot.json)，均稳定、0失败/0skip。编译exit0/57包兼容，工程保存不证明模型已理解正确；新完整06及后续边界另验。203514两完整控制0HTTP预案经root/独审严格重构：21可信原文件SHA、负例user/schema逐字不变、合成正例仅四处draft操作，原错误理解/工具/资料保持；实际源核验尾全文=prepared、两输入13,445/13,688，见[主审预检](artifacts/phase7/root-request-control-audit.json)和[独审预检](artifacts/phase7/review-3-request-preflight-audit.json)。

205035仅调整核验输出顺序与三项description：reason、unsupported_claims先于supported，四字段类型、required集合、1500/20边界和extra禁止不变；完整messages/原错理解/资料与203514逐字相同。34可信来源及实际schema顺序经[主审预检](artifacts/phase7/root-review-schema-preflight.json)和[独审预检](artifacts/phase7/review-3-review-schema-preflight.json)通过，输入14,128/14,371、预留32,499仍在原预算。产品源码已落地，但这仍是未证明的机制假设；[官方结构化输出说明](https://help.aliyun.com/en/model-studio/qwen-structured-output)支持JSON结构约束，不能替代语义验收。当前源码主审[38项86.012秒](artifacts/phase7/verdict-schema-regression.txt)/[稳定快照](artifacts/phase7/verdict-schema-regression-snapshot.json)，独审[19项46.942秒](artifacts/phase7/review-3-review-schema-tests.txt)/[稳定快照](artifacts/phase7/review-3-review-schema-tests-snapshot.json)均0失败/0skip，compileall exit0。新全量已启动；仅授权一次真实negative，全文双门前positive与fresh06暂停。

205412新schema真实negative仍FAIL：1HTTP/3,602tokens/6,282活动ms/unknown0/0业务，positive与fresh06/07–09没有发送。SDK properties、required及实际返回JSON均reason-first；完整请求与prepared/source逐字相等，34可信SHA及源码前后稳定。模型却只笼统判物流字段有据、把“不立即退款”当尊重未来条件，未检查ceiling属性，还误称空citation_ids提供支持。新假设正确送出但没有达到目标，见[独立顺序及失败出处](artifacts/phase7/review-3-review-schema-negative-failure.json)。停止当前配置的付费复验，重新审查单一总判决的核验机制，H12/H13仍HIGH，Stage 2未执行；不宣布通过、不升级正式服务。

| 步骤 | 命令/证据 | 当前结果 |
|---|---|---|
| Code Review | 独立code-reviewer从Stage 1重新检查，最终报告另列 | 第三轮进行中，真实模型闭环尚待通过 |
| 测试完整性 | 隔离bootstrap后`unittest.defaultTestLoader.discover('tests')`，真实PG；前端`pnpm exec tsx --test scripts/*.test.ts` | 反馈修订前全量272项530.155秒/0skip/源码稳定另列；当前41项70.487秒及独审22项22.997秒/0skip/源码稳定通过，修后最终全量274项542.232秒/0失败/0错误/0skip/源码稳定；前端53项0失败/跳过 |
| 编译 | `uv pip check`、`compileall`；`pnpm build`含`vue-tsc --noEmit` | 最新57后端依赖兼容，Python exit0；最新前端26.17秒exit0 |
| 功能测试 | 隔离API/Vite、真实Qwen/Embedding、Playwright页面、HTTP/SSE | 页面与SSE工程验证通过；真实模型H12/H13仍HIGH，后续批次未发送 |

前端测试2515.6802ms，见[完整输出](artifacts/phase7/frontend-tests.txt)、[构建](artifacts/phase7/frontend-build.txt)、[Lint](artifacts/phase7/frontend-lint.txt)。独立审查另跑53项及vue-tsc/Vite26.27秒，保留[测试](artifacts/phase7/review-3-frontend-tests.txt)和[构建](artifacts/phase7/review-3-frontend-build.txt)。独立parser结构4项及启停脚本3项通过，见[parser](artifacts/phase7/parser-tests.txt)、[启停](artifacts/phase7/local-script-tests.txt)。

核验结构修复后最新前端重验53项2476.3377ms、0失败/跳过，`vue-tsc --noEmit && vite build` exit0、3318模块、27.15秒，见[最终前端测试](artifacts/phase7/frontend-tests-final.txt)、[最终构建](artifacts/phase7/frontend-build-final.txt)。Python `compileall -q src tests ../agent-eval` exit0，`uv pip check`当场输出57包全部兼容。

通用计划状态修订后前端最新53项2483.4484ms、0失败/跳过，vue-tsc/Vite26.17秒exit0/3318模块，见[当前前端测试](artifacts/phase7/frontend-tests-final-current.txt)、[当前构建](artifacts/phase7/frontend-build-final-current.txt)。没有UI改动时不重复跑同一构建。

242项480.287秒全量回归通过后新增来源提醒/修复转录；该批保留为[修改前全量](artifacts/phase7/backend-tests-before-grounding.txt)，不能当最新版本验收。新增最后请求人审和完整修复来源反例后，19项工具/核验39.723秒、14项知识/理解修订39.268秒通过，见[工具及核验](artifacts/phase7/grounding-regression-fixed.txt)、[知识与修订](artifacts/phase7/grounding-revision-knowledge.txt)。其中第一次31项有1个夹具错误：最后消息增加system提醒后，夹具把它当tool解析；改为按role读取完整tool而不改业务断言，[原失败](artifacts/phase7/grounding-regression.txt)保留。

真实PG故障反例覆盖FT-01/02/04/05/08/09/10：并发stop/新输入/接管/租约失效拒绝晚到出站，未知终局复用凭证，SDK连接PID与事务回滚，发布/撤销共锁、一次重建保留预算，历史未来快照与模拟资料隔离，危险持久化及早到/人工持有期间wake。ScriptedModel/FakeEmbedding的冻结输出只证明工程链，不用于自然语言业务质量评分。

## 真实模型评测与失败保留

9个输入及13份原资料SHA在首次付费前冻结，见[用例](../../globalmail-agent/agent-eval/cases.json)、[冻结](../../globalmail-agent/agent-eval/freeze.json)。知识初始化只使用原中文SOP-OUTON-01，真实上传→解析→核对→Embedding构建→显式发布；精确simulation SKU及available_at保留，不将英文示例删掉或改成客户事实。各轮唯一随机schema/对象，逐封真实追加，不导入完整故事、未来反馈、参考答案或其他客户详情。

原始请求/响应/正文仅留Git忽略的`tmp/phase7-agent-eval`；仓库保存[安全摘要](artifacts/phase7/real-model.json)。每次分别记录源码/提示SHA、采样、供应商ID、模型HTTP数、工具、引用、出站、预算及cleanup。真实材料阅读、业务判断、JSON格式和持久化分层核对，不据状态completed判语义正确。

旧配置P7-01实际3请求通过缺订单补问，后继获准把该已付费真实响应作为历史种子：只映射同正文随机source ID，重走工程链，0新对话HTTP；它不算新配置重新评测。曾重放P7-02四响应前缀的批次明确区分旧采样和新HTTP；旧两次ledger遗漏原耗时的偏差仍记录，修正后在Budget初始化前写入原39,907ms再由原门禁计费，不因重放放宽120秒。

原失败包括SSE保存白名单、来源/citation格式、正文claims缺段、历史订单引用、输入代理超过16k、未支持客户配对经历以及一次第6请求timeout。语义核验曾漏判SOP英文模板的“之前做过配对”，补通用规则后正确拒发；拒发仍不满足P7-02有据回复目标。采样0→0.7沿官方默认只改一个参数，后续仍有同预设失败，不将温度当唯一根因。详见[提示适配](PHASE-7-PROMPT-ADAPTATION.md)。

最新来源提醒和转录去重先用冻结失败请求离线验证，完整read消息相同、0付费：17,504→14,504及17,427→15,869，见[预算重放](artifacts/phase7/generation-guard-budget.json)。单次有因实际复验只复用P7-01历史，重新完整执行P7-02；本地semantic gate要求逐案阅读全文通过才推进后继，保持原completed/出站/语言/查单检索目标。最终结果待批次完成回写。

180804批次正确生成neutral是否/if so问句，却被核验器误当历史断言，6HTTP/0出站，仍业务FAIL。补核验正反例后181311目标核验已识别neutral，但将前导“we will check the remote pairing”判为含糊物理执行承诺，整个原稿仍FAIL；不改其标签。生成器再改为直接问缺失观察，独立冻结明确纯问题正例和原When负例进行判界诊断，不能把离线核验HTTP算原cycle第7次或新闭环通过。

181658判界诊断2次实际HTTP通过正/负事前目标，7,658tokens/8,031ms/unknown0；正例明确标合成删歧义变体、全部非draft数据原样，0业务提交。原完整草稿FAIL仍保留，新完整闭环正在执行。

181730仍业务FAIL：尚余4次模型额度时，完整工具声明使输入代理16,201，仅超201，却被旧分支切成终局菜单，知识检索不可达；模型幻造get_product_manual被网关拒绝，3HTTP/0出站，不能当业务成功。只修压力下菜单分层：先暂缓候选写入和已完整提供的context重复声明，保留全部scoped业务/知识读，原完整messages代理13,737，见[无删输入复算](artifacts/phase7/menu-pressure-input.json)。真实PG长上下文反例保留完整客户文字、合法读取及原预算，3.647秒通过；20项相邻测试40.362秒通过，见[单项](artifacts/phase7/menu-pressure-regression-final.txt)、[相邻](artifacts/phase7/menu-pressure-nearby-tests.txt)。初始夹具240/300重复数未满足“完整声明超门而精简声明仍可读”的前提，失败日志保留；最终200重复数同时断言两个输入门限和实际工具菜单，不靠假前提判绿。

作者知道材料的合成开发例没有独立holdout，不报告生产准确率/自动解决率，也不证明全部22份资料、七类完整业务或厂家批准操作。

182447真实读取查单/完整SOP成功，生成稿的“If so, when you attempted…”仍被核验器忽略条件而误拒：5HTTP、19,171tokens、37,515ms、0出站，业务FAIL保留。182942仅在首部system补规则的独立正例再次误拒，1HTTP、3,970tokens、4,734ms；首FAIL停止，负例未付费。

改为完整DATA之后追加核验system提醒后，17项相邻真实PG36.552秒通过；独立17项35.749秒及实际Graph请求捕获确认原user全文/schema逐字相同，system→user→system输入代理14,988，见[相邻回归](artifacts/phase7/validation-tail-regression.txt)和[独立结构核对](artifacts/phase7/review-3-tail-request-structure.json)。183751独立定向控制2次真实HTTP达到事前目标：182447完整条件稿supported=true，175613无条件When原稿supported=false；8,441tokens、12,077ms、0业务/出站。它只证明此次核验边界，完整P7-02及后继闭环仍待验，不把控制算原周期第7次。

245项447.654秒全量回归在核验尾部system改动前通过，保留为[尾部改动前全量](artifacts/phase7/backend-tests-before-validation-tail.txt)；最新源码全量另跑，不能用此批代替最终验收。

核验尾部结构完整回归已完成：从backend执行`PYTHONPATH=src;tests;../agent-eval`，先调用`isolated_database_environment()`，再用`unittest.defaultTestLoader.discover('tests')`和`TextTestRunner`运行，245项456.435秒、OK/exit0，无跳过。原日志含预期故障注入的dependency unavailable记录，最终结果无失败，见[人审菜单修订前全量](artifacts/phase7/backend-tests-before-handoff-menu.txt)。它不覆盖后来human-only回退/类别语义修订；新源全量待实际闭环稳定后再验。

184249四响应重放工程审计PASS，0新对话HTTP、0终局提交/出站；真实gateway重新查订单/检索完整SOP，原英文示例及所有业务值保留。差异明确为8个随机身份/command/引用UUID映射和两次观察的observed_at/derived business_digest，其他业务值及draft全部非ID字段相等，正文SHA `ad219354abb8f342d2d4db1e532bd77a79b040d2579ea41527edd87b537b78f1`。账本实际4旧请求、3当前工具、15,257tokens、unknown0、42,780ms（包含原整轮37,515ms保守base），下一完整核验代理14,988；主动在第5请求reserve前停止。临时schema/对象已清理。该工程manifest未含后来补的三份可信原文件SHA，原样保留；新实际启动另冻结原request05/run-record/result等11文件，失败response05不读取。安全摘要的prefix_engineering_audits单列，不当业务通过。

184615 P7-02达到原冻结目标：经[独立出处审查](artifacts/phase7/review-3-draft-prefix-provenance.json)后，在当前真实图/预算/工具/栅栏内审计重放前四响应，再发1次新实际核验并真实提交1封模拟回复。三方编码者/主Agent/独立审查阅读全文确认客户事实/订单/SOP有据，未知配对先问是否、If so作用域内询问观察，不复制无条件模板、不重复索单、不发未批准维修或承诺履约。5账本请求=4旧paid+1新HTTP、3工具、19,438tokens、unknown0、47,748ms含保守base，completed/outbound_delta1、等待customer_information。新HTTP4,181tokens/6,047ms，只新增核验与真实提交；旧草稿生成不当fresh证据。后继及五个边界未完成，整体仍验收中。

同批P7-03首失败即停，尚未人工/04/边界：3实际HTTP、2工具、11,340tokens、31,359ms、unknown0/0出站；失败尝试5facts原文引用正确，但类别选product_inquiry，分类偏差另记，不冒充格式错。准确查单/完整SOP后第四HTTP尚未发送，input_budget_exceeded。从真实第三请求/响应及本案持久tool结果重构未发送的第四消息，明确标reconstructed_not_sent：全声明20,424、精简读取17,960、双终局16,547、仅人审15,372。缺口是最后声明分层未再选择能容纳的human-only；全文/目标/预算不改，修复后新批次另验，原FAIL保留。

人审最后菜单修复后31项相邻PG63.118秒OK，含双终局超门而human合法时真实人审，以及human仍超时保持budget_exhausted/0人审/0出站两反例，[原日志](artifacts/phase7/handoff-menu-nearby-tests.txt)。最初400重复的夹具不满足human可容纳前提，[原失败](artifacts/phase7/handoff-menu-regression-first.txt)保留；320重复合法长来信同时断言两个门限并实际提交人审，400重复另成为负边界，不用放松断言判绿。分类提示补通用故障/咨询界线，实际新输出尚待验。

新分类提示后两项菜单PG6.031秒再次通过，见[最新提示边界](artifacts/phase7/handoff-menu-final-prompt-tests.txt)。185555第二封历史seed工程0新chat完成：真实当前图/查单/完整SOP/已付费核验/guard提交，5旧请求、3工具、19,438tokens、unknown0、52,185ms含原已接受周期47,748ms保守base。先逐字段核对182447四响应到184615已接受版本，再映射当前scope，原11+已接受13可信文件SHA在工程前冻结；正文/claims/SOP非ID相同，失败182447核验和184615第三封均不作为响应种子。见[独立第二封出处](artifacts/phase7/review-3-second-seed-provenance.json)。此历史初始化的1封出站不当新业务质量，最新fresh调用从第三封开始。

## 人工计划与实际进度反例

单工具命名及菜单校验后48项相邻SDK/真实PG84.309秒OK，无skip；独立48项85.547秒OK且源码无运行中变化。第一次全量252项468.200秒有2条知识重建夹具失败：原understanding不带字面订单候选却直接调用检索，故本次菜单门在并发barrier之前拒绝。只补合法客户原文候选，5项知识22.814秒OK，原FAIL日志另存[全量旧前提失败](artifacts/phase7/backend-tests-tool-menu-knowledge-premise-failures.txt)。最终全量另跑，不把48项当全量。

191114第三封实际达handed_off/0出站：一次理解保存5项真实失败/拒重复事实及精确历史订单来源，实际查单与原完整SOP后命名request_human_review生成持久人审。4fresh HTTP/3tools/16,602tokens/41,797ms/unknown0，全部原冻结工程目标true；主Agent与独立reviewer全文核对核心PASS。理解requested_solution附加replacement是推测候选，不能当客户办理同意；未发送人审draft含开发阶段措辞/英文summary，不能称核准客户成稿。

同批第四封工程恢复成功：人工回复/中文备注并未自动出站，客户新来信创建新run/trace；4fresh HTTP/2tools/15,836tokens/45,609ms/unknown0，真实生成/核验/提交1出站。失败检查与“无补发”有人工记录支持，但末句把原“will check”/“待员工核对”写成“currently checking”，实际核验supported=true还把该进行时断言解释成proposal。质量FAIL保留，不能以completed或恢复成功算有据回复通过，未推进五边界。

通用生成及尾部核验提示增加计划/待办与进行/完成的来源界线，理解不自行扩展客户办理方案；原人工/客户/工具资料与9冻结目标、预算不变。12项真实PG核验/人工/记忆26.908秒OK，见[相邻工程回归](artifacts/phase7/human-plan-prompt-tests.txt)，这不证明新自然语言正确。原完整失败核验负例、显式计划正变体及只复用合格第三封作历史的fresh第四封另验。

192018双例0HTTP预检保留完整user DATA/schema，负例原稿不改；显式合成正例只把draft.body与draft.claims[1].text的一句进行时改为待办。root逐字段核对原始与prepared SHA、全非draft数据、当前三角色和15,474预算均通过，见[独立预检](artifacts/phase7/root-human-plan-preflight-audit.json)。该证据只证明结构，双例实际语义另验。独立审查最新15项21.305秒通过，见[状态相邻回归](artifacts/phase7/review-3-plan-tests.txt)。

192652实际双例核验PASS：原进行时稿拒绝、明确合成待办稿接受，2HTTP/8,325tokens/11,359ms/unknown0/0业务提交，源码SHA未变。主Agent已阅读全文，不抹去191114原FAIL。正例核验理由中的“没有履约记录”不能独立建立账本否定事实；该稿无补发来自人工明确原话，fresh04应据实际来源核对转述范围，不能把absence或工程completed当质量依据。第三封只作审计历史初始化，第四封新理解/生成/核验/提交仍待验。

192730第三封历史工程审计0新chat失败，原因是评测转录把真实工具调用附随普通assistant正文误解析为JSON，随后空review报错；原失败保留。只修eval转录并补完整真实content/arguments不变反例，14项本地1.542秒OK，独立14项1.605秒OK。192935重验0新chat通过：4原请求/3当前工具/16,602tokens/45,499ms含原41,797base/unknown0/0第三封出站/无账本写，清理3项true。root独立复算16可信原文件SHA、10随机身份映射/14处列明差异、所有理解/工具/完整SOP/人审summary-gaps/草稿claims引用非ID字段相等，见[完整出处审计](artifacts/phase7/root-third-seed-provenance.json)。该原已合格HITL仅为历史，不证明新三提示生成质量，原未发送草稿的限制仍保留。

来源预验修订前全量252项456.798秒OK/0skip，全部backend源码/提示/测试/迁移/锁文件before/after一致，见[该版本全量](artifacts/phase7/backend-tests-before-source-precheck.txt)及[源码快照](artifacts/phase7/backend-tests-before-source-precheck-snapshot.json)。它不覆盖下面的新检查时序。

193324新第四封已保留人工计划“will review”，但礼貌句被标customer_fact空来源，其他两段order_fact却只引用人工/客户消息，核验supported=true后Commit拒绝customer_fact_without_message，0出站。4fresh HTTP/2tools/15,568tokens/42,702ms/unknown0/cleanup3true，原FAIL保留。额外no refund issued不能仅由人工“没有创建退款”推出；若据模拟订单refunded_minor=0，也必须以其实际业务命令及快照范围为来源。结构和语义单列，不把本次时态正确算闭环通过。

新application/draft_validation复用原全部确定性来源/语言/依赖/业务摘要门，在Graph付费核验前检查，格式错误只允许原一次repair；权限/租约/下架/stale错误继续抛出，Commit仍验证规范化SHA并同事务重复末门。通用提示明确礼貌、人工记录与账本claims类型及各自来源。25项真实PG55.190秒OK，见[来源预验回归](artifacts/phase7/source-precheck-regression.txt)：坏来源无语义请求、完整坏稿保留供一次修复、合法稿单出站、重复错0核验/0出站；恶意clarification仍需全文语义拒绝，不把分类当真值。新版完整全量与fresh04另验。

独立source专项47项真实PG114.028秒OK/0skip，backend src/相关测试/五提示前后SHA一致，见[独立专项](artifacts/phase7/review-3-source-tests.txt)及[源码快照](artifacts/phase7/review-3-source-tests-snapshot.json)。H09程序检查时序缺口已关闭，原193324失败不改；H08业务质量仍须fresh04及边界，Stage1尚未通过。

194223仅历史初始化失败、0新chat、尚未human/第四封：新增来源说明使human-only实际输入15,940→16,157超原16k，3旧账/2真实工具/11,776tokens/46,265ms含原41,797base/unknown0/cleanuptrue。原合格第三封标签不变，不称新04质量FAIL。仅合并grounding重复来源/自检说明，完整保留各语义边界；实际被挡request只替换system，所有非system邮件/under/tool/SOP及schema/tools逐字相同，精确代理16,157→15,809，见[原完整请求复算](artifacts/phase7/root-source-prompt-budget.json)。3项PG菜单6.597秒OK，见[最新菜单回归](artifacts/phase7/source-prompt-menu-tests.txt)，300正夹具各门限仍成立，不调预算/估算或删资料。新0chat历史审计和fresh04待验。

旧320完整重复菜单正夹具在提示加长后不再满足首轮read声明前提；改300完整重复且保留首read合法/双终局超门/human可放/全文相等/实际人审0出站断言。3项真实PG6.062秒OK，见[新前提回归](artifacts/phase7/human-plan-menu-premise-tests.txt)。旧夹具全量252项466.065秒/1FAIL，见[原全量失败](artifacts/phase7/backend-tests-human-plan-menu-premise-failure.txt)。最新全量已启动，单独冻结全部backend源码/提示/测试/迁移/锁文件前后SHA及0skip，不用邻近通过代替。

194702当前源历史重验0新chat通过：第三封4旧账/3当前tools/16,602tokens/45,890ms含原41,797base/unknown0/0第三出站/无账本写、cleanup3true。root与独立reviewer再直接逐raw核对所有理解/人审/草稿/完整业务与SOP/4请求及响应、16原SHA/10ID14列明差异，所有当前源码SHA匹配且新draft_validation已纳入。见[当前根审](artifacts/phase7/root-third-seed-current-provenance.json)、[独立第三层](artifacts/phase7/review-3-194702-third-seed-provenance.json)及[独立第二层](artifacts/phase7/review-3-194702-second-seed-provenance.json)。独立最新6项PG12.354秒/0skip通过。仅作为旧已合格历史；当前fresh04新理解/生成/核验/提交另验。

194850 fresh第四封冻结核心目标PASS：当前完整图中重新理解/查单/生成/核验/提交，4新HTTP、2工具、16,438tokens、54,280ms、unknown0，completed/outbound_delta1，新run/trace，人工回复/备注未自动出站。主Agent和独立审查阅读全文：5项已失败检查正确保留，无重复排障、退款、正在核对或已执行承诺。正文确认检查已记录及未补发，后者有可见人工seq6明确原话支持，不是由查询缺记录推出。保留MEDIUM来源精度：单个customer_fact claim仅引用“没有创建补发”的人工备注，未引用更直接的“No replacement has been dispatched”消息，核验理由也混淆创建与派发；不能称本轮独立核实了售后派发账本。waiting_for为customer_information但未补问，分类精度另记。见[独立全文核对](artifacts/phase7/review-3-business-semantic-checks.json)。旧失败及合格历史不重新标成fresh；五边界继续逐案验收。

195403五边界首案P7-05德语FAIL后即停止，06–09没有调用。6实际HTTP/4工具/19,330tokens/53,250ms/unknown0，人审0自动出站，cleanup3true。分层结果：首理解intent缺订单原文引用，第二理解修复；实际查单与完整适用SOP成功；第五请求德语草稿漏覆盖开头礼貌句，来源预验正确拒绝，剩一请求只能人审，没有语义核验。未发送稿还推测连接故障，SOP没有直接支持该诊断；最后人审把未厂家核准误解为不能询问历史现象。它不满足冻结completed/1出站目标，不改标签或据德文格式正确判业务通过。后续通用claims单写组装及专属intent来源schema修复先工程验证，再有因完整复验；原raw保存。

claims单写修订前全量254项516.038秒OK/0skip、全部backend源码/提示/测试/迁移/锁文件前后一致，见[修订前全量](artifacts/phase7/backend-tests-before-claims-parts.txt)及[快照](artifacts/phase7/backend-tests-before-claims-parts-snapshot.json)。新协议29项真实PG71.871秒OK，见[相邻回归](artifacts/phase7/claims-parts-regression.txt)；最后补非法JSON参数类型和显式body=null拒绝，4项9.997秒OK，见[最终参数回归](artifacts/phase7/claims-parts-invalid-json-final.txt)。模型仅公开ReplyParts，内部Draft继续requiredbody；缺body的新claims逐字双换行组装，旧显式body原覆盖门保持。精确新旧normalized凭证重放仅计一次，超长/未知字段/空普通邮件/恶意clarification都有真实反例。最新Python编译exit0，见[编译证据](artifacts/phase7/backend-compile-claims-parts-final.json)。新版258全量和独立专项/真实德语另验，不拿29项替代整阶段。

200822新德语协议工程completed/1出站，6实际HTTP/22,979tokens/45,750ms/unknown0，但全文双审质量FAIL（H11），即刻FAIL gate停批/cleanup，不运行06–09。首理解已直接引用本intent字面订单，claims全文组装逐字正确；第一草稿把业务command标customer_fact，经原一次来源修复后正确分类。最终正文仍无据推断“连接问题很可能是原因”，客户症状/原完整SOP只支持询问观察，不支持因果与概率，实际第六全文核验误判supported=true。原真实出站与全部请求/响应保留，不能因完成/引用存在判有据回复PASS。通用原因界线后修与完整原负例/显式仅删原因句正例正在准备，0HTTP准备不能关闭H11。

201501原因判界0HTTP准备经root和独审逐字段核对通过：negative完整原user DATA/schema逐字相等；明确合成positive仅在draft.body及claims[2].text各删同一原因句一次，其他全部来源、原SOP、订单、理解和条件问题相等。proxy14,384/14,184，见[根预检](artifacts/phase7/root-cause-preflight-audit.json)及[独立预检](artifacts/phase7/review-3-cause-preflight-audit.json)。实际产品尾已按该计划落地，raw源文件SHA与通用换行规范后的实际system文本SHA分列；两prepared全文与实际prompt逐字相同，见[根源核对](artifacts/phase7/root-cause-actual-source.json)及[独立源核对](artifacts/phase7/review-3-cause-source-check.json)。0HTTP准备不当语义通过。

原因规则前全量258项669.175秒OK/0skip/wholeSHA稳定，见[该版全量](artifacts/phase7/backend-tests-before-cause-rule.txt)及[快照](artifacts/phase7/backend-tests-before-cause-rule-snapshot.json)。新规则29项真实PG89.411秒OK，见[当前回归](artifacts/phase7/cause-rule-regression.txt)；独立19项54.981秒/0skip/源码前后一致通过，Python编译exit0。源预算/早期来源/legacy覆盖/完整hash/最后额度门没有放宽。当前两实际控制、完整新德语/剩四边界和新源全量另验。

202127两独立实际原因控制PASS，2HTTP/7,822tokens/14,750总活动ms/unknown0/0业务，适配器请求耗时合计14.516秒（分开计口径）。原完整negative明确列出德语原因句并拒绝：症状/问诊参考不能建立很可能的故障原因；显式合成positive中性配对/条件观察问题通过，不预设客户尝试。root与独审已全文读两响应，实际SDK所有messages/schema与冻结prepared逐字相同，当前产品source与付费前manifest相同；raw文件SHA与发送文本SHA分列，见[独立实际核对](artifacts/phase7/review-3-cause-actual-check.json)。这只证明本次诊断边界，不算旧周期第七请求、不关闭H11或证明完整德语闭环。当前源码最终全量与唯一新05–09批次另验。

## 实际页面与网络

185852 fresh P7-03仍FAIL：分类troubleshooting及第二次修复后的5条完整事实/历史订单字面出处正确，查单和完整SOP成功；实际request05仅request_human_review、15,517输入代理，模型却返回旧search_reference且types是字符串，被参数门拒绝；第六请求完整输入16,004被Budget拒绝，实际HTTP未发。5HTTP、2成功工具、18,649tokens、55,609ms、unknown0、0出站，schema/对象cleanup全部true。原实际request/response01–05及blocked-next-request.json保留，无人审/04，不据分类正确判闭环通过。

官方协议说明非thinking required无调用保证，改为单工具具体命名、多工具auto并在usage settle后核对本次声明菜单。4项SDK payload单测已通过（首次直接unittest未加载隔离PG，31项跳过，仅记unit-only）；首次36项隔离回归发现4个旧夹具依赖未声明调用，原FAIL保留。合法get_case_context明确保留本案菜单、历史候选引用客户字面订单、负长输入通过完整合法来源facts证明human请求也超门，仍不抹原失败或改16k。最新邻近/全量/真实闭环待完成。

隔离页面API18181/Web15174，随机schema与临时对象。UI使用明确ScriptedModel驱动真实图/事务/接口和数据库状态，不计模型语义质量。实际查单/检索/引用抽屉、完整理解/候选修订、已提交模拟邮件及历史对照、风险表单必填备注、timeout失败→同cycle attempt2保留2/6用量、queued停止0模型均有独立操作证据。四个工程fixture持久状态见[UI记录](artifacts/phase7/review-3-ui-state.json)；独立已检查明亮1440×900/暗色1280×720，根Agent另查[1280浅色抽屉](artifacts/phase7/workbench-run-1280-light.png)。Stage2邻居工作台/知识/系统页面继承对照尚待执行，不用该JSON冒充视觉验收。

真实HTTP SSE首次补读、Last-Event-ID重连单调同scope、15秒心跳、重连不新增run/mail；负游标422、未来游标409、安全payload无正文，0模型调用。见[网络结果](artifacts/phase7/network-check.json)、[独立复验](artifacts/phase7/review-3-network-check.json)，入口为[phase7-network-check.py](../../globalmail-agent/scripts/phase7-network-check.py)。

## 审查及正式数据

第一轮[初审FAIL](PHASE-7-REVIEW-INITIAL.md)和第二轮[FAIL](PHASE-7-REVIEW-FINAL.md)原样保留。首次发现全文依据门、早到事件及危险跨轮保留缺口；第二轮发现同旧消息换quote复活已更正风险；已补真实反例并修复。第二轮文件名含FINAL，正文仍是FAIL。

第三次新建审查被`agent thread limit reached`拒绝；用户明确允许“本次复用审查实例”。第三轮据此重新读源文档/当前代码，从Stage 1重审，不称fresh、不改AGENTS默认隔离规则。独立已重跑86项PG（164.346秒）、53前端、实际页面及4个风险反例；最新来源修复又独立跑8项核验/7项eval自检和编译。完整两阶段结论待最终真实结果，见[进行中审查](PHASE-7-REVIEW-3.md)。

正式迁移前只读核对0005、54总表、22资料/22版本、构建/发布/Embedding缓存均0及160份资料原字节，见[升级前](artifacts/phase7/formal-before.json)。2026-10-08收尾再做[只读保旧核对](artifacts/phase7/formal-current-readonly.json)：正式库仍0005/54总表/53旧业务表，全部旧表列/行/SHA、设置及160份原件字节一致，22资料/22版本及build/release/cache0保持；原formal-before字节未变。正式15173/18080当前均未监听，未重启或升级，未写评测数据。自有15174/18181、随机浏览器schema及对象目录已清理，root与独审各自CLI已关闭，root自有CLI删除数据返回无用户数据。待门槛全部通过后用现有启停脚本增量升级并核对全部53旧业务表旧列行摘要、设置SHA和原件SHA。不会自动导入、发布知识或发测试邮件。
