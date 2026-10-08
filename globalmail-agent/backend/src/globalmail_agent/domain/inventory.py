"""Exact matching, with no SKU prefix or global stock fallback."""


def compatible(line, item_id, rows):
    if not line.get("hardware_revision"):
        return None
    if item_id == line["sku"]:
        return True
    return any(row["sku"] == line["sku"] and row["part_id"] == item_id
        and row["hardware_revision"] == line["hardware_revision"]
        and "simulation" in row.get("allowed_modes", []) for row in rows)
