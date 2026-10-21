"""Atomic read/write of config.json (data_dir, theme, auto_backup, ...)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from app import paths

log = logging.getLogger(__name__)

VALID_THEMES = ("light", "dark", "system")
DEFAULTS: dict = {
    "schema_version": 1,
    "portable": False,          # True -> config + data live next to the exe
    "data_dir": "",              # relative to app_dir when inside it, else absolute
    "theme": "system",           # light | dark | system
    "auto_backup": True,
    "backup_keep": 5,
    "last_tab": "mmo",
    "window_geometry": "",       # base64 QByteArray, optional
}


def _merged(raw: dict) -> dict:
    cfg = dict(DEFAULTS)
    for key, value in raw.items():
        if key in cfg and type(value) is type(cfg[key]):
            cfg[key] = value
        elif key not in cfg:
            cfg[key] = value
    if cfg["theme"] not in VALID_THEMES:
        cfg["theme"] = "system"
    return cfg


def load() -> dict:
    """Read the first existing config file; fall back to defaults."""
    for p in paths.config_candidates():
        if p.is_file():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    return _merged(raw)
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("Config %s unreadable (%s), trying next", p, exc)
    return dict(DEFAULTS)


def save(cfg: dict) -> Path:
    """Write atomically (temp file + os.replace) with UTF-8."""
    target = paths.config_path(for_write=True)
    if cfg.get("portable"):
        target = paths.app_dir() / "config.json"
    payload = {k: v for k, v in cfg.items() if k in DEFAULTS or not k.startswith("_")}
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, target)
    return target


def resolved_data_dir(cfg: dict | None = None) -> Path:
    cfg = cfg if cfg is not None else load()
    return paths.resolve_data_dir(cfg.get("data_dir") or None)
