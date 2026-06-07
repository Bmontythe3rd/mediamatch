"""Tests for name generation logic."""
from mediamatch.core.renamer import build_movie_name, build_tv_name, _sanitize


def test_movie_name_with_year_and_id():
    assert build_movie_name("The Dark Knight", 2008, 155) == "The Dark Knight (2008) {tmdb-155}"


def test_movie_name_no_id():
    assert build_movie_name("Inception", 2010) == "Inception (2010)"


def test_movie_name_no_year():
    assert build_movie_name("Unknown Film", None) == "Unknown Film"


def test_tv_name():
    assert build_tv_name("Breaking Bad", 2008, 1396) == "Breaking Bad (2008) {tmdb-1396}"


def test_sanitize_removes_forbidden_chars():
    assert _sanitize('A: B / C * D?') == "A B  C  D"


def test_sanitize_strips_trailing_dots():
    assert not _sanitize("foo.").endswith(".")
