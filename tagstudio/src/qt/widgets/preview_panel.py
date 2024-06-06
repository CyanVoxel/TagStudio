# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio

import time
import typing
from datetime import datetime as dt
from pathlib import Path

import cv2
import rawpy
from humanfriendly import format_size
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QResizeEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSizePolicy,
    QMessageBox,
)
from src.core.constants import IMAGE_TYPES, RAW_IMAGE_TYPES, VIDEO_TYPES
from src.core.enums import SettingItems, Theme
from src.core.library import Entry, ItemType, Library
from src.core.logging import get_logger
from src.core.constants import TS_FOLDER_NAME
from src.qt.helpers.file_opener import FileOpenerLabel, FileOpenerHelper, open_file
from src.qt.modals.add_field import AddFieldModal
from src.qt.widgets.fields import FieldContainer
from src.qt.widgets.panel import PanelModal
from src.qt.widgets.tag_box import TagBoxWidget
from src.qt.widgets.text import TextWidget
from src.qt.widgets.text_box_edit import EditTextBox
from src.qt.widgets.text_line_edit import EditTextLine
from src.qt.widgets.thumb_renderer import ThumbRenderer
from src.qt.widgets.video_player import VideoPlayer

# Only import for type checking/autocompletion, will not be imported at runtime.
if typing.TYPE_CHECKING:
    from src.qt.ts_qt import QtDriver

logger = get_logger(__name__)


