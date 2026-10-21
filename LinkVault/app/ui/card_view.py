"""Tab Airdrop / Tool AI: card grid drawn by a delegate on QListView.

Grid columns adapt to viewport width (UI_SPEC EntryCard, responsive rule).
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QModelIndex, QRect, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLabel, QLineEdit,
                             QListView, QPushButton, QVBoxLayout, QWidget,
                             QStyledItemDelegate)

from app import paths
from app.models import Entry, EntryListModel
from app.ui import theme
from app.ui.dialogs import AIRDROP_STATUSES, ConfirmDialog, EntryDialog
from app.ui.imaging import logo_pixmap
from app.ui.widgets import EmptyGuide, is_safe_link, open_link

CARD_W = 270
CARD_H = 150
LOGO_PX = 48

STATUS_ROLE_COLORS = {
    "Mới": "info",
    "Đang farm": "success",
    "Chờ snapshot": "warning",
    "Đã nhận": "success",
    "Hết hạn": "error",
}


class CardDelegate(QStyledItemDelegate):
    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)
    link_clicked = pyqtSignal(int)
    status_clicked = pyqtSignal(int)

    def __init__(self, data_dir: Path, kind: str, parent=None):
        super().__init__(parent)
        self.data_dir = Path(data_dir)
        self.kind = kind
        self._action_rects: dict[int, dict[str, QRect]] = {}
        self._link_rects: dict[int, QRect] = {}

    def sizeHint(self, option, index):  # noqa: N802
        return QSize(CARD_W, CARD_H)

    def paint(self, painter: QPainter, option, index):  # noqa: N802
        app = __import__("PyQt6.QtWidgets", fromlist=["QApplication"]).QApplication.instance()
        c = theme.colors(getattr(app, "resolved_mode", "light"))
        entry: Entry | None = index.data(EntryListModel.REVERSE["entry"])
        if entry is None:
            return
        rect = option.rect.adjusted(6, 6, -6, -6)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        hover = option.state & QStyleStateMouseOver()
        border = QColor(c["primary"]) if hover else QColor(c["border"])
        painter.setPen(QPen(border, 1))
        painter.setBrush(QColor(c["surface"]))
        painter.drawRoundedRect(QRectF(rect), 12, 12)

        pad = 16
        x = rect.left() + pad
        y = rect.top() + pad
        logo_rect = QRectF(x, y, LOGO_PX, LOGO_PX)
        pm = logo_pixmap(self.data_dir, entry.logo, LOGO_PX)
        from app.ui.widgets import paint_logo
        paint_logo(painter, logo_rect, entry.name, pm)

        text_x = x + LOGO_PX + 12
        f_name = QFont(painter.font())
        f_name.setPixelSize(15)
        f_name.setWeight(QFont.Weight.DemiBold)
        fm = QFontMetrics(f_name)
        badge_w = 0
        if self.kind == "airdrop" and entry.status:
            fb = QFont(painter.font())
            fb.setPixelSize(12)
            fb.setWeight(QFont.Weight.DemiBold)
            badge_w = QFontMetrics(fb).horizontalAdvance(entry.status) + 24
        name_w = rect.right() - pad - text_x - badge_w - 8
        name_rect = QRect(text_x, int(y), max(40, name_w), 24)
        painter.setFont(f_name)
        painter.setPen(QColor(c["text"]))
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         fm.elidedText(entry.name, Qt.TextElideMode.ElideRight, name_rect.width()))

        if self.kind == "airdrop" and entry.status:
            role = STATUS_ROLE_COLORS.get(entry.status, "info")
            col = QColor(c[role])
            bw = badge_w
            bx = rect.right() - pad - bw
            badge = QRect(bx, int(y + 2), bw, 22)
            painter.setPen(QPen(col, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(badge), 11, 11)
            fb = QFont(painter.font())
            fb.setPixelSize(12)
            fb.setWeight(QFont.Weight.DemiBold)
            painter.setFont(fb)
            painter.setPen(col)
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, entry.status)

        yy = y + LOGO_PX + 10
        if self.kind == "tool" and entry.link:
            f_link = QFont(painter.font())
            f_link.setPixelSize(12)
            painter.setFont(f_link)
            painter.setPen(QColor(c["info"]))
            link_rect = QRect(int(x), int(yy), rect.width() - 2 * pad, 18)
            painter.drawText(link_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             QFontMetrics(f_link).elidedText(
                                 entry.link, Qt.TextElideMode.ElideRight, link_rect.width()))
            self._link_rects[index.row()] = link_rect
            yy += 24
        elif entry.link and self.kind == "airdrop":
            self._link_rects[index.row()] = QRect()

        body_key = "effect" if self.kind == "tool" else "note"
        body = getattr(entry, body_key, "") or ""
        if body:
            box = QRect(int(x), int(yy), rect.width() - 2 * pad,
                        rect.bottom() - pad - int(yy) - 40)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(c["surface_alt"]))
            painter.drawRoundedRect(QRectF(box), 8, 8)
            painter.setBrush(QColor(c["secondary"]))
            painter.drawRect(box.left(), box.top(), 3, box.height())
            self._draw_wrapped(painter, box.adjusted(10, 4, -6, -4), body,
                               c["muted_text"], 13, 3)

        ay = rect.bottom() - pad - 32
        self._action_rects[index.row()] = {
            "edit": QRect(int(x), ay, 50, 32),
            "del": QRect(int(x) + 58, ay, 50, 32),
        }
        if self.kind == "airdrop":
            self._action_rects[index.row()]["status"] = QRect(
                rect.right() - pad - 110, ay, 110, 32)
        self._mini_btn(painter, self._action_rects[index.row()]["edit"], "Sửa", c)
        self._mini_btn(painter, self._action_rects[index.row()]["del"], "Xoá", c, danger=True)
        if "status" in self._action_rects[index.row()]:
            self._mini_btn(painter, self._action_rects[index.row()]["status"],
                           entry.status or "Đổi trạng thái", c)
        painter.restore()

    def _mini_btn(self, painter: QPainter, r: QRect, text: str, c: dict,
                  danger: bool = False):
        painter.setPen(QPen(QColor(c["error"] if danger else c["border"]), 1))
        painter.setBrush(QColor(c["surface"]))
        painter.drawRoundedRect(QRectF(r), 8, 8)
        f = QFont(painter.font())
        f.setPixelSize(12)
        painter.setFont(f)
        painter.setPen(QColor(c["error"] if danger else c["text"]))
        fm = QFontMetrics(f)
        painter.drawText(r, Qt.AlignmentFlag.AlignCenter,
                         fm.elidedText(text, Qt.TextElideMode.ElideRight, r.width() - 8))

    def _draw_wrapped(self, painter: QPainter, rect: QRect, text: str, color: str,
                      px: int, max_lines: int) -> None:
        f = QFont(painter.font())
        f.setPixelSize(px)
        painter.setFont(f)
        painter.setPen(QColor(color))
        fm = QFontMetrics(f)
        line_h = int(fm.height() * 1.35)
        words = text.split()
        lines: list[str] = []
        cur = ""
        for word in words:
            trial = (cur + " " + word).strip()
            if fm.horizontalAdvance(trial) <= rect.width() or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        truncated = len(lines) > max_lines
        lines = lines[:max_lines]
        if lines and truncated:
            lines[-1] = lines[-1][: max(1, len(lines[-1]) - 1)] + "…"
        y = rect.top()
        for ln in lines:
            painter.drawText(QRect(rect.left(), y, rect.width(), line_h),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, ln)
            y += line_h

    def editorEvent(self, event, model, option, index):  # noqa: N802
        from PyQt6.QtCore import QEvent

        entry = index.data(EntryListModel.REVERSE["entry"])
        if entry is None:
            return False
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        rects = self._action_rects.get(index.row(), {})
        if event.type() == QEvent.Type.MouseButtonRelease:
            if "edit" in rects and rects["edit"].contains(pos):
                self.edit_clicked.emit(entry.id)
                return True
            if "del" in rects and rects["del"].contains(pos):
                self.delete_clicked.emit(entry.id)
                return True
            if "status" in rects and rects["status"].contains(pos):
                self.status_clicked.emit(entry.id)
                return True
            link_rect = self._link_rects.get(index.row())
            if link_rect and link_rect.contains(pos) and is_safe_link(entry.link):
                self.link_clicked.emit(entry.id)
                return True
        return False


def QStyleStateMouseOver():
    from PyQt6.QtWidgets import QStyle
    return QStyle.StateFlag.State_MouseOver


class CardView(QWidget):
    """Header + optional filter chips + adaptive card grid (S-03/S-04)."""

    export_requested = pyqtSignal(str)
    import_requested = pyqtSignal(str)
    count_changed = pyqtSignal(str, int)
    delete_occurred = pyqtSignal(object)

    def __init__(self, db, kind: str, data_dir: Path, parent=None):
        super().__init__(parent)
        self.db = db
        self.kind = kind
        self.data_dir = Path(data_dir)
        self.model = EntryListModel(db, kind, self)
        self._build()
        self.model.reload()
        self._sync_empty()
        self.model.modelReset.connect(self._sync_empty)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 16)
        root.setSpacing(12)

        head = QHBoxLayout()
        titles = {"airdrop": ("Airdrop", "Danh sách kèo đang theo dõi"),
                  "tool": ("Tool AI", "AI hỗ trợ công việc")}
        t, s = titles[self.kind]
        col = QVBoxLayout()
        title = QLabel(t)
        title.setObjectName("PageTitle")
        sub = QLabel(s)
        sub.setObjectName("PageSubtitle")
        col.addWidget(title)
        col.addWidget(sub)
        head.addLayout(col)
        head.addStretch(1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm nhanh… (Ctrl+F)")
        self.search.setFixedWidth(220)
        self.search.setClearButtonEnabled(True)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(200)
        self._debounce.timeout.connect(
            lambda: self.model.set_filters(search=self.search.text().strip(),
                                           status=self._status_filter))
        self.search.textChanged.connect(self._debounce.start)
        head.addWidget(self.search)

        btn_import = QPushButton("Nhập")
        btn_import.setProperty("role", "ghost")
        btn_import.clicked.connect(lambda: self.import_requested.emit(self.kind))
        btn_export = QPushButton("Xuất")
        btn_export.setProperty("role", "ghost")
        btn_export.clicked.connect(lambda: self.export_requested.emit(self.kind))
        add_label = "Thêm kèo" if self.kind == "airdrop" else "Thêm AI"
        btn_add = QPushButton(f"+ {add_label}")
        btn_add.setProperty("role", "primary")
        btn_add.clicked.connect(self.add_new)
        head.addWidget(btn_import)
        head.addWidget(btn_export)
        head.addWidget(btn_add)
        root.addLayout(head)

        self._status_filter = ""
        if self.kind == "airdrop":
            chips = QHBoxLayout()
            chips.setSpacing(8)
            self._chip_buttons = []
            labels = ["Tất cả"] + AIRDROP_STATUSES
            for i, label in enumerate(labels):
                chip = QPushButton(label)
                chip.setProperty("role", "chip")
                chip.setCheckable(True)
                chip.setChecked(i == 0)
                chip.clicked.connect(lambda _=False, lb=label, b=chip: self._pick_chip(lb, b))
                chips.addWidget(chip)
                self._chip_buttons.append(chip)
            chips.addStretch(1)
            root.addLayout(chips)

        self.list = QListView()
        self.list.setModel(self.model)
        delegate = CardDelegate(self.data_dir, self.kind, self.list)
        self.list.setItemDelegate(delegate)
        self.list.setViewMode(QListView.ViewMode.IconMode)
        self.list.setResizeMode(QListView.ResizeMode.Adjust)
        self.list.setMovement(QListView.Movement.Static)
        self.list.setWrapping(True)
        self.list.setUniformItemSizes(True)
        self.list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.list.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self.list.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.list.doubleClicked.connect(self._on_double)
        delegate.edit_clicked.connect(self.edit_by_id)
        delegate.delete_clicked.connect(self.confirm_delete_id)
        delegate.link_clicked.connect(self._open_link_id)
        delegate.status_clicked.connect(self._cycle_status)
        root.addWidget(self.list, 1)

        self.empty = EmptyGuide("Chưa có mục nào trong danh sách.\n"
                                "Bấm nút bên trên để thêm mục đầu tiên.",
                                self.add_new, self)
        root.addWidget(self.empty, 1)
        self.empty.setVisible(False)

    def _pick_chip(self, label: str, btn: QPushButton) -> None:
        for b in self._chip_buttons:
            b.setChecked(b is btn)
        self._status_filter = "" if label == "Tất cả" else label
        self.model.set_filters(search=self.search.text().strip(),
                               status=self._status_filter)

    def _sync_empty(self) -> None:
        empty = self.model.rowCount() == 0 and self.model._total == 0
        self.list.setVisible(not empty)
        self.empty.setVisible(empty)
        self.count_changed.emit(self.kind, self.db.count_entries(self.kind))

    def refresh(self) -> None:
        self.model.reload()
        self._sync_empty()

    def add_new(self) -> None:
        dlg = EntryDialog(self.kind, self.data_dir, None, self.window())
        if dlg.exec() and dlg.result_entry:
            self._persist_logo(dlg.logo, dlg.result_entry)
            self.model.add(dlg.result_entry)
            self.count_changed.emit(self.kind, self.db.count_entries(self.kind))

    def edit_by_id(self, entry_id: int) -> None:
        data = self.db.get_entry(entry_id)
        if not data:
            return
        dlg = EntryDialog(self.kind, self.data_dir, Entry.from_dict(data), self.window())
        if dlg.exec():
            if dlg.delete_requested:
                self.confirm_delete_id(entry_id)
                return
            if dlg.result_entry:
                dlg.result_entry.id = entry_id
                self._persist_logo(dlg.logo, dlg.result_entry)
                self.model.update(dlg.result_entry)

    def _cycle_status(self, entry_id: int) -> None:
        data = self.db.get_entry(entry_id)
        if not data:
            return
        e = Entry.from_dict(data)
        try:
            idx = AIRDROP_STATUSES.index(e.status)
        except ValueError:
            idx = -1
        e.status = AIRDROP_STATUSES[(idx + 1) % len(AIRDROP_STATUSES)]
        self.model.update(e)

    def confirm_delete_id(self, entry_id: int) -> None:
        data = self.db.get_entry(entry_id)
        if not data:
            return
        dlg = ConfirmDialog("Xoá mục",
                            f"Bạn chắc chắn muốn xoá “{data['name']}”?\n"
                            "Bạn có thể Hoàn tác ngay sau khi xoá.",
                            confirm_text="Xoá", danger=True, parent=self.window())
        if dlg.exec():
            removed = self.model.remove(entry_id)
            if removed is not None:
                self.delete_occurred.emit(removed)
            self.count_changed.emit(self.kind, self.db.count_entries(self.kind))

    def undo_delete(self, entry: Entry) -> None:
        self.model.restore(entry)
        self.count_changed.emit(self.kind, self.db.count_entries(self.kind))

    def _open_link_id(self, entry_id: int) -> None:
        data = self.db.get_entry(entry_id)
        if data:
            open_link(data.get("link"))

    def _on_double(self, index: QModelIndex) -> None:
        entry = index.data(EntryListModel.REVERSE["entry"])
        if entry:
            self.edit_by_id(entry.id)

    @staticmethod
    def _persist_logo(logo_picker, entry: Entry) -> None:
        name, src = logo_picker.take_pending_file()
        if not name or src is None or not src.is_file():
            return
        dest = paths.logos_dir(Path(logo_picker.data_dir))
        dest.mkdir(parents=True, exist_ok=True)
        try:
            import shutil
            shutil.copyfile(src, dest / Path(name).name)
            logo_picker._source_path = None
        except OSError:
            pass
