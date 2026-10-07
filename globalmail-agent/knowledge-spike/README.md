# 知识管线专项验证

日期：2026-10-07。输入依据：Product-Spec v1.10、KNOWLEDGE-DESIGN v1.0。这里只实现隔离的可复跑实验，不作为正式知识服务或产品验收。

## 本轮规划和完成标准

1. 建立独立解析环境并锁定依赖。MinerU 与原技术探针分开安装，原件/已有结果不改写；安装失败必须保留实际原因。
2. 比较 PDF 解析。使用现有 17 页产品 PDF 和有明确答案的困难样本，记录页覆盖、SKU、图表/步骤、原件位置、耗时和资源；渲染检查样本，不把“命令成功”当作内容正确。
3. 实现结构与适用范围优先的切分实验。Markdown 保留层级，SOP 子块保留前提/停止条件，图文/政策与同版来源关联；比较不同切分初值。
4. 扩展至少 60 条开发查询，调用真实 Embedding，分别报告证据召回、越界过滤、多证据和无答案行为；对照新模型，不可用时记录错误而非静默替换。
5. 用隔离 PostgreSQL 验证发布、更新失败保旧版、回滚、下架、迟到任务和向量索引切换的最小契约；不宣称已实现 UI、完整清理/备份或生产服务。
6. 编译、必要回归测试及 fresh code-reviewer 审查；修复后复核，汇总实测边界并更新知识方案中的选型结论。

## 数据与隔离

- 只读取 data/knowledge/v1 的已审读知识和已标注开发查询；不读取原始客户邮件或 eval_holdout。
- 本轮新增查询及困难样本全部属于开发数据，不能宣称独立测试或生产准确率。
- 运行目录为 Git 忽略的 tmp/knowledge-spike；MinerU 模型、缓存、解析图片与向量保存在该目录。
- 报告不得包含 Key、连接密码、未经筛选的异常响应或客户个人信息。
- 所有报告在开始时写入 running 状态，失败写入失败阶段；不得留下误导性的旧通过结果。

## 实测结果

结论见 [KNOWLEDGE-VALIDATION.md](../../docs/verification/KNOWLEDGE-VALIDATION.md)。MinerU Basic 推荐用于复杂/扫描 PDF；短 SOP/案例优先完整保留，长文按结构切块，检索后按父文档去重并复核适用范围；qwen3.7-text-embedding 1024 维推荐为下一阶段主候选，v4 为独立模型空间的回退配置。

- pypdf、MinerU Flash/Basic：现有 17 页说明书和两份 4 页困难样本已比较；Standard 额外比较两份困难样本。Basic/Standard 的两个困难样本均覆盖 21/21 关键项、16/16 表行，Basic 本次耗时更低。
- 60 条冻结开发查询：36 正例、12 边界、6 无答案、6 多证据，英德各 30 条。双模型、4 档切分均实测。300/500 目标的实际块内容一致，不能据此选最优长度。
- 按文档去重、短父文档补全后，两模型都覆盖 36 正例和 6 多证据，12 边界始终为空。小候选库及开发调参结果不能代替独立准确率。
- 固定 18 条真实模型证据检查由初版 13/18 调整到 18/18，包含 6 条无答案；只验证证据充分性和逐字引用，不是完整回复验收。
- 临时 PostgreSQL 实测 7 组生命周期检查和 8 项契约测试，包括真实双模型切换、失败保旧、回滚、下架、晚到任务和数据库删除栅栏。正式对象/隐私删除、worker、UI、政策捆绑发布、备份恢复不在本实验内。

## 环境与依赖

Windows / Python 3.12.10，独立环境 `tmp/knowledge-spike/mineru-venv`。`mineru-requirements.lock` 固定 115 个安装版本，包含 MinerU 4.0.10、Docvortex 0.5.9、OpenAI SDK 2.54.0；不与旧 tech-spike 的 SDK 3.x 混装。合成 PDF 生成脚本使用 Windows 的微软雅黑字体。需要 uv、Docker Desktop；Standard 本机使用 llama.cpp 后端和 RTX 5060 Ti。

以下命令从仓库根目录执行，全部输出位于本地实验目录。安装和模型下载需要网络；模型许可按所锁版本核对。约 2.10 GB 模型文件的路径、字节数及 SHA-256 在 `model-assets.json`，不把权重纳入 Git。

