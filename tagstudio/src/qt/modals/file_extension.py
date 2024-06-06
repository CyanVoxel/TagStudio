# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio


from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QStyledItemDelegate,
    QLineEdit,
)

from src.core.library import Library
from src.qt.widgets.panel import PanelWidget


class FileExtensionItemDelegate(QStyledItemDelegate):
    def setModelData(self, editor, model, index):
        if isinstance(editor, QLineEdit):
            if editor.text() and not editor.text().startswith("."):
                editor.setText(f".{editor.text()}")
        super().setModelData(editor, model, index)


class FileExtensionModal(PanelWidget):
    done = Signal()

    def __init__(self, library: "Library"):
        super().__init__()
        self.lib = library
        self.setWindowTitle("File Extensions")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumSize(200, 400)
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(6, 6, 6, 6)

        self.table = QTableWidget(len(self.lib.ignored_extensions), 1)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setItemDelegate(FileExtensionItemDelegate())

        self.add_button = QPushButton()
        self.add_button.setText("&Add Extension")
        self.add_button.clicked.connect(self.add_item)
        self.add_button.setDefault(True)
        self.add_button.setMinimumWidth(100)

        self.root_layout.addWidget(self.table)
        self.root_layout.addWidget(
            self.add_button, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.refresh_list()

    def refresh_list(self):
        for i, ext in enumerate(self.lib.ignored_extensions):
            self.table.setItem(i, 0, QTableWidgetItem(ext))

    def add_item(self):
        self.table.insertRow(self.table.rowCount())

    def save(self):
        self.lib.ignored_extensions.clear()
        for i in range(self.table.rowCount()):
            ext = self.table.item(i, 0)
            if ext and ext.text():
                self.lib.ignored_extensions.append(ext.text())
