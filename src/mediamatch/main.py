"""Application entry point."""
from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from mediamatch import __app_name__
from mediamatch.ui.main_window import MainWindow


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setOrganizationName("MediaMatch")

    # Slightly larger default font for readability
    font = app.font()
    font.setPointSize(max(font.pointSize(), 10))
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
