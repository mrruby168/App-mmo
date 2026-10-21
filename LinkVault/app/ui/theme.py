"""Theme: load UI_SPEC.json tokens, build light/dark QSS, register fonts.

Colours and sizes come from the design pack only — views must not hardcode
hex values (ARCHITECTURE.md section 14).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PyQt6.QtGui import QColor, QFontDatabase
from PyQt6.QtWidgets import QApplication

from app import paths

log = logging.getLogger(__name__)

FALLBACK_COLORS_LIGHT = {
    "primary": "#0F9D7A", "on_primary": "#FFFFFF", "secondary": "#C98A12",
    "background": "#EEF1F5", "surface": "#FFFFFF", "surface_alt": "#F5F7FA",
    "sidebar": "#101827", "text": "#141B2B", "muted_text": "#66728A",
    "border": "#DDE3EC", "success": "#0F9D7A", "warning": "#C98A12",
    "error": "#D64545", "info": "#2F6FE4",
}
FALLBACK_COLORS_DARK = {
    "primary": "#2FD3A4", "on_primary": "#062A21", "secondary": "#F0B63E",
    "background": "#0B0F17", "surface": "#151C2A", "surface_alt": "#1B2434",
    "sidebar": "#0D1320", "text": "#E8EDF6", "muted_text": "#8D99B0",
    "border": "#26314A", "success": "#2FD3A4", "warning": "#F0B63E",
    "error": "#FF7070", "info": "#6B9BFF",
}
LOGO_PALETTE = ["#0F9D7A", "#2F6FE4", "#A855F7", "#E0662F", "#D6336C", "#0C8FB0"]

_tokens: dict = {}


def load_tokens() -> dict:
    """Read UI_SPEC.json; fall back to embedded copies of its colour tokens."""
    global _tokens
    if _tokens:
        return _tokens
    spec_path = paths.resource_path("UI_SPEC.json")
    colors_light = dict(FALLBACK_COLORS_LIGHT)
    colors_dark = dict(FALLBACK_COLORS_DARK)
    palette = list(LOGO_PALETTE)
    try:
        spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        colors_light.update(spec.get("colors", {}).get("light", {}))
        dark_block = spec.get("colors", {}).get("dark")
        if dark_block:
            colors_dark.update(dark_block)
        palette = spec.get("colors", {}).get("logo_palette", palette) or palette
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("UI_SPEC.json not readable (%s); using embedded tokens", exc)
    _tokens = {"light": colors_light, "dark": colors_dark, "logo_palette": palette}
    return _tokens


def colors(mode: str) -> dict:
    t = load_tokens()
    return t["dark"] if mode == "dark" else t["light"]


def logo_color(text: str) -> QColor:
    palette = load_tokens()["logo_palette"]
    idx = sum(ord(c) for c in (text or "?")) % len(palette)
    return QColor(palette[idx])


def load_fonts(app: QApplication) -> None:
    """Register bundled Be Vietnam Pro files when present (spec typography)."""
    font_dir = paths.resource_path("assets/fonts")
    loaded = []
    if font_dir.is_dir():
        for f in sorted(font_dir.glob("*")):
            if f.suffix.lower() in (".ttf", ".otf", ".woff2"):
                fid = QFontDatabase.addApplicationFont(str(f))
                if fid >= 0:
                    loaded += QFontDatabase.applicationFontFamilies(fid)
    family = "Be Vietnam Pro" if any("Be Vietnam" in x for x in loaded) else "Segoe UI"
    font = app.font()
    font.setFamily(family)
    font.setPointSize(10)
    app.setFont(font)


def qss(mode: str) -> str:
    c = colors(mode)
    return f"""
