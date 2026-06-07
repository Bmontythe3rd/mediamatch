"""Settings dialog for TMDb API key and preferences."""
from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QVBoxLayout, QCheckBox, QGroupBox,
)

from mediamatch.utils.helpers import settings_file


def load_settings() -> dict:
    path = settings_file()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_settings(data: dict):
    path = settings_file()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(460)
        self._settings = load_settings()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # TMDb group
        tmdb_group = QGroupBox("TMDb API (optional — improves accuracy)")
        form = QFormLayout(tmdb_group)

        self._api_key_edit = QLineEdit(self._settings.get("tmdb_api_key", ""))
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        self._api_key_edit.setPlaceholderText("Paste your TMDb API key here")
        form.addRow("API Key:", self._api_key_edit)

        hint = QLabel(
            '<a href="https://www.themoviedb.org/settings/api">Get a free TMDb API key →</a>'
        )
        hint.setOpenExternalLinks(True)
        hint.setTextFormat(Qt.RichText)
        form.addRow("", hint)

        layout.addWidget(tmdb_group)

        # Options group
        opts_group = QGroupBox("Rename options")
        opts_form = QFormLayout(opts_group)

        self._include_tmdb_id = QCheckBox("Append TMDb ID to folder name  (e.g. {tmdb-155})")
        self._include_tmdb_id.setChecked(self._settings.get("include_tmdb_id", True))
        opts_form.addRow(self._include_tmdb_id)

        self._dry_run = QCheckBox("Dry-run mode  (preview only, never rename files)")
        self._dry_run.setChecked(self._settings.get("dry_run", False))
        opts_form.addRow(self._dry_run)

        layout.addWidget(opts_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self):
        self._settings["tmdb_api_key"] = self._api_key_edit.text().strip()
        self._settings["include_tmdb_id"] = self._include_tmdb_id.isChecked()
        self._settings["dry_run"] = self._dry_run.isChecked()
        save_settings(self._settings)
        self.accept()

    @property
    def settings(self) -> dict:
        return self._settings