class PreviewPanel(QWidget):
    """The Preview Panel Widget."""

    tags_updated = Signal()

    def __init__(self, library: Library, driver: "QtDriver"):
        super().__init__()
        self.lib = library
        self.driver: QtDriver = driver
        self.initialized = False
        self.isOpen: bool = False
        # self.filepath = None
        # self.item = None # DEPRECATED, USE self.selected
        self.common_fields: list = []
        self.mixed_fields: list = []
        self.selected: list[tuple[ItemType, int]] = []  # New way of tracking items
        self.tag_callback = None
        self.containers: list[QWidget] = []

        self.img_button_size: tuple[int, int] = (266, 266)
        self.image_ratio: float = 1.0

        self.image_container = QWidget()
        image_layout = QHBoxLayout(self.image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)

        self.open_file_action = QAction("Open file", self)
        self.open_explorer_action = QAction("Open file in explorer", self)

        self.preview_img = QPushButton()
        self.preview_img.setMinimumSize(*self.img_button_size)
        self.preview_img.setFlat(True)
        self.preview_img.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

        self.preview_img.addAction(self.open_file_action)
        self.preview_img.addAction(self.open_explorer_action)
        self.preview_vid = VideoPlayer(driver)
        self.preview_vid.hide()
        self.thumb_renderer = ThumbRenderer()
        self.thumb_renderer.updated.connect(
            lambda ts, i, s: (self.preview_img.setIcon(i))
        )
        self.thumb_renderer.updated_ratio.connect(
            lambda ratio: (
                self.set_image_ratio(ratio),
                self.update_image_size(
                    (
                        self.image_container.size().width(),
                        self.image_container.size().height(),
                    ),
                    ratio,
                ),
            )
        )

        image_layout.addWidget(self.preview_img)
        image_layout.setAlignment(self.preview_img, Qt.AlignmentFlag.AlignCenter)
        image_layout.addWidget(self.preview_vid)
        image_layout.setAlignment(self.preview_vid, Qt.AlignmentFlag.AlignCenter)
        self.image_container.setMinimumSize(*self.img_button_size)
        self.file_label = FileOpenerLabel("Filename")
        self.file_label.setWordWrap(True)
        self.file_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.file_label.setStyleSheet("font-weight: bold; font-size: 12px")

        self.dimensions_label = QLabel("Dimensions")
        self.dimensions_label.setWordWrap(True)
        # self.dim_label.setTextInteractionFlags(
        # 	Qt.TextInteractionFlag.TextSelectableByMouse)

        properties_style = (
            f"background-color:{Theme.COLOR_BG.value};"
            f"font-family:Oxanium;"
            f"font-weight:bold;"
            f"font-size:12px;"
            f"border-radius:6px;"
            f"padding-top: 4px;"
            f"padding-right: 1px;"
            f"padding-bottom: 1px;"
            f"padding-left: 1px;"
        )

        self.dimensions_label.setStyleSheet(properties_style)

        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setContentsMargins(6, 1, 6, 6)

        scroll_container: QWidget = QWidget()
        scroll_container.setObjectName("entryScrollContainer")
        scroll_container.setLayout(self.scroll_layout)

        info_section = QWidget()
        info_layout = QVBoxLayout(info_section)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(6)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("entryScrollArea")
        scroll_area.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShadow(QFrame.Shadow.Plain)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        # NOTE: I would rather have this style applied to the scroll_area
        # background and NOT the scroll container background, so that the
        # rounded corners are maintained when scrolling. I was unable to
        # find the right trick to only select that particular element.
        scroll_area.setStyleSheet(
            "QWidget#entryScrollContainer{"
            f"background: {Theme.COLOR_BG.value};"
            "border-radius:6px;"
            "}"
        )
        scroll_area.setWidget(scroll_container)

        info_layout.addWidget(self.file_label)
        info_layout.addWidget(self.dimensions_label)
        info_layout.addWidget(scroll_area)

        # keep list of rendered libraries to avoid needless re-rendering
        self.render_libs: set = set()
        self.libs_layout = QVBoxLayout()
        self.fill_libs_widget(self.libs_layout)

        self.libs_flow_container: QWidget = QWidget()
        self.libs_flow_container.setObjectName("librariesList")
        self.libs_flow_container.setLayout(self.libs_layout)
        self.libs_flow_container.setSizePolicy(
            QSizePolicy.Preferred,  # type: ignore
            QSizePolicy.Maximum,  # type: ignore
        )

        # set initial visibility based on settings
        if not self.driver.settings.value(
            SettingItems.WINDOW_SHOW_LIBS, True, type=bool
        ):
            self.libs_flow_container.hide()

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.setHandleWidth(12)
        splitter.splitterMoved.connect(
            lambda: self.update_image_size(
                (
                    self.image_container.size().width(),
                    self.image_container.size().height(),
                )
            )
        )

        splitter.addWidget(self.image_container)
        splitter.addWidget(info_section)
        splitter.addWidget(self.libs_flow_container)
        splitter.setStretchFactor(1, 2)

        self.afb_container = QWidget()
        self.afb_layout = QVBoxLayout(self.afb_container)
        self.afb_layout.setContentsMargins(0, 12, 0, 0)

        self.add_field_button = QPushButton()
        self.add_field_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_field_button.setMinimumSize(96, 28)
        self.add_field_button.setMaximumSize(96, 28)
        self.add_field_button.setText("Add Field")
        self.afb_layout.addWidget(self.add_field_button)
        self.afm = AddFieldModal(self.lib)
        self.place_add_field_button()
        self.update_image_size(
            (self.image_container.size().width(), self.image_container.size().height())
        )

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(splitter)

    def fill_libs_widget(self, layout: QVBoxLayout):
        settings = self.driver.settings
        settings.beginGroup(SettingItems.LIBS_LIST)
        lib_items: dict[str, tuple[str, str]] = {}
        for item_tstamp in settings.allKeys():
            val: str = settings.value(item_tstamp)  # type: ignore
            cut_val = val
            if len(val) > 45:
                cut_val = f"{val[0:10]} ... {val[-10:]}"
            lib_items[item_tstamp] = (val, cut_val)

        settings.endGroup()

        new_keys = set(lib_items.keys())
        if new_keys == self.render_libs:
            # no need to re-render
            return

        # sort lib_items by the key
        libs_sorted = sorted(lib_items.items(), key=lambda item: item[0], reverse=True)

        self.render_libs = new_keys
        self._fill_libs_widget(libs_sorted, layout)

    def _fill_libs_widget(
        self, libraries: list[tuple[str, tuple[str, str]]], layout: QVBoxLayout
    ):
        def clear_layout(layout_item: QVBoxLayout):
            for i in reversed(range(layout_item.count())):
                child = layout_item.itemAt(i)
                if child.widget() is not None:
                    child.widget().deleteLater()
                elif child.layout() is not None:
                    clear_layout(child.layout())  # type: ignore

        # remove any potential previous items
        clear_layout(layout)

        label = QLabel("Recent Libraries")
        label.setAlignment(Qt.AlignCenter)  # type: ignore

        row_layout = QHBoxLayout()
        row_layout.addWidget(label)
        layout.addLayout(row_layout)

        def set_button_style(btn: QPushButton, extras: list[str] | None = None):
            base_style = [
                f"background-color:{Theme.COLOR_BG.value};",
                "border-radius:6px;",
                "text-align: left;",
                "padding-top: 3px;",
                "padding-left: 6px;",
                "padding-bottom: 4px;",
            ]

            full_style_rows = base_style + (extras or [])

            btn.setStyleSheet(
                (
                    "QPushButton{"
                    f"{''.join(full_style_rows)}"
                    "}"
                    f"QPushButton::hover{{background-color:{Theme.COLOR_HOVER.value};}}"
                    f"QPushButton::pressed{{background-color:{Theme.COLOR_PRESSED.value};}}"
                    f"QPushButton::disabled{{background-color:{Theme.COLOR_DISABLED_BG.value};}}"
                )
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        for item_key, (full_val, cut_val) in libraries:
            button = QPushButton(text=cut_val)
            button.setObjectName(f"path{item_key}")

            lib = Path(full_val)
            if not lib.exists() or not (lib / TS_FOLDER_NAME).exists():
                button.setDisabled(True)
                button.setToolTip("Location is missing")

            def open_library_button_clicked(path):
                return lambda: self.driver.open_library(Path(path))

            button.clicked.connect(open_library_button_clicked(full_val))
            set_button_style(button)

            button_remove = QPushButton("➖")
            button_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            button_remove.setFixedWidth(30)
            set_button_style(button_remove)

            def remove_recent_library_clicked(key: str):
                return lambda: (
                    self.driver.remove_recent_library(key),
                    self.fill_libs_widget(self.libs_layout),
                )

            button_remove.clicked.connect(remove_recent_library_clicked(item_key))

            row_layout = QHBoxLayout()
            row_layout.addWidget(button)
            row_layout.addWidget(button_remove)

            layout.addLayout(row_layout)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.update_image_size(
            (self.image_container.size().width(), self.image_container.size().height())
        )
        return super().resizeEvent(event)

    def get_preview_size(self) -> tuple[int, int]:
        return (
            self.image_container.size().width(),
            self.image_container.size().height(),
        )

    def set_image_ratio(self, ratio: float):
        # logger.info(f'Updating Ratio to: {ratio} #####################################################')
        self.image_ratio = ratio

    def update_image_size(self, size: tuple[int, int], ratio: float = None):
        if ratio:
            self.set_image_ratio(ratio)
        # self.img_button_size = size
        # logger.info(f'')
        # self.preview_img.setMinimumSize(64,64)

        adj_width: float = size[0]
        adj_height: float = size[1]
        # Landscape
        if self.image_ratio > 1:
            # logger.info('Landscape')
            adj_height = size[0] * (1 / self.image_ratio)
        # Portrait
        elif self.image_ratio <= 1:
            # logger.info('Portrait')
            adj_width = size[1] * self.image_ratio

        if adj_width > size[0]:
            adj_height = adj_height * (size[0] / adj_width)
            adj_width = size[0]
        elif adj_height > size[1]:
            adj_width = adj_width * (size[1] / adj_height)
            adj_height = size[1]

        # adj_width = min(adj_width, self.image_container.size().width())
        # adj_height = min(adj_width, self.image_container.size().height())

        # self.preview_img.setMinimumSize(s)
        # self.preview_img.setMaximumSize(s_max)
        adj_size = QSize(int(adj_width), int(adj_height))
        self.img_button_size = (int(adj_width), int(adj_height))
        self.preview_img.setMaximumSize(adj_size)
        self.preview_img.setIconSize(adj_size)
        self.preview_vid.resizeVideo(adj_size)
        self.preview_vid.setMaximumSize(adj_size)
        self.preview_vid.setMinimumSize(adj_size)
        # self.preview_img.setMinimumSize(adj_size)

        # if self.preview_img.iconSize().toTuple()[0] < self.preview_img.size().toTuple()[0] + 10:
        # 	if type(self.item) == Entry:
        # 		filepath = os.path.normpath(f'{self.lib.library_dir}/{self.item.path}/{self.item.filename}')
        # 		self.thumb_renderer.render(time.time(), filepath, self.preview_img.size().toTuple(), self.devicePixelRatio(),update_on_ratio_change=True)

        # logger.info(f' Img Aspect Ratio: {self.image_ratio}')
        # logger.info(f'  Max Button Size: {size}')
        # logger.info(f'Container Size: {(self.image_container.size().width(), self.image_container.size().height())}')
        # logger.info(f'Final Button Size: {(adj_width, adj_height)}')
        # logger.info(f'')
        # logger.info(f'  Icon Size: {self.preview_img.icon().actualSize().toTuple()}')
        # logger.info(f'Button Size: {self.preview_img.size().toTuple()}')

    def place_add_field_button(self):
        self.scroll_layout.addWidget(self.afb_container)
        self.scroll_layout.setAlignment(
            self.afb_container, Qt.AlignmentFlag.AlignHCenter
        )

        try:
            self.afm.done.disconnect()
            self.add_field_button.clicked.disconnect()
        except RuntimeError:
            pass

        # self.afm.done.connect(lambda f: (self.lib.add_field_to_entry(self.selected[0][1], f), self.update_widgets()))
        self.afm.done.connect(
            lambda f: (self.add_field_to_selected(f), self.update_widgets())
        )
        self.add_field_button.clicked.connect(self.afm.show)

    def add_field_to_selected(self, field_id: int):
        """Adds an entry field to one or more selected items."""
        added = set()
        for item_pair in self.selected:
            if item_pair[0] == ItemType.ENTRY and item_pair[1] not in added:
                self.lib.add_field_to_entry(item_pair[1], field_id)
                added.add(item_pair[1])

    # def update_widgets(self, item: Union[Entry, Collation, Tag]):
    def update_widgets(self):
        """
        Renders the panel's widgets with the newest data from the Library.
        """
        logger.info(f"[ENTRY PANEL] UPDATE WIDGETS ({self.driver.selected})")
        self.isOpen = True
        # self.tag_callback = tag_callback if tag_callback else None
        window_title = ""

        # update list of libraries
        self.fill_libs_widget(self.libs_layout)

        # 0 Selected Items
        if not self.driver.selected:
            if self.selected or not self.initialized:
                self.file_label.setText("No Items Selected")
                self.file_label.setFilePath("")
                self.file_label.setCursor(Qt.CursorShape.ArrowCursor)

                self.dimensions_label.setText("")
                self.preview_img.setContextMenuPolicy(
                    Qt.ContextMenuPolicy.NoContextMenu
                )
                self.preview_img.setCursor(Qt.CursorShape.ArrowCursor)

                ratio: float = self.devicePixelRatio()
                self.thumb_renderer.render(
                    time.time(),
                    "",
                    (512, 512),
                    ratio,
                    True,
                    update_on_ratio_change=True,
                )
                try:
                    self.preview_img.clicked.disconnect()
                except RuntimeError:
                    pass
                for i, c in enumerate(self.containers):
                    c.setHidden(True)
            self.preview_img.show()
            self.preview_vid.stop()
            self.preview_vid.hide()
            self.selected = list(self.driver.selected)
            self.add_field_button.setHidden(True)

        # 1 Selected Item
        elif len(self.driver.selected) == 1:
            # 1 Selected Entry
            if self.driver.selected[0][0] == ItemType.ENTRY:
                self.preview_img.show()
                self.preview_vid.stop()
                self.preview_vid.hide()
                item: Entry = self.lib.get_entry(self.driver.selected[0][1])
                # If a new selection is made, update the thumbnail and filepath.
                if not self.selected or self.selected != self.driver.selected:
                    filepath = self.lib.library_dir / item.path / item.filename
                    self.file_label.setFilePath(filepath)
                    window_title = str(filepath)
                    ratio: float = self.devicePixelRatio()
                    self.thumb_renderer.render(
                        time.time(),
                        filepath,
                        (512, 512),
                        ratio,
                        update_on_ratio_change=True,
                    )
                    self.file_label.setText("\u200b".join(str(filepath)))
                    self.file_label.setCursor(Qt.CursorShape.PointingHandCursor)

                    self.preview_img.setContextMenuPolicy(
                        Qt.ContextMenuPolicy.ActionsContextMenu
                    )
                    self.preview_img.setCursor(Qt.CursorShape.PointingHandCursor)

                    self.opener = FileOpenerHelper(filepath)
                    self.open_file_action.triggered.connect(self.opener.open_file)
                    self.open_explorer_action.triggered.connect(
                        self.opener.open_explorer
                    )

                    # TODO: Do this somewhere else, this is just here temporarily.
                    try:
                        image = None
                        if filepath.suffix.lower() in IMAGE_TYPES:
                            image = Image.open(str(filepath))
                        elif filepath.suffix.lower() in RAW_IMAGE_TYPES:
                            try:
                                with rawpy.imread(str(filepath)) as raw:
                                    rgb = raw.postprocess()
                                    image = Image.new(
                                        "L", (rgb.shape[1], rgb.shape[0]), color="black"
                                    )
                            except (
                                rawpy._rawpy.LibRawIOError,
                                rawpy._rawpy.LibRawFileUnsupportedError,
                            ):
                                pass
                        elif filepath.suffix.lower() in VIDEO_TYPES:
                            video = cv2.VideoCapture(str(filepath))
                            video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            success, frame = video.read()
                            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            image = Image.fromarray(frame)
                            if success:
                                self.preview_img.hide()
                                self.preview_vid.play(
                                    str(filepath.resolve().absolute()),
                                    QSize(image.width, image.height),
                                )
                                self.resizeEvent(
                                    QResizeEvent(
                                        QSize(image.width, image.height),
                                        QSize(image.width, image.height),
                                    )
                                )
                                self.preview_vid.show()

                        # Stats for specific file types are displayed here.
                        if image and filepath.suffix.lower() in (
                            IMAGE_TYPES + VIDEO_TYPES + RAW_IMAGE_TYPES
                        ):
                            self.dimensions_label.setText(
                                f"{filepath.suffix.upper()[1:]}  •  {format_size(filepath.stat().st_size)}\n{image.width} x {image.height} px"
                            )
                        else:
                            self.dimensions_label.setText(
                                f"{filepath.suffix.upper()[1:]}  •  {format_size(filepath.stat().st_size)}"
                            )

                        if not filepath.is_file():
                            raise FileNotFoundError

                    except FileNotFoundError as e:
                        self.dimensions_label.setText(f"{filepath.suffix.upper()[1:]}")
                        logger.error(
                            f"[PreviewPanel] Couldn't Render thumbnail for {filepath} (because of {e})"
                        )
                    except (FileNotFoundError, cv2.error) as e:
                        self.dimensions_label.setText(f"{filepath.suffix.upper()}")
                        logger.error(
                            f"[PreviewPanel] Couldn't Render thumbnail for {filepath} (because of {e})"
                        )
                    except (
                        UnidentifiedImageError,
                        DecompressionBombError,
                    ) as e:
                        self.dimensions_label.setText(
                            f"{filepath.suffix.upper()[1:]}  •  {format_size(filepath.stat().st_size)}"
                        )
                        logger.error(
                            f"[PreviewPanel] Couldn't Render thumbnail for {filepath} (because of {e})"
                        )

                    try:
                        self.preview_img.clicked.disconnect()
                    except RuntimeError:
                        pass
                    self.preview_img.clicked.connect(
                        lambda checked=False, filepath=filepath: open_file(filepath)
                    )

                self.selected = list(self.driver.selected)
                for i, f in enumerate(item.fields):
                    self.write_container(i, f)

                # Hide leftover containers
                if len(self.containers) > len(item.fields):
                    for i, c in enumerate(self.containers):
                        if i > (len(item.fields) - 1):
                            c.setHidden(True)

                self.add_field_button.setHidden(False)

            # 1 Selected Collation
            elif self.driver.selected[0][0] == ItemType.COLLATION:
                pass

            # 1 Selected Tag
            elif self.driver.selected[0][0] == ItemType.TAG_GROUP:
                pass

        # Multiple Selected Items
        elif len(self.driver.selected) > 1:
            self.preview_img.show()
            self.preview_vid.stop()
            self.preview_vid.hide()
            if self.selected != self.driver.selected:
                self.file_label.setText(f"{len(self.driver.selected)} Items Selected")
                self.file_label.setCursor(Qt.CursorShape.ArrowCursor)
                self.file_label.setFilePath("")
                self.dimensions_label.setText("")

                self.preview_img.setContextMenuPolicy(
                    Qt.ContextMenuPolicy.NoContextMenu
                )
                self.preview_img.setCursor(Qt.CursorShape.ArrowCursor)

                ratio: float = self.devicePixelRatio()
                self.thumb_renderer.render(
                    time.time(),
                    "",
                    (512, 512),
                    ratio,
                    True,
                    update_on_ratio_change=True,
                )
                try:
                    self.preview_img.clicked.disconnect()
                except RuntimeError:
                    pass

            self.common_fields = []
            self.mixed_fields = []
            for i, item_pair in enumerate(self.driver.selected):
                if item_pair[0] == ItemType.ENTRY:
                    item = self.lib.get_entry(item_pair[1])
                    if i == 0:
                        for f in item.fields:
                            self.common_fields.append(f)
                    else:
                        common_to_remove = []
                        for f in self.common_fields:
                            # Common field found (Same ID, identical content)
                            if f not in item.fields:
                                common_to_remove.append(f)

                                # Mixed field found (Same ID, different content)
                                if self.lib.get_field_index_in_entry(
                                    item, self.lib.get_field_attr(f, "id")
                                ):
                                    # if self.lib.get_field_attr(f, 'type') == ('tag_box'):
                                    # 	pass
                                    # logger.info(f)
                                    # logger.info(type(f))
                                    f_stripped = {
                                        self.lib.get_field_attr(f, "id"): None
                                    }
                                    if f_stripped not in self.mixed_fields and (
                                        f not in self.common_fields
                                        or f in common_to_remove
                                    ):
                                        #  and (f not in self.common_fields or f in common_to_remove)
                                        self.mixed_fields.append(f_stripped)
                        self.common_fields = [
                            f for f in self.common_fields if f not in common_to_remove
                        ]
            order: list[int] = (
                [0]
                + [1, 2]
                + [9, 17, 18, 19, 20]
                + [8, 7, 6]
                + [4]
                + [3, 21]
                + [10, 14, 11, 12, 13, 22]
                + [5]
            )
            self.mixed_fields = sorted(
                self.mixed_fields,
                key=lambda x: order.index(self.lib.get_field_attr(x, "id")),
            )

            self.selected = list(self.driver.selected)
            for i, f in enumerate(self.common_fields):
                logger.info(f"ci:{i}, f:{f}")
                self.write_container(i, f)
            for i, f in enumerate(self.mixed_fields, start=len(self.common_fields)):
                logger.info(f"mi:{i}, f:{f}")
                self.write_container(i, f, mixed=True)

            # Hide leftover containers
            if len(self.containers) > len(self.common_fields) + len(self.mixed_fields):
                for i, c in enumerate(self.containers):
                    if i > (len(self.common_fields) + len(self.mixed_fields) - 1):
                        c.setHidden(True)

            self.add_field_button.setHidden(False)

        self.initialized = True

        # # Uninitialized or New Item:
        # if not self.item or self.item.id != item.id:
        # 	# logger.info(f'Uninitialized or New Item ({item.id})')
        # 	if type(item) == Entry:
        # 		# New Entry: Render preview and update filename label
        # 		filepath = os.path.normpath(f'{self.lib.library_dir}/{item.path}/{item.filename}')
        # 		window_title = filepath
        # 		ratio: float = self.devicePixelRatio()
        # 		self.thumb_renderer.render(time.time(), filepath, (512, 512), ratio,update_on_ratio_change=True)
        # 		self.file_label.setText("\u200b".join(filepath))

        # 		# TODO: Deal with this later.
        # 		# https://stackoverflow.com/questions/64252654/pyqt5-drag-and-drop-into-system-file-explorer-with-delayed-encoding
        # 		# https://doc.qt.io/qtforpython-5/PySide2/QtCore/QMimeData.html#more
        # 		# drag = QDrag(self.preview_img)
        # 		# mime = QMimeData()
        # 		# mime.setUrls([filepath])
        # 		# drag.setMimeData(mime)
        # 		# drag.exec_(Qt.DropAction.CopyAction)

        # 		try:
        # 			self.preview_img.clicked.disconnect()
        # 		except RuntimeError:
        # 			pass
        # 		self.preview_img.clicked.connect(
        # 			lambda checked=False, filepath=filepath: open_file(filepath))

        # 		for i, f in enumerate(item.fields):
        # 			self.write_container(item, i, f)

        # 		self.item = item

        # 		# try:
        # 		# 	self.tags_updated.disconnect()
        # 		# except RuntimeError:
        # 		# 	pass
        # 		# if self.tag_callback:
        # 		# 	# logger.info(f'[UPDATE CONTAINER] Updating Callback for {item.id}: {self.tag_callback}')
        # 		# 	self.tags_updated.connect(self.tag_callback)

        # # Initialized, Updating:
        # elif self.item and self.item.id == item.id:
        # 	# logger.info(f'Initialized Item, Updating! ({item.id})')
        # 	for i, f in enumerate(item.fields):
        # 		self.write_container(item, i, f)

        # # Hide leftover containers
        # if len(self.containers) > len(self.item.fields):
        # 	for i, c in enumerate(self.containers):
        # 		if i > (len(self.item.fields) - 1):
        # 			c.setHidden(True)

        self.setWindowTitle(window_title)
        self.show()

    def set_tags_updated_slot(self, slot: object):
        """
        Replacement for tag_callback.
        """
        try:
            self.tags_updated.disconnect()
        except RuntimeError:
            pass
        logger.info("[UPDATE CONTAINER] Setting tags updated slot")
        self.tags_updated.connect(slot)

    # def write_container(self, item:Union[Entry, Collation, Tag], index, field):
    def write_container(self, index, field, mixed=False):
        """Updates/Creates data for a FieldContainer."""
        # logger.info(f'[ENTRY PANEL] WRITE CONTAINER')
        # Remove 'Add Field' button from scroll_layout, to be re-added later.
        self.scroll_layout.takeAt(self.scroll_layout.count() - 1).widget()
        container: FieldContainer = None
        if len(self.containers) < (index + 1):
            container = FieldContainer()
            self.containers.append(container)
            self.scroll_layout.addWidget(container)
        else:
            container = self.containers[index]
            # container.inner_layout.removeItem(container.inner_layout.itemAt(1))
            # container.setHidden(False)
        if self.lib.get_field_attr(field, "type") == "tag_box":
            # logger.info(f'WRITING TAGBOX FOR ITEM {item.id}')
            container.set_title(self.lib.get_field_attr(field, "name"))
            # container.set_editable(False)
            container.set_inline(False)
            title = f"{self.lib.get_field_attr(field, 'name')} (Tag Box)"
            if not mixed:
                item = self.lib.get_entry(
                    self.selected[0][1]
                )  # TODO TODO TODO: TEMPORARY
                if type(container.get_inner_widget()) == TagBoxWidget:
                    inner_container: TagBoxWidget = container.get_inner_widget()
                    inner_container.set_item(item)
                    inner_container.set_tags(self.lib.get_field_attr(field, "content"))
                    try:
                        inner_container.updated.disconnect()
                    except RuntimeError:
                        pass
                    # inner_container.updated.connect(lambda f=self.filepath, i=item: self.write_container(item, index, field))
                else:
                    inner_container = TagBoxWidget(
                        item,
                        title,
                        index,
                        self.lib,
                        self.lib.get_field_attr(field, "content"),
                        self.driver,
                    )

                    container.set_inner_widget(inner_container)
                inner_container.field = field
                inner_container.updated.connect(
                    lambda: (
                        self.write_container(index, field),
                        self.tags_updated.emit(),
                    )
                )
                # if type(item) == Entry:
                # NOTE: Tag Boxes have no Edit Button (But will when you can convert field types)
                # f'Are you sure you want to remove this \"{self.lib.get_field_attr(field, "name")}\" field?'
                # container.set_remove_callback(lambda: (self.lib.get_entry(item.id).fields.pop(index), self.update_widgets(item)))
                prompt = f'Are you sure you want to remove this "{self.lib.get_field_attr(field, "name")}" field?'

                # TODO: Reuse the callback
                # NOTE: Not a lambda as it was previously due to ruff complaining about lambdas being assigned to variables
                def callback():
                    return self.remove_field(field), self.update_widgets()

                container.set_remove_callback(
                    lambda: self.remove_message_box(prompt=prompt, callback=callback)
                )
                container.set_copy_callback(None)
                container.set_edit_callback(None)
            else:
                text = "<i>Mixed Data</i>"
                title = f"{self.lib.get_field_attr(field, 'name')} (Wacky Tag Box)"
                inner_container = TextWidget(title, text)
                container.set_inner_widget(inner_container)
                container.set_copy_callback(None)
                container.set_edit_callback(None)
                container.set_remove_callback(None)

            self.tags_updated.emit()
            # self.dynamic_widgets.append(inner_container)
        elif self.lib.get_field_attr(field, "type") in "text_line":
            # logger.info(f'WRITING TEXTLINE FOR ITEM {item.id}')
            container.set_title(self.lib.get_field_attr(field, "name"))
            # container.set_editable(True)
            container.set_inline(False)
            # Normalize line endings in any text content.
            if not mixed:
                text = self.lib.get_field_attr(field, "content").replace("\r", "\n")
            else:
                text = "<i>Mixed Data</i>"
            title = f"{self.lib.get_field_attr(field, 'name')} (Text Line)"
            inner_container = TextWidget(title, text)
            container.set_inner_widget(inner_container)
            # if type(item) == Entry:
            if not mixed:
                modal = PanelModal(
                    EditTextLine(self.lib.get_field_attr(field, "content")),
                    title=title,
                    window_title=f'Edit {self.lib.get_field_attr(field, "name")}',
                    save_callback=(
                        lambda content: (
                            self.update_field(field, content),
                            self.update_widgets(),
                        )
                    ),
                )
                container.set_edit_callback(modal.show)
                prompt = f'Are you sure you want to remove this "{self.lib.get_field_attr(field, "name")}" field?'

                def callback():
                    return self.remove_field(field), self.update_widgets()

                container.set_remove_callback(
                    lambda: self.remove_message_box(prompt=prompt, callback=callback)
                )
                container.set_copy_callback(None)
            else:
                container.set_edit_callback(None)
                container.set_copy_callback(None)
                container.set_remove_callback(None)
            # container.set_remove_callback(lambda: (self.lib.get_entry(item.id).fields.pop(index), self.update_widgets(item)))

        elif self.lib.get_field_attr(field, "type") in "text_box":
            # logger.info(f'WRITING TEXTBOX FOR ITEM {item.id}')
            container.set_title(self.lib.get_field_attr(field, "name"))
            # container.set_editable(True)
            container.set_inline(False)
            # Normalize line endings in any text content.
            if not mixed:
                text = self.lib.get_field_attr(field, "content").replace("\r", "\n")
            else:
                text = "<i>Mixed Data</i>"
            title = f"{self.lib.get_field_attr(field, 'name')} (Text Box)"
            inner_container = TextWidget(title, text)
            container.set_inner_widget(inner_container)
            # if type(item) == Entry:
            if not mixed:
                container.set_copy_callback(None)
                modal = PanelModal(
                    EditTextBox(self.lib.get_field_attr(field, "content")),
                    title=title,
                    window_title=f'Edit {self.lib.get_field_attr(field, "name")}',
                    save_callback=(
                        lambda content: (
                            self.update_field(field, content),
                            self.update_widgets(),
                        )
                    ),
                )
                container.set_edit_callback(modal.show)
                prompt = f'Are you sure you want to remove this "{self.lib.get_field_attr(field, "name")}" field?'

                def callback():
                    return self.remove_field(field), self.update_widgets()

                container.set_remove_callback(
                    lambda: self.remove_message_box(prompt=prompt, callback=callback)
                )
            else:
                container.set_edit_callback(None)
                container.set_copy_callback(None)
                container.set_remove_callback(None)
        elif self.lib.get_field_attr(field, "type") == "collation":
            # logger.info(f'WRITING COLLATION FOR ITEM {item.id}')
            container.set_title(self.lib.get_field_attr(field, "name"))
            # container.set_editable(True)
            container.set_inline(False)
            collation = self.lib.get_collation(
                self.lib.get_field_attr(field, "content")
            )
            title = f"{self.lib.get_field_attr(field, 'name')} (Collation)"
            text = f"{collation.title} ({len(collation.e_ids_and_pages)} Items)"
            if len(self.selected) == 1:
                text += f" - Page {collation.e_ids_and_pages[[x[0] for x in collation.e_ids_and_pages].index(self.selected[0][1])][1]}"
            inner_container = TextWidget(title, text)
            container.set_inner_widget(inner_container)
            # if type(item) == Entry:
            container.set_copy_callback(None)
            # container.set_edit_callback(None)
            # container.set_remove_callback(lambda: (self.lib.get_entry(item.id).fields.pop(index), self.update_widgets(item)))
            prompt = f'Are you sure you want to remove this "{self.lib.get_field_attr(field, "name")}" field?'

            def callback():
                return self.remove_field(field), self.update_widgets()

            container.set_remove_callback(
                lambda: self.remove_message_box(prompt=prompt, callback=callback)
            )
        elif self.lib.get_field_attr(field, "type") == "datetime":
            # logger.info(f'WRITING DATETIME FOR ITEM {item.id}')
            if not mixed:
                try:
                    container.set_title(self.lib.get_field_attr(field, "name"))
                    # container.set_editable(False)
                    container.set_inline(False)
                    # TODO: Localize this and/or add preferences.
                    date = dt.strptime(
                        self.lib.get_field_attr(field, "content"), "%Y-%m-%d %H:%M:%S"
                    )
                    title = f"{self.lib.get_field_attr(field, 'name')} (Date)"
                    inner_container = TextWidget(title, date.strftime("%D - %r"))
                    container.set_inner_widget(inner_container)
                except Exception:
                    container.set_title(self.lib.get_field_attr(field, "name"))
                    # container.set_editable(False)
                    container.set_inline(False)
                    title = f"{self.lib.get_field_attr(field, 'name')} (Date) (Unknown Format)"
                    inner_container = TextWidget(
                        title, str(self.lib.get_field_attr(field, "content"))
                    )
                # if type(item) == Entry:
                container.set_copy_callback(None)
                container.set_edit_callback(None)
                # container.set_remove_callback(lambda: (self.lib.get_entry(item.id).fields.pop(index), self.update_widgets(item)))
                prompt = f'Are you sure you want to remove this "{self.lib.get_field_attr(field, "name")}" field?'

                def callback():
                    return self.remove_field(field), self.update_widgets()

                container.set_remove_callback(
                    lambda: self.remove_message_box(prompt=prompt, callback=callback)
                )
            else:
                text = "<i>Mixed Data</i>"
                title = f"{self.lib.get_field_attr(field, 'name')} (Wacky Date)"
                inner_container = TextWidget(title, text)
                container.set_inner_widget(inner_container)
                container.set_copy_callback(None)
                container.set_edit_callback(None)
                container.set_remove_callback(None)
        else:
            # logger.info(f'[ENTRY PANEL] Unknown Type: {self.lib.get_field_attr(field, "type")}')
            container.set_title(self.lib.get_field_attr(field, "name"))
            # container.set_editable(False)
            container.set_inline(False)
            title = f"{self.lib.get_field_attr(field, 'name')} (Unknown Field Type)"
            inner_container = TextWidget(
                title, str(self.lib.get_field_attr(field, "content"))
            )
            container.set_inner_widget(inner_container)
            # if type(item) == Entry:
            container.set_copy_callback(None)
            container.set_edit_callback(None)
            # container.set_remove_callback(lambda: (self.lib.get_entry(item.id).fields.pop(index), self.update_widgets(item)))
            prompt = f'Are you sure you want to remove this "{self.lib.get_field_attr(field, "name")}" field?'

            def callback():
                return self.remove_field(field), self.update_widgets()

            # callback = lambda: (self.lib.get_entry(item.id).fields.pop(index), self.update_widgets())
            container.set_remove_callback(
                lambda: self.remove_message_box(prompt=prompt, callback=callback)
            )
        container.edit_button.setHidden(True)
        container.setHidden(False)
        self.place_add_field_button()

    def remove_field(self, field: dict):
        """Removes a field from all selected Entries, given a field object."""
        for item_pair in self.selected:
            if item_pair[0] == ItemType.ENTRY:
                entry = self.lib.get_entry(item_pair[1])
                try:
                    index = entry.fields.index(field)
                    updated_badges = False
                    if 8 in entry.fields[index].keys() and (
                        1 in entry.fields[index][8] or 0 in entry.fields[index][8]
                    ):
                        updated_badges = True
                    # TODO: Create a proper Library/Entry method to manage fields.
                    entry.fields.pop(index)
                    if updated_badges:
                        self.driver.update_badges()
                except ValueError:
                    # TODO: Decide whether this should be logged as info or an error
                    logger.info(
                        f"[PREVIEW PANEL][ERROR?] Tried to remove field from Entry ({entry.id}) that never had it"
                    )
                    pass

    def update_field(self, field: dict, content):
        """Removes a field from all selected Entries, given a field object."""
        field = dict(field)
        for item_pair in self.selected:
            if item_pair[0] == ItemType.ENTRY:
                entry = self.lib.get_entry(item_pair[1])
                try:
                    logger.info(field)
                    index = entry.fields.index(field)
                    self.lib.update_entry_field(entry.id, index, content, "replace")
                except ValueError:
                    logger.error(
                        f"[PREVIEW PANEL] Tried to update field from Entry ({entry.id}) that never had it"
                    )
                    pass

    def remove_message_box(self, prompt: str, callback: typing.Callable) -> None:
        remove_mb = QMessageBox()
        remove_mb.setText(prompt)
        remove_mb.setWindowTitle("Remove Field")
        remove_mb.setIcon(QMessageBox.Icon.Warning)
        cancel_button = remove_mb.addButton(
            "&Cancel", QMessageBox.ButtonRole.DestructiveRole
        )
        remove_mb.addButton("&Remove", QMessageBox.ButtonRole.RejectRole)
        # remove_mb.setStandardButtons(QMessageBox.StandardButton.Cancel)
        remove_mb.setDefaultButton(cancel_button)
        result = remove_mb.exec_()
        # logger.info(result)
        if result == 1:
            callback()
