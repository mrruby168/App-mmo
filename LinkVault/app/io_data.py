"""Import / export / migration / backup, run in QThreadPool workers.

Pure functions here are UI-free and unit-testable; the Task wrappers emit
progress/finish signals back to the main thread (ARCHITECTURE.md section 7).
"""

from __future__ import annotations

import base64
import csv
import io
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from app import paths
from app.db import Database, now_iso

log = logging.getLogger(__name__)

FORMAT_VERSION = 1
CSV_HEADERS = {
    "mmo": ["kind", "name", "logo", "link", "how_to", "progress", "tools", "note"],
    "ai": ["kind", "name", "logo", "link", "how_to", "progress", "tools", "note"],
    "airdrop": ["kind", "name", "logo", "status", "note"],
    "tool": ["kind", "name", "logo", "link", "effect"],
}
LOGO_MAX_PX = 96


# --------------------------------------------------------------------- logo
def save_logo_bytes(data: bytes, data_dir: Path, name_hint: str = "") -> str:
    """Store raw image bytes under data_dir/logos, return the file name only."""
    ext = "png"
    if data[:3] == b"\xff\xd8\xff":
        ext = "jpg"
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        ext = "gif"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        ext = "webp"
    digest = abs(hash((name_hint, len(data), datetime.now().isoformat())))
    fname = f"{digest % (10**8):08d}.{ext}"
    logos = paths.logos_dir(data_dir)
    logos.mkdir(parents=True, exist_ok=True)
    (logos / fname).write_bytes(data)
    return fname


def encode_logo(entry: dict, data_dir: Path) -> str | None:
    """Base64 of the logo file for JSON export (None when missing/broken)."""
    fname = entry.get("logo")
    if not fname:
        return None
    safe = Path(fname).name  # never trust stored path (traversal guard)
    fpath = paths.logos_dir(data_dir) / safe
    if not fpath.is_file():
        return None
    try:
        raw = fpath.read_bytes()
        if len(raw) > 2_000_000:
            return None
        return base64.b64encode(raw).decode("ascii")
    except OSError:
        return None


def decode_logo(b64: str | None, data_dir: Path, name_hint: str) -> str | None:
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception:
        return None
    return save_logo_bytes(raw, data_dir, name_hint)


# -------------------------------------------------------------------- JSON
def export_json(db: Database, dest: Path) -> int:
    """Full backup with logos embedded as base64. Returns item count."""
    entries = db.all_entries()
    notes = db.all_notes()
    payload = {
        "app": "LinkVault",
        "format_version": FORMAT_VERSION,
        "exported_at": now_iso(),
        "entries": [],
        "notes": notes,
    }
    for e in entries:
        row = {k: v for k, v in e.items() if k != "logo"}
        row["logo_name"] = Path(e["logo"]).name if e.get("logo") else None
        row["logo_b64"] = encode_logo(e, db.data_dir)
        payload["entries"].append(row)
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(entries) + len(notes)


def _entry_from_export_row(row: dict, data_dir: Path) -> dict:
    e = {
        "kind": row.get("kind", ""),
        "name": row.get("name", ""),
        "link": row.get("link", ""),
        "how_to": row.get("how_to", ""),
        "progress": row.get("progress", 0),
        "tools": row.get("tools", []),
        "note": row.get("note", ""),
        "status": row.get("status", ""),
        "effect": row.get("effect", ""),
        "sort_order": row.get("sort_order", 0),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }
    if row.get("logo_b64"):
        e["logo"] = decode_logo(row["logo_b64"], data_dir, e["name"])
    else:
        name = row.get("logo_name")
        e["logo"] = Path(name).name if name else None
    return e


