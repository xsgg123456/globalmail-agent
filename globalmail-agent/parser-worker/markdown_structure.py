"""Preserve complete Markdown structure without executing markup or visiting links."""
import re
from globalmail_agent.knowledge.parser_contract import ParserBlock, ParserDiagnostic


def markdown_blocks(content):
    blocks, diagnostics, pending = [], [], []
    section, section_number = "document", 0

    def emit(kind="paragraph", rows=None):
        if not pending:
            return
        text = "\n".join(pending)
        identifier = f"md-{len(blocks) + 1:04d}"
        blocks.append(ParserBlock(id=identifier, section_id=section, type=kind,
                                  text=text, table_rows=rows or []))
        pending.clear()

    lines = content.splitlines()
    index, fence = 0, None
    while index < len(lines):
        line = lines[index]
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence:
            pending.append(line)
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
                emit()
        elif marker:
            emit()
            fence = marker[1]
            pending.append(line)
        elif re.match(r"^#{1,6}\s+", line):
            emit()
            section_number += 1
            section = f"section-{section_number:04d}"
            pending.append(line)
            emit("heading")
        elif ("|" in line and index + 1 < len(lines)
              and re.match(r"^\s*\|?\s*:?-{3,}", lines[index + 1])):
            emit()
            rows = []
            while index < len(lines) and "|" in lines[index]:
                current = lines[index]
                pending.append(current)
                cells = [cell.strip() for cell in current.strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", cell or " ") for cell in cells):
                    rows.append(cells)
                index += 1
            emit("table", rows)
            continue
        elif not line.strip():
            emit("list" if pending and re.match(r"^\s*(?:[-*+]\s|\d+[.)]\s)", pending[0]) else "paragraph")
        else:
            pending.append(line)
        index += 1
    emit("list" if pending and re.match(r"^\s*(?:[-*+]\s|\d+[.)]\s)", pending[0]) else "paragraph")
    diagnostics = missing_images(blocks)
    return blocks, diagnostics


def missing_images(blocks):
    affected = set()
    for block in blocks:
        text = block.text + "\n" + "\n".join(" ".join(row) for row in block.table_rows)
        if not re.match(r"^\s*(```|~~~)", text) and re.search(r'!\[[^\]]*\](?:\([^)]*\)|\[[^\]]*\])|<img\b', text, re.I):
            affected.add(block.section_id)
    return [ParserDiagnostic(code="markdown_image_not_loaded", severity="error",
        block_ids=[block.id for block in blocks if block.section_id == section],
        message="正文引用图片尚无受控字节，相关章节须补齐图片或明确排除。", blocks_review=True)
        for section in sorted(affected)]
