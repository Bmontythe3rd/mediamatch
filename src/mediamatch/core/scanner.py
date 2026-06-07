"""Walk a root directory and identify media folders as movies or TV shows."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".m4v", ".mov", ".wmv",
    ".flv", ".webm", ".ts", ".m2ts", ".mpg", ".mpeg",
}

# Matches season/series subdirectory names (Season 1, S01, S10, Series 2, etc.)
_SEASON_DIR_RE = re.compile(r'\b(season|series|s\d{1,2})\b', re.IGNORECASE)

# Matches episode markers in filenames/folder names
_EPISODE_RE = re.compile(
    r'[Ss]\d{1,2}[Ee]\d{1,2}'   # S01E01
    r'|\d{1,2}[xX]\d{2}'        # 1x01
    r'|\bE\d{2,3}\b'             # E01 absolute
    r'|[Ee]pisode\.?\s*\d+'      # Episode 1 / Episode.1
)


class MediaType(Enum):
    MOVIE = auto()
    TV_SHOW = auto()
    UNKNOWN = auto()


@dataclass
class MediaItem:
    path: Path
    media_type: MediaType
    original_name: str
    proposed_name: str = ""
    tmdb_id: int | None = None
    tmdb_title: str = ""
    tmdb_year: int | None = None
    confidence: float = 0.0
    enabled: bool = True
    error: str = ""

    @property
    def needs_rename(self) -> bool:
        return bool(self.proposed_name) and self.proposed_name != self.original_name


def _has_video_files(path: Path) -> bool:
    return any(f.suffix.lower() in VIDEO_EXTENSIONS for f in path.rglob("*") if f.is_file())


def _looks_like_tv(path: Path) -> bool:
    """Heuristic: folder name, subdirs, or video files contain season/episode markers."""
    # Check the top-level folder name itself (e.g. "Breaking.Bad.S01" or "Show.S01E01")
    if _SEASON_DIR_RE.search(path.name) or _EPISODE_RE.search(path.name):
        return True

    # Check immediate subdirectory names for season folders (Season 1, S02, Series 3, etc.)
    for child in path.iterdir():
        if child.is_dir() and _SEASON_DIR_RE.search(child.name):
            return True

    # Check video file names — any single episode marker is enough
    video_files = [f for f in path.rglob("*") if f.suffix.lower() in VIDEO_EXTENSIONS]
    return any(_EPISODE_RE.search(f.name) for f in video_files)


def scan_directory(root: Path, progress_callback=None) -> list[MediaItem]:
    """Scan root for immediate child folders that contain media."""
    items: list[MediaItem] = []

    if not root.is_dir():
        return items

    # Gather immediate children that contain video files
    candidates = [
        child for child in sorted(root.iterdir())
        if child.is_dir() and _has_video_files(child)
    ]

    total = len(candidates)
    for i, folder in enumerate(candidates):
        media_type = MediaType.TV_SHOW if _looks_like_tv(folder) else MediaType.MOVIE
        items.append(MediaItem(
            path=folder,
            media_type=media_type,
            original_name=folder.name,
        ))
        if progress_callback:
            progress_callback(i + 1, total, folder.name)

    return items
