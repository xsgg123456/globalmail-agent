# Phase 5 知识维护与解析核对验证

日期：2026-10-08。依据：Product-Spec v1.13、DEV-PLAN Phase 5、主架构第6.2/7.1/8节及[实施计划](../planning/PHASE-5-IMPLEMENTATION.md)。测试使用随机 PostgreSQL schema、私有对象目录和隔离页面15174/API18181。正式15173/18080不导入测试资料。

## 本期交付与边界

实现原件上传、不可变版本、Markdown修订/PDF替换/受控JSON与JSONL、结构化政策编辑、精确SKU/章节/页范围、独立解析、持久任务、原件对照、人工核对、差异和操作记录。资料全部保持simulation及未发布。没有向量、切分索引、发布/回滚/下架、检索或正式Agent；这些按Phase6及后续计划实现。

原件最多50MiB，PDF实际1–300页；拒绝伪装、损坏、加密、主动动作和附件。MinerU Basic/Standard采用独立Python环境、固定SDK和本地权重；子进程不继承数据库或模型API凭据，不下载缺失模型、不静默换档。完整raw/规范块/表格/图号/一基页码/原页与区域图片登记对象依赖；浏览器不返回raw或主机路径。

核对必须匹配当前原件、解析和适用摘要。正文、范围、档位或解析代次变化撤销旧核对；旧不可变版本及其记录保留。缺页不能以排除勾选绕过；缺关键图片须补齐或排除整段依赖并说明原因。保存核对不发布。

## 四步验证

| 检查 | 本次实际证据 |
|---|---|
| Code Review | 前两轮Stage1 FAIL保留：[首轮](PHASE-5-REVIEW.md)、[第二轮](PHASE-5-REVIEW-FINAL.md)。修复后重新派fresh审查，[第三轮](PHASE-5-REVIEW-CLOSED.md)Stage 1/2本期PASS，无新HIGH/MEDIUM阻塞。独立重跑后端123、前端33、parser4项及构建，并实际比较邻居页面、明暗宽窄屏和PDF详情。 |
| 测试完整性 | 主Agent后端123项，真实PG全部启用、无skip，含正式HTTP与真实worker/子进程；前端33项含未知响应、版本冲突、晚到结果、轮询卸载及旧会话回归；parser独立4项含原PDF像素裁剪/结构/权重篡改。 |
| 编译与依赖 | Python compileall零错误；API25包与parser115包兼容；vue-tsc零错误，最后提示修订后Vite实际构建成功26.36秒。 |
| 功能测试 | 真实页面新建→解析→原件对照→核对→修订→差异、政策同源说明、PDF取消/重试/替换、故障详情和准备资料；独立审查补JSON/JSONL范围维护、明暗窄屏及邻居页面比较，具体范围以其证据为准。 |

仓库根执行后端验证（配置只进子进程，不打印连接串）：

```powershell
$testSettings=Get-Content .local-data/runtime/settings.json -Raw | ConvertFrom-Json
$env:GLOBALMAIL_TEST_DATABASE_URL=$testSettings.database_url
$env:PYTHONPATH='globalmail-agent/backend/src'
globalmail-agent/backend/.venv/Scripts/python.exe -m unittest discover -s globalmail-agent/backend/tests -q
globalmail-agent/backend/.venv/Scripts/python.exe -m compileall -q globalmail-agent/backend/src globalmail-agent/backend/migrations globalmail-agent/backend/tests
uv pip check --python globalmail-agent/backend/.venv/Scripts/python.exe
```

原始输出摘录：

```text
Ran 123 tests in 157.655s
OK
Checked 25 packages in 1ms
All installed packages are compatible
```

故意断开依赖的用例打印安全的`knowledge_worker_dependency_unavailable`/`protocol_worker_dependency_unavailable`，没有暴露异常细节。Starlette/httpx弃用提示是现有测试依赖警告，本期没有无关升级。

前端目录执行：

```powershell
pnpm exec vue-tsc --noEmit
pnpm exec tsx --test scripts/*.test.ts
pnpm build
```

