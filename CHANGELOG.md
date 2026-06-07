# Changelog

All notable changes to MediaMatch will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
