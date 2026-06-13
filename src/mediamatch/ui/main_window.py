"""Main application window."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QFileDialog,
    QProgressBar, QStatusBar, QToolBar, QMessageBox,
    QCheckBox, QSplitter, QTextEdit, QSizePolicy,
)

from mediamatch import __app_name__, __version__
from mediamatch.core.scanner import scan_directory, MediaItem
from mediamatch.core.renamer import propose_name, apply_plan
from mediamatch.core.tmdb import TMDbClient
from mediamatch.core import undo
from mediamatch.ui.preview_table import PreviewTable
from mediamatch.ui.settings_dialog import SettingsDialog, load_settings
from mediamatch.utils.helpers import resource_path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------

class ScanWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, root: Path, tmdb_client: TMDbClient, include_tmdb_id: bool):
        super().__init__()
        self.root = root
        self.tmdb_client = tmdb_client
        self.include_tmdb_id = include_tmdb_id

    def run(self):
        try:
            items = scan_directory(self.root, self.progress.emit)
            total = len(items)
            enriched = []
            for i, item in enumerate(items):
                self.progress.emit(i + 1, total, f"Looking up: {item.original_name}")
                item = propose_name(item, self.tmdb_client)
                if not self.include_tmdb_id:
                    item.tmdb_id = None
                    # Re-propose without ID
                    item = propose_name(item, None)
                enriched.append(item)
            self.finished.emit(enriched)
        except Exception as exc:
            self.error.emit(str(exc))


class RenameWorker(QObject):
    progress = Signal(int, int, str)
    item_done = Signal(int, bool)
    finished = Signal(int, int, int)  # ops_succeeded, ops_failed, items_touched

    def __init__(self, items: list[MediaItem], dry_run: bool):
        super().__init__()
        self.items = items
        self.dry_run = dry_run

    def run(self):
        enabled = [(i, item) for i, item in enumerate(self.items) if item.enabled and item.needs_rename]
        ops_ok = 0
        ops_fail = 0
        batch: list[tuple[Path, Path]] = []
        for count, (idx, item) in enumerate(enabled):
            self.progress.emit(count + 1, len(enabled), item.original_name)
            successes, failures = apply_plan(item, dry_run=self.dry_run)
            ops_ok += len(successes)
            ops_fail += len(failures)
            if not self.dry_run:
                batch.extend(successes)
            self.item_done.emit(idx, len(failures) == 0)
        if batch:
            undo.record_batch(batch)
        self.finished.emit(ops_ok, ops_fail, len(enabled))


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._settings = load_settings()
        self._tmdb = TMDbClient(self._settings.get("tmdb_api_key", ""))
        self._items: list[MediaItem] = []
        self._model = None
        self._thread: QThread | None = None

        self.setWindowTitle(f"{__app_name__} {__version__}")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        icon_path = resource_path("assets/icon.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()
        self._build_menu()
        self._update_button_states()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 8)
        root_layout.setSpacing(8)

        # Folder picker row
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Media folder:"))
        self._folder_edit = QLineEdit()
        self._folder_edit.setPlaceholderText("Select a folder containing your media…")
        self._folder_edit.setReadOnly(True)
        folder_row.addWidget(self._folder_edit, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse_btn)
        root_layout.addLayout(folder_row)

        # Options row
        opts_row = QHBoxLayout()
        self._tmdb_checkbox = QCheckBox("Use TMDb lookup")
        self._tmdb_checkbox.setChecked(bool(self._settings.get("tmdb_api_key")))
        self._tmdb_checkbox.setEnabled(bool(self._settings.get("tmdb_api_key")))
        opts_row.addWidget(self._tmdb_checkbox)

        self._dry_run_checkbox = QCheckBox("Dry run (preview only)")
        self._dry_run_checkbox.setChecked(self._settings.get("dry_run", False))
        opts_row.addWidget(self._dry_run_checkbox)

        opts_row.addStretch()

        self._scan_btn = QPushButton("Scan Folder")
        self._scan_btn.setFixedWidth(120)
        self._scan_btn.clicked.connect(self._start_scan)
        opts_row.addWidget(self._scan_btn)
        root_layout.addLayout(opts_row)

        # Preview table
        self._table = PreviewTable()
        root_layout.addWidget(self._table, 1)

        # Bottom action row
        action_row = QHBoxLayout()
        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.clicked.connect(self._select_all)
        action_row.addWidget(self._select_all_btn)

        self._deselect_all_btn = QPushButton("Deselect All")
        self._deselect_all_btn.clicked.connect(self._deselect_all)
        action_row.addWidget(self._deselect_all_btn)

        action_row.addStretch()

        self._undo_btn = QPushButton("Undo Last Rename")
        self._undo_btn.clicked.connect(self._undo_last)
        action_row.addWidget(self._undo_btn)

        self._apply_btn = QPushButton("Apply Renames")
        self._apply_btn.setFixedWidth(140)
        self._apply_btn.clicked.connect(self._apply_renames)
        font = self._apply_btn.font()
        font.setBold(True)
        self._apply_btn.setFont(font)
        action_row.addWidget(self._apply_btn)
        root_layout.addLayout(action_row)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setTextVisible(True)
        root_layout.addWidget(self._progress)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready — select a folder to begin.")

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        open_action = QAction("Open Folder…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._browse_folder)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        edit_menu = menubar.addMenu("Edit")
        settings_action = QAction("Settings…", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._open_settings)
        edit_menu.addAction(settings_action)

        help_menu = menubar.addMenu("Help")
        about_action = QAction("About MediaMatch", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Media Folder")
        if folder:
            self._folder_edit.setText(folder)
            self._items = []
            self._model = None
            self._update_button_states()

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._settings = dlg.settings
            api_key = self._settings.get("tmdb_api_key", "")
            self._tmdb.set_api_key(api_key)
            self._tmdb_checkbox.setEnabled(bool(api_key))
            self._tmdb_checkbox.setChecked(bool(api_key))
            self._dry_run_checkbox.setChecked(self._settings.get("dry_run", False))

    def _start_scan(self):
        folder = self._folder_edit.text().strip()
        if not folder:
            QMessageBox.warning(self, "No Folder", "Please select a media folder first.")
            return

        tmdb_client = self._tmdb if (self._tmdb_checkbox.isChecked() and self._tmdb.available) else None
        include_id = self._settings.get("include_tmdb_id", True)

        self._set_busy(True)
        self._status_bar.showMessage("Scanning…")
        self._progress.setValue(0)
        self._progress.setVisible(True)

        worker = ScanWorker(Path(folder), tmdb_client or TMDbClient(), include_id)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_scan_progress)
        worker.finished.connect(self._on_scan_finished)
        worker.error.connect(self._on_scan_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_scan_progress(self, current: int, total: int, name: str):
        if total:
            pct = int(current / total * 100)
            self._progress.setValue(pct)
        self._status_bar.showMessage(f"Processing ({current}/{total}): {name}")

    def _on_scan_finished(self, items: list[MediaItem]):
        self._items = items
        self._model = self._table.set_items(items)
        self._model.check_changed.connect(self._update_button_states)
        self._set_busy(False)
        self._progress.setVisible(False)
        needs = sum(1 for i in items if i.needs_rename)
        self._status_bar.showMessage(
            f"Found {len(items)} media item(s) — {needs} need renaming."
        )
        self._update_button_states()

    def _on_scan_error(self, msg: str):
        self._set_busy(False)
        self._progress.setVisible(False)
        QMessageBox.critical(self, "Scan Error", msg)
        self._status_bar.showMessage("Scan failed.")

    def _apply_renames(self):
        if not self._model:
            return
        count = self._model.checked_count()
        if count == 0:
            QMessageBox.information(self, "Nothing to Rename", "No items are selected for renaming.")
            return

        dry = self._dry_run_checkbox.isChecked()
        label = "dry-run preview" if dry else "rename"
        reply = QMessageBox.question(
            self, "Confirm",
            f"{'Simulate' if dry else 'Rename'} {count} item(s)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._set_busy(True)
        self._progress.setValue(0)
        self._progress.setVisible(True)

        worker = RenameWorker(self._items, dry)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(lambda c, t, n: (
            self._progress.setValue(int(c / t * 100)) if t else None,
            self._status_bar.showMessage(f"Renaming ({c}/{t}): {n}"),
        ))
        worker.item_done.connect(lambda row, ok: self._model and self._model.refresh_all())
        worker.finished.connect(self._on_rename_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_rename_finished(self, ops_ok: int, ops_fail: int, items: int):
        self._set_busy(False)
        self._progress.setVisible(False)
        dry = self._dry_run_checkbox.isChecked()
        verb = "Would rename" if dry else "Renamed"
        msg = f"{verb} {ops_ok} path(s) across {items} title(s)."
        if ops_fail:
            msg += f" {ops_fail} failed."
        self._status_bar.showMessage(msg)
        QMessageBox.information(self, "Complete", msg)
        self._update_button_states()

    def _select_all(self):
        if self._model:
            self._model.set_all_enabled(True)
            self._update_button_states()

    def _deselect_all(self):
        if self._model:
            self._model.set_all_enabled(False)
            self._update_button_states()

    def _undo_last(self):
        ok, msg = undo.undo_last()
        QMessageBox.information(self, "Undo", msg)
        if ok:
            self._status_bar.showMessage(msg)

    def _show_about(self):
        QMessageBox.about(
            self, f"About {__app_name__}",
            f"<b>{__app_name__} {__version__}</b><br><br>"
            "Rename your media folders to Plex/Jellyfin naming conventions.<br><br>"
            "Uses <a href='https://guessit.readthedocs.io/'>GuessIt</a> for filename parsing "
            "and optionally <a href='https://www.themoviedb.org/'>TMDb</a> for metadata enrichment.<br><br>"
            "MIT License",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_busy(self, busy: bool):
        self._scan_btn.setEnabled(not busy)
        self._apply_btn.setEnabled(not busy)

    def _update_button_states(self):
        has_items = bool(self._items)
        has_pending = self._model.checked_count() > 0 if self._model else False
        self._select_all_btn.setEnabled(has_items)
        self._deselect_all_btn.setEnabled(has_items)
        self._apply_btn.setEnabled(has_pending)
