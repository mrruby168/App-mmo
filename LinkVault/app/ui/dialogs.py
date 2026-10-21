"""EntryDialog (add/edit with validation) and ConfirmDialog (UI_SPEC S-07)."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QPlainTextEdit, QPushButton, QSlider,
                             QVBoxLayout, QWidget)

from app import paths
from app.models import Entry, Note
from app.ui import theme
from app.ui.widgets import TagEditor, initials, paint_logo

KIND_LABELS = {"mmo": "dự án", "ai": "web AI", "airdrop": "kèo airdrop", "tool": "AI"}
AIRDROP_STATUSES = ["Mới", "Đang farm", "Chờ snapshot", "Đã nhận", "Hết hạn"]


class LogoPicker(QPushButton):
    """64px square button showing the chosen logo or letter badge."""

    def __init__(self, data_dir: Path, parent=None):
        super().__init__(parent)
        self.data_dir = Path(data_dir)
        self.logo_name: str | None = None
        self.setFixedSize(64, 64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Chọn ảnh logo")
        self.setStyleSheet("border: none; background: transparent;")
        self.clicked.connect(self._pick)
        self._pending_pixmap: QPixmap | None = None

    def set_entry(self, entry: Entry) -> None:
        self.logo_name = entry.logo
        self._pending_pixmap = None
        self.update()

    def take_pending_file(self) -> tuple[str | None, Path | None]:
        """Return (logo_name, source_path_to_copy) for the caller to persist."""
        return self.logo_name, getattr(self, "_source_path", None)

    def _pick(self) -> None:
        fname, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh logo", str(Path.home()),
            "Ảnh (*.png *.jpg *.jpeg *.gif *.webp *.bmp)")
        if not fname:
            return
        pm = QPixmap(fname)
        if pm.isNull():
            return
        self._pending_pixmap = pm
        self._source_path = Path(fname)
        digest = abs(hash((fname, pm.width(), pm.height()))) % (10 ** 8)
        suffix = Path(fname).suffix.lower().lstrip(".") or "png"
        self.logo_name = f"{digest:08d}.{suffix}"
        self.update()

    def paintEvent(self, event):  # noqa: N802
        from PyQt6.QtGui import QPainter
        from PyQt6.QtCore import QRectF
        painter = QPainter(self)
        rect = QRectF(0, 0, self.width(), self.height())
        text = "?"
        dlg = self.findParentEntryDialog()
        if dlg is not None:
            text = dlg.name_edit.text() or "?"
        pm = self._pending_pixmap
        if pm is None and self.logo_name:
            from app.ui.imaging import logo_pixmap
            pm = logo_pixmap(self.data_dir, self.logo_name, 64)
        paint_logo(painter, rect, text, pm)

    def findParentEntryDialog(self):
        w = self.parent()
        while w is not None and not isinstance(w, EntryDialog):
            w = w.parent()
        return w

    def refresh(self) -> None:
        self.update()


class FieldRow(QWidget):
    """Label + input + inline error message (dialog 'error' state)."""

    def __init__(self, label_text: str, widget: QWidget, error_label_id: str = "",
                 parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setProperty("role", "fieldlabel")
        self.error = QLabel("")
        self.error.setProperty("role", "fielderror")
        self.error.setVisible(False)
        lay.addWidget(lbl)
        lay.addWidget(widget)
        lay.addWidget(error)
        self.widget = widget

    def set_error(self, msg: str) -> None:
        self.error.setText(msg)
        self.error.setVisible(bool(msg))
        prop = "invalid" if msg else ""
        target = self.widget
        if isinstance(target, QLineEdit):
            target.setProperty("invalid", "true" if msg else "")
            target.style().unpolish(target)
            target.style().polish(target)


class EntryDialog(QDialog):
    """Add/edit an Entry. Fields depend on kind (ARCHITECTURE §6)."""

    def __init__(self, kind: str, data_dir: Path, entry: Entry | None = None,
                 parent=None):
        super().__init__(parent)
        self.kind = kind
        self.data_dir = Path(data_dir)
        self.entry_in = entry
        object_name = "Thêm" if entry is None else "Sửa"
        noun = KIND_LABELS.get(kind, "mục")
        self.setWindowTitle(f"{object_name} {noun} — Link Vault")
        self.setModal(True)
        self.setMinimumWidth(560)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 16)
        root.setSpacing(14)

        title = QLabel(f"{object_name} {noun}")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        root.addWidget(title)

        top = QHBoxLayout()
        top.setSpacing(14)
        self.logo = LogoPicker(self.data_dir)
        top.addWidget(self.logo)
        top.addStretch(1)
        root.addLayout(top)

        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("nameEdit")
        self.name_edit.setPlaceholderText("Tên dự án (bắt buộc)")
        self.row_name = FieldRow("Tên dự án", self.name_edit)
        root.addWidget(self.row_name)

        show_link = kind in ("mmo", "ai", "tool")
        self.row_link = FieldRow("Link", QLineEdit())
        self.link_edit = self.row_link.widget
        self.link_edit.setObjectName("linkEdit")
        self.link_edit.setPlaceholderText("https://…")
        self.row_link.setVisible(show_link)
        root.addWidget(self.row_link)

        if kind in ("mmo", "ai"):
            self.row_how = FieldRow("Cách làm", QPlainTextEdit())
            self.how_edit = self.row_how.widget
            self.how_edit.setMaximumHeight(90)
            root.addWidget(self.row_how)

            prog_wrap = QWidget()
            pl = QHBoxLayout(prog_wrap)
            pl.setContentsMargins(0, 0, 0, 0)
            self.progress_slider = QSlider(Qt.Orientation.Horizontal)
            self.progress_slider.setRange(0, 100)
            self.progress_value = QLabel("0%")
            self.progress_value.setMinimumWidth(48)
            self.progress_slider.valueChanged.connect(
                lambda v: self.progress_value.setText(f"{v}%"))
            pl.addWidget(self.progress_slider)
            pl.addWidget(self.progress_value)
            self.row_progress = FieldRow("Tiến độ", prog_wrap)
            root.addWidget(self.row_progress)

            self.tools = TagEditor()
            self.row_tools = FieldRow("Công cụ hỗ trợ", self.tools)
            root.addWidget(self.row_tools)

        if kind == "airdrop":
            self.status_combo = QComboBox()
            self.status_combo.addItems(AIRDROP_STATUSES)
            self.row_status = FieldRow("Trạng thái", self.status_combo)
            root.addWidget(self.row_status)

        if kind == "tool":
            self.effect_edit = QPlainTextEdit()
            self.effect_edit.setMaximumHeight(90)
            self.row_effect = FieldRow("Tác dụng", self.effect_edit)
            root.addWidget(self.row_effect)

        show_note = kind != "tool"
        self.row_note = FieldRow("Note", QPlainTextEdit())
        self.note_edit = self.row_note.widget
        self.note_edit.setMaximumHeight(90)
        self.row_note.setVisible(show_note)
        root.addWidget(self.row_note)

        btns = QHBoxLayout()
        self.delete_btn = QPushButton("Xoá dự án")
        self.delete_btn.setProperty("role", "ghost")
        self.delete_btn.setProperty("variant", "danger")
        self.delete_btn.setVisible(entry is not None)
        self.delete_btn.clicked.connect(self._on_delete)
        btns.addWidget(self.delete_btn)
        btns.addStretch(1)
        cancel = QPushButton("Huỷ")
        cancel.setProperty("role", "ghost")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Lưu")
        save.setProperty("role", "primary")
        save.setDefault(True)
        save.clicked.connect(self._on_save)
        btns.addWidget(cancel)
        btns.addWidget(save)
        root.addLayout(btns)

        if entry:
            self._load(entry)

        # Enter saves, Esc cancels (UI_SPEC EntryDialog interaction)
        for w in (self.name_edit, self.link_edit):
            w.returnPressed.connect(self._on_save)
        self.name_edit.textEdited.connect(lambda _t="": self.logo.refresh())

    def _load(self, e: Entry) -> None:
        self.name_edit.setText(e.name)
        self.link_edit.setText(e.link or "")
        self.logo.logo_name = e.logo
        if self.kind in ("mmo", "ai"):
            self.how_edit.setPlainText(e.how_to or "")
            self.progress_slider.setValue(int(e.progress or 0))
            self.tools.set_tags(e.tools or [])
        if self.kind == "airdrop":
            idx = AIRDROP_STATUSES.index(e.status) if e.status in AIRDROP_STATUSES else 0
            self.status_combo.setCurrentIndex(idx)
        if self.kind == "tool":
            self.effect_edit.setPlainText(e.effect or "")
        if self.kind != "tool":
            self.note_edit.setPlainText(e.note or "")

    def _validate(self) -> bool:
        ok = True
        name = self.name_edit.text().strip()
        if not name:
            self.row_name.set_error("Tên là bắt buộc.")
            ok = False
        else:
            self.row_name.set_error("")
        link = self.link_edit.text().strip()
        if self.row_link.isVisible():
            if link and not link.lower().startswith(("http://", "https://")):
                self.row_link.set_error("Link phải bắt đầu bằng http:// hoặc https://")
                ok = False
            else:
                self.row_link.set_error("")
        return ok

    def _on_save(self) -> None:
        if not self._validate():
            return
        result = Entry(
            kind=self.kind,
            name=self.name_edit.text().strip(),
            link=self.link_edit.text().strip(),
            logo=self.logo.logo_name,
            how_to=self.how_edit.toPlainText().strip() if self.kind in ("mmo", "ai") else "",
            progress=self.progress_slider.value() if self.kind in ("mmo", "ai") else 0,
            tools=self.tools.tags() if self.kind in ("mmo", "ai") else [],
            note=self.note_edit.toPlainText().strip() if self.kind != "tool" else "",
            status=self.status_combo.currentText() if self.kind == "airdrop" else "",
            effect=self.effect_edit.toPlainText().strip() if self.kind == "tool" else "",
        )
        if self.entry_in:
            result.id = self.entry_in.id
            result.sort_order = self.entry_in.sort_order
        self.result_entry = result
        self.accept()

    def _on_delete(self) -> None:
        self.delete_requested = True
        self.accept()

    delete_requested = False
    result_entry: Entry | None = None


class ConfirmDialog(QDialog):
    def __init__(self, title: str, message: str, confirm_text: str = "Đồng ý",
                 danger: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 16)
        lay.setSpacing(16)
        t = QLabel(title)
        t.setStyleSheet("font-size: 18px; font-weight: 700;")
        m = QLabel(message)
        m.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(m)
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Huỷ")
        cancel.setProperty("role", "ghost")
        cancel.clicked.connect(self.reject)
        yes = QPushButton(confirm_text)
        yes.setProperty("role", "primary" if not danger else "ghost")
        if danger:
            yes.setProperty("variant", "danger")
            yes.setStyleSheet(
                "QPushButton[variant=danger]{background:"
                + theme.colors(getattr(self.window(), "color_mode", "light"))["error"]
                + "; color:#FFFFFF; border:none; border-radius:8px; padding:0 16px;"
                  "min-height:40px; font-weight:600;}")
        yes.setDefault(True)
        yes.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addWidget(yes)
        lay.addLayout(btns)
