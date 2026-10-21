"""Qt models: dataclasses Entry/Note plus list models backed by Database.

Models reload lazily in batches (fetchMore) so huge lists stay responsive;
views use delegates, never one widget per row (ARCHITECTURE.md section 8).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt

BATCH = 200

ENTRY_FIELDS = ("kind", "name", "logo", "link", "how_to", "progress",
                "tools", "note", "status", "effect", "sort_order")
NOTE_FIELDS = ("title", "body", "pinned")


@dataclass
class Entry:
    id: int = 0
    kind: str = "mmo"
    name: str = ""
    logo: str | None = None
    link: str = ""
    how_to: str = ""
    progress: int = 0
    tools: list = field(default_factory=list)
    note: str = ""
    status: str = ""
    effect: str = ""
    sort_order: int = 0
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Entry":
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def to_dict(self) -> dict:
        return copy.deepcopy(self.__dict__)


@dataclass
class Note:
    id: int = 0
    title: str = ""
    body: str = ""
    pinned: bool = False
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Note":
        d = dict(d)
        if "pinned" in d:
            d["pinned"] = bool(d["pinned"])
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["pinned"] = 1 if self.pinned else 0
        return d


class _BatchedModel(QAbstractListModel):
    """Shared batching logic: keep a loaded prefix, fetch more on demand."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._items: list = []
        self._total = 0

    # ---------------------------------------------------------- public API
    def item_at(self, row: int):
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def find_by_id(self, item_id: int):
        for i, it in enumerate(self._items):
            if it.id == item_id:
                return i, it
        return -1, None

    def rowCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self._items)

    def canFetchMore(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self._items) < self._total

    def fetchMore(self, parent=QModelIndex()):  # noqa: N802
        if parent.isValid():
            return
        remaining = self._total - len(self._items)
        take = min(BATCH, remaining)
        if take <= 0:
            return
        self.beginInsertRows(QModelIndex(), len(self._items), len(self._items) + take - 1)
        self._items.extend(self._fetch_batch(len(self._items), take))
        self.endInsertRows()

    # -------------------------------------------------------- subclass hooks
    def _count(self) -> int:
        raise NotImplementedError

    def _fetch_batch(self, offset: int, limit: int) -> list:
        raise NotImplementedError

    def reload(self) -> None:
        self.beginResetModel()
        self._total = self._count()
        self._items = self._fetch_batch(0, min(BATCH, self._total))
        self.endResetModel()

    def refresh_filtered(self) -> None:
        """Re-run the filtered query from scratch (search / filter changed)."""
        self.reload()


