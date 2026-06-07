# MediaMatch

[![Build & Release](https://github.com/Bmontythe3rd/mediamatch/actions/workflows/build.yml/badge.svg)](https://github.com/Bmontythe3rd/mediamatch/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

**MediaMatch** automatically renames your media folders to the naming conventions expected by [Plex](https://www.plex.tv/) and [Jellyfin](https://jellyfin.org/). Point it at a folder full of movies or TV shows, preview the proposed renames, and apply in one click.

---

## Features

- **Auto-detects** movies vs. TV shows from folder structure and filenames
- **Smart parsing** via [GuessIt](https://guessit.readthedocs.io/) — handles virtually any naming chaos
- **Optional TMDb enrichment** — confirms titles, years, and appends `{tmdb-ID}` for perfect library matching
- **Preview before rename** — a diff-style table shows current → proposed names before anything changes
- **Dry-run mode** — simulate all renames without touching a single file
- **Undo** — every rename is logged; undo the last batch in one click
- **Cross-platform** — identical experience on Windows, macOS, and Linux

---

## Installation

### Windows
Download `MediaMatch-x.x.x-Setup.exe` from the [Releases page](https://github.com/Bmontythe3rd/mediamatch/releases) and run the installer.

### macOS
Download `MediaMatch-x.x.x.pkg` from the [Releases page](https://github.com/Bmontythe3rd/mediamatch/releases) and open it. You may need to allow it in **System Settings → Privacy & Security** on first run.

### Linux (any distro)
Download `MediaMatch-x.x.x-x86_64.AppImage` from the [Releases page](https://github.com/Bmontythe3rd/mediamatch/releases), make it executable, and run:

```bash
chmod +x MediaMatch-x.x.x-x86_64.AppImage
./MediaMatch-x.x.x-x86_64.AppImage
```

No installation required — AppImages are self-contained.

### From source (any platform)

> **Note:** Modern Linux distros and macOS expose Python 3 as `python3`/`pip3`.
> Use `python3 -m pip` if the `pip` command is not found.

```bash
git clone https://github.com/Bmontythe3rd/mediamatch.git
cd mediamatch
python3 -m pip install -e .
python3 -m mediamatch.main
```

If `python3 -m mediamatch.main` works but the `mediamatch-gui` command isn't
found, your `pip` scripts directory (`~/.local/bin` on Linux/macOS) is not on
your `PATH`. Either add it:

```bash
# Add to ~/.bashrc or ~/.zshrc, then restart your shell
export PATH="$HOME/.local/bin:$PATH"
```

Or just always launch with `python3 -m mediamatch.main`.

---

## Usage

1. **Open MediaMatch.**
2. Click **Browse…** and select the root folder containing your media (e.g. `/mnt/media/Movies`).
3. *(Optional)* Enable **Use TMDb lookup** for best results — see [Getting a TMDb API Key](#getting-a-tmdb-api-key).
4. Click **Scan Folder**. MediaMatch will analyze all subfolders and propose new names.
5. Review the table:
   - **Current Name** — the folder name as it is now
   - **Proposed Name** — the Plex/Jellyfin-compliant target name (bold = will be renamed)
   - **Type** — Movie or TV Show
   - **Status** — Ready / Already correct / Error
6. Uncheck any items you want to skip.
7. Click **Apply Renames**. Confirm in the dialog.

### Dry-run mode
Enable **Dry run (preview only)** in the toolbar or **Settings** to simulate all renames without writing anything to disk. The table will show what *would* happen.

### Undo
Click **Undo Last Rename** (or press `Ctrl+Z`) to reverse the most recent rename operation. The undo log is stored at:
- **Windows:** `%APPDATA%\MediaMatch\undo_log.json`
- **macOS:** `~/Library/Application Support/MediaMatch/undo_log.json`
- **Linux:** `~/.config/MediaMatch/undo_log.json`

---

## Naming Conventions

MediaMatch outputs names that are fully compatible with both Plex and Jellyfin:

### Movies
```
Movie Title (Year)/
Movie Title (Year) {tmdb-12345}/   ← with TMDb ID enabled
```

### TV Shows
```
Show Name (Year)/
Show Name (Year) {tmdb-67890}/     ← with TMDb ID enabled
  └── Season 01/
       └── Show Name - S01E01 - Episode Title.mkv
```

> **Note:** MediaMatch renames the *top-level folder* for each title. Season folder renaming and episode file renaming are planned for a future release.

---

## Getting a TMDb API Key

TMDb is the same metadata source Plex and Jellyfin use internally. A free API key takes about 60 seconds to obtain:

1. Create a free account at [themoviedb.org](https://www.themoviedb.org/)
2. Go to **Settings → API → Create → Developer**
3. Fill in the short form (app name: "MediaMatch", personal use)
4. Copy your **API Key (v3 auth)**
5. In MediaMatch, open **Edit → Settings** and paste the key

MediaMatch works without a key (using GuessIt parsing only), but TMDb lookup provides significantly better accuracy — especially for titles with unusual spacing, punctuation, or foreign characters.

---

## Building from Source

### Requirements
- Python 3.10+
- Git

```bash
git clone https://github.com/Bmontythe3rd/mediamatch.git
cd mediamatch
python3 -m pip install -r requirements-dev.txt
```

### Run in dev mode
```bash
python3 src/mediamatch/main.py
```

### Build platform installer locally
```bash
# Build the PyInstaller bundle first (run on your target OS):
pyinstaller mediamatch.spec --clean

# Windows — requires Inno Setup installed:
iscc packaging/windows/installer.iss

# macOS:
bash packaging/macos/build_pkg.sh

# Linux — requires appimagetool:
# (see .github/workflows/build.yml for the full steps)
```

---

## CI/CD

Pushing a version tag triggers a full matrix build across all three platforms via GitHub Actions:

```bash
git tag v1.0.1
git push origin v1.0.1
```

The workflow builds the Windows `.exe` installer, macOS `.pkg`, and Linux `.AppImage`, then automatically attaches them to a GitHub Release.

See [`.github/workflows/build.yml`](.github/workflows/build.yml) for details.

---

## Project Structure

```
mediamatch/
├── src/mediamatch/
│   ├── core/
│   │   ├── scanner.py       # Folder walking & media detection
│   │   ├── parser.py        # GuessIt wrapper
│   │   ├── tmdb.py          # TMDb API client
│   │   ├── renamer.py       # Name generation & filesystem renames
│   │   └── undo.py          # JSON-backed undo log
│   ├── ui/
│   │   ├── main_window.py   # Main PySide6 window
│   │   ├── preview_table.py # Diff-style rename preview table
│   │   └── settings_dialog.py
│   └── utils/
│       └── helpers.py       # Paths, resource resolution
├── assets/                  # App icons (.svg/.png/.ico/.icns)
├── packaging/
│   ├── windows/installer.iss
│   ├── macos/build_pkg.sh
│   └── linux/AppImageBuilder.yml
├── .github/workflows/build.yml
├── mediamatch.spec          # PyInstaller spec
├── pyproject.toml
└── requirements.txt
```

---

## Contributing

Pull requests are welcome! Please:

1. Fork the repo and create a feature branch
2. Keep changes focused — one feature or fix per PR
3. Add or update tests in `tests/` if applicable
4. Run `pytest` before submitting

For large changes, open an issue first to discuss the approach.

---

## License

[MIT](LICENSE) © Bryan Montgomery
