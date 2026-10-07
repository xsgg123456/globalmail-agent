"""Synthetic parser fixtures only; never publish these as product knowledge."""
import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import pypdfium2

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'tmp/knowledge-spike'


def draw_page(c, page):
    c.setFont('Helvetica-Bold', 15)
    c.drawString(36, 802, 'Synthetic parser test - not a real product manual')
    c.setFont('Helvetica', 9)
    c.drawString(36, 782, f'Page {page} / 4 - controlled ground truth')
    if page == 1:
        c.setFont('Helvetica-Bold', 13)
        c.drawString(36, 752, 'SIM-ALPHA remote pairing')
        c.drawString(314, 752, 'SIM-BETA cable check')
        left = ['ALPHA-START', 'Disconnect power before pairing.',
                'Hold POWER for 7 seconds.', 'Observe the LAMP flash twice.',
                'A steady remote LED is NOT success.', 'STOP if there is a burning smell.', 'ALPHA-END']
        right = ['BETA-START', 'Keep the unit disconnected.',
                 'Check the external cable only.', 'Do NOT open the sealed controller.',
                 'Never apply ALPHA pairing to BETA.', 'Escalate if the cable is damaged.', 'BETA-END']
        c.setFont('Helvetica', 10)
        for i in range(len(left)):
            c.drawString(36, 722-i*27, left[i])
            c.drawString(314, 722-i*27, right[i])
        c.setFont('FixtureCJK', 12)
        c.drawString(36, 430, '中文说明：仅用于解析测试，闻到焦味立即停止。')
    elif page in (2, 3):
        c.drawString(36, 750, 'SIM compatibility table - continued' if page == 3 else 'SIM compatibility table')
        headers = ['Part', 'Voltage (V)', 'Current (A)', 'Applies to']
        xs = [40, 155, 280, 405]
        for x, h in zip(xs, headers):
            c.drawString(x, 715, h)
        start = 1 if page == 2 else 9
        for i, n in enumerate(range(start, start+8)):
            y = 682-i*40
            values = [f'SIM-R{n:02}', '12' if n % 2 else '24', '1.5' if n % 2 else '2.0',
                      'SIM-ALPHA' if n % 2 else 'SIM-BETA']
            for x, v in zip(xs, values):
                c.drawString(x, y, v)
            c.line(36, y-12, 558, y-12)
        c.drawString(36, 300, 'Do not substitute parts across models or voltage ratings.')
    else:
        c.setFont('Helvetica-Bold', 14)
        c.drawString(36, 750, 'SIM-GAMMA illustrated instructions')
        c.setFont('Helvetica', 12)
        for i, text in enumerate(['1. Disconnect mains power.', '2. Wait 90 seconds.',
                                  '3. Connect terminal B only.', '4. Never bridge A and B.',
                                  'STOP if the casing is cracked.']):
            c.rect(42, 640-i*82, 500, 52)
            c.drawString(58, 660-i*82, text)
        c.drawString(36, 195, 'The text on this page will be rasterized in the native fixture.')


def render_bytes(data):
    doc = pypdfium2.PdfDocument(data)
    images = []
    try:
        for page in doc:
            bitmap = page.render(scale=2)
            images.append(bitmap.to_pil().convert('RGB').copy())
            bitmap.close()
            page.close()
    finally:
        doc.close()
    return images


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    # The fixture uses a Windows CJK font, embedded for deterministic rendering.
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont('FixtureCJK', 'C:/Windows/Fonts/msyh.ttc', subfontIndex=0))
    draft = io.BytesIO()
    c = canvas.Canvas(draft, pagesize=(595, 842), invariant=1)
    for page in range(1, 5):
        draw_page(c, page)
        c.showPage()
    c.save()
    pages = render_bytes(draft.getvalue())
    for scanned in (False, True):
        target = WORK / ('difficult-scanned.pdf' if scanned else 'difficult-native.pdf')
        out = canvas.Canvas(str(target), pagesize=(595, 842), invariant=1)
        for n, im in enumerate(pages, 1):
            if scanned or n == 4:
                out.drawImage(ImageReader(im), 0, 0, width=595, height=842)
            else:
                draw_page(out, n)
            out.showPage()
        out.save()
    sheet = Image.new('RGB', (1190, 842), 'white')
    for i, im in enumerate(pages):
        im.thumbnail((595, 421))
        sheet.paste(im, ((i % 2)*595, (i // 2)*421))
    sheet.save(WORK / 'fixture-preview.png')
    truth = {
        'scope': 'synthetic_developer_fixture_not_product_fact', 'pages': 4,
        'page_markers': {'1': ['SIM-ALPHA', 'SIM-BETA', '7 seconds', 'LAMP flash twice',
                              'burning smell', 'sealed controller', '闻到焦味立即停止'],
                         '2': ['SIM-R01', '12', '1.5', 'SIM-R08', '24', '2.0'],
                         '3': ['SIM-R09', 'SIM-R16', 'Voltage', 'Current'],
                         '4': ['90 seconds', 'terminal B only', 'Never bridge A and B', 'casing is cracked']},
        'table_rows': [{'part': f'SIM-R{n:02}', 'voltage': 12 if n%2 else 24,
                        'current': 1.5 if n%2 else 2.0,
                        'model': 'SIM-ALPHA' if n%2 else 'SIM-BETA'} for n in range(1,17)],
        'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in WORK.glob('difficult-*.pdf')},
    }
    (WORK/'fixture-truth.json').write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'fixtures': truth['files'], 'pages_each': 4}))


if __name__ == '__main__':
    main()
