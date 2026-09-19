import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.services.metric_layout import CellRegion, header_region


def load_gray(image_path: str) -> np.ndarray:
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")
    return image


def preprocess_gray(gray: np.ndarray) -> np.ndarray:
    denoised = cv2.fastNlMeansDenoising(gray, h=8)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    return enhanced


def crop_region(gray: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> np.ndarray:
    h, w = gray.shape[:2]
    x1, x2 = max(0, x1), min(w, x2)
    y1, y2 = max(0, y1), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return np.zeros((1, 1), dtype=np.uint8)
    return gray[y1:y2, x1:x2]


def save_crop(region: np.ndarray) -> Path:
    temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    path = Path(temp.name)
    temp.close()
    if region.size == 0:
        region = np.zeros((10, 10), dtype=np.uint8)
    Image.fromarray(region).save(path)
    return path


def extract_header_crop(image_path: str) -> Path:
    gray = preprocess_gray(load_gray(image_path))
    h, w = gray.shape[:2]
    x1, y1, x2, y2 = header_region(w, h)
    return save_crop(crop_region(gray, x1, y1, x2, y2))


def extract_cell_crops(image_path: str, cells: list[CellRegion]) -> list[tuple[CellRegion, Path]]:
    gray = preprocess_gray(load_gray(image_path))
    result: list[tuple[CellRegion, Path]] = []
    for cell in cells:
        crop = crop_region(gray, cell.x1, cell.y1, cell.x2, cell.y2)
        result.append((cell, save_crop(crop)))
    return result
