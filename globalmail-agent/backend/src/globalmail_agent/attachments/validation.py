"""Decode actual static images before accepting bytes; never use client MIME as proof."""
import hashlib
import io
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from globalmail_agent.application.conversation_lock import ServiceError

MAX_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 20_000_000
MAX_IMAGES = 4
FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
MIME_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def inspect_image(filename, content):
    if (not filename or len(filename) > 240 or Path(filename).name != filename
            or any(c in filename for c in ("/", "\\", ":", "\x00"))
            or any(ord(c) < 32 for c in filename)):
        raise ServiceError("invalid_filename", 422)
    expected = FORMATS.get(Path(filename).suffix.lower())
    if expected is None:
        raise ServiceError("unsupported_image_format", 422)
    if not isinstance(content, bytes) or not content:
        raise ServiceError("empty_file", 422)
    if len(content) > MAX_BYTES:
        raise ServiceError("image_too_large", 422)
    try:
        with Image.open(io.BytesIO(content), formats=list(MIME_TYPES)) as image:
            if image.format != expected:
                raise ServiceError("image_format_mismatch", 422)
            width, height = image.size
            if width < 1 or height < 1 or width * height > MAX_PIXELS:
                raise ServiceError("image_pixel_limit", 422)
            if getattr(image, "n_frames", 1) != 1 or getattr(image, "is_animated", False):
                raise ServiceError("animated_image_unsupported", 422)
            image.verify()
        with Image.open(io.BytesIO(content), formats=[expected]) as image:
            image.load()
            thumbnail = ImageOps.exif_transpose(image).convert("RGB")
            thumbnail.thumbnail((512, 512), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            thumbnail.save(output, "JPEG", quality=85)
        return {"mime_type": MIME_TYPES[expected], "size_bytes": len(content),
            "width": width, "height": height, "source_sha256": hashlib.sha256(content).hexdigest(),
            "thumbnail": output.getvalue()}
    except ServiceError:
        raise
    except Image.DecompressionBombError:
        raise ServiceError("image_pixel_limit", 422) from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError):
        raise ServiceError("invalid_image", 422) from None