class EntryListModel(_BatchedModel):
    ROLES = {
        Qt.ItemDataRole.UserRole + 1: "id",
        Qt.ItemDataRole.UserRole + 2: "kind",
        Qt.ItemDataRole.UserRole + 3: "name",
        Qt.ItemDataRole.UserRole + 4: "logo",
        Qt.ItemDataRole.UserRole + 5: "link",
        Qt.ItemDataRole.UserRole + 6: "how_to",
        Qt.ItemDataRole.UserRole + 7: "progress",
        Qt.ItemDataRole.UserRole + 8: "tools",
        Qt.ItemDataRole.UserRole + 9: "note",
        Qt.ItemDataRole.UserRole + 10: "status",
        Qt.ItemDataRole.UserRole + 11: "effect",
        Qt.ItemDataRole.UserRole + 12: "entry",
    }
    REVERSE = {v: k for k, v in ROLES.items()}

    def __init__(self, db, kind: str, parent=None):
        self.kind = kind
        self.search = ""
        self.status_filter = ""
        super().__init__(db, parent)

    def set_filters(self, search: str = "", status: str = "") -> None:
        if search != self.search or status != self.status_filter:
            self.search = search
            self.status_filter = status
            self.refresh_filtered()

    def _query(self, offset: int | None = None, limit: int | None = None):
        sql = "SELECT * FROM entries WHERE kind=?"
        args: list = [self.kind]
        if self.search:
            like = f"%{self.search}%"
            sql += " AND (name LIKE ? OR link LIKE ? OR note LIKE ? OR how_to LIKE ?)"
            args += [like, like, like, like]
        if self.status_filter:
            sql += " AND status=?"
            args.append(self.status_filter)
        sql += " ORDER BY sort_order, id"
        if offset is not None and limit is not None:
            sql += " LIMIT ? OFFSET ?"
            args += [limit, offset]
        return self.db.conn.execute(sql, args)

    def _count(self) -> int:
        return len(self._query().fetchall())

    def _fetch_batch(self, offset: int, limit: int) -> list:
        return [Entry.from_dict(self.db.entry_row_to_dict(r))
                for r in self._query(offset, limit)]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        entry = self._items[index.row()]
        if role in self.ROLES:
            key = self.ROLES[role]
            if key == "entry":
                return entry
            value = getattr(entry, key)
            if key == "tools":
                return "; ".join(value)
            return value
        return None

    # ------------------------------------------------------------ CRUD sync
    def add(self, entry: Entry) -> int:
        entry.sort_order = self.db.next_sort_order(self.kind)
        entry.id = self.db.insert_entry(entry.to_dict())
        self.beginResetModel()
        self.reload_internal()
        self.endResetModel()
        return entry.id

    def update(self, entry: Entry) -> None:
        self.db.update_entry(entry.id, entry.to_dict())
        row, existing = self.find_by_id(entry.id)
        if row >= 0:
            reloaded = Entry.from_dict(self.db.get_entry(entry.id))
            self._items[row] = reloaded
            idx = self.index(row)
            self.dataChanged.emit(idx, idx)
        elif self._matches(entry):
            self.refresh_filtered()

    def remove(self, entry_id: int) -> Entry | None:
        removed = self.db.get_entry(entry_id)
        self.db.delete_entry(entry_id)
        row, _ = self.find_by_id(entry_id)
        if row >= 0:
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._items[row]
            self._total = max(0, self._total - 1)
            self.endRemoveRows()
        return Entry.from_dict(removed) if removed else None

    def restore(self, entry: Entry) -> int:
        """Undo-delete: re-insert keeping original field values."""
        new_id = self.db.insert_entry(entry.to_dict())
        self.refresh_filtered()
        return new_id

    def _matches(self, entry: Entry) -> bool:
        if entry.kind != self.kind:
            return False
        if self.status_filter and entry.status != self.status_filter:
            return False
        if self.search:
            s = self.search.lower()
            haystack = " ".join([entry.name, entry.link, entry.note, entry.how_to]).lower()
            return s in haystack
        return True

    def reload_internal(self) -> None:
        """Reload without emitting reset (caller already began reset)."""
        self._total = self._count()
        self._items = self._fetch_batch(0, min(BATCH, self._total))

    def reload(self) -> None:  # noqa: D102 (override with internal variant)
        self.beginResetModel()
        self.reload_internal()
        self.endResetModel()


class NoteListModel(_BatchedModel):
    ROLES = {
        Qt.ItemDataRole.UserRole + 1: "id",
        Qt.ItemDataRole.UserRole + 2: "title",
        Qt.ItemDataRole.UserRole + 3: "body",
        Qt.ItemDataRole.UserRole + 4: "pinned",
        Qt.ItemDataRole.UserRole + 5: "updated_at",
        Qt.ItemDataRole.UserRole + 6: "note",
    }

    def __init__(self, db, parent=None):
        self.search = ""
        super().__init__(db, parent)

    def set_search(self, text: str) -> None:
        if text != self.search:
            self.search = text
            self.refresh_filtered()

    def _query(self, offset=None, limit=None):
        sql = "SELECT * FROM notes"
        args: list = []
        if self.search:
            sql += " WHERE title LIKE ? OR body LIKE ?"
            args += [f"%{self.search}%", f"%{self.search}%"]
        sql += " ORDER BY pinned DESC, updated_at DESC"
        if offset is not None and limit is not None:
            sql += " LIMIT ? OFFSET ?"
            args += [limit, offset]
        return self.db.conn.execute(sql, args)

    def _count(self) -> int:
        return len(self._query().fetchall())

    def _fetch_batch(self, offset: int, limit: int) -> list:
        return [Note.from_dict(dict(r)) for r in self._query(offset, limit)]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        note = self._items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return note.title
        if role in self.ROLES:
            key = self.ROLES[role]
            return getattr(note, key) if key != "note" else note
        return None

    def add(self, note: Note) -> int:
        note.id = self.db.insert_note(note.to_dict())
        self.reload()
        return note.id

    def update(self, note: Note) -> None:
        self.db.update_note(note.id, note.to_dict())
        self.reload()

    def remove(self, note_id: int) -> Note | None:
        removed = self.db.get_note(note_id)
        self.db.delete_note(note_id)
        self.reload()
        return Note.from_dict(removed) if removed else None

    def restore(self, note: Note) -> int:
        new_id = self.db.insert_note(note.to_dict())
        self.reload()
        return new_id
