"""A proposal reserves affected units; execution alone reserves ERP stock."""
from globalmail_agent.domain.policy_ledger import units_for


def selected_units(command, line):
    return units_for({"quantity": command.quantity, "affected_unit_ids": command.affected_unit_ids}
        if command.affected_unit_ids is not None else {"quantity": command.quantity}, line)


def refundable_balance(operations, executions):
    succeeded = reserved = 0
    for operation in operations:
        if operation.get("kind") != "refund":
            continue
        linked = [e for e in executions if e.get("operation_id") == operation["operation_id"]]
        if any(e.get("status") == "succeeded" for e in linked):
            succeeded += operation["amount_minor"]
        elif operation.get("status") != "cancelled" and not operation.get("confirmed_not_executed"):
            reserved += operation["amount_minor"]
    return succeeded, reserved
