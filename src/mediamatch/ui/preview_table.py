"""Tree-style preview of the full rename plan.

Top-level rows show each show/movie. TV-show rows expand to season-folder
rows, which expand to individual episode file rows. Movie rows expand to
their single video file row.

Each row has its own checkbox; toggling a parent cascades to its children.
Conflict rows (target already exists or two ops collide on the same name)
are highlighted in red.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QFont, QBrush
from PySide6.QtWidgets import QTreeView, QHeaderView, QAbstractItemView

from mediamatch.core.scanner import MediaItem, MediaType, RenameOp

COLUMNS = ["", "Current Name", "Proposed Name", "Type", "Status"]
COL_NAME, COL_CURRENT, COL_PROPOSED, COL_TYPE, COL_STATUS = range(5)

_TYPE_LABELS = {MediaType.MOVIE: "Movie", MediaType.TV_SHOW: "TV Show", MediaType.UNKNOWN: "?"}
_KIND_LABELS = {"folder": "Folder", "season": "Season", "file": "File"}

_GREEN = QColor("#2ecc71")
_ORANGE = QColor("#e67e22")
_RED = QColor("#e74c3c")
_GREY = QColor("#95a5a6")

# Roles for stashing model objects on items.
ROLE_ITEM = Qt.UserRole + 1
ROLE_OP = Qt.UserRole + 2


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} PB"


def _total_size(item: MediaItem) -> int:
    paths = []
    if item.movie_file:
        paths.append(item.movie_file.path)
    paths.extend(ep.path for ep in item.episodes)
    total = 0
    for p in paths:
        try:
            total += p.stat().st_size
        except OSError:
            pass
    return total


class PreviewModel(QStandardItemModel):
    check_changed = Signal()

    def __init__(self, items: list[MediaItem], parent=None):
        super().__init__(parent)
        self._items = items
        self.setHorizontalHeaderLabels(COLUMNS)
        self._building = True
        self._build()
        self._building = False

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build(self):
        root = self.invisibleRootItem()
        for item in self._items:
            self._add_item_row(root, item)

    def _add_item_row(self, parent: QStandardItem, item: MediaItem):
        check_item = QStandardItem()
        check_item.setCheckable(True)
        check_item.setCheckState(Qt.Checked if item.enabled else Qt.Unchecked)
        check_item.setData(item, ROLE_ITEM)

        current = QStandardItem(item.original_name)
        proposed = QStandardItem(item.proposed_name or "—")
        if item.needs_rename:
            f = QFont(); f.setBold(True)
            proposed.setFont(f)

        type_label = _TYPE_LABELS.get(item.media_type, "?")
        extras = []
        if item.episodes:
            extras.append(f"{len(item.episodes)} episode(s)")
        size = _total_size(item)
        if size:
            extras.append(_human_size(size))
        if extras:
            type_label = f"{type_label}  ·  {' · '.join(extras)}"
        type_col = QStandardItem(type_label)

        status_col = QStandardItem(self._status_text(item))
        status_col.setForeground(QBrush(self._status_color(item)))

        row = [check_item, current, proposed, type_col, status_col]
        for cell in row:
            cell.setEditable(False)
        check_item.setEditable(False)
        # Re-enable check-box editing only on the check column itself.
        check_item.setFlags(check_item.flags() | Qt.ItemIsUserCheckable)

        parent.appendRow(row)

        # Children: render the rename plan.
        plan = item.rename_plan
        if not plan:
            return
        if item.media_type == MediaType.TV_SHOW:
            self._add_tv_children(check_item, item, plan)
        else:
            self._add_flat_children(check_item, plan, skip_top_folder=True)

    def _add_tv_children(self, parent_check: QStandardItem, item: MediaItem, plan):
        # Group file ops by their season folder for nice nesting.
        # Season ops become parent rows; file ops become children of the
        # matching season op when one exists, otherwise hang off the top item.
        season_rows: dict[Path, QStandardItem] = {}
        for op in plan.ops:
            if op.kind == "folder":
                # Top folder rename is represented by the parent item row already.
                continue
            if op.kind == "season":
                row_check = self._add_op_row(parent_check, op)
                season_rows[op.src] = row_check
        for op in plan.ops:
            if op.kind != "file":
                continue
            # Find season parent: the file's parent dir.
            parent_dir = op.src.parent
            parent_row = season_rows.get(parent_dir, parent_check)
            self._add_op_row(parent_row, op)

    def _add_flat_children(self, parent_check: QStandardItem, plan, skip_top_folder: bool):
        for op in plan.ops:
            if skip_top_folder and op.kind == "folder":
                continue
            self._add_op_row(parent_check, op)

    def _add_op_row(self, parent: QStandardItem, op: RenameOp) -> QStandardItem:
        check_item = QStandardItem()
        check_item.setCheckable(True)
        check_item.setCheckState(Qt.Checked if op.enabled else Qt.Unchecked)
        check_item.setData(op, ROLE_OP)

        current = QStandardItem(op.src.name)
        proposed = QStandardItem(op.dst_name)
        if op.needs_rename:
            f = QFont(); f.setBold(True)
            proposed.setFont(f)
        kind = QStandardItem(_KIND_LABELS.get(op.kind, op.kind))
        status = QStandardItem(self._op_status_text(op))
        status.setForeground(QBrush(self._op_status_color(op)))

        row = [check_item, current, proposed, kind, status]
        for cell in row:
            cell.setEditable(False)
        check_item.setFlags(check_item.flags() | Qt.ItemIsUserCheckable)
        parent.appendRow(row)
        return check_item

    # ------------------------------------------------------------------
    # Status formatting
    # ------------------------------------------------------------------

    def _status_text(self, item: MediaItem) -> str:
        if item.error:
            return f"Error: {item.error}"
        plan = item.rename_plan
        if not plan or not plan.ops:
            return "Already correct"
        conflicts = sum(1 for o in plan.ops if o.conflict)
        pending = sum(1 for o in plan.ops if o.needs_rename and not o.conflict)
        if conflicts and pending:
            return f"{pending} ready · {conflicts} conflict(s)"
        if conflicts:
            return f"{conflicts} conflict(s)"
        if pending:
            return f"{pending} change(s) ready"
        return "Already correct"

    def _status_color(self, item: MediaItem) -> QColor:
        plan = item.rename_plan
        if item.error:
            return _RED
        if not plan or not any(o.needs_rename for o in plan.ops):
            return _GREY
        if any(o.conflict for o in plan.ops):
            return _ORANGE
        return _GREEN

    def _op_status_text(self, op: RenameOp) -> str:
        if op.conflict:
            return op.error or "Conflict"
        if op.error:
            return f"Error: {op.error}"
        if not op.needs_rename:
            return "Already correct"
        return "Ready"

    def _op_status_color(self, op: RenameOp) -> QColor:
        if op.conflict:
            return _RED
        if op.error:
            return _RED
        if not op.needs_rename:
            return _GREY
        return _GREEN

    # ------------------------------------------------------------------
    # Check-state cascading
    # ------------------------------------------------------------------

    def setData(self, index, value, role=Qt.EditRole) -> bool:
        result = super().setData(index, value, role)
        if not self._building and role == Qt.CheckStateRole and index.column() == COL_NAME:
            self._propagate_check(index, value)
            self.check_changed.emit()
        return result

    def _propagate_check(self, index, value):
        item = self.itemFromIndex(index)
        checked = (value == Qt.Checked) or (value == int(Qt.Checked))

        payload_item = item.data(ROLE_ITEM)
        payload_op = item.data(ROLE_OP)
        if payload_item is not None:
            payload_item.enabled = checked
        if payload_op is not None:
            payload_op.enabled = checked

        # Cascade to children.
        self._building = True
        try:
            for r in range(item.rowCount()):
                child = item.child(r, COL_NAME)
                if child is None:
                    continue
                child.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                child_op = child.data(ROLE_OP)
                if child_op is not None:
                    child_op.enabled = checked
                # Recurse one more level (season -> files)
                for rr in range(child.rowCount()):
                    grand = child.child(rr, COL_NAME)
                    if grand is None:
                        continue
                    grand.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                    grand_op = grand.data(ROLE_OP)
                    if grand_op is not None:
                        grand_op.enabled = checked
        finally:
            self._building = False

    # ------------------------------------------------------------------
    # Public helpers (kept for parity with the old PreviewTable API)
    # ------------------------------------------------------------------

    @property
    def items(self) -> list[MediaItem]:
        return self._items

    def checked_count(self) -> int:
        return sum(1 for i in self._items if i.enabled and i.needs_rename)

    def set_all_enabled(self, enabled: bool):
        for i in self._items:
            i.enabled = enabled
            if i.rename_plan:
                for op in i.rename_plan.ops:
                    op.enabled = enabled
        self._rebuild()
        self.check_changed.emit()

    def refresh_all(self):
        self._rebuild()

    def _rebuild(self):
        self.clear()
        self.setHorizontalHeaderLabels(COLUMNS)
        self._building = True
        try:
            self._build()
        finally:
            self._building = False


class PreviewTable(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setAnimated(False)
        self.setRootIsDecorated(True)
        self.setHeaderHidden(False)

    def set_items(self, items: list[MediaItem]) -> PreviewModel:
        model = PreviewModel(items, self)
        self.setModel(model)
        header = self.header()
        header.setSectionResizeMode(COL_NAME, QHeaderView.Fixed)
        self.setColumnWidth(COL_NAME, 36)
        header.setSectionResizeMode(COL_CURRENT, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_PROPOSED, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_TYPE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeToContents)
        self.expandAll()
        return model
