# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio


from time import sleep
import typing

from PySide6.QtCore import Signal, Qt, QThreadPool
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListView,
)

from src.core.library import Library
from src.qt.helpers.function_iterator import FunctionIterator
from src.qt.helpers.custom_runnable import CustomRunnable
from src.qt.widgets.progress import ProgressWidget

# Only import for type checking/autocompletion, will not be imported at runtime.
if typing.TYPE_CHECKING:
    from src.qt.ts_qt import QtDriver


class MirrorEntriesModal(QWidget):
    done = Signal()

    def __init__(self, library: "Library", driver: "QtDriver"):
        super().__init__()
        self.lib = library
        self.driver = driver
        self.setWindowTitle("Mirror Entries")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumSize(500, 400)
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(6, 6, 6, 6)

        self.desc_widget = QLabel()
        self.desc_widget.setObjectName("descriptionLabel")
        self.desc_widget.setWordWrap(True)
        self.desc_widget.setText(f"""
		Are you sure you want to mirror the following {len(self.lib.dupe_files)} Entries?
		""")
        self.desc_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.list_view = QListView()
        self.model = QStandardItemModel()
        self.list_view.setModel(self.model)

        self.button_container = QWidget()
        self.button_layout = QHBoxLayout(self.button_container)
        self.button_layout.setContentsMargins(6, 6, 6, 6)
        self.button_layout.addStretch(1)

        self.cancel_button = QPushButton()
        self.cancel_button.setText("&Cancel")
        self.cancel_button.setDefault(True)
        self.cancel_button.clicked.connect(self.hide)
        self.button_layout.addWidget(self.cancel_button)

        self.mirror_button = QPushButton()
        self.mirror_button.setText("&Mirror")
        self.mirror_button.clicked.connect(self.hide)
        self.mirror_button.clicked.connect(lambda: self.mirror_entries())
        self.button_layout.addWidget(self.mirror_button)

        self.root_layout.addWidget(self.desc_widget)
        self.root_layout.addWidget(self.list_view)
        self.root_layout.addWidget(self.button_container)

    def refresh_list(self):
        self.desc_widget.setText(f"""
		Are you sure you want to mirror the following {len(self.lib.dupe_files)} Entries?
		""")

        self.model.clear()
        for i in self.lib.dupe_files:
            self.model.appendRow(QStandardItem(str(i)))

    def mirror_entries(self):
        # pb = QProgressDialog('', None, 0, len(self.lib.dupe_files))
        # # pb.setMaximum(len(self.lib.missing_files))
        # pb.setFixedSize(432, 112)
        # pb.setWindowFlags(pb.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        # pb.setWindowTitle('Mirroring Entries')
        # pb.setWindowModality(Qt.WindowModality.ApplicationModal)
        # pb.show()

        # r = CustomRunnable(lambda: self.mirror_entries_runnable(pb))
        # r.done.connect(lambda: self.done.emit())
        # r.done.connect(lambda: self.driver.preview_panel.refresh())
        # # r.done.connect(lambda: self.model.clear())
        # # QThreadPool.globalInstance().start(r)
        # r.run()

        iterator = FunctionIterator(self.mirror_entries_runnable)
        pw = ProgressWidget(
            window_title="Mirroring Entries",
            label_text=f"Mirroring 1/{len(self.lib.dupe_files)} Entries...",
            cancel_button_text=None,
            minimum=0,
            maximum=len(self.lib.dupe_files),
        )
        pw.show()
        iterator.value.connect(lambda x: pw.update_progress(x + 1))
        iterator.value.connect(
            lambda x: pw.update_label(
                f"Mirroring {x+1}/{len(self.lib.dupe_files)} Entries..."
            )
        )
        r = CustomRunnable(lambda: iterator.run())
        QThreadPool.globalInstance().start(r)
        r.done.connect(
            lambda: (
                pw.hide(),
                pw.deleteLater(),
                self.driver.preview_panel.update_widgets(),
                self.done.emit(),
            )
        )

    def mirror_entries_runnable(self):
        mirrored: list = []
        for i, dupe in enumerate(self.lib.dupe_files):
            # pb.setValue(i)
            # pb.setLabelText(f'Mirroring {i}/{len(self.lib.dupe_files)} Entries')
            entry_id_1 = self.lib.get_entry_id_from_filepath(dupe[0])
            entry_id_2 = self.lib.get_entry_id_from_filepath(dupe[1])
            self.lib.mirror_entry_fields([entry_id_1, entry_id_2])
            sleep(0.005)
            yield i
        for d in mirrored:
            self.lib.dupe_files.remove(d)
        # self.driver.filter_items('')
        # self.done.emit()
