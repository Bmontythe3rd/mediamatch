# Changelog

All notable changes to MediaMatch will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-06-13

### Added
- **Full Plex-standard renames** for TV shows: season folders normalised to
  `Season XX` (and `Season 00` for specials) and episode files renamed to
  `ShowName (Year) - sXXeYY[-eZZ][ - Title].ext`.
- **Movie file renames** inside each movie folder
  (`MovieName (Year).ext`), matched on the largest video file so sample
  files and extras are ignored.
- **TMDb episode-title lookup** — when a TMDb API key is configured, real
  episode titles are fetched (and cached per season) to fill the
  `Optional Title` slot.
- **Tree-view preview** showing the full rename plan: each title expands
  into its season folders and episode files, with per-row checkboxes that
  cascade to children.
- **Conflict detection** — rows whose target name already exists on disk,
  or whose target collides with another planned rename, are flagged in
  red so you can resolve them before applying.
- **Episode count and total size** shown next to each TV show in the
  preview.
- **Batched undo** — every rename produced by a single Apply click is
  recorded as one batch, so a single Undo Last Rename reverses the
  entire operation (folder + season folders + every episode file).
- **`1x01`-style episode numbers** are now recognised in addition to
  `sXXeYY`, both for classification and number extraction.

### Changed
- Scanner now walks each title folder to collect season folders and
  episode files (or the primary movie file), instead of only the
  top-level folder.
- TV/movie classification is more accurate: explicit season folders,
  `Specials` folders, multi-file and single-file episode markers,
  `1x01`/`Episode N` patterns, and folder-name-only hints
  (e.g. `Show.S03`) all classify correctly.

### Fixed
- Multi-episode files (`s01e01-e02`) are now recognised and renamed
  correctly instead of crashing GuessIt on list-valued episode numbers.
- `pyproject.toml` build-backend corrected to `setuptools.build_meta`
  so `pip install -e .` works locally.

## [1.0.4] - 2026-06-07

### Added
- Debian/Ubuntu `.deb` package — install via `sudo apt install mediamatch` once
  the apt repository is configured, or download directly from the Releases page
- GitHub Pages apt repository (branch `apt`) updated automatically on each
  release via a new `apt-repo.yml` workflow
- Fixed hardcoded `1.0.0` version string in AppImage and tar.gz filenames —
  release artifacts now carry the correct version number

## [1.0.3] - 2026-06-07

### Added
- Linux uninstall script (`uninstall.sh`) bundled in the release tar.gz alongside
  `install.sh`; handles tar.gz, pip/source, and AppImage installs and removes all
  config data — run without arguments for a dry-run preview, pass `--yes` to
  actually remove everything

## [1.0.2] - 2026-06-07

### Fixed
- TV show folders are now correctly identified in many more cases: season
  directories beyond Season 3 (`S04`–`S99`), `1x01`-style episode filenames,
  `Episode N` naming, and folders containing only a single episode file (e.g.
  miniseries) were all previously misclassified as movies
- guessit now receives the scanner's media-type classification as a hint,
  preventing ambiguous folder names (no episode markers) from being parsed as
  movies
- TMDb search results for both movies and TV shows are now ranked by title
  similarity instead of returning the first year-match or `results[0]`,
  reducing wrong-match assignments; low-confidence TV matches emit a warning
  in the application log
## [1.0.0] - 2026-06-06

### Added
- Initial release
- Auto-detection of movies vs. TV shows from folder structure
- GuessIt-powered filename parsing
- Optional TMDb API enrichment with graceful offline fallback
- PySide6 GUI with diff-style preview table
- Dry-run mode (simulate renames without touching files)
- JSON-backed undo log with one-click undo
- Windows `.exe` installer (Inno Setup)
- macOS `.pkg` installer (pkgbuild/productbuild)
- Linux universal AppImage
- GitHub Actions matrix CI/CD for automated multi-platform builds
