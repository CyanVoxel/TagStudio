# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio


import math
import typing

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from src.core.library import Library, Tag
from src.core.logging import get_logger
from src.core.palette import ColorType, get_tag_color
from src.qt.flowlayout import FlowLayout

# Only import for type checking/autocompletion, will not be imported at runtime.
if typing.TYPE_CHECKING:
    from src.qt.ts_qt import QtDriver

logger = get_logger(__name__)


def folders_to_tags(library: Library):
    logger.info("Converting folders to Tags")
    tree: dict = dict(dirs={})

    def add_tag_to_tree(items: list[Tag]):
        branch = tree
        for tag in items:
            if tag.name not in branch["dirs"]:
                branch["dirs"][tag.name] = dict(dirs={}, tag=tag)
            branch = branch["dirs"][tag.name]

    def add_folders_to_tree(items: list[str]) -> Tag:
        branch: dict = tree
        for folder in items:
            if folder not in branch["dirs"]:
                new_tag = Tag(
                    -1,
                    folder,
                    "",
                    [],
                    ([branch["tag"].id] if "tag" in branch else []),
                    "",
                )
                library.add_tag_to_library(new_tag)
                branch["dirs"][folder] = dict(dirs={}, tag=new_tag)
            branch = branch["dirs"][folder]
        return branch["tag"]

    for tag in library.tags:
        reversed_tag = reverse_tag(library, tag, None)
        add_tag_to_tree(reversed_tag)

    for entry in library.entries:
        folders = list(entry.path.parts)
        if len(folders) == 1 and folders[0] == "":
            continue
        tag = add_folders_to_tree(folders)
        if tag:
            if not entry.has_tag(library, tag.id):
                entry.add_tag(library, tag.id, 6)

    logger.info("Done")


def reverse_tag(library: Library, tag: Tag, list: list[Tag]) -> list[Tag]:
    if list is not None:
        list.append(tag)
    else:
        list = [tag]

    if len(tag.subtag_ids) == 0:
        list.reverse()
        return list
    else:
        for subtag_id in tag.subtag_ids:
            subtag = library.get_tag(subtag_id)
        return reverse_tag(library, subtag, list)


# =========== UI ===========


def generate_preview_data(library: Library):
    tree: dict = dict(dirs={}, files=[])

    def add_tag_to_tree(items: list[Tag]):
        branch: dict = tree
        for tag in items:
            if tag.name not in branch["dirs"]:
                branch["dirs"][tag.name] = dict(dirs={}, tag=tag, files=[])
            branch = branch["dirs"][tag.name]

    def add_folders_to_tree(items: list[str]) -> dict:
        branch: dict = tree
        for folder in items:
            if folder not in branch["dirs"]:
                new_tag = Tag(-1, folder, "", [], [], "green")
                branch["dirs"][folder] = dict(dirs={}, tag=new_tag, files=[])
            branch = branch["dirs"][folder]
        return branch

    for tag in library.tags:
        reversed_tag = reverse_tag(library, tag, None)
        add_tag_to_tree(reversed_tag)

    for entry in library.entries:
        folders = list(entry.path.parts)
        if len(folders) == 1 and folders[0] == "":
            continue
        branch = add_folders_to_tree(folders)
        if branch:
            field_indexes = library.get_field_index_in_entry(entry, 6)
            has_tag = False
            for index in field_indexes:
                content = library.get_field_attr(entry.fields[index], "content")
                for tag_id in content:
                    tag = library.get_tag(tag_id)
                    if tag.name == branch["tag"].name:
                        has_tag = True
                        break
            if not has_tag:
                branch["files"].append(entry.filename)

    def cut_branches_adding_nothing(branch: dict):
        folders = set(branch["dirs"].keys())
        for folder in folders:
            cut = cut_branches_adding_nothing(branch["dirs"][folder])
            if cut:
                branch["dirs"].pop(folder)

        if "tag" not in branch:
            return
        if branch["tag"].id == -1 or len(branch["files"]) > 0:  # Needs to be first
            return False
        if len(branch["dirs"].keys()) == 0:
            return True

    cut_branches_adding_nothing(tree)

    return tree


