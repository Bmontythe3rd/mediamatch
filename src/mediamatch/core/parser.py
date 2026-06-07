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


def parse_name(name: str) -> ParsedMedia:
    result = guessit(name)
    return ParsedMedia(
        title=str(result.get("title", name)),
        year=int(result["year"]) if "year" in result else None,
        season=int(result["season"]) if "season" in result else None,
        episode=int(result["episode"]) if "episode" in result else None,
        episode_title=str(result["episode_title"]) if "episode_title" in result else None,
        media_type=str(result.get("type", "movie")),
    )
