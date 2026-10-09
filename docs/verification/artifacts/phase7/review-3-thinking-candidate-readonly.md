# 有界核验模式候选的只读契约评估

2026-10-08。当前未实施、未付费、未改变产品非thinking配置；H12/H13开放，Stage 2未执行。本文件不批准模式切换。DEV-PLAN:348当期明确enable_thinking=false，若主Agent提出仅validation切换，须先取得用户对该契约变化的授权，不能将审查者的参数可行性判断充当授权。

官方[Chat Completions参数](https://help.aliyun.com/en/model-studio/qwen-api-via-openai-chat-completions)将max_completion_tokens定义为推理与答案的合计输出，支持Qwen Plus3.5及以后，并提示实际计数可能最多偏差10。候选1990可为原2000门留此容差。thinking_budget通过extra_body提供，仅限制推理部分，不是总输出预算；不能用thinking_budget=512再额外给答案2000或在账中扣除推理。官方usage的completion/text计数已含推理，reasoning_tokens是其子集。

官方[结构化输出](https://help.aliyun.com/en/model-studio/qwen-structured-output)列出Qwen3.7-Plus支持JSON Schema，包含thinking结构化输出说明；这支持机制候选的接口可行性，不保证本案条件/译名负例会正确。官方[深度思考](https://help.aliyun.com/en/model-studio/deep-thinking)说明thinking_budget超限后转答案；512上限与原总1990并不保证剩余空间足够完整逐项JSON，也不能保证30秒内完成。

本地`backend/src/globalmail_agent/agent/budget.py:38/60/79`原预留input+2000、按实际completion_tokenssettle并保留unknown已适合总输出计账，不能再另加推理或视为免费。Provider当前没有该候选参数，不能据现有非thinkingSDK测试说thinking通过。若获准落地，阶段区分应显式且可测试：仅validation启用，Understanding/decision保持当期配置；实际返回finish=length、超2k、未知usage及超时均沿原安全失败规则，不追加第7请求修补。

`agent-eval/recording.py:21`当前SDK捕获allowlist没有max_completion_tokens；未来候选审计须明确捕获这个实发字段以及extra_body.thinking_budget，事前freeze并比较原messages/schema/完整资料全等。最终公开证据仅需配置/usage/count/hash和语义判读，不把内部推理全文当业务证据或客户内容。独立候选预算预检、具体SDK测试及actual原负稿必须分别提供，当前没有任何模式质量实测。
