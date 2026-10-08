"""Create original-page previews and exact figure crops; never interpret their meaning."""
import hashlib
from pathlib import Path
import pypdfium2 as pdfium
from globalmail_agent.knowledge.parser_contract import ParserAsset, ParserDiagnostic


def asset(content, path, asset_id, kind, page):
    return ParserAsset(id=asset_id, relative_path=path, media_type="image/png", kind=kind,
                       page=page, sha256=hashlib.sha256(content).hexdigest())


def render_assets(source, directory, blocks):
    target = directory / "assets"
    target.mkdir(exist_ok=True)
    assets, diagnostics = [], []
    document = pdfium.PdfDocument(source)
    try:
        for index in range(len(document)):
            page_number = index + 1
            page = document[index]
            try:
                width, height = page.get_size()
                scale = min(1.5, 1400 / max(width, height))
                bitmap = page.render(scale=scale)
                image = bitmap.to_pil()
                relative = f"assets/page-{page_number:04d}.png"
                image.save(directory / relative)
                assets.append(asset((directory / relative).read_bytes(), relative,
                                    f"page-{page_number:04d}", "page_preview", page_number))
                image.close()
                bitmap.close()
                for block in blocks:
                    if block.page != page_number or block.type not in {"figure", "table"}:
                        continue
                    box = block.bbox
                    if (not box or len(box) != 4 or not 0 <= box[0] < box[2] <= 1
                            or not 0 <= box[1] < box[3] <= 1):
                        diagnostics.append(ParserDiagnostic(code="figure_geometry_missing", severity="error",
                            page=page_number, block_ids=[block.id], message="图片或表格缺少可定位的边界。",
                            blocks_review=True))
                        continue
                    crop = (box[0] * width, (1 - box[3]) * height, (1 - box[2]) * width, box[1] * height)
                    bitmap = page.render(scale=scale, crop=crop)
                    image = bitmap.to_pil()
                    relative = f"assets/{block.id}.png"
                    image.save(directory / relative)
                    assets.append(asset((directory / relative).read_bytes(), relative, block.id,
                                        "figure", page_number))
                    block.asset_ids.append(block.id)
                    if block.type == "figure":
                        diagnostics.append(ParserDiagnostic(code="figure_requires_human_comparison",
                            severity="warning", page=page_number, block_ids=[block.id], asset_ids=[block.id],
                            message="已保存原PDF图片像素；图片中的操作含义仍需人工对照原件核对。"))
                    image.close()
                    bitmap.close()
            finally:
                page.close()
    finally:
        document.close()
    return assets, diagnostics
