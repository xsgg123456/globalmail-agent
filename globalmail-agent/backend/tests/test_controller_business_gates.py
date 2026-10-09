"""Reachable multi-order ledger counterexamples must never satisfy another line's gate."""
from copy import deepcopy
import unittest
from globalmail_agent.evaluation.service_gates import verify_business_gate


class ControllerBusinessGateTests(unittest.TestCase):
    def observation(self):
        refund = {"operation_id": "REF-A", "order_id": "ORDER-A", "order_line_id": "LINE-A", "kind": "refund",
            "managed": True, "status": "waiting_condition", "version": 1, "allowed_events": []}
        returned = {"operation_id": "RET-B", "order_id": "ORDER-B", "order_line_id": "LINE-B", "kind": "return",
            "managed": True, "status": "accepted", "version": 2, "allowed_events": ["create_execution"]}
        return {"ledger": {"operations": [refund, returned], "executions": [], "shipments": [], "returns": []}}

    def test_another_order_or_line_return_never_satisfies_this_refund_gate(self):
        event = {"kind": "return_update", "gate": {"operation_required": {"kind": "refund", "order_line_id": "LINE-A"}}, "payload": {}}
        for target in [("ORDER-B", "LINE-B"), ("ORDER-A", "LINE-B")]:
            observation = self.observation()
            observation["ledger"]["operations"][1].update(order_id=target[0], order_line_id=target[1])
            self.assertEqual(verify_business_gate(None, "after_internal_return_request", event, observation, {}).status, "blocked")
        observation["ledger"]["operations"][1].update(order_id="ORDER-A", order_line_id="LINE-A")
        result = verify_business_gate(None, "after_internal_return_request", event, observation, {})
        self.assertEqual(result.status, "passed")
        self.assertIn("return_operation:RET-B:version:2", result.evidence_refs)
        observation["ledger"]["operations"][1]["status"] = "cancelled"
        self.assertEqual(verify_business_gate(None, "after_internal_return_request", event, observation, {}).status, "blocked")

    def test_return_or_shipment_kind_alone_cannot_pass_an_illegal_transition(self):
        for kind in ["return_update", "shipment_update", "service_note"]:
            event = {"kind": kind, "gate": {"operation_required": {"kind": "refund", "order_line_id": "LINE-A"}},
                "payload": {"record": {"status": "succeeded"}}}
            self.assertEqual(verify_business_gate(None, "legal_execution_status_transition", event, self.observation(), {}).status, "blocked")
