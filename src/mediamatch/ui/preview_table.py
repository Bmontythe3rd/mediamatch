"""Table widget showing current → proposed renames with type and status columns."""
from __future__ import annotations

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QTableView, QHeaderView, QAbstractItemView

from mediamatch.core.scanner import MediaItem, MediaType

COLUMNS = ["", "Current Name", "Proposed Name", "Type", "Status"]
COL_CHECK, COL_CURRENT, COL_PROPOSED, COL_TYPE, COL_STATUS = range(5)

_TYPE_LABELS = {MediaType.MOVIE: "Movie", MediaType.TV_SHOW: "TV Show", MediaType.UNKNOWN: "?"}
_GREEN = QColor("#2ecc71")
_ORANGE = QColor("#e67e22")
_RED = QColor("#e74c3c")
_GREY = QColor("#95a5a6")


class PreviewModel(QAbstractTableModel):
    check_changed = Signal()

    def __init__(self, items: list[MediaItem], parent=None):
        super().__init__(parent)
        self._items = items

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._items)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        col = index.column()

        if role == Qt.CheckStateRole and col == COL_CHECK:
            return Qt.Checked if item.enabled else Qt.Unchecked

        if role == Qt.DisplayRole:
            if col == COL_CURRENT:
                return item.original_name
            if col == COL_PROPOSED:
                return item.proposed_name or "—"
            if col == COL_TYPE:
                return _TYPE_LABELS.get(item.media_type, "?")
            if col == COL_STATUS:
                if item.error:
                    return f"Error: {item.error}"
                if not item.proposed_name:
                    return "Pending"
                if item.proposed_name == item.original_name:
                    return "Already correct"
                return "Ready"
            return None

        if role == Qt.ForegroundRole and col == COL_STATUS:
            if item.error:
                return _RED
            if not item.proposed_name:
                return _GREY
            if item.proposed_name == item.original_name:
                return _GREY
            return _GREEN

        if role == Qt.FontRole and col == COL_PROPOSED and item.needs_rename:
            f = QFont()
            f.setBold(True)
            return f

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == COL_CHECK:
            base |= Qt.ItemIsUserCheckable
        return base

    def setData(self, index: QModelIndex, value, role=Qt.EditRole) -> bool:
        if role == Qt.CheckStateRole and index.column() == COL_CHECK:
            self._items[index.row()].enabled = (value == Qt.Checked)
            self.dataChanged.emit(index, index, [role])
            self.check_changed.emit()
            return True
        return False

    def replace_items(self, items: list[MediaItem]):
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def update_row(self, row: int):
        self.dataChanged.emit(
            self.index(row, 0),
            self.index(row, len(COLUMNS) - 1),
        )

    @property
    def items(self) -> list[MediaItem]:
        return self._items

    def checked_count(self) -> int:
        return sum(1 for i in self._items if i.enabled and i.needs_rename)


class PreviewTable(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(COL_CHECK, QHeaderView.Fixed)
        self.setColumnWidth(COL_CHECK, 28)
        self.horizontalHeader().setSectionResizeMode(COL_CURRENT, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(COL_PROPOSED, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(COL_TYPE, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(COL_STATUS, QHeaderView.ResizeToContents)
        self.setShowGrid(False)
        self.setWordWrap(False)

    def set_items(self, items: list[MediaItem]):
        model = PreviewModel(items, self)
        self.setModel(model)
        return model
