# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio

"""The core classes and methods of TagStudio."""

from src.alt_core.library import Library


class TagStudioCore:
    """
    Instantiate this to establish a TagStudio session.
    Holds all TagStudio session data and provides methods to manage it.
    """

    def __init__(self):
        self.lib: Library = Library()
