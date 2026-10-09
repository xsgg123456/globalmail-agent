"""Actual SDK payload capture without network; original graph input stays immutable."""
import base64
from unittest import TestCase
from unittest.mock import Mock
import test_model_provider as provider_tests
from test_attachment_validation import image_bytes
from globalmail_agent.attachments.views import bounded_view
from globalmail_agent.attachments.understanding import VisualUnderstanding, authorized_order_numbers
from agent_fixture import understanding


class VisionProviderTests(TestCase):
    def test_sdk_gets_authorized_image_bytes_but_original_messages_have_only_text(self):
        model, client, response = provider_tests.ModelProviderTests().provider()
        messages = [{"role": "user", "content": "Exact original material."}]
        loader = Mock(return_value=b"approved_png_bytes")
        model.request(messages, schema={"type": "object"}, image_views=[{"attachment_id": "approved-image"}], image_loader=loader)
        sent = client.with_options.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(sent["messages"][0]["content"][0]["text"], messages[0]["content"])
        self.assertEqual(sent["messages"][0]["content"][-1]["image_url"]["url"],
            "data:image/png;base64," + base64.b64encode(b"approved_png_bytes").decode())
        self.assertEqual(messages, [{"role": "user", "content": "Exact original material."}])
        loader.assert_called_once_with({"attachment_id": "approved-image"})

    def test_exif_patch_sizing_and_manual_order_number_priority(self):
        view, width, height, tokens = bounded_view(image_bytes("JPEG", size=(3000, 1500), orientation=6))
        self.assertLessEqual(max(width, height), 1024)
        self.assertEqual((width, height), (512, 1024))
        self.assertGreater(tokens, width * height // 1024 + 2)
        value = VisualUnderstanding.model_validate({**understanding([]), "images": [{"attachment_id": "one",
            "status": "understood", "coverage": "整图", "quality": "清晰", "observations": [], "hypotheses": [],
            "uncertainties": [], "risk_flags": [], "field_candidates": [{"key": "order_number", "raw_text": "OLD123",
            "value": "OLD123", "ambiguous_characters": []}]}]})
        payload = {"visual_sources": {"manual": {"attachment_id": "one", "evidence_kind": "field_candidate",
            "correction": {"key": "order_number", "value": "NEW123"}}}}
        self.assertEqual(authorized_order_numbers(value, payload), ["NEW123"])
