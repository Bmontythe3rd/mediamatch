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
        year=int(result["year"]) if "year" in result else None,
        season=int(result["season"]) if "season" in result else None,
        episode=int(result["episode"]) if "episode" in result else None,
        episode_title=str(result["episode_title"]) if "episode_title" in result else None,
        media_type=str(result.get("type", "movie")),
    )
