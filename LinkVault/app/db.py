"""SQLite access layer.  All SQL lives here; this module must not import PyQt.

Schema follows ARCHITECTURE.md section 6: one ``entries`` table shared by the
four tabs plus a ``notes`` table, migrations driven by PRAGMA user_version.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app import paths

log = logging.getLogger(__name__)

KINDS = ("mmo", "ai", "airdrop", "tool")
USER_VERSION = 1

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS entries(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK(kind IN ('mmo','ai','airdrop','tool')),
    name TEXT NOT NULL,
    logo TEXT,
    link TEXT,
    how_to TEXT,
    progress INTEGER DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
    tools TEXT DEFAULT '[]',
    note TEXT,
    status TEXT,
    effect TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_entries_kind_sort ON entries(kind, sort_order);
CREATE INDEX IF NOT EXISTS idx_entries_kind_status ON entries(kind, status);
CREATE TABLE IF NOT EXISTS notes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT,
    pinned INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    """One connection per thread; workers open their own instance."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        paths.logos_dir(self.data_dir).mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(paths.db_path(self.data_dir)))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    def close(self) -> None:
        try:
            self.conn.commit()
        finally:
            self.conn.close()

    # ------------------------------------------------------------- migration
    def _migrate(self) -> None:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version < 1:
            self.conn.executescript(SCHEMA_V1)
            self.conn.execute(f"PRAGMA user_version = {USER_VERSION}")
            self.conn.commit()

    # --------------------------------------------------------------- entries
    @staticmethod
    def _entry_params(e: dict) -> tuple:
        tools = e.get("tools") or []
        if isinstance(tools, str):
            tools = [t for t in tools.split(";") if t.strip()]
        return (
            e.get("kind", ""),
            e.get("name", "").strip(),
            e.get("logo"),
            (e.get("link") or "").strip(),
            e.get("how_to", ""),
            int(e.get("progress") or 0),
            json.dumps(list(tools), ensure_ascii=False),
            e.get("note", ""),
            e.get("status", ""),
            e.get("effect", ""),
            int(e.get("sort_order") or 0),
            e.get("created_at") or now_iso(),
            e.get("updated_at") or now_iso(),
        )

    def insert_entry(self, e: dict) -> int:
        ts = now_iso()
        params = self._entry_params(e)
        cur = self.conn.execute(
            "INSERT INTO entries(kind,name,logo,link,how_to,progress,tools,note,"
            "status,effect,sort_order,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            params[:-2] + (ts, ts),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_entry(self, entry_id: int, e: dict) -> None:
        params = self._entry_params(e)[:-2]
        self.conn.execute(
            "UPDATE entries SET kind=?,name=?,logo=?,link=?,how_to=?,progress=?,"
            "tools=?,note=?,status=?,effect=?,sort_order=?,updated_at=? WHERE id=?",
            params + (now_iso(), entry_id),
        )
        self.conn.commit()

    def delete_entry(self, entry_id: int) -> None:
        self.conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        self.conn.commit()

    def get_entry(self, entry_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone()
        return self.entry_row_to_dict(row) if row else None

    def entry_row_to_dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        try:
            d["tools"] = json.loads(d.get("tools") or "[]")
        except json.JSONDecodeError:
            d["tools"] = []
        return d

    def list_entries(self, kind: str, search: str = "", status: str = "") -> list[dict]:
        sql = "SELECT * FROM entries WHERE kind=?"
        args: list = [kind]
        if search:
            like = f"%{search}%"
            sql += " AND (name LIKE ? OR link LIKE ? OR note LIKE ? OR how_to LIKE ?)"
            args += [like, like, like, like]
        if status:
            sql += " AND status=?"
            args.append(status)
        sql += " ORDER BY sort_order, id"
        return [self.entry_row_to_dict(r) for r in self.conn.execute(sql, args)]

    def count_entries(self, kind: str) -> int:
        row = self.conn.execute("SELECT COUNT(*) c FROM entries WHERE kind=?", (kind,)).fetchone()
        return row["c"]

    def next_sort_order(self, kind: str) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM entries WHERE kind=?", (kind,)
        ).fetchone()
        return row["n"]

    def all_entries(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM entries ORDER BY kind, sort_order, id")
        return [self.entry_row_to_dict(r) for r in rows]

    # ----------------------------------------------------------------- notes
    def insert_note(self, n: dict) -> int:
        ts = now_iso()
        cur = self.conn.execute(
            "INSERT INTO notes(title,body,pinned,created_at,updated_at) VALUES(?,?,?,?,?)",
            (n.get("title", "").strip() or "Ghi chú", n.get("body", ""),
             1 if n.get("pinned") else 0, ts, ts),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_note(self, note_id: int, n: dict) -> None:
        self.conn.execute(
            "UPDATE notes SET title=?, body=?, pinned=?, updated_at=? WHERE id=?",
            (n.get("title", "").strip() or "Ghi chú", n.get("body", ""),
             1 if n.get("pinned") else 0, now_iso(), note_id),
        )
        self.conn.commit()

    def delete_note(self, note_id: int) -> None:
        self.conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        self.conn.commit()

    def get_note(self, note_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        return dict(row) if row else None

    def list_notes(self, search: str = "") -> list[dict]:
        sql = "SELECT * FROM notes"
        args: list = []
        if search:
            sql += " WHERE title LIKE ? OR body LIKE ?"
            args = [f"%{search}%", f"%{search}%"]
        sql += " ORDER BY pinned DESC, updated_at DESC"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def all_notes(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM notes ORDER BY id")]

    # ------------------------------------------------------- bulk operations
    def replace_all(self, entries: list[dict], notes: list[dict]) -> None:
        """Overwrite import mode: wipe then insert inside one transaction."""
        with self.conn:
            self.conn.execute("DELETE FROM entries")
            self.conn.execute("DELETE FROM notes")
            for e in entries:
                params = self._entry_params(e)
                self.conn.execute(
                    "INSERT INTO entries(id,kind,name,logo,link,how_to,progress,tools,"
                    "note,status,effect,sort_order,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (e.get("id"),) + params,
                )
            for n in notes:
                self.conn.execute(
                    "INSERT INTO notes(id,title,body,pinned,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?)",
                    (n.get("id"), n.get("title", ""), n.get("body", ""),
                     1 if n.get("pinned") else 0,
                     n.get("created_at") or now_iso(), n.get("updated_at") or now_iso()),
                )

    def find_entry_match(self, kind: str, name: str, link: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM entries WHERE kind=? AND lower(name)=lower(?) "
            "AND (link=? OR (link IS NULL AND ?=''))",
            (kind, name.strip(), (link or "").strip(), (link or "").strip()),
        ).fetchone()
        return self.entry_row_to_dict(row) if row else None

    def stats(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) c FROM entries").fetchone()["c"]
        notes = self.conn.execute("SELECT COUNT(*) c FROM notes").fetchone()["c"]
        size = 0
        db_file = paths.db_path(self.data_dir)
        if db_file.is_file():
            size = db_file.stat().st_size
        return {"entries": total, "notes": notes, "db_bytes": size}
