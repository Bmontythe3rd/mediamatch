"""TMDb API lookup with graceful offline fallback."""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
            results = self._tmdb["movie"].search(title)
            if not results:
                return None
            # Prefer result matching year if supplied
            best = None
            for r in results:
                release_year = int(r.release_date[:4]) if getattr(r, "release_date", "") else None
                if year and release_year == year:
                    best = (r, release_year)
                    break
            if best is None:
                r = results[0]
                release_year = int(r.release_date[:4]) if getattr(r, "release_date", "") else None
                best = (r, release_year)
            r, release_year = best
            return TMDbResult(
                tmdb_id=r.id,
                title=r.title,
                year=release_year,
                overview=getattr(r, "overview", ""),
            )
        except Exception as exc:
            logger.warning("TMDb movie search failed: %s", exc)
            return None

    def search_tv(self, title: str, year: int | None = None) -> TMDbResult | None:
        if not self.available:
            return None
        try:
            results = self._tmdb["tv"].search(title)
            if not results:
                return None
            best = None
            for r in results:
                first_air = getattr(r, "first_air_date", "") or ""
                air_year = int(first_air[:4]) if first_air else None
                if year and air_year == year:
                    best = (r, air_year)
                    break
            if best is None:
                r = results[0]
                first_air = getattr(r, "first_air_date", "") or ""
                air_year = int(first_air[:4]) if first_air else None
                best = (r, air_year)
            r, air_year = best
            return TMDbResult(
                tmdb_id=r.id,
                title=r.name,
                year=air_year,
                overview=getattr(r, "overview", ""),
            )
        except Exception as exc:
            logger.warning("TMDb TV search failed: %s", exc)
            return None
