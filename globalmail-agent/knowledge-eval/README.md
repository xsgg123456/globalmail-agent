# Phase 6 实际检索评测

使用固定22份准备资料、生产解析/切分/任务/发布/检索服务、真实Embedding和PG精确余弦。全部写入随机schema与私有对象目录，结束自动清理；不发布用户正式资料，不调用对话模型、Agent或邮箱。

根目录执行（需已安装本机PG、API与独立parser）：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='globalmail-agent/backend/src;globalmail-agent/backend/tests;globalmail-agent/knowledge-eval'
globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/knowledge-eval/evaluate_retrieval.py
```

服务端配置由`provider_config.py`私下读取根`.env`与本机数据库设置，不输出凭据。可预先设置专用`GLOBALMAIL_TEST_DATABASE_URL`。正式库尚无vector扩展时，不要与其他PG测试/隔离页面同时运行。

`query-freeze.json`冻结原60条开发查询与新增12条的字节摘要，脚本先检查再执行。查询的预期证据包含文档ID和正文关键内容，统计最多5份父证据是否覆盖。作者知道材料内容，新增查询不是独立业务留出集；缺事实时找到相关资料也不能证明会拒答或最终答案正确。未覆盖图意的阻断块明确排除，本轮只验文本检索。

`provider-results.json`记录真实供应商探针，`retrieval-results.json`记录最终构建/查询、token用量和时延；`retrieval-progress.json`是运行中的阶段产物。完整范围和结论由`docs/verification/PHASE-6-VALIDATION.md`说明。查询失败也保留，不能回改标签把失败抹掉。

`retrieval-progress-initial.json`保留首轮40条后遇到旧历史模式的脚本中断；`retrieval-results-policy-1.0.json`保留旧说明完整72条的实际未通过结果（含返回全文）。独立审查确认其中存在真正缺失的政策前提，生产生成器修为1.1后才重新运行。查询和原句检查不变，没有用同义打分覆盖原失败。

最终生成器1.1/切分structure/4结果：44/44单项正例、多项5/6完整（11/12项依据）、16/16边界无证据；单项及多项合计49/50完整。KQ-058的政策片段仍漏一项，全文及原标签保留。6条缺事实查询返回相关资料，不代表最终回答正确或会拒答。模型、用量、上限与局限详见验证记录。
