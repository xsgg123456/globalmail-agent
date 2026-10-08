"""Expose only visible, scoped choice facts; never address tokens or raw branch state."""
from globalmail_agent.application.business_projection import project

CHOICE_FIELDS = {"accepted", "quantity", "amount_minor", "currency", "order_line_id",
    "item_id", "part_id", "address_version", "source_message_id", "source_message_seq", "evidence_ref"}
ADDRESS_FIELDS = {"confirmed", "version", "market", "evidence_ref"}


def customer_view(model):
    choices = []
    for choice in model["state"].get("customer_choices", []):
        record = project(choice, CHOICE_FIELDS)
        record.update(action=choice.get("kind"), source_kind=choice.get("original_source_kind"))
        if len(model["lines"]) == 1 and model["lines"][0][1]["quantity"] == 1:
            record.setdefault("order_line_id", model["lines"][0][1]["line_id"])
            record.setdefault("quantity", 1)
        choices.append(record)
    address = model["state"].get("address_confirmation")
    safe_address = None if not address else {**project(address, ADDRESS_FIELDS),
        "source_kind": address.get("original_source_kind")}
    return {"customer_choices": choices, "address_confirmation": safe_address}