```text
tests 33
pass 33
fail 0
skipped 0
duration_ms 2268.0735
✓ built in 26.36s
```

独立parser目录执行：

```powershell
uv run --frozen python -m unittest discover -s tests -q
uv pip check --python .venv/Scripts/python.exe
```

```text
Ran 4 tests in 0.104s
OK
Checked 115 packages in 4ms
All installed packages are compatible
```

启停脚本验证：`pwsh -NoProfile -File globalmail-agent/scripts/test-local.ps1`，3项PASS：重复初始化保留设置摘要、端口占用拒绝、按自有PID及创建时间停止进程。全部使用自己的临时配置、进程和目录，不改正式设置。

## 真实解析：输入、输出及可说的结论

模型收到完整17页原PDF或完整4页合成样本；MinerU默认OCR自动模式，没有业务Agent提示、客户订单、参考回复或人工答案输入。这里测试“从材料提取文字、表格与位置”，不测试售后决策或最终回复。机器保存图像像素不代表读懂图中的操作含义。

| 实际输入与解析档位 | 输出 | 内容核对 |
|---|---|---|
| 17页`product-manuals-v1.pdf`，Basic | 完整17页、274块、26资产、8项人工图意核对提示；早期直接进程实测23.14秒，最终配置在真实worker中重跑 | 8份逻辑范围2–3、4–5、6–7、8–9、10–11、12–13、14–15、16–17逐份检查，块不越界；1个完整物理缓存共同引用，配置指纹与实际子进程一致 |
| 合成困难原生PDF4页，Basic | full=true、36块、2表，10.00秒 | 冻结样本21/21关键项、16/16表行，表头V/A及逐行型号/数值保留 |
| 同源合成扫描PDF4页，Basic | full=true、36块、2表，13.70秒 | 21/21关键项、16/16表行 |
| 同源合成扫描PDF4页，Standard | full=true、36块、2表，18.59秒 | 21/21关键项、16/16表行 |

17页原件SHA256：`d91001bbf34a5a0d217c4943cec3495b6352bd71ec81ba89a26c5f4e2b370265`。固定MinerU4.0.10/DocVortex0.5.9；15个权重共2,098,681,010字节，逐文件SHA核验。详细安全元数据与GUI响应在[证据数据](artifacts/phase5/results.json)。缓存完整原始输出留在运行对象存储，未把全部私有产物提交Git。

关键项包含断电、7秒、灯闪两次、焦味停止、禁止拆封闭控制器、90秒、仅接B、禁止桥接A/B及破壳停止；16行分别核对部件、12/24V、1.5/2.0A和对应型号。这是开发者自编且有已知答案的样本，不能据此宣称生产准确率或未见资料表现。未读取客户原图、完整场景故事、controller、evaluation或holdout替代材料；没有新调用付费模型或Embedding。

## 真实页面与故障路径

