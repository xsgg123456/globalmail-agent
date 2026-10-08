"""Pure MiddleJson projection and original pixels, in the locked parser environment."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "globalmail-agent/backend/src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mineru_structure import project
import model_integrity
from pdf_assets import render_assets


class StructureTests(unittest.TestCase):
    def test_pages_figures_tables_keep_unit_headers_caption_and_location(self):
        node = {"type": "table", "bbox": [0.1, 0.1, 0.9, 0.3], "content": [{"content": "<table><tr><th>型号</th><th>输入 (V)</th></tr><tr><td>SKU-1</td><td>24</td></tr></table>"}, {"content": "先断电"}]}
        raw = {"schema": "docvortex.middle", "schema_version": "2.0", "is_full_document": True, "pages": [{"page_idx": 0, "blocks": [node]}]}
        blocks, diagnostics, full = project(raw, 1)
        self.assertTrue(full)
        self.assertEqual(blocks[0].page, 1)
        self.assertIn("先断电", blocks[0].text)
        self.assertEqual(blocks[0].table_rows, [["型号", "输入 (V)"], ["SKU-1", "24"]])
        self.assertEqual(blocks[0].bbox, node["bbox"])
        self.assertFalse(diagnostics)

    def test_missing_pages_and_unknown_schema_do_not_become_complete(self):
        raw = {"schema": "docvortex.middle", "schema_version": "2.0", "is_full_document": True, "pages": [{"page_idx": 1, "blocks": []}]}
        _, diagnostics, full = project(raw, 2)
        self.assertFalse(full)
        self.assertTrue(diagnostics[0].blocks_review)
        raw["schema_version"] = "unsupported"
        with self.assertRaises(ValueError): project(raw, 2)

    def test_model_mismatch_is_detected_before_sdk_can_download(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"files": [{"path": "a", "bytes": 3, "sha256": "0" * 64}]}))
            (root / "models").mkdir(); (root / "models/a").write_bytes(b"bad")
            with patch.dict(os.environ, {"MINERU_HOME": directory}), patch.object(model_integrity, "MANIFEST", manifest):
                with self.assertRaisesRegex(ValueError, "local_model_mismatch"): model_integrity.verify_models("mineru_basic")

    def test_figure_crop_is_the_original_pdf_region_and_invalid_geometry_blocks_review(self):
        from reportlab.pdfgen import canvas
        from PIL import Image
        from globalmail_agent.knowledge.parser_contract import ParserBlock
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "source.pdf"
            drawing = canvas.Canvas(str(source), pagesize=(200, 200)); drawing.setFillColorRGB(1, 0, 0); drawing.rect(0, 100, 100, 100, fill=1, stroke=0); drawing.save()
            blocks = [ParserBlock(id="figure", page=1, type="figure", bbox=[0, 0, 0.5, 0.5]), ParserBlock(id="missing", page=1, type="figure")]
            assets, diagnostics = render_assets(source, root, blocks)
            with Image.open(root / "assets/figure.png") as image:
                red, green, blue = image.convert("RGB").getpixel((image.width // 2, image.height // 2))
                self.assertGreater(red, 240); self.assertLess(green, 20); self.assertLess(blue, 20)
            self.assertTrue(any(d.code == "figure_geometry_missing" and d.blocks_review for d in diagnostics))
            self.assertEqual(blocks[0].asset_ids, ["figure"])
