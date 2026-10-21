"""Shared widgets: LogoBadge painting helpers, TagEditor, ToastBar, link utils."""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt, QUrl, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap, QDesktopServices
from PyQt6.QtWidgets import (QCompleter, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QSizePolicy, QVBoxLayout, QWidget)

from app.ui import theme

SAFE_LINK_RE = re.compile(r"^https?://", re.IGNORECASE)


def is_safe_link(link: str | None) -> bool:
    """Only http/https may be opened (REQUIREMENTS F-12, ARCHITECTURE §9)."""
    return bool(link and SAFE_LINK_RE.match(link.strip()))


def open_link(link: str | None) -> bool:
    if not is_safe_link(link):
        return False
    return QDesktopServices.openUrl(QUrl(link.strip()))


def initials(name: str) -> str:
    parts = [p for p in re.split(r"[\s_\-\.]+", (name or "?").strip()) if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def paint_logo(painter: QPainter, rect: QRectF, name: str, pixmap: QPixmap | None,
               radius: float = 12.0) -> None:
    """Draw rounded logo image or letter badge fallback (UI_PREVIEW hint)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path_rect = rect
    if pixmap and not pixmap.isNull():
        scaled = pixmap.scaled(int(rect.width() * 2), int(rect.height() * 2),
                               Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                               Qt.TransformationMode.SmoothTransformation)
        from PyQt6.QtGui import QPainterPath, QBrush
        clip = QPainterPath()
        clip.addRoundedRect(path_rect, radius, radius)
        painter.setClipPath(clip)
        centered = QRectF(
            rect.center().x() - scaled.width() / 4.0,
            rect.center().y() - scaled.height() / 4.0,
            scaled.width() / 2.0, scaled.height() / 2.0,
        )
        painter.drawPixmap(centered, scaled)
    else:
        from PyQt6.QtGui import QPainterPath
        bg = theme.logo_color(name)
        painter.fillPath(_rounded(path_rect, radius), QBrush(bg))
        painter.setPen(QColor("#FFFFFF"))
        f = QFont(painter.font())
        f.setPixelSize(int(rect.height() * 0.38))
        f.setWeight(QFont.Weight.Bold)
        painter.setFont(f)
        painter.drawText(path_rect, Qt.AlignmentFlag.AlignCenter, initials(name))
    painter.restore()


def _rounded(rect: QRectF, radius: float):
    from PyQt6.QtGui import QPainterPath
    p = QPainterPath()
    p.addRoundedRect(rect, radius, radius)
    return p


class TagEditor(QWidget):
    """Input + Enter adds a chip; chips removable (UI_SPEC TagChip)."""

    def __init__(self, placeholder: str = "Nhãn rồi Enter…", parent=None):
        super().__init__(parent)
        self._tags: list[str] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setMinimumHeight(32)
        self.edit.setMaximumWidth(180)
        self.edit.returnPressed.connect(self._commit)
        completer = QCompleter([], self)
        completer.setFilterMode(Qt.MatchFlag.ContainsMatch)
        self.edit.setCompleter(completer)
        self._chips_host = []
        layout.insertWidget(0, self.edit)
        size_policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setSizePolicy(size_policy)

    def _commit(self) -> None:
        text = self.edit.text().strip()
        if text and text.lower() not in [t.lower() for t in self._tags]:
            self._tags.append(text)
            self._add_chip(text)
        self.edit.clear()

    def _add_chip(self, text: str) -> None:
        btn = QPushButton(text)
        btn.setProperty("role", "chip")
        btn.setCheckable(False)
        btn.setToolTip("Bấm để xoá nhãn")
        btn.setMinimumHeight(24)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _=False, t=text: self.remove_tag(t))
        self.layout().insertWidget(self.layout().count() - 1, btn)
        self._chips_host.append((text, btn))

    def remove_tag(self, text: str) -> None:
        self._tags = [t for t in self._tags if t != text]
        for pair in list(self._chips_host):
            if pair[0] == text:
                self.layout().removeWidget(pair[1])
                pair[1].deleteLater()
                self._chips_host.remove(pair)

    def set_tags(self, tags: list[str]) -> None:
        for t in list(self._tags):
            self.remove_tag(t)
        for t in tags or []:
            t = str(t).strip()
            if t:
                self._tags.append(t)
                self._add_chip(t)

    def tags(self) -> list[str]:
        pending = self.edit.text().strip()
        result = list(self._tags)
        if pending and pending.lower() not in [x.lower() for x in result]:
            result.append(pending)
        return result


class ToastBar(QWidget):
    """Transient message strip used by main window (Undo lives here too)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToastInfo")
        self.setVisible(False)
        self.setMinimumHeight(40)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 8, 4)
        layout.setSpacing(12)
        self.label = QLabelWrap("")
        self.label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.label)
        layout.addStretch(1)
        self.action_btn = QPushButton("")
        self.action_btn.setProperty("role", "ghost")
        self.action_btn.setVisible(False)
        self.action_btn.setMinimumHeight(32)
        layout.addWidget(self.action_btn)
        close = QPushButton("✕")
        close.setProperty("role", "ghost")
        close.setFixedWidth(40)
        close.setMinimumHeight(32)
        close.setStyleSheet("background: transparent; border: none;")
        close.clicked.connect(self.hide_toast)
        layout.addWidget(close)
        self._timer = None

    def show_message(self, text: str, kind: str = "info", ms: int = 4000,
                     action_text: str = "", action_cb=None) -> None:
        from PyQt6.QtCore import QTimer

        self.label.setText(text)
        self.setObjectName({"success": "ToastSuccess", "error": "ToastError"}.get(kind, "ToastInfo"))
        style = theme.colors(getattr(self.window(), "color_mode", "light")
                             if hasattr(self.window(), "color_mode") else "light")
        if kind == "error":
            ms = 0  # errors stay until dismissed
        base = {"ToastSuccess": f"background:{style['success']}; color:{style['on_primary']}; border-radius:8px;",
                "ToastError": f"background:{style['error']}; color:#FFFFFF; border-radius:8px;",
                "ToastInfo": f"background:{style['surface']}; color:{style['text']};"
                             f" border:1px solid {style['border']}; border-radius:8px;"}[self.objectName()]
        self.setStyleSheet(base)
        self.label.setStyleSheet(f"background: transparent; border: none; color: inherit;")
        if action_text and action_cb:
            self.action_btn.setText(action_text)
            self.action_btn.setVisible(True)
            try:
                self.action_btn.clicked.disconnect()
            except TypeError:
                pass
            self.action_btn.clicked.connect(lambda: (action_cb(), self.hide_toast()))
        else:
            self.action_btn.setVisible(False)
        self.setVisible(True)
        if self._timer:
            self._timer.stop()
        if ms > 0:
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self.hide_toast)
            self._timer.start(ms)

    def hide_toast(self) -> None:
        self.setVisible(False)


class QLabelWrap(QWidget):
    """Plain label wrapper so toast inherits objectName styling cleanly."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QVBoxLayout, QLabel
        self._lbl = QLabel(text)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._lbl)

    def setText(self, text: str) -> None:  # noqa: N802
        self._lbl.setText(text)

    def text(self) -> str:
        return self._lbl.text()


class EmptyGuide(QWidget):
    """Shown when a tab has zero records (UI_SPEC 'empty' state)."""

    def __init__(self, text: str, add_cb, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(text)
        lbl.setStyleSheet("background: transparent; font-size: 14px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        btn = QPushButton("+ Thêm mục đầu tiên")
        btn.setProperty("role", "primary")
        btn.clicked.connect(add_cb)
        lay.addWidget(lbl)
        lay.addSpacing(12)
        lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
