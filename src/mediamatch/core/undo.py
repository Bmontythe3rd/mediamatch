"""Persist a rename history so operations can be undone."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_LOG_PATH = Path.home() / ".mediamatch" / "undo_log.json"


def _load(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    try:
        return json.loads(log_path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(entries: list[dict], log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def record(old_path: Path, new_path: Path, log_path: Path = DEFAULT_LOG_PATH):
    entries = _load(log_path)
    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "old": str(old_path),
        "new": str(new_path),
    })
    _save(entries, log_path)


def undo_last(log_path: Path = DEFAULT_LOG_PATH) -> tuple[bool, str]:
    """Reverse the most recent logged rename. Returns (success, message)."""
    entries = _load(log_path)
    if not entries:
        return False, "Nothing to undo."
    last = entries[-1]
    old = Path(last["old"])
    new = Path(last["new"])
    if not new.exists():
        return False, f"Path no longer exists: {new}"
    try:
        new.rename(old)
        _save(entries[:-1], log_path)
        return True, f"Restored: {new.name} → {old.name}"
    except OSError as exc:
        return False, str(exc)


def clear_log(log_path: Path = DEFAULT_LOG_PATH):
    if log_path.exists():
        log_path.unlink()


def get_history(log_path: Path = DEFAULT_LOG_PATH) -> list[dict]:
    return _load(log_path)
