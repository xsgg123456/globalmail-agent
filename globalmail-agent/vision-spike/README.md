# 客户图片图文风险实验

Phase 1 的独立实验，不是正式工作台或业务Agent。沿用 `../tech-spike/uv.lock` 对应 Python 3.12、Pillow 12.3.0、OpenAI 3.26.0、Pydantic 2.13.5 环境；不安装独立OCR、不升级模型。

从仓库根目录执行（PowerShell）：

```powershell
$visionPython = 'tmp/tech-selection/venv/Scripts/python.exe'
& $visionPython globalmail-agent/vision-spike/build_fixtures.py
& $visionPython globalmail-agent/vision-spike/validate_fixtures.py
& $visionPython -m unittest discover -s globalmail-agent/vision-spike -p 'test_*.py' -v
& $visionPython globalmail-agent/vision-spike/probe_vision.py --run my-new-run --rounds 3 --workers 1
Copy-Item data/visual/v1/evaluation/labels.jsonl tmp/vision-spike/my-new-run/labels.jsonl
& $visionPython globalmail-agent/vision-spike/evaluate_results.py --run my-new-run
& $visionPython globalmail-agent/vision-spike/write_business_review.py --run my-new-run
& $visionPython globalmail-agent/vision-spike/archive_evidence.py
```

探针只连接已有 `.env` 配置中的百炼北京端点与 qwen3.7-plus；不显示密钥。实际调用会产生供应商用量。run目录必须全新，失败和中断保留旧记录，不能复用绿色结果。进程启动保存输入、提示和源码摘要；标签由评估侧单独复制，模型程序不打开标签。中断时除汇总外，逐案例journal保留已返回请求；尚在供应商执行的请求费用可能未知。

默认案例串行；`--workers 3` 仅让三个独立合成实验并发，各案例内部三轮串行，全图与裁剪共用单轮预算。正式Agent仍按架构单槽。实验无业务写工具，所以12工具额度消耗为0，不代表真实工具网关已验证。

输入预处理：校验scope/序号/撤销/摘要/实际格式/静态帧，单封4图、单张10MiB/20百万像素、合计20MiB；方向校正，最长边1280、像素≤1,048,576。首轮全图，固定900×450左上裁剪作密集截图对照，保留坐标及摘要。Laplacian方差<1提示极低细节，只是保守开发诊断，不是OCR或可靠通用模糊检测器。

每轮最多6请求/6视图/120秒、单次16k输入/2k输出、累计80k，SDK重试关闭，单次网络timeout30秒。文本/Schema UTF-8字节加视觉像素上限及余量作保守预留；实际usage逐次结算，缺失或请求失败保持未知并保留占用，不按base64长度算视觉tokens。HTTP timeout是SDK传输超时，正式worker仍需活动时间/提交栅栏；此实验不证明完整事务时限。

结果原文与请求摘要保存在忽略的 `tmp/vision-spike/<run>/`，无base64输出。提交仓库的摘要另行去除正文；[中文审阅页](../../data/visual/v1/review.html)仅含本项目合成材料。自动评估按字段/观察/路由/安全检查分别报告，危险/越权错误不能被平均分抵消；规则检查不替代逐例语义和用户业务核对。

运行记录与边界见 [VISUAL-VALIDATION](../../docs/verification/VISUAL-VALIDATION.md)。初次数组失败、模糊误读和初审报告均保留；人工标签确认及产品AC均不得由脚本自动勾选。

当前final-v5完成108次，存在9条独立审阅发现的关键业务错误，Phase 1验收未通过。中文页仅在结果SHA一致时展示独立语义审阅；`semantic-review-v4/v5`是Agent审阅，不是人工确认。独立代码审查见[review-close.md](review-close.md)，未通过时不设置clean或提交完成状态。
