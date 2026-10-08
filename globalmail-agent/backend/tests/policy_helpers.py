"""Verified server-context samples; no customer request can supply these facts."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V1 = json.loads((ROOT / "data/knowledge/v1/policies/policy-profile.json").read_text(encoding="utf-8"))
V2 = json.loads((ROOT / "data/knowledge/v2/policies/policy-profile.json").read_text(encoding="utf-8"))


def fact(**fields):
    return {"source_kind": "verified_fixture", "evidence_ref": "fixture:" + str(
        fields.get("operation_id") or fields.get("execution_id") or fields.get("return_id") or "evidence"), **fields}


def context(action="refund", quantity=1, paid=10001, amount=None, version=2):
    amount = paid if amount is None else amount
    line = fact(line_id="line-1", sku="exact-sku", quantity=quantity, paid_minor=paid, hardware_revision="SIM-V1")
    order = fact(order_id="order-1", brand="OUTON", market="US", channel="amazon", currency="USD",
        paid_minor=paid, refunded_minor=0, pending_refund_minor=0, line_count=1,
        delivered_at="2026-09-20T12:00:00+08:00")
    state = {"visible_source_message_ids": ["message-1"], "customer_choices": [fact(
        kind=action, accepted=True, order_line_id="line-1", quantity=quantity, amount_minor=amount,
        currency="USD", source_message_id="message-1", address_version=2,
        item_id="part-1" if action == "spare_part" else "exact-sku")],
        "address_confirmation": fact(confirmed=True, version=2, market="US"), "operations": [],
        "execution_records": [], "returns": [fact(return_id="rma-1", order_line_id="line-1",
            received=True, inspection="passed", quantity=quantity)],
        "inventory": [fact(item_id="exact-sku", on_hand=4, reserved=1, market="US", hardware_revision="SIM-V1",
            snapshot_at="2026-10-08T09:00:00+08:00"), fact(item_id="part-1", on_hand=5, reserved=0,
            market="US", hardware_revision="SIM-V1", snapshot_at="2026-10-08T09:00:00+08:00")],
        "problem_evidence": [fact(order_line_id="line-1", reason="defect",
            item_id="part-1" if action == "spare_part" else "exact-sku")], "risk_flags": [], "shipments": []}
    return {"mode": "simulation", "as_of": "2026-10-08T10:00:00+08:00", "order": order, "line": line,
        "state": state, "policy": copy.deepcopy(V2 if version == 2 else V1), "policy_metadata": {
            "publication_status": "unpublished", "hash": "policyhash"},
        "product": fact(sku="exact-sku", hardware_revision="SIM-V1", market="US"),
        "parts": [fact(part_id="part-1", safety_critical=False, customer_replaceable=True)],
        "compatibility": [fact(part_id="part-1", sku="exact-sku", hardware_revision="SIM-V1", market="US",
            status="compatible_in_simulation")]}


def command(action="refund", amount=10001, quantity=1):
    from globalmail_agent.domain.policy import EligibilityRequest
    return EligibilityRequest(action=action, order_line_id="line-1", quantity=quantity,
        amount_minor=amount if action == "refund" else None, currency="USD" if action == "refund" else None,
        item_id="part-1" if action == "spare_part" else None)


def statuses(result, code):
    return [row["status"] for row in result["conditions"] if row["code"] == code]
