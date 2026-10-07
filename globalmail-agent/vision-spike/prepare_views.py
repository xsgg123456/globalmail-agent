"""Fail-closed scope, byte and image validation for the isolated probe."""
import base64
import hashlib
import io
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ImageStat, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/visual/v1'
CONFIG = {'version': 'v2-low-detail-advisory', 'max_edge': 1280, 'max_pixels': 1048576,
          'low_detail_threshold': 1.0,
          'max_images': 4, 'max_bytes': 10 * 1024**2,
          'max_total_bytes': 20 * 1024**2, 'max_source_pixels': 20000000}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def resolve_image(relative, root=DATA):
    path = (root / relative).resolve()
    if not path.is_relative_to((root / 'images').resolve()):
        raise ValueError('outside_images')
    return path


def authorize(row, attachment):
    for key in ('customer', 'mode', 'branch', 'purpose'):
        if attachment['scope'][key] != row['scope'][key]:
            raise ValueError('scope_denied')
    if attachment['message_seq'] > row['scope']['visible_seq']:
        raise ValueError('future_image')
    if attachment.get('revoked', False):
        raise ValueError('revoked')
    if attachment.get('privacy_review') != 'synthetic_no_pii':
        raise ValueError('unreviewed_source')


def prepare(row, variant='full', root=DATA):
    attachments = row['attachments']
    if len(attachments) > CONFIG['max_images']:
        raise ValueError('image_count_limit')
    views, coverage, total = [], [], 0
    for attachment in attachments:
        authorize(row, attachment)
        path = resolve_image(attachment['path'], root)
        status = {'attachment_id': attachment['id']}
        if not path.exists():
            coverage.append({**status, 'status': 'missing', 'reason': 'no_controlled_bytes'})
            continue
        size = path.stat().st_size
        total += size
        if size > CONFIG['max_bytes'] or total > CONFIG['max_total_bytes']:
            raise ValueError('byte_limit')
        raw = path.read_bytes()
        if sha(raw) != attachment['sha256']:
            raise ValueError('source_hash_mismatch')
        try:
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in ('JPEG', 'PNG', 'WEBP') or getattr(source, 'n_frames', 1) != 1:
                    coverage.append({**status, 'status': 'unsupported', 'reason': 'format_or_animation'})
                    continue
                if source.width * source.height > CONFIG['max_source_pixels']:
                    raise ValueError('pixel_limit')
                image = ImageOps.exif_transpose(source).convert('RGB')
                original_size = image.size
        except (UnidentifiedImageError, OSError):
            suffix = path.suffix.lower()
            state = 'unsupported' if suffix in ('.pdf', '.mp4', '.mp3') else 'unreadable'
            coverage.append({**status, 'status': state, 'reason': 'decode_failed_or_unsupported'})
            continue
        box = [0, 0, image.width, image.height]
        if variant == 'crop':
            # Fixed top-left review area, not selected using expected answers.
            box = [0, 0, min(900, image.width), min(450, image.height)]
            image = image.crop(box)
        image.thumbnail((CONFIG['max_edge'], CONFIG['max_edge']))
        if image.width * image.height > CONFIG['max_pixels']:
            scale = (CONFIG['max_pixels'] / (image.width * image.height)) ** 0.5
            image = image.resize((int(image.width * scale), int(image.height * scale)))
        output = io.BytesIO()
        image.save(output, format='PNG')
        data = output.getvalue()
        edge = image.convert('L').filter(ImageFilter.Kernel(
            (3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=128))
        if image.width > 4 and image.height > 4:
            edge = edge.crop((2, 2, image.width - 2, image.height - 2))
        detail_score = round(ImageStat.Stat(edge).var[0], 4)
        views.append({'attachment_id': attachment['id'], 'source_sha256': sha(raw),
                      'derived_sha256': sha(data), 'source_size': original_size,
                      'size': image.size, 'source_box': box, 'variant': variant,
                      'detail_score': detail_score,
                      'low_detail_warning': detail_score < CONFIG['low_detail_threshold'],
                      'data_url': 'data:image/png;base64,' + base64.b64encode(data).decode()})
        coverage.append({**status, 'status': 'ready', 'reason': 'authorized_controlled_bytes'})
    return views, coverage
