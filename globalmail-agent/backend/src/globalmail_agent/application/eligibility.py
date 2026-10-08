"""Read-only policy preview; all identity, evidence and versions come from queries."""
from globalmail_agent.domain.policy import EligibilityRequest, evaluate_eligibility


class EligibilityService:
    def __init__(self, engine):
        from globalmail_agent.application.business_queries import BusinessQueries
        self.queries = BusinessQueries(engine)

    def preview(self, conversation_id, command: EligibilityRequest):
        context = self.queries.eligibility_context(conversation_id, command.order_line_id)
        if context["status"] != "ok":
            return context
        data = context.get("data") or {}
        if not data.get("policy"):
            return {**context, "status": "unavailable", "reason_code": "policy_unavailable",
                    "data": None, "retryable": False}
        try:
            decision = evaluate_eligibility(command, data)
        except (KeyError, TypeError, ValueError):
            return {**context, "status": "unavailable", "reason_code": "policy_context_incomplete",
                    "data": None, "retryable": False}
        return {**context, "status": "ok", "reason_code": "eligibility_preview", "data": decision,
                "retryable": False}
