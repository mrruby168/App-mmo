"""Link Vault — application entry point (the ONLY file with the Qt guard).

Run:  python main.py [--portable]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Rule R-01: QApplication must be created AFTER argparse, inside main().
# No Qt widget module may be imported before this point at runtime.
# ---------------------------------------------------------------------------


def _bootstrap_logging() -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        log_file = Path(__file__).resolve().parent / "app.log"
        handlers.insert(0, logging.FileHandler(log_file, encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=handlers,
    )


def _parse_args(argv: list[str]):
    import argparse

    parser = argparse.ArgumentParser(
        prog="LinkVault",
        description="Link Vault — quản lý link MMO / AI / Airdrop / Tool.",
    )
    parser.add_argument("--portable", action="store_true",
                        help="Lưu config + dữ liệu ngay cạnh file thực thi.")
    parser.add_argument("--data-dir", default=None,
                        help="Thư mục dữ liệu tùy chọn (override config).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _bootstrap_logging()
    log = logging.getLogger("main")
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    from app import config, paths
    from app.db import Database
    from app.ui import theme as theme_mod

    cfg = config.load()
    if args.portable:
        cfg["portable"] = True
        cfg.setdefault("data_dir", "data")
    data_dir = (Path(args.data_dir).resolve() if args.data_dir
                else paths.resolve_data_dir(cfg.get("data_dir") or None))
    ok, err = paths.is_writable_dir(data_dir)
    if not ok:
        fallback = paths.default_data_dir()
        log.warning("Data dir %s không dùng được (%s) → chuyển sang %s",
                    data_dir, err, fallback)
        data_dir = fallback
        cfg["data_dir"] = paths.store_data_dir(fallback)
        config.save(cfg)

    # Qt imports happen only here, after argparse finished.
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv[:1])
    app.setApplicationName("LinkVault")
    resolved = theme_mod.apply_theme(app, cfg.get("theme", "system"))
    app.resolved_mode = resolved
    theme_mod.load_fonts(app)

    db = Database(data_dir)
    from app.ui.main_window import MainWindow

    win = MainWindow(db, cfg)
    icon_path = paths.resource_path("assets/icons/app_icon.png")
    if icon_path.is_file():
        from PyQt6.QtGui import QIcon
        win.setWindowIcon(QIcon(str(icon_path)))
    win.show()
    log.info("Link Vault started · data=%s theme=%s", data_dir, resolved)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
