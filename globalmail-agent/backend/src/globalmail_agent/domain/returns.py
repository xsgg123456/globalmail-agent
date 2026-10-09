"""Return authorization, postage and warehouse facts have separate stages."""


def return_document(policy, reason, external_id, quantity, units, command):
    payer = policy["return"]["defect_label_fee_payer" if reason == "defect" else "unwanted_label_fee_payer"]
    return {"return_id": external_id, "quantity": quantity, "affected_unit_ids": units,
        "status": "authorized", "received": False, "inspection": None,
        "authorized_return_reference": command.receipt_ref, "return_address": command.return_address,
        "packing_instructions": command.packing_instructions, "prepaid_label_ref": command.prepaid_label_ref,
        "postage_responsibility": payer, "prepaid_label": payer == "merchant",
        "document_source": "scenario_console_manual", "simulation": True}
