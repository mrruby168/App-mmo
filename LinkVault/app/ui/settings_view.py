"""Tab Cài đặt: theme, data folder (migrate), portable mode, backup/restore."""

from __future__ import annotations

import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QThreadPool, pyqtSignal
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QFileDialog, QFrame,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QSpinBox, QVBoxLayout, QWidget)

from app import config, paths
from app.io_data import IOTask, create_backup, rotate_backups
from app.ui import theme
from app.ui.dialogs import ConfirmDialog

log = logging.getLogger(__name__)


def format_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"


class Section(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setProperty("role", "section")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(20, 16, 20, 16)
        self.lay.setSpacing(10)
        t = QLabel(title)
        t.setStyleSheet("font-size: 15px; font-weight: 700; background: transparent;")
        self.lay.addWidget(t)


class SettingsView(QWidget):
    theme_changed = pyqtSignal(str)
    data_dir_migrated = pyqtSignal(object)  # new Path

    def __init__(self, db, cfg: dict, parent=None):
        super().__init__(parent)
        self.db = db
        self.cfg = cfg
        self.pool = QThreadPool.globalInstance()
        self._build()
        self.refresh_stats()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 16)
        root.setSpacing(16)

        head = QVBoxLayout()
        title = QLabel("Cài đặt")
        title.setObjectName("PageTitle")
        sub = QLabel("Giao diện, dữ liệu và sao lưu")
        sub.setObjectName("PageSubtitle")
        head.addWidget(title)
        head.addWidget(sub)
        root.addLayout(head)

        # ---- Appearance
        s1 = Section("Giao diện")
        row = QHBoxLayout()
        self.theme_group = QButtonGroup(self)
        self._theme_buttons: dict[str, QPushButton] = {}
        current = self.cfg.get("theme", "system")
        for key, label in (("light", "Sáng"), ("dark", "Tối"), ("system", "Theo hệ thống")):
            btn = QPushButton(label)
            btn.setProperty("role", "chip")
            btn.setCheckable(True)
            btn.setChecked(key == current)
            self.theme_group.addButton(btn)
            self._theme_buttons[key] = btn
            btn.clicked.connect(lambda _=False, k=key: self._set_theme(k))
            row.addWidget(btn)
        row.addStretch(1)
        s1.lay.addLayout(row)
        root.addWidget(s1)

        # ---- Data location
        s2 = Section("Vị trí dữ liệu")
        row2 = QHBoxLayout()
        self.dir_edit = QLineEdit(str(self.db.data_dir))
        self.dir_edit.setReadOnly(True)
        browse = QPushButton("Chọn thư mục…")
        browse.setProperty("role", "ghost")
        browse.clicked.connect(self._browse_dir)
        move_btn = QPushButton("Di chuyển dữ liệu…")
        move_btn.setProperty("role", "ghost")
        move_btn.clicked.connect(self._migrate_dir)
        row2.addWidget(self.dir_edit, 1)
        row2.addWidget(browse)
        row2.addWidget(move_btn)
        s2.lay.addLayout(row2)

        row2b = QHBoxLayout()
        self.portable_cb = QCheckBox("Chế độ portable (lưu cấu hình + dữ liệu cạnh file .exe)")
        self.portable_cb.setChecked(bool(self.cfg.get("portable")))
        self.portable_cb.toggled.connect(self._toggle_portable)
        row2b.addWidget(self.portable_cb)
        row2b.addStretch(1)
        s2.lay.addLayout(row2b)

        stats_row = QHBoxLayout()
        self.stats_lbl = QLabel("")
        self.stats_lbl.setStyleSheet("background: transparent; color: palette(mid);")
        open_btn = QPushButton("Mở thư mục dữ liệu")
        open_btn.setProperty("role", "ghost")
        open_btn.clicked.connect(self._open_data_folder)
        stats_row.addWidget(self.stats_lbl, 1)
        stats_row.addWidget(open_btn)
        s2.lay.addLayout(stats_row)
        root.addWidget(s2)

        # ---- Backup & restore
        s3 = Section("Sao lưu & phục hồi")
        row3 = QHBoxLayout()
        self.auto_backup_cb = QCheckBox("Tự động sao lưu khi đóng ứng dụng")
        self.auto_backup_cb.setChecked(bool(self.cfg.get("auto_backup", True)))
        self.auto_backup_cb.toggled.connect(self._toggle_auto_backup)
        row3.addWidget(self.auto_backup_cb)
        row3.addSpacing(16)
        row3.addWidget(QLabel("Giữ bản:"))
        self.keep_spin = QSpinBox()
        self.keep_spin.setRange(1, 20)
        self.keep_spin.setValue(int(self.cfg.get("backup_keep", 5)))
        self.keep_spin.valueChanged.connect(self._set_keep)
        row3.addWidget(self.keep_spin)
        row3.addStretch(1)
        s3.lay.addLayout(row3)

        row4 = QHBoxLayout()
        bk = QPushButton("Sao lưu ngay")
        bk.setProperty("role", "primary")
        bk.setMinimumHeight(32)
        bk.clicked.connect(self._backup_now)
        rs = QPushButton("Phục hồi từ tệp…")
        rs.setProperty("role", "ghost")
        rs.setMinimumHeight(32)
        rs.clicked.connect(self._restore_file)
        op = QPushButton("Mở thư mục sao lưu")
        op.setProperty("role", "ghost")
        op.setMinimumHeight(32)
        op.clicked.connect(self._open_backup_folder)
        row4.addWidget(bk)
        row4.addWidget(rs)
        row4.addWidget(op)
        row4.addStretch(1)
        s3.lay.addLayout(row4)
        self.backup_info = QLabel("")
        self.backup_info.setStyleSheet("background: transparent; color: palette(mid); font-size: 12px;")
        s3.lay.addWidget(self.backup_info)
        root.addWidget(s3)

        # ---- About
        s4 = Section("Giới thiệu")
        from app import APP_VERSION
        about = QLabel(f"Link Vault v{APP_VERSION} — Quản lý link cá nhân cho MMO / AI / "
                       "Airdrop / Tool.\nDữ liệu nằm hoàn toàn trên máy bạn.")
        about.setStyleSheet("background: transparent;")
        s4.lay.addWidget(about)
        root.addWidget(s4)
        root.addStretch(1)
        self._refresh_backup_info()

    # ------------------------------------------------------------ handlers
    def _set_theme(self, key: str) -> None:
        self._theme_buttons[key].setChecked(True)
        self.cfg["theme"] = key
        config.save(self.cfg)
        self.theme_changed.emit(key)

    def _toggle_auto_backup(self, checked: bool) -> None:
        self.cfg["auto_backup"] = checked
        config.save(self.cfg)

    def _set_keep(self, value: int) -> None:
        self.cfg["backup_keep"] = value
        config.save(self.cfg)

    def _toggle_portable(self, checked: bool) -> None:
        self.cfg["portable"] = checked
        if checked:
            self.cfg["data_dir"] = "data"
            self.dir_edit.setText(str(paths.app_dir() / "data"))
        else:
            self.cfg["data_dir"] = ""
            self.dir_edit.setText(str(paths.default_data_dir()))
        try:
            config.save(self.cfg)
        except OSError as exc:
            self.window().show_toast(f"Không lưu được cấu hình: {exc}", "error")
        self._refresh_backup_info()

    def _browse_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Chọn thư mục dữ liệu",
                                                  str(Path.home()))
        if chosen:
            self.pending_dir = Path(chosen)
            self.dir_edit.setText(chosen)

    def _migrate_dir(self) -> None:
        target = getattr(self, "pending_dir", None)
        if not target:
            chosen = QFileDialog.getExistingDirectory(self, "Thư mục đích để chứa dữ liệu",
                                                      str(Path.home()))
            if not chosen:
                return
            target = Path(chosen)
        dlg = ConfirmDialog(
            "Di chuyển dữ liệu",
            f"Sao chép toàn bộ DB + logo sang:\n{target}\n\n"
            "Dữ liệu cũ vẫn giữ nguyên. Xác nhận để bắt đầu.",
            confirm_text="Di chuyển", parent=self.window())
        if not dlg.exec():
            return
        task = IOTask(_migrate_worker, self.db, target)
        task.signals.progress.connect(lambda cur, tot: None)
        task.signals.error.connect(lambda msg: self.window().show_toast(msg, "error"))
        task.signals.finished.connect(self._migration_done)
        self.pool.start(task)

    def _migration_done(self, report) -> None:
        new_dir, ok, err = report
        if not ok:
            self.window().show_toast(err, "error")
            return
        self.cfg["data_dir"] = paths.store_data_dir(new_dir)
        config.save(self.cfg)
        self.dir_edit.setText(str(new_dir))
        self.data_dir_migrated.emit(new_dir)
        self.window().show_toast(f"Đã di chuyển dữ liệu sang {new_dir}", "success")

    def _backup_now(self) -> None:
        dest = create_backup(self.db.data_dir, int(self.cfg.get("backup_keep", 5)))
        if dest:
            self.window().show_toast(f"Đã sao lưu: {dest.name}", "success")
        else:
            self.window().show_toast("Chưa có database để sao lưu.", "info")
        self._refresh_backup_info()

    def _restore_file(self) -> None:
        fname, _ = QFileDialog.getOpenFileName(
            self, "Chọn bản sao lưu (.db)", str(paths.backups_dir(self.db.data_dir)),
            "Database (*.db)")
        if not fname:
            return
        src = Path(fname)
        try:
            import sqlite3
            con = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
            rows = con.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' "
                "AND name IN ('entries','notes')").fetchone()[0]
            con.close()
        except Exception as exc:  # noqa: BLE001
            self.window().show_toast(f"Tệp không hợp lệ: {exc}", "error")
            return
        if rows < 2:
            self.window().show_toast("Tệp không phải database của Link Vault.", "error")
            return
        dlg = ConfirmDialog(
            "Phục hồi dữ liệu",
            "Toàn bộ dữ liệu hiện tại sẽ bị thay bằng nội dung tệp sao lưu.\n"
            "Nên bấm “Sao lưu ngay” trước nếu chưa an tâm. Tiếp tục?",
            confirm_text="Phục hồi", danger=True, parent=self.window())
        if not dlg.exec():
            return
        create_backup(self.db.data_dir, keep=int(self.cfg.get("backup_keep", 5)) + 1)
        import shutil
        import sqlite3
        try:
            self.db.conn.close()
        except Exception:  # noqa: BLE001
            pass
        target = paths.db_path(self.db.data_dir)
        shutil.copyfile(src, target)
        for suffix in ("-wal", "-shm"):
            stale = Path(str(target) + suffix)
            if stale.exists():
                stale.unlink()
        self.window().reopen_database()
        self.window().show_toast("Đã phục hồi dữ liệu.", "success")

    def _open_backup_folder(self) -> None:
        open_explorer(paths.backups_dir(self.db.data_dir))

    def _open_data_folder(self) -> None:
        open_explorer(self.db.data_dir)

    def _refresh_backup_info(self) -> None:
        backups = sorted(paths.backups_dir(self.db.data_dir).glob("linkvault-*.db"),
                         key=lambda p: p.name, reverse=True)
        if backups:
            newest = datetime.fromtimestamp(backups[0].stat().st_mtime)
            self.backup_info.setText(
                f"Có {len(backups)} bản sao lưu · Mới nhất: "
                f"{newest.strftime('%H:%M %d/%m/%Y')}")
        else:
            self.backup_info.setText("Chưa có bản sao lưu nào.")

    def refresh_stats(self) -> None:
        st = self.db.stats()
        logos = paths.logos_dir(self.db.data_dir)
        logo_count = len(list(logos.glob("*"))) if logos.is_dir() else 0
        self.stats_lbl.setText(
            f"{st['entries']} dòng liên kết · {st['notes']} ghi chú · "
            f"{logo_count} logo · DB {format_size(st['db_bytes'])}")


def _migrate_worker(db, new_dir: Path):
    """Runs in worker thread: fresh connection to source, copy everything."""
    from app.io_data import migrate_data_dir
    try:
        migrate_data_dir(db, new_dir)
        return new_dir, True, ""
    except Exception as exc:  # noqa: BLE001
        return new_dir, False, str(exc)


def open_explorer(path: Path) -> None:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError as exc:
        log.warning("open_explorer failed: %s", exc)
