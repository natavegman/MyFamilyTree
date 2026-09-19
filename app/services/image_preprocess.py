import tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

MAX_DIMENSION = 2048


def preprocess_for_ocr(source_path: str) -> Path:
    """Prepare scan for OCR: grayscale, contrast, sharpen, resize if needed."""
    source = Path(source_path)
    image = Image.open(source).convert("L")
    image = image.filter(ImageFilter.MedianFilter(size=3))
    image = ImageEnhance.Contrast(image).enhance(1.6)
    image = ImageEnhance.Sharpness(image).enhance(1.4)

    if max(image.size) > MAX_DIMENSION:
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

    suffix = source.suffix.lower() or ".jpg"
    temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temp_path = Path(temp_file.name)
    temp_file.close()

    save_format = "JPEG" if suffix in {".jpg", ".jpeg"} else "PNG"
    image.save(temp_path, format=save_format, quality=92)
    return temp_path


def crop_header(source_path: str, height_ratio: float = 0.14) -> Path:
    """Crop top center band — metric book year line, avoid page numbers at corners."""
    source = Path(source_path)
    image = Image.open(source).convert("L")
    width, height = image.size
    left = int(width * 0.1)
    right = int(width * 0.9)
    bottom = max(1, int(height * height_ratio))
    crop = image.crop((left, 0, right, bottom))
    crop = ImageEnhance.Contrast(crop).enhance(2.0)
    crop = ImageEnhance.Sharpness(crop).enhance(2.0)

    temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    temp_path = Path(temp_file.name)
    temp_file.close()
    crop.save(temp_path, format="JPEG", quality=95)
    return temp_path
