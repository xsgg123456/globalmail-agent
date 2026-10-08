"""Window, warehouse, address and stock conditions from verified server context."""
from datetime import timedelta
from globalmail_agent.domain.policy_conditions import date, integer, reported_problem
from globalmail_agent.domain.policy_ledger import units_for


def window(checks, order, as_of, days):
    delivered, now = date(order.get("delivered_at")), date(as_of)
    if not delivered or not now:
        return checks.add("delivery_date", "缺可信签收时间或查询截点", "needs_input")
    if not checks.evidence("delivery_date", order, "签收时间"):
        return False
    if delivered > now:
        return checks.add("delivery_date", "签收时间晚于当前截点", "requires_review")
    if now > delivered + timedelta(days=days):
        return checks.add("delivery_date", "已超政策窗口，需人工审查例外", "requires_review")
    return checks.add("delivery_date", f"在签收后{days}天窗口内", records=[order])


def warehouse(checks, state, line, units, quantity):
    rows = [row for row in state.get("returns", [])
        if (row.get("order_line_id") or row.get("line_id")) == line["line_id"]]
    if not rows:
        checks.add("warehouse_receipt", "等待仓库收件回执", "wait")
        checks.add("warehouse_inspection", "等待仓库质检回执", "wait")
        return
    received, inspected = [], []
    receipt_units, inspection_units = set(), set()
    for row in rows:
        if not checks.evidence("warehouse_receipt", row, "仓库收件回执", "wait"):
            continue
        if row.get("received") is not True:
            continue
        row_units = units_for(row, line)
        if not integer(row.get("quantity"), 1) or row_units is None:
            checks.add("warehouse_receipt", "收件数量或受影响份额不明确", "needs_input")
            continue
        received.append(row)
        receipt_units |= row_units
        if row.get("inspection") != "passed":
            if row.get("inspection") in ("disputed", "failed", "rejected"):
                checks.add("warehouse_inspection", "仓库验收有争议或未通过", "requires_review", [row])
            continue
        if not checks.evidence("warehouse_inspection", row, "仓库质检回执", "wait"):
            continue
        inspected_quantity = row.get("inspected_quantity", row["quantity"])
        inspection_record = {**row, "quantity": inspected_quantity}
        if "inspected_unit_ids" in row:
            inspection_record["affected_unit_ids"] = row["inspected_unit_ids"]
        inspected_units = units_for(inspection_record, line)
        if (not integer(inspected_quantity, 1) or inspected_quantity > row["quantity"]
                or inspected_units is None or not inspected_units <= row_units):
            checks.add("warehouse_inspection", "质检合格数量须明确覆盖对应收件份额", "needs_input")
            continue
        inspected.append(row)
        inspection_units |= inspected_units
    checks.add("warehouse_receipt", "仓库已收到此次受影响份额" if units and units <= receipt_units else
        "收件数量尚未覆盖此次受影响份额", "fulfilled" if units and units <= receipt_units else "wait", received)
    checks.add("warehouse_inspection", "仓库质检已覆盖此次受影响份额" if units and units <= inspection_units else
        "等待覆盖此次受影响份额的质检", "fulfilled" if units and units <= inspection_units else "wait", inspected)


def address(checks, state, choice, order):
    row = state.get("address_confirmation", {})
    if not checks.evidence("address", row, "当前地址确认"):
        return
    confirmed = (row.get("confirmed") is True and integer(row.get("version"), 1)
        and choice is not None and integer(choice.get("address_version"), 1)
        and choice["address_version"] == row["version"] and row.get("market") == order.get("market"))
    if row.get("source_kind") == "customer_statement":
        confirmed = confirmed and row.get("source_message_id") in state.get("visible_source_message_ids", [])
    checks.add("address", "客户当前选择与已确认地址版本一致" if confirmed else
        "须确认此次选择使用当前地址版本", "fulfilled" if confirmed else "needs_input", [row] if confirmed else [])


