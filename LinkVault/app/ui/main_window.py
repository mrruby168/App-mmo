"""MainWindow: sidebar nav + QStackedWidget pages + toast bar (UI_SPEC S-05)."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence, QPixmap
from PyQt6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
                             QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from app import config, paths
from app.db import Database
from app.io_data import IOTask, create_backup, export_csv, export_json, import_csv, import_json
from app.models import Entry, Note
from app.ui import theme
from app.ui.card_view import CardView
from app.ui.dialogs import ConfirmDialog
from app.ui.entry_view import EntryView
from app.ui.imaging import clear_cache
from app.ui.note_view import NoteView
from app.ui.settings_view import SettingsView
from app.ui.widgets import ToastBar

log = logging.getLogger(__name__)

TABS = [
    ("mmo", "MMO"),
    ("ai", "AI kiếm tiền"),
    ("airdrop", "Airdrop"),
    ("tool", "Tool AI"),
    ("note", "Note"),
    ("settings", "Cài đặt"),
]


class Sidebar(QWidget):
    def __init__(self, main, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(240)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 20, 16, 16)
        lay.setSpacing(8)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        logo = QLabel()
        pm = self._brand_pixmap()
        if pm:
            logo.setPixmap(pm)
        else:
            logo.setText("🔐")
            logo.setStyleSheet("font-size: 22px; background: transparent; border: none;")
        name = QLabel("Link Vault")
        name.setObjectName("Brand")
        brand_row.addWidget(logo)
        brand_row.addWidget(name)
        brand_row.addStretch(1)
        lay.addLayout(brand_row)
        lay.addSpacing(16)

        self.nav_buttons: dict[str, QPushButton] = {}
        for key, label in TABS:
            btn = QPushButton(label)
            btn.setProperty("role", "nav")
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=key: main.switch_tab(k))
            lay.addWidget(btn)
            self.nav_buttons[key] = btn
        lay.addStretch(1)

    @staticmethod
    def _brand_pixmap() -> QPixmap | None:
        icon_path = paths.resource_path("assets/icons/app_icon.png")
        if icon_path.is_file():
            pm = QPixmap(str(icon_path))
            if not pm.isNull():
                return pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        return None

    def select(self, key: str) -> None:
        for k, b in self.nav_buttons.items():
            b.setChecked(k == key)


class MainWindow(QMainWindow):
    def __init__(self, db: Database, cfg: dict):
        super().__init__()
        self.setWindowTitle("Link Vault")
        self.resize(1200, 720)
        self.setMinimumSize(900, 600)
        self.db = db
        self.cfg = cfg
        self.pool = QThreadPool.globalInstance()

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.sidebar = Sidebar(self)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        self.stack = QStackedWidget()
        self.pages: dict[str, QWidget] = {}
        self.views: dict[str, object] = {}
        for key, _label in TABS:
            if key in ("mmo", "ai"):
                view = EntryView(db, key, db.data_dir)
            elif key in ("airdrop", "tool"):
                view = CardView(db, key, db.data_dir)
            elif key == "note":
                view = NoteView(db, db.data_dir)
            else:
                view = SettingsView(db, cfg)
            if hasattr(view, "count_changed"):
                view.count_changed.connect(self._on_count)
            if hasattr(view, "delete_occurred"):
                view.delete_occurred.connect(self._offer_undo)
            if hasattr(view, "export_requested"):
                view.export_requested.connect(self._export_for_kind)
                view.import_requested.connect(self._import_for_kind)
            if key == "settings":
                view.theme_changed.connect(self._apply_theme_choice)
                view.data_dir_migrated.connect(self._after_migration)
            self.pages[key] = view
            self.views[key] = view
            self.stack.addWidget(view)
        right.addWidget(self.stack, 1)

        self.toast = ToastBar()
        right.addWidget(self.toast)
        root.addLayout(right, 1)
        self.setCentralWidget(central)

        # counts badges
        self._counts: dict[str, int] = {}
        for key in ("mmo", "ai", "airdrop", "tool"):
            self._counts[key] = db.count_entries(key)
        self._counts["note"] = db.conn.execute("SELECT COUNT(*) c FROM notes").fetchone()["c"]
        self._refresh_nav_labels()

        # shortcuts
        act_new = QAction("Thêm mục mới", self)
        act_new.setShortcut(QKeySequence("Ctrl+N"))
        act_new.triggered.connect(self._add_current)
        self.addAction(act_new)
        act_save = QAction("Lưu ngay", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._flush_note)
        self.addAction(act_save)
        act_export = QAction("Xuất dữ liệu", self)
        act_export.setShortcut(QKeySequence("Ctrl+E"))
        act_export.triggered.connect(self._export_all)
        self.addAction(act_export)
        act_quit = QAction("Thoát", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        self.addAction(act_quit)

        start = cfg.get("last_tab", "mmo")
        if start not in self.pages:
            start = "mmo"
        self.switch_tab(start)

    # ------------------------------------------------------------- switching
    def switch_tab(self, key: str) -> None:
        self.current_key = key
        self.stack.setCurrentWidget(self.pages[key])
        self.sidebar.select(key)
        self.cfg["last_tab"] = key
        config.save(self.cfg)
        if key == "settings":
            self.pages[key].db = self.db
            self.pages[key].cfg = self.cfg
            self.pages[key].refresh_stats()

    def _on_count(self, kind: str, n: int) -> None:
        self._counts[kind] = n
        self._refresh_nav_labels()

    def _refresh_nav_labels(self) -> None:
        for key, label in TABS:
            if key in self._counts and key != "settings":
                btn = self.sidebar.nav_buttons[key]
                if key in ("mmo", "ai", "airdrop", "tool", "note"):
                    btn.setText(f"{label}   {self._counts[key]}")

    def _add_current(self) -> None:
        view = self.pages.get(getattr(self, "current_key", ""))
        if hasattr(view, "add_new"):
            view.add_new()

    def _flush_note(self) -> None:
        view = self.pages.get(getattr(self, "current_key", ""))
        if isinstance(view, NoteView):
            view._save_now()

    # ------------------------------------------------------------------ undo
    def _offer_undo(self, removed) -> None:
        view = self.pages[removed.kind if hasattr(removed, "kind") else "note"]
        undo_cb = lambda: view.undo_delete(removed)
        if isinstance(removed, Note):
            self.toast.show_message("Đã xoá ghi chú.", "info", ms=6000,
                                    action_text="Hoàn tác", action_cb=undo_cb)
        else:
            self.toast.show_message(f"Đã xoá “{removed.name}”.", "info", ms=6000,
                                    action_text="Hoàn tác", action_cb=undo_cb)

    # ---------------------------------------------------------------- toasts
    def show_toast(self, text: str, kind: str = "info") -> None:
        self.toast.show_message(text, kind)

    # ---------------------------------------------------------- export/import
    def _export_for_kind(self, kind: str) -> None:
        base = str(Path.home() / f"linkvault_{kind}.csv")
        fname, _ = QFileDialog.getSaveFileName(self, f"Xuất tab {kind.upper()}",
                                               base, "CSV (*.csv)")
        if not fname:
            return
        task = IOTask(export_csv, self.db, kind, Path(fname))
        task.signals.finished.connect(
            lambda n: self.toast.show_message(f"Đã xuất {n} dòng vào {Path(fname).name}",
                                              "success"))
        task.signals.error.connect(lambda msg: self.show_toast(f"Lỗi xuất: {msg}", "error"))
        self.pool.start(task)

    def _import_for_kind(self, kind: str) -> None:
        fname, _ = QFileDialog.getOpenFileName(self, f"Nhập cho tab {kind.upper()}",
                                               str(Path.home()),
                                               "Dữ liệu (*.json *.csv);;"
                                               "JSON (*.json);;CSV (*.csv)")
        if not fname:
            return
        src = Path(fname)
        if src.suffix.lower() == ".json":
            dlg = ImportChoiceDialog(self)
            if not dlg.exec():
                return
            mode = dlg.mode
            task = IOTask(import_json, self.db, src, mode)
            task.signals.finished.connect(self._import_done)
        else:
            task = IOTask(import_csv, self.db, src, kind, "merge")
            task.signals.finished.connect(self._import_done)
        task.signals.error.connect(lambda msg: self.show_toast(f"Lỗi nhập: {msg}", "error"))
        self.pool.start(task)

    def _import_done(self, result) -> None:
        for view in self.pages.values():
            if hasattr(view, "refresh"):
                view.refresh()
        self._reload_counts()
        if isinstance(result, dict):
            errs = result.get("errors") or []
            summary = (f"Hoàn tất: thêm {result.get('added', 0)}, cập nhật "
                       f"{result.get('updated', 0)}")
            if result.get("notes"):
                summary += f", ghi chú {result['notes']}"
            if errs:
                detail = "\n".join(errs[:20])
                self.toast.show_message(f"{summary} · {len(errs)} lỗi:", "error",
                                        action_text="Xem lỗi",
                                        action_cb=lambda: ErrorListDialog(detail, self).exec())
            else:
                self.toast.show_message(summary, "success")

    def _export_all(self) -> None:
        base = str(Path.home() / "linkvault_backup.json")
        fname, _ = QFileDialog.getSaveFileName(self, "Xuất toàn bộ dữ liệu",
                                               base, "JSON (*.json)")
        if not fname:
            return
        task = IOTask(export_json, self.db, Path(fname))
        task.signals.finished.connect(
            lambda n: self.toast.show_message(f"Đã xuất {n} mục vào {Path(fname).name}",
                                              "success"))
        task.signals.error.connect(lambda msg: self.show_toast(f"Lỗi xuất: {msg}", "error"))
        self.pool.start(task)

    def _reload_counts(self) -> None:
        for key in ("mmo", "ai", "airdrop", "tool"):
            self._counts[key] = self.db.count_entries(key)
        self._counts["note"] = self.db.conn.execute(
            "SELECT COUNT(*) c FROM notes").fetchone()["c"]
        self._refresh_nav_labels()

    # ----------------------------------------------------------------- theme
    def _apply_theme_choice(self, mode: str) -> None:
        resolved = theme.apply_theme(self.applicationInstance(), mode)
        self.applicationInstance().resolved_mode = resolved
        clear_cache()

    # -------------------------------------------------------------- migration
    def _after_migration(self, new_dir: Path) -> None:
        try:
            self.db.close()
        except Exception:  # noqa: BLE001
            pass
        self.db = Database(new_dir)
        clear_cache()
        self._rebuild_pages()

    def reopen_database(self) -> None:
        try:
            self.db.close()
        except Exception:  # noqa: BLE001
            pass
        self.db = Database(paths.resolve_data_dir(self.cfg.get("data_dir") or None))
        clear_cache()
        self._rebuild_pages()

    def _rebuild_pages(self) -> None:
        old_key = getattr(self, "current_key", "mmo")
        for widget in list(self.pages.values()):
            self.stack.removeWidget(widget)
            widget.deleteLater()
        self.pages = {}
        for key, _label in TABS:
            if key in ("mmo", "ai"):
                view = EntryView(self.db, key, self.db.data_dir)
            elif key in ("airdrop", "tool"):
                view = CardView(self.db, key, self.db.data_dir)
            elif key == "note":
                view = NoteView(self.db, self.db.data_dir)
            else:
                view = SettingsView(self.db, self.cfg)
            if hasattr(view, "count_changed"):
                view.count_changed.connect(self._on_count)
            if hasattr(view, "delete_occurred"):
                view.delete_occurred.connect(self._offer_undo)
            if hasattr(view, "export_requested"):
                view.export_requested.connect(self._export_for_kind)
                view.import_requested.connect(self._import_for_kind)
            if key == "settings":
                view.theme_changed.connect(self._apply_theme_choice)
                view.data_dir_migrated.connect(self._after_migration)
            self.pages[key] = view
            self.views[key] = view
            self.stack.addWidget(view)
        self._reload_counts()
        self.switch_tab(old_key)

    # ---------------------------------------------------------------- close
    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        view = self.pages.get(getattr(self, "current_key", ""))
        if isinstance(view, NoteView):
            view._save_now()
        if self.cfg.get("auto_backup", True):
            try:
                create_backup(self.db.data_dir, int(self.cfg.get("backup_keep", 5)))
            except Exception as exc:  # noqa: BLE001
                log.warning("Auto backup failed: %s", exc)
        try:
            self.db.close()
        except Exception:  # noqa: BLE001
            pass
        event.accept()


class ImportChoiceDialog(QDialog):
    """Merge vs Overwrite choice before importing a JSON backup."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cách nhập dữ liệu")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.mode = "merge"
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 16)
        lay.setSpacing(12)
        t = QLabel("Nhập từ bản sao lưu JSON")
        t.setStyleSheet("font-size: 18px; font-weight: 700;")
        m = QLabel("Chọn cách xử lý khi trùng dữ liệu (cùng tên + link):")
        m.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(m)
        merge = QPushButton("Hợp nhất — cập nhật mục trùng, thêm mục mới")
        merge.setProperty("role", "primary")
        overwrite = QPushButton("Ghi đè — xoá hết hiện tại rồi nhập")
        overwrite.setProperty("role", "ghost")
        overwrite.setStyleSheet(overwrite.styleSheet())
        cancel = QPushButton("Huỷ")
        cancel.setProperty("role", "ghost")
        merge.clicked.connect(lambda: self._pick("merge"))
        overwrite.clicked.connect(lambda: self._pick("overwrite"))
        cancel.clicked.connect(self.reject)
        lay.addWidget(merge)
        lay.addWidget(overwrite)
        lay.addWidget(cancel)

    def _pick(self, mode: str) -> None:
        self.mode = mode
        self.accept()


class ErrorListDialog(QDialog):
    def __init__(self, detail: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chi tiết lỗi nhập")
        self.setMinimumSize(480, 320)
        lay = QVBoxLayout(self)
        lbl = QLabel(detail)
        lbl.setWordWrap(True)
        from PyQt6.QtWidgets import QScrollArea, QWidget as WW
        area = QScrollArea()
        area.setWidgetResizable(True)
        holder = WW()
        hl = QVBoxLayout(holder)
        hl.addWidget(lbl)
        hl.addStretch(1)
        area.setWidget(holder)
        lay.addWidget(area)
        btn = QPushButton("Đóng")
        btn.setProperty("role", "ghost")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
