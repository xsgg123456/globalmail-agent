"""Image outputs remain customer evidence; a returned string is not a ledger receipt."""
from typing import Literal
from pydantic import Field
from globalmail_agent.agent.understanding import StrictModel, Understanding
from globalmail_agent.application.conversation_lock import ServiceError


class FieldCandidate(StrictModel):
    key: Literal["order_number", "sku", "model", "error_code", "other"]
    raw_text: str = Field(max_length=500)
    value: str | None = Field(max_length=500)
    ambiguous_characters: list[str] = Field(max_length=20)


class ImageAnalysis(StrictModel):
    attachment_id: str = Field(max_length=100)
    status: Literal["understood", "partial", "unreadable"]
    coverage: str = Field(min_length=1, max_length=500)
    quality: str = Field(min_length=1, max_length=500)
    field_candidates: list[FieldCandidate] = Field(max_length=8)
    observations: list[str] = Field(max_length=8)
    hypotheses: list[str] = Field(max_length=8)
    uncertainties: list[str] = Field(max_length=8)
    risk_flags: list[Literal["fire", "electric_shock", "injury", "battery_danger", "other_safety"]] = Field(max_length=5)


class VisualUnderstanding(Understanding):
    images: list[ImageAnalysis] = Field(max_length=6)


def vision_schema():
    def compact(value):
        if isinstance(value, dict):
            return {k: compact(v) for k, v in value.items() if k != "title"}
        if isinstance(value, list):
            return [compact(v) for v in value]
        return value
    # Display-only JSON Schema titles add no constraints; keep every field/description.
    return compact(VisualUnderstanding.model_json_schema())


def visual_sources(value, refs):
    expected = {r["attachment_id"] for r in refs}
    if len(value.images) != len(expected) or {r.attachment_id for r in value.images} != expected:
        raise ServiceError("visual_coverage_invalid", 422)
    sources = {}
    for image in value.images:
        if image.status == "unreadable" and (image.field_candidates or image.observations or image.risk_flags):
            raise ServiceError("visual_unreadable_has_facts", 422)
        strings = [*image.observations, *image.hypotheses, *image.uncertainties]
        for field in image.field_candidates:
            strings.extend([field.raw_text, field.value or ""])
        strings.extend(image.risk_flags)
        sources["image:" + image.attachment_id] = {"sender": "visual_evidence",
            "body": "\n".join(s for s in strings if s), "kind": "customer_image",
            "attachment_id": image.attachment_id}
    candidates = [(c.value, c.sources) for c in value.order_candidates]
    candidates.extend((i.order_number, i.sources) for i in value.intents if i.order_number)
    for number, references in candidates:
        for ref in references:
            if ref.message_id.startswith("image:"):
                image = next((r for r in value.images if "image:" + r.attachment_id == ref.message_id), None)
                if image is None or not any(f.key == "order_number" and not f.ambiguous_characters
                        and f.value == number and f.value in f.raw_text for f in image.field_candidates):
                    raise ServiceError("visual_order_ambiguous", 422)
    return sources


def authorized_order_numbers(value, payload):
    manual = {s["attachment_id"]: s["correction"]["value"] for s in payload.get("visual_sources", {}).values()
        if s.get("evidence_kind") == "field_candidate" and s.get("correction", {}).get("key") == "order_number"}
    return list(dict.fromkeys([*manual.values(), *[field.value for image in value.images
        for field in image.field_candidates if field.key == "order_number" and field.value
        and not field.ambiguous_characters and field.value in field.raw_text
        and (image.attachment_id not in manual or manual[image.attachment_id] == field.value)]]))


def apply_manual_corrections(value, payload):
    from globalmail_agent.agent.understanding import Fact, SourceRef, Candidate
    manual = [(identity, source) for identity, source in payload.get("visual_sources", {}).items()
        if source.get("kind") == "manual_image_correction"]
    for identity, source in manual:
        image_id = "image:" + source["attachment_id"]
        kind, content = source["evidence_kind"], source["correction"]
        image = next((i for i in value.images if i.attachment_id == source["attachment_id"]), None)
        if kind == "field_candidate":
            value.facts = [f for f in value.facts if not any(r.message_id == image_id for r in f.sources)]
            if image:
                image.field_candidates = [f for f in image.field_candidates if f.key != content.get("key")]
        if kind in {"observation", "hypothesis"}:
            affected = {"visual_observation", "model_inference"} if kind == "observation" else {"visual_hypothesis", "model_inference"}
            value.facts = [f for f in value.facts if not (f.kind in affected and any(r.message_id == image_id for r in f.sources))]
            if image:
                if kind == "observation": image.observations = []
                else: image.hypotheses = []
        if kind == "field_candidate" and content.get("key") == "order_number":
            value.order_candidates = [c for c in value.order_candidates if not any(r.message_id == image_id for r in c.sources)]
            for intent in value.intents:
                if any(r.message_id == image_id for r in intent.sources):
                    intent.order_number = None
            value.order_candidates.append(Candidate(value=content["value"], sources=[SourceRef(message_id=identity, quote=content["value"])]))
        value.facts.append(Fact(key="manual_" + content.get("key", kind), value=content["value"], kind="human_decision",
            sources=[SourceRef(message_id=identity, quote=content["value"])]))
    return value
