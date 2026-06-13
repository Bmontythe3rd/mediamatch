"""Tests for name generation and rename-plan construction."""
from pathlib import Path

from mediamatch.core.renamer import (
    build_movie_name, build_tv_name, build_season_folder,
    build_episode_filename, build_movie_filename, _sanitize,
    propose_name, apply_plan,
)
from mediamatch.core.scanner import (
    MediaItem, MediaType, EpisodeFile, MovieFile,
)


# -- Folder names -----------------------------------------------------------

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


# -- Plex season folder -----------------------------------------------------

def test_season_folder_zero_padded():
    assert build_season_folder(1) == "Season 01"
    assert build_season_folder(12) == "Season 12"


def test_season_folder_specials_is_season_zero():
    assert build_season_folder(0) == "Season 00"


# -- Episode filename builder ----------------------------------------------

def test_episode_filename_basic():
    name = build_episode_filename("Breaking Bad", 2008, 1, 1, episode_title="Pilot", ext=".mkv")
    assert name == "Breaking Bad (2008) - s01e01 - Pilot.mkv"


def test_episode_filename_no_title():
    name = build_episode_filename("Show", 2010, 2, 5, ext=".MP4")
    assert name == "Show (2010) - s02e05.mp4"


def test_episode_filename_multi_episode():
    name = build_episode_filename(
        "Show", 2010, 1, 1, episode_end=2, episode_title="Two-Parter", ext=".mkv"
    )
    assert name == "Show (2010) - s01e01-e02 - Two-Parter.mkv"


def test_episode_filename_strips_forbidden_chars():
    name = build_episode_filename("Title", 2020, 1, 1, episode_title="Bad: Char/Name", ext=".mkv")
    assert ":" not in name
    assert "/" not in name


# -- Movie filename --------------------------------------------------------

def test_movie_filename_uses_clean_title():
    assert build_movie_filename("Inception", 2010, ".MKV") == "Inception (2010).mkv"


# -- Plan construction & apply --------------------------------------------

def _make_show_fixture(tmp_path: Path) -> Path:
    """Build a small TV show fixture and return the root."""
    show = tmp_path / "breaking.bad.2008.s01"
    s01 = show / "Season 1"
    s01.mkdir(parents=True)
    (s01 / "breaking.bad.s01e01.pilot.mkv").write_bytes(b"x")
    (s01 / "breaking.bad.s01e02.cat.in.the.bag.mkv").write_bytes(b"x")
    specials = show / "Specials"
    specials.mkdir()
    (specials / "breaking.bad.s00e01.behind.the.scenes.mkv").write_bytes(b"x")
    return show


def test_tv_plan_creates_season_and_episode_ops(tmp_path: Path):
    from mediamatch.core.scanner import scan_directory

    root = tmp_path / "root"
    root.mkdir()
    _make_show_fixture(root)

    items = scan_directory(root)
    assert len(items) == 1
    item = items[0]
    assert item.media_type == MediaType.TV_SHOW

    propose_name(item, tmdb_client=None)

    plan = item.rename_plan
    assert plan is not None
    kinds = sorted(op.kind for op in plan.ops)
    assert "folder" in kinds
    assert kinds.count("season") >= 1
    assert kinds.count("file") >= 3

    season_targets = [op.dst_name for op in plan.ops if op.kind == "season"]
    assert "Season 01" in season_targets
    assert "Season 00" in season_targets

    file_targets = [op.dst_name for op in plan.ops if op.kind == "file"]
    assert any("s01e01" in n.lower() for n in file_targets)
    assert any("s00e01" in n.lower() for n in file_targets)


def test_apply_plan_renames_files_and_folders(tmp_path: Path):
    from mediamatch.core.scanner import scan_directory

    root = tmp_path / "root"
    root.mkdir()
    _make_show_fixture(root)

    [item] = scan_directory(root)
    propose_name(item, tmdb_client=None)
    successes, failures = apply_plan(item, dry_run=False)

    assert failures == []
    assert successes  # at least something renamed

    # Top folder should now match the proposed name (GuessIt may not
    # title-case without TMDb enrichment, so compare case-insensitively).
    assert item.path.exists()
    assert "breaking bad" in item.path.name.lower()
    assert "(2008)" in item.path.name

    # Season folders renamed.
    season_dirs = sorted(p.name for p in item.path.iterdir() if p.is_dir())
    assert "Season 00" in season_dirs
    assert "Season 01" in season_dirs

    # Episode files renamed inside Season 01.
    s01_files = sorted(p.name for p in (item.path / "Season 01").iterdir())
    assert any("s01e01" in name.lower() and name.lower().startswith("breaking bad") for name in s01_files)


def test_apply_plan_dry_run_changes_nothing(tmp_path: Path):
    from mediamatch.core.scanner import scan_directory

    root = tmp_path / "root"
    root.mkdir()
    show_path = _make_show_fixture(root)

    [item] = scan_directory(root)
    propose_name(item, tmdb_client=None)
    successes, failures = apply_plan(item, dry_run=True)

    assert successes
    assert failures == []
    # Dry run must not touch disk.
    assert show_path.exists()


def test_movie_plan_renames_inner_file(tmp_path: Path):
    from mediamatch.core.scanner import scan_directory

    root = tmp_path / "root"
    root.mkdir()
    movie_dir = root / "inception.2010.1080p.bluray.x264"
    movie_dir.mkdir()
    (movie_dir / "inception.2010.1080p.bluray.x264.mkv").write_bytes(b"x")

    [item] = scan_directory(root)
    assert item.media_type == MediaType.MOVIE
    propose_name(item, tmdb_client=None)
    successes, failures = apply_plan(item, dry_run=False)
    assert failures == []
    assert "(2010)" in item.path.name
    assert "inception" in item.path.name.lower()
    inside = [p.name for p in item.path.iterdir()]
    assert any(p.lower().startswith("inception") and p.lower().endswith("(2010).mkv") for p in inside)


def test_conflict_is_flagged(tmp_path: Path):
    """Two episodes that would produce the same target name get a conflict
    marker so the GUI can warn the user."""
    item = MediaItem(
        path=tmp_path,
        media_type=MediaType.TV_SHOW,
        original_name=tmp_path.name,
    )
    # Two episode files with the same season/episode numbers.
    f1 = tmp_path / "a.s01e01.mkv"
    f2 = tmp_path / "b.s01e01.mkv"
    f1.write_bytes(b"")
    f2.write_bytes(b"")
    item.episodes = [
        EpisodeFile(path=f1, season=1, episode=1),
        EpisodeFile(path=f2, season=1, episode=1),
    ]
    propose_name(item, tmdb_client=None)
    file_ops = [o for o in item.rename_plan.ops if o.kind == "file"]
    # Both file ops should be marked as conflicting since they target the
    # same name in the same parent folder.
    assert any(o.conflict for o in file_ops)
