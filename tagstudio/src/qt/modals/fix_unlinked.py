# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio


import typing

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from src.core.library import Library
from src.qt.helpers.custom_runnable import CustomRunnable
from src.qt.helpers.function_iterator import FunctionIterator
from src.qt.modals.delete_unlinked import DeleteUnlinkedEntriesModal
from src.qt.modals.merge_dupe_entries import MergeDuplicateEntries
from src.qt.modals.relink_unlinked import RelinkUnlinkedEntries
from src.qt.widgets.progress import ProgressWidget

# Only import for type checking/autocompletion, will not be imported at runtime.
if typing.TYPE_CHECKING:
    from src.qt.ts_qt import QtDriver


class FixUnlinkedEntriesModal(QWidget):
    def __init__(self, library: "Library", driver: "QtDriver"):
        super().__init__()
        self.lib = library
        self.driver = driver
        self.missing_count = -1
        self.dupe_count = -1
        self.setWindowTitle("Fix Unlinked Entries")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumSize(400, 300)
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(6, 6, 6, 6)

        self.unlinked_desc_widget = QLabel()
        self.unlinked_desc_widget.setObjectName("unlinkedDescriptionLabel")
        self.unlinked_desc_widget.setWordWrap(True)
        self.unlinked_desc_widget.setStyleSheet("text-align:left;")
        self.unlinked_desc_widget.setText(
            """Each library entry is linked to a file in one of your directories. If a file linked to an entry is moved or deleted outside of TagStudio, it is then considered unlinked. Unlinked entries may be automatically relinked via searching your directories, manually relinked by the user, or deleted if desired."""
        )

        self.dupe_desc_widget = QLabel()
        self.dupe_desc_widget.setObjectName("dupeDescriptionLabel")
        self.dupe_desc_widget.setWordWrap(True)
        self.dupe_desc_widget.setStyleSheet("text-align:left;")
        self.dupe_desc_widget.setText(
            """Duplicate entries are defined as multiple entries which point to the same file on disk. Merging these will combine the tags and metadata from all duplicates into a single consolidated entry. These are not to be confused with "duplicate files", which are duplicates of your files themselves outside of TagStudio."""
        )

        self.missing_count_label = QLabel()
        self.missing_count_label.setObjectName("missingCountLabel")
        self.missing_count_label.setStyleSheet("font-weight:bold;" "font-size:14px;")
        self.missing_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.dupe_count_label = QLabel()
        self.dupe_count_label.setObjectName("dupeCountLabel")
        self.dupe_count_label.setStyleSheet("font-weight:bold;" "font-size:14px;")
        self.dupe_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.refresh_unlinked_button = QPushButton()
        self.refresh_unlinked_button.setText("&Refresh All")
        self.refresh_unlinked_button.clicked.connect(
            lambda: self.refresh_missing_files()
        )

        self.merge_class = MergeDuplicateEntries(self.lib, self.driver)
        self.relink_class = RelinkUnlinkedEntries(self.lib, self.driver)

        self.search_button = QPushButton()
        self.search_button.setText("&Search && Relink")
        self.relink_class.done.connect(
            lambda: self.refresh_and_repair_dupe_entries(self.merge_class)
        )
        self.search_button.clicked.connect(lambda: self.relink_class.repair_entries())

        self.refresh_dupe_button = QPushButton()
        self.refresh_dupe_button.setText("Refresh Duplicate Entries")
        self.refresh_dupe_button.clicked.connect(lambda: self.refresh_dupe_entries())

        self.merge_dupe_button = QPushButton()
        self.merge_dupe_button.setText("&Merge Duplicate Entries")
        self.merge_class.done.connect(lambda: self.set_dupe_count(-1))
        self.merge_class.done.connect(lambda: self.set_missing_count(-1))
        self.merge_class.done.connect(lambda: self.driver.filter_items())
        self.merge_dupe_button.clicked.connect(lambda: self.merge_class.merge_entries())

        self.manual_button = QPushButton()
        self.manual_button.setText("&Manual Relink")

        self.delete_button = QPushButton()
        self.delete_modal = DeleteUnlinkedEntriesModal(self.lib, self.driver)
        self.delete_modal.done.connect(
            lambda: self.set_missing_count(len(self.lib.missing_files))
        )
        self.delete_modal.done.connect(lambda: self.driver.update_thumbs())
        self.delete_button.setText("De&lete Unlinked Entries")
        self.delete_button.clicked.connect(lambda: self.delete_modal.show())

        self.button_container = QWidget()
        self.button_layout = QHBoxLayout(self.button_container)
        self.button_layout.setContentsMargins(6, 6, 6, 6)
        self.button_layout.addStretch(1)

        self.done_button = QPushButton()
        self.done_button.setText("&Done")
        self.done_button.setDefault(True)
        self.done_button.clicked.connect(self.hide)
        self.button_layout.addWidget(self.done_button)

        self.root_layout.addWidget(self.missing_count_label)
        self.root_layout.addWidget(self.unlinked_desc_widget)
        self.root_layout.addWidget(self.refresh_unlinked_button)
        self.root_layout.addWidget(self.search_button)
        self.manual_button.setHidden(True)
        self.root_layout.addWidget(self.manual_button)
        self.root_layout.addWidget(self.delete_button)
        self.root_layout.addStretch(1)
        self.root_layout.addWidget(self.dupe_count_label)
        self.root_layout.addWidget(self.dupe_desc_widget)
        self.root_layout.addWidget(self.refresh_dupe_button)
        self.root_layout.addWidget(self.merge_dupe_button)
        self.root_layout.addStretch(2)
        self.root_layout.addWidget(self.button_container)

        self.set_missing_count(self.missing_count)
        self.set_dupe_count(self.dupe_count)

    def refresh_missing_files(self):
        iterator = FunctionIterator(self.lib.refresh_missing_files)
        pw = ProgressWidget(
            window_title="Scanning Library",
            label_text="Scanning Library for Unlinked Entries...",
            cancel_button_text=None,
            minimum=0,
            maximum=len(self.lib.entries),
        )
        pw.show()
        iterator.value.connect(lambda v: pw.update_progress(v + 1))
        r = CustomRunnable(lambda: iterator.run())
        QThreadPool.globalInstance().start(r)
        r.done.connect(
            lambda: (
                pw.hide(),
                pw.deleteLater(),
                self.set_missing_count(len(self.lib.missing_files)),
                self.delete_modal.refresh_list(),
                self.refresh_dupe_entries(),
            )
        )

    def refresh_dupe_entries(self):
        iterator = FunctionIterator(self.lib.refresh_dupe_entries)
        pw = ProgressWidget(
            window_title="Scanning Library",
            label_text="Scanning Library for Duplicate Entries...",
            cancel_button_text=None,
            minimum=0,
            maximum=len(self.lib.entries),
        )
        pw.show()
        iterator.value.connect(lambda v: pw.update_progress(v + 1))
        r = CustomRunnable(lambda: iterator.run())
        QThreadPool.globalInstance().start(r)
        r.done.connect(
            lambda: (
                pw.hide(),
                pw.deleteLater(),
                self.set_dupe_count(len(self.lib.dupe_entries)),
            )
        )

    def refresh_and_repair_dupe_entries(self, merge_class: MergeDuplicateEntries):
        iterator = FunctionIterator(self.lib.refresh_dupe_entries)
        pw = ProgressWidget(
            window_title="Scanning Library",
            label_text="Scanning Library for Duplicate Entries...",
            cancel_button_text=None,
            minimum=0,
            maximum=len(self.lib.entries),
        )
        pw.show()
        iterator.value.connect(lambda v: pw.update_progress(v + 1))
        r = CustomRunnable(lambda: iterator.run())
        QThreadPool.globalInstance().start(r)
        r.done.connect(
            lambda: (
                pw.hide(),  # type: ignore
                pw.deleteLater(),  # type: ignore
                self.set_dupe_count(len(self.lib.dupe_entries)),
                merge_class.merge_entries(),
            )
        )

    def set_missing_count(self, count: int):
        self.missing_count = count
        if self.missing_count < 0:
            self.search_button.setDisabled(True)
            self.delete_button.setDisabled(True)
            self.missing_count_label.setText("Unlinked Entries: N/A")
        elif self.missing_count == 0:
            self.search_button.setDisabled(True)
            self.delete_button.setDisabled(True)
            self.missing_count_label.setText(f"Unlinked Entries: {count}")
        else:
            self.search_button.setDisabled(False)
            self.delete_button.setDisabled(False)
            self.missing_count_label.setText(f"Unlinked Entries: {count}")

    def set_dupe_count(self, count: int):
        self.dupe_count = count
        if self.dupe_count < 0:
            self.dupe_count_label.setText("Duplicate Entries: N/A")
            self.merge_dupe_button.setDisabled(True)
        elif self.dupe_count == 0:
            self.dupe_count_label.setText(f"Duplicate Entries: {count}")
            self.merge_dupe_button.setDisabled(True)
        else:
            self.dupe_count_label.setText(f"Duplicate Entries: {count}")
            self.merge_dupe_button.setDisabled(False)
