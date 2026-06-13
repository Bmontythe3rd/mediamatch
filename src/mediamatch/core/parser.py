"""Wrap guessit to extract structured info from a folder/file name."""
from __future__ import annotations

from dataclasses import dataclass

from guessit import guessit


@dataclass
class ParsedMedia:
    title: str
    year: int | None
    season: int | None
    episode: int | None
    episode_title: str | None
    media_type: str  # "movie" or "episode"


def _first_int(value) -> int | None:
    """GuessIt may return a single int or a list (multi-episode files)."""
    if value is None:
        return None
    if isinstance(value, list):
        return int(value[0]) if value else None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_name(name: str, media_type_hint: str | None = None) -> ParsedMedia:
    """Parse a filename or folder name into structured media info.

    media_type_hint: "tv" or "movie" — when supplied, passed to guessit so it
    doesn't have to guess the type from context alone.
    """
    options: dict = {}
    if media_type_hint == "tv":
        options["type"] = "episode"
    elif media_type_hint == "movie":
        options["type"] = "movie"
    result = guessit(name, options)
    return ParsedMedia(
        title=str(result.get("title", name)),
        year=_first_int(result.get("year")),
        season=_first_int(result.get("season")),
        episode=_first_int(result.get("episode")),
        episode_title=str(result["episode_title"]) if "episode_title" in result else None,
        media_type=str(result.get("type", "movie")),
    )
