# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio


import time
import typing
from pathlib import Path
from typing import Optional

from PIL import Image, ImageQt
from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QAction, QEnterEvent, QPixmap
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from src.core.constants import AUDIO_TYPES, IMAGE_TYPES, VIDEO_TYPES
from src.core.library import Entry, ItemType, Library
from src.qt.flowlayout import FlowWidget
from src.qt.helpers.file_opener import FileOpenerHelper
from src.qt.widgets.thumb_button import ThumbButton
from src.qt.widgets.thumb_renderer import ThumbRenderer

if typing.TYPE_CHECKING:
    from src.qt.widgets.preview_panel import PreviewPanel

DEFAULT_META_TAG_FIELD = 8
TAG_FAVORITE = 1
TAG_ARCHIVED = 0


class ItemThumb(FlowWidget):
    """
    The thumbnail widget for a library item (Entry, Collation, Tag Group, etc.).
    """

    update_cutoff: float = time.time()

    collation_icon_128: Image.Image = Image.open(
        str(Path(__file__).parents[3] / "resources/qt/images/collation_icon_128.png")
    )
    collation_icon_128.load()

    tag_group_icon_128: Image.Image = Image.open(
        str(Path(__file__).parents[3] / "resources/qt/images/tag_group_icon_128.png")
    )
    tag_group_icon_128.load()

    small_text_style = (
        "background-color:rgba(0, 0, 0, 192);"
        "font-family:Oxanium;"
        "font-weight:bold;"
        "font-size:12px;"
        "border-radius:3px;"
        "padding-top: 4px;"
        "padding-right: 1px;"
        "padding-bottom: 1px;"
        "padding-left: 1px;"
    )

    med_text_style = (
        "background-color:rgba(0, 0, 0, 192);"
        "font-family:Oxanium;"
        "font-weight:bold;"
        "font-size:18px;"
        "border-radius:3px;"
        "padding-top: 4px;"
        "padding-right: 1px;"
        "padding-bottom: 1px;"
        "padding-left: 1px;"
    )

    def __init__(
        self,
        mode: Optional[ItemType],
        library: Library,
        panel: "PreviewPanel",
        thumb_size: tuple[int, int],
    ):
        """Modes: entry, collation, tag_group"""
        super().__init__()
        self.lib = library
        self.panel = panel
        self.mode = mode
        self.item_id: int = -1
        self.isFavorite: bool = False
        self.isArchived: bool = False
        self.thumb_size: tuple[int, int] = thumb_size
        self.setMinimumSize(*thumb_size)
        self.setMaximumSize(*thumb_size)
        check_size = 24
        # self.setStyleSheet('background-color:red;')

        # +----------+
        # |   ARC FAV| Top Right: Favorite & Archived Badges
        # |          |
        # |          |
        # |EXT      #| Lower Left: File Type, Tag Group Icon, or Collation Icon
        # +----------+ Lower Right: Collation Count, Video Length, or Word Count

        # Thumbnail ============================================================

        # +----------+
        # |*--------*|
        # ||        ||
        # ||        ||
        # |*--------*|
        # +----------+
        self.base_layout = QVBoxLayout(self)
        self.base_layout.setObjectName("baseLayout")
        # self.base_layout.setRowStretch(1, 2)
        self.base_layout.setContentsMargins(0, 0, 0, 0)

        # +----------+
        # |[~~~~~~~~]|
        # |          |
        # |          |
        # |          |
        # +----------+
        self.top_layout = QHBoxLayout()
        self.top_layout.setObjectName("topLayout")
        # self.top_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # self.top_layout.setColumnStretch(1, 2)
        self.top_layout.setContentsMargins(6, 6, 6, 6)
        self.top_container = QWidget()
        self.top_container.setLayout(self.top_layout)
        self.base_layout.addWidget(self.top_container)

        # +----------+
        # |[~~~~~~~~]|
        # |     ^    |
        # |     |    |
        # |     v    |
        # +----------+
        self.base_layout.addStretch(2)

        # +----------+
        # |[~~~~~~~~]|
        # |     ^    |
        # |     v    |
        # |[~~~~~~~~]|
        # +----------+
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.setObjectName("bottomLayout")
        # self.bottom_container.setAlignment(Qt.AlignmentFlag.AlignBottom)
        # self.bottom_layout.setColumnStretch(1, 2)
        self.bottom_layout.setContentsMargins(6, 6, 6, 6)
        self.bottom_container = QWidget()
        self.bottom_container.setLayout(self.bottom_layout)
        self.base_layout.addWidget(self.bottom_container)

        # self.root_layout = QGridLayout(self)
        # self.root_layout.setObjectName('rootLayout')
        # self.root_layout.setColumnStretch(1, 2)
        # self.root_layout.setRowStretch(1, 2)
        # self.root_layout.setContentsMargins(6,6,6,6)
        # # root_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.thumb_button = ThumbButton(self, thumb_size)
        self.renderer = ThumbRenderer()
        self.renderer.updated.connect(
            lambda ts, i, s, ext: (
                self.update_thumb(ts, image=i),
                self.update_size(ts, size=s),
                self.set_extension(ext),  # type: ignore
            )
        )
        self.thumb_button.setFlat(True)

        # self.bg_button.setStyleSheet('background-color:blue;')
        # self.bg_button.setLayout(self.root_layout)
        self.thumb_button.setLayout(self.base_layout)
        # self.bg_button.setMinimumSize(*thumb_size)
        # self.bg_button.setMaximumSize(*thumb_size)

        self.thumb_button.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        self.opener = FileOpenerHelper("")
        open_file_action = QAction("Open file", self)
        open_file_action.triggered.connect(self.opener.open_file)
        open_explorer_action = QAction("Open file in explorer", self)
        open_explorer_action.triggered.connect(self.opener.open_explorer)
        self.thumb_button.addAction(open_file_action)
        self.thumb_button.addAction(open_explorer_action)

        # Static Badges ========================================================

        # Item Type Badge ------------------------------------------------------
        # Used for showing the Tag Group / Collation icons.
        # Mutually exclusive with the File Extension Badge.
        self.item_type_badge = QLabel()
        self.item_type_badge.setObjectName("itemBadge")
        self.item_type_badge.setPixmap(
            QPixmap.fromImage(
                ImageQt.ImageQt(
                    ItemThumb.collation_icon_128.resize(
                        (check_size, check_size), Image.Resampling.BILINEAR
                    )
                )
            )
        )
        self.item_type_badge.setMinimumSize(check_size, check_size)
        self.item_type_badge.setMaximumSize(check_size, check_size)
        # self.root_layout.addWidget(self.item_type_badge, 2, 0)
        self.bottom_layout.addWidget(self.item_type_badge)

        # File Extension Badge -------------------------------------------------
        # Mutually exclusive with the File Extension Badge.
        self.ext_badge = QLabel()
        self.ext_badge.setObjectName("extBadge")
        # self.ext_badge.setText('MP4')
        # self.ext_badge.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.ext_badge.setStyleSheet(ItemThumb.small_text_style)
        # self.type_badge.setAlignment(Qt.AlignmentFlag.AlignRight)
        # self.root_layout.addWidget(self.ext_badge, 2, 0)
        self.bottom_layout.addWidget(self.ext_badge)
        # self.type_badge.setHidden(True)
        # bl_layout.addWidget(self.type_badge)

        self.bottom_layout.addStretch(2)

        # Count Badge ----------------------------------------------------------
        # Used for Tag Group + Collation counts, video length, word count, etc.
        self.count_badge = QLabel()
        self.count_badge.setObjectName("countBadge")
        # self.count_badge.setMaximumHeight(17)
        self.count_badge.setText("-:--")
        # self.count_badge.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.count_badge.setStyleSheet(ItemThumb.small_text_style)
        # self.count_badge.setAlignment(Qt.AlignmentFlag.AlignBottom)
        # self.root_layout.addWidget(self.count_badge, 2, 2)
        self.bottom_layout.addWidget(
            self.count_badge, alignment=Qt.AlignmentFlag.AlignBottom
        )

        self.top_layout.addStretch(2)

        # Intractable Badges ===================================================
        self.cb_container = QWidget()
        # check_badges.setStyleSheet('background-color:cyan;')
        self.cb_layout = QHBoxLayout()
        self.cb_layout.setDirection(QBoxLayout.Direction.RightToLeft)
        self.cb_layout.setContentsMargins(0, 0, 0, 0)
        self.cb_layout.setSpacing(6)
        self.cb_container.setLayout(self.cb_layout)
        # self.cb_container.setHidden(True)
        # self.root_layout.addWidget(self.check_badges, 0, 2)
        self.top_layout.addWidget(self.cb_container)

        # Favorite Badge -------------------------------------------------------
        self.favorite_badge = QCheckBox()
        self.favorite_badge.setObjectName("favBadge")
        self.favorite_badge.setToolTip("Favorite")
        self.favorite_badge.setStyleSheet(
            f"QCheckBox::indicator{{width: {check_size}px;height: {check_size}px;}}"
            f"QCheckBox::indicator::unchecked{{image: url(:/images/star_icon_empty_128.png)}}"
            f"QCheckBox::indicator::checked{{image: url(:/images/star_icon_filled_128.png)}}"
            #  f'QCheckBox{{background-color:yellow;}}'
        )
        self.favorite_badge.setMinimumSize(check_size, check_size)
        self.favorite_badge.setMaximumSize(check_size, check_size)
        self.favorite_badge.stateChanged.connect(
            lambda x=self.favorite_badge.isChecked(): self.on_favorite_check(bool(x))
        )

        # self.fav_badge.setContentsMargins(0,0,0,0)
        # tr_layout.addWidget(self.fav_badge)
        # root_layout.addWidget(self.fav_badge, 0, 2)
        self.cb_layout.addWidget(self.favorite_badge)
        self.favorite_badge.setHidden(True)

        # Archive Badge --------------------------------------------------------
        self.archived_badge = QCheckBox()
        self.archived_badge.setObjectName("archiveBadge")
        self.archived_badge.setToolTip("Archive")
        self.archived_badge.setStyleSheet(
            f"QCheckBox::indicator{{width: {check_size}px;height: {check_size}px;}}"
            f"QCheckBox::indicator::unchecked{{image: url(:/images/box_icon_empty_128.png)}}"
            f"QCheckBox::indicator::checked{{image: url(:/images/box_icon_filled_128.png)}}"
            #  f'QCheckBox{{background-color:red;}}'
        )
        self.archived_badge.setMinimumSize(check_size, check_size)
        self.archived_badge.setMaximumSize(check_size, check_size)
        # self.archived_badge.clicked.connect(lambda x: self.assign_archived(x))
        self.archived_badge.stateChanged.connect(
            lambda x=self.archived_badge.isChecked(): self.on_archived_check(bool(x))
        )

        # tr_layout.addWidget(self.archive_badge)
        self.cb_layout.addWidget(self.archived_badge)
        self.archived_badge.setHidden(True)
        # root_layout.addWidget(self.archive_badge, 0, 2)
        # self.dumpObjectTree()

        self.set_mode(mode)

    def set_mode(self, mode: Optional[ItemType]) -> None:
        if mode is None:
            self.unsetCursor()
            self.thumb_button.setHidden(True)
            # self.check_badges.setHidden(True)
            # self.ext_badge.setHidden(True)
            # self.item_type_badge.setHidden(True)
            pass
        elif mode == ItemType.ENTRY and self.mode != ItemType.ENTRY:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.thumb_button.setHidden(False)
            self.cb_container.setHidden(False)
            # Count Badge depends on file extension (video length, word count)
            self.item_type_badge.setHidden(True)
            self.count_badge.setStyleSheet(ItemThumb.small_text_style)
            self.count_badge.setHidden(True)
            self.ext_badge.setHidden(True)
        elif mode == ItemType.COLLATION and self.mode != ItemType.COLLATION:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.thumb_button.setHidden(False)
            self.cb_container.setHidden(True)
            self.ext_badge.setHidden(True)
            self.count_badge.setStyleSheet(ItemThumb.med_text_style)
            self.count_badge.setHidden(False)
            self.item_type_badge.setHidden(False)
        elif mode == ItemType.TAG_GROUP and self.mode != ItemType.TAG_GROUP:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.thumb_button.setHidden(False)
            # self.cb_container.setHidden(True)
            self.ext_badge.setHidden(True)
            self.count_badge.setHidden(False)
            self.item_type_badge.setHidden(False)
        self.mode = mode
        # logging.info(f'Set Mode To: {self.mode}')

    # def update_(self, thumb: QPixmap, size:QSize, ext:str, badges:list[QPixmap]) -> None:
    # 	"""Updates the ItemThumb's visuals."""
    # 	if thumb:
    # 		pass

    def set_extension(self, ext: str) -> None:
        if ext and ext.startswith(".") is False:
            ext = "." + ext
        if ext and ext not in IMAGE_TYPES or ext in [".gif", ".apng"]:
            self.ext_badge.setHidden(False)
            self.ext_badge.setText(ext.upper()[1:])
            if ext in VIDEO_TYPES + AUDIO_TYPES:
                self.count_badge.setHidden(False)
        else:
            if self.mode == ItemType.ENTRY:
                self.ext_badge.setHidden(True)
                self.count_badge.setHidden(True)

    def set_count(self, count: str) -> None:
        if count:
            self.count_badge.setHidden(False)
            self.count_badge.setText(count)
        else:
            if self.mode == ItemType.ENTRY:
                self.ext_badge.setHidden(True)
                self.count_badge.setHidden(True)

    def update_thumb(self, timestamp: float, image: QPixmap = None):
        """Updates attributes of a thumbnail element."""
        # logging.info(f'[GUI] Updating Thumbnail for element {id(element)}: {id(image) if image else None}')
        if timestamp > ItemThumb.update_cutoff:
            self.thumb_button.setIcon(image if image else QPixmap())
            # element.repaint()

    def update_size(self, timestamp: float, size: QSize):
        """Updates attributes of a thumbnail element."""
        # logging.info(f'[GUI] Updating size for element {id(element)}:  {size.__str__()}')
        if timestamp > ItemThumb.update_cutoff:
            if self.thumb_button.iconSize != size:
                self.thumb_button.setIconSize(size)
                self.thumb_button.setMinimumSize(size)
                self.thumb_button.setMaximumSize(size)

    def update_clickable(self, clickable: typing.Callable):
        """Updates attributes of a thumbnail element."""
        # logging.info(f'[GUI] Updating Click Event for element {id(element)}: {id(clickable) if clickable else None}')
        try:
            self.thumb_button.clicked.disconnect()
        except RuntimeError:
            pass
        if clickable:
            self.thumb_button.clicked.connect(clickable)

    def update_badges(self):
        if self.mode == ItemType.ENTRY:
            # logging.info(f'[UPDATE BADGES] ENTRY: {self.lib.get_entry(self.item_id)}')
            # logging.info(f'[UPDATE BADGES] ARCH: {self.lib.get_entry(self.item_id).has_tag(self.lib, 0)}, FAV: {self.lib.get_entry(self.item_id).has_tag(self.lib, 1)}')
            self.assign_archived(self.lib.get_entry(self.item_id).has_tag(self.lib, 0))
            self.assign_favorite(self.lib.get_entry(self.item_id).has_tag(self.lib, 1))

    def set_item_id(self, id: int):
        """
        also sets the filepath for the file opener
        """
        self.item_id = id
        if id == -1:
            return
        entry = self.lib.get_entry(self.item_id)
        filepath = self.lib.library_dir / entry.path / entry.filename
        self.opener.set_filepath(filepath)

    def assign_favorite(self, value: bool):
        # Switching mode to None to bypass mode-specific operations when the
        # checkbox's state changes.
        mode = self.mode
        self.mode = None
        self.isFavorite = value
        self.favorite_badge.setChecked(value)
        if not self.thumb_button.underMouse():
            self.favorite_badge.setHidden(not self.isFavorite)
        self.mode = mode

    def assign_archived(self, value: bool):
        # Switching mode to None to bypass mode-specific operations when the
        # checkbox's state changes.
        mode = self.mode
        self.mode = None
        self.isArchived = value
        self.archived_badge.setChecked(value)
        if not self.thumb_button.underMouse():
            self.archived_badge.setHidden(not self.isArchived)
        self.mode = mode

    def show_check_badges(self, show: bool):
        if self.mode != ItemType.TAG_GROUP:
            self.favorite_badge.setHidden(
                True if (not show and not self.isFavorite) else False
            )
            self.archived_badge.setHidden(
                True if (not show and not self.isArchived) else False
            )

    def enterEvent(self, event: QEnterEvent) -> None:
        self.show_check_badges(True)
        return super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.show_check_badges(False)
        return super().leaveEvent(event)

    def on_archived_check(self, toggle_value: bool):
        if self.mode == ItemType.ENTRY:
            self.isArchived = toggle_value
            self.toggle_item_tag(toggle_value, TAG_ARCHIVED)

    def on_favorite_check(self, toggle_value: bool):
        if self.mode == ItemType.ENTRY:
            self.isFavorite = toggle_value
            self.toggle_item_tag(toggle_value, TAG_FAVORITE)

    def toggle_item_tag(self, toggle_value: bool, tag_id: int):
        def toggle_tag(entry: Entry):
            if toggle_value:
                self.favorite_badge.setHidden(False)
                entry.add_tag(
                    self.panel.driver.lib,
                    tag_id,
                    field_id=DEFAULT_META_TAG_FIELD,
                    field_index=-1,
                )
            else:
                entry.remove_tag(self.panel.driver.lib, tag_id)

        # Is the badge a part of the selection?
        if (ItemType.ENTRY, self.item_id) in self.panel.driver.selected:
            # Yes, add chosen tag to all selected.
            for _, item_id in self.panel.driver.selected:
                entry = self.lib.get_entry(item_id)
                toggle_tag(entry)
        else:
            # No, add tag to the entry this badge is on.
            entry = self.lib.get_entry(self.item_id)
            toggle_tag(entry)

        if self.panel.isOpen:
            self.panel.update_widgets()
        self.panel.driver.update_badges()
