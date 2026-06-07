"""TMDb API lookup with graceful offline fallback."""
from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _title_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.casefold(), b.casefold()).ratio()


@dataclass
class TMDbResult:
    tmdb_id: int
    title: str
    year: int | None
    overview: str = ""
    confidence: float = 1.0


class TMDbClient:
    def __init__(self, api_key: str = ""):
        self._api_key = api_key
        self._tmdb = None
        if api_key:
            self._init_client()

    def _init_client(self):
        try:
            from tmdbv3api import TMDb, Movie, TV
            tmdb = TMDb()
            tmdb.api_key = self._api_key
            tmdb.language = "en"
            self._tmdb = {"movie": Movie(), "tv": TV()}
            logger.info("TMDb client initialised")
        except Exception as exc:
            logger.warning("Failed to init TMDb client: %s", exc)
            self._tmdb = None

    def set_api_key(self, api_key: str):
        self._api_key = api_key
        self._tmdb = None
        if api_key:
            self._init_client()

    @property
    def available(self) -> bool:
        return self._tmdb is not None

    def search_movie(self, title: str, year: int | None = None) -> TMDbResult | None:
        if not self.available:
            return None
        try:
            results = list(self._tmdb["movie"].search(title) or [])
            if not results:
                return None

            scored: list[tuple[float, object, int | None]] = []
            for r in results:
                release_year = int(r.release_date[:4]) if getattr(r, "release_date", "") else None
                sim = _title_similarity(title, getattr(r, "title", "") or "")
                year_bonus = 0.15 if (year and release_year == year) else 0.0
                scored.append((sim + year_bonus, r, release_year))

            scored.sort(key=lambda x: x[0], reverse=True)
            best_score, r, release_year = scored[0]

            return TMDbResult(
                tmdb_id=r.id,
                title=r.title,
                year=release_year,
                overview=getattr(r, "overview", ""),
                confidence=min(best_score, 1.0),
            )
        except Exception as exc:
            logger.warning("TMDb movie search failed: %s", exc)
            return None

    def search_tv(self, title: str, year: int | None = None) -> TMDbResult | None:
        if not self.available:
            return None
        try:
            results = list(self._tmdb["tv"].search(title) or [])

            # If year-constrained search returned nothing, retry without year
            if not results:
                logger.debug("TMDb TV search for %r returned no results", title)
                return None

            # Score each result by title similarity + year match bonus
            scored: list[tuple[float, object, int | None]] = []
            for r in results:
                first_air = getattr(r, "first_air_date", "") or ""
                air_year = int(first_air[:4]) if first_air else None
                sim = _title_similarity(title, getattr(r, "name", "") or "")
                year_bonus = 0.15 if (year and air_year == year) else 0.0
                scored.append((sim + year_bonus, r, air_year))

            scored.sort(key=lambda x: x[0], reverse=True)
            best_score, r, air_year = scored[0]

            # If the best match is a poor title similarity, log a warning
            if best_score < 0.4:
                logger.warning(
                    "Low-confidence TV match for %r: %r (score=%.2f)",
                    title, getattr(r, "name", ""), best_score,
                )

            return TMDbResult(
                tmdb_id=r.id,
                title=r.name,
                year=air_year,
                overview=getattr(r, "overview", ""),
                confidence=min(best_score, 1.0),
            )
        except Exception as exc:
            logger.warning("TMDb TV search failed: %s", exc)
            return None
