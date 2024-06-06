# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio


import math
from types import FunctionType, MethodType
from pathlib import Path
from typing import Optional, cast, Callable

from PIL import Image, ImageQt
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPixmap, QEnterEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton


class FieldContainer(QWidget):
    # TODO: reference a resources folder rather than path.parents[3]?
    clipboard_icon_128: Image.Image = Image.open(
        str(Path(__file__).parents[3] / "resources/qt/images/clipboard_icon_128.png")
    ).resize((math.floor(24 * 1.25), math.floor(24 * 1.25)))
    clipboard_icon_128.load()

    edit_icon_128: Image.Image = Image.open(
        str(Path(__file__).parents[3] / "resources/qt/images/edit_icon_128.png")
    ).resize((math.floor(24 * 1.25), math.floor(24 * 1.25)))
    edit_icon_128.load()

    trash_icon_128: Image.Image = Image.open(
        str(Path(__file__).parents[3] / "resources/qt/images/trash_icon_128.png")
    ).resize((math.floor(24 * 1.25), math.floor(24 * 1.25)))
    trash_icon_128.load()

    def __init__(self, title: str = "Field", inline: bool = True) -> None:
        super().__init__()
        # self.mode:str = mode
        self.setObjectName("fieldContainer")
        # self.item = item
        self.title: str = title
        self.inline: bool = inline
        # self.editable:bool = editable
        self.copy_callback: FunctionType = None
        self.edit_callback: FunctionType = None
        self.remove_callback: Callable = None
        button_size = 24
        # self.setStyleSheet('border-style:solid;border-color:#1e1a33;border-radius:8px;border-width:2px;')

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setObjectName("baseLayout")
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        # self.setStyleSheet('background-color:red;')

        self.inner_layout = QVBoxLayout()
        self.inner_layout.setObjectName("innerLayout")
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(0)
        self.inner_container = QWidget()
        self.inner_container.setObjectName("innerContainer")
        self.inner_container.setLayout(self.inner_layout)
        self.root_layout.addWidget(self.inner_container)

        self.title_container = QWidget()
        # self.title_container.setStyleSheet('background:black;')
        self.title_layout = QHBoxLayout(self.title_container)
        self.title_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title_layout.setObjectName("fieldLayout")
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.title_layout.setSpacing(0)
        self.inner_layout.addWidget(self.title_container)

        self.title_widget = QLabel()
        self.title_widget.setMinimumHeight(button_size)
        self.title_widget.setObjectName("fieldTitle")
        self.title_widget.setWordWrap(True)
        self.title_widget.setStyleSheet("font-weight: bold; font-size: 14px;")
        # self.title_widget.setStyleSheet('background-color:orange;')
        self.title_widget.setText(title)
        # self.inner_layout.addWidget(self.title_widget)
        self.title_layout.addWidget(self.title_widget)

        self.title_layout.addStretch(2)

        self.copy_button = QPushButton()
        self.copy_button.setMinimumSize(button_size, button_size)
        self.copy_button.setMaximumSize(button_size, button_size)
        self.copy_button.setFlat(True)
        self.copy_button.setIcon(
            QPixmap.fromImage(ImageQt.ImageQt(self.clipboard_icon_128))
        )
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_layout.addWidget(self.copy_button)
        self.copy_button.setHidden(True)

        self.edit_button = QPushButton()
        self.edit_button.setMinimumSize(button_size, button_size)
        self.edit_button.setMaximumSize(button_size, button_size)
        self.edit_button.setFlat(True)
        self.edit_button.setIcon(QPixmap.fromImage(ImageQt.ImageQt(self.edit_icon_128)))
        self.edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_layout.addWidget(self.edit_button)
        self.edit_button.setHidden(True)

        self.remove_button = QPushButton()
        self.remove_button.setMinimumSize(button_size, button_size)
        self.remove_button.setMaximumSize(button_size, button_size)
        self.remove_button.setFlat(True)
        self.remove_button.setIcon(
            QPixmap.fromImage(ImageQt.ImageQt(self.trash_icon_128))
        )
        self.remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_layout.addWidget(self.remove_button)
        self.remove_button.setHidden(True)

        self.field_container = QWidget()
        self.field_container.setObjectName("fieldContainer")
        self.field_layout = QHBoxLayout()
        self.field_layout.setObjectName("fieldLayout")
        self.field_layout.setContentsMargins(0, 0, 0, 0)
        self.field_container.setLayout(self.field_layout)
        # self.field_container.setStyleSheet('background-color:#666600;')
        self.inner_layout.addWidget(self.field_container)

        # self.set_inner_widget(mode)

    def set_copy_callback(self, callback: Optional[MethodType]):
        try:
            self.copy_button.clicked.disconnect()
        except RuntimeError:
            pass

        self.copy_callback = callback
        self.copy_button.clicked.connect(callback)

    def set_edit_callback(self, callback: Optional[MethodType]):
        try:
            self.edit_button.clicked.disconnect()
        except RuntimeError:
            pass

        self.edit_callback = callback
        self.edit_button.clicked.connect(callback)

    def set_remove_callback(self, callback: Optional[Callable]):
        try:
            self.remove_button.clicked.disconnect()
        except RuntimeError:
            pass

        self.remove_callback = callback
        self.remove_button.clicked.connect(callback)

    def set_inner_widget(self, widget: "FieldWidget"):
        # widget.setStyleSheet('background-color:green;')
        # self.inner_container.dumpObjectTree()
        # logging.info('')
        if self.field_layout.itemAt(0):
            # logging.info(f'Removing {self.field_layout.itemAt(0)}')
            # self.field_layout.removeItem(self.field_layout.itemAt(0))
            self.field_layout.itemAt(0).widget().deleteLater()
        self.field_layout.addWidget(widget)

    def get_inner_widget(self) -> Optional["FieldWidget"]:
        if self.field_layout.itemAt(0):
            return cast(FieldWidget, self.field_layout.itemAt(0).widget())
        return None

    def set_title(self, title: str):
        self.title = title
        self.title_widget.setText(title)

    def set_inline(self, inline: bool):
        self.inline = inline

    # def set_editable(self, editable:bool):
    # 	self.editable = editable

    def enterEvent(self, event: QEnterEvent) -> None:
        # if self.field_layout.itemAt(1):
        # 	self.field_layout.itemAt(1).
        # NOTE: You could pass the hover event to the FieldWidget if needed.
        if self.copy_callback:
            self.copy_button.setHidden(False)
        if self.edit_callback:
            self.edit_button.setHidden(False)
        if self.remove_callback:
            self.remove_button.setHidden(False)
        return super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        if self.copy_callback:
            self.copy_button.setHidden(True)
        if self.edit_callback:
            self.edit_button.setHidden(True)
        if self.remove_callback:
            self.remove_button.setHidden(True)
        return super().leaveEvent(event)


class FieldWidget(QWidget):
    field = dict

    def __init__(self, title) -> None:
        super().__init__()
        # self.item = item
        self.title = title
