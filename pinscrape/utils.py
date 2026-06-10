import os
import cv2
import numpy as np
import time
from pathlib import Path
from urllib.parse import urlparse

# Network safety defaults shared across the scraper.
REQUEST_TIMEOUT = (5, 30)  # (connect, read) seconds
MAX_IMAGE_BYTES = 25 * 1024 * 1024  # 25 MiB cap to avoid decompression bombs

# Hosts we are willing to fetch images from. Pinterest serves images from the
# pinimg.com CDN and a few pinterest.* domains. Any suffix match of these is allowed.
ALLOWED_IMAGE_HOST_SUFFIXES = (
    "pinimg.com",
    "pinterest.com",
    "pinterest.co.uk",
    "pinterest.ca",
    "pinterest.fr",
    "pinterest.de",
    "pinterest.jp",
)


def is_allowed_image_url(url: str) -> bool:
    """Return True only for https URLs pointing at a trusted Pinterest CDN host.

    Guards against SSRF: scraped JSON could contain arbitrary URLs (internal
    hosts, file://, http://169.254.169.254/, etc.).
    """
    try:
        parsed = urlparse(str(url))
    except Exception:
        return False
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    return any(host == s or host.endswith("." + s) for s in ALLOWED_IMAGE_HOST_SUFFIXES)


def safe_image_path(url: str, folder) -> Path:
    """Derive a safe output Path for an image URL inside ``folder``.

    Returns None if the basename is empty, contains path separators / ``..``,
    or if the resolved path escapes the target folder (path traversal guard).
    """
    folder = Path(folder)
    name = os.path.basename(urlparse(str(url)).path)
    if not name or name in (".", "..") or os.sep in name or (os.altsep and os.altsep in name):
        return None
    if "/" in name or "\\" in name:
        return None

    target = (folder / name)
    try:
        resolved_folder = folder.resolve()
        resolved_target = target.resolve()
    except Exception:
        return None
    # resolved_target must be inside resolved_folder.
    if resolved_folder != resolved_target and resolved_folder not in resolved_target.parents:
        return None
    return target


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