def parse_json_import(path: Path) -> tuple[list[dict], list[dict], list[str]]:
    """Return (entries, notes, errors); every bad row is reported, not hidden."""
    errors: list[str] = []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [], [f"File không đọc được: {exc}"]
    if not isinstance(raw, dict) or raw.get("app") != "LinkVault":
        return [], [], ["File không phải bản xuất của Link Vault."]
    version = raw.get("format_version")
    if version != FORMAT_VERSION:
        errors.append(f"Phiên bản file {version!r} khác phiên bản hỗ trợ {FORMAT_VERSION}.")
    entries, notes = [], []
    for i, row in enumerate(raw.get("entries", []) or []):
        if not isinstance(row, dict) or not str(row.get("name", "")).strip():
            errors.append(f"Dòng entries thứ {i + 1}: thiếu tên.")
            continue
        if row.get("kind") not in ("mmo", "ai", "airdrop", "tool"):
            errors.append(f"Dòng entries thứ {i + 1}: kind không hợp lệ.")
            continue
        entries.append(row)
    for i, row in enumerate(raw.get("notes", []) or []):
        if not isinstance(row, dict) or not str(row.get("title", "")).strip():
            errors.append(f"Dòng notes thứ {i + 1}: thiếu tiêu đề.")
            continue
        notes.append(row)
    return entries, notes, errors


def import_json(db: Database, src: Path, mode: str = "merge") -> dict:
    """mode: 'merge' (match by kind+name+link) or 'overwrite' (replace all)."""
    rows, note_rows, errors = parse_json_import(src)
    result = {"added": 0, "updated": 0, "notes": 0, "errors": errors}
    if mode == "overwrite":
        entries = [_entry_from_export_row(r, db.data_dir) for r in rows]
        db.replace_all(entries, note_rows)
        result["added"] = len(entries)
        result["notes"] = len(note_rows)
        return result
    for row in rows:
        e = _entry_from_export_row(row, db.data_dir)
        existing = db.find_entry_match(e["kind"], e["name"], e.get("link") or "")
        if existing:
            newer = max(str(existing.get("updated_at") or ""), str(row.get("updated_at") or ""))
            merged = {**existing, **{k: v for k, v in e.items() if v not in (None, "", [])}}
            merged["updated_at"] = newer
            db.update_entry(existing["id"], merged)
            result["updated"] += 1
        else:
            e["sort_order"] = db.next_sort_order(e["kind"])
            db.insert_entry(e)
            result["added"] += 1
    for n in note_rows:
        match = db.conn.execute(
            "SELECT id FROM notes WHERE lower(title)=lower(?)", (n.get("title", ""),)
        ).fetchone()
        if match:
            db.update_note(match["id"], n)
        else:
            db.insert_note(n)
        result["notes"] += 1
    return result


# --------------------------------------------------------------------- CSV
def export_csv(db: Database, kind: str, dest: Path) -> int:
    headers = CSV_HEADERS[kind]
    text_io = io.StringIO()
    writer = csv.writer(text_io)
    writer.writerow(headers)
    rows = db.list_entries(kind)
    for e in rows:
        out = []
        for h in headers:
            v = e.get(h)
            if h == "tools" and isinstance(v, list):
                v = "; ".join(v)
            out.append("" if v is None else v)
        writer.writerow(out)
    dest.write_bytes(b"\xef\xbb\xbf" + text_io.getvalue().encode("utf-8"))
    return len(rows)


def import_csv(db: Database, src: Path, kind: str, mode: str = "merge") -> dict:
    result = {"added": 0, "updated": 0, "errors": []}
    try:
        content = src.read_bytes()
        if content.startswith(b"\xef\xbb\xbf"):
            content = content[3:]
        text = content.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        result["errors"].append(f"File CSV không đọc được: {exc}")
        return result
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "name" not in reader.fieldnames:
        result["errors"].append("CSV thiếu cột 'name'.")
        return result
    if mode == "overwrite":
        keep_notes = db.all_notes()
        db.replace_all([], keep_notes)
    for i, row in enumerate(reader):
        name = (row.get("name") or "").strip()
        if not name:
            result["errors"].append(f"Dòng {i + 2}: thiếu tên, đã bỏ qua.")
            continue
        tools_raw = row.get("tools") or ""
        e = {
            "kind": (row.get("kind") or kind).strip() or kind,
            "name": name,
            "logo": Path(row["logo"]).name if row.get("logo") else None,
            "link": (row.get("link") or "").strip(),
            "how_to": row.get("how_to", ""),
            "progress": int(float(row["progress"])) if str(row.get("progress", "")).strip()
            and str(row.get("progress")).strip().replace(".", "", 1).isdigit() else 0,
            "tools": [t.strip() for t in tools_raw.split(";") if t.strip()],
            "note": row.get("note", ""),
            "status": row.get("status", ""),
            "effect": row.get("effect", ""),
        }
        if e["kind"] not in ("mmo", "ai", "airdrop", "tool"):
            e["kind"] = kind
        if mode == "overwrite":
            db.insert_entry(e)
            result["added"] += 1
        else:
            existing = db.find_entry_match(e["kind"], e["name"], e["link"])
            if existing:
                db.update_entry(existing["id"], {**existing, **e})
                result["updated"] += 1
            else:
                e["sort_order"] = db.next_sort_order(e["kind"])
                db.insert_entry(e)
                result["added"] += 1
    return result


