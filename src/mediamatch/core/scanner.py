"""Walk a root directory and identify media folders as movies or TV shows.

For v1.1 the scanner also discovers the season folders and episode files inside
each TV show, and the primary video file inside each movie folder. This data is
attached to the resulting MediaItem so the renamer can produce a full
Plex-standard rename plan covering folder, season, and individual files.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from .parser import parse_name

VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".m4v", ".mov", ".wmv",
    ".flv", ".webm", ".ts", ".m2ts", ".mpg", ".mpeg",
}

# Strict patterns used to *extract* season/episode numbers when we already
# believe we're looking at a TV folder.
SEASON_FOLDER_RE = re.compile(r"(?i)^(?:season[ ._-]*0*(\d+)|s0*(\d+))$")
SPECIALS_FOLDER_RE = re.compile(r"(?i)^(?:specials?|season[ ._-]*0+|s0+)$")
EPISODE_RE = re.compile(r"(?i)s(\d{1,2})e(\d{1,2})(?:[-e]+e?(\d{1,2}))?")
ALT_EPISODE_RE = re.compile(r"(?i)(\d{1,2})x(\d{2})")  # 1x01 style

# Broader hint patterns used purely to *classify* a folder as TV. These catch
# season hints in folder names ("Show.S01", "Series 2") and looser episode
# markers ("1x01", "Episode 3", absolute "E12").
_CLASSIFY_SEASON_HINT_RE = re.compile(r"(?i)\b(season|series|s\d{1,2})\b")
_CLASSIFY_EPISODE_HINT_RE = re.compile(
    r"[Ss]\d{1,2}[Ee]\d{1,2}"   # S01E01
    r"|\d{1,2}[xX]\d{2}"        # 1x01
    r"|\bE\d{2,3}\b"            # absolute E01
    r"|[Ee]pisode\.?\s*\d+"     # Episode 1 / Episode.1
)


class MediaType(Enum):
    MOVIE = auto()
    TV_SHOW = auto()
    UNKNOWN = auto()


@dataclass
class EpisodeFile:
    """A single episode video file inside a TV show folder."""
    path: Path
    season: int | None = None
    episode: int | None = None
    episode_end: int | None = None  # for multi-episode files (e.g. s01e01-e02)
    parsed_title: str | None = None
    is_special: bool = False  # lives in Specials/Season 00


@dataclass
class MovieFile:
    """The primary video file inside a movie folder."""
    path: Path


@dataclass
class RenameOp:
    """A single planned rename. kind: 'file' | 'season' | 'folder'."""
    src: Path
    dst_name: str
    kind: str
    enabled: bool = True
    error: str = ""
    conflict: bool = False
    done: bool = False

    @property
    def needs_rename(self) -> bool:
        return self.src.name != self.dst_name


@dataclass
class RenamePlan:
    ops: list[RenameOp] = field(default_factory=list)

    def enabled_ops(self) -> list[RenameOp]:
        return [o for o in self.ops if o.enabled and o.needs_rename]


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
    episodes: list[EpisodeFile] = field(default_factory=list)
    movie_file: MovieFile | None = None
    rename_plan: RenamePlan | None = None

    @property
    def needs_rename(self) -> bool:
        if self.rename_plan and self.rename_plan.enabled_ops():
            return True
        return bool(self.proposed_name) and self.proposed_name != self.original_name


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def _iter_video_files(path: Path):
    for f in path.rglob("*"):
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
            yield f


def _has_video_files(path: Path) -> bool:
    return any(True for _ in _iter_video_files(path))


def _season_number_from_dir(name: str) -> tuple[int | None, bool]:
    """Return (season_number, is_specials) inferred from a folder name."""
    if SPECIALS_FOLDER_RE.match(name):
        return 0, True
    m = SEASON_FOLDER_RE.match(name)
    if m:
        n = int(m.group(1) or m.group(2))
        return n, n == 0
    return None, False



def _episode_numbers_from_filename(name: str) -> tuple[int | None, int | None]:
    """Extract (episode, episode_end) directly from sNNeMM[-eOO] or NxMM in filename."""
    m = EPISODE_RE.search(name)
    if m:
        ep = int(m.group(2))
        end = int(m.group(3)) if m.group(3) else None
        return ep, end
    alt = ALT_EPISODE_RE.search(name)
    if alt:
        return int(alt.group(2)), None
    return None, None


def _classify_folder(path: Path) -> MediaType:
    """Decide whether a top-level title folder is a movie or a TV show."""
    # Strong signal: any direct child looks like a season/specials folder.
    for child in path.iterdir():
        if child.is_dir():
            season, _ = _season_number_from_dir(child.name)
            if season is not None or SPECIALS_FOLDER_RE.match(child.name):
                return MediaType.TV_SHOW
            # Looser hint: a child folder named "Season 4", "S03", "Series 2" etc.
            if _CLASSIFY_SEASON_HINT_RE.search(child.name):
                return MediaType.TV_SHOW

    # The top-level folder name itself may carry the hint, e.g. "Breaking.Bad.S01"
    if _CLASSIFY_SEASON_HINT_RE.search(path.name) or _CLASSIFY_EPISODE_HINT_RE.search(path.name):
        return MediaType.TV_SHOW

    # Otherwise: any video file with an episode marker (S01E01, 1x01,
    # Episode 1, absolute E01) is enough.
    video_files = list(_iter_video_files(path))
    if not video_files:
        return MediaType.UNKNOWN

    if any(_CLASSIFY_EPISODE_HINT_RE.search(f.name) for f in video_files):
        return MediaType.TV_SHOW

    name_parsed = parse_name(path.name)
    if name_parsed.media_type == "episode":
        return MediaType.TV_SHOW

    return MediaType.MOVIE


def _collect_episodes(show_root: Path) -> list[EpisodeFile]:
    """Walk a TV show folder and collect every episode video file."""
    episodes: list[EpisodeFile] = []

    for video in _iter_video_files(show_root):
        # Determine season: prefer enclosing season folder, then filename.
        season: int | None = None
        is_special = False
        for ancestor in video.parents:
            if ancestor == show_root:
                break
            s, sp = _season_number_from_dir(ancestor.name)
            if s is not None:
                season = s
                is_special = sp
                break

        ep, ep_end = _episode_numbers_from_filename(video.name)
        parsed = parse_name(video.stem, media_type_hint="tv")

        if season is None and parsed.season is not None:
            season = parsed.season
        if ep is None and parsed.episode is not None:
            ep = parsed.episode

        episodes.append(EpisodeFile(
            path=video,
            season=season,
            episode=ep,
            episode_end=ep_end,
            parsed_title=parsed.episode_title,
            is_special=is_special or season == 0,
        ))

    # If we found nothing with a season number but only one season folder
    # exists, fill in the season number from that folder. Already handled
    # above via ancestor lookup; nothing more to do here.
    return episodes


def _pick_movie_file(folder: Path) -> MovieFile | None:
    """Return the largest video file in the folder as the canonical movie file."""
    candidates = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
    ]
    if not candidates:
        # Look one level deeper for cases like Movie/VIDEO_TS or Movie/extras
        candidates = list(_iter_video_files(folder))
    if not candidates:
        return None
    # Skip obvious extras (samples, trailers) when there's a clearly bigger main file.
    sized = sorted(candidates, key=lambda f: f.stat().st_size, reverse=True)
    main = sized[0]
    # If the largest file is named 'sample' and there's another, prefer the other.
    if "sample" in main.stem.lower() and len(sized) > 1:
        main = sized[1]
    return MovieFile(path=main)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_directory(root: Path, progress_callback=None) -> list[MediaItem]:
    """Scan root for immediate child folders that contain media."""
    items: list[MediaItem] = []
    if not root.is_dir():
        return items

    candidates = [
        child for child in sorted(root.iterdir())
        if child.is_dir() and _has_video_files(child)
    ]

    total = len(candidates)
    for i, folder in enumerate(candidates):
        media_type = _classify_folder(folder)
        item = MediaItem(
            path=folder,
            media_type=media_type,
            original_name=folder.name,
        )
        if media_type == MediaType.TV_SHOW:
            item.episodes = _collect_episodes(folder)
        elif media_type == MediaType.MOVIE:
            item.movie_file = _pick_movie_file(folder)
        items.append(item)
        if progress_callback:
            progress_callback(i + 1, total, folder.name)

    return items
