"""Safe log metadata. Never copy provider exceptions, model reasoning or raw bodies."""
ALLOWED = {"run_id", "stage", "status", "reason_code", "tool_name", "attempt_no", "request_id"}


def safe_summary(values):
    return {key: value for key, value in values.items() if key in ALLOWED
        and isinstance(value, (str, int, bool)) and len(str(value)) <= 160}
