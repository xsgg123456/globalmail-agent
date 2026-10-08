"""Validate actual bytes and exact product bindings; never follow document links."""
import io
import json
import logging
from pathlib import Path
from pypdf import PdfReader
from globalmail_agent.adapters.fixture_loader import FIXTURE_ROOT
from globalmail_agent.application.conversation_lock import ServiceError

MAX_BYTES = 50 * 1024 * 1024


def catalog():
    try:
        rows = json.loads((FIXTURE_ROOT / "products.json").read_text(encoding="utf-8"))
        return [{"sku": p["sku"], "brand": p["brand"], "name": " / ".join(p["registered_names"])} for p in rows]
    except (OSError, ValueError, KeyError, TypeError):
        raise ServiceError("catalog_unavailable", 503) from None


def validate_bindings(rows, brand, page_range):
    products = {p["sku"]: p for p in catalog()}
    seen = set()
    for row in rows:
        if row["sku"] not in products or brand and products[row["sku"]]["brand"] != brand:
            raise ServiceError("invalid_sku_scope", 422)
        key = row["section_id"], row["sku"]
        if key in seen:
            raise ServiceError("duplicate_applicability", 422)
        seen.add(key)
        start, end = row["page_start"], row["page_end"]
        if page_range:
            if start is None or start < page_range[0] or end > page_range[1]:
                raise ServiceError("invalid_page_scope", 422)
        elif start is not None:
            raise ServiceError("invalid_page_scope", 422)


def inspect_content(filename, content):
    if not filename or len(filename) > 240 or Path(filename).name != filename or any(c in filename for c in ("/", "\\", ":")):
        raise ServiceError("invalid_filename", 422)
    if not content or len(content) > MAX_BYTES:
        raise ServiceError("file_too_large" if content else "empty_file", 422)
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise ServiceError("invalid_pdf", 422)
        # Parser logging is not allowed to reveal document strings or filesystem paths.
        logger = logging.getLogger("pypdf")
        original = logger.disabled
        logger.disabled = True
        try:
            reader = PdfReader(io.BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise ServiceError("encrypted_pdf", 422)
            pages = len(reader.pages)
            if not 1 <= pages <= 300:
                raise ServiceError("pdf_page_limit", 422)
            from globalmail_agent.knowledge.pdf_checks import reject_active
            reject_active(reader)
            return "pdf", pages
        except ServiceError:
            raise
        except Exception:
            raise ServiceError("invalid_pdf", 422) from None
        finally:
            logger.disabled = original
    if suffix not in {".md", ".json", ".jsonl"} or content.startswith((b"%PDF-", b"MZ", b"PK\x03\x04")):
        raise ServiceError("unsupported_format", 422)
    try:
        text = content.decode("utf-8")
        if not text.strip():
            raise ServiceError("empty_file", 422)
        if "\x00" in text:
            raise ValueError()
        if suffix in {".json", ".jsonl"}:
            value = json.loads(text) if suffix == ".json" else [json.loads(line) for line in text.splitlines() if line.strip()]
            from globalmail_agent.knowledge.policy_bundle import bundle
            from globalmail_agent.knowledge.json_structure import validate_knowledge_structure
            if suffix == ".json" and isinstance(value, dict) and value.get("schema_version") != "globalmail.knowledge/1":
                bundle(value)
            else:
                validate_knowledge_structure(content, suffix[1:])
    except ServiceError:
        raise
    except (ValueError, UnicodeError, KeyError, TypeError):
        raise ServiceError("invalid_knowledge_schema", 422) from None
    return suffix[1:], None
