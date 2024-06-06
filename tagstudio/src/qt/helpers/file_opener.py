# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel
from src.core.logging import get_logger

logger = get_logger(__name__)


def open_file(path: str | Path, file_manager: bool = False) -> None:
    """Open a file in the default application or file explorer.

    Args:
            path (str): The path to the file to open.
            file_manager (bool, optional): Whether to open the file in the file manager (e.g. Finder on macOS).
                    Defaults to False.
    """

    if isinstance(path, Path):
        _path = str(path.resolve().absolute())
    else:
        _path = str(path)

    logger.info(f"Opening file: {_path}")
    if not os.path.exists(_path):
        logger.error(f"File not found: {_path}")
        return

    try:
        if sys.platform == "win32":
            normpath = os.path.normpath(_path)
            if file_manager:
                command_name = "explorer"
                command_args = '/select,"' + normpath + '"'
                # For some reason, if the args are passed in a list, this will error when the path has spaces, even while surrounded in double quotes
                subprocess.Popen(
                    command_name + command_args,
                    shell=True,
                    close_fds=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    | subprocess.CREATE_BREAKAWAY_FROM_JOB,
                )
            else:
                command_name = "start"
                # first parameter is for title, NOT filepath
                command_args = ["", normpath]
                subprocess.Popen(
                    [command_name] + command_args,
                    shell=True,
                    close_fds=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    | subprocess.CREATE_BREAKAWAY_FROM_JOB,
                )
        else:
            if sys.platform == "darwin":
                command_name = "open"
                command_args = [_path]
                if file_manager:
                    # will reveal in Finder
                    command_args.append("-R")
            else:
                if file_manager:
                    command_name = "dbus-send"
                    # might not be guaranteed to launch default?
                    command_args = [
                        "--session",
                        "--dest=org.freedesktop.FileManager1",
                        "--type=method_call",
                        "/org/freedesktop/FileManager1",
                        "org.freedesktop.FileManager1.ShowItems",
                        f"array:string:file://{_path}",
                        "string:",
                    ]
                else:
                    command_name = "xdg-open"
                    command_args = [_path]
            command = shutil.which(command_name)
            if command is not None:
                subprocess.Popen([command] + command_args, close_fds=True)
            else:
                logger.info(f"Could not find {command_name} on system PATH")
    except Exception:
        logger.exception(f"Error opening a file at {_path}")


class FileOpenerHelper:
    def __init__(self, filepath: str | Path):
        """Initialize the FileOpenerHelper.

        Args:
                filepath (str): The path to the file to open.
        """
        self.filepath = str(filepath)

    def set_filepath(self, filepath: str | Path):
        """Set the filepath to open.

        Args:
                filepath (str): The path to the file to open.
        """
        self.filepath = str(filepath)

    def open_file(self):
        """Open the file in the default application."""
        open_file(self.filepath)

    def open_explorer(self):
        """Open the file in the default file explorer."""
        open_file(self.filepath, file_manager=True)


class FileOpenerLabel(QLabel):
    def __init__(self, text, parent=None):
        """Initialize the FileOpenerLabel.

        Args:
                text (str): The text to display.
                parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(text, parent)

    def setFilePath(self, filepath):
        """Set the filepath to open.

        Args:
                filepath (str): The path to the file to open.
        """
        self.filepath = filepath

    def mousePressEvent(self, event):
        """Handle mouse press events.

        On a left click, open the file in the default file explorer. On a right click, show a context menu.

        Args:
                event (QMouseEvent): The mouse press event.
        """
        super().mousePressEvent(event)

        if event.button() == Qt.LeftButton:
            opener = FileOpenerHelper(self.filepath)
            opener.open_explorer()
        elif event.button() == Qt.RightButton:
            # Show context menu
            pass
