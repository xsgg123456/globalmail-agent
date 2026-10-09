"""Integer balances and cross-issue compensation checks; no database writes."""
from globalmail_agent.domain.policy_conditions import integer, reference, TRUSTED_KINDS

ACTIVE = {"accepted", "pending", "processing", "submitted", "waiting", "waiting_condition", "awaiting_execution", "unknown", "result_unknown"}
SUCCESS = {"succeeded", "completed", "shipped"}
TERMINAL = {"failed", "cancelled", "canceled", "rejected"}
COMPENSATING = {"refund", "replacement", "spare_part"}


def units_for(record, line):
    quantity = record.get("quantity")
    if not integer(quantity, 1) or quantity > line["quantity"]:
        return None
    allocations = line.get("unit_allocations", [])
    universe = {row.get("unit_id") for row in allocations} if allocations else {
        str(i) for i in range(line["quantity"])}
    supplied = record.get("affected_unit_ids")
    if supplied is not None:
        if not isinstance(supplied, list) or any(not isinstance(value, str) for value in supplied):
            return None
        values = set(supplied)
        return values if len(values) == len(supplied) == quantity and values <= universe else None
    return universe if quantity == line["quantity"] else None


def trusted(record):
    return record.get("source_kind") in TRUSTED_KINDS and reference(record) and record.get("verified") is not False


def ledger(checks, state, line, currency, selected_units, action, order):
    if not integer(line.get("paid_minor")) or not integer(line.get("quantity"), 1):
        return None
    operations = [row for row in state.get("operations", [])
        if row.get("order_line_id") == line["line_id"]]
    execution_records = state.get("execution_records", [])
    total, succeeded_amount, reserved_amount, refs, conflicted = 0, 0, 0, [], False
    seen = set()
    for operation in operations:
        key = operation.get("operation_id")
        if not isinstance(key, str) or not key or key in seen:
            checks.add("compensation_ledger", "操作编号缺失或重复，需核对账本", "requires_review")
            return None
        seen.add(key)
        executions = [row for row in execution_records if row.get("operation_id") == key]
        if not trusted(operation) or any(not trusted(row) for row in executions):
            checks.add("compensation_ledger", "补偿记录必须来自已核验业务账本", "requires_review")
            return None
        kind, status = operation.get("kind") or operation.get("action"), operation.get("status")
        if kind not in COMPENSATING:
            continue
        succeeded = [row for row in executions if row.get("status") == "succeeded"]
        occupying = (status in ACTIVE or status == "failed" and operation.get("confirmed_not_executed") is not True
            or any(row.get("status") in ACTIVE or row.get("status") == "failed" and
                row.get("confirmed_not_executed") is not True for row in executions))
        completed = bool(succeeded) or (kind != "refund" and status in SUCCESS)
        if status not in ACTIVE | SUCCESS | TERMINAL:
            checks.add("compensation_ledger", "已有操作状态未知，先核对原操作", "wait", [operation])
            occupying = True
        if kind == "refund" and status in SUCCESS and not succeeded:
            checks.add("compensation_ledger", "已完成退款缺少关联成功执行回执", "requires_review")
            return None
        if status in TERMINAL and status != "failed" and occupying:
            checks.add("compensation_ledger", "取消或失败记录仍有处理中执行，须对账", "requires_review")
            return None
        if status in TERMINAL and completed:
            checks.add("compensation_ledger", "失败或取消申请仍有成功执行，须对账", "requires_review")
            return None
        if not completed and not occupying:
            continue
        refs += [operation, *executions]
        if kind == "refund":
            amount = operation.get("amount_minor")
            amounts = [row.get("amount_minor") for row in executions
                if row.get("status") in ACTIVE | {"succeeded"}]
            if (not integer(amount) or operation.get("currency") != currency
                    or any(not integer(value) or value != amount for value in amounts)
                    or any(row.get("currency") != currency for row in executions
                           if row.get("status") in ACTIVE | {"succeeded"})):
                checks.add("compensation_ledger", "退款金额或币种不一致，禁止自动换汇", "requires_review")
                return None
            # Multiple attempts represent one operation, never amount per execution row.
            total += amount
            if completed:
                succeeded_amount += amount
            else:
                reserved_amount += amount
        units = units_for(operation, line)
        if action in COMPENSATING and (units is None or selected_units is None or units & selected_units):
            conflicted = True
            checks.add("compensation_conflict", "同订单行份额已有补偿，先查原操作或澄清方案",
                       "wait" if occupying and not completed else "requires_review", [operation])
    if any(row.get("operation_id") not in seen for row in execution_records
           if row.get("order_line_id") == line["line_id"]):
        checks.add("compensation_ledger", "存在未关联申请的执行记录", "requires_review")
        return None
    if total > line["paid_minor"]:
        checks.add("compensation_ledger", "退款和占用超过订单行实付，须对账", "requires_review")
        return None
    aggregate = (order.get("refunded_minor"), order.get("pending_refund_minor"))
    if any(not integer(value) for value in aggregate):
        checks.add("compensation_ledger", "订单退款汇总字段未知，需核对记录完整性", "requires_review")
        return None
    if order.get("line_count") == 1:
        if aggregate != (succeeded_amount, reserved_amount):
            checks.add("compensation_ledger", "订单汇总与关联退款账本不一致，须对账", "requires_review")
            return None
    elif any(aggregate) and not all(integer(line.get(key)) for key in ("refunded_minor", "pending_refund_minor")):
        checks.add("compensation_ledger", "多商品退款汇总不能摊到此订单行", "requires_review")
        return None
    if any(key in line for key in ("refunded_minor", "pending_refund_minor")) and (
            line.get("refunded_minor"), line.get("pending_refund_minor")) != (succeeded_amount, reserved_amount):
        checks.add("compensation_ledger", "订单行退款汇总与账本不一致", "requires_review")
        return None
    if not conflicted:
        checks.add("compensation_ledger", "已跨事项核对同订单行补偿", records=refs or [line])
    return line["paid_minor"] - total
