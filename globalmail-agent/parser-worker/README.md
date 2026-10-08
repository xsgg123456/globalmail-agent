# 本地知识解析进程

Phase 5 的解析适配器。API 的 Python 环境负责 Markdown/政策/受控 JSON 和 JSONL；PDF 在这里固定的 MinerU 4.0.10 / DocVortex 0.5.9 独立环境运行。`uv.lock` 固定依赖，不与 API SDK 混装。每次执行只收到受控原件路径，不继承数据库或模型 API 凭据。

从仓库根目录安装并核对已存在的模型：

```powershell
pwsh -File globalmail-agent/scripts/setup-parser.ps1
# 首次准备 Basic 本地模型（需要网络）
pwsh -File globalmail-agent/scripts/setup-parser.ps1 -DownloadModels
# Standard 另外需要 GGUF/mmproj，当前本机已有
pwsh -File globalmail-agent/scripts/setup-parser.ps1 -DownloadModels -Standard
```

默认复用已存在的 `tmp/knowledge-spike/mineru-home`；没有该目录时使用 `.local-data/parser-models`。通过服务端 `GLOBALMAIL_PARSER_HOME` 指定其他模型目录，目录下应有 `models/`。`GLOBALMAIL_PARSER_PYTHON` 可指定独立解析解释器。目录不存在、大小不符时页面如实显示档位不可用；执行前核对每个权重的 SHA-256，摘要不符则终止，不静默下载或换模型。下载后的远端文件若已经变化，同样拒绝继续。

`model-assets.json` 记录实际使用的 15 个文件、摘要与 2,098,681,010 字节。程序、权重、日志和缓存分别管理；源码许可见 [MinerU](licenses/mineru-LICENSE.md)、[DocVortex](licenses/docvortex-LICENSE.md)。权重来源见 [官方模型来源](https://opendatalab.github.io/MinerU/usage/model_source/)、[ONNX 模型仓库](https://modelscope.cn/models/OpenDataLab/MinerU-4_models_onnx)、[GGUF 原仓库](https://modelscope.cn/models/42ailab/MinerU2.5-Pro-2605-1.2B-GGUF)。权重不纳入 Git，不将应用代码许可冒充模型许可。

PDF 最多 50 MiB / 300 页。后台每 15 秒续租，知识槽租约 90 秒；15 分钟超时或取消/过期后只终止本次子进程树。来源摘要、解析档位、适配代码与模型清单共同决定缓存；配置变化须重新解析。完整物理解析和原始中间结构保存为内部对象，逻辑资料按原件页码范围投影，共享 PDF 不重复解析。

解析返回页码、章节、正文、表格、图号和位置；页预览/图片由原 PDF 像素生成。缺页、缺图、非法结构阻止核对。图片像素已保存仍需人核对操作含义；缺关键图时须补齐或明确排除整个相关章节。核对成功仅到 `reviewed`，没有发布、向量或 Agent 可用状态。

```powershell
cd globalmail-agent/parser-worker
uv run --frozen python -m unittest discover -s tests -q
uv pip check --python .venv/Scripts/python.exe
```
