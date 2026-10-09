"""Hash raw model arguments and actual normalized output; never assemble product state."""
import json
from uuid import UUID, uuid5
from bootstrap import digest


def draft_lineage(record, requests):
    tools = {t["id"]: t for t in record["tools"] if t["name"] == "create_reply_draft"}
    lineage = []
    for index, request in enumerate(requests, 1):
        for call in request.get("response", {}).get("calls", []):
            if call["name"] != "create_reply_draft":
                continue
            row = {"request_index": index, "provider_call_id": call["id"],
                "raw_arguments_sha256": digest(call["arguments"].encode())}
            try:
                args = json.loads(call["arguments"])
                if not isinstance(args, dict):
                    raise TypeError
                texts = [c["text"] for c in args.get("claims", [])]
                assembled = "\n\n".join(texts)
            except (ValueError, TypeError, KeyError):
                row["safe_error_code"] = "draft_arguments_not_object_or_claim_strings"
                lineage.append(row)
                continue
            tool = tools.get(str(uuid5(UUID(str(record["run"]["id"])), call["id"])))
            data = ((tool or {}).get("result") or {}).get("data") or {}
            normalized = data.get("body")
            explicit = "body" in args
            body = args.get("body")
            row.update({"raw_body_present": explicit,
                "model_body_mode": "legacy_explicit_body" if explicit else "ordered_claims",
                "raw_body_sha256": digest(body.encode()) if isinstance(body, str) else None,
                "claim_text_sha256_in_order": [digest(t.encode()) for t in texts],
                "ordered_claim_join_sha256": digest(assembled.encode()),
                "current_gateway_command_id": (tool or {}).get("id"),
                "actual_normalized_body_sha256": digest(normalized.encode()) if isinstance(normalized, str) else None,
                "normalized_equals_original_explicit_body": normalized == body if explicit and isinstance(normalized, str) else None,
                "normalized_equals_exact_ordered_claim_join": normalized == assembled if not explicit and isinstance(normalized, str) else None,
                "assembly_policy": "original claim text/order, exact two-newline separator; no trimming or added sentences",
                "quality_evidence": "diagnostic lineage only; frozen targets and semantic review unchanged"})
            lineage.append(row)
    return lineage