# ------------------------------------------------------------------ backup
def create_backup(db_dir: Path, keep: int = 5) -> Path | None:
    """Snapshot linkvault.db (+ logos folder marker) into data_dir/backups."""
    db_file = paths.db_path(db_dir)
    if not db_file.is_file():
        return None
    backups = paths.backups_dir(db_dir)
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backups / f"linkvault-{stamp}.db"
    src = sqlite3_connect_ro(db_file)
    dst = sqlite3_connect_rw(dest)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    rotate_backups(backups, keep)
    return dest


def sqlite3_connect_ro(db_file: Path):
    import sqlite3
    return sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)


def sqlite3_connect_rw(dest: Path):
    import sqlite3
    return sqlite3.connect(str(dest))


def rotate_backups(backups: Path, keep: int = 5) -> None:
    files = sorted(backups.glob("linkvault-*.db"), key=lambda p: p.name)
    for old in files[:-keep] if keep > 0 else files:
        try:
            old.unlink()
        except OSError as exc:
            log.warning("Backup rotation failed for %s: %s", old, exc)


# ------------------------------------------------------------- migration
def migrate_data_dir(db: Database, new_dir: Path, progress_cb=None) -> dict:
    """Copy DB + logos from current dir to *new_dir*; caller reopens there."""
    new_dir = Path(new_dir)
    ok, err = paths.is_writable_dir(new_dir)
    if not ok:
        raise RuntimeError(err)
    report = {"copied_db": False, "copied_logos": 0, "skipped": []}
    total_steps = 2
    if progress_cb:
        progress_cb(0, total_steps)
    src_db = paths.db_path(db.data_dir)
    if src_db.is_file():
        db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        dest_db = paths.db_path(new_dir)
        ro = sqlite3_connect_ro(src_db)
        rw = sqlite3_connect_rw(dest_db)
        try:
            ro.backup(rw)
        finally:
            ro.close()
            rw.close()
        report["copied_db"] = True
    if progress_cb:
        progress_cb(1, total_steps)
    src_logos = paths.logos_dir(db.data_dir)
    if src_logos.is_dir():
        dest_logos = paths.logos_dir(new_dir)
        dest_logos.mkdir(parents=True, exist_ok=True)
        for f in src_logos.iterdir():
            if f.is_file():
                try:
                    shutil.copy2(f, dest_logos / f.name)
                    report["copied_logos"] += 1
                except OSError as exc:
                    report["skipped"].append(f"{f.name}: {exc}")
    if progress_cb:
        progress_cb(2, total_steps)
    return report


# ---------------------------------------------------------------- workers
class WorkerSignals(QObject):
    finished = pyqtSignal(object)   # result payload
    progress = pyqtSignal(int, int)
    error = pyqtSignal(str)


class IOTask(QRunnable):
    """Run one of the pure functions above off the GUI thread."""

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @staticmethod
    def _default_progress(a, b):  # placeholder replaced below
        pass

    def run(self) -> None:  # noqa: D102
        import inspect

        try:
            kwargs = dict(self.kwargs)
            params = inspect.signature(self.fn).parameters
            if "progress_cb" in params:
                cb_sink = self.signals.progress
                kwargs["progress_cb"] = lambda cur, tot: cb_sink.emit(cur, tot)
            result = self.fn(*self.args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            log.exception("IO worker failed")
            self.signals.error.emit(str(exc))
            return
        self.signals.finished.emit(result)
