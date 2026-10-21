"""Tab Note: master–detail (list + editor), autosave 800 ms, pin & delete."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QRect, QSize, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QLabel,
                             QLineEdit, QListView, QPlainTextEdit, QPushButton,
                             QStyle, QStyledItemDelegate, QVBoxLayout, QWidget)

from app.models import Note, NoteListModel
from app.ui import theme
from app.ui.dialogs import ConfirmDialog
from app.ui.widgets import EmptyGuide

log = logging.getLogger(__name__)

ROW_H = 72


def humanize_date(iso: str) -> str:
    from datetime import datetime, timezone
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return iso[:10]
    local = dt.astimezone()
    today = local.date()
    delta = (today - local.date()).days
    if delta == 0:
        return "Hôm nay"
    if delta == 1:
        return "Hôm qua"
    return local.strftime("%d/%m/%Y")


class NoteRowDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):  # noqa: N802
        return QSize(option.rect.width(), ROW_H)

    def paint(self, painter: QPainter, option, index):  # noqa: N802
        app = QApplicationInstance()
        c = theme.colors(getattr(app, "resolved_mode", "light"))
        note: Note | None = index.data(NoteListModel.ROLES[Qt.ItemDataRole.UserRole + 6])
        if note is None:
            return
        rect = option.rect.adjusted(2, 2, -2, -6)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = option.state & QStyle.StateFlag.State_Selected
        painter.setPen(QPen(QColor(c["primary"]) if selected else QColor(c["border"]), 1))
        painter.setBrush(QColor(c["surface"]))
        painter.drawRoundedRect(rect, 10, 10)

        x = rect.left() + 14
        w = rect.width() - 28
        title_font = QFont(painter.font())
        title_font.setPixelSize(14)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor(c["text"]))
        fm = QFontMetrics(title_font)
        pin = "📌 " if note.pinned else ""
        date_f = QFont(painter.font())
        date_f.setPixelSize(12)
        date_w = QFontMetrics(date_f).horizontalAdvance(humanize_date(note.updated_at)) + 4
        title_rect = QRect(x, rect.top() + 8, w - date_w, 22)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         fm.elidedText(pin + note.title, Qt.TextElideMode.ElideRight,
                                       title_rect.width()))
        painter.setFont(date_f)
        painter.setPen(QColor(c["muted_text"]))
        painter.drawText(QRect(rect.right() - 14 - date_w, rect.top() + 8, date_w, 22),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                         humanize_date(note.updated_at))

        body_font = QFont(painter.font())
        body_font.setPixelSize(13)
        painter.setFont(body_font)
        painter.setPen(QColor(c["muted_text"]))
        preview = (note.body or "").replace("\n", " ").strip()
        bfm = QFontMetrics(body_font)
        painter.drawText(QRect(x, rect.top() + 32, w, 20),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         bfm.elidedText(preview, Qt.TextElideMode.ElideRight, w))
        painter.restore()


def QApplicationInstance():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance()


class NoteView(QWidget):
    count_changed = pyqtSignal(str, int)

    def __init__(self, db, data_dir: Path, parent=None):
        super().__init__(parent)
        self.db = db
        self.model = NoteListModel(db, self)
        self.current_id: int | None = None
        self._loading = False
        self._build()
        self.model.reload()
        self._sync_empty()
        self.model.modelReset.connect(self._sync_empty)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 16)
        root.setSpacing(12)

        head = QHBoxLayout()
        col = QVBoxLayout()
        title = QLabel("Note")
        title.setObjectName("PageTitle")
        sub = QLabel("Ghi chú dài, tự lưu khi gõ")
        sub.setObjectName("PageSubtitle")
        col.addWidget(title)
        col.addWidget(sub)
        head.addLayout(col)
        head.addStretch(1)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm trong ghi chú (Ctrl+F)")
        self.search.setFixedWidth(220)
        self.search.setClearButtonEnabled(True)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(200)
        self._debounce.timeout.connect(
            lambda: self.model.set_search(self.search.text().strip()))
        self.search.textChanged.connect(self._debounce.start)
        head.addWidget(self.search)
        btn = QPushButton("+ Ghi chú mới")
        btn.setProperty("role", "primary")
        btn.clicked.connect(self.add_note)
        head.addWidget(btn)
        root.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(16)

        left = QVBoxLayout()
        self.list = QListView()
        self.list.setModel(self.model)
        self.list.setItemDelegate(NoteRowDelegate(self.list))
        self.list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.list.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self.list.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.list.setMinimumWidth(280)
        self.list.setMaximumWidth(340)
        self.list.selectionModel().currentChanged.connect(self._select_row)
        left.addWidget(self.list)
        body.addLayout(left)

        right = QVBoxLayout()
        panel = QFrame()
        panel.setProperty("role", "section")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(16, 16, 16, 12)
        pl.setSpacing(8)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Tiêu đề ghi chú")
        self.title_edit.setStyleSheet(
            "font-size: 18px; font-weight: 700; border: none; background: transparent;"
            "border-bottom: 1px solid palette(mid); border-radius: 0;")
        self.meta = QLabel("")
        self.meta.setStyleSheet("background: transparent; color: palette(mid); font-size: 12px;")
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Nội dung…")
        self.editor.setTabChangesFocus(True)
        pl.addWidget(self.title_edit)
        pl.addWidget(self.meta)
        pl.addWidget(self.editor, 1)

        actions = QHBoxLayout()
        self.pin_btn = QPushButton("Ghim")
        self.pin_btn.setProperty("role", "ghost")
        self.pin_btn.setCheckable(True)
        self.pin_btn.clicked.connect(self._toggle_pin)
        del_btn = QPushButton("Xoá")
        del_btn.setProperty("role", "ghost")
        del_btn.setProperty("variant", "danger")
        del_btn.clicked.connect(self._delete_current)
        save_btn = QPushButton("Lưu")
        save_btn.setProperty("role", "primary")
        save_btn.setMinimumHeight(32)
        save_btn.clicked.connect(self._save_now)
        actions.addWidget(self.pin_btn)
        actions.addWidget(del_btn)
        actions.addStretch(1)
        actions.addWidget(save_btn)
        pl.addLayout(actions)
        right.addWidget(panel)
        body.addLayout(right, 1)
        root.addLayout(body, 1)

        self.empty = EmptyGuide("Chưa có ghi chú nào.\nBấm “+ Ghi chú mới” để bắt đầu.",
                                self.add_note, self)
        root.addWidget(self.empty, 1)
        self.empty.setVisible(False)

        self._autosave = QTimer(self)
        self._autosave.setSingleShot(True)
        self._autosave.setInterval(800)
        self._autosave.timeout.connect(self._save_now)
        self.title_edit.textEdited.connect(self._schedule_save)
        self.editor.textChanged.connect(self._schedule_save)

    # ------------------------------------------------------------- selection
    def _select_row(self, index) -> None:
        if not index.isValid():
            return
        note = index.data(NoteListModel.ROLES[Qt.ItemDataRole.UserRole + 6])
        self._load(note)

    def _load(self, note: Note) -> None:
        self._loading = True
        self.current_id = note.id
        self.title_edit.setText(note.title)
        self.editor.setPlainText(note.body)
        self.pin_btn.setChecked(note.pinned)
        self.pin_btn.setText("Đã ghim" if note.pinned else "Ghim")
        self.meta.setText(f"Sửa lần cuối: {humanize_date(note.updated_at)} · Tự động lưu")
        self._loading = False

    def _schedule_save(self) -> None:
        if not self._loading and self.current_id is not None:
            self._autosave.start()

    def _save_now(self) -> None:
        if self.current_id is None or self._loading:
            return
        note = self.db.get_note(self.current_id)
        if not note:
            return
        n = Note.from_dict(note)
        n.title = self.title_edit.text().strip() or "Ghi chú"
        n.body = self.editor.toPlainText()
        n.pinned = self.pin_btn.isChecked()
        self.model.update(n)
        row, _ = self.model.find_by_id(n.id)
        if row >= 0:
            idx = self.model.index(row)
            self.list.setCurrentIndex(idx)
        self.meta.setText(f"Sửa lần cuối: {humanize_date(self.db.get_note(n.id)['updated_at'])} · Đã lưu")

    def _toggle_pin(self) -> None:
        checked = self.pin_btn.isChecked()
        self.pin_btn.setText("Đã ghim" if checked else "Ghim")
        self._save_now()

    def _delete_current(self) -> None:
        if self.current_id is None:
            return
        data = self.db.get_note(self.current_id)
        if not data:
            return
        dlg = ConfirmDialog("Xoá ghi chú",
                            f"Bạn chắc chắn muốn xoá “{data['title']}”?\n"
                            "Bạn có thể Hoàn tác ngay sau khi xoá.",
                            confirm_text="Xoá", danger=True, parent=self.window())
        if dlg.exec():
            removed = self.model.remove(self.current_id)
            self.current_id = None
            self.title_edit.clear()
            self.editor.clear()
            if removed is not None:
                self.delete_occurred.emit(removed)
            self.count_changed.emit("note", self.db.conn.execute(
                "SELECT COUNT(*) c FROM notes").fetchone()["c"])

    delete_occurred = pyqtSignal(object)

    def undo_delete(self, note: Note) -> None:
        self.model.restore(note)
        self.count_changed.emit("note", self.db.conn.execute(
            "SELECT COUNT(*) c FROM notes").fetchone()["c"])

    def add_note(self) -> None:
        n = Note(title="Ghi chú mới", body="")
        new_id = self.model.add(n)
        self.count_changed.emit("note", self.db.conn.execute(
            "SELECT COUNT(*) c FROM notes").fetchone()["c"])
        row, _ = self.model.find_by_id(new_id)
        if row >= 0:
            self.list.setCurrentIndex(self.model.index(row))
            self.title_edit.setFocus()
            self.title_edit.selectAll()

    def _sync_empty(self) -> None:
        empty = self.model.rowCount() == 0 and self.model._total == 0
        visible = not empty
        self.list.setVisible(visible)
        for child in self.findChildren(QFrame):
            if child.property("role") == "section":
                child.setVisible(visible)
        self.empty.setVisible(empty)
        self.count_changed.emit("note", self.db.conn.execute(
            "SELECT COUNT(*) c FROM notes").fetchone()["c"])

    def refresh(self) -> None:
        keep = self.current_id
        self.model.reload()
        if keep is not None:
            row, _ = self.model.find_by_id(keep)
            if row >= 0:
                self.list.setCurrentIndex(self.model.index(row))
        self._sync_empty()

    def keyPressEvent(self, event):  # noqa: N802
        from PyQt6.QtGui import QKeySequence
        if event.matches(QKeySequence.StandardKey.Find):
            self.search.setFocus()
            self.search.selectAll()
            return
        super().keyPressEvent(event)