| 流程 | 实际结果与证据 |
|---|---|
| 准备资料导入 | POST202，22份原件/逻辑资料完成后全部needs_review、published=false；8份PDF共享完整17页物理解析，保留原时间/摘要/逻辑页号，普通修订不能扩大同源范围跨品牌。 |
| Markdown新建及人工核对 | 页面填写来源/时间/完整正文/型号依据；新建202、解析完成、核对200、reviewed且published=false；[原件对照](../../output/playwright/phase5-md-review.png)。 |
| 修订响应丢失与重试 | Playwright转发真实POST使服务先保存，再丢弃响应；错误显示输入保留。重试同key、同body均true，202，资料仅2版本；旧版核对保留、新版draft无核对；[真实差异](../../output/playwright/phase5-version-diff.png)。这是浏览器网络故障注入，服务实际处理与PG幂等断言均检查。 |
| 结构化政策修订 | 实际表单把退货窗口改45天、部分退款上限12.50%；保存202，同一版本规则为45/1250基点，中文说明一致，draft未发布；[政策页面](../../output/playwright/phase5-policy-version.png)。原场景政策引用及v1/v2文件不改。 |
| PDF原件及图片 | 树形书架原件第8–9页，32块/3资产仅在该范围；原页像素与规范块/图号同时可见，图片含义仍需人工；[实际页面](../../output/playwright/phase5-pdf-compare.png)。 |
| PDF取消/重试/替换 | 真实Basic任务取消202→重试202→attempt2 completed；2页换1页202，新范围[1,1]、SHA变化，旧版[1,2]及原件保留，新版无核对/未发布；[取消状态](../../output/playwright/phase5-cancelled-task.png)。增长、缩短、准备共享PDF独立替换另有4项PG→HTTP回归。 |
| 原件丢失或损坏 | 4项真实worker回归证明坏任务有限三次自动重试、记录安全错误并释放槽，健康资料完成；恢复精确原件后HTTP重试完成。命中缓存仍检查原件；旧原件不可用不阻挡新版本详情。人工核对提交重新核验原件，不能用旧摘要绕过。实际页面仍可读任务/失败原因和重试，下载原件返回503，[故障页面](../../output/playwright/phase5-source-fault.png)。 |
| 超时/取消/晚到/配置变化 | 真实子进程以0.25秒加速超时测试终止自己的进程树；生产限额900秒，不宣称等待完整15分钟或高负载验证。真实PG验证DB时钟、过期fence、取消/新版本/删除栅栏和提交途中租约失效时全部回滚；配置变化禁止旧缓存或旧子进程产物提交。 |

首轮两项缺陷（PDF旧页范围、JSON只改范围被迫填Markdown）和第二轮队首原件故障均保留FAIL报告，修复后新增可达反例再复审；没有将“全套绿”当作故障不存在。界面不执行Markdown/表格HTML、不抓链接，范围依据由维护者明确填写。

## 正式升级与收尾

执行`stop-local.ps1`及`start-local.ps1 -SkipInstall`，正式服务升级`0003_business_catalog`→`0004_knowledge_content`。只读核验原有32表行数和完整行摘要一致，运行设置SHA256不变，新增10张知识表，正式资料0份；没有导入准备包或测试资料。旧会话/业务表本身为空，这不作为已有真实客户资料迁移的证明。升级摘要见[证据数据](artifacts/phase5/results.json)。

`check-runtime.py`实际输出`status:passed`：API与前端代理各3项HTTP200，非法Host/Origin拒绝；本次未重启数据库，不宣称本轮重新验证数据库重启。正式运行Phase5、knowledge=true、agent=false，34 SKU与Basic/Standard两档实际可用，见[运行检查](artifacts/phase5/runtime-check.json)及[安全状态](artifacts/phase5/formal-runtime.json)。实际浏览器只读打开[正式知识页](../../output/playwright/phase5-formal-empty.png)，显示空库与未发布/Agent暂未接入。

本期测试会话、知识资料和原件仅在随机schema及私有临时目录中。实际关闭浏览器及隔离入口后，helper输出`Isolated processes/schema/object directory cleaned.`；只读确认本期schema为0、私有对象目录不存在、15174/18181均无监听，见[清理核验](artifacts/phase5/cleanup.json)。完整安全证据已归档。本轮`tmp/phase5-*`辅助文件及`tmp/phase5-parser`临时解析产物的批量删除、核对路径后的单目录删除均被自动审批拒绝，返回仅`blocked by policy`，因此仍保留，不改用其他命令绕过。真实模型缓存及安装环境保留供用户运行。正式知识入口：`http://127.0.0.1:15173/#/knowledge`，安装与模型检查见[本机运行](../../globalmail-agent/scripts/README.md)及[parser说明](../../globalmail-agent/parser-worker/README.md)。

AC-055/063只取得本期解析/位置/核对门证据，生产材料人工核对和Phase6切分/发布门仍未完成。其余发布/检索/Agent/删除AC按DEV-PLAN唯一主阶段保留；82项没有作整体验收，Phase1原业务失败结论不变。
