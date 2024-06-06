# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio


import math

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from src.core.library import Library
from src.core.palette import ColorType, get_tag_color
from src.qt.widgets.panel import PanelWidget
from src.qt.widgets.tag import TagWidget


class TagSearchPanel(PanelWidget):
    tag_chosen = Signal(int)

    def __init__(self, library):
        super().__init__()
        self.lib: Library = library
        # self.callback = callback
        self.first_tag_id = None
        self.tag_limit = 30
        # self.selected_tag: int = 0
        self.setMinimumSize(300, 400)
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(6, 0, 6, 0)

        self.search_field = QLineEdit()
        self.search_field.setObjectName("searchField")
        self.search_field.setMinimumSize(QSize(0, 32))
        self.search_field.setPlaceholderText("Search Tags")
        self.search_field.textEdited.connect(
            lambda x=self.search_field.text(): self.update_tags(x)
        )
        self.search_field.returnPressed.connect(
            lambda checked=False: self.on_return(self.search_field.text())
        )

        # self.content_container = QWidget()
        # self.content_layout = QHBoxLayout(self.content_container)

        self.scroll_contents = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_contents)
        self.scroll_layout.setContentsMargins(6, 0, 6, 0)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area = QScrollArea()
        # self.scroll_area.setStyleSheet('background: #000000;')
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        # self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShadow(QFrame.Shadow.Plain)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        # sa.setMaximumWidth(self.preview_size[0])
        self.scroll_area.setWidget(self.scroll_contents)

        # self.add_button = QPushButton()
        # self.root_layout.addWidget(self.add_button)
        # self.add_button.setText('Add Tag')
        # # self.done_button.clicked.connect(lambda checked=False, x=1101: (callback(x), self.hide()))
        # self.add_button.clicked.connect(lambda checked=False, x=1101: callback(x))
        # # self.setLayout(self.root_layout)

        self.root_layout.addWidget(self.search_field)
        self.root_layout.addWidget(self.scroll_area)

    # def reset(self):
    # 	self.search_field.setText('')
    # 	self.update_tags('')
    # 	self.search_field.setFocus()

    def on_return(self, text: str):
        if text and self.first_tag_id is not None:
            # callback(self.first_tag_id)
            self.tag_chosen.emit(self.first_tag_id)
            self.search_field.setText("")
            self.update_tags()
        else:
            self.search_field.setFocus()
            self.parentWidget().hide()

    def update_tags(self, query: str = ""):
        # for c in self.scroll_layout.children():
        # 	c.widget().deleteLater()
        while self.scroll_layout.count():
            # logging.info(f"I'm deleting { self.scroll_layout.itemAt(0).widget()}")
            self.scroll_layout.takeAt(0).widget().deleteLater()

        found_tags = self.lib.search_tags(query, include_cluster=True)[
            : self.tag_limit - 1
        ]
        self.first_tag_id = found_tags[0] if found_tags else None

        for tag_id in found_tags:
            c = QWidget()
            layout = QHBoxLayout(c)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(3)
            tw = TagWidget(self.lib, self.lib.get_tag(tag_id), False, False)
            ab = QPushButton()
            ab.setMinimumSize(23, 23)
            ab.setMaximumSize(23, 23)
            ab.setText("+")
            ab.setStyleSheet(
                f"QPushButton{{"
                f"background: {get_tag_color(ColorType.PRIMARY, self.lib.get_tag(tag_id).color)};"
                # f'background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {get_tag_color(ColorType.PRIMARY, tag.color)}, stop:1.0 {get_tag_color(ColorType.BORDER, tag.color)});'
                # f"border-color:{get_tag_color(ColorType.PRIMARY, tag.color)};"
                f"color: {get_tag_color(ColorType.TEXT, self.lib.get_tag(tag_id).color)};"
                f"font-weight: 600;"
                f"border-color:{get_tag_color(ColorType.BORDER, self.lib.get_tag(tag_id).color)};"
                f"border-radius: 6px;"
                f"border-style:solid;"
                f"border-width: {math.ceil(1*self.devicePixelRatio())}px;"
                # f'padding-top: 1.5px;'
                # f'padding-right: 4px;'
                f"padding-bottom: 5px;"
                # f'padding-left: 4px;'
                f"font-size: 20px;"
                f"}}"
                f"QPushButton::hover"
                f"{{"
                f"border-color:{get_tag_color(ColorType.LIGHT_ACCENT, self.lib.get_tag(tag_id).color)};"
                f"color: {get_tag_color(ColorType.DARK_ACCENT, self.lib.get_tag(tag_id).color)};"
                f"background: {get_tag_color(ColorType.LIGHT_ACCENT, self.lib.get_tag(tag_id).color)};"
                f"}}"
            )

            ab.clicked.connect(lambda checked=False, x=tag_id: self.tag_chosen.emit(x))

            layout.addWidget(tw)
            layout.addWidget(ab)
            self.scroll_layout.addWidget(c)

        self.search_field.setFocus()

    # def enterEvent(self, event: QEnterEvent) -> None:
    # 	self.search_field.setFocus()
    # 	return super().enterEvent(event)
    # 	self.focusOutEvent