```powershell
uv venv --python 3.12.10 tmp/knowledge-spike/mineru-venv
uv pip install --python tmp/knowledge-spike/mineru-venv/Scripts/python.exe -r globalmail-agent/knowledge-spike/mineru-requirements.lock
$env:PYTHONUTF8='1'
$env:MINERU_HOME=(Join-Path $PWD 'tmp/knowledge-spike/mineru-home')
$env:MINERU_MODEL_SOURCE='modelscope'
& tmp/knowledge-spike/mineru-venv/Scripts/mineru-kit.exe models download --tier basic --small-backend onnx --source modelscope
& tmp/knowledge-spike/mineru-venv/Scripts/mineru-kit.exe models download --tier standard --small-backend onnx --vlm-engine llama-cpp --source modelscope
Invoke-WebRequest -Uri 'https://modelscope.cn/models/Qwen/Qwen3-Embedding-0.6B/resolve/master/tokenizer.json' -OutFile tmp/knowledge-spike/qwen3-tokenizer.json
```

tokenizer 仅用于代理计数，托管模型一致性未确认。来源或模型更新时需重新核对摘要和结果，不能将同名远端文件视为不可变资产。`chunking-results.json` 记录实际 tokenizer 内容摘要。

## 按依赖顺序复跑

原输入是 `output/pdf/product-manuals-v1.pdf` 与 `data/knowledge/v1` 允许的知识。不要调用原始客户资料刷新脚本；不要把 eval_holdout 加进实验。首次运行 API 阶段需要根目录已忽略的 `.env` 中配置 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`；端点限定北京百炼 HTTPS，结果只保存安全元数据。

```powershell
$experimentPython=Join-Path $PWD 'tmp/knowledge-spike/mineru-venv/Scripts/python.exe'
$experimentCode=Join-Path $PWD 'globalmail-agent/knowledge-spike'
& $experimentPython "$experimentCode/build_fixtures.py"
& $experimentPython "$experimentCode/probe_parsing.py"
& $experimentPython "$experimentCode/probe_parsing.py" --parsers mineru-standard --sources difficult-native.pdf difficult-scanned.pdf --standard-report
& $experimentPython "$experimentCode/chunking.py"
& $experimentPython "$experimentCode/probe_retrieval.py"
& $experimentPython "$experimentCode/probe_evidence.py"
& $experimentPython "$experimentCode/probe_lifecycle.py"
& $experimentPython -B -m unittest discover -s $experimentCode -p 'test_*.py' -v
uv pip check --python $experimentPython
```

逐条执行并检查退出码，某步失败先处理原因，再运行依赖它的步骤。`probe_lifecycle.py` 自建回环端口、带所有权标签的临时数据库并清理；不要使用业务数据库。普通 unittest 有 5 项 DB 测试按设计跳过，必须另跑 lifecycle 入口，完整 8 项契约测试无跳过才算数据库验证通过。

PDF 生成后查看 `tmp/knowledge-spike/fixture-preview.png`，确认四页布局再接受解析分数。页面文字命中不证明真实产品图片或操作语义正确。

向量缓存由端点、模型、维度、输入格式及完整输入寻址；复跑可能不再产生 API 消耗。成功检索报告的 run_id、当前源/查询/块摘要与产物摘要必须一致，两个下游入口才允许读取。父正文还会独立核验版本、正文摘要及适用范围。上游失败、资料修改后未重新切块、或旧中间结果混入都会拒绝继续。当前实验没有并发运行编排；每次按上述顺序串行复跑。

## 证据文件

| 文件 | 用途 |
|---|---|
| parsing-results.json / parsing-standard-results.json | 解析覆盖、耗时、进程内存及已知缺失 |
| chunking-results.json | 四档块数、代理 tokens 及摘要 |
| retrieval-queries.jsonl / query-set-notes.md | 冻结开发标签与来源限制 |
| retrieval-initial-results.json | 首次真实调用的 usage/耗时原件；保留不覆盖 |
| retrieval-results.json | 当前复跑的排序、输入快照与各中间产物摘要 |
| evidence-initial-results.json / evidence-results.json | 旧提示与修订提示的 18 条检查，保留开发调整轨迹 |
| lifecycle-results.json | 实际数据库七组检查、八项测试及资源清理 |
| review-notes.md | 首次独立审查及修复前反例，保留历史 |
| review-final.md | 修复后 fresh 独立复核；三项问题关闭，本轮实验 PASS |
| verification-results.json | 修复后编译、测试计数、上游输入复核、源码与证据摘要 |

运行临时数据不随 Git 分发；新环境先生成它们再运行离线测试。正式验收必须新增独立数据和业务端到端运行，不能把本实验成功计作 Product-Spec AC 全部完成。
