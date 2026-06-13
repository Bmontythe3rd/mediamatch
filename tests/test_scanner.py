"""Scanner tests against a synthetic filesystem fixture."""
from pathlib import Path

from mediamatch.core.scanner import (
    scan_directory, MediaType,
    _season_number_from_dir, _episode_numbers_from_filename, _classify_folder,
    VIDEO_EXTENSIONS,
)


# -- Season-folder name parser ---------------------------------------------

def test_season_folder_detection():
    assert _season_number_from_dir("Season 01") == (1, False)
    assert _season_number_from_dir("season 12") == (12, False)
    assert _season_number_from_dir("S03") == (3, False)
    assert _season_number_from_dir("Specials") == (0, True)
    assert _season_number_from_dir("Season 00") == (0, True)
    assert _season_number_from_dir("Random") == (None, False)


# -- Episode number extraction --------------------------------------------

def test_episode_regex_finds_numbers():
    assert _episode_numbers_from_filename("Show.S01E03.mkv") == (3, None)
    assert _episode_numbers_from_filename("Show.s02e10-e11.mkv") == (10, 11)
    assert _episode_numbers_from_filename("Show.s01e05e06.mkv") == (5, 6)
    assert _episode_numbers_from_filename("Show.1x07.mkv") == (7, None)
    assert _episode_numbers_from_filename("nothing.mkv") == (None, None)


# -- Classification --------------------------------------------------------

def test_classify_tv_via_season_folder(tmp_path: Path):
    show = tmp_path / "Show"
    s1 = show / "Season 1"
    s1.mkdir(parents=True)
    (s1 / "show.s01e01.mkv").write_bytes(b"")
    assert _classify_folder(show) == MediaType.TV_SHOW


def test_classify_tv_via_high_season_number(tmp_path: Path):
    show = tmp_path / "Grey's Anatomy"
    (show / "Season 15").mkdir(parents=True)
    (show / "Season 15" / "ep.mkv").write_bytes(b"")
    assert _classify_folder(show) == MediaType.TV_SHOW


def test_classify_tv_via_s_numbered_folder(tmp_path: Path):
    show = tmp_path / "The Wire"
    (show / "S04").mkdir(parents=True)
    (show / "S04" / "episode.mkv").write_bytes(b"")
    assert _classify_folder(show) == MediaType.TV_SHOW


def test_classify_tv_via_multiple_episode_files(tmp_path: Path):
    show = tmp_path / "Anime"
    show.mkdir()
    (show / "anime.s01e01.mkv").write_bytes(b"")
    (show / "anime.s01e02.mkv").write_bytes(b"")
    assert _classify_folder(show) == MediaType.TV_SHOW


def test_classify_tv_via_single_episode_file(tmp_path: Path):
    """One episode file with an episode marker is enough — miniseries case."""
    show = tmp_path / "Pilot"
    show.mkdir()
    (show / "Show.S01E01.mkv").write_bytes(b"")
    assert _classify_folder(show) == MediaType.TV_SHOW


def test_classify_tv_via_1x01_style(tmp_path: Path):
    show = tmp_path / "Firefly"
    show.mkdir()
    (show / "Firefly.1x01.mkv").write_bytes(b"")
    assert _classify_folder(show) == MediaType.TV_SHOW


def test_classify_tv_via_episode_word(tmp_path: Path):
    show = tmp_path / "Some Miniseries"
    show.mkdir()
    (show / "Episode.1.mkv").write_bytes(b"")
    assert _classify_folder(show) == MediaType.TV_SHOW


def test_classify_tv_via_folder_name_only(tmp_path: Path):
    """Folder named 'Breaking.Bad.S03' is TV even if the inner file isn't marked."""
    show = tmp_path / "Breaking.Bad.S03"
    show.mkdir()
    (show / "episode.mkv").write_bytes(b"")
    assert _classify_folder(show) == MediaType.TV_SHOW


def test_classify_movie_plain(tmp_path: Path):
    folder = tmp_path / "inception.2010"
    folder.mkdir()
    (folder / "inception.2010.mkv").write_bytes(b"")
    assert _classify_folder(folder) == MediaType.MOVIE


def test_classify_movie_with_year_in_name(tmp_path: Path):
    folder = tmp_path / "Inception (2010)"
    folder.mkdir()
    (folder / "Inception.2010.BluRay.mkv").write_bytes(b"")
    assert _classify_folder(folder) == MediaType.MOVIE


# -- Full scan ------------------------------------------------------------

def test_scan_directory_attaches_episodes(tmp_path: Path):
    root = tmp_path
    show = root / "breaking.bad.s01"
    s1 = show / "Season 1"
    s1.mkdir(parents=True)
    (s1 / "breaking.bad.s01e01.pilot.mkv").write_bytes(b"")
    (s1 / "breaking.bad.s01e02.cat.in.the.bag.mkv").write_bytes(b"")

    items = scan_directory(root)
    assert len(items) == 1
    item = items[0]
    assert item.media_type == MediaType.TV_SHOW
    assert len(item.episodes) == 2
    seasons = {ep.season for ep in item.episodes}
    assert seasons == {1}
    episodes = sorted(ep.episode for ep in item.episodes)
    assert episodes == [1, 2]


def test_scan_directory_attaches_movie_file(tmp_path: Path):
    root = tmp_path
    folder = root / "inception.2010"
    folder.mkdir()
    main = folder / "inception.2010.mkv"
    main.write_bytes(b"x" * 1000)
    sample = folder / "sample.mkv"
    sample.write_bytes(b"x")

    [item] = scan_directory(root)
    assert item.media_type == MediaType.MOVIE
    assert item.movie_file is not None
    assert item.movie_file.path.name == "inception.2010.mkv"