def availability(checks, context, line, order, command):
    item = command.item_id or (line.get("sku") if command.action == "replacement" else None)
    if not item:
        checks.add("compatibility", "需要准确商品或部件编号", "needs_input")
        return
    state, product = context["state"], context.get("product") or {}
    if command.action == "spare_part":
        part = next((row for row in context.get("parts", []) if row.get("part_id") == item), None)
        if not part:
            checks.add("compatibility", "未找到准确配件登记", "requires_review")
            return
        if part.get("safety_critical") is True or part.get("customer_replaceable") is False:
            checks.add("safety", "安全关键部件须人工审查", "requires_review", [part])
        matches = [row for row in context.get("compatibility", [])
            if row.get("part_id") == item and row.get("sku") == line.get("sku")
            and row.get("hardware_revision") == line.get("hardware_revision")]
        mapping = matches[0] if len(matches) == 1 else None
    else:
        if item != line.get("sku"):
            checks.add("compatibility", "替代型号须核对兼容并经人工审查", "requires_review")
            return
        mapping = product if product.get("sku") == item else None
    if mapping and checks.evidence("compatibility", mapping, "准确适配"):
        market = mapping.get("market") or mapping.get("region_spec")
        hardware = mapping.get("hardware_revision") or mapping.get("simulation_hardware_revision")
        if not market or market != order.get("market") or hardware != line.get("hardware_revision"):
            checks.add("compatibility", "缺准确地区或硬件版本适配依据", "requires_review")
        elif mapping.get("status") in ("incompatible", "not_compatible"):
            checks.add("compatibility", "准确适配记录显示不兼容", "ineligible", [mapping])
        else:
            checks.add("compatibility", "准确SKU、地区和硬件版本适配", records=[mapping])
    elif not mapping:
        checks.add("compatibility", "缺准确SKU和硬件版本适配记录", "requires_review")
    stock = [row for row in state.get("inventory", []) if row.get("item_id") == item]
    if len(stock) != 1:
        checks.add("inventory", "当前可用库存未知", "needs_input")
        return
    row = stock[0]
    if not checks.evidence("inventory", row, "可用库存"):
        return
    snapshot, now = date(row.get("snapshot_at")), date(context.get("as_of"))
    if not snapshot or not now or snapshot > now:
        checks.add("inventory", "库存快照时间缺失或晚于当前截点", "needs_input")
        return
    on_hand, reserved = row.get("on_hand"), row.get("reserved")
    if not integer(on_hand) or not integer(reserved) or reserved > on_hand:
        checks.add("inventory", "库存数量无效或预留需对账", "requires_review")
        return
    if (row.get("market") or row.get("region_spec")) != order.get("market") or row.get("hardware_revision") != line.get("hardware_revision"):
        checks.add("inventory", "缺当前地区和硬件规格库存依据", "needs_input")
        return
    checks.add("inventory", "当前库存可用" if on_hand - reserved >= command.quantity else
        "当前库存不足，等待补货或客户另选方案", "fulfilled" if on_hand - reserved >= command.quantity else "wait", [row])


def return_conditions(checks, state, line):
    problem = reported_problem(checks, state, line, ("defect", "unwanted"))
    if problem and problem.get("reason") == "unwanted":
        row = state.get("return_condition", {})
        if checks.evidence("return_condition", row, "非质量退货完整性"):
            okay = row.get("unused") is True and row.get("complete") is True
            checks.add("return_condition", "未使用且完整" if okay else "需确认未使用且完整",
                       "fulfilled" if okay else "needs_input", [row] if okay else [])


def logistics(checks, context, line):
    rows = [row for row in context["state"].get("shipments", []) if row.get("order_line_id") == line["line_id"]]
    if not rows:
        checks.add("shipment", "缺当前订单行包裹记录", "needs_input")
    now = date(context.get("as_of"))
    for row in rows:
        if not checks.evidence("order_identity", row, "关联包裹依据"):
            continue
        updated = date(row.get("updated_at"))
        if not updated or not now or updated > now:
            checks.add("shipment", "包裹轨迹时间未知或晚于截点", "needs_input")
        elif row.get("status") not in ("delivered", "cancelled") and (
                now - updated > timedelta(days=context["policy"]["logistics"]["stale_tracking_days"])):
            checks.add("shipment", "包裹轨迹已超过政策更新间隔，需查件", "wait", [row])
        else:
            checks.add("shipment", "已查到当前关联包裹记录，标签不代表发货", records=[row])
