import cv2
import numpy as np
import time
from pathlib import Path


def image_hash(image: cv2.Mat, hash_size: int = 8) -> int:
    resized = cv2.resize(image, (hash_size + 1, hash_size))
    diff = resized[:, 1:] > resized[:, :-1]
    return sum(2 ** i for i, v in enumerate(diff.flatten()) if v)


def ensure_dir(folder: str) -> Path:
    p = Path(folder)
    p.mkdir(parents=True, exist_ok=True)
    return p


def current_epoch_ms() -> int:
    return int(time.time() * 1000)
