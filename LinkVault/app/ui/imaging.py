"""Pixmap LRU cache + logo lookup shared by delegates and dialogs."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PyQt6.QtGui import QPixmap

from app import paths

_CACHE: "OrderedDict[tuple[str, int], QPixmap]" = OrderedDict()
LIMIT = 256


def logo_pixmap(data_dir: Path, filename: str | None, size_px: int) -> QPixmap | None:
    """Load a cached display-size pixmap for *filename* (name only, no path)."""
    if not filename:
        return None
    safe = Path(filename).name
    key = (safe, size_px)
    hit = _CACHE.get(key)
    if hit is not None:
        _CACHE.move_to_end(key)
        return hit
    fpath = paths.logos_dir(Path(data_dir)) / safe
    if not fpath.is_file():
        return None
    pm = QPixmap(str(fpath))
    if pm.isNull():
        return None
    scaled = pm.scaled(size_px * 2, size_px * 2, QtAspectRatioKeep(),
                       QtSmooth())
    _CACHE[key] = scaled
    while len(_CACHE) > LIMIT:
        _CACHE.popitem(last=False)
    return scaled


def clear_cache() -> None:
    _CACHE.clear()


def QtAspectRatioKeep():
    from PyQt6.QtCore import Qt
    return Qt.AspectRatioMode.KeepAspectRatio


def QtSmooth():
    from PyQt6.QtCore import Qt
    return Qt.TransformationMode.SmoothTransformation
