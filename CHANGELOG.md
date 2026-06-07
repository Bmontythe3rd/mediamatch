# Changelog

All notable changes to MediaMatch will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