QWidget {{
    background: {c['background']};
    color: {c['text']};
    font-size: 14px;
}}
QLabel {{ background: transparent; }}
#Sidebar {{ background: {c['sidebar']}; }}
#Sidebar QLabel#Brand {{ color: #FFFFFF; font-size: 15px; font-weight: 700; }}
QPushButton[role="nav"] {{
    background: transparent; color: #9AA6BB; border: none; border-radius: 8px;
    padding: 0 10px; text-align: left; font-weight: 500; min-height: 40px;
}}
QPushButton[role="nav"]:hover {{ background: rgba(255,255,255,0.06); color: #FFFFFF; }}
QPushButton[role="nav"]:selected {{ background: rgba(47,211,164,0.14); color: #FFFFFF; }}
QPushButton[role="nav"]:focus {{ border: 2px solid {c['primary']}; }}
#PageTitle {{ font-size: 24px; font-weight: 700; }}
#PageSubtitle {{ color: {c['muted_text']}; font-size: 13px; }}
QPushButton[role="primary"] {{
    background: {c['primary']}; color: {c['on_primary']}; border: none;
    border-radius: 8px; padding: 0 16px; font-weight: 600; min-height: 40px;
}}
QPushButton[role="primary"]:hover {{ background: {c['primary']}; }}
QPushButton[role="primary"]:disabled {{ color: {c['muted_text']}; background: {c['surface_alt']}; }}
QPushButton[role="ghost"] {{
    background: transparent; color: {c['text']}; border: 1px solid {c['border']};
    border-radius: 8px; padding: 0 12px; min-height: 40px; font-weight: 500;
}}
QPushButton[role="ghost"]:hover {{ border-color: {c['primary']}; color: {c['primary']}; }}
QPushButton[role="ghost"]:disabled {{ color: {c['muted_text']}; }}
QPushButton[role="ghost"][variant="danger"] {{ color: {c['error']}; }}
QPushButton[role="ghost"][variant="danger"]:hover {{ border-color: {c['error']}; }}
QPushButton[role="chip"] {{
    background: transparent; color: {c['muted_text']}; border: 1px solid {c['border']};
    border-radius: 16px; padding: 0 12px; min-height: 32px;
}}
QPushButton[role="chip"]:checked {{
    background: {c['text']}; color: {c['surface']}; border-color: {c['text']}; font-weight: 600;
}}
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox {{
    background: {c['surface_alt']}; border: 1px solid {c['border']};
    border-radius: 8px; padding: 8px 12px; min-height: 24px; selection-background-color: {c['primary']};
    selection-color: {c['on_primary']};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus {{
    border: 2px solid {c['primary']};
}}
QLineEdit[invalid="true"], QPlainTextEdit[invalid="true"] {{ border: 2px solid {c['error']}; }}
QFrame[role="card"], QFrame[role="section"], QFrame[role="rowbox"] {{
    background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 12px;
}}
QListView {{
    background: {c['background']}; border: none; outline: none;
}}
QListView::item {{ background: transparent; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['muted_text']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 5px; min-width: 30px; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border: 2px solid {c['border']}; border-radius: 5px;
    background: {c['surface_alt']};
}}
QCheckBox::indicator:checked {{ background: {c['primary']}; border-color: {c['primary']}; }}
QMessageBox {{ background: {c['surface']}; }}
QToolTip {{
    background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']};
    padding: 6px 8px; border-radius: 6px;
}}
QDialog {{ background: {c['surface']}; }}
QDialog QLabel[role="fieldlabel"] {{ color: {c['muted_text']}; font-size: 12px; font-weight: 600; }}
QDialog QLabel[role="fielderror"] {{ color: {c['error']}; font-size: 12px; }}
#ToastSuccess {{ background: {c['success']}; color: {c['on_primary']}; border-radius: 8px; }}
#ToastError {{ background: {c['error']}; color: #FFFFFF; border-radius: 8px; }}
#ToastInfo {{ background: {c['surface']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 8px; }}
QProgressBar {{
    background: {c['surface_alt']}; border: 1px solid {c['border']};
    border-radius: 4px; height: 8px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {c['primary']}; border-radius: 3px; }}
"""


def apply_theme(app: QApplication, mode: str) -> None:
    """mode: 'light' | 'dark' | 'system' (resolved via palette hint)."""
    from PyQt6.QtCore import Qt

    if mode == "system":
        system_dark = QColor(app.palette().color(app.palette().ColorRole.Window)).value() < 0.5
        resolved = "dark" if system_dark else "light"
    else:
        resolved = mode
    app.setStyle("Fusion")
    _apply_palette(app, resolved)
    app.setStyleSheet(qss(resolved))
    return resolved


def _apply_palette(app: QApplication, mode: str) -> None:
    from PyQt6.QtGui import QPalette
    from PyQt6.QtCore import Qt

    c = colors(mode)
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(c["background"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(c["surface"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(c["surface_alt"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(c["text"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(c["text"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(c["surface"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(c["text"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(c["primary"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(c["on_primary"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(c["surface"]))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(c["text"]))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(c["muted_text"]))
    disabled = QColor(c["muted_text"])
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText,
                 QPalette.ColorRole.ButtonText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, disabled)
    app.setPalette(pal)
    app.color_mode = mode  # remembered by widgets that paint manually
