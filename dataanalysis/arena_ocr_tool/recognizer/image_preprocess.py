from __future__ import annotations

from PIL import Image, ImageEnhance, ImageFilter


def load_image(path: str) -> Image.Image:
    Image.MAX_IMAGE_PIXELS = None
    return Image.open(path).convert("RGB")


def prepare_for_ocr(image: Image.Image) -> Image.Image:
    """Return a sharpened copy for OCR while keeping the original untouched."""
    work = image.convert("RGB")
    if max(work.size) < 1800:
        work = work.resize((work.width * 2, work.height * 2), Image.Resampling.LANCZOS)
    work = ImageEnhance.Contrast(work).enhance(1.25)
    work = ImageEnhance.Sharpness(work).enhance(1.35)
    return work.filter(ImageFilter.SHARPEN)

