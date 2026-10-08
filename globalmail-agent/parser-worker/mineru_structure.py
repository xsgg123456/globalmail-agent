"""Map supported MiddleJson without discarding nested text, captions or table structure."""
from bs4 import BeautifulSoup
from globalmail_agent.knowledge.parser_contract import ParserBlock, ParserDiagnostic


def text_content(node):
    if isinstance(node, list):
        return "\n".join(filter(None, (text_content(child) for child in node)))
    if not isinstance(node, dict):
        return ""
    content = node.get("content", "")
    if isinstance(content, list):
        return text_content(content)
    if not isinstance(content, str) or content.startswith("data:"):
        return ""
    if "<table" in content.lower():
        return BeautifulSoup(content, "html.parser").get_text(" ", strip=True)
    return content


def table_rows(node):
    if isinstance(node, list):
        return [row for child in node for row in table_rows(child)]
    if not isinstance(node, dict):
        return []
    content = node.get("content", "")
    if isinstance(content, list):
        return table_rows(content)
    if isinstance(content, str) and "<table" in content.lower():
        return [[cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
                for row in BeautifulSoup(content, "html.parser").find_all("tr")]
    return []


def project(raw, expected_pages):
    if raw.get("schema") != "docvortex.middle" or raw.get("schema_version") != "2.0":
        raise ValueError("unsupported_middle_schema")
    pages = raw.get("pages")
    if not isinstance(pages, list):
        raise ValueError("missing_middle_pages")
    indices = [page.get("page_idx") for page in pages]
    full = raw.get("is_full_document") is True and sorted(indices) == list(range(expected_pages))
    diagnostics, blocks = [], []
    if not full:
        diagnostics.append(ParserDiagnostic(code="incomplete_page_coverage", severity="error",
            message="解析未完整覆盖原件页码，不能通过核对。", blocks_review=True))
    for page in pages:
        page_number = page["page_idx"] + 1
        section = f"page-{page_number:04d}"
        for index, node in enumerate(page.get("blocks", [])):
            node_type = node.get("type", "")
            identifier = f"p{page_number:04d}-b{index:04d}"
            if node_type in {"doc_title", "paragraph_title"}:
                section = identifier
            rows = table_rows(node)
            kind = ("heading" if node_type in {"doc_title", "paragraph_title"} else
                    "figure" if node_type in {"image", "chart"} else
                    "table" if rows or node_type == "table" else "paragraph")
            blocks.append(ParserBlock(id=identifier, page=page_number, section_id=section,
                type=kind, text=text_content(node), bbox=node.get("bbox"),
                table_rows=rows, figure_id=identifier if kind == "figure" else None))
    return blocks, diagnostics, full
