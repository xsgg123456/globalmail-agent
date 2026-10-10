"""Default runtime exposes reads and internal proposals, never commercial writes."""
BLOCKED = {"check_after_sales_eligibility", "create_after_sales_operation", "cancel_after_sales_operation"}


def after_sales_stage(state, context):
    return set(), False


def stage_tools(tools, state, context):
    return [tool for tool in tools if tool['function']['name'] not in BLOCKED], False


def decision_menu(state, context, budget, messages):
    from globalmail_agent.agent.tool_schemas import schemas
    from globalmail_agent.agent.budget import input_estimate
    internal = context.payload.get("execution_mode") == "human_assist"
    terminals = {"request_human_review"} if internal else {"create_reply_draft", "request_human_review"}
    candidates = state["understanding"]["order_candidates"] or any(
        i["order_number"] for i in state["understanding"]["intents"])
    allowed = None if candidates or context.payload.get("verified_business_observations") else (
        terminals | {"get_case_context", "update_case_state", "revise_understanding"})
    def menu(names):
        tools = schemas(names, multiple_waits=False)
        return [t for t in tools if not (internal and t["function"]["name"] == "create_reply_draft")]
    tools = menu(allowed)
    remaining = budget.remaining_requests()
    if remaining <= 1:
        return menu({"request_human_review"})
    if remaining <= 2:
        return menu(terminals)
    if input_estimate(messages, tools) > 16000:
        tools = menu({t["function"]["name"] for t in tools} - {
            "get_case_context", "update_case_state", "revise_understanding"})
    if input_estimate(messages, tools) > 16000:
        tools = menu(terminals)
    if input_estimate(messages, tools) > 16000:
        tools = menu({"request_human_review"})
    return tools
