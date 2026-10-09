# 第七轮独立证据

本目录逐字节复制自 reviewer 自有 `tmp/phase8-review7*` 文件及 `tmp/phase8-review7/`。`evidence-sha256.json`记录复制时字节SHA；`current-source-audit.json`是最后独立重算的源码SHA。脚本以原tmp目录/仓库根定位，复跑应先恢复原 `tmp/phase8-review7*` 路径，且重新建立隔离schema/对象目录和无worker服务；不能在正式库复跑。UI cid/attachment_id 是本轮已清理的私有测试身份，不能用于今后的数据。

- `phase8-review7-tests.txt`：27项现有生产路径测试和1项自写HTTP测试首次执行。自写测试带一项无关Graph调用的 `agent_dependency_error`诊断；报告没有把此调用判为Graph通过。
- `phase8-review7-thumbnail-tests.txt`、`thumbnail-tests.json`：移除无关调用、明确人工接管后，EXIF真实缩略字节/越域404/原图与缩略410的干净重跑。当前脚本对应此重跑。
- `phase8-review7-ui-finish.txt`/`ui-finish.json`：实际浏览器加载512px缩略、渲染112×80、长文件名、thumbnail503与原图实际800px解码、证据200。
- `phase8-review7-ui-revoke.txt`/`ui-revoke.json`：真实UI接管/确认撤销后DOM图片0、filename禁用、410/no-store。脚本内HTTP字段名original请求没有thumbnail参数，接口默认true，因此该字段是默认preview410；显式 `thumbnail=false`原图410由上述独立TestClient重跑证明。原始日志保持原样，不改标签掩盖此差异。
- `neighbor-knowledge-real.png`、`neighbor-system-real.png`是另行CLI截图并实际查看的邻居渲染。最早 `neighbor-knowledge.png`/`neighbor-system-status.png`在过渡期截图空白，原始文件保留但不作为视觉通过依据。
- timeline使用现有独立纵向滚动区域，固定composer占用下截图可有纵向裁切；报告没有声称整卡始终可见。实际图像自然尺寸/渲染尺寸与HTTP真实解码均有数值证据。
- 独立前端55/0skip、项目vue-tsc+Vite28.35秒、backend compileall0原始输出原样保留。实际模型语义不在这些工程证明内。

本目录只保存本轮审查材料，未改前六轮结论。服务/schema/对象目录由主Agent唯一所有者清理，reviewer自有Playwright session已关闭。
