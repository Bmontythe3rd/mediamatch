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
        # episode title cache: (tv_id, season) -> {episode_number: name}
        self._episode_cache: dict[tuple[int, int], dict[int, str]] = {}
        if api_key:
            self._init_client()

    def _init_client(self):
        try:
            from tmdbv3api import TMDb, Movie, TV, Season
            tmdb = TMDb()
            tmdb.api_key = self._api_key
            tmdb.language = "en"
            self._tmdb = {"movie": Movie(), "tv": TV(), "season": Season()}
            logger.info("TMDb client initialised")
        except Exception as exc:
            logger.warning("Failed to init TMDb client: %s", exc)
            self._tmdb = None

    def set_api_key(self, api_key: str):
        self._api_key = api_key
        self._tmdb = None
        self._episode_cache.clear()
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

    def get_episode_title(self, tv_id: int, season: int, episode: int) -> str | None:
        """Fetch the episode title from TMDb. Caches the whole season the
        first time a given (tv_id, season) is requested."""
        if not self.available or tv_id is None or season is None or episode is None:
            return None
        key = (tv_id, season)
        if key not in self._episode_cache:
            try:
                details = self._tmdb["season"].details(tv_id, season)
                episodes = getattr(details, "episodes", []) or []
                self._episode_cache[key] = {
                    int(getattr(ep, "episode_number", 0)): str(getattr(ep, "name", "") or "")
                    for ep in episodes
                }
            except Exception as exc:
                logger.debug("TMDb season fetch failed (tv=%s s=%s): %s", tv_id, season, exc)
                self._episode_cache[key] = {}
        return self._episode_cache[key].get(episode) or None
