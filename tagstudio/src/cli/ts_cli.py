# type: ignore
# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio

"""DEPRECIATED: A basic CLI driver for TagStudio."""

import datetime
import math

# from multiprocessing import Value
import os

# import subprocess
import sys
import time
import traceback

# import climage
# import click
from datetime import datetime as dt

# import pillow_avif
from pathlib import Path

import cv2
from PIL import Image, ImageChops, UnidentifiedImageError
from PIL.Image import DecompressionBombError
from src.core.constants import (
    BOX_FIELDS,
    COLLAGE_FOLDER_NAME,
    DOC_TYPES,
    IMAGE_TYPES,
    TAG_COLORS,
    TEXT_FIELDS,
    TS_FOLDER_NAME,
    VERSION,
    VERSION_BRANCH,
    VIDEO_TYPES,
)
from src.core.library import ItemType, Tag
from src.core.ts_core import TagStudioCore
from src.core.utils.web import strip_web_protocol
from src.qt.helpers.file_opener import open_file

WHITE_FG = "\033[37m"
WHITE_BG = "\033[47m"
BRIGHT_WHITE_FG = "\033[97m"
BRIGHT_WHITE_BG = "\033[107m"
BLACK_FG = "\033[30m"
BRIGHT_CYAN_FG = "\033[96m"
BRIGHT_CYAN_BG = "\033[106m"
BRIGHT_MAGENTA_FG = "\033[95m"
BRIGHT_MAGENTA_BG = "\033[105m"
BRIGHT_GREEN_FG = "\033[92m"
BRIGHT_GREEN_BG = "\033[102m"
YELLOW_FG = "\033[33m"
YELLOW_BG = "\033[43m"
BRIGHT_YELLOW_FG = "\033[93m"
BRIGHT_YELLOW_BG = "\033[103m"
RED_BG = "\033[41m"
BRIGHT_RED_FG = "\033[91m"
BRIGHT_RED_BG = "\033[101m"
MAGENTA_FG = "\033[35m"
MAGENTA_BG = "\033[45m"
RESET = "\033[0m"
SAVE_SCREEN = "\033[?1049h\033[?47h\033[H"
RESTORE_SCREEN = "\033[?47l\033[?1049l"

ERROR = f"{RED_BG}{BRIGHT_WHITE_FG}[ERROR]{RESET}"
WARNING = f"{RED_BG}{BRIGHT_WHITE_FG}[WARNING]{RESET}"
INFO = f"{BRIGHT_CYAN_BG}{BLACK_FG}[INFO]{RESET}"


def clear():
    """Clears the terminal screen."""

    # Windows
    if os.name == "nt":
        _ = os.system("cls")

    # Unix
    else:
        _ = os.system("clear")


