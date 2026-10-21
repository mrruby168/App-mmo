"""Tab MMO / AI kiếm tiền: QListView + delegate-drawn rows (UI_SPEC EntryRow).

One widget for the whole list — rows are painted, never instantiated — plus
search (debounce 200 ms), status filter chips and inline actions.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import (QAbstractItemModel, QModelIndex, QRect, QRectF, QSize,
                          Qt, QTimer, pyqtSignal)
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QLabel,
                             QLineEdit, QListView, QPushButton, QSizePolicy,
                             QVBoxLayout, QWidget, QStyledItemDelegate, QStyle)

from app import paths

from app.models import Entry, EntryListModel
from app.ui import theme
from app.ui.dialogs import AIRDROP_STATUSES, EntryDialog
from app.ui.imaging import logo_pixmap
from app.ui.widgets import EmptyGuide, is_safe_link, open_link

ROW_H = 84
PAD = 12
LOGO_PX = 48
ACTION_W = 112


class EntryRowDelegate(QStyledItemDelegate):
    """Paints: logo | name+link | how_to | progress | tools | note | actions."""

    link_clicked = pyqtSignal(int)          # entry id
    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, data_dir: Path, model: EntryListModel, parent=None):
        super().__init__(parent)
        self.data_dir = Path(data_dir)
        self.model_ref = model
        self._action_rects: dict[int, dict[str, QRect]] = {}
        self._link_rects: dict[int, QRect] = {}

    # ------------------------------------------------------------ geometry
    def sizeHint(self, option, index):  # noqa: N802
        return QSize(option.rect.width(), ROW_H)

    def _columns(self, rect: QRect) -> dict[str, QRect]:
        w = rect.width() - PAD * 2
        x = rect.left() + PAD
        y = rect.top() + PAD // 2
        h = ROW_H - PAD
        cols: dict[str, QRect] = {}
        cols["proj"] = QRect(x, y, int(w * 0.30), h)
        cols["how"] = QRect(cols["proj"].right() + 12, y, int(w * 0.20), h)
        cols["prog"] = QRect(cols["how"].right() + 12, y, 116, h)
        cols["tools"] = QRect(cols["prog"].right() + 12, y, int(w * 0.14), h)
        cols["note"] = QRect(cols["tools"].right() + 12, y, max(90, w - (cols["tools"].right() + 12 - x) - ACTION_W), h)
        cols["act"] = QRect(rect.right() - PAD - ACTION_W, y, ACTION_W, h)
        return cols

    # -------------------------------------------------------------- paint
    def paint(self, painter: QPainter, option, index):  # noqa: N802
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        c = theme.colors(getattr(app, "resolved_mode", "light"))
        entry: Entry | None = index.data(EntryListModel.REVERSE["entry"])
        if entry is None:
            return
        rect = option.rect
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        card = QRectF(rect.adjusted(2, 2, -2, -6))
        selected = option.state & QStyle.StateFlag.State_Selected
        hover = option.state & QStyle.StateFlag.State_MouseOver
        bg = QColor(c["surface"])
        border = QColor(c["border"])
        if selected:
            border = QColor(c["primary"])
        elif hover:
            border = QColor(c["primary"]).lighter(120)
        painter.setPen(QPen(border, 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(card, 12, 12)

        cols = self._columns(rect)
        self._action_rects[index.row()] = {
            "edit": QRect(cols["act"].left(), cols["act"].top() + 6, 50, 32),
            "del": QRect(cols["act"].left() + 58, cols["act"].top() + 6, 50, 32),
        }

        from app.ui.widgets import paint_logo
        pm = logo_pixmap(self.data_dir, entry.logo, LOGO_PX)
        proj = cols["proj"]
        logo_rect = QRectF(proj.left(), proj.top() + (proj.height() - LOGO_PX) / 2,
                           LOGO_PX, LOGO_PX)
        paint_logo(painter, logo_rect, entry.name, pm)

        text_x = proj.left() + LOGO_PX + 12
        f_name = QFont(painter.font())
        f_name.setPixelSize(15)
        f_name.setWeight(QFont.Weight.DemiBold)
        painter.setFont(f_name)
        painter.setPen(QColor(c["text"]))
        fm = QFontMetrics(f_name)
        name_rect = QRect(text_x, proj.top() + 8, proj.right() - text_x, 22)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         fm.elidedText(entry.name, Qt.TextElideMode.ElideRight, name_rect.width()))

        f_link = QFont(painter.font())
        f_link.setPixelSize(12)
        painter.setFont(f_link)
        painter.setPen(QColor(c["info"]))
        link_rect = QRect(text_x, proj.top() + 34, proj.right() - text_x, 18)
        display_link = entry.link or ""
        fml = QFontMetrics(f_link)
        painter.drawText(link_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         fml.elidedText(display_link, Qt.TextElideMode.ElideRight, link_rect.width()))
        self._link_rects[index.row()] = link_rect if display_link else QRect()

        # how_to (2 lines clamped)
        self._draw_wrapped(painter, cols["how"], entry.how_to, c["text"], 13, 2, c)

        # progress bar + label ("Đang làm"/"Hoàn tất" + %)
        pr = cols["prog"]
        bar_y = pr.top() + pr.height() / 2 - 10
        track = QRectF(pr.left(), bar_y, pr.width(), 8)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(c["surface_alt"]))
        painter.drawRoundedRect(track, 4, 4)
        pct = max(0, min(100, int(entry.progress or 0)))
        if pct > 0:
            fill = QRectF(pr.left(), bar_y, pr.width() * pct / 100.0, 8)
            painter.setBrush(QColor(c["primary"] if pct < 100 else c["success"]))
            painter.drawRoundedRect(fill, 4, 4)
        f_small = QFont(painter.font())
        f_small.setPixelSize(12)
        painter.setFont(f_small)
        painter.setPen(QColor(c["muted_text"]))
        state = "Hoàn tất" if pct >= 100 else "Đang làm"
        painter.drawText(QRect(pr.left(), int(bar_y) + 12, pr.width(), 16),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, state)
        painter.drawText(QRect(pr.left(), int(bar_y) + 12, pr.width(), 16),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{pct}%")

        # tool tags
        self._draw_tags(painter, cols["tools"], entry.tools or [], c)

        # note block with gold left border
        note = cols["note"]
        if entry.note:
            box = QRect(note.left(), note.top() + 8, note.width(), note.height() - 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(c["surface_alt"]))
            painter.drawRoundedRect(QRectF(box), 8, 8)
            painter.setBrush(QColor(c["secondary"]))
            painter.drawRect(box.left(), box.top(), 3, box.height())
            self._draw_wrapped(painter, box.adjusted(10, 4, -6, -4), entry.note,
                               c["muted_text"], 13, 3, c)

        # action buttons
        rects = self._action_rects[index.row()]
        self._paint_mini_btn(painter, rects["edit"], "Sửa", c, hover_border=c["primary"])
        self._paint_mini_btn(painter, rects["del"], "Xoá", c, danger=True)
        painter.restore()

    def _paint_mini_btn(self, painter: QPainter, r: QRect, text: str, c: dict,
                        danger: bool = False, hover_border: str | None = None):
        painter.setPen(QPen(QColor(c["error"] if danger else (hover_border or c["border"])), 1))
        painter.setBrush(QColor(c["surface"]))
        painter.drawRoundedRect(QRectF(r), 8, 8)
        f = QFont(painter.font())
        f.setPixelSize(13)
        painter.setFont(f)
        painter.setPen(QColor(c["error"] if danger else c["text"]))
        painter.drawText(r, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_wrapped(self, painter: QPainter, rect: QRect, text: str, color: str,
                      px: int, max_lines: int, c: dict) -> None:
        if not text:
            return
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
        lines = lines[:max_lines]
        if len(text.split()) and len(lines) == max_lines:
            last = lines[-1]
            while lines and fm.horizontalAdvance(last + "…") > rect.width():
                last = last[:-1]
            remaining_words = len(text.split()) - sum(len(x.split()) for x in lines)
            lines[-1] = last + ("…" if remaining_words > 0 or last != text[len(''.join(lines[:-1])):] else "")
        y = rect.top() + (rect.height() - line_h * len(lines)) // 2
        for ln in lines:
            painter.drawText(QRect(rect.left(), y, rect.width(), line_h),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, ln)
            y += line_h

    def _draw_tags(self, painter: QPainter, rect: QRect, tags: list[str], c: dict) -> None:
        f = QFont(painter.font())
        f.setPixelSize(12)
        painter.setFont(f)
        fm = QFontMetrics(f)
        x = rect.left()
        y = rect.top() + rect.height() // 2 - 12
        shown = 0
        for t in tags:
            chip_w = fm.horizontalAdvance(t) + 16
            if x + chip_w > rect.right():
                more = [tt for tt in tags[shown:]]
                if more:
                    label = f"+{len(more)}"
                    painter.setPen(QColor(c["muted_text"]))
                    painter.drawText(QRect(x, y + 2, 40, 20), Qt.AlignmentFlag.AlignLeft, label)
                break
            box = QRect(x, y, chip_w, 24)
            painter.setPen(QPen(QColor(c["border"]), 1))
            painter.setBrush(QColor(c["surface_alt"]))
            painter.drawRoundedRect(QRectF(box), 6, 6)
            painter.setPen(QColor(c["text"]))
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, t)
            x += chip_w + 6
            shown += 1

    # ------------------------------------------------------------ hit-test
    def editorEvent(self, event, model, option, index):  # noqa: N802
        from PyQt6.QtCore import QEvent, QPoint

        etype = event.type()
        entry = index.data(EntryListModel.REVERSE["entry"])
        if entry is None:
            return False
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        rects = self._action_rects.get(index.row(), {})
        if etype == QEvent.Type.MouseButtonRelease:
            if "edit" in rects and rects["edit"].contains(pos):
                self.edit_clicked.emit(entry.id)
                return True
            if "del" in rects and rects["del"].contains(pos):
                self.delete_clicked.emit(entry.id)
                return True
            link_rect = self._link_rects.get(index.row())
            if link_rect and link_rect.contains(pos):
                if is_safe_link(entry.link):
                    self.link_clicked.emit(entry.id)
                return True
        return False


class EntryView(QWidget):
    """Header (title/search/Import/Export/Add) + chips + list (S-01/S-02)."""

    export_requested = pyqtSignal(str)   # kind
    import_requested = pyqtSignal(str)
    count_changed = pyqtSignal(str, int)
    delete_occurred = pyqtSignal(object)  # Entry removed (for undo toast)

    STATUS_CHIPS = {
        "mmo": ["Tất cả", "Đang làm", "Hoàn tất"],
        "ai": ["Tất cả", "Đang làm", "Ý tưởng", "Hoàn tất"],
    }

    def __init__(self, db, kind: str, data_dir: Path, parent=None):
        super().__init__(parent)
        self.db = db
        self.kind = kind
        self.data_dir = Path(data_dir)
        self.model = EntryListModel(db, kind, self)
        self._status_filter = ""
        self._build()
        self.model.reload()
        self._sync_empty()
        self.model.modelReset.connect(self._sync_empty)
        self.model.rowsRemoved.connect(lambda *_: self._sync_empty())
        self.model.rowsInserted.connect(lambda *_: self._sync_empty())

    # ------------------------------------------------------------- widgets
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 16)
        root.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(8)
        titles = {"mmo": ("MMO", "Theo dõi các web kiếm tiền"),
                  "ai": ("AI kiếm tiền", "Web kiếm tiền cùng AI")}
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
        self.search.setPlaceholderText("Tìm theo tên, link, ghi chú (Ctrl+F)")
        self.search.setFixedWidth(220)
        self.search.setClearButtonEnabled(True)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(200)
        self._debounce.timeout.connect(self._apply_search)
        self.search.textChanged.connect(self._debounce.start)
        self.search.installEventFilter(self)
        head.addWidget(self.search)

        btn_import = QPushButton("Nhập")
        btn_import.setProperty("role", "ghost")
        btn_import.clicked.connect(lambda: self.import_requested.emit(self.kind))
        btn_export = QPushButton("Xuất")
        btn_export.setProperty("role", "ghost")
        btn_export.clicked.connect(lambda: self.export_requested.emit(self.kind))
        btn_add = QPushButton(f"+ {'Thêm dự án'}")
        btn_add.setProperty("role", "primary")
        btn_add.clicked.connect(self.add_new)
        head.addWidget(btn_import)
        head.addWidget(btn_export)
        head.addWidget(btn_add)
        root.addLayout(head)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        self._chip_buttons: list[QPushButton] = []
        group_labels = self.STATUS_CHIPS.get(self.kind, ["Tất cả"])
        for i, label in enumerate(group_labels):
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
        self.list.setItemDelegate(EntryRowDelegate(self.data_dir, self.model, self.list))
        self.list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.list.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setUniformItemSizes(True)
        self.list.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self.list.doubleClicked.connect(self._on_double)
        delegate = self.list.itemDelegate()
        delegate.edit_clicked.connect(self.edit_by_id)
        delegate.delete_clicked.connect(self.confirm_delete_id)
        delegate.link_clicked.connect(self._open_link_id)
        root.addWidget(self.list, 1)

        self.empty = EmptyGuide(f"Chưa có mục nào ở tab {self.kind.upper()}.\n"
                                "Bấm nút bên trên để thêm dự án đầu tiên.",
                                self.add_new, self)
        root.addWidget(self.empty, 1)
        self.empty.setVisible(False)

    # --------------------------------------------------------------- logic
    def _pick_chip(self, label: str, btn: QPushButton) -> None:
        for b in self._chip_buttons:
            b.setChecked(b is btn)
        if label == "Tất cả":
            self._status_filter = ""
        elif label in ("Đang làm",):
            self._status_filter = "__in_progress"
        elif label == "Hoàn tất":
            self._status_filter = "__complete"
        else:
            self._status_filter = label
        self._apply_filters_now()

    def _apply_search(self) -> None:
        self._apply_filters_now()

    def _apply_filters_now(self) -> None:
        search = self.search.text().strip()
        # progress pseudo-status handled via post-filter on model query
        status_sql = ""
        if self._status_filter in ("__in_progress", "__complete", "Ý tưởng"):
            status_sql = ""
            self.model.status_filter = ""
            self.model.search = search
            self.model.refresh_filtered()
            # apply pseudo filter by hiding rows through a proxy-free reload
            self._pseudo_filter(search)
            return
        self.model.set_filters(search=search, status=self._status_filter)
        self._sync_empty()

    def _pseudo_filter(self, search: str) -> None:
        wanted = self._status_filter
        keep_all = self.model._items
        filtered = []
        total = 0
        for e in keep_all:
            ok = True
            if wanted == "__in_progress":
                ok = e.progress < 100
            elif wanted == "__complete":
                ok = e.progress >= 100
            elif wanted == "Ý tưởng":
                ok = e.status == "Ý tưởng"
            if ok:
                filtered.append(e)
        self.model.beginResetModel()
        self.model._total = len(filtered)
        self.model._items = filtered
        self.model.endResetModel()
        self._sync_empty()

    def _sync_empty(self) -> None:
        empty = self.model.rowCount() == 0 and self.model._total == 0
        self.list.setVisible(not empty)
        self.empty.setVisible(empty)
        self.count_changed.emit(self.kind, self.db.count_entries(self.kind))

    def refresh(self) -> None:
        self.model.reload()
        self._sync_empty()

    # ------------------------------------------------------------ CRUD UI
    def add_new(self) -> None:
        dlg = EntryDialog(self.kind, self.data_dir, None, self.window())
        if dlg.exec():
            if dlg.result_entry:
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
                self.count_changed.emit(self.kind, self.db.count_entries(self.kind))

    def confirm_delete_id(self, entry_id: int) -> None:
        data = self.db.get_entry(entry_id)
        if not data:
            return
        from app.ui.dialogs import ConfirmDialog
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

    def keyPressEvent(self, event):  # noqa: N802
        from PyQt6.QtGui import QKeySequence, QKeyEvent
        if event.matches(QKeySequence.StandardKey.Find):
            self.search.setFocus()
            self.search.selectAll()
            return
        if event.key() == Qt.Key.Key_Escape and self.search.hasFocus():
            self.search.clear()
            self.list.setFocus()
            return
        super().keyPressEvent(event)

    @staticmethod
    def _persist_logo(logo_picker, entry: Entry) -> None:
        """Copy freshly-picked image into data_dir/logos under its new name."""
        name, src = logo_picker.take_pending_file()
        if not name or src is None or not src.is_file():
            return
        dest = paths.logos_dir(Path(logo_picker.data_dir))
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / Path(name).name
        try:
            import shutil
            shutil.copyfile(src, target)
            logo_picker._source_path = None
        except OSError:
            pass


