"""Tests for the TV show vs movie detection heuristic."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from mediamatch.core.scanner import _looks_like_tv, VIDEO_EXTENSIONS


def _make_tree(tmp_path: Path, structure: dict) -> Path:
    """Build a directory tree from a nested dict.
    Keys ending in a video extension become files; all others become dirs.
    """
    for name, children in structure.items():
        node = tmp_path / name
        if any(name.endswith(ext) for ext in VIDEO_EXTENSIONS):
            node.touch()
        else:
            node.mkdir(parents=True, exist_ok=True)
            if isinstance(children, dict):
                _make_tree(node, children)
    return tmp_path


class TestLooksLikeTv:
    def test_season_subfolder(self, tmp_path):
        show = tmp_path / "Breaking Bad"
        show.mkdir()
        (show / "Season 1").mkdir()
        (show / "Season 1" / "s01e01.mkv").touch()
        assert _looks_like_tv(show)

    def test_season_subfolder_high_number(self, tmp_path):
        show = tmp_path / "Grey's Anatomy"
        show.mkdir()
        (show / "Season 15").mkdir()
        (show / "Season 15" / "s15e01.mkv").touch()
        assert _looks_like_tv(show)

    def test_s_numbered_subfolder(self, tmp_path):
        show = tmp_path / "The Wire"
        show.mkdir()
        (show / "S04").mkdir()
        (show / "S04" / "episode.mkv").touch()
        assert _looks_like_tv(show)

    def test_episode_file_sxxexx(self, tmp_path):
        show = tmp_path / "Chernobyl"
        show.mkdir()
        (show / "Chernobyl.S01E01.1080p.mkv").touch()
        assert _looks_like_tv(show)

    def test_episode_file_1x01_style(self, tmp_path):
        show = tmp_path / "Firefly"
        show.mkdir()
        (show / "Firefly.1x01.mkv").touch()
        assert _looks_like_tv(show)

    def test_episode_word_in_filename(self, tmp_path):
        show = tmp_path / "Some Miniseries"
        show.mkdir()
        (show / "Episode.1.mkv").touch()
        assert _looks_like_tv(show)

    def test_folder_name_contains_season(self, tmp_path):
        show = tmp_path / "Breaking.Bad.S03"
        show.mkdir()
        (show / "episode.mkv").touch()
        assert _looks_like_tv(show)

    def test_single_episode_folder(self, tmp_path):
        """A folder with one episode file should be detected as TV (not require 2+)."""
        show = tmp_path / "Pilot"
        show.mkdir()
        (show / "Show.S01E01.mkv").touch()
        assert _looks_like_tv(show)

    def test_plain_movie_folder(self, tmp_path):
        movie = tmp_path / "The Dark Knight"
        movie.mkdir()
        (movie / "The.Dark.Knight.2008.mkv").touch()
        assert not _looks_like_tv(movie)

    def test_movie_with_year_in_name(self, tmp_path):
        movie = tmp_path / "Inception (2010)"
        movie.mkdir()
        (movie / "Inception.2010.BluRay.mkv").touch()
        assert not _looks_like_tv(movie)