class CliDriver:
    """A basic CLI driver for TagStudio."""

    def __init__(self, core, args):
        self.core: TagStudioCore = core
        self.lib = self.core.lib
        self.filtered_entries: list[tuple[ItemType, int]] = []
        self.args = args
        self.first_open: bool = True
        self.first_browse: bool = True
        self.is_missing_count_init: bool = False
        self.is_new_file_count_init: bool = False
        self.is_dupe_entry_count_init: bool = False
        self.is_dupe_file_count_init: bool = False

        self.external_preview_size: tuple[int, int] = (960, 960)
        epd_path = (
            Path(__file__).parents[2] / "resources/cli/images/external_preview.png"
        )
        self.external_preview_default: Image = (
            Image.open(epd_path)
            if epd_path.exists()
            else Image.new(mode="RGB", size=(self.external_preview_size))
        )
        self.external_preview_default.thumbnail(self.external_preview_size)
        epb_path = Path(__file__).parents[3] / "resources/cli/images/no_preview.png"
        self.external_preview_broken: Image = (
            Image.open(epb_path)
            if epb_path.exists()
            else Image.new(mode="RGB", size=(self.external_preview_size))
        )
        self.external_preview_broken.thumbnail(self.external_preview_size)

        self.branch: str = (" (" + VERSION_BRANCH + ")") if VERSION_BRANCH else ""
        self.base_title: str = f"TagStudio {VERSION}{self.branch} - CLI Mode"
        self.title_text: str = self.base_title
        self.buffer = {}

    def start(self):
        """Enters the CLI."""
        print(SAVE_SCREEN, end="")
        try:
            self.scr_main_menu()
        except SystemExit:
            # self.cleanup_before_exit()
            # sys.exit()
            self.exit(save=False, backup=False)
        except KeyboardInterrupt:
            # traceback.print_exc()
            print("\nForce Quitting TagStudio...")
            # if self.lib and self.lib.library_dir:
            # 	self.backup_library()
            # self.cleanup_before_exit()
            # sys.exit()
            self.exit(save=False, backup=False)
        except Exception:
            traceback.print_exc()
            print("\nPress Enter to Continue...")
            input()
            # if self.lib and self.lib.library_dir:
            # 	self.backup_library()
            # self.cleanup_before_exit()
            # sys.exit()
            self.exit(save=False, backup=True)
        # except:
        # 	print(
        # 		'\nAn Unknown Exception in TagStudio has Occurred. Press Enter to Continue...')
        # 	input()
        # 	# if self.lib and self.lib.library_dir:
        # 	# 	self.backup_library()
        # 	# self.cleanup_before_exit()
        # 	# sys.exit()
        # 	self.quit(save=False, backup=True)

    def cleanup_before_exit(self, restore_screen=True):
        """Things do be done on application exit."""
        try:
            if self.args.external_preview:
                self.close_external_preview()
        except Exception:
            traceback.print_exc()
            print("\nCrashed on Cleanup! This is unusual... Press Enter to Continue...")
            input()
            self.backup_library()

        if restore_screen:
            print(f"{RESET}{RESTORE_SCREEN}", end="")

    def exit(self, save: bool, backup: bool):
        """Exists TagStudio, and optionally saves and/or backs up data."""

        if save:
            print(f"{INFO} Saving Library to disk...")
            self.save_library(display_message=False)
        if backup:
            print(f"{INFO} Saving Library changes to Backups folder...")
            self.backup_library(display_message=False)

        self.cleanup_before_exit()

        try:
            sys.exit()
        except SystemExit:
            sys.exit()

    def format_title(self, str, color=f"{BRIGHT_WHITE_FG}{MAGENTA_BG}") -> str:
        """Formats a string with title formatting."""
        # Floating Pill (Requires NerdFont)
        # return f'◀ {str} ▶'.center(os.get_terminal_size()[0], " ").replace('◀', '\033[96m\033[0m\033[30m\033[106m').replace('▶', '\033[0m\033[96m\033[0m')
        # Solid Background
        return f'{color}{str.center(os.get_terminal_size()[0], " ")[:os.get_terminal_size()[0]]}{RESET}'

    def format_subtitle(self, str, color=BRIGHT_CYAN_FG) -> str:
        """Formats a string with subtitle formatting."""
        return f'{color}{(" "+str+" ").center(os.get_terminal_size()[0], "═")[:os.get_terminal_size()[0]]}{RESET}'

    def format_h1(self, str, color=BRIGHT_MAGENTA_FG) -> str:
        """Formats a string with h1 formatting."""
        return f'{color}{("┫ "+str+" ┣").center(os.get_terminal_size()[0], "━")[:os.get_terminal_size()[0]]}{RESET}'

    def format_h2(self, str, color=BRIGHT_GREEN_FG) -> str:
        """Formats a string with h2 formatting."""
        return f'{color}{(" "+str+" ").center(os.get_terminal_size()[0], "·")[:os.get_terminal_size()[0]]}{RESET}'

    def get_file_color(self, ext: str):
        if ext.lower().replace(".", "", 1) == "gif":
            return BRIGHT_YELLOW_FG
        if ext.lower().replace(".", "", 1) in IMAGE_TYPES:
            return WHITE_FG
        elif ext.lower().replace(".", "", 1) in VIDEO_TYPES:
            return BRIGHT_CYAN_FG
        elif ext.lower().replace(".", "", 1) in DOC_TYPES:
            return BRIGHT_GREEN_FG
        else:
            return BRIGHT_WHITE_FG

    def get_tag_color(self, color: str) -> str:
        if color.lower() == "black":
            return "\033[48;2;17;16;24m" + "\033[38;2;183;182;190m"
            # return '\033[48;5;233m' + BRIGHT_WHITE_FG
        elif color.lower() == "dark gray":
            return "\033[48;2;36;35;42m" + "\033[38;2;189;189;191m"
            # return '\033[48;5;233m' + BRIGHT_WHITE_FG
        elif color.lower() == "gray":
            return "\033[48;2;83;82;90m" + "\033[38;2;203;202;210m"
            # return '\033[48;5;246m' + BRIGHT_WHITE_FG
        elif color.lower() == "light gray":
            return "\033[48;2;170;169;176m" + "\033[38;2;34;33;40m"
            # return '\033[48;5;250m' + BLACK_FG
        elif color.lower() == "white":
            return "\033[48;2;242;241;248m" + "\033[38;2;48;47;54m"
            # return '\033[48;5;231m' + '\033[38;5;244m'
        elif color.lower() == "light pink":
            return "\033[48;2;255;143;190m" + "\033[38;2;108;43;57m"
            # return '\033[48;5;212m' + '\033[38;5;88m'
        elif color.lower() == "pink":
            return "\033[48;2;250;74;117m" + "\033[38;2;91;23;35m"
            # return '\033[48;5;204m' + '\033[38;5;224m'
        elif color.lower() == "magenta":
            return "\033[48;2;224;43;132m" + "\033[38;2;91;13;54m"
            # return '\033[48;5;197m' + '\033[38;5;224m'
        elif color.lower() == "red":
            return "\033[48;2;226;44;60m" + "\033[38;2;68;13;18m"
            # return '\033[48;5;196m' + '\033[38;5;224m'
        elif color.lower() == "red orange":
            return "\033[48;2;232;55;38m" + "\033[38;2;97;18;11m"
            # return '\033[48;5;202m' + '\033[38;5;221m'
        elif color.lower() == "salmon":
            return "\033[48;2;246;88;72m" + "\033[38;2;111;27;22m"
            # return '\033[48;5;203m' + '\033[38;5;88m'
        elif color.lower() == "orange":
            return "\033[48;2;237;96;34m" + "\033[38;2;85;30;10m"
            # return '\033[48;5;208m' + '\033[38;5;229m'
        elif color.lower() == "yellow orange":
            return "\033[48;2;250;154;44m" + "\033[38;2;102;51;13m"
            # return '\033[48;5;214m' + '\033[38;5;88m'
        elif color.lower() == "yellow":
            return "\033[48;2;255;214;61m" + "\033[38;2;117;67;18m"
            # return '\033[48;5;220m' + '\033[38;5;88m'
        elif color.lower() == "mint":
            return "\033[48;2;74;237;144m" + "\033[38;2;22;79;62m"
            # return '\033[48;5;84m' + '\033[38;5;17m'
        elif color.lower() == "lime":
            return "\033[48;2;149;227;69m" + "\033[38;2;65;84;21m"
            # return '\033[48;5;154m' + '\033[38;5;17m'
        elif color.lower() == "light green":
            return "\033[48;2;138;236;125m" + "\033[38;2;44;85;38m"
            # return '\033[48;5;40m' + '\033[38;5;17m'
        elif color.lower() == "green":
            return "\033[48;2;40;187;72m" + "\033[38;2;13;56;40m"
            # return '\033[48;5;28m' + '\033[38;5;191m'
        elif color.lower() == "teal":
            return "\033[48;2;23;191;157m" + "\033[38;2;7;58;68m"
            # return '\033[48;5;36m' + '\033[38;5;17m'
        elif color.lower() == "cyan":
            return "\033[48;2;60;222;196m" + "\033[38;2;12;64;66m"
            # return '\033[48;5;50m' + '\033[38;5;17m'
        elif color.lower() == "light blue":
            return "\033[48;2;85;187;246m" + "\033[38;2;18;37;65m"
            # return '\033[48;5;75m' + '\033[38;5;17m'
        elif color.lower() == "blue":
            return "\033[48;2;59;99;240m" + "\033[38;2;158;192;249m"
            # return '\033[48;5;27m' + BRIGHT_WHITE_FG
        elif color.lower() == "blue violet":
            return "\033[48;2;93;88;241m" + "\033[38;2;149;176;249m"
            # return '\033[48;5;63m' + BRIGHT_WHITE_FG
        elif color.lower() == "violet":
            return "\033[48;2;120;60;239m" + "\033[38;2;187;157;247m"
            # return '\033[48;5;57m' + BRIGHT_WHITE_FG
        elif color.lower() == "purple":
            return "\033[48;2;155;79;240m" + "\033[38;2;73;24;98m"
            # return '\033[48;5;135m' + BRIGHT_WHITE_FG
        elif color.lower() == "peach":
            return "\033[48;2;241;198;156m" + "\033[38;2;97;63;47m"
            # return '\033[48;5;223m' + '\033[38;5;88m'
        elif color.lower() == "brown":
            return "\033[48;2;130;50;22m" + "\033[38;2;205;157;131m"
            # return '\033[48;5;130m' + BRIGHT_WHITE_FG
        elif color.lower() == "lavender":
            return "\033[48;2;173;142;239m" + "\033[38;2;73;43;101m"
            # return '\033[48;5;141m' + '\033[38;5;17m'
        elif color.lower() == "blonde":
            return "\033[48;2;239;198;100m" + "\033[38;2;109;70;30m"
            # return '\033[48;5;221m' + '\033[38;5;88m'
        elif color.lower() == "auburn":
            return "\033[48;2;161;50;32m" + "\033[38;2;217;138;127m"
            # return '\033[48;5;88m' + '\033[38;5;216m'
        elif color.lower() == "light brown":
            return "\033[48;2;190;91;45m" + "\033[38;2;76;41;14m"
        elif color.lower() == "dark brown":
            return "\033[48;2;76;35;21m" + "\033[38;2;183;129;113m"
            # return '\033[48;5;172m' + BRIGHT_WHITE_FG
        elif color.lower() == "cool gray":
            return "\033[48;2;81;87;104m" + "\033[38;2;158;161;195m"
            # return '\033[48;5;102m' + BRIGHT_WHITE_FG
        elif color.lower() == "warm gray":
            return "\033[48;2;98;88;80m" + "\033[38;2;192;171;146m"
            # return '\033[48;5;59m' + BRIGHT_WHITE_FG
        elif color.lower() == "olive":
            return "\033[48;2;76;101;46m" + "\033[38;2;180;193;122m"
            # return '\033[48;5;58m' + '\033[38;5;193m'
        elif color.lower() == "berry":
            return "\033[48;2;159;42;167m" + "\033[38;2;204;143;220m"
        else:
            return ""

    def copy_field_to_buffer(self, entry_field) -> None:
        """Copies an Entry Field object into the internal buffer."""
        self.buffer = dict(entry_field)

    def paste_field_from_buffer(self, entry_id) -> None:
        """Merges or adds the Entry Field object in the internal buffer to the Entry."""
        if self.buffer:
            # entry: Entry = self.lib.entries[entry_index]
            # entry = self.lib.get_entry(entry_id)
            field_id: int = self.lib.get_field_attr(self.buffer, "id")
            content = self.lib.get_field_attr(self.buffer, "content")

            # NOTE: This code is pretty much identical to the match_conditions code
            # found in the core. Could this be made generic? Especially for merging Entries.
            if self.lib.get_field_obj(int(field_id))["type"] == "tag_box":
                existing_fields: list[int] = self.lib.get_field_index_in_entry(
                    entry_id, field_id
                )
                if existing_fields:
                    self.lib.update_entry_field(
                        entry_id, existing_fields[0], content, "append"
                    )
                else:
                    self.lib.add_field_to_entry(entry_id, field_id)
                    self.lib.update_entry_field(entry_id, -1, content, "append")

            if self.lib.get_field_obj(int(field_id))["type"] in TEXT_FIELDS:
                if not self.lib.does_field_content_exist(entry_id, field_id, content):
                    self.lib.add_field_to_entry(entry_id, field_id)
                    self.lib.update_entry_field(entry_id, -1, content, "replace")

            # existing_fields: list[int] = self.lib.get_field_index_in_entry(entry_index, field_id)
            # if existing_fields:
            # 	self.lib.update_entry_field(entry_index, existing_fields[0], content, 'append')
            # else:
            # 	self.lib.add_field_to_entry(entry_index, field_id)
            # 	self.lib.update_entry_field(entry_index, -1, content, 'replace')

    def init_external_preview(self) -> None:
        """Initialized the external preview image file."""
        if self.lib and self.lib.library_dir:
            external_preview_path: Path = (
                self.lib.library_dir / TS_FOLDER_NAME / "external_preview.jpg"
            )
            if not external_preview_path.is_file():
                temp = self.external_preview_default
                temp.save(external_preview_path)
            open_file(external_preview_path)

    def set_external_preview_default(self) -> None:
        """Sets the external preview to its default image."""
        if self.lib and self.lib.library_dir:
            external_preview_path: Path = (
                self.lib.library_dir / TS_FOLDER_NAME / "external_preview.jpg"
            )
            if external_preview_path.is_file():
                temp = self.external_preview_default
                temp.save(external_preview_path)

    def set_external_preview_broken(self) -> None:
        """Sets the external preview image file to the 'broken' placeholder."""
        if self.lib and self.lib.library_dir:
            external_preview_path: Path = (
                self.lib.library_dir / TS_FOLDER_NAME / "external_preview.jpg"
            )
            if external_preview_path.is_file():
                temp = self.external_preview_broken
                temp.save(external_preview_path)

    def close_external_preview(self) -> None:
        """Destroys and closes the external preview image file."""
        if self.lib and self.lib.library_dir:
            external_preview_path: Path = (
                self.lib.library_dir / TS_FOLDER_NAME / "external_preview.jpg"
            )
            if external_preview_path.is_file():
                os.remove(external_preview_path)

    def scr_create_library(self, path=None):
        """Screen for creating a new TagStudio library."""

        subtitle = "Create Library"

        clear()
        print(f"{self.format_title(self.title_text)}")
        print(self.format_subtitle(subtitle))
        print("")

        if not path:
            print("Enter Library Folder Path: \n> ", end="")
            path = input()

        path = Path(path)

        if path.exists():
            print("")
            print(
                f'{INFO} Are you sure you want to create a new Library at "{path}"? (Y/N)\n> ',
                end="",
            )
            con = input().lower()
            if con == "y" or con == "yes":
                result = self.lib.create_library(path)
                if result == 0:
                    print(
                        f'{INFO} Created new TagStudio Library at: "{path}"\nPress Enter to Return to Main Menu...'
                    )
                    input()
                    # self.open_library(path)
                elif result == 1:
                    print(
                        f'{ERROR} Could not create Library. Path: "{path}" is pointing inside an existing TagStudio Folder.\nPress Enter to Return to Main Menu...'
                    )
                    input()
                elif result == 2:
                    print(
                        f'{ERROR} Could not write inside path: "{path}"\nPress Enter to Return to Main Menu...'
                    )
                    input()
        else:
            print(
                f'{ERROR} Invalid Path: "{path}"\nPress Enter to Return to Main Menu...'
            )
            input()
        # if Core.open_library(path) == 1:
        #     self.library_name = path
        #     self.scr_library_home()
        # else:
        #     print(f'[ERROR]: No existing TagStudio library found at \'{path}\'')
        #     self.scr_main_menu()

    def open_library(self, path):
        """Opens a TagStudio library."""

        return_code = self.lib.open_library(path)
        if return_code == 1:
            # self.lib = self.core.library
            if self.args.external_preview:
                self.init_external_preview()

            if len(self.lib.entries) <= 1000:
                print(
                    f"{INFO} Checking for missing files in Library '{self.lib.library_dir}'..."
                )
                self.lib.refresh_missing_files()
            # else:
            #     print(
            #         f'{INFO} Automatic missing file refreshing is turned off for large libraries (1,000+ Entries)')
            self.title_text: str = self.base_title + ""
            self.scr_library_home()
        else:
            clear()
            print(f"{ERROR} No existing TagStudio library found at '{path}'")
            self.scr_main_menu(clear_scr=False)

    def close_library(self, save=True):
        """
        Saves (by default) and clears the current Library as well as related operations.
        Does *not* direct the navigation back to the main menu, that's not my job.
        """
        if save:
            self.lib.save_library_to_disk()
        if self.args.external_preview:
            self.close_external_preview()
        self.lib.clear_internal_vars()

    def backup_library(self, display_message: bool = True) -> bool:
        """Saves a backup copy of the Library file to disk. Returns True if successful."""
        if self.lib and self.lib.library_dir:
            filename = self.lib.save_library_backup_to_disk()
            location = self.lib.library_dir / TS_FOLDER_NAME / "backups" / filename
            if display_message:
                print(f'{INFO} Backup of Library saved at "{location}".')
            return True
        return False

    def save_library(self, display_message: bool = True) -> bool:
        """Saves the Library file to disk. Returns True if successful."""
        if self.lib and self.lib.library_dir:
            self.lib.save_library_to_disk()
            if display_message:
                print(f"{INFO} Library saved to disk.")
            return True
        return False

    def get_char_limit(self, text: str) -> int:
        """
        Returns an estimated value for how many characters of a block of text should be allowed to display before being truncated.
        """
        # char_limit: int = (
        # 	(os.get_terminal_size()[0] * os.get_terminal_size()[1]) // 6)
        # char_limit -= (text.count('\n') + text.count('\r') * (os.get_terminal_size()[0] // 1.0))
        # char_limit = char_limit if char_limit > 0 else min(40, len(text))

        char_limit: int = os.get_terminal_size()[0] * (os.get_terminal_size()[1] // 5)
        char_limit -= (text.count("\n") + text.count("\r")) * (
            os.get_terminal_size()[0] // 2
        )
        char_limit = char_limit if char_limit > 0 else min((64), len(text))

        # print(f'Char Limit: {char_limit}, Len: {len(text)}')
        return char_limit

    def truncate_text(self, text: str) -> str:
        """Returns a truncated string for displaying, calculated with `get_char_limit()`."""
        if len(text) > self.get_char_limit(text):
            # print(f'Char Limit: {self.get_char_limit(text)}, Len: {len(text)}')
            return f"{text[:int(self.get_char_limit(text) - 1)]} {WHITE_FG}[...]{RESET}"
        else:
            return text

    def print_fields(self, index) -> None:
        """Prints an Entry's formatted fields to the screen."""
        entry = self.lib.entries[index]

        if entry and self.args.debug:
            print("")
            print(f"{BRIGHT_WHITE_BG}{BLACK_FG} ID: {RESET} ", end="")
            print(entry.id_)

        if entry and entry.fields:
            for i, field in enumerate(entry.fields):
                # Buffer between box fields below other fields if this isn't the first field
                if (
                    i != 0
                    and self.lib.get_field_attr(field, "type") in BOX_FIELDS
                    and self.lib.get_field_attr(entry.fields[i - 1], "type")
                    not in BOX_FIELDS
                ):
                    print("")
                # Format the field title differently for box fields.
                if self.lib.get_field_attr(field, "type") in BOX_FIELDS:
                    print(
                        f'{BRIGHT_WHITE_BG}{BLACK_FG} {self.lib.get_field_attr(field, "name")}: {RESET} ',
                        end="\n",
                    )
                else:
                    print(
                        f'{BRIGHT_WHITE_BG}{BLACK_FG} {self.lib.get_field_attr(field, "name")}: {RESET} ',
                        end="",
                    )
                if self.lib.get_field_attr(field, "type") == "tag_box":
                    char_count: int = 0
                    for tag_id in self.lib.get_field_attr(field, "content"):
                        tag = self.lib.get_tag(tag_id)
                        # Properly wrap Tags on screen
                        char_count += len(f" {tag.display_name(self.lib)} ") + 1
                        if char_count > os.get_terminal_size()[0]:
                            print("")
                            char_count = len(f" {tag.display_name(self.lib)} ") + 1
                        print(
                            f"{self.get_tag_color(tag.color)} {tag.display_name(self.lib)} {RESET}",
                            end="",
                        )
                        # If the tag isn't the last one, print a space for the next one.
                        if tag_id != self.lib.get_field_attr(field, "content")[-1]:
                            print(" ", end="")
                        else:
                            print("")
                elif self.lib.get_field_attr(field, "type") in TEXT_FIELDS:
                    # Normalize line endings in any text content.
                    text: str = self.lib.get_field_attr(field, "content").replace(
                        "\r", "\n"
                    )
                    print(self.truncate_text(text))
                elif self.lib.get_field_attr(field, "type") == "datetime":
                    try:
                        # TODO: Localize this and/or add preferences.
                        date = dt.strptime(
                            self.lib.get_field_attr(field, "content"),
                            "%Y-%m-%d %H:%M:%S",
                        )
                        print(date.strftime("%D - %r"))
                    except Exception:
                        print(self.lib.get_field_attr(field, "content"))
                else:
                    print(self.lib.get_field_attr(field, "content"))

                # Buffer between box fields above other fields if this isn't the last field
                if (
                    entry.fields[i] != entry.fields[-1]
                    and self.lib.get_field_attr(field, "type") in BOX_FIELDS
                ):
                    print("")
        else:
            # print(f'{MAGENTA_BG}{BRIGHT_WHITE_FG}[No Fields]{RESET}{WHITE_FG} (Run \'edit\', then \'add <field name>\' to add some!){RESET}')
            print(f"{MAGENTA_BG}{BRIGHT_WHITE_FG}[No Fields]{RESET}{WHITE_FG}")

    def print_thumbnail(
        self, index, filepath="", ignore_fields=False, max_width=-1
    ) -> None:
        """
        Prints an Entry's formatted thumbnail to the screen.
        Takes in either an Entry index or a direct filename.
        """
        entry = None if index < 0 else self.lib.entries[index]
        if entry:
            filepath = self.lib.library_dir / entry.path / entry.filename
        external_preview_path: Path = None
        if self.args.external_preview:
            external_preview_path = (
                self.lib.library_dir / TS_FOLDER_NAME / "external_preview.jpg"
            )
        # thumb_width = min(
        # 	os.get_terminal_size()[0]//2,
        # 	math.floor(os.get_terminal_size()[1]*0.5))
        # thumb_width = math.floor(os.get_terminal_size()[1]*0.5)

        # if entry:
        file_type = os.path.splitext(filepath)[1].lower()[1:]
        if file_type in (IMAGE_TYPES + VIDEO_TYPES):
            # TODO: Make the image-grabbing part try to get thumbnails.

            # Lots of calculations to determine an image width that works well.
            w, h = (1, 1)
            # final_img_path = filepath
            if file_type in IMAGE_TYPES:
                try:
                    raw = Image.open(filepath)
                    w, h = raw.size
                    # NOTE: Temporary way to hack a non-terminal preview.
                    if self.args.external_preview:
                        raw = raw.convert("RGB")
                        # raw.thumbnail((512, 512))
                        raw.thumbnail(self.external_preview_size)
                        raw.save(external_preview_path)
                except (
                    UnidentifiedImageError,
                    FileNotFoundError,
                    DecompressionBombError,
                ) as e:
                    print(f'{ERROR} Could not load image "{filepath} due to {e}"')
                    if self.args.external_preview:
                        self.set_external_preview_broken()
            elif file_type in VIDEO_TYPES:
                try:
                    video = cv2.VideoCapture(filepath)
                    video.set(
                        cv2.CAP_PROP_POS_FRAMES,
                        (video.get(cv2.CAP_PROP_FRAME_COUNT) // 2),
                    )
                    success, frame = video.read()
                    if not success:
                        # Depending on the video format, compression, and frame
                        # count, seeking halfway does not work and the thumb
                        # must be pulled from the earliest available frame.
                        video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        success, frame = video.read()
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    final_frame = Image.fromarray(frame)
                    w, h = final_frame.size
                    final_frame.save(
                        self.lib.library_dir / TS_FOLDER_NAME / "temp.jpg", quality=50
                    )
                    # final_img_path = self.lib.library_dir / TS_FOLDER_NAME / "temp.jpg"
                    # NOTE: Temporary way to hack a non-terminal preview.
                    if self.args.external_preview and entry:
                        final_frame.thumbnail(self.external_preview_size)
                        final_frame.save(external_preview_path)
                except SystemExit:
                    sys.exit()
                except Exception:
                    print(f'{ERROR} Could not load video thumbnail for "{filepath}"')
                    if self.args.external_preview and entry:
                        self.set_external_preview_broken()
                    pass

            img_ratio: float = w / h
            term_ratio_norm: float = (
                os.get_terminal_size()[1] / os.get_terminal_size()[0]
            ) * 2
            base_mod: float = 0.7
            field_cnt_mod: float = 0
            desc_len_mod: float = 0
            tag_cnt_mod: float = 0
            if entry and entry.fields and not ignore_fields:
                field_cnt_mod = 1.5 * len(entry.fields)
                for f in entry.fields:
                    if self.lib.get_field_attr(f, "type") == "tag_box":
                        tag_cnt_mod += 0.5 * len(self.lib.get_field_attr(f, "content"))
                    elif self.lib.get_field_attr(f, "type") == "text_box":
                        desc_len_mod += 0.07 * len(
                            self.truncate_text(self.lib.get_field_attr(f, "content"))
                        )
                        desc_len_mod += 1.7 * self.truncate_text(
                            self.lib.get_field_attr(f, "content")
                        ).count("\n")
                        desc_len_mod += 1.7 * self.truncate_text(
                            self.lib.get_field_attr(f, "content")
                        ).count("\r")
            try:
                thumb_width = min(
                    math.floor(
                        (
                            os.get_terminal_size()[0]
                            * img_ratio
                            * term_ratio_norm
                            * base_mod
                        )
                        - (
                            (field_cnt_mod + desc_len_mod + tag_cnt_mod)
                            * (img_ratio * 0.7)
                        )
                    ),
                    os.get_terminal_size()[0],
                )
                if max_width > 0:
                    thumb_width = max_width if thumb_width > max_width else thumb_width
                # image = climage.convert(final_img_path, is_truecolor=True, is_256color=False,
                # 						is_16color=False, is_8color=False, width=thumb_width)
                # Center Alignment Hack
                spacing = (os.get_terminal_size()[0] - thumb_width) // 2
                if not self.args.external_preview or not entry:
                    print(" " * spacing, end="")
                    # NOTE: Image is not defined, therefore commented out.
                    # print(image.replace("\n", ("\n" + " " * spacing)))

                if file_type in VIDEO_TYPES:
                    os.remove(self.lib.library_dir / TS_FOLDER_NAME / "temp.jpg")
            except Exception:
                if not self.args.external_preview or not entry:
                    print(
                        f"{ERROR} Could not display preview. Is there enough screen space?"
                    )

    def print_columns(self, content: list[object], add_enum: False) -> None:
        """
        Prints content in a column format.
        Content: A list of tuples list[(element, formatting)]
        """
        try:
            if content:
                # This is an estimate based on the existing screen formatting.
                margin: int = 7
                enum_padding: int = 0
                term_width: int = os.get_terminal_size()[0]

                num_width: int = len(str(len(content) + 1))
                if add_enum:
                    enum_padding = num_width + 2

                longest_width: int = (
                    len(max(content, key=lambda x: len(x[0]))[0]) + 1
                )  # + Padding
                column_count: int = term_width // (longest_width + enum_padding + 3)
                column_count: int = column_count if column_count > 0 else 1
                max_display: int = column_count * (os.get_terminal_size()[1] - margin)
                displayable: int = min(max_display, len(content))

                # Recalculate based on displayable items
                num_width = len(str(len(content[:max_display]) + 1))
                if add_enum:
                    enum_padding = num_width + 2
                longest_width = (
                    len(max(content[:max_display], key=lambda x: len(x[0]))[0]) + 1
                )
                column_count = term_width // (longest_width + enum_padding + 3)
                column_count = column_count if column_count > 0 else 1
                max_display = column_count * (os.get_terminal_size()[1] - margin)
                # displayable: int = min(max_display, len(content))

                num_width = len(str(len(content[:max_display]) + 1))
                if add_enum:
                    enum_padding = num_width + 2
                # longest_width = len(max(content[:max_display], key=lambda x: len(x[0]))[0]) + 1
                # column_count = term_width // (longest_width + enum_padding + 3)
                # column_count = column_count if column_count > 0 else 1
                # max_display = column_count * (os.get_terminal_size()[1]-margin)

                # print(num_width)
                # print(term_width)
                # print(longest_width)
                # print(columns)
                # print(max(content, key = lambda x : len(x[0])))
                # print(len(max(content, key = lambda x : len(x[0]))[0]))

                # # Prints out the list in a left-to-right tabular column form with color formatting.
                # for i, element in enumerate(content):
                # 	if i != 0 and i % (columns-1) == 0:
                # 		print('')
                # 	if add_enum:
                # 		print(f'{element[1]}[{str(i+1).zfill(num_width)}] {element[0]} {RESET}', end='')
                # 	else:
                # 		print(f'{element[1]} {element[0]} {RESET}', end='')
                # 	print(' ' * (longest_width - len(element[0])), end='')

                # Prints out the list in a top-down tabular column form with color formatting.
                # This is my greatest achievement.
                row_count: int = math.floor(len(content) / column_count)
                table_size: int = row_count * column_count
                table_size = table_size if table_size > 0 else 1
                # print(f'Rows:{max_rows}, Cols:{max_columns}')
                row_num = 1
                col_num = 1
                for i, element in enumerate(content):
                    if i < max_display:
                        if row_count > 1:
                            row_number = i // column_count
                            index = (i * row_count) - (row_number * (table_size - 1))
                            # col_number = index // math.ceil(len(content) / max_columns)
                            offset: int = 0
                            if displayable % table_size == 1:
                                offset = (
                                    1
                                    if (index >= row_count)
                                    and (row_number != row_count)
                                    else 0
                                )
                            elif displayable % table_size != 0:
                                if 1 < col_num <= displayable % table_size:
                                    offset += col_num - 1
                                elif col_num > 1 and col_num > displayable % table_size:
                                    offset = displayable % table_size

                            if (
                                col_num > 1
                                and (os.get_terminal_size()[1] - margin) < row_count
                            ):
                                offset -= (
                                    row_count - (os.get_terminal_size()[1] - margin)
                                ) * (col_num - 1) + (col_num - 1)

                            # print(f'{row_count}/{(os.get_terminal_size()[1]-margin)}', end='')

                            index += offset
                            # print(offset, end='')
                            # print(f'{row_num}-{col_num}', end='')
                        else:
                            index = i
                        if i != 0 and i % column_count == 0:
                            row_num += 1
                            col_num = 1
                            print("")
                        if index < len(content):
                            col_num += 1
                            col_num = col_num if col_num <= column_count else 1
                            if add_enum:
                                print(
                                    f"{content[index][1]}[{str(index+1).zfill(num_width)}] {content[index][0]} {RESET}",
                                    end="",
                                )
                            else:
                                print(
                                    f"{content[index][1]} {content[index][0]} {RESET}",
                                    end="",
                                )
                            if row_count > 0:
                                print(
                                    " " * (longest_width - len(content[index][0])),
                                    end="",
                                )
                            else:
                                print(" ", end="")
                    else:
                        print(
                            "\n"
                            + self.format_h2(f"[{len(content) - max_display} More...]"),
                            end="",
                        )
                        # print(WHITE_FG + '\n' + f'[{len(content) - max_display} More...]'.center(os.get_terminal_size()[0], " ")[:os.get_terminal_size()[0]]+RESET)
                        # print(f'\n{WHITE_FG}[{{RESET}', end='')
                        break
                # print(f'Rows:{row_count}, Cols:{column_count}')
                print("")

        except Exception:
            traceback.print_exc()
            print("\nPress Enter to Continue...")
            input()
            pass

    def run_macro(self, name: str, entry_id: int):
        """Runs a specific Macro on an Entry given a Macro name."""
        # entry: Entry = self.lib.get_entry_from_index(entry_id)
        entry = self.lib.get_entry(entry_id)
        path = self.lib.library_dir / entry.path / entry.filename
        source = path.split(os.sep)[1].lower()
        if name == "sidecar":
            self.lib.add_generic_data_to_entry(
                self.core.get_gdl_sidecar(path, source), entry_id
            )
        elif name == "autofill":
            self.run_macro("sidecar", entry_id)
            self.run_macro("build-url", entry_id)
            self.run_macro("match", entry_id)
            self.run_macro("clean-url", entry_id)
            self.run_macro("sort-fields", entry_id)
        elif name == "build-url":
            data = {"source": self.core.build_url(entry_id, source)}
            self.lib.add_generic_data_to_entry(data, entry_id)
        elif name == "sort-fields":
            order: list[int] = (
                [0]
                + [1, 2]
                + [9, 17, 18, 19, 20]
                + [10, 14, 11, 12, 13, 22]
                + [4, 5]
                + [8, 7, 6]
                + [3, 21]
            )
            self.lib.sort_fields(entry_id, order)
        elif name == "match":
            self.core.match_conditions(entry_id)
        elif name == "scrape":
            self.core.scrape(entry_id)
        elif name == "clean-url":
            # entry = self.lib.get_entry_from_index(entry_id)
            if entry.fields:
                for i, field in enumerate(entry.fields, start=0):
                    if self.lib.get_field_attr(field, "type") == "text_line":
                        self.lib.update_entry_field(
                            entry_id=entry_id,
                            field_index=i,
                            content=strip_web_protocol(
                                self.lib.get_field_attr(field, "content")
                            ),
                            mode="replace",
                        )

    def create_collage(self) -> str:
        """Generates and saves an image collage based on Library Entries."""

        run: bool = True
        keep_aspect: bool = False
        data_only_mode: bool = False
        data_tint_mode: bool = False

        mode: int = self.scr_choose_option(
            subtitle="Choose Collage Mode(s)",
            choices=[
                (
                    "Normal",
                    "Creates a standard square image collage made up of Library media files.",
                ),
                (
                    "Data Tint",
                    "Tints the collage with a color representing data about the Library Entries/files.",
                ),
                (
                    "Data Only",
                    "Ignores media files entirely and only outputs a collage of Library Entry/file data.",
                ),
                ("Normal & Data Only", "Creates both Normal and Data Only collages."),
            ],
            prompt="",
            required=True,
        )

        if mode == 1:
            data_tint_mode = True

        if mode == 2:
            data_only_mode = True

        if mode in [0, 1, 3]:
            keep_aspect = self.scr_choose_option(
                subtitle="Choose Aspect Ratio Option",
                choices=[
                    (
                        "Stretch to Fill",
                        "Stretches the media file to fill the entire collage square.",
                    ),
                    (
                        "Keep Aspect Ratio",
                        "Keeps the original media file's aspect ratio, filling the rest of the square with black bars.",
                    ),
                ],
                prompt="",
                required=True,
            )

        if mode in [1, 2, 3]:
            # TODO: Choose data visualization options here.
            pass

        full_thumb_size: int = 1

        if mode in [0, 1, 3]:
            full_thumb_size = self.scr_choose_option(
                subtitle="Choose Thumbnail Size",
                choices=[
                    ("Tiny (32px)", ""),
                    ("Small (64px)", ""),
                    ("Medium (128px)", ""),
                    ("Large (256px)", ""),
                    ("Extra Large (512px)", ""),
                ],
                prompt="",
                required=True,
            )

        thumb_size: int = (
            32
            if (full_thumb_size == 0)
            else 64
            if (full_thumb_size == 1)
            else 128
            if (full_thumb_size == 2)
            else 256
            if (full_thumb_size == 3)
            else 512
            if (full_thumb_size == 4)
            else 32
        )

        # if len(com) > 1 and com[1] == 'keep-aspect':
        # 	keep_aspect = True
        # elif len(com) > 1 and com[1] == 'data-only':
        # 	data_only_mode = True
        # elif len(com) > 1 and com[1] == 'data-tint':
        # 	data_tint_mode = True
        grid_size = math.ceil(math.sqrt(len(self.lib.entries))) ** 2
        grid_len = math.floor(math.sqrt(grid_size))
        thumb_size = thumb_size if not data_only_mode else 1
        img_size = thumb_size * grid_len

        print(
            f"Creating collage for {len(self.lib.entries)} Entries.\nGrid Size: {grid_size} ({grid_len}x{grid_len})\nIndividual Picture Size: ({thumb_size}x{thumb_size})"
        )
        if keep_aspect:
            print("Keeping original aspect ratios.")
        if data_only_mode:
            print("Visualizing Entry Data")

        if not data_only_mode:
            time.sleep(5)

        collage = Image.new("RGB", (img_size, img_size))
        filename = (
            self.lib.library_dir
            / TS_FOLDER_NAME
            / COLLAGE_FOLDER_NAME
            / f'collage_{datetime.datetime.utcnow().strftime("%F_%T").replace(":", "")}.png'
        )

        i = 0
        for x in range(0, grid_len):
            for y in range(0, grid_len):
                try:
                    if i < len(self.lib.entries) and run:
                        # entry: Entry = self.lib.get_entry_from_index(i)
                        entry = self.lib.entries[i]
                        filepath = self.lib.library_dir / entry.path / entry.filename
                        color: str = ""

                        if data_tint_mode or data_only_mode:
                            color = "#000000"  # Black (Default)

                            if entry.fields:
                                has_any_tags: bool = False
                                has_content_tags: bool = False
                                has_meta_tags: bool = False
                                for field in entry.fields:
                                    if (
                                        self.lib.get_field_attr(field, "type")
                                        == "tag_box"
                                    ):
                                        if self.lib.get_field_attr(field, "content"):
                                            has_any_tags = True
                                            if (
                                                self.lib.get_field_attr(field, "id")
                                                == 7
                                            ):
                                                has_content_tags = True
                                            elif (
                                                self.lib.get_field_attr(field, "id")
                                                == 8
                                            ):
                                                has_meta_tags = True
                                if has_content_tags and has_meta_tags:
                                    color = "#28bb48"  # Green
                                elif has_any_tags:
                                    color = "#ffd63d"  # Yellow
                                    # color = '#95e345' # Yellow-Green
                                else:
                                    # color = '#fa9a2c' # Yellow-Orange
                                    color = "#ed8022"  # Orange
                            else:
                                color = "#e22c3c"  # Red

                            if data_only_mode:
                                pic: Image = Image.new(
                                    "RGB", (thumb_size, thumb_size), color
                                )
                                collage.paste(pic, (y * thumb_size, x * thumb_size))
                        if not data_only_mode:
                            print(
                                f"\r{INFO} Combining [{i+1}/{len(self.lib.entries)}]: {self.get_file_color(filepath.suffix.lower())}{entry.path}{os.sep}{entry.filename}{RESET}"
                            )
                            # sys.stdout.write(f'\r{INFO} Combining [{i+1}/{len(self.lib.entries)}]: {self.get_file_color(file_type)}{entry.path}{os.sep}{entry.filename}{RESET}')
                            # sys.stdout.flush()

                            if filepath.suffix.lower() in IMAGE_TYPES:
                                try:
                                    with Image.open(
                                        self.lib.library_dir
                                        / entry.path
                                        / entry.filename
                                    ) as pic:
                                        if keep_aspect:
                                            pic.thumbnail((thumb_size, thumb_size))
                                        else:
                                            pic = pic.resize((thumb_size, thumb_size))
                                        if data_tint_mode and color:
                                            pic = pic.convert(mode="RGB")
                                            pic = ImageChops.hard_light(
                                                pic,
                                                Image.new(
                                                    "RGB",
                                                    (thumb_size, thumb_size),
                                                    color,
                                                ),
                                            )
                                        collage.paste(
                                            pic, (y * thumb_size, x * thumb_size)
                                        )
                                except DecompressionBombError as e:
                                    print(
                                        f"[ERROR] One of the images was too big ({e})"
                                    )

                            elif filepath.suffix.lower() in VIDEO_TYPES:
                                video = cv2.VideoCapture(filepath)
                                video.set(
                                    cv2.CAP_PROP_POS_FRAMES,
                                    (video.get(cv2.CAP_PROP_FRAME_COUNT) // 2),
                                )
                                success, frame = video.read()
                                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                with Image.fromarray(frame, mode="RGB") as pic:
                                    if keep_aspect:
                                        pic.thumbnail((thumb_size, thumb_size))
                                    else:
                                        pic = pic.resize((thumb_size, thumb_size))
                                    if data_tint_mode and color:
                                        pic = ImageChops.hard_light(
                                            pic,
                                            Image.new(
                                                "RGB", (thumb_size, thumb_size), color
                                            ),
                                        )
                                    collage.paste(pic, (y * thumb_size, x * thumb_size))
                except UnidentifiedImageError:
                    print(f"\n{ERROR} Couldn't read {entry.path / entry.filename}")
                except KeyboardInterrupt:
                    # self.quit(save=False, backup=True)
                    run = False
                    clear()
                    print(f"{INFO} Collage operation cancelled.")
                    # clear_scr = False
                except Exception:
                    print(f"{ERROR} {entry.path / entry.filename}")
                    traceback.print_exc()
                    print("Continuing...")
                i = i + 1

        if run:
            self.lib.verify_ts_folders()
            collage.save(filename)
            return filename
        return ""

    def global_commands(self, com: list[str]) -> tuple[bool, str]:
        """
        Executes from a set of global commands.\n
        Returns a (bool,str) tuple containing (was command executed?, optional command message)
        """
        was_executed: bool = False
        message: str = ""
        com_name = com[0].lower()

        # Backup Library =======================================================
        if com_name == "backup":
            self.backup_library(display_message=False)
            was_executed = True
            message = f"{INFO} Backed up Library to disk."
        # Create Collage =======================================================
        elif com_name == "collage":
            filename = self.create_collage()
            if filename:
                was_executed = True
                message = f'{INFO} Saved collage to "{filename}".'
        # Save Library =========================================================
        elif com_name in ("save", "write", "w"):
            self.save_library(display_message=False)
            was_executed = True
            message = f"{INFO} Library saved to disk."
        # Toggle Debug =========================================================
        elif com_name == "toggle-debug":
            self.args.debug = not self.args.debug
            was_executed = True
            message = (
                f"{INFO} Debug Mode Active."
                if self.args.debug
                else f"{INFO} Debug Mode Deactivated."
            )
        # Toggle External Preview ==============================================
        elif com_name == "toggle-external-preview":
            self.args.external_preview = not self.args.external_preview
            if self.args.external_preview:
                self.init_external_preview()
            else:
                self.close_external_preview()
            was_executed = True
            message = (
                f"{INFO} External Preview Enabled."
                if self.args.external_preview
                else f"{INFO} External Preview Disabled."
            )
        # Quit =================================================================
        elif com_name in ("quit", "q"):
            self.exit(save=True, backup=False)
            was_executed = True
        # Quit without Saving ==================================================
        elif com_name in ("quit!", "q!"):
            self.exit(save=False, backup=False)
            was_executed = True

        return (was_executed, message)

    def scr_browse_help(self, prev) -> None:
        """A Help screen for commands available during Library Browsing."""
        pass

    def scr_main_menu(self, clear_scr=True):
        """The CLI main menu."""

        while True:
            if self.args.open and self.first_open:
                self.first_open = False
                self.open_library(self.args.open)

            if clear_scr:
                clear()
            clear_scr = True
            print(f"{self.format_title(self.title_text)}")
            print("")
            print(f"\t{BRIGHT_WHITE_FG}{MAGENTA_BG} - Basic Commands - {RESET}")
            print(f"\t\tOpen Library: {WHITE_FG}open | o <folder path>{RESET}")
            print(f"\t\tCreate New Library: {WHITE_FG}new | n <folder path>{RESET}")
            # print(f'\t\tHelp: {WHITE_FG}help | h{RESET}')
            print("")
            print(f"\t\tQuit TagStudio: {WHITE_FG}quit | q{RESET}")
            print("")
            print(
                f"\t💡TIP: {WHITE_FG}TagStudio can be launched with the --open (or -o) option followed\n\t\tby <folder path> to immediately open a library!{RESET}"
            )
            print("")
            print("> ", end="")

            com: list[str] = input().lstrip().rstrip().split(" ")
            gc, message = self.global_commands(com)
            if gc:
                if message:
                    clear()
                    print(message)
                    clear_scr = False
            else:
                if com[0].lower() == "open" or com[0].lower() == "o":
                    if len(com) > 1:
                        self.open_library(com[1])
                elif com[0].lower() == "new" or com[0].lower() == "n":
                    if len(com) > 1:
                        self.scr_create_library(com[1])
                # elif (com[0].lower() == 'toggle-debug'):
                # 	self.args.debug = not self.args.debug
                # elif com[0].lower() in ['quit', 'q', 'close', 'c']:
                # 	sys.exit()
                # elif com[0].lower() in ['quit!', 'q!']:
                # 	sys.exit()
                else:
                    clear()
                    print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                    clear_scr = False

    def scr_library_home(self, clear_scr=True):
        """Home screen for an opened Library."""

        while True:
            subtitle = f"Library '{self.lib.library_dir}'"
            if self.lib.is_legacy_library:
                subtitle += " (Legacy Format)"
            if self.args.debug:
                subtitle += " (Debug Mode Active)"
            # Directory Info -------------------------------------------------------
            file_count: str = (
                f"{BRIGHT_YELLOW_FG}N/A (Run 'refresh dir' to update){RESET}"
                if self.lib.dir_file_count == -1
                else f"{WHITE_FG}{self.lib.dir_file_count}{RESET}"
            )

            new_file_count: str = (
                f"{BRIGHT_YELLOW_FG}N/A (Run 'refresh dir' to update){RESET}"
                if (
                    self.lib.files_not_in_library == []
                    and not self.is_new_file_count_init
                )
                else f"{WHITE_FG}{len(self.lib.files_not_in_library)}{RESET}"
            )

            # Issues ---------------------------------------------------------------
            missing_file_count: str = (
                f"{BRIGHT_YELLOW_FG}N/A (Run 'refresh missing' to update){RESET}"
                if (self.lib.missing_files == [] and not self.is_missing_count_init)
                else f"{BRIGHT_RED_FG}{len(self.lib.missing_files)}{RESET}"
            )
            missing_file_count = (
                f"{BRIGHT_GREEN_FG}0{RESET}"
                if (self.is_missing_count_init and len(self.lib.missing_files) == 0)
                else missing_file_count
            )

            dupe_entry_count: str = (
                f"{BRIGHT_YELLOW_FG}N/A (Run 'refresh dupe entries' to update){RESET}"
                if (self.lib.dupe_entries == [] and not self.is_dupe_entry_count_init)
                else f"{BRIGHT_RED_FG}{len(self.lib.dupe_entries)}{RESET}"
            )
            dupe_entry_count = (
                f"{BRIGHT_GREEN_FG}0{RESET}"
                if (self.is_dupe_entry_count_init and len(self.lib.dupe_entries) == 0)
                else dupe_entry_count
            )

            dupe_file_count: str = (
                f"{BRIGHT_YELLOW_FG}N/A (Run 'refresh dupe files' to update){RESET}"
                if (self.lib.dupe_files == [] and not self.is_dupe_file_count_init)
                else f"{BRIGHT_RED_FG}{len(self.lib.dupe_files)}{RESET}"
            )
            dupe_file_count = (
                f"{BRIGHT_GREEN_FG}0{RESET}"
                if (self.is_dupe_file_count_init and len(self.lib.dupe_files) == 0)
                else dupe_file_count
            )
            # fixed_file_count: str = 'N/A (Run \'fix missing\' to refresh)' if self.lib.fixed_files == [
            # ] else len(self.lib.fixed_files)

            if clear_scr:
                clear()
            clear_scr = True
            print(self.format_title(self.base_title))
            print(self.format_subtitle(subtitle))
            print("")

            if self.args.browse and self.first_browse:
                self.first_browse = False
                self.filtered_entries = self.lib.search_library()
                self.scr_browse_entries_gallery(0)
            else:
                print(f"\t{BRIGHT_CYAN_BG}{BLACK_FG} - Library Info - {RESET}")
                print(f"\t   Entries: {WHITE_FG}{len(self.lib.entries)}{RESET}")
                # print(f'\tCollations: {WHITE_FG}0{RESET}')
                print(f"\t      Tags: {WHITE_FG}{len(self.lib.tags)}{RESET}")
                print(f"\t    Fields: {WHITE_FG}{len(self.lib.default_fields)}{RESET}")
                # print(f'\t    Macros: {WHITE_FG}0{RESET}')
                print("")
                print(f"\t{BRIGHT_CYAN_BG}{BLACK_FG} - Directory Info - {RESET}")
                print(f"\t   Media Files: {file_count} (0 KB)")
                print(f"\tNot in Library: {new_file_count} (0 KB)")
                # print(f'\t Sidecar Files: 0 (0 KB)')
                # print(f'\t   Total Files: 0 (0 KB)')
                print("")
                print(f"\t{BRIGHT_CYAN_BG}{BLACK_FG} - Issues - {RESET}")
                print(f"\t    Missing Files: {missing_file_count}")
                print(f"\tDuplicate Entries: {dupe_entry_count}")
                print(f"\t  Duplicate Files: {dupe_file_count}")
                # print(f'  Fixed Files: {WHITE_FG}{fixed_file_count}{RESET}')
                print("")
                print(f"\t{BRIGHT_WHITE_FG}{MAGENTA_BG} - Basic Commands - {RESET}")

                print(f"\tBrowse Library: {WHITE_FG}browse | b{RESET}")
                print(f"\tSearch Library: {WHITE_FG}search | s < query >{RESET}")
                print(
                    f"\tList Info: {WHITE_FG}list | ls < dir | entires | tags | fields | macros | new | missing >{RESET}"
                )
                print(f"\tAdd New Files to Library: {WHITE_FG}add new{RESET}")
                print(
                    f"\tRefresh Info: {WHITE_FG}refresh | r < dir | missing | dupe entries | dupe files >{RESET}"
                )
                print(
                    f"\tFix Issues: {WHITE_FG}fix < missing | dupe entries | dupe files > {RESET}"
                )
                # print(f'\tHelp: {WHITE_FG}help | h{RESET}')

                print("")
                print(f"\tSave Library: {WHITE_FG}save | backup{RESET}")
                print(f"\tClose Library: {WHITE_FG}close | c{RESET}")
                print(f"\tQuit TagStudio: {WHITE_FG}quit | q{RESET}")
                # print(f'Quit Without Saving: {WHITE_FG}quit! | q!{RESET}')
                print("")
                print("> ", end="")

                com: list[str] = input().lstrip().rstrip().split(" ")
                gc, message = self.global_commands(com)
                if gc:
                    if message:
                        clear()
                        print(message)
                        clear_scr = False
                else:
                    # Refresh ==============================================================
                    if (com[0].lower() == "refresh" or com[0].lower() == "r") and len(
                        com
                    ) > 1:
                        if com[1].lower() == "files" or com[1].lower() == "dir":
                            print(
                                f"{INFO} Scanning for files in '{self.lib.library_dir}'..."
                            )
                            self.lib.refresh_dir()
                            self.is_new_file_count_init = True
                        elif com[1].lower() == "missing":
                            print(
                                f"{INFO} Checking for missing files in '{self.lib.library_dir}'..."
                            )
                            self.lib.refresh_missing_files()
                            self.is_missing_count_init = True
                        elif com[1].lower() == "duplicate" or com[1].lower() == "dupe":
                            if len(com) > 2:
                                if com[2].lower() == "entries" or com[2].lower() == "e":
                                    print(
                                        f"{INFO} Checking for duplicate entries in Library '{self.lib.library_dir}'..."
                                    )
                                    self.lib.refresh_dupe_entries()
                                    self.is_dupe_entry_count_init = True
                                elif com[2].lower() == "files" or com[2].lower() == "f":
                                    print(
                                        f"{WHITE_FG}Enter the filename for your DupeGuru results file:\n> {RESET}",
                                        end="",
                                    )
                                    dg_results_file = Path(input())
                                    print(
                                        f"{INFO} Checking for duplicate files in Library '{self.lib.library_dir}'..."
                                    )
                                    self.lib.refresh_dupe_files(dg_results_file)
                                    self.is_dupe_file_count_init = True
                            else:
                                clear()
                                print(
                                    f'{ERROR} Specify which duplicates to refresh (files, entries, all) \'{" ".join(com)}\''
                                )
                                clear_scr = False
                        else:
                            clear()
                            print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                            clear_scr = False
                    # List =================================================================
                    elif (com[0].lower() == "list" or com[0].lower() == "ls") and len(
                        com
                    ) > 1:
                        if com[1].lower() == "entries":
                            for i, e in enumerate(self.lib.entries, start=0):
                                title = f"[{i+1}/{len(self.lib.entries)}] {self.lib.entries[i].path / os.path.sep / self.lib.entries[i].filename}"
                                print(
                                    self.format_subtitle(
                                        title,
                                        color=self.get_file_color(
                                            os.path.splitext(
                                                self.lib.entries[i].filename
                                            )[1]
                                        ),
                                    )
                                )
                                self.print_fields(i)
                                print("")
                                time.sleep(0.05)
                            print("Press Enter to Continue...")
                            input()
                        elif com[1].lower() == "new":
                            for i in self.lib.files_not_in_library:
                                print(i)
                                time.sleep(0.1)
                            print("Press Enter to Continue...")
                            input()
                        elif com[1].lower() == "missing":
                            for i in self.lib.missing_files:
                                print(i)
                                time.sleep(0.1)
                            print("Press Enter to Continue...")
                            input()
                        elif com[1].lower() == "fixed":
                            for i in self.lib.fixed_files:
                                print(i)
                                time.sleep(0.1)
                            print("Press Enter to Continue...")
                            input()
                        elif com[1].lower() == "files" or com[1].lower() == "dir":
                            # NOTE: This doesn't actually print the directory files, it just prints
                            # files that are attached to Entries. Should be made consistent.
                            # print(self.lib.file_to_entry_index_map.keys())
                            for key in self.lib.filename_to_entry_id_map.keys():
                                print(key)
                                time.sleep(0.05)
                            print("Press Enter to Continue...")
                            input()
                        elif com[1].lower() == "duplicate" or com[1].lower() == "dupe":
                            if len(com) > 2:
                                if com[2].lower() == "entries" or com[2].lower() == "e":
                                    for dupe in self.lib.dupe_entries:
                                        print(
                                            self.lib.entries[dupe[0]].path
                                            / self.lib.entries[dupe[0]].filename
                                        )
                                        for d in dupe[1]:
                                            print(
                                                f"\t-> {(self.lib.entries[d].path / self.lib.entries[d].filename)}"
                                            )
                                            time.sleep(0.1)
                                    print("Press Enter to Continue...")
                                    input()
                                elif com[2].lower() == "files" or com[2].lower() == "f":
                                    for dupe in self.lib.dupe_files:
                                        print(dupe)
                                        time.sleep(0.1)
                                    print("Press Enter to Continue...")
                                    input()
                        elif com[1].lower() == "tags":
                            self.scr_list_tags(tag_ids=self.lib.search_tags(""))
                        else:
                            clear()
                            print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                            clear_scr = False
                    # Top ======================================================
                    # Tags -----------------------------------------------------
                    elif com[0].lower() == "top":
                        if len(com) > 1 and com[1].lower() == "tags":
                            self.lib.count_tag_entry_refs()
                            self.scr_top_tags()
                    # Browse ===========================================================
                    elif com[0].lower() == "browse" or com[0].lower() == "b":
                        if len(com) > 1:
                            if com[1].lower() == "entries":
                                self.filtered_entries = self.lib.search_library()
                                self.scr_browse_entries_gallery(0)
                            else:
                                clear()
                                print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                                clear_scr = False
                        else:
                            self.filtered_entries = self.lib.search_library()
                            self.scr_browse_entries_gallery(0)
                    # Search ===========================================================
                    elif com[0].lower() == "search" or com[0].lower() == "s":
                        if len(com) > 1:
                            self.filtered_entries = self.lib.search_library(
                                " ".join(com[1:])
                            )
                            self.scr_browse_entries_gallery(0)
                        else:
                            self.scr_browse_entries_gallery(0)
                        # self.scr_library_home(clear_scr=False)
                    # Add New Entries ==================================================
                    elif " ".join(com) == "add new":
                        if not self.is_new_file_count_init:
                            print(
                                f"{INFO} Scanning for files in '{self.lib.library_dir}' (This may take a while)..."
                            )
                            # if not self.lib.files_not_in_library:
                            self.lib.refresh_dir()
                        # self.is_new_file_count_init = False
                        new_ids: list[int] = self.lib.add_new_files_as_entries()
                        print(
                            f"{INFO} Running configured Macros on {len(new_ids)} new Entries..."
                        )
                        for id in new_ids:
                            self.run_macro("autofill", id)
                        # print(f'{INFO} Scanning for files in \'{self.lib.library_dir}\' (This may take a while)...')
                        # self.lib.refresh_dir()
                        self.is_new_file_count_init = True
                        # self.scr_library_home()
                    # Fix ==============================================================
                    elif (com[0].lower() == "fix") and len(com) > 1:
                        if com[1].lower() == "missing":
                            subtitle = "Fix Missing Files"
                            choices: list[(str, str)] = [
                                (
                                    "Search with Manual & Automated Repair",
                                    f"""Searches the Library directory ({self.lib.library_dir}) for files with the same name as the missing one(s), and automatically repairs Entries which only point to one matching file. If there are multiple filename matches for one Entry, a manual selection screen appears after any automatic repairing.\nRecommended if you moved files and don\'t have use strictly unique filenames in your Library directory.""",
                                ),
                                (
                                    "Search with Automated Repair Only",
                                    "Same as above, only skipping the manual step.",
                                ),
                                (
                                    "Remove Entries",
                                    """Removes Entries from the Library which point to missing files.\nOnly use if you know why a file is missing, and/or don\'t wish to keep that Entry\'s data.""",
                                ),
                            ]
                            prompt: str = "Choose how you want to repair Entries that point to missing files."
                            selection: int = self.scr_choose_option(
                                subtitle=subtitle, choices=choices, prompt=prompt
                            )

                            if selection >= 0 and not self.is_missing_count_init:
                                print(
                                    f"{INFO} Checking for missing files in '{self.lib.library_dir}'..."
                                )
                                self.lib.refresh_missing_files()

                            if selection == 0:
                                print(
                                    f"{INFO} Attempting to resolve {len(self.lib.missing_files)} missing files in '{self.lib.library_dir}' (This will take long for several results)..."
                                )
                                self.lib.fix_missing_files()

                                fixed_indices = []
                                if self.lib.missing_matches:
                                    clear()
                                    for unresolved in self.lib.missing_matches:
                                        res = self.scr_choose_missing_match(
                                            self.lib.get_entry_id_from_filepath(
                                                unresolved
                                            ),
                                            clear_scr=False,
                                        )
                                        if res is not None and int(res) >= 0:
                                            clear()
                                            print(
                                                f"{INFO} Updated {self.lib.entries[self.lib.get_entry_id_from_filepath(unresolved)].path} -> {self.lib.missing_matches[unresolved][res]}"
                                            )
                                            self.lib.entries[
                                                self.lib.get_entry_id_from_filepath(
                                                    unresolved
                                                )
                                            ].path = self.lib.missing_matches[
                                                unresolved
                                            ][res]
                                            fixed_indices.append(unresolved)
                                        elif res and int(res) < 0:
                                            clear()
                                            print(
                                                f"{INFO} Skipped match resolution selection.."
                                            )
                                if self.args.external_preview:
                                    self.set_external_preview_default()
                                self.lib.remove_missing_matches(fixed_indices)
                            elif selection == 1:
                                print(
                                    f"{INFO} Attempting to resolve missing files in '{self.lib.library_dir}' (This may take a LOOOONG while)..."
                                )
                                self.lib.fix_missing_files()
                            elif selection == 2:
                                print(
                                    f"{WARNING} Remove all Entries pointing to missing files? (Y/N)\n>{RESET} ",
                                    end="",
                                )
                                confirmation = input()
                                if (
                                    confirmation.lower() == "y"
                                    or confirmation.lower() == "yes"
                                ):
                                    deleted = []
                                    for i, missing in enumerate(self.lib.missing_files):
                                        print(
                                            f"Deleting {i}/{len(self.lib.missing_files)} Unlinked Entries"
                                        )
                                        try:
                                            id = self.lib.get_entry_id_from_filepath(
                                                missing
                                            )
                                            print(
                                                f"Removing Entry ID {id}:\n\t{missing}"
                                            )
                                            self.lib.remove_entry(id)
                                            self.driver.purge_item_from_navigation(
                                                ItemType.ENTRY, id
                                            )
                                            deleted.append(missing)
                                        except KeyError:
                                            print(
                                                f'{ERROR} "{id}" was reported as missing, but is not in the file_to_entry_id map.'
                                            )
                                    for d in deleted:
                                        self.lib.missing_files.remove(d)
                                    # for missing in self.lib.missing_files:
                                    # 	try:
                                    # 		index = self.lib.get_entry_index_from_filename(missing)
                                    # 		print(f'Removing Entry at Index [{index+1}/{len(self.lib.entries)}]:\n\t{missing}')
                                    # 		self.lib.remove_entry(index)
                                    # 	except KeyError:
                                    # 		print(
                                    # 			f'{ERROR} \"{index}\" was reported as missing, but is not in the file_to_entry_index map.')

                            if selection >= 0:
                                print(
                                    f"{INFO} Checking for missing files in '{self.lib.library_dir}'..."
                                )
                                self.lib.refresh_missing_files()
                                self.is_missing_count_init = True

                        # Fix Duplicates ===============================================================
                        elif com[1].lower() == "duplicate" or com[1].lower() == "dupe":
                            if len(com) > 2:
                                # Fix Duplicate Entries ----------------------------------------------------
                                if com[2].lower() == "entries" or com[2].lower() == "e":
                                    subtitle = "Fix Duplicate Entries"
                                    choices: list[(str, str)] = [
                                        (
                                            "Merge",
                                            "Each Entry pointing to the same file will have their data merged into a single remaining Entry.",
                                        )
                                    ]
                                    prompt: str = "Choose how you want to address groups of Entries which point to the same file."
                                    selection: int = self.scr_choose_option(
                                        subtitle=subtitle,
                                        choices=choices,
                                        prompt=prompt,
                                    )

                                    if selection == 0:
                                        if self.is_dupe_entry_count_init:
                                            print(
                                                f"{WARNING} Are you sure you want to merge {len(self.lib.dupe_entries)} Entries? (Y/N)\n> ",
                                                end="",
                                            )
                                        else:
                                            print(
                                                f"{WARNING} Are you sure you want to merge any duplicate Entries? (Y/N)\n> ",
                                                end="",
                                            )
                                        confirmation = input()
                                        if (
                                            confirmation.lower() == "y"
                                            or confirmation.lower() == "yes"
                                        ):
                                            if not self.is_dupe_entry_count_init:
                                                print(
                                                    f"{INFO} Checking for duplicate entries in Library '{self.lib.library_dir}'..."
                                                )
                                                self.lib.refresh_dupe_entries()
                                            self.lib.merge_dupe_entries()
                                            self.is_dupe_entry_count_init = False
                                # Fix Duplicate Entries ----------------------------------------------------
                                elif com[2].lower() == "files" or com[2].lower() == "f":
                                    subtitle = "Fix Duplicate Files"
                                    choices: list[(str, str)] = [
                                        (
                                            "Mirror",
                                            """For every predetermined duplicate file, mirror those files\' Entries with each other.\nMirroring involves merging all Entry field data together and then duplicating it across each Entry.\nThis process does not delete any Entries or files.""",
                                        )
                                    ]
                                    prompt: str = """Choose how you want to address handling data for files considered to be duplicates by an application such as DupeGuru. It\'s recommended that you mirror data here, then manually delete the duplicate files based on your own best judgement. Afterwards run \"fix missing\" and choose the \"Remove Entries\" option."""
                                    selection: int = self.scr_choose_option(
                                        subtitle=subtitle,
                                        choices=choices,
                                        prompt=prompt,
                                    )

                                    if selection == 0:
                                        if self.is_dupe_file_count_init:
                                            print(
                                                f"{WARNING} Are you sure you want to mirror Entry fields for {len(self.lib.dupe_files)} duplicate files? (Y/N)\n> ",
                                                end="",
                                            )
                                        else:
                                            print(
                                                f"{WARNING} Are you sure you want to mirror any Entry felids for duplicate files? (Y/N)\n> ",
                                                end="",
                                            )
                                        confirmation = input()
                                        if (
                                            confirmation.lower() == "y"
                                            or confirmation.lower() == "yes"
                                        ):
                                            print(
                                                f"{INFO} Mirroring {len(self.lib.dupe_files)} Entries for duplicate files..."
                                            )
                                            for i, dupe in enumerate(
                                                self.lib.dupe_files
                                            ):
                                                entry_id_1 = (
                                                    self.lib.get_entry_id_from_filepath(
                                                        dupe[0]
                                                    )
                                                )
                                                entry_id_2 = (
                                                    self.lib.get_entry_id_from_filepath(
                                                        dupe[1]
                                                    )
                                                )
                                                self.lib.mirror_entry_fields(
                                                    [entry_id_1, entry_id_2]
                                                )
                                    clear()
                                else:
                                    clear()
                                    print(
                                        f'{ERROR} Invalid duplicate type "{" ".join(com[2:])}".'
                                    )
                                    clear_scr = False
                            else:
                                clear()
                                print(
                                    f'{ERROR} Specify which duplicates to fix (entries, files, etc) "{" ".join(com)}".'
                                )
                                clear_scr = False
                        else:
                            clear()
                            print(
                                f'{ERROR} Invalid fix selection "{" ".join(com[1:])}". Try "fix missing", "fix dupe entries", etc.'
                            )
                            clear_scr = False
                    # # Save to Disk =========================================================
                    # elif com[0].lower() in ['save', 'write', 'w']:
                    # 	self.lib.save_library_to_disk()
                    # 	clear()
                    # 	print(
                    # 		f'{INFO} Library saved to disk.')
                    # 	clear_scr = False
                    # # Save Backup to Disk =========================================================
                    # elif (com[0].lower() == 'backup'):
                    # 	self.backup_library()
                    # 	clear_scr = False
                    # Close ============================================================
                    elif com[0].lower() == "close" or com[0].lower() == "c":
                        # self.core.clear_internal_vars()
                        self.close_library()
                        # clear()
                        return
                    # Unknown Command ==================================================
                    else:
                        clear()
                        print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                        clear_scr = False
                        # self.scr_library_home(clear_scr=False)

    def scr_browse_entries_gallery(self, index, clear_scr=True, refresh=True):
        """Gallery View for browsing Library Entries."""

        title = f"{self.base_title} - Library '{self.lib.library_dir}'"

        while True:
            # try:
            if refresh:
                if clear_scr:
                    clear()
                clear_scr = True

                print(self.format_title(title))

                if self.filtered_entries:
                    # entry = self.lib.get_entry_from_index(
                    # 	self.filtered_entries[index])
                    entry = self.lib.get_entry(self.filtered_entries[index][1])
                    filename = self.lib.library_dir / entry.path / entry.filename
                    # if self.lib.is_legacy_library:
                    #     title += ' (Legacy Format)'
                    h1 = f"[{index + 1}/{len(self.filtered_entries)}] {filename}"

                    # print(self.format_subtitle(subtitle))
                    print(
                        self.format_h1(h1, self.get_file_color(filename.suffix.lower()))
                    )
                    print("")

                    if not filename.is_file():
                        print(
                            f"{RED_BG}{BRIGHT_WHITE_FG}[File Missing]{RESET}{BRIGHT_RED_FG} (Run 'fix missing' to resolve){RESET}"
                        )
                        print("")
                        if self.args.external_preview:
                            self.set_external_preview_broken()
                    else:
                        self.print_thumbnail(self.filtered_entries[index][1])

                    self.print_fields(self.filtered_entries[index][1])
                else:
                    if self.lib.entries:
                        print(
                            self.format_h1(
                                "No Entry Results for Query", color=BRIGHT_RED_FG
                            )
                        )
                        self.set_external_preview_default()
                    else:
                        print(
                            self.format_h1("No Entries in Library", color=BRIGHT_RED_FG)
                        )
                        self.set_external_preview_default()
                    print("")

                print("")
                print(
                    self.format_subtitle(
                        "Prev   Next   Goto <#>   Open File   Search <Query>   List Tags",
                        BRIGHT_MAGENTA_FG,
                    )
                )
                print(
                    self.format_subtitle(
                        "Add, Remove, Edit <Field>    Remove    Close    Quit",
                        BRIGHT_MAGENTA_FG,
                    )
                )
                print("> ", end="")

                com: list[str] = input().lstrip().rstrip().split(" ")
                gc, message = self.global_commands(com)
                if gc:
                    if message:
                        clear()
                        print(message)
                        clear_scr = False
                else:
                    # except SystemExit:
                    # 	self.cleanup_before_exit()
                    # 	sys.exit()
                    # except IndexError:
                    # 	clear()
                    # 	print(f'{INFO} No matches found for query')
                    # 	# self.scr_library_home(clear_scr=False)
                    # 	# clear_scr=False
                    # 	return

                    # Previous =============================================================
                    if (
                        com[0].lower() == "prev"
                        or com[0].lower() == "p"
                        or com[0].lower() == "previous"
                    ):
                        if len(com) > 1:
                            try:
                                # self.scr_browse_entries_gallery(
                                # 	(index - int(com[1])) % len(self.filtered_entries))
                                # return
                                index = (index - int(com[1])) % len(
                                    self.filtered_entries
                                )
                            # except SystemExit:
                            # 	self.cleanup_before_exit()
                            # 	sys.exit()
                            except (IndexError, ValueError):
                                clear()
                                print(f"{ERROR} Invalid \"Previous\" Index: '{com[1]}'")
                                # self.scr_browse_entries_gallery(index, clear_scr=False)
                                clear_scr = False
                                # return
                        else:
                            # self.scr_browse_entries_gallery(
                            # 	(index - 1) % len(self.filtered_entries))
                            # return
                            index = (index - 1) % len(self.filtered_entries)
                    # Next =================================================================
                    elif com[0].lower() == "next" or com[0].lower() == "n":
                        if len(com) > 1:
                            try:
                                # NOTE: Will returning this as-is instead of after screw up the try-catch?
                                index = (index + int(com[1])) % len(
                                    self.filtered_entries
                                )
                                # self.scr_browse_entries_gallery(
                                # 	(index + int(com[1])) % len(self.filtered_entries))
                                # return
                            # except SystemExit:
                            # 	self.cleanup_before_exit()
                            # 	sys.exit()
                            except (IndexError, ValueError):
                                clear()
                                print(f"{ERROR} Invalid \"Next\" Index: '{com[1]}'")
                                # self.scr_browse_entries_gallery(index, clear_scr=False)
                                clear_scr = False
                                # return
                        else:
                            # self.scr_browse_entries_gallery(
                            # 	(index + 1) % len(self.filtered_entries))
                            # return
                            index = (index + 1) % len(self.filtered_entries)
                    # Goto =================================================================
                    elif (com[0].lower() == "goto" or com[0].lower() == "g") and len(
                        com
                    ) > 1:
                        try:
                            if int(com[1]) - 1 < 0:
                                raise IndexError
                            if int(com[1]) > len(self.filtered_entries):
                                raise IndexError
                            # self.scr_browse_entries_gallery(int(com[1])-1)
                            # return
                            index = int(com[1]) - 1
                        # except SystemExit:
                        # 	self.cleanup_before_exit()
                        # 	sys.exit()
                        except (IndexError, ValueError):
                            clear()
                            print(f"{ERROR} Invalid \"Goto\" Index: '{com[1]}'")
                            # self.scr_browse_entries_gallery(index, clear_scr=False)
                            clear_scr = False
                            # return
                    # Search ===============================================================
                    elif com[0].lower() == "search" or com[0].lower() == "s":
                        if len(com) > 1:
                            self.filtered_entries = self.lib.search_library(
                                " ".join(com[1:])
                            )
                            # self.scr_browse_entries_gallery(0)
                            index = 0
                        else:
                            self.filtered_entries = self.lib.search_library()
                            # self.scr_browse_entries_gallery(0)
                            index = 0
                        # running = False
                        # return
                        # self.scr_library_home(clear_scr=False)
                        # return
                    # # Toggle Debug ===========================================================
                    # elif (com[0].lower() == 'toggle-debug'):
                    # 	self.args.debug = not self.args.debug
                    # Open with Default Application ========================================
                    elif com[0].lower() == "open" or com[0].lower() == "o":
                        if len(com) > 1:
                            if com[1].lower() == "location" or com[1].lower() == "l":
                                open_file(filename, True)
                        else:
                            open_file(filename)
                        # refresh=False
                        # self.scr_browse_entries_gallery(index)
                    # Add Field ============================================================
                    elif com[0].lower() == "add" or com[0].lower() == "a":
                        if len(com) > 1:
                            id_list = self.lib.filter_field_templates(
                                " ".join(com[1:]).lower()
                            )
                            if id_list:
                                final_ids = []
                                if len(id_list) == 1:
                                    final_ids.append(id_list[0])
                                else:
                                    final_ids = self.scr_select_field_templates(id_list)

                                for id in final_ids:
                                    if id >= 0:
                                        self.lib.add_field_to_entry(
                                            self.filtered_entries[index][1], id
                                        )
                                # self.scr_browse_entries_gallery(index)
                                # return
                                # else:
                                # 	clear()
                                # 	print(f'{ERROR} Invalid selection.')
                                # 	return self.scr_browse_entries_gallery(index, clear_scr=False)

                        else:
                            clear()
                            print(f"{INFO} Please specify a field to add.")
                            # self.scr_browse_entries_gallery(index, clear_scr=False)
                            clear_scr = False
                            # return
                        # self.scr_browse_entries_gallery(index)
                        # return
                    # Remove Field =========================================================
                    elif com[0].lower() == "remove" or com[0].lower() == "rm":
                        if len(com) > 1:
                            # entry_fields = self.lib.get_entry_from_index(
                            # 	self.filtered_entries[index]).fields
                            entry_fields = self.lib.get_entry(
                                self.filtered_entries[index][1]
                            ).fields
                            field_indices: list[int] = []
                            for i, f in enumerate(entry_fields):
                                if int(
                                    self.lib.get_field_attr(f, "id")
                                ) in self.lib.filter_field_templates(
                                    " ".join(com[1:]).lower()
                                ):
                                    field_indices.append(i)

                            try:
                                final_field_index = -1
                                # if len(field_indices) == 1:
                                # 	final_index = field_indices[0]
                                # NOTE: The difference between this loop and Edit is that it always asks
                                # you to specify the field, even if there is only one option.
                                if len(field_indices) >= 1:
                                    print(field_indices)
                                    print(entry_fields)
                                    print(
                                        [
                                            self.lib.get_field_attr(
                                                entry_fields[x], "id"
                                            )
                                            for x in field_indices
                                        ]
                                    )
                                    final_field_index = field_indices[
                                        self.scr_select_field_templates(
                                            [
                                                self.lib.get_field_attr(
                                                    entry_fields[x], "id"
                                                )
                                                for x in field_indices
                                            ],
                                            allow_multiple=False,
                                            mode="remove",
                                            return_index=True,
                                        )[0]
                                    ]
                                else:
                                    clear()
                                    print(
                                        f'{ERROR} Entry does not contain the field "{" ".join(com[1:])}".'
                                    )
                                    # self.scr_browse_entries_gallery(index, clear_scr=False)
                                    clear_scr = False
                                    # return
                                # except SystemExit:
                                # 	self.cleanup_before_exit()
                                # 	sys.exit()
                            except IndexError:
                                pass

                            if final_field_index >= 0:
                                self.lib.get_entry(
                                    self.filtered_entries[index][1]
                                ).fields.pop(final_field_index)
                                # self.lib.entries[self.filtered_entries[index]].fields.pop(
                                # 	final_field_index)
                        else:
                            clear()
                            print(f"{INFO} Please specify a field to remove.")
                            # self.scr_browse_entries_gallery(index, clear_scr=False)
                            clear_scr = False
                            # return
                        # self.scr_browse_entries_gallery(index)
                        # return
                    # Edit Field ===========================================================
                    elif com[0].lower() == "edit" or com[0].lower() == "e":
                        if len(com) > 1:
                            # entry_fields = self.lib.get_entry_from_index(
                            # 	self.filtered_entries[index]).fields
                            entry_fields = self.lib.get_entry(
                                self.filtered_entries[index][1]
                            ).fields
                            field_indices: list[int] = []
                            for i, f in enumerate(entry_fields):
                                if int(
                                    self.lib.get_field_attr(f, "id")
                                ) in self.lib.filter_field_templates(
                                    " ".join(com[1:]).lower()
                                ):
                                    field_indices.append(i)

                            try:
                                final_field_index = -1
                                if len(field_indices) == 1:
                                    final_field_index = field_indices[0]
                                elif len(field_indices) > 1:
                                    print(field_indices)
                                    print(entry_fields)
                                    print(
                                        [
                                            self.lib.get_field_attr(
                                                entry_fields[x], "id"
                                            )
                                            for x in field_indices
                                        ]
                                    )
                                    final_field_index = field_indices[
                                        self.scr_select_field_templates(
                                            [
                                                self.lib.get_field_attr(
                                                    entry_fields[x], "id"
                                                )
                                                for x in field_indices
                                            ],
                                            allow_multiple=False,
                                            mode="edit",
                                            return_index=True,
                                        )[0]
                                    ]
                                else:
                                    clear()
                                    print(
                                        f'{ERROR} Entry does not contain the field "{" ".join(com[1:])}".'
                                    )
                                    # self.scr_browse_entries_gallery(index, clear_scr=False)
                                    clear_scr = False
                                    # return
                            # except SystemExit:
                            # 	self.cleanup_before_exit()
                            # 	sys.exit()
                            except IndexError:
                                pass

                            if final_field_index >= 0:
                                if (
                                    self.lib.get_field_attr(
                                        entry_fields[final_field_index], "type"
                                    )
                                    == "tag_box"
                                ):
                                    self.scr_edit_entry_tag_box(
                                        self.filtered_entries[index][1],
                                        field_index=final_field_index,
                                    )
                                elif (
                                    self.lib.get_field_attr(
                                        entry_fields[final_field_index], "type"
                                    )
                                    == "text_line"
                                ):
                                    self.scr_edit_entry_text(
                                        self.filtered_entries[index][1],
                                        field_index=final_field_index,
                                        allow_newlines=False,
                                    )
                                elif (
                                    self.lib.get_field_attr(
                                        entry_fields[final_field_index], "type"
                                    )
                                    == "text_box"
                                ):
                                    self.scr_edit_entry_text(
                                        self.filtered_entries[index][1],
                                        field_index=final_field_index,
                                    )
                                else:
                                    clear()
                                    print(
                                        f'{INFO} Sorry, this type of field ({self.lib.get_field_attr(entry_fields[final_field_index], "type")}) isn\'t editable yet.'
                                    )
                                    # self.scr_browse_entries_gallery(index, clear_scr=False)
                                    clear_scr = False
                                    # return
                        else:
                            clear()
                            print(f"{INFO} Please specify a field to edit.")
                            # self.scr_browse_entries_gallery(index, clear_scr=False)
                            clear_scr = False
                            # return
                        # self.scr_browse_entries_gallery(index)
                        # return
                    # Copy Field ===========================================================
                    elif com[0].lower() == "copy" or com[0].lower() == "cp":
                        # NOTE: Nearly identical code to the Edit section.
                        if len(com) > 1:
                            # entry_fields = self.lib.get_entry_from_index(
                            # 	self.filtered_entries[index]).fields
                            entry_fields = self.lib.get_entry(
                                self.filtered_entries[index][1]
                            ).fields
                            field_indices: list[int] = []
                            for i, f in enumerate(entry_fields):
                                if int(
                                    self.lib.get_field_attr(f, "id")
                                ) in self.lib.filter_field_templates(
                                    " ".join(com[1:]).lower()
                                ):
                                    field_indices.append(i)

                            # try:
                            final_field_index = -1
                            if len(field_indices) == 1:
                                final_field_index = field_indices[0]
                            elif len(field_indices) > 1:
                                print(field_indices)
                                print(entry_fields)
                                print(
                                    [
                                        self.lib.get_field_attr(entry_fields[x], "id")
                                        for x in field_indices
                                    ]
                                )
                                final_field_index = field_indices[
                                    self.scr_select_field_templates(
                                        [
                                            self.lib.get_field_attr(
                                                entry_fields[x], "id"
                                            )
                                            for x in field_indices
                                        ],
                                        allow_multiple=False,
                                        mode="edit",
                                        return_index=True,
                                    )[0]
                                ]
                            else:
                                clear()
                                print(
                                    f'{ERROR} Entry does not contain the field "{" ".join(com[1:])}".'
                                )
                                # self.scr_browse_entries_gallery(index, clear_scr=False)
                                clear_scr = False
                                # return
                            # except SystemExit:
                            # 	self.cleanup_before_exit()
                            # 	sys.exit()
                            # except:
                            # 	pass

                            if final_field_index >= 0:
                                self.copy_field_to_buffer(
                                    entry.fields[final_field_index]
                                )
                                # refresh = False
                        else:
                            clear()
                            print(f"{INFO} Please specify a field to copy.")
                            # self.scr_browse_entries_gallery(index, clear_scr=False)
                            clear_scr = False
                            # return
                        # self.scr_browse_entries_gallery(index)
                        # return
                    # Paste Field ===========================================================
                    elif com[0].lower() == "paste" or com[0].lower() == "ps":
                        self.paste_field_from_buffer(self.filtered_entries[index][1])
                        # self.scr_browse_entries_gallery(index)
                        # return
                    # Run Macro ============================================================
                    elif len(com) > 1 and com[0].lower() == "run":
                        if len(com) > 2 and com[1].lower() == "macro":
                            macro_name = (com[2]).lower()
                            if len(com) > 3:
                                # Run on all filtered Entries
                                if (
                                    com[-1].lower() == "--all"
                                    or com[-1].lower() == "-a"
                                ):
                                    clear()
                                    print(
                                        f'{INFO} Running Macro "{macro_name}" on {len(self.filtered_entries)} Entries...'
                                    )
                                    for type, id in self.filtered_entries:
                                        self.run_macro(name=macro_name, entry_id=id)
                                    # self.scr_browse_entries_gallery(index)
                            else:
                                # Run on current Entry
                                self.run_macro(
                                    name=macro_name,
                                    entry_id=self.filtered_entries[index][1],
                                )
                                # self.scr_browse_entries_gallery(index)
                            # return
                        else:
                            clear()
                            print(f"{ERROR} Please specify a Macro to run.")
                            # self.scr_browse_entries_gallery(index, clear_scr=False)
                            clear_scr = False
                            # return
                    # List Tags ============================================================
                    elif (com[0].lower() == "list" or com[0].lower() == "ls") and len(
                        com
                    ) > 1:
                        if com[1].lower() == "tags":
                            clear()
                            self.scr_list_tags(tag_ids=self.lib.search_tags(""))
                        else:
                            clear()
                            print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                            clear_scr = False
                        # self.scr_browse_entries_gallery(index, clear_scr=False)

                        # return
                    # # Save to Disk =========================================================
                    # elif (com[0].lower() == 'save' or com[0].lower() == 'write' or com[0].lower() == 'w'):
                    # 	self.lib.save_library_to_disk()
                    # 	clear()
                    # 	print(
                    # 		f'{INFO} Library saved to disk.')
                    # 	# self.scr_browse_entries_gallery(index, clear_scr=False)
                    # 	clear_scr = False
                    # 	# return
                    # # Save Backup to Disk =========================================================
                    # elif (com[0].lower() == 'backup'):
                    # 	clear()
                    # 	self.backup_library()
                    # 	clear_scr = False
                    # Close View ===========================================================
                    elif com[0].lower() == "close" or com[0].lower() == "c":
                        if self.args.external_preview:
                            self.set_external_preview_default()
                        # self.scr_library_home()
                        clear()
                        return
                    # # Quit =================================================================
                    # elif com[0].lower() == 'quit' or com[0].lower() == 'q':
                    # 	self.lib.save_library_to_disk()
                    # 	# self.cleanup()
                    # 	sys.exit()
                    # # Quit without Saving ==================================================
                    # elif com[0].lower() == 'quit!' or com[0].lower() == 'q!':
                    # 	# self.cleanup()
                    # 	sys.exit()
                    # Unknown Command ======================================================
                    elif com:
                        clear()
                        print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                        # self.scr_browse_entries_gallery(index, clear_scr=False)
                        clear_scr = False
                        # return

    def scr_choose_option(
        self,
        subtitle: str,
        choices: list,
        prompt: str = "",
        required=False,
        clear_scr=True,
    ) -> int:
        """
        Screen for choosing one of a given set of generic options.
        Takes in a list of (str,str) tuples which consist of (option name, option description),
        with the description being optional.
        Returns the index of the selected choice (starting at 0), or -1 if the choice was '0', 'Cancel', or 'C'.
        """

        title = f"{self.base_title} - Library '{self.lib.library_dir}'"
        # invalid_input: bool = False

        while True:
            if clear_scr:
                clear()
            clear_scr = True

            print(self.format_title(title, color=f"{BLACK_FG}{BRIGHT_CYAN_BG}"))
            print(self.format_subtitle(subtitle))
            # if invalid_input:
            # 	print(self.format_h1(
            # 		str='Please Enter a Valid Selection Number', color=BRIGHT_RED_FG))
            # 	invalid_input = False
            print("")
            if prompt:
                print(prompt)
                print("")
                print("")

            for i, choice in enumerate(choices, start=1):
                print(
                    f"{BRIGHT_WHITE_BG}{BLACK_FG}[{str(i).zfill(len(str(len(choices))))}]{RESET} {BRIGHT_WHITE_BG}{BLACK_FG} {choice[0]} {RESET}"
                )
                if choice[1]:
                    print(f"{WHITE_FG}{choice[1]}{RESET}")
                    print("")

            if not required:
                print("")
                print(
                    f"{BRIGHT_WHITE_BG}{BLACK_FG}[0]{RESET} {BRIGHT_WHITE_BG}{BLACK_FG} Cancel {RESET}"
                )

            print("")
            if not required:
                print(
                    self.format_subtitle("<#>    0 or Cancel    Quit", BRIGHT_CYAN_FG)
                )
            else:
                print(self.format_subtitle("<#>    Quit", BRIGHT_CYAN_FG))
            print("> ", end="")

            com: list[str] = input().strip().split(" ")
            gc, message = self.global_commands(com)
            if gc:
                if message:
                    clear()
                    print(message)
                    clear_scr = False
            else:
                com_name = com[0].lower()

                try:
                    # # Quit =========================================================
                    # if com.lower() == 'quit' or com.lower() == 'q':
                    # 	self.lib.save_library_to_disk()
                    # 	# self.cleanup()
                    # 	sys.exit()
                    # # Quit without Saving ==========================================
                    # elif com.lower() == 'quit!' or com.lower() == 'q!':
                    # 	# self.cleanup()
                    # 	sys.exit()
                    # Cancel =======================================================
                    if com_name in ("cancel", "c", "0") and not required:
                        clear()
                        return -1
                    # Selection ====================================================
                    elif com_name.isdigit() and 0 < int(com_name) <= len(choices):
                        clear()
                        return int(com_name) - 1
                    else:
                        # invalid_input = True
                        # print(self.format_h1(str='Please Enter a Valid Selection Number', color=BRIGHT_RED_FG))
                        clear()
                        print(f"{ERROR} Please Enter a Valid Selection Number/Option.")
                        clear_scr = False
                except (TypeError, ValueError):
                    clear()
                    print(f"{ERROR} Please Enter a Valid Selection Number/Option.")
                    clear_scr = False

    def scr_choose_missing_match(self, index, clear_scr=True, refresh=True) -> int:
        """
        Screen for manually resolving a missing file.
        Returns the index of the choice made (starting at 0), or -1 if skipped.
        """

        title = f"{self.base_title} - Library '{self.lib.library_dir}'"
        subtitle = "Resolve Missing File Conflict"

        while True:
            entry = self.lib.get_entry_from_index(index)
            filename = self.lib.library_dir / entry.path / entry.filename

            if refresh:
                if clear_scr:
                    clear()
                clear_scr = True
                print(self.format_title(title, color=f"{BLACK_FG}{BRIGHT_CYAN_BG}"))
                print(self.format_subtitle(subtitle))
                print("")
                print(self.format_h1(filename, BRIGHT_RED_FG), end="\n\n")

                self.print_fields(index)

                for i, match in enumerate(self.lib.missing_matches[filename]):
                    print(self.format_h1(f"[{i+1}] {match}"), end="\n\n")
                    fn = self.lib.library_dir / match / entry.filename
                    self.print_thumbnail(
                        index=-1,
                        filepath=fn,
                        max_width=(
                            os.get_terminal_size()[1]
                            // len(self.lib.missing_matches[filename])
                            - 2
                        ),
                    )
                    if fn in self.lib.filename_to_entry_id_map.keys():
                        self.print_fields(self.lib.get_entry_id_from_filepath(fn))
                print("")
                print(
                    self.format_subtitle(
                        "<#>    0 to Skip    Open Files    Quit", BRIGHT_CYAN_FG
                    )
                )
                print("> ", end="")

            com: list[str] = input().lstrip().rstrip().split(" ")
            gc, message = self.global_commands(com)
            if gc:
                if message:
                    clear()
                    print(message)
                    clear_scr = False
            else:
                # Refresh ==============================================================
                if com[0].lower() == "refresh" or com[0].lower() == "r":
                    # if (com[0].lower() == 'refresh' or com[0].lower() == 'r') and len(com) > 1:
                    # if com[1].lower() == 'files' or com[1].lower() == 'dir':
                    # 	clear()
                    # 	return self.scr_choose_missing_match(index)
                    # else:
                    # 	clear()
                    # 	print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                    # self.scr_library_home(clear_scr=False)
                    # clear_scr=False
                    pass
                # Open =============================================================
                elif com[0].lower() == "open" or com[0].lower() == "o":
                    for match in self.lib.missing_matches[filename]:
                        fn = self.lib.library_dir / match / entry.filename
                        open_file(fn)
                    refresh = False
                    # clear()
                    # return self.scr_choose_missing_match(index, clear_scr=False)
                # # Quit =============================================================
                # elif com[0].lower() == 'quit' or com[0].lower() == 'q':
                # 	self.lib.save_library_to_disk()
                # 	# self.cleanup()
                # 	sys.exit()
                # # Quit without Saving ==============================================
                # elif com[0].lower() == 'quit!' or com[0].lower() == 'q!':
                # 	# self.cleanup()
                # 	sys.exit()
                # Selection/Other ==================================================
                else:
                    try:
                        i = int(com[0]) - 1
                        if i < len(self.lib.missing_matches[filename]):
                            if i < -1:
                                return -1
                            else:
                                return i
                        else:
                            raise IndexError
                    # except SystemExit:
                    # 	self.cleanup_before_exit()
                    # 	sys.exit()
                    except (ValueError, IndexError):
                        clear()
                        print(f'{ERROR} Invalid command \'{" ".join(com)}\'')
                        # return self.scr_choose_missing_match(index, clear_scr=False)
                        clear_scr = False

    def scr_resolve_dupe_files(self, index, clear_scr=True):
        """Screen for manually resolving duplicate files."""

        title = f"{self.base_title} - Library '{self.lib.library_dir}'"
        subtitle = "Resolve Duplicate Files"

        while True:
            dupe = self.lib.dupe_files[index]

            if dupe[0].exists() and dupe[1].exists():
                # entry = self.lib.get_entry_from_index(index_1)
                entry_1_index = self.lib.get_entry_id_from_filepath(dupe[0])
                entry_2_index = self.lib.get_entry_id_from_filepath(dupe[1])

                if clear_scr:
                    clear()
                clear_scr = True

                print(self.format_title(title, color=f"{BLACK_FG}{BRIGHT_CYAN_BG}"))
                print(self.format_subtitle(subtitle))

                print("")
                print(f"{WHITE_BG}{BLACK_FG} Similarity: {RESET} ", end="")
                print(f"{dupe[2]}%")

                # File 1
                print("")
                print(self.format_h1(dupe[0], BRIGHT_RED_FG), end="\n\n")
                print(f"{WHITE_BG}{BLACK_FG} File Size: {RESET} ", end="")
                print("0 KB")
                print(f"{WHITE_BG}{BLACK_FG} Resolution: {RESET} ", end="")
                print("0x0")
                if entry_1_index is not None:
                    print("")
                    self.print_fields(entry_1_index)
                else:
                    print(f"{BRIGHT_RED_FG}No Library Entry for file.{RESET}")

                # File 2
                print("")
                print(self.format_h1(dupe[1], BRIGHT_RED_FG), end="\n\n")
                print(f"{WHITE_BG}{BLACK_FG} File Size: {RESET} ", end="")
                print("0 KB")
                print(f"{WHITE_BG}{BLACK_FG} Resolution: {RESET} ", end="")
                print("0x0")
                if entry_2_index is not None:
                    print("")
                    self.print_fields(entry_2_index)
                else:
                    print(f"{BRIGHT_RED_FG}No Library Entry for file.{RESET}")

                # for i, match in enumerate(self.lib.missing_matches[filename]):
                # 	print(self.format_h1(f'[{i+1}] {match}'), end='\n\n')
                # 	fn = f'{os.path.normpath(self.lib.library_dir + "/" + match + "/" + entry_1.filename)}'
                # 	self.print_thumbnail(self.lib.get_entry_from_filename(fn),
                # 						 max_width=(os.get_terminal_size()[1]//len(self.lib.missing_matches[filename])-2))
                # 	self.print_fields(self.lib.get_entry_from_filename(fn))
                print("")
                print(
                    self.format_subtitle(
                        "Mirror    Delete <#>    Skip    Close    Open Files    Quit",
                        BRIGHT_CYAN_FG,
                    )
                )
                print("> ", end="")

                com: list[str] = input().lstrip().rstrip().split(" ")
                gc, message = self.global_commands(com)
                if gc:
                    if message:
                        clear()
                        print(message)
                        clear_scr = False
                else:
                    # Refresh ==========================================================
                    if (com[0].lower() == "refresh" or com[0].lower() == "r") and len(
                        com
                    ) > 1:
                        # if com[1].lower() == 'files' or com[1].lower() == 'dir':
                        # 	clear()
                        # return self.scr_resolve_dupe_files(index, clear_scr=True)
                        # else:
                        # 	clear()
                        # 	print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                        # self.scr_library_home(clear_scr=False)
                        pass
                    # Open =============================================================
                    elif com[0].lower() == "open" or com[0].lower() == "o":
                        # for match in self.lib.missing_matches[filename]:
                        # 	fn = f'{os.path.normpath(self.lib.library_dir + "/" + match + "/" + entry_1.filename)}'
                        # 	open_file(fn)
                        open_file(dupe[0])
                        open_file(dupe[1])
                        # clear()
                        # return self.scr_resolve_dupe_files(index, clear_scr=False)
                    # Mirror Entries ===================================================
                    elif com[0].lower() == "mirror" or com[0].lower() == "mir":
                        return com
                    # Skip ============================================================
                    elif com[0].lower() == "skip":
                        return com
                    # Skip ============================================================
                    elif (
                        com[0].lower() == "close"
                        or com[0].lower() == "cancel"
                        or com[0].lower() == "c"
                    ):
                        return ["close"]
                    # Delete ===========================================================
                    elif com[0].lower() == "delete" or com[0].lower() == "del":
                        if len(com) > 1:
                            if com[1] == "1":
                                return ["del", 1]
                            elif com[1] == "2":
                                return ["del", 2]
                            else:
                                # return self.scr_resolve_dupe_files(index)
                                pass
                        else:
                            clear()
                            print(
                                f"{ERROR} Please specify which file (ex. delete 1, delete 2) to delete file."
                            )
                            # return self.scr_resolve_dupe_files(index, clear_scr=False)
                            clear_scr = False
                    # # Quit =============================================================
                    # elif com[0].lower() == 'quit' or com[0].lower() == 'q':
                    # 	self.lib.save_library_to_disk()
                    # 	# self.cleanup()
                    # 	sys.exit()
                    # # Quit without Saving ==============================================
                    # elif com[0].lower() == 'quit!' or com[0].lower() == 'q!':
                    # 	# self.cleanup()
                    # 	sys.exit()
                    # Other ============================================================
                    else:
                        # try:
                        # 	i = int(com[0]) - 1
                        # 	if i < len(self.lib.missing_matches[filename]):
                        # 		return i
                        # 	else:
                        # 		raise IndexError
                        # except SystemExit:
                        # 	sys.exit()
                        # except:
                        clear()
                        print(f'{ERROR} Invalid command \'{" ".join(com)}\'')
                        # return self.scr_resolve_dupe_files(index, clear_scr=False)
                        clear_scr = False

    def scr_edit_entry_tag_box(self, entry_index, field_index, clear_scr=True):
        """Screen for editing an Entry tag-box field."""

        title = f"{self.base_title} - Library '{self.lib.library_dir}'"

        entry = self.lib.entries[entry_index]
        filename = self.lib.library_dir / entry.path / entry.filename
        field_name = self.lib.get_field_attr(entry.fields[field_index], "name")
        subtitle = f'Editing "{field_name}" Field'
        h1 = f"{filename}"

        while True:
            if clear_scr:
                clear()
            clear_scr = True

            print(self.format_title(title, color=f"{BLACK_FG}{BRIGHT_CYAN_BG}"))
            print(self.format_subtitle(subtitle))
            print(
                self.format_h1(h1, self.get_file_color(os.path.splitext(filename)[1]))
            )
            print("")

            if not filename.is_file():
                print(
                    f"{RED_BG}{BRIGHT_WHITE_FG}[File Missing]{RESET}{BRIGHT_RED_FG} (Run 'fix missing' to resolve){RESET}"
                )
                print("")
            else:
                self.print_thumbnail(entry_index)

            print(f"{BRIGHT_WHITE_BG}{BLACK_FG} {field_name}: {RESET} ")
            for i, tag_id in enumerate(
                entry.fields[field_index][list(entry.fields[field_index].keys())[0]]
            ):
                tag = self.lib.get_tag(tag_id)
                print(
                    f"{self.get_tag_color(tag.color)}[{i+1}]{RESET} {self.get_tag_color(tag.color)} {tag.display_name(self.lib)} {RESET}"
                )
                # if tag_id != field[field_id][-1]:
                # 	print(' ', end='')
            print("")

            print(
                self.format_subtitle(
                    "Add <Tag Name>    Remove <#>    Open File    Close/Done    Quit"
                )
            )
            print("> ", end="")

            com: list[str] = input().lstrip().rstrip().split(" ")
            gc, message = self.global_commands(com)
            if gc:
                if message:
                    clear()
                    print(message)
                    clear_scr = False
            else:
                # Open with Default Application ========================================
                if com[0].lower() == "open" or com[0].lower() == "o":
                    open_file(filename)
                    # self.scr_edit_entry_tag_box(entry_index, field_index)
                    # return
                # Close View ===========================================================
                elif (
                    com[0].lower() == "close"
                    or com[0].lower() == "c"
                    or com[0].lower() == "done"
                ):
                    # self.scr_browse_entries_gallery()
                    clear()
                    return
                # # Quit =================================================================
                # elif com[0].lower() == 'quit' or com[0].lower() == 'q':
                # 	self.lib.save_library_to_disk()
                # 	# self.cleanup()
                # 	sys.exit()
                # # Quit without Saving ==================================================
                # elif com[0].lower() == 'quit!' or com[0].lower() == 'q!':
                # 	# self.cleanup()
                # 	sys.exit()
                # Add Tag ==============================================================
                elif com[0].lower() == "add":
                    if len(com) > 1:
                        tag_list = self.lib.search_tags(
                            " ".join(com[1:]), include_cluster=True
                        )
                        t: list[int] = []
                        if len(tag_list) > 1:
                            t = self.scr_select_tags(tag_list)
                        else:
                            t = tag_list  # Single Tag
                        if t:
                            self.lib.update_entry_field(
                                entry_index, field_index, content=t, mode="append"
                            )
                        # self.scr_edit_entry_tag_box(entry_index, field_index)
                        # return
                # Remove Tag ===========================================================
                elif com[0].lower() == "remove" or com[0].lower() == "rm":
                    if len(com) > 1:
                        try:
                            selected_tag_ids: list[int] = []
                            for c in com[1:]:
                                if (int(c) - 1) < 0:
                                    raise IndexError
                                # print(self.lib.get_field_attr(entry.fields[field_index], 'content'))
                                # print(self.lib.get_field_attr(entry.fields[field_index], 'content')[int(c)-1])
                                selected_tag_ids.append(
                                    self.lib.get_field_attr(
                                        entry.fields[field_index], "content"
                                    )[int(c) - 1]
                                )
                                # i = int(com[1]) - 1

                            # tag = entry.fields[field_index][list(
                            # 	entry.fields[field_index].keys())[0]][i]
                            self.lib.update_entry_field(
                                entry_index,
                                field_index,
                                content=selected_tag_ids,
                                mode="remove",
                            )
                        # except SystemExit:
                        # 	self.cleanup_before_exit()
                        # 	sys.exit()
                        except Exception:
                            clear()
                            print(f"{ERROR} Invalid Tag Selection '{com[1:]}'")
                            clear_scr = False
                            # self.scr_edit_entry_tag_box(
                            # 	entry_index, field_index, clear_scr=False)
                            # return
                        # self.scr_edit_entry_tag_box(entry_index, field_index)
                        # return
                # Unknown Command ======================================================
                else:
                    clear()
                    print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                    # self.scr_edit_entry_tag_box(
                    # 	entry_index, field_index, clear_scr=False)
                    # return
                    clear_scr = False

    def scr_select_tags(self, tag_ids: list[int], clear_scr=True) -> list[int]:
        """Screen for selecting and returning one or more Tags. Used for Entry editing."""

        title = f"{self.base_title} - Library '{self.lib.library_dir}'"
        subtitle = "Select Tag(s) to Add"

        if clear_scr:
            clear()
        clear_scr = True
        print(self.format_title(title, color=f"{BLACK_FG}{BRIGHT_GREEN_BG}"))
        print(self.format_subtitle(subtitle, BRIGHT_GREEN_FG))
        # print(self.format_h1(h1, self.get_file_color(
        #     os.path.splitext(filename)[1])))
        print("")

        tag_tuple_list = []
        for tag_id in tag_ids:
            tag = self.lib.get_tag(tag_id)
            tag_tuple_list.append(
                (tag.display_name(self.lib), self.get_tag_color(tag.color))
            )

        self.print_columns(tag_tuple_list, add_enum=True)
        print("")

        print(self.format_subtitle("Enter #(s)    Cancel", BRIGHT_GREEN_FG))
        print("> ", end="")

        com: list[str] = input().rstrip().split(" ")
        selected_ids: list[int] = []
        try:
            for c in com:
                selected_ids.append(tag_ids[int(c) - 1])
        except SystemExit:
            self.cleanup_before_exit()
            sys.exit()
        except Exception:
            print(f"{ERROR} Invalid Tag Selection")

        return selected_ids

    # TODO: This can be replaced by the new scr_choose_option method.
    def scr_select_field_templates(
        self,
        field_ids: list[int],
        allow_multiple=True,
        mode="add",
        return_index=False,
        clear_scr=True,
    ) -> list[int]:
        """
        Screen for selecting and returning one or more Field Templates. Used for Entry editing.
        Allow Multiple: Lets the user select multiple items, returned in a list. If false, returns a list of only the first selected item.
        Mode: 'add', 'edit', 'remove' - Changes prompt text and colors.
        Return Index: Instead of returning the Field IDs that were selected, this returns the indices of the selected items from the given list.
        """

        title = f"TagStudio {VERSION}{self.branch} - CLI Mode - Library '{self.lib.library_dir}'"
        subtitle = "Select Field(s) to Add"
        plural = "(s)"

        if not allow_multiple:
            plural = ""

        fg_text_color = BLACK_FG
        fg_color = BRIGHT_GREEN_FG
        bg_color = BRIGHT_GREEN_BG
        if mode == "edit":
            fg_color = BRIGHT_CYAN_FG
            bg_color = BRIGHT_CYAN_BG
            subtitle = f"Select Field{plural} to Edit"
        elif mode == "remove":
            fg_color = BRIGHT_RED_FG
            bg_color = BRIGHT_RED_BG
            # fg_text_color = BRIGHT_WHITE_FG
            subtitle = f"Select Field{plural} to Remove"

        if clear_scr:
            clear()
        clear_scr = True
        print(self.format_title(title, color=f"{fg_text_color}{bg_color}"))
        print(self.format_subtitle(subtitle, fg_color))
        # print(self.format_h1(h1, self.get_file_color(
        #     os.path.splitext(filename)[1])))
        print("")

        for i, field_id in enumerate(field_ids):
            name = self.lib.get_field_obj(field_id)["name"]
            type = self.lib.get_field_obj(field_id)["type"]
            if i < (os.get_terminal_size()[1] - 7):
                print(
                    f"{BRIGHT_WHITE_BG}{BLACK_FG}[{i+1}]{RESET} {BRIGHT_WHITE_BG}{BLACK_FG} {name} ({type}) {RESET}"
                )
            else:
                print(f"{WHITE_FG}[...]{RESET}")
                break
        print("")

        print(self.format_subtitle(f"Enter #{plural}    Cancel", fg_color))
        print("> ", end="")

        com: list[str] = input().split(" ")
        selected_ids: list[int] = []
        try:
            for c in com:
                if int(c) > 0:
                    if return_index:
                        selected_ids.append(int(c) - 1)
                    else:
                        selected_ids.append(field_ids[int(c) - 1])
        except SystemExit:
            self.cleanup_before_exit()
            sys.exit()
        except Exception:
            print(f"{ERROR} Invalid Tag Selection")

        if not allow_multiple and selected_ids:
            return [selected_ids[0]]
        return selected_ids

    def scr_edit_entry_text(
        self, entry_index, field_index, allow_newlines=True, clear_scr=True
    ):
        """Screen for editing an Entry text_line field."""

        title = f"{self.base_title} - Library '{self.lib.library_dir}'"

        entry = self.lib.entries[entry_index]
        filename = self.lib.library_dir / entry.path / entry.filename
        field_name = self.lib.get_field_attr(entry.fields[field_index], "name")
        subtitle = f'Editing "{field_name}" Field'
        h1 = f"{filename}"

        if clear_scr:
            clear()
        clear_scr = True
        print(self.format_title(title, color=f"{BLACK_FG}{BRIGHT_CYAN_BG}"))
        print(self.format_subtitle(subtitle))
        print(self.format_h1(h1, self.get_file_color(os.path.splitext(filename)[1])))
        print("")

        if not filename.is_file():
            print(
                f"{RED_BG}{BRIGHT_WHITE_FG}[File Missing]{RESET}{BRIGHT_RED_FG} (Run 'fix missing' to resolve){RESET}"
            )
            print("")
        else:
            self.print_thumbnail(entry_index, ignore_fields=True)

        print(
            self.format_title(
                "Opened with Default Text Editor", f"{BLACK_FG}{BRIGHT_CYAN_BG}"
            )
        )
        # print('')
        # print(
        # 	f'{BRIGHT_WHITE_BG}{BLACK_FG} {field_name}: {RESET} ')
        # print(self.lib.get_field_attr(entry.fields[field_index], 'content'))
        # for i, tag_id in enumerate(entry.fields[field_index][list(entry.fields[field_index].keys())[0]]):
        # 	tag = self.lib.get_tag_from_id(tag_id)
        # 	print(
        # 		f'{self.get_tag_color(tag.color)}[{i+1}]{RESET} {self.get_tag_color(tag.color)} {tag.display_name(self.lib)} {RESET}')
        # print('')

        # print(self.format_subtitle(
        # 	'Add <Tag Name>    Remove <#>    Open File    Close/Done    Quit'))

        # new_content: str = click.edit(self.lib.get_field_attr(
        # 	entry.fields[field_index], 'content'))
        new_content: str = ""  # NOTE: Removing
        if new_content is not None:
            if not allow_newlines:
                new_content = new_content.replace("\r", "").replace("\n", "")
            self.lib.update_entry_field(
                entry_index,
                field_index,
                new_content.rstrip("\n").rstrip("\r"),
                "replace",
            )

    def scr_list_tags(
        self, query: str = "", tag_ids: list[int] = None, clear_scr=True
    ) -> None:
        """A screen for listing out and performing CRUD operations on Library Tags."""
        # NOTE: While a screen that just displays the first 40 or so random tags on your screen
        # isn't really that useful, this is just a temporary measure to provide a launchpad
        # screen for necessary commands such as adding and editing tags.
        # A more useful screen presentation might look like a list of ranked occurrences, but
        # that can be figured out and implemented later.
        tag_ids = tag_ids or []
        title = f"{self.base_title} - Library '{self.lib.library_dir}'"

        while True:
            h1 = f"{len(self.lib.tags)} Tags"

            if tag_ids:
                if len(tag_ids) < len(self.lib.search_tags("")):
                    h1 = f"[{len(tag_ids)}/{len(self.lib.tags)}] Tags"
                    if query:
                        h1 += f" connected to '{query}'"
            else:
                h1 = "No Tags"
                if query:
                    h1 += f" connected to '{query}'"

            if clear_scr:
                clear()
            clear_scr = True
            print(self.format_title(title))
            print(self.format_h1(h1))
            print("")

            tag_tuple_list = []
            for tag_id in tag_ids:
                tag = self.lib.get_tag(tag_id)
                if self.args.debug:
                    tag_tuple_list.append(
                        (tag.debug_name(), self.get_tag_color(tag.color))
                    )
                else:
                    tag_tuple_list.append(
                        (tag.display_name(self.lib), self.get_tag_color(tag.color))
                    )

            self.print_columns(tag_tuple_list, add_enum=True)

            print("")
            print(
                self.format_subtitle(
                    "Create    Edit <#>    Delete <#>    Search <Query>    Close/Done",
                    BRIGHT_MAGENTA_FG,
                )
            )
            print("> ", end="")

            com: list[str] = input().strip().split(" ")
            gc, message = self.global_commands(com)
            if gc:
                if message:
                    clear()
                    print(message)
                    clear_scr = False
            else:
                com_name = com[0].lower()
                # Search Tags ==========================================================
                if com_name in ("search", "s"):
                    if len(com) > 1:
                        new_query: str = " ".join(com[1:])
                        # self.scr_list_tags(prev_scr, query=new_query,
                        # 				tag_ids=self.lib.filter_tags(new_query, include_cluster=True))
                        query = new_query
                        tag_ids = self.lib.search_tags(new_query, include_cluster=True)
                        # return
                    else:
                        # self.scr_list_tags(prev_scr, tag_ids=self.lib.filter_tags(''))
                        tag_ids = self.lib.search_tags("")
                        # return
                # Edit Tag ===========================================================
                elif com_name in ("edit", "e"):
                    if len(com) > 1:
                        try:
                            index = int(com[1]) - 1
                            if index < 0:
                                raise IndexError
                            self.scr_manage_tag(tag_ids[index])

                            # Refilter in case edits change results
                            tag_ids = self.lib.search_tags(query, include_cluster=True)
                            # self.scr_list_tags(prev_scr, query=query, tag_ids=tag_ids)
                            # return
                        # except SystemExit:
                        # 	self.cleanup_before_exit()
                        # 	sys.exit()
                        except (ValueError, IndexError):
                            clear()
                            print(f'{ERROR} Invalid Selection \'{" ".join(com[1])}\'')
                            clear_scr = False
                            # self.scr_list_tags(prev_scr, query=query,
                            # 				tag_ids=tag_ids, clear_scr=False)
                            # return

                # Create Tag ============================================================
                elif com_name in ("create", "mk"):
                    tag = Tag(
                        id=0,
                        name="New Tag",
                        shorthand="",
                        aliases=[],
                        subtags_ids=[],
                        color="",
                    )
                    self.scr_manage_tag(self.lib.add_tag_to_library(tag), mode="create")

                    tag_ids = self.lib.search_tags(query, include_cluster=True)

                    # self.scr_list_tags(prev_scr, query=query, tag_ids=tag_ids)
                    # return
                # Delete Tag ===========================================================
                elif com_name in ("delete", "del"):
                    if len(com) > 1:
                        if len(com) > 1:
                            try:
                                index = int(com[1]) - 1
                                if index < 0:
                                    raise IndexError
                                deleted = self.scr_delete_tag(tag_ids[index])
                                if deleted:
                                    tag_ids.remove(tag_ids[index])
                                    tag_ids = self.lib.search_tags(
                                        query, include_cluster=True
                                    )
                                # self.scr_list_tags(
                                # 	prev_scr, query=query, tag_ids=tag_ids)
                                # return
                            # except SystemExit:
                            # 	self.cleanup_before_exit()
                            # 	sys.exit()
                            except IndexError:
                                clear()
                                print(
                                    f'{ERROR} Invalid Selection \'{" ".join(com[1])}\''
                                )
                                clear_scr = False
                                # self.scr_list_tags(prev_scr, query=query,
                                # 				tag_ids=tag_ids, clear_scr=False)
                                # return
                # Close View ===========================================================
                elif com_name in ("close", "c", "done"):
                    # prev_scr()
                    return
                # # Quit =================================================================
                # elif com[0].lower() == 'quit' or com[0].lower() == 'q':
                # 	self.lib.save_library_to_disk()
                # 	# self.cleanup()
                # 	sys.exit()
                # # Quit without Saving ==================================================
                # elif com[0].lower() == 'quit!' or com[0].lower() == 'q!':
                # 	# self.cleanup()
                # 	sys.exit()
                # Unknown Command ======================================================
                else:
                    clear()
                    print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                    # self.scr_list_tags(prev_scr, query=query,
                    # 				tag_ids=tag_ids, clear_scr=False)
                    # return
                    clear_scr = False

    def scr_top_tags(self, clear_scr=True) -> None:
        """A screen that lists out the top tags for the library."""

        title = f"{self.base_title} - Library '{self.lib.library_dir}'"

        while True:
            h1 = "Top Tags"

            # if tag_ids:
            # 	if len(tag_ids) < len(self.lib.filter_tags('')):
            # 		h1 = f'[{len(tag_ids)}/{len(self.lib.tags)}] Tags'
            # 		if query:
            # 			h1 += f' connected to \'{query}\''
            # else:
            # 	h1 = f'No Tags'
            # 	if query:
            # 		h1 += f' connected to \'{query}\''

            if clear_scr:
                clear()
            clear_scr = True
            print(self.format_title(title))
            print(self.format_h1(h1))
            print("")

            tag_tuple_list = []
            for tag_id, count in self.lib.tag_entry_refs:
                tag = self.lib.get_tag(tag_id)
                if self.args.debug:
                    tag_tuple_list.append(
                        (f"{tag.debug_name()} - {count}", self.get_tag_color(tag.color))
                    )
                else:
                    tag_tuple_list.append(
                        (
                            f"{tag.display_name(self.lib)} - {count}",
                            self.get_tag_color(tag.color),
                        )
                    )

            self.print_columns(tag_tuple_list, add_enum=True)

            print("")
            print(self.format_subtitle("Close/Done", BRIGHT_MAGENTA_FG))
            print("> ", end="")

            com: list[str] = input().lstrip().rstrip().split(" ")
            gc, message = self.global_commands(com)
            if gc:
                if message:
                    clear()
                    print(message)
                    clear_scr = False
            else:
                # Close View ===================================================
                if (
                    com[0].lower() == "close"
                    or com[0].lower() == "c"
                    or com[0].lower() == "done"
                ):
                    return
                # Unknown Command ==============================================
                elif com[0]:
                    clear()
                    print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                    clear_scr = False

    def scr_manage_tag(self, tag_id: int, mode="edit", clear_scr=True):
        """Screen for editing fields of a Tag object."""

        title = f"{self.base_title} - Library '{self.lib.library_dir}'"

        while True:
            tag: Tag = self.lib.get_tag(tag_id)
            subtitle = (
                f'Editing Tag "{self.lib.get_tag(tag_id).display_name(self.lib)}"'
            )
            # h1 = f'{self.lib.tags[tag_index].display_name()}'

            fg_text_color = BLACK_FG
            fg_color = BRIGHT_CYAN_FG
            bg_color = BRIGHT_CYAN_BG
            if mode == "create":
                subtitle = (
                    f'Creating Tag "{self.lib.get_tag(tag_id).display_name(self.lib)}"'
                )
                fg_color = BRIGHT_GREEN_FG
                bg_color = BRIGHT_GREEN_BG
            # elif mode == 'remove':
            # 	# TODO: Uhh is this ever going to get used? Delete this when you know.
            # 	subtitle = f'Removing Tag \"{self.lib.get_tag_from_id(tag_id).display_name(self.lib)}\"'
            # 	fg_color = BRIGHT_RED_FG
            # 	bg_color = BRIGHT_RED_BG

            if clear_scr:
                clear()
            clear_scr = True
            print(self.format_title(title, color=f"{fg_text_color}{bg_color}"))
            print(self.format_subtitle(subtitle, fg_color))
            # print(self.format_h1(h1, self.get_file_color(
            # 	os.path.splitext(filename)[1])))
            if self.args.debug:
                print("")
                print(f"{BRIGHT_WHITE_BG}{BLACK_FG} ID: {RESET} ", end="")
                print(tag.id)

            print("")
            print(f"{BRIGHT_WHITE_BG}{BLACK_FG} Name: {RESET} ", end="")
            print(tag.name)

            print(f"{BRIGHT_WHITE_BG}{BLACK_FG} Shorthand: {RESET} ", end="")
            print(tag.shorthand)

            print("")
            print(f"{BRIGHT_WHITE_BG}{BLACK_FG} Aliases: {RESET} ", end="\n")
            for a in tag.aliases:
                print(f"{a}")

            print("")
            print(f"{BRIGHT_WHITE_BG}{BLACK_FG} Subtags: {RESET} ", end="\n")
            char_count: int = 0
            for id in tag.subtag_ids:
                st = self.lib.get_tag(id)
                # Properly wrap Tags on screen
                char_count += len(f" {st.display_name(self.lib)} ") + 1
                if char_count > os.get_terminal_size()[0]:
                    print("")
                    char_count = len(f" {st.display_name(self.lib)} ") + 1
                print(
                    f"{self.get_tag_color(st.color)} {st.display_name(self.lib)} {RESET}",
                    end="",
                )
                # If the tag isn't the last one, print a space for the next one.
                if id != tag.subtag_ids[-1]:
                    print(" ", end="")
                else:
                    print("")

            print("")
            print(f"{BRIGHT_WHITE_BG}{BLACK_FG} Color: {RESET} ", end="")
            print(f"{self.get_tag_color(tag.color)} {tag.color.title()} {RESET}")

            print("")
            print(self.format_subtitle("Edit <Field>    Close/Done", fg_color))
            print("> ", end="")

            com: list[str] = input().lstrip().rstrip().split(" ")
            gc, message = self.global_commands(com)
            if gc:
                if message:
                    clear()
                    print(message)
                    clear_scr = False
            else:
                # Edit Tag Field =======================================================
                if com[0].lower() == "edit" or com[0].lower() == "e":
                    if len(com) > 1:
                        selection: str = " ".join(com[1:]).lower()
                        if "id".startswith(selection) and self.args.debug:
                            clear()
                            print(f"{ERROR} Tag IDs are not editable.")
                            clear_scr = False
                        elif "name".startswith(selection):
                            new_name: str = self.scr_edit_text(
                                text=tag.name, field_name="Name", allow_newlines=False
                            )
                            new_tag: Tag = Tag(
                                id=tag.id,
                                name=new_name,
                                shorthand=tag.shorthand,
                                aliases=tag.aliases,
                                subtags_ids=tag.subtag_ids,
                                color=tag.color,
                            )
                            self.lib.update_tag(new_tag)
                            # self.scr_manage_tag(tag_id=tag_id, mode=mode)
                            # return
                            # clear_scr=False
                        elif "shorthand".startswith(selection):
                            new_shorthand: str = self.scr_edit_text(
                                text=tag.shorthand,
                                field_name="Shorthand",
                                allow_newlines=False,
                            )
                            new_tag: Tag = Tag(
                                id=tag.id,
                                name=tag.name,
                                shorthand=new_shorthand,
                                aliases=tag.aliases,
                                subtags_ids=tag.subtag_ids,
                                color=tag.color,
                            )
                            self.lib.update_tag(new_tag)
                            # self.scr_manage_tag(tag_id=tag_id, mode=mode)
                            # return
                            # clear_scr=False
                        elif "aliases".startswith(selection):
                            new_aliases: list[str] = self.scr_edit_text(
                                text="\n".join(tag.aliases),
                                field_name="Aliases",
                                note="# Tag Aliases Below Are Separated By Newlines",
                                allow_newlines=True,
                            ).split("\n")
                            new_tag: Tag = Tag(
                                id=tag.id,
                                name=tag.name,
                                shorthand=tag.shorthand,
                                aliases=new_aliases,
                                subtags_ids=tag.subtag_ids,
                                color=tag.color,
                            )
                            self.lib.update_tag(new_tag)
                            # self.scr_manage_tag(tag_id=tag_id, mode=mode)
                            # return
                            # clear_scr=False
                        elif "subtags".startswith(selection):
                            new_subtag_ids: list[int] = self.scr_edit_generic_tag_box(
                                tag_ids=tag.subtag_ids, tag_box_name="Subtags"
                            )
                            new_tag: Tag = Tag(
                                id=tag.id,
                                name=tag.name,
                                shorthand=tag.shorthand,
                                aliases=tag.aliases,
                                subtags_ids=new_subtag_ids,
                                color=tag.color,
                            )
                            self.lib.update_tag(new_tag)
                            # self.scr_manage_tag(tag_id=tag_id, mode=mode)
                            # return
                            # clear_scr=False
                        elif "color".startswith(selection):
                            new_color: str = self.scr_tag_color_dropdown(
                                fallback=tag.color, colors=TAG_COLORS
                            )
                            new_tag: Tag = Tag(
                                id=tag.id,
                                name=tag.name,
                                shorthand=tag.shorthand,
                                aliases=tag.aliases,
                                subtags_ids=tag.subtag_ids,
                                color=new_color,
                            )
                            self.lib.update_tag(new_tag)
                            # self.scr_manage_tag(tag_id=tag_id, mode=mode)
                            # return
                            # clear_scr=False
                        else:
                            clear()
                            print(f'{ERROR} Unknown Tag field "{" ".join(com[1:])}".')
                            # self.scr_manage_tag(tag_id, mode, clear_scr=False)
                            # return
                            clear_scr = False
                # Close View ===========================================================
                elif (
                    com[0].lower() == "close"
                    or com[0].lower() == "done"
                    or com[0].lower() == "c"
                ):
                    return
                # # Quit =================================================================
                # elif com[0].lower() == 'quit' or com[0].lower() == 'q':
                # 	self.lib.save_library_to_disk()
                # 	# self.cleanup()
                # 	sys.exit()
                # # Quit without Saving ==================================================
                # elif com[0].lower() == 'quit!' or com[0].lower() == 'q!':
                # 	# self.cleanup()
                # 	sys.exit()
                # Unknown Command ======================================================
                else:
                    clear()
                    print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                    clear_scr = False
                    # return self.scr_browse_entries_gallery(index, clear_scr=False)

    def scr_delete_tag(self, tag_id: int, clear_scr=True) -> bool:
        """Screen for confirming the deletion of a Tag."""

        title = f"{self.base_title} - Library '{self.lib.library_dir}'"

        tag: Tag = self.lib.get_tag(tag_id)
        subtitle = f'Confirm Deletion of Tag "{self.lib.get_tag(tag_id).display_name(self.lib)}"'
        # h1 = f'{self.lib.tags[tag_index].display_name()}'
        entry_ref_count, subtag_ref_count = self.lib.get_tag_ref_count(tag_id)

        fg_text_color = BLACK_FG
        fg_color = BRIGHT_RED_FG
        bg_color = BRIGHT_RED_BG

        if clear_scr:
            clear()
        clear_scr = True
        print(self.format_title(title, color=f"{fg_text_color}{bg_color}"))
        print(self.format_subtitle(subtitle, fg_color))
        print("")

        print(
            f"{INFO} {BRIGHT_WHITE_FG}This Tag is in {fg_color}{entry_ref_count}{RESET}{BRIGHT_WHITE_FG} Entries{RESET} ",
            end="",
        )
        print("")

        print(
            f"{INFO} {BRIGHT_WHITE_FG}This Tag is a Subtag for {fg_color}{subtag_ref_count}{RESET}{BRIGHT_WHITE_FG} Tags{RESET} ",
            end="",
        )
        print("")

        print("")
        print(f"{BRIGHT_WHITE_BG}{BLACK_FG} Name: {RESET} ", end="")
        print(tag.name)

        print(f"{BRIGHT_WHITE_BG}{BLACK_FG} Shorthand: {RESET} ", end="")
        print(tag.shorthand)

        print("")
        print(f"{BRIGHT_WHITE_BG}{BLACK_FG} Aliases: {RESET} ", end="\n")
        for a in tag.aliases:
            print(f"{a}")

        print("")
        print(f"{BRIGHT_WHITE_BG}{BLACK_FG} Subtags: {RESET} ", end="\n")
        char_count: int = 0
        for id in tag.subtag_ids:
            st = self.lib.get_tag(id)
            # Properly wrap Tags on screen
            char_count += len(f" {st.display_name(self.lib)} ") + 1
            if char_count > os.get_terminal_size()[0]:
                print("")
                char_count = len(f" {st.display_name(self.lib)} ") + 1
            print(
                f"{self.get_tag_color(st.color)} {st.display_name(self.lib)} {RESET}",
                end="",
            )
            # If the tag isn't the last one, print a space for the next one.
            if id != tag.subtag_ids[-1]:
                print(" ", end="")
            else:
                print("")

        print("")
        print(f"{BRIGHT_WHITE_BG}{BLACK_FG} Color: {RESET} ", end="")
        print(f"{self.get_tag_color(tag.color)} {tag.color.title()} {RESET}")

        print("")
        print(self.format_subtitle("Yes    Cancel", fg_color))
        print("> ", end="")

        com: str = input().rstrip()

        if com.lower() == "yes" or com.lower() == "y":
            self.lib.remove_tag(tag_id)
            return True

        return False

    def scr_edit_text(
        self,
        text: str,
        field_name: str,
        note: str = "",
        allow_newlines=True,
        clear_scr=True,
    ) -> str:
        """
        Screen for editing generic text. Currently used in Tag editing.\n
        `text`: The text to be edited and returned.\n
        `field_name`: The name to display of what is being edited.\n
        `note`: An optional help message to display on screen for users..\n
        `allow_newlines`: Determines if the text should be allowed to contain newlines.\n
        """
        # NOTE: This code is derived from scr_edit_entry_text, just without the
        # specific entry stuff like filenames and preview images. There may be
        # a good way to combine the methods in the future, but for now here's this.
        title = f"{self.base_title} - Library '{self.lib.library_dir}'"
        subtitle = f'Editing "{field_name}"'

        if clear_scr:
            clear()
        clear_scr = True
        print(self.format_title(title, color=f"{BLACK_FG}{BRIGHT_CYAN_BG}"))
        print(self.format_subtitle(subtitle))
        print("")

        print(
            self.format_title(
                "Opened with Default Text Editor", f"{BLACK_FG}{BRIGHT_CYAN_BG}"
            )
        )

        # new_text: str = click.edit(text)
        new_text: str = input()
        if new_text is not None:
            if not allow_newlines:
                new_text = new_text.replace("\r", "").replace("\n", "")
            else:
                new_text = new_text.rstrip("\n").rstrip("\r")
            return new_text
        return text

    def scr_tag_color_dropdown(
        self, fallback: str, colors: list[str], clear_scr=True
    ) -> str:
        """
        Screen for selecting and returning a string of a color name. Used in Tag editing.
        Fallback: The value to return if an invalid selection by the user was made.
        """

        title = f"{self.base_title} - Library '{self.lib.library_dir}'"
        subtitle = "Select Color"

        fg_text_color = BLACK_FG
        fg_color = BRIGHT_CYAN_FG
        bg_color = BRIGHT_CYAN_BG

        if clear_scr:
            clear()
        clear_scr = True

        print(self.format_title(title, color=f"{fg_text_color}{bg_color}"))
        print(self.format_subtitle(subtitle, fg_color))
        print("")

        color_tuple_list = []
        for color in colors:
            color_tuple_list.append((color.title(), self.get_tag_color(color)))

        self.print_columns(color_tuple_list, add_enum=True)
        print("")

        # for i, color in enumerate(colors):
        # 	if i < (os.get_terminal_size()[1] - 7):
        # 		print(
        # 			f'{self.get_tag_color(color)}[{i+1}]{RESET} {self.get_tag_color(color)} {color.title()} {RESET}')
        # 	else:
        # 		print(f'{WHITE_FG}[...]{RESET}')
        # 		break
        # print('')

        print(self.format_subtitle("Enter #    Cancel", fg_color))
        print("> ", end="")

        selected: str = input()
        try:
            if selected.isdigit() and 0 < int(selected) <= len(colors):
                selected = colors[int(selected) - 1]
                return selected
        # except SystemExit:
        # 	self.cleanup_before_exit()
        # 	sys.exit()
        except Exception:
            print(f"{ERROR} Invalid Tag Selection")

        return fallback

    def scr_edit_generic_tag_box(
        self, tag_ids: list[int], tag_box_name: str, clear_scr=True
    ) -> list[int]:
        """Screen for editing a generic tag_box. Used in Tag subtag modification."""

        title = f"{self.base_title} - Library '{self.lib.library_dir}'"

        while True:
            subtitle = f"Editing {tag_box_name}"

            if clear_scr:
                clear()
            clear_scr = True

            print(self.format_title(title, color=f"{BLACK_FG}{BRIGHT_CYAN_BG}"))
            print(self.format_subtitle(subtitle))
            print("")

            print(f"{BRIGHT_WHITE_BG}{BLACK_FG} {tag_box_name}: {RESET} ")
            for i, id in enumerate(tag_ids):
                tag = self.lib.get_tag(id)
                print(
                    f"{self.get_tag_color(tag.color)}[{i+1}]{RESET} {self.get_tag_color(tag.color)} {tag.display_name(self.lib)} {RESET}"
                )
            print("")

            print(
                self.format_subtitle(
                    "Add <Tag Name>    Remove <#>    Close/Done    Quit"
                )
            )
            print("> ", end="")

            com: list[str] = input().lstrip().rstrip().split(" ")
            gc, message = self.global_commands(com)
            if gc:
                if message:
                    clear()
                    print(message)
                    clear_scr = False
            else:
                # Add Tag ==============================================================
                if com[0].lower() == "add":
                    if len(com) > 1:
                        tag_list = self.lib.search_tags(
                            " ".join(com[1:]), include_cluster=True
                        )
                        selected_ids: list[int] = []
                        if len(tag_list) > 1:
                            selected_ids = self.scr_select_tags(tag_list)
                        else:
                            selected_ids = tag_list  # Single Tag
                        if selected_ids:
                            for id in selected_ids:
                                if id in tag_ids:
                                    selected_ids.remove(id)
                            return self.scr_edit_generic_tag_box(
                                tag_ids + selected_ids, tag_box_name
                            )
                            tag_ids = tag_ids + selected_ids
                        # else:
                        # 	return self.scr_edit_generic_tag_box(tag_ids, tag_box_name)
                # Remove Tag ===========================================================
                elif com[0].lower() == "remove" or com[0].lower() == "rm":
                    if len(com) > 1:
                        try:
                            # selected_tag_ids: list[int] = []
                            # for c in com[1:]:
                            # 	if (int(c)-1) < 0:
                            # 		raise IndexError
                            # 	selected_tag_ids.append(tag_ids[int(c[1])-1])
                            selected_id = tag_ids[int(com[1]) - 1]
                            tag_ids.remove(selected_id)
                            # return self.scr_edit_generic_tag_box(tag_ids, tag_box_name)
                        # except SystemExit:
                        # 	self.cleanup_before_exit()
                        # 	sys.exit()
                        except Exception:
                            clear()
                            print(f"{ERROR} Invalid Tag Selection '{com[1:]}'")
                            # return self.scr_edit_generic_tag_box(tag_ids, tag_box_name, clear_scr=False)
                            clear_scr = False
                # Close View ===========================================================
                elif (
                    com[0].lower() == "close"
                    or com[0].lower() == "c"
                    or com[0].lower() == "done"
                ):
                    # clear()
                    # pass
                    return tag_ids
                # # Quit =================================================================
                # elif com[0].lower() == 'quit' or com[0].lower() == 'q':
                # 	self.lib.save_library_to_disk()
                # 	# self.cleanup()
                # 	sys.exit()
                # # Quit without Saving ==================================================
                # elif com[0].lower() == 'quit!' or com[0].lower() == 'q!':
                # 	# self.cleanup()
                # 	sys.exit()
                # Unknown Command ======================================================
                else:
                    clear()
                    print(f'{ERROR} Unknown command \'{" ".join(com)}\'')
                    # return self.scr_edit_generic_tag_box(tag_ids, tag_box_name, clear_scr=False)
                    clear_scr = False

            # return tag_ids
