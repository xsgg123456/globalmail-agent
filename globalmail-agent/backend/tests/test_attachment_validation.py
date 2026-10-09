"""Actual Pillow decoding, frame rejection and byte/pixel boundary checks."""
import io
import unittest
from PIL import Image
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.attachments.validation import inspect_image, MAX_BYTES


def image_bytes(fmt="PNG", size=(80, 40), animated=False, orientation=None):
    image = Image.new("RGB", size, "navy")
    output = io.BytesIO()
    options = {}
    if animated:
        options.update(save_all=True, append_images=[Image.new("RGB", size, "white")], duration=100, loop=0)
    if orientation is not None:
        exif = Image.Exif()
        exif[274] = orientation
        options["exif"] = exif
    image.save(output, fmt, **options)
    return output.getvalue()


class ImageValidationTests(unittest.TestCase):
    def rejected(self, filename, content, code):
        with self.assertRaises(ServiceError) as caught:
            inspect_image(filename, content)
        self.assertEqual(caught.exception.code, code)

    def test_supported_formats_decode_with_actual_mime_digest_and_stripped_thumbnail(self):
        for fmt, extension, mime in (("PNG", "png", "image/png"), ("JPEG", "jpg", "image/jpeg"), ("WEBP", "webp", "image/webp")):
            data = inspect_image("image." + extension, image_bytes(fmt))
            self.assertEqual(data["mime_type"], mime)
            self.assertEqual((data["width"], data["height"]), (80, 40))
            self.assertEqual(len(data["source_sha256"]), 64)
            with Image.open(io.BytesIO(data["thumbnail"])) as thumb:
                self.assertEqual(thumb.format, "JPEG")
                self.assertEqual(thumb.getexif(), {})

    def test_exif_orientation_is_applied_to_thumbnail_without_mutating_source_metadata(self):
        data = inspect_image("image.jpg", image_bytes("JPEG", orientation=6))
        self.assertEqual((data["width"], data["height"]), (80, 40))
        with Image.open(io.BytesIO(data["thumbnail"])) as thumb:
            self.assertEqual(thumb.size, (40, 80))

    def test_fake_types_corruption_animated_png_webp_and_paths_are_rejected(self):
        self.rejected("fake.jpg", image_bytes(), "image_format_mismatch")
        self.rejected("fake.png", b"<svg xmlns='test'/>", "invalid_image")
        self.rejected("bad.png", image_bytes()[:40], "invalid_image")
        for fmt, extension in (("PNG", "png"), ("WEBP", "webp")):
            self.rejected("animated." + extension, image_bytes(fmt, animated=True), "animated_image_unsupported")
        for filename in ("../photo.png", "C:\\photo.png", "remote:https.png", "x\x00.png", "x\n.png"):
            self.rejected(filename, image_bytes(), "invalid_filename")
        self.rejected("photo.gif", image_bytes("GIF"), "unsupported_image_format")

    def test_exact_byte_boundary_and_actual_pixel_limit(self):
        jpeg = image_bytes("JPEG")
        padded = jpeg + b"\x00" * (MAX_BYTES - len(jpeg))
        self.assertEqual(inspect_image("photo.jpg", padded)["size_bytes"], MAX_BYTES)
        self.rejected("photo.jpg", padded + b"\x00", "image_too_large")
        self.rejected("empty.png", b"", "empty_file")
        self.rejected("huge.png", image_bytes(size=(5000, 4001)), "image_pixel_limit")
