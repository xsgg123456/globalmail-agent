"""Only group contiguous blocks with identical section, SKU and page applicability."""
import re
from globalmail_agent.knowledge.base import canonical, sha
from globalmail_agent.application.conversation_lock import ServiceError


def proxy_tokens(text):
    return sum(1 if ord(char) < 128 else 2 for char in text)


def matching(block, bindings):
    return sorted([{k: a[k] for k in ("section_id", "sku", "page_start", "page_end", "basis")}
        for a in bindings if a["section_id"] in {"document", block["section_id"]}
        and (block["page"] is None or a["page_start"] is not None and a["page_start"] <= block["page"] <= a["page_end"])],
        key=lambda a: (a["sku"], a["section_id"], a["basis"]))


def block_text(block):
    rows = block["structure"].get("table_rows", [])
    return "\n".join([block["text"], *[" | ".join(row) for row in rows]]).strip()


def safety_line(line):
    return (any(term in line for term in ("前提", "警告", "注意", "停止", "断电", "禁止", "安全", "拔掉电源"))
        or re.search(r"\b(warning|caution|prerequisite|disconnect|unplug|stop|danger|safety|do not|must not)\b", line, re.I) is not None)


def safety_blocks(blocks):
    sections = {b["section_id"] for b in blocks if b.get("type", b["structure"].get("type")) == "heading" and safety_line(block_text(b))}
    return [b for b in blocks if b["section_id"] in sections or
            any(safety_line(line) for line in block_text(b).splitlines())]


def units(block, limit):
    text = block_text(block)
    if proxy_tokens(text) <= limit:
        return [text] if text else []
    rows = block["structure"].get("table_rows", [])
    if rows:
        header = block["text"] + "\n" + " | ".join(rows[0])
        values = [header + "\n" + " | ".join(row) for row in rows[1:]] or [header]
    else:
        # Complete paragraphs/steps survive; never cut a numbered step in the middle.
        values = [v.strip() for v in re.split(r"\n\s*\n|\n(?=\s*(?:\d+[.)、]|[-*] ))", text) if v.strip()]
    if any(proxy_tokens(v) > limit for v in values):
        raise ServiceError("structured_block_too_long", 422)
    return values


def pack_items(items, target, maximum):
    groups, current = [], []
    for item in items:
        text = "\n\n".join(v[0] for v in [*current, item])
        if current and (proxy_tokens(text) > maximum or proxy_tokens("\n\n".join(v[0] for v in current)) >= target):
            groups.append(current)
            current = []
        current.append(item)
    if current:
        groups.append(current)
    return groups


def sku_set(applies):
    return {a["sku"] for a in applies}


def merge_bindings(blocks, bindings, skus):
    merged = {canonical(a): a for b in blocks for a in matching(b, bindings) if a["sku"] in skus}
    return sorted(merged.values(), key=lambda a: (a["sku"], a["section_id"], a["basis"]))


def contexts(grouped, retained, bindings, short):
    for signature, applies, group in grouped:
        if short:
            yield signature, merge_bindings(group, bindings, sku_set(applies)), group, []
            continue
        # Stop conditions may follow the procedure; source qualification, not order, determines inclusion.
        safety = [b for b in safety_blocks(retained) if b not in group]
        # Different SKU prerequisites form separate parents, with each source's own binding.
        partitions = {}
        for sku in sorted(sku_set(applies)):
            qualified = [b for b in safety if sku in sku_set(matching(b, bindings))]
            key = tuple(b["block_key"] for b in qualified)
            partitions.setdefault(key, (set(), qualified))[0].add(sku)
        for skus, qualified in partitions.values():
            yield signature, merge_bindings([*group, *qualified], bindings, skus), group, qualified


def chunks(title, blocks, bindings, exclusions, profile, *, safety_context=True):
    grouped = []
    retained = [b for b in blocks if b["block_key"] not in exclusions]
    for block in retained:
        applies = matching(block, bindings)
        if not applies:
            raise ServiceError("unbound_section")
        signature = canonical([block["section_id"], applies])
        if not grouped or grouped[-1][0] != signature:
            grouped.append((signature, applies, []))
        grouped[-1][2].append(block)
    full = "\n\n".join(block_text(b) for b in retained)
    short = bool(grouped and proxy_tokens(full) <= profile["parent_tokens"] and
                 len({tuple(sorted(sku_set(g[1]))) for g in grouped}) == 1)
    if short:
        # A short SOP keeps prerequisites, steps and stopping conditions together.
        grouped = [(b"short_parent", grouped[0][1], retained)]
    parents = []
    context_groups = contexts(grouped, retained, bindings, short) if safety_context else [
        (signature, merge_bindings(group, bindings, sku_set(applies)), group, [])
        for signature, applies, group in grouped]
    for _, applies, group, prior in context_groups:
        sections = list(dict.fromkeys(b["section_id"] for b in group))
        section = sections[0] if len(sections) == 1 else "document"
        warning_blocks = safety_blocks([*prior, *group]) if safety_context else []
        warning = "\n\n".join(dict.fromkeys(block_text(b) for b in warning_blocks))
        prefix = title + "\n章节：" + " / ".join(sections) + ("\n必要前提与停止条件：\n" + warning if warning and not short else "") + "\n正文：\n"
        maximum = (profile["short_input_max_tokens"] if short else profile["max_tokens"]) - proxy_tokens(prefix)
        if maximum < 100:
            raise ServiceError("structured_context_too_long", 422)
        values = [(v, b) for b in group for v in units(b, maximum)]
        full = "\n\n".join(v[0] for v in values)
        capacity = profile["parent_tokens"] - proxy_tokens(warning) - (2 if warning else 0)
        groups = [values] if short or proxy_tokens(full) <= capacity else pack_items(values, capacity, capacity)
        for selected in groups:
            text = "\n\n".join(v[0] for v in selected)
            # Expansion includes the exact prerequisites even when a later parent contains the hit.
            missing_warning = "\n\n".join(dict.fromkeys(block_text(b) for b in warning_blocks if block_text(b) not in text))
            expanded = (missing_warning + "\n\n" + text) if missing_warning else text
            if proxy_tokens(expanded) > profile["parent_tokens"]:
                raise ServiceError("parent_context_too_long", 422)
            if short and proxy_tokens(text) > maximum:
                raise ServiceError("short_document_input_too_long", 422)
            child_texts = [text] if proxy_tokens(text) <= maximum else ["\n\n".join(v[0] for v in part)
                for part in pack_items(selected, profile["target_tokens"], maximum)]
            if any(proxy_tokens(v) > maximum for v in child_texts):
                raise ServiceError("structured_block_too_long", 422)
            location_blocks = {b["block_key"]: b for _, b in selected}
            if missing_warning:
                location_blocks.update({b["block_key"]: b for b in warning_blocks if block_text(b) not in text})
            locations = [{"block_id": b["block_key"], "page": b["page"], "section": b["section_id"], **b["structure"]} for b in location_blocks.values()]
            parents.append({"section_id": section, "text": expanded, "content_sha256": sha(expanded.encode()),
                "applicability": applies, "locations": locations, "proxy_tokens": proxy_tokens(expanded),
                "children": [{"input_text": prefix + value, "input_sha256": sha((prefix + value).encode())} for value in child_texts]})
    if not parents:
        raise ServiceError("empty_reviewed_content")
    return parents
