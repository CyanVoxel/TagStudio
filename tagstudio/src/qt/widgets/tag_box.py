# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio


import logging
import math
import typing

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QPushButton

from src.core.library import Library, Tag
from src.qt.flowlayout import FlowLayout
from src.qt.widgets.fields import FieldWidget
from src.qt.widgets.tag import TagWidget
from src.qt.widgets.panel import PanelModal
from src.qt.modals.build_tag import BuildTagPanel
from src.qt.modals.tag_search import TagSearchPanel

# Only import for type checking/autocompletion, will not be imported at runtime.
if typing.TYPE_CHECKING:
    from src.qt.ts_qt import QtDriver


class TagBoxWidget(FieldWidget):
    updated = Signal()

    def __init__(
        self,
        item,
        title,
        field_index,
        library: Library,
        tags: list[int],
        driver: "QtDriver",
    ) -> None:
        super().__init__(title)
        # QObject.__init__(self)
        self.item = item
        self.lib = library
        self.driver = driver  # Used for creating tag click callbacks that search entries for that tag.
        self.field_index = field_index
        self.tags: list[int] = tags
        self.setObjectName("tagBox")
        self.base_layout = FlowLayout()
        self.base_layout.setGridEfficiency(False)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.base_layout)

        self.add_button = QPushButton()
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.setMinimumSize(23, 23)
        self.add_button.setMaximumSize(23, 23)
        self.add_button.setText("+")
        self.add_button.setStyleSheet(
            f"QPushButton{{"
            f"background: #1e1e1e;"
            f"color: #FFFFFF;"
            f"font-weight: bold;"
            f"border-color: #333333;"
            f"border-radius: 6px;"
            f"border-style:solid;"
            f"border-width:{math.ceil(1*self.devicePixelRatio())}px;"
            # f'padding-top: 1.5px;'
            # f'padding-right: 4px;'
            f"padding-bottom: 5px;"
            # f'padding-left: 4px;'
            f"font-size: 20px;"
            f"}}"
            f"QPushButton::hover"
            f"{{"
            f"border-color: #CCCCCC;"
            f"background: #555555;"
            f"}}"
        )
        tsp = TagSearchPanel(self.lib)
        tsp.tag_chosen.connect(lambda x, checked: self.update_tag_callback(x, checked))
        self.add_modal = PanelModal(tsp, title, "Add Tags")
        self.add_button.clicked.connect(
            lambda: (tsp.update_tags(current_tags=self.tags), self.add_modal.show())  # type: ignore
        )

        self.set_tags(tags)
        # self.add_button.setHidden(True)

    def set_item(self, item):
        self.item = item

    def set_tags(self, tags: list[int]):
        logging.info(f"[TAG BOX WIDGET] SET TAGS: T:{tags} for E:{self.item.id}")
        is_recycled = False
        if self.base_layout.itemAt(0):
            # logging.info(type(self.base_layout.itemAt(0).widget()))
            while self.base_layout.itemAt(0) and self.base_layout.itemAt(1):
                # logging.info(f"I'm deleting { self.base_layout.itemAt(0).widget()}")
                self.base_layout.takeAt(0).widget().deleteLater()
            is_recycled = True
        for tag in tags:
            # TODO: Remove space from the special search here (tag_id:x) once that system is finalized.
            # tw = TagWidget(self.lib, self.lib.get_tag(tag), True, True,
            # 							on_remove_callback=lambda checked=False, t=tag: (self.lib.get_entry(self.item.id).remove_tag(self.lib, t, self.field_index), self.updated.emit()),
            # 							on_click_callback=lambda checked=False, q=f'tag_id: {tag}': (self.driver.main_window.searchField.setText(q), self.driver.filter_items(q)),
            # 							on_edit_callback=lambda checked=False, t=tag: (self.edit_tag(t))
            # 							)
            tw = TagWidget(self.lib, self.lib.get_tag(tag), True, True)
            tw.on_click.connect(
                lambda checked=False, q=f"tag_id: {tag}": (
                    self.driver.main_window.searchField.setText(q),
                    self.driver.filter_items(q),
                )
            )
            tw.on_remove.connect(lambda checked=False, t=tag: (self.remove_tag(t)))
            tw.on_edit.connect(lambda checked=False, t=tag: (self.edit_tag(t)))
            self.base_layout.addWidget(tw)
        self.tags = tags

        # Move or add the '+' button.
        if is_recycled:
            self.base_layout.addWidget(self.base_layout.takeAt(0).widget())
        else:
            self.base_layout.addWidget(self.add_button)

        # Handles an edge case where there are no more tags and the '+' button
        # doesn't move all the way to the left.
        if self.base_layout.itemAt(0) and not self.base_layout.itemAt(1):
            self.base_layout.update()

    def edit_tag_callback(self, tag: Tag):
        self.lib.update_tag(tag)

    def edit_tag(self, tag_id: int):
        btp = BuildTagPanel(self.lib, tag_id)
        # btp.on_edit.connect(lambda x: self.edit_tag_callback(x))
        self.edit_modal = PanelModal(
            btp,
            self.lib.get_tag(tag_id).display_name(self.lib),
            "Edit Tag",
            done_callback=(self.driver.preview_panel.update_widgets),
            has_save=True,
        )
        # self.edit_modal.widget.update_display_name.connect(lambda t: self.edit_modal.title_widget.setText(t))
        self.edit_modal.saved.connect(lambda: self.lib.update_tag(btp.build_tag()))
        # panel.tag_updated.connect(lambda tag: self.lib.update_tag(tag))
        self.edit_modal.show()

    def update_tag_callback(self, tag_id: int, checked: bool):
        logging.info(
            f"[TAG BOX WIDGET] UPDATE TAG CALLBACK: {'Add' if checked else 'Remove'} T:{tag_id} to E:{self.item.id}"
        )
        if checked:
            self.add_tag(tag_id)
        else:
            self.remove_tag(tag_id)

    def add_tag(self, tag_id: int):
        # self.base_layout.addWidget(TagWidget(self.lib, self.lib.get_tag(tag), True))
        # self.tags.append(tag)
        logging.info(f"[TAG BOX WIDGET] SELECTED T:{self.driver.selected}")
        id: int = list(self.field.keys())[0]  # type: ignore
        for x in self.driver.selected:
            self.driver.lib.get_entry(x[1]).add_tag(
                self.driver.lib, tag_id, field_id=id, field_index=-1
            )
            self.updated.emit()
        if tag_id == 0 or tag_id == 1:
            self.driver.update_badges()

        # if type((x[0]) == ThumbButton):
        # 	# TODO: Remove space from the special search here (tag_id:x) once that system is finalized.
        # logging.info(f'I want to add tag ID {tag_id} to entry {self.item.filename}')
        # self.updated.emit()
        # if tag_id not in self.tags:
        # 	self.tags.append(tag_id)
        # self.set_tags(self.tags)
        # elif type((x[0]) == ThumbButton):

    def remove_tag(self, tag_id: int):
        logging.info(f"[TAG BOX WIDGET] SELECTED T:{self.driver.selected}")
        id: int = list(self.field.keys())[0]  # type: ignore
        for x in self.driver.selected:
            index = self.driver.lib.get_field_index_in_entry(
                self.driver.lib.get_entry(x[1]), id
            )
            self.driver.lib.get_entry(x[1]).remove_tag(
                self.driver.lib, tag_id, field_index=index[0]
            )
            self.updated.emit()
        if tag_id == 0 or tag_id == 1:
            self.driver.update_badges()

    # def show_add_button(self, value:bool):
    # 	self.add_button.setHidden(not value)
