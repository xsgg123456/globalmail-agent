"""Bounded traversal of resolved PDF dictionaries, including page annotations."""
from pypdf.generic import IndirectObject, DictionaryObject, ArrayObject
from globalmail_agent.application.conversation_lock import ServiceError

ACTIVE_KEYS = {"/JavaScript", "/JS", "/OpenAction", "/AA", "/Launch", "/RichMedia", "/RichMediaContent",
    "/RichMediaSettings", "/EmbeddedFiles"}
ACTIVE_ACTIONS = {"/JavaScript", "/Launch", "/SubmitForm", "/ImportData", "/GoToR", "/GoToE", "/Rendition", "/Movie", "/Sound"}


def reject_active(reader):
    pending, seen_refs, seen_nodes, count = [(reader.root_object, 0)], set(), set(), 0
    while pending:
        value, depth = pending.pop()
        if depth > 64 or count > 50000:
            raise ServiceError("pdf_structure_limit", 422)
        if isinstance(value, IndirectObject):
            key = value.idnum, value.generation
            if key in seen_refs:
                continue
            seen_refs.add(key)
            value = value.get_object()
        if isinstance(value, (DictionaryObject, ArrayObject)):
            if id(value) in seen_nodes:
                continue
            seen_nodes.add(id(value))
            count += 1
        if isinstance(value, DictionaryObject):
            if set(value) & ACTIVE_KEYS or value.get("/S") in ACTIVE_ACTIONS:
                raise ServiceError("active_pdf_content", 422)
            pending.extend((child, depth + 1) for child in value.values())
        elif isinstance(value, ArrayObject):
            pending.extend((child, depth + 1) for child in value)
