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

### Linux

Two packages are available on the [Releases page](https://github.com/Bmontythe3rd/mediamatch/releases):

| Package | Best for |
|---|---|
| `MediaMatch-x.x.x-x86_64.AppImage` | Ubuntu, Debian, Fedora, most distros |
| `MediaMatch-x.x.x-linux-x86_64.tar.gz` | Arch Linux, NixOS, or anywhere FUSE 2 is unavailable |

#### Option A — AppImage (Ubuntu / Debian / Fedora)

AppImages require **FUSE 2** (`libfuse2`). All other Qt dependencies, including `libxcb-cursor0`, are **bundled inside the AppImage** — no extra packages needed.

> **Important:** Do **not** run the AppImage with `sudo`. It must run as your normal user to access the display.

```bash
chmod +x MediaMatch-x.x.x-x86_64.AppImage
./MediaMatch-x.x.x-x86_64.AppImage
```

**Arch Linux — FUSE 2 fix:**
```bash
sudo pacman -S fuse2
./MediaMatch-x.x.x-x86_64.AppImage
```

**Ubuntu 22.04+:**
```bash
sudo apt install libfuse2
./MediaMatch-x.x.x-x86_64.AppImage
```

**Fedora:**
```bash
sudo dnf install fuse fuse-libs
./MediaMatch-x.x.x-x86_64.AppImage
```

**No-root workaround (any distro):** If you cannot install FUSE, extract and run directly:
```bash
./MediaMatch-x.x.x-x86_64.AppImage --appimage-extract
./squashfs-root/AppRun
```

---

#### Option B — tar.gz (Arch Linux / no FUSE required)

This is a plain directory bundle that runs without FUSE.

```bash
tar -xzf MediaMatch-x.x.x-linux-x86_64.tar.gz
cd MediaMatch
./MediaMatch          # run directly
# or install to ~/.local:
bash install.sh
```

After `install.sh`, launch with `mediamatch` from any terminal (requires `~/.local/bin` in your `PATH`).

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

## Uninstalling

### Linux

An uninstall script is included in the release tar.gz (`uninstall.sh`) and in the repo at `packaging/linux/uninstall.sh`. It handles all installation methods — tar.gz, pip/source, and AppImage — and also removes config data.

**Preview what will be removed (dry run, nothing is deleted):**
```bash
bash uninstall.sh
```

**Actually remove everything:**
```bash
bash uninstall.sh --yes
```

The script removes:
- `~/.local/lib/mediamatch/` — application files (tar.gz install)
- `~/.local/bin/mediamatch` and `~/.local/bin/mediamatch-gui` — launcher scripts
- `~/.local/share/applications/mediamatch.desktop` — desktop entry
- `~/.local/share/icons/hicolor/256x256/apps/mediamatch.png` — app icon
- `~/.local/lib/python*/site-packages/mediamatch*` — pip-installed package files
- Any `MediaMatch*.AppImage` found under your home directory
- Any `squashfs-root/` left over from a `--appimage-extract` run
- `~/.config/MediaMatch/` — settings and undo log

### Windows
Use **Add or Remove Programs** (or **Settings → Apps**) and search for *MediaMatch*.

### macOS
Drag **MediaMatch.app** from `/Applications` to the Trash. Config data can be removed with:
```bash
rm -rf ~/Library/Application\ Support/MediaMatch
```

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
