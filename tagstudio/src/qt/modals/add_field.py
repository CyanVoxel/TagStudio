# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio


from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
)

from src.core.library import Library


class AddFieldModal(QWidget):
    done = Signal(int)

    def __init__(self, library: "Library"):
        # [Done]
        # - OR -
        # [Cancel] [Save]
        super().__init__()
        self.lib = library
        self.setWindowTitle("Add Field")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumSize(400, 300)
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(6, 6, 6, 6)

        self.title_widget = QLabel()
        self.title_widget.setObjectName("fieldTitle")
        self.title_widget.setWordWrap(True)
        self.title_widget.setStyleSheet(
            # 'background:blue;'
            # 'text-align:center;'
            "font-weight:bold;" "font-size:14px;" "padding-top: 6px" ""
        )
        self.title_widget.setText("Add Field")
        self.title_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.combo_box = QComboBox()
        self.combo_box.setEditable(False)
        # self.combo_box.setMaxVisibleItems(5)
        self.combo_box.setStyleSheet("combobox-popup:0;")
        self.combo_box.view().setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        for df in self.lib.default_fields:
            self.combo_box.addItem(
                f'{df["name"]} ({df["type"].replace("_", " ").title()})'
            )

        self.button_container = QWidget()
        self.button_layout = QHBoxLayout(self.button_container)
        self.button_layout.setContentsMargins(6, 6, 6, 6)
        self.button_layout.addStretch(1)

        # self.cancel_button = QPushButton()
        # self.cancel_button.setText('Cancel')

        self.cancel_button = QPushButton()
        self.cancel_button.setText("Cancel")
        self.cancel_button.clicked.connect(self.hide)
        # self.cancel_button.clicked.connect(widget.reset)
        self.button_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton()
        self.save_button.setText("Add")
        # self.save_button.setAutoDefault(True)
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.hide)
        self.save_button.clicked.connect(
            lambda: self.done.emit(self.combo_box.currentIndex())
        )
        # self.save_button.clicked.connect(lambda: save_callback(widget.get_content()))
        self.button_layout.addWidget(self.save_button)

        # self.returnPressed.connect(lambda: self.done.emit(self.combo_box.currentIndex()))

        # self.done.connect(lambda x: callback(x))

        self.root_layout.addWidget(self.title_widget)
        self.root_layout.addWidget(self.combo_box)
        # self.root_layout.setStretch(1,2)
        self.root_layout.addStretch(1)
        self.root_layout.addWidget(self.button_container)
