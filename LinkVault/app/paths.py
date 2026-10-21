"""Single source of truth for every filesystem path (ARCHITECTURE.md section 4).

No other module may use ``__file__``, ``os.getcwd()`` or hand-written path
strings.  Works both from source and from a PyInstaller *onedir* bundle.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from app import CONFIG_FILENAME, DB_FILENAME


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> Path:
    """Directory of the executable (frozen) or the project root (source)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    # .../<root>/app/paths.py  ->  <root>
    return Path(__file__).resolve().parent.parent


def resource_path(relative: str = "") -> Path:
    """Read-only bundled resource (fonts, icons, qss, design files)."""
    if is_frozen():
        base = Path(getattr(sys, "_MEIPASS", app_dir() / "_internal"))
    else:
        base = app_dir()
    return base / relative if relative else base


def appdata_dir() -> Path:
    """%APPDATA%\\LinkVault on Windows, XDG config elsewhere."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "LinkVault"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "LinkVault"
    return Path.home() / ".config" / "LinkVault"


def config_candidates() -> list[Path]:
    """Portable config next to the exe has priority over the roaming one."""
    return [app_dir() / CONFIG_FILENAME, appdata_dir() / CONFIG_FILENAME]


def config_path(for_write: bool = False) -> Path:
    """Existing config path; when none exists yet, the default target."""
    for p in config_candidates():
        if p.is_file():
            return p
    if not for_write:
        return config_candidates()[0]
    portable_marker_dir = app_dir()
    try:
        portable_marker_dir.mkdir(parents=True, exist_ok=True)
        return portable_marker_dir / CONFIG_FILENAME
    except OSError:
        target = appdata_dir()
        target.mkdir(parents=True, exist_ok=True)
        return target / CONFIG_FILENAME


def default_data_dir() -> Path:
    """Fallback data dir: app_dir/data when writable, else roaming dir."""
    candidate = app_dir() / "data"
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        probe = candidate / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return candidate
    except OSError:
        roaming = appdata_dir() / "data"
        roaming.mkdir(parents=True, exist_ok=True)
        return roaming


def db_path(data_dir: Path) -> Path:
    return Path(data_dir) / DB_FILENAME


def logos_dir(data_dir: Path) -> Path:
    return Path(data_dir) / "logos"


def backups_dir(data_dir: Path) -> Path:
    return Path(data_dir) / "backups"


def log_path() -> Path:
    """app.log lives next to the config file (never inside the data dir)."""
    cfg = config_path()
    try:
        cfg.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return Path(os.devnull)
    return cfg.parent / "app.log"


def resolve_data_dir(raw: str | None) -> Path:
    """Turn the stored value (relative-to-app or absolute) into a real path."""
    if not raw:
        return default_data_dir()
    p = Path(raw)
    if not p.is_absolute():
        p = app_dir() / p
    return p


def store_data_dir(data_dir: Path) -> str:
    """Store relative to app_dir when possible so the folder stays portable."""
    data_dir = Path(data_dir).resolve()
    base = app_dir().resolve()
    try:
        rel = data_dir.relative_to(base)
        text = str(rel) if str(rel) != "." else "."
        return text
    except ValueError:
        return str(data_dir)


def is_writable_dir(path: Path) -> tuple[bool, str]:
    """Check that *path* exists (or can be created) and accepts writes."""
    path = Path(path)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"Không tạo được thư mục: {exc.strerror or exc}"
    probe = path / ".write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return False, f"Thư mục không cho ghi: {exc.strerror or exc}"
    return True, ""
