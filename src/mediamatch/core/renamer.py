"""Generate Plex/Jellyfin-compliant target names and apply renames."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from .parser import parse_name, ParsedMedia
from .scanner import MediaItem, MediaType
from .tmdb import TMDbClient, TMDbResult

logger = logging.getLogger(__name__)


def _sanitize(name: str) -> str:
    """Remove characters forbidden in folder names on Windows/macOS/Linux."""
    forbidden = r'\/:*?"<>|'
    for ch in forbidden:
        name = name.replace(ch, "")
    return name.strip(" .")


def build_movie_name(title: str, year: int | None, tmdb_id: int | None = None) -> str:
    base = _sanitize(title)
    if year:
        base = f"{base} ({year})"
    if tmdb_id:
        base = f"{base} {{tmdb-{tmdb_id}}}"
    return base


def build_tv_name(title: str, year: int | None, tmdb_id: int | None = None) -> str:
    base = _sanitize(title)
    if year:
        base = f"{base} ({year})"
    if tmdb_id:
        base = f"{base} {{tmdb-{tmdb_id}}}"
    return base


def propose_name(item: MediaItem, tmdb_client: TMDbClient | None = None) -> MediaItem:
    """Fill item.proposed_name (and TMDb fields) without touching the filesystem."""
    hint = "tv" if item.media_type == MediaType.TV_SHOW else "movie"
    parsed: ParsedMedia = parse_name(item.original_name, media_type_hint=hint)

    tmdb_result: TMDbResult | None = None
    if tmdb_client and tmdb_client.available:
        if item.media_type == MediaType.MOVIE:
            tmdb_result = tmdb_client.search_movie(parsed.title, parsed.year)
        else:
            tmdb_result = tmdb_client.search_tv(parsed.title, parsed.year)

    if tmdb_result:
        item.tmdb_id = tmdb_result.tmdb_id
        item.tmdb_title = tmdb_result.title
        item.tmdb_year = tmdb_result.year
        item.confidence = tmdb_result.confidence
        title = tmdb_result.title
        year = tmdb_result.year
    else:
        title = parsed.title
        year = parsed.year
        item.confidence = 0.5 if parsed.title else 0.0

    if item.media_type == MediaType.MOVIE:
        item.proposed_name = build_movie_name(title, year, item.tmdb_id)
    else:
        item.proposed_name = build_tv_name(title, year, item.tmdb_id)

    return item


def apply_rename(item: MediaItem) -> bool:
    """Rename item.path on disk. Returns True on success."""
    if not item.needs_rename or not item.enabled:
        return False
    new_path = item.path.parent / item.proposed_name
    if new_path.exists():
        item.error = f"Target already exists: {item.proposed_name}"
        logger.warning(item.error)
        return False
    try:
        item.path.rename(new_path)
        item.path = new_path
        item.original_name = item.proposed_name
        item.proposed_name = ""
        item.error = ""
        return True
    except OSError as exc:
        item.error = str(exc)
        logger.error("Rename failed for %s: %s", item.path, exc)
        return False
