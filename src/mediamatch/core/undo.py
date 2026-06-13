"""Persist a rename history so operations can be undone.

A single Apply click may produce many filesystem renames (folder + season
folders + episode files). They're grouped into one batch entry so that a
single Undo click reverses the whole apply.

Schema:
    [
      {
        "timestamp": "...",
        "moves": [{"old": "...", "new": "..."}, ...]
      },
      # Legacy entries from v1.0 are still understood:
      {"timestamp": "...", "old": "...", "new": "..."}
    ]
"""
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


def _entry_moves(entry: dict) -> list[tuple[Path, Path]]:
    """Normalise both new-style batch and legacy single entries."""
    if "moves" in entry:
        return [(Path(m["old"]), Path(m["new"])) for m in entry["moves"]]
    if "old" in entry and "new" in entry:
        return [(Path(entry["old"]), Path(entry["new"]))]
    return []


def record_batch(moves: list[tuple[Path, Path]], log_path: Path = DEFAULT_LOG_PATH):
    """Append a single batch entry holding every move from one Apply click."""
    if not moves:
        return
    entries = _load(log_path)
    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "moves": [{"old": str(o), "new": str(n)} for o, n in moves],
    })
    _save(entries, log_path)


def record(old_path: Path, new_path: Path, log_path: Path = DEFAULT_LOG_PATH):
    """Legacy single-move recorder, kept for compatibility."""
    record_batch([(old_path, new_path)], log_path)


def undo_last(log_path: Path = DEFAULT_LOG_PATH) -> tuple[bool, str]:
    """Reverse every rename in the most recent batch. Returns (success, message)."""
    entries = _load(log_path)
    if not entries:
        return False, "Nothing to undo."
    last = entries[-1]
    moves = _entry_moves(last)
    if not moves:
        # Malformed entry; drop and try again.
        _save(entries[:-1], log_path)
        return False, "Skipped malformed undo entry."

    # Reverse in opposite order of application: folder -> season -> file
    # was the original order (file first); to undo we reverse the list so
    # parent renames are reverted before the children they contained.
    reversed_count = 0
    errors: list[str] = []
    for old, new in reversed(moves):
        if not new.exists():
            errors.append(f"Missing: {new.name}")
            continue
        try:
            new.rename(old)
            reversed_count += 1
        except OSError as exc:
            errors.append(f"{new.name}: {exc}")

    _save(entries[:-1], log_path)
    if errors and reversed_count == 0:
        return False, "; ".join(errors)
    summary = f"Reverted {reversed_count} rename(s)."
    if errors:
        summary += f" {len(errors)} skipped."
    return True, summary


def clear_log(log_path: Path = DEFAULT_LOG_PATH):
    if log_path.exists():
        log_path.unlink()


def get_history(log_path: Path = DEFAULT_LOG_PATH) -> list[dict]:
    return _load(log_path)
