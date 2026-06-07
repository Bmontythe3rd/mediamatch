"""Walk a root directory and identify media folders as movies or TV shows."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".m4v", ".mov", ".wmv",
    ".flv", ".webm", ".ts", ".m2ts", ".mpg", ".mpeg",
}

SEASON_PATTERNS = {"season", "s01", "s02", "s03", "s1", "s2", "s3"}


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
    """Heuristic: contains season-named subdirs or multiple episode-like video files."""
    children = [c for c in path.iterdir() if c.is_dir()]
    for child in children:
        name_lower = child.name.lower()
        if any(p in name_lower for p in SEASON_PATTERNS):
            return True

    # Check if there are multiple video files with SxxExx patterns
    import re
    episode_re = re.compile(r"[Ss]\d{1,2}[Ee]\d{1,2}")
    video_files = [f for f in path.rglob("*") if f.suffix.lower() in VIDEO_EXTENSIONS]
    matching = sum(1 for f in video_files if episode_re.search(f.name))
    return matching >= 2


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