class FoldersToTagsModal(QWidget):
    # done = Signal(int)
    def __init__(self, library: "Library", driver: "QtDriver"):
        super().__init__()
        self.library = library
        self.driver = driver
        self.count = -1
        self.filename = ""

        self.setWindowTitle("Create Tags From Folders")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumSize(640, 640)
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(6, 6, 6, 6)

        self.title_widget = QLabel()
        self.title_widget.setObjectName("title")
        self.title_widget.setWordWrap(True)
        self.title_widget.setStyleSheet(
            "font-weight:bold;" "font-size:14px;" "padding-top: 6px"
        )
        self.title_widget.setText("Create Tags From Folders")
        self.title_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.desc_widget = QLabel()
        self.desc_widget.setObjectName("descriptionLabel")
        self.desc_widget.setWordWrap(True)
        self.desc_widget.setText(
            """Creates tags based on your folder structure and applies them to your entries.\n The structure below shows all the tags that will be created and what entries they will be applied to."""
        )
        self.desc_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.open_close_button_w = QWidget()
        self.open_close_button_layout = QHBoxLayout(self.open_close_button_w)

        self.open_all_button = QPushButton()
        self.open_all_button.setText("Open All")
        self.open_all_button.clicked.connect(lambda: self.set_all_branches(False))
        self.close_all_button = QPushButton()
        self.close_all_button.setText("Close All")
        self.close_all_button.clicked.connect(lambda: self.set_all_branches(True))

        self.open_close_button_layout.addWidget(self.open_all_button)
        self.open_close_button_layout.addWidget(self.close_all_button)

        self.scroll_contents = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_contents)
        self.scroll_layout.setContentsMargins(6, 0, 6, 0)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area = QScrollArea()
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShadow(QFrame.Shadow.Plain)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidget(self.scroll_contents)

        self.apply_button = QPushButton()
        self.apply_button.setText("&Apply")
        self.apply_button.setMinimumWidth(100)
        self.apply_button.clicked.connect(self.on_apply)

        self.showEvent = self.on_open  # type: ignore

        self.root_layout.addWidget(self.title_widget)
        self.root_layout.addWidget(self.desc_widget)
        self.root_layout.addWidget(self.open_close_button_w)
        self.root_layout.addWidget(self.scroll_area)
        self.root_layout.addWidget(
            self.apply_button, alignment=Qt.AlignmentFlag.AlignCenter
        )

    def on_apply(self, event):
        folders_to_tags(self.library)
        self.close()
        self.driver.preview_panel.update_widgets()

    def on_open(self, event):
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.itemAt(i).widget().setParent(None)

        data = generate_preview_data(self.library)

        for folder in data["dirs"].values():
            test = TreeItem(folder, None)
            self.scroll_layout.addWidget(test)

    def set_all_branches(self, hidden: bool):
        for i in reversed(range(self.scroll_layout.count())):
            child = self.scroll_layout.itemAt(i).widget()
            if type(child) == TreeItem:
                child.set_all_branches(hidden)


class TreeItem(QWidget):
    def __init__(self, data: dict, parentTag: Tag):
        super().__init__()

        self.setStyleSheet("QLabel{font-size: 13px}")

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(20, 0, 0, 0)
        self.root_layout.setSpacing(1)

        self.test = QWidget()
        self.root_layout.addWidget(self.test)

        self.tag_layout = FlowLayout(self.test)

        self.label = QLabel()
        self.tag_layout.addWidget(self.label)
        self.tag_widget = ModifiedTagWidget(data["tag"], parentTag)
        self.tag_widget.bg_button.clicked.connect(lambda: self.hide_show())
        self.tag_layout.addWidget(self.tag_widget)

        self.children_widget = QWidget()
        self.children_layout = QVBoxLayout(self.children_widget)
        self.root_layout.addWidget(self.children_widget)

        self.populate(data)

    def hide_show(self):
        self.children_widget.setHidden(not self.children_widget.isHidden())
        self.label.setText(">" if self.children_widget.isHidden() else "v")

    def populate(self, data: dict):
        for folder in data["dirs"].values():
            item = TreeItem(folder, data["tag"])
            self.children_layout.addWidget(item)
        for file in data["files"]:
            label = QLabel()
            label.setText("    ->  " + file)
            self.children_layout.addWidget(label)

        if len(data["files"]) == 0 and len(data["dirs"].values()) == 0:
            self.hide_show()
        else:
            self.label.setText("v")

    def set_all_branches(self, hidden: bool):
        for i in reversed(range(self.children_layout.count())):
            child = self.children_layout.itemAt(i).widget()
            if type(child) == TreeItem:
                child.set_all_branches(hidden)

        self.children_widget.setHidden(hidden)
        self.label.setText(">" if self.children_widget.isHidden() else "v")


class ModifiedTagWidget(
    QWidget
):  # Needed to be modified because the original searched the display name in the library where it wasn't added yet
    def __init__(self, tag: Tag, parentTag: Tag) -> None:
        super().__init__()
        self.tag = tag

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.base_layout = QVBoxLayout(self)
        self.base_layout.setObjectName("baseLayout")
        self.base_layout.setContentsMargins(0, 0, 0, 0)

        self.bg_button = QPushButton(self)
        self.bg_button.setFlat(True)
        if parentTag is not None:
            text = f"{tag.name} ({parentTag.name})".replace("&", "&&")
        else:
            text = tag.name.replace("&", "&&")
        self.bg_button.setText(text)
        self.bg_button.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

        self.inner_layout = QHBoxLayout()
        self.inner_layout.setObjectName("innerLayout")
        self.inner_layout.setContentsMargins(2, 2, 2, 2)
        self.bg_button.setLayout(self.inner_layout)
        self.bg_button.setMinimumSize(math.ceil(22 * 1.5), 22)

        self.bg_button.setStyleSheet(
            f"QPushButton{{"
            f"background: {get_tag_color(ColorType.PRIMARY, tag.color)};"
            f"color: {get_tag_color(ColorType.TEXT, tag.color)};"
            f"font-weight: 600;"
            f"border-color:{get_tag_color(ColorType.BORDER, tag.color)};"
            f"border-radius: 6px;"
            f"border-style:inset;"
            f"border-width: {math.ceil(1*self.devicePixelRatio())}px;"
            f"padding-right: 4px;"
            f"padding-bottom: 1px;"
            f"padding-left: 4px;"
            f"font-size: 13px"
            f"}}"
            f"QPushButton::hover{{"
            f"border-color:{get_tag_color(ColorType.LIGHT_ACCENT, tag.color)};"
            f"}}"
        )

        self.base_layout.addWidget(self.bg_button)
        self.setMinimumSize(50, 20)
