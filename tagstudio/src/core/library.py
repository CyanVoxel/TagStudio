# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio

"""The Library object and related methods for TagStudio."""

import datetime
import logging
import os
import time
import traceback
import xml.etree.ElementTree as ET
import ujson

from enum import Enum
from pathlib import Path
from typing import cast, Generator
from typing_extensions import Self

from src.core.json_typing import JsonCollation, JsonEntry, JsonLibary, JsonTag
from src.core.utils.str import strip_punctuation
from src.core.utils.web import strip_web_protocol
from src.core.enums import SearchMode
from src.core.constants import (
    BACKUP_FOLDER_NAME,
    COLLAGE_FOLDER_NAME,
    TEXT_FIELDS,
    TS_FOLDER_NAME,
    VERSION,
)

TYPE = ["file", "meta", "alt", "mask"]


# RESULT_TYPE = Enum('Result', ['ENTRY', 'COLLATION', 'TAG_GROUP'])
class ItemType(Enum):
    ENTRY = 0
    COLLATION = 1
    TAG_GROUP = 2


logging.basicConfig(format="%(message)s", level=logging.INFO)


class Entry:
    """A Library Entry Object. Referenced by ID."""

    def __init__(
        self, id: int, filename: str | Path, path: str | Path, fields: list[dict]
    ) -> None:
        # Required Fields ======================================================
        self.id = int(id)
        self.filename = Path(filename)
        self.path = Path(path)
        self.fields: list[dict] = fields
        self.type = None

        # Optional Fields ======================================================
        # # Any Type
        # self.alts: list[id] = None
        # # Image/Video
        # self.crop: tuple[int, int, int, int] = None
        # self.mask: list[id] = None
        # # Video
        # self.trim: tuple[float, float] = None

        # Handy Data ===========================================================
        # # Any Type
        # self.date_created: datetime.datetime = None
        # self.date_modified: datetime.datetime = None
        # self.file_size: int = None
        # self.isArchived: bool = None
        # self.isFavorite: bool = None
        # # Image/Video
        # self.dimensions: tuple[int, int] = None
        # # Video
        # self.length: float = None
        # # Text
        # self.word_count: int = None

    def __str__(self) -> str:
        return f"\n{self.compressed_dict()}\n"

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, __value: object) -> bool:
        __value = cast(Self, __value)
        return (
            int(self.id) == int(__value.id)
            and self.filename == __value.filename
            and self.path == __value.path
            and self.fields == __value.fields
        )

    def compressed_dict(self) -> JsonEntry:
        """
        An alternative to __dict__ that only includes fields containing
        non-default data.
        """
        obj: JsonEntry = {"id": self.id}
        if self.filename:
            obj["filename"] = str(self.filename)
        if self.path:
            obj["path"] = str(self.path)
        if self.fields:
            obj["fields"] = self.fields

        return obj

    def has_tag(self, library: "Library", tag_id: int) -> bool:
        if self.fields:
            for f in self.fields:
                if library.get_field_attr(f, "type") == "tag_box":
                    if tag_id in library.get_field_attr(f, "content"):
                        return True
        return False

    def remove_tag(self, library: "Library", tag_id: int, field_index=-1):
        """
        Removes a Tag from the Entry. If given a field index, the given Tag will
        only be removed from that index. If left blank, all instances of that
        Tag will be removed from the Entry.
        """
        if self.fields:
            for i, f in enumerate(self.fields):
                if library.get_field_attr(f, "type") == "tag_box":
                    if field_index >= 0 and field_index == i:
                        t: list[int] = library.get_field_attr(f, "content")
                        logging.info(
                            f't:{tag_id}, i:{i}, idx:{field_index}, c:{library.get_field_attr(f, "content")}'
                        )
                        t.remove(tag_id)
                    elif field_index < 0:
                        t = library.get_field_attr(f, "content")
                        while tag_id in t:
                            t.remove(tag_id)

    def add_tag(
        self, library: "Library", tag_id: int, field_id: int, field_index: int = -1
    ):
        # if self.fields:
        # if field_index != -1:
        # logging.info(f'[LIBRARY] ADD TAG to E:{self.id}, F-DI:{field_id}, F-INDEX:{field_index}')
        for i, f in enumerate(self.fields):
            if library.get_field_attr(f, "id") == field_id:
                field_index = i
                # logging.info(f'[LIBRARY] FOUND F-INDEX:{field_index}')
                break

        if field_index == -1:
            library.add_field_to_entry(self.id, field_id)
            # logging.info(f'[LIBRARY] USING NEWEST F-INDEX:{field_index}')

        # logging.info(list(self.fields[field_index].keys()))
        field_id = list(self.fields[field_index].keys())[0]
        # logging.info(f'Entry Field ID: {field_id}, Index: {field_index}')

        tags: list[int] = self.fields[field_index][field_id]
        if tag_id not in tags:
            # logging.info(f'Adding Tag: {tag_id}')
            tags.append(tag_id)
            self.fields[field_index][field_id] = sorted(
                tags, key=lambda t: library.get_tag(t).display_name(library)
            )

        # logging.info(f'Tags: {self.fields[field_index][field_id]}')


class Tag:
    """A Library Tag Object. Referenced by ID."""

    def __init__(
        self,
        id: int,
        name: str,
        shorthand: str,
        aliases: list[str],
        subtags_ids: list[int],
        color: str,
    ) -> None:
        self.id = int(id)
        self.name = name
        self.shorthand = shorthand
        self.aliases = aliases
        # Ensures no duplicates while retaining order.
        self.subtag_ids: list[int] = []
        for s in subtags_ids:
            if int(s) not in self.subtag_ids:
                self.subtag_ids.append(int(s))
        # [int(s) for s in subtags_ids]
        self.color = color

    def __str__(self) -> str:
        return (
            f"\nID: {self.id}\nName: {self.name}\n"
            f"Shorthand: {self.shorthand}\nAliases: {self.aliases}\n"
            f"Subtags: {self.subtag_ids}\nColor: {self.color}\n"
        )

    def __repr__(self) -> str:
        return self.__str__()

    def debug_name(self) -> str:
        """Returns a formatted tag name intended for displaying."""
        # return (f'{self.name} (ID: {self.id}) Subtags: {self.subtag_ids}')
        return f"{self.name} (ID: {self.id})"

    def display_name(self, library: "Library") -> str:
        """Returns a formatted tag name intended for displaying."""
        if self.subtag_ids:
            if library.get_tag(self.subtag_ids[0]).shorthand:
                return (
                    f"{self.name}" f" ({library.get_tag(self.subtag_ids[0]).shorthand})"
                )
            else:
                return f"{self.name}" f" ({library.get_tag(self.subtag_ids[0]).name})"
        else:
            return f"{self.name}"

    def compressed_dict(self) -> JsonTag:
        """
        An alternative to __dict__ that only includes fields containing
        non-default data.
        """
        obj: JsonTag = {"id": self.id}
        if self.name:
            obj["name"] = self.name
        if self.shorthand:
            obj["shorthand"] = self.shorthand
        if self.aliases:
            obj["aliases"] = self.aliases
        if self.subtag_ids:
            obj["subtag_ids"] = self.subtag_ids
        if self.color:
            obj["color"] = self.color

        return obj

    def add_subtag(self, tag_id: int):
        if tag_id not in self.subtag_ids:
            self.subtag_ids.append(tag_id)

    def remove_subtag(self, tag_id: int):
        try:
            self.subtag_ids.remove(tag_id)
        except ValueError:
            pass


class Collation:
    """
    A Library Collation Object. Referenced by ID.
    Entries and their Page #s are grouped together in the e_ids_and_paged tuple.
    Sort order is `(filename | title | date, asc | desc)`.
    """

    def __init__(
        self,
        id: int,
        title: str,
        e_ids_and_pages: list[tuple[int, int]],
        sort_order: str,
        cover_id: int = -1,
    ) -> None:
        self.id = int(id)
        self.title = title
        self.e_ids_and_pages = e_ids_and_pages
        self.sort_order = sort_order
        self.cover_id = cover_id
        self.fields = None  # Optional Collation-wide fields. WIP.

    def __str__(self) -> str:
        return f"\n{self.compressed_dict()}\n"

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, __value: object) -> bool:
        __value = cast(Self, __value)
        return int(self.id) == int(__value.id) and self.fields == __value.fields

    def compressed_dict(self) -> JsonCollation:
        """
        An alternative to __dict__ that only includes fields containing
        non-default data.
        """
        obj: JsonCollation = {"id": self.id}
        if self.title:
            obj["title"] = self.title
        if self.e_ids_and_pages:
            # TODO: work with tuples
            obj["e_ids_and_pages"] = [list(x) for x in self.e_ids_and_pages]
            # obj['e_ids_and_pages'] = self.e_ids_and_pages
        if self.sort_order:
            obj["sort_order"] = self.sort_order
        if self.cover_id:
            obj["cover_id"] = self.cover_id

        return obj


class Library:
    """Class for the Library object, and all CRUD operations made upon it."""

    def __init__(self) -> None:
        # Library Info =========================================================
        self.library_dir: Path = None

        # Entries ==============================================================
        # List of every Entry object.
        self.entries: list[Entry] = []
        self._next_entry_id: int = 0
        # Map of every Entry ID to the index of the Entry in self.entries.
        self._entry_id_to_index_map: dict[int, int] = {}
        # # List of filtered Entry indexes generated by the filter_entries() method.
        # self.filtered_entries: list[int] = []
        # Duplicate Entries
        # Defined by Entries that point to files that one or more other Entries are also pointing to.
        # tuple(int, list[int])
        self.dupe_entries: list[tuple[int, list[int]]] = []

        # Collations ===========================================================
        # List of every Collation object.
        self.collations: list[Collation] = []
        self._next_collation_id: int = 0
        self._collation_id_to_index_map: dict[int, int] = {}

        # File Interfacing =====================================================
        self.dir_file_count: int = -1
        self.files_not_in_library: list[Path] = []
        self.missing_files: list[Path] = []
        self.fixed_files: list[Path] = []  # TODO: Get rid of this.
        self.missing_matches: dict = {}
        # Duplicate Files
        # Defined by files that are exact or similar copies to others. Generated by DupeGuru.
        # (Filepath, Matched Filepath, Match Percentage)
        self.dupe_files: list[tuple[Path, Path, int]] = []
        # Maps the filenames of entries in the Library to their entry's index in the self.entries list.
        #   Used for O(1) lookup of a file based on the current index (page number - 1) of the image being looked at.
        #   That filename can then be used to provide quick lookup to image metadata entries in the Library.
        self.filename_to_entry_id_map: dict[Path, int] = {}
        # A list of file extensions to be ignored by TagStudio.
        self.default_ext_blacklist: list = [".json", ".xmp", ".aae"]
        self.ignored_extensions: list = self.default_ext_blacklist

        # Tags =================================================================
        # List of every Tag object (ts-v8).
        self.tags: list[Tag] = []
        self._next_tag_id: int = 1000
        # Map of each Tag ID with its entry reference count.
        self._tag_entry_ref_map: dict[int, int] = {}
        self.tag_entry_refs: list[tuple[int, int]] = []
        # Map of every Tag name and alias to the ID(s) of its associated Tag(s).
        #   Used for O(1) lookup of Tag IDs based on search terms.
        #   NOTE: While it is recommended to keep Tag aliases unique to each Tag,
        #   there may be circumstances where this is not possible or elegant.
        #   Because of this, names and aliases are mapped to a list of IDs rather than a
        #   singular ID to handle potential alias collision.
        self._tag_strings_to_id_map: dict[str, list[int]] = {}
        # Map of every Tag ID to an array of Tag IDs that make up the Tag's "cluster", aka a list
        # of references from other Tags that specify this Tag as one of its subtags.
        #   This in effect is like a reverse subtag map.
        #   Used for O(1) lookup of the Tags to return in a query given a Tag ID.
        self._tag_id_to_cluster_map: dict[int, list[int]] = {}
        # Map of every Tag ID to the index of the Tag in self.tags.
        self._tag_id_to_index_map: dict[int, int] = {}

        self.default_tags: list[JsonTag] = [
            {"id": 0, "name": "Archived", "aliases": ["Archive"], "color": "Red"},
            {
                "id": 1,
                "name": "Favorite",
                "aliases": ["Favorited", "Favorites"],
                "color": "Yellow",
            },
        ]

        # self.default_tags = [
        # 	Tag(id=0, name='Archived', shorthand='', aliases=['Archive'], subtags_ids=[], color='red'),
        # 	Tag(id=1, name='Favorite', shorthand='', aliases=['Favorited, Favorites, Likes, Liked, Loved'], subtags_ids=[], color='yellow'),
        # ]

        self.default_fields: list[dict] = [
            {"id": 0, "name": "Title", "type": "text_line"},
            {"id": 1, "name": "Author", "type": "text_line"},
            {"id": 2, "name": "Artist", "type": "text_line"},
            {"id": 3, "name": "URL", "type": "text_line"},
            {"id": 4, "name": "Description", "type": "text_box"},
            {"id": 5, "name": "Notes", "type": "text_box"},
            {"id": 6, "name": "Tags", "type": "tag_box"},
            {"id": 7, "name": "Content Tags", "type": "tag_box"},
            {"id": 8, "name": "Meta Tags", "type": "tag_box"},
            {"id": 9, "name": "Collation", "type": "collation"},
            {"id": 10, "name": "Date", "type": "datetime"},
            {"id": 11, "name": "Date Created", "type": "datetime"},
            {"id": 12, "name": "Date Modified", "type": "datetime"},
            {"id": 13, "name": "Date Taken", "type": "datetime"},
            {"id": 14, "name": "Date Published", "type": "datetime"},
            {"id": 15, "name": "Archived", "type": "checkbox"},
            {"id": 16, "name": "Favorite", "type": "checkbox"},
            {"id": 17, "name": "Book", "type": "collation"},
            {"id": 18, "name": "Comic", "type": "collation"},
            {"id": 19, "name": "Series", "type": "collation"},
            {"id": 20, "name": "Manga", "type": "collation"},
            {"id": 21, "name": "Source", "type": "text_line"},
            {"id": 22, "name": "Date Uploaded", "type": "datetime"},
            {"id": 23, "name": "Date Released", "type": "datetime"},
            {"id": 24, "name": "Volume", "type": "collation"},
            {"id": 25, "name": "Anthology", "type": "collation"},
            {"id": 26, "name": "Magazine", "type": "collation"},
            {"id": 27, "name": "Publisher", "type": "text_line"},
            {"id": 28, "name": "Guest Artist", "type": "text_line"},
            {"id": 29, "name": "Composer", "type": "text_line"},
            {"id": 30, "name": "Comments", "type": "text_box"},
        ]

    def create_library(self, path: Path) -> int:
        """
        Creates a TagStudio library in the given directory.\n
        Return Codes:\n
        0: Library Successfully Created\n
        2: File creation error
        """

        path = self._fix_lib_path(path)

        try:
            self.clear_internal_vars()
            self.library_dir = Path(path)
            self.verify_ts_folders()
            self.save_library_to_disk()
            self.open_library(self.library_dir)
        except:
            traceback.print_exc()
            return 2

        return 0

    def _fix_lib_path(self, path) -> Path:
        """If '.TagStudio' is included in the path, trim the path up to it."""
        path = Path(path)
        paths = [x for x in [path, *path.parents] if x.stem == TS_FOLDER_NAME]
        if len(paths) > 0:
            return paths[0].parent
        return path

    def verify_ts_folders(self) -> None:
        """Verifies/creates folders required by TagStudio."""

        full_ts_path = self.library_dir / TS_FOLDER_NAME
        full_backup_path = self.library_dir / TS_FOLDER_NAME / BACKUP_FOLDER_NAME
        full_collage_path = self.library_dir / TS_FOLDER_NAME / COLLAGE_FOLDER_NAME

        if not os.path.isdir(full_ts_path):
            os.mkdir(full_ts_path)

        if not os.path.isdir(full_backup_path):
            os.mkdir(full_backup_path)

        if not os.path.isdir(full_collage_path):
            os.mkdir(full_collage_path)

    def verify_default_tags(self, tag_list: list[JsonTag]) -> list[JsonTag]:
        """
        Ensures that the default builtin tags  are present in the Library's
        save file. Takes in and returns the tag dictionary from the JSON file.
        """
        missing: list[JsonTag] = []

        for dt in self.default_tags:
            if dt["id"] not in [t["id"] for t in tag_list]:
                missing.append(dt)

        for m in missing:
            tag_list.append(m)

        return tag_list

    def open_library(self, path: str | Path) -> int:
        """
        Opens a TagStudio v9+ Library.
        Returns 0 if library does not exist, 1 if successfully opened, 2 if corrupted.
        """

        return_code: int = 2

        _path: Path = self._fix_lib_path(path)

        if (_path / TS_FOLDER_NAME / "ts_library.json").exists():
            try:
                with open(
                    _path / TS_FOLDER_NAME / "ts_library.json",
                    "r",
                    encoding="utf-8",
                ) as file:
                    json_dump: JsonLibary = ujson.load(file)
                    self.library_dir = Path(_path)
                    self.verify_ts_folders()
                    major, minor, patch = json_dump["ts-version"].split(".")

                    # Load Extension Blacklist ---------------------------------
                    if "ignored_extensions" in json_dump.keys():
                        self.ignored_extensions = json_dump["ignored_extensions"]

                    # Parse Tags ---------------------------------------------------
                    if "tags" in json_dump.keys():
                        start_time = time.time()

                        # Step 1: Verify default built-in tags are present.
                        json_dump["tags"] = self.verify_default_tags(json_dump["tags"])

                        for tag in json_dump["tags"]:
                            # Step 2: Create a Tag object and append it to the internal Tags list,
                            # then map that Tag's ID to its index in the Tags list.

                            id = int(tag.get("id", 0))

                            # Don't load tags with duplicate IDs
                            if id not in {t.id for t in self.tags}:
                                if id >= self._next_tag_id:
                                    self._next_tag_id = id + 1

                                name = tag.get("name", "")
                                shorthand = tag.get("shorthand", "")
                                aliases = tag.get("aliases", [])
                                subtag_ids = tag.get("subtag_ids", [])
                                color = tag.get("color", "")

                                t = Tag(
                                    id=id,
                                    name=name,
                                    shorthand=shorthand,
                                    aliases=aliases,
                                    subtags_ids=subtag_ids,
                                    color=color,
                                )

                                # NOTE: This does NOT use the add_tag_to_library() method!
                                # That method is only used for Tags added at runtime.
                                # This process uses the same inner methods, but waits until all of the
                                # Tags are registered in the Tags list before creating the Tag clusters.
                                self.tags.append(t)
                                self._map_tag_id_to_index(t, -1)
                                self._map_tag_strings_to_tag_id(t)
                            else:
                                logging.info(
                                    f"[LIBRARY]Skipping Tag with duplicate ID: {tag}"
                                )

                        # Step 3: Map each Tag's subtags together now that all Tag objects in it.
                        for t in self.tags:
                            self._map_tag_id_to_cluster(t)

                        end_time = time.time()
                        logging.info(
                            f"[LIBRARY] Tags loaded in {(end_time - start_time):.3f} seconds"
                        )

                    # Parse Entries ------------------------------------------------
                    if entries := json_dump.get("entries"):
                        start_time = time.time()
                        for entry in entries:
                            if "id" in entry:
                                id = int(entry["id"])
                                if id >= self._next_entry_id:
                                    self._next_entry_id = id + 1
                            else:
                                # Version 9.1.x+ Compatibility
                                id = self._next_entry_id
                                self._next_entry_id += 1

                            filename = entry.get("filename", "")
                            e_path = entry.get("path", "")
                            fields: list = []
                            if "fields" in entry:
                                # Cast JSON str keys to ints

                                for f in entry["fields"]:
                                    f[int(list(f.keys())[0])] = f[list(f.keys())[0]]
                                    del f[list(f.keys())[0]]
                                fields = entry["fields"]

                            # Look through fields for legacy Collation data --------
                            if int(major) >= 9 and int(minor) < 1:
                                for f in fields:
                                    if self.get_field_attr(f, "type") == "collation":
                                        # NOTE: This legacy support will be removed in
                                        # a later version, probably 9.2.
                                        # Legacy Collation data present in v9.0.x
                                        # DATA SHAPE: {name: str, page: int}

                                        # We'll do an inefficient linear search each
                                        # time to convert the legacy data.
                                        matched = False
                                        collation_id = -1
                                        for c in self.collations:
                                            if (
                                                c.title
                                                == self.get_field_attr(f, "content")[
                                                    "name"
                                                ]
                                            ):
                                                c.e_ids_and_pages.append(
                                                    (
                                                        id,
                                                        int(
                                                            self.get_field_attr(
                                                                f, "content"
                                                            )["page"]
                                                        ),
                                                    )
                                                )
                                                matched = True
                                                collation_id = c.id
                                        if not matched:
                                            c = Collation(
                                                id=self._next_collation_id,
                                                title=self.get_field_attr(f, "content")[
                                                    "name"
                                                ],
                                                e_ids_and_pages=[],
                                                sort_order="",
                                            )
                                            collation_id = self._next_collation_id
                                            self._next_collation_id += 1
                                            c.e_ids_and_pages.append(
                                                (
                                                    id,
                                                    int(
                                                        self.get_field_attr(
                                                            f, "content"
                                                        )["page"]
                                                    ),
                                                )
                                            )
                                            self.collations.append(c)
                                            self._map_collation_id_to_index(c, -1)
                                        f_id = self.get_field_attr(f, "id")
                                        f.clear()
                                        f[int(f_id)] = collation_id
                            # Collation Field data present in v9.1.x+
                            # DATA SHAPE: int
                            elif int(major) >= 9 and int(minor) >= 1:
                                pass

                            e = Entry(
                                id=int(id),
                                filename=filename,
                                path=e_path,
                                fields=fields,
                            )
                            self.entries.append(e)
                            self._map_entry_id_to_index(e, -1)

                        end_time = time.time()
                        logging.info(
                            f"[LIBRARY] Entries loaded in {(end_time - start_time):.3f} seconds"
                        )

                    # Parse Collations ---------------------------------------------------
                    if "collations" in json_dump.keys():
                        start_time = time.time()
                        for collation in json_dump["collations"]:
                            # Step 1: Create a Collation object and append it to
                            # the internal Collations list, then map that
                            # Collation's ID to its index in the Collations list.

                            id = int(collation.get("id", 0))
                            if id >= self._next_collation_id:
                                self._next_collation_id = id + 1

                            title = collation.get("title", "")
                            e_ids_and_pages = collation.get("e_ids_and_pages", [])
                            sort_order = collation.get("sort_order", "")
                            cover_id = collation.get("cover_id", -1)

                            c = Collation(
                                id=id,
                                title=title,
                                e_ids_and_pages=e_ids_and_pages,  # type: ignore
                                sort_order=sort_order,
                                cover_id=cover_id,
                            )

                            # NOTE: This does NOT use the add_collation_to_library() method
                            # which is intended to be used at runtime. However, there is
                            # currently no reason why it couldn't be used here, and is
                            # instead not used for consistency.
                            self.collations.append(c)
                            self._map_collation_id_to_index(c, -1)
                        end_time = time.time()
                        logging.info(
                            f"[LIBRARY] Collations loaded in {(end_time - start_time):.3f} seconds"
                        )

                    return_code = 1
            except ujson.JSONDecodeError:
                logging.info("[LIBRARY][ERROR]: Empty JSON file!")

        # If the Library is loaded, continue other processes.
        if return_code == 1:
            (self.library_dir / TS_FOLDER_NAME).mkdir(parents=True, exist_ok=True)
            self._map_filenames_to_entry_ids()

        return return_code

    # @deprecated('Use new Entry ID system.')
    def _map_filenames_to_entry_ids(self):
        """Maps a full filepath to its corresponding Entry's ID."""
        self.filename_to_entry_id_map.clear()
        for entry in self.entries:
            self.filename_to_entry_id_map[(entry.path / entry.filename)] = entry.id

    # def _map_filenames_to_entry_ids(self):
    # 	"""Maps the file paths of entries to their index in the library list."""
    # 	self.file_to_entry_index_map.clear()
    # 	for i, entry in enumerate(self.entries):
    # 		if os.name == 'nt':
    # 			self.file_to_entry_index_map[str(os.path.normpath(
    # 				f'{entry.path}/{entry.filename}')).lower()] = i
    # 		else:
    # 			self.file_to_entry_index_map[str(
    # 				os.path.normpath(f'{entry.path}/{entry.filename}'))] = i

    # def close_library(self, save: bool = True):
    # 	"""Closes the open TagStudio Library."""
    # 	self.clear_internal_vars()

    def to_json(self):
        """
        Creates a JSON serialized string from the Library object.
        Used in saving the library to disk.
        """

        file_to_save: JsonLibary = {
            "ts-version": VERSION,
            "ignored_extensions": [],
            "tags": [],
            "collations": [],
            "fields": [],
            "macros": [],
            "entries": [],
        }

        print("[LIBRARY] Formatting Tags to JSON...")

        file_to_save["ignored_extensions"] = [i for i in self.ignored_extensions if i]

        for tag in self.tags:
            file_to_save["tags"].append(tag.compressed_dict())

        file_to_save["tags"] = self.verify_default_tags(file_to_save["tags"])
        print("[LIBRARY] Formatting Entries to JSON...")
        for entry in self.entries:
            file_to_save["entries"].append(entry.compressed_dict())

        print("[LIBRARY] Formatting Collations to JSON...")
        for collation in self.collations:
            file_to_save["collations"].append(collation.compressed_dict())

        print("[LIBRARY] Done Formatting to JSON!")
        return file_to_save

    def save_library_to_disk(self):
        """Saves the Library to disk at the default TagStudio folder location."""

        logging.info(f"[LIBRARY] Saving Library to Disk...")
        start_time = time.time()
        filename = "ts_library.json"

        self.verify_ts_folders()

        with open(
            self.library_dir / TS_FOLDER_NAME / filename, "w", encoding="utf-8"
        ) as outfile:
            outfile.flush()
            ujson.dump(
                self.to_json(),
                outfile,
                ensure_ascii=False,
                escape_forward_slashes=False,
            )
            # , indent=4 <-- How to prettyprint dump
        end_time = time.time()
        logging.info(
            f"[LIBRARY] Library saved to disk in {(end_time - start_time):.3f} seconds"
        )

    def save_library_backup_to_disk(self) -> str:
        """
        Saves a backup file of the Library to disk at the default TagStudio folder location.
        Returns the filename used, including the date and time."""

        logging.info(f"[LIBRARY] Saving Library Backup to Disk...")
        start_time = time.time()
        filename = f'ts_library_backup_{datetime.datetime.utcnow().strftime("%F_%T").replace(":", "")}.json'

        self.verify_ts_folders()
        with open(
            self.library_dir / TS_FOLDER_NAME / BACKUP_FOLDER_NAME / filename,
            "w",
            encoding="utf-8",
        ) as outfile:
            outfile.flush()
            ujson.dump(
                self.to_json(),
                outfile,
                ensure_ascii=False,
                escape_forward_slashes=False,
            )
        end_time = time.time()
        logging.info(
            f"[LIBRARY] Library backup saved to disk in {(end_time - start_time):.3f} seconds"
        )
        return filename
        # , indent=4 <-- How to prettyprint dump

    def clear_internal_vars(self):
        """Clears the internal variables of the Library object."""
        self.library_dir = None
        self.is_legacy_library = False

        self.entries.clear()
        self._next_entry_id = 0
        # self.filtered_entries.clear()
        self._entry_id_to_index_map.clear()

        self._collation_id_to_index_map.clear()

        self.missing_matches = {}
        self.dir_file_count = -1
        self.files_not_in_library.clear()
        self.missing_files.clear()
        self.fixed_files.clear()
        self.filename_to_entry_id_map: dict[Path, int] = {}
        self.ignored_extensions = self.default_ext_blacklist

        self.tags.clear()
        self._next_tag_id = 1000
        self._tag_strings_to_id_map = {}
        self._tag_id_to_cluster_map = {}
        self._tag_id_to_index_map = {}
        self._tag_entry_ref_map.clear()

    def refresh_dir(self) -> Generator:
        """Scans a directory for files, and adds those relative filenames to internal variables."""

        # Reset file interfacing variables.
        # -1 means uninitialized, aka a scan like this was never attempted before.
        self.dir_file_count = 0
        self.files_not_in_library.clear()

        # Scans the directory for files, keeping track of:
        #   - Total file count
        #   - Files without library entries
        # for type in TYPES:
        start_time = time.time()
        for f in self.library_dir.glob("**/*"):
            try:
                if (
                    "$RECYCLE.BIN" not in f.parts
                    and TS_FOLDER_NAME not in f.parts
                    and "tagstudio_thumbs" not in f.parts
                    and not f.is_dir()
                ):
                    if f.suffix not in self.ignored_extensions:
                        self.dir_file_count += 1
                        file = f.relative_to(self.library_dir)
                        try:
                            _ = self.filename_to_entry_id_map[file]
                        except KeyError:
                            # print(file)
                            self.files_not_in_library.append(file)
            except PermissionError:
                logging.info(
                    f"The File/Folder {f} cannot be accessed, because it requires higher permission!"
                )
            end_time = time.time()
            # Yield output every 1/30 of a second
            if (end_time - start_time) > 0.034:
                yield self.dir_file_count
                start_time = time.time()
        # Sorts the files by date modified, descending.
        if len(self.files_not_in_library) <= 100000:
            try:
                self.files_not_in_library = sorted(
                    self.files_not_in_library,
                    key=lambda t: -(self.library_dir / t).stat().st_ctime,
                )
            except (FileExistsError, FileNotFoundError):
                print(
                    "[LIBRARY] [ERROR] Couldn't sort files, some were moved during the scanning/sorting process."
                )
                pass
        else:
            print(
                "[LIBRARY][INFO] Not bothering to sort files because there's OVER 100,000! Better sorting methods will be added in the future."
            )

    def refresh_missing_files(self):
        """Tracks the number of Entries that point to an invalid file path."""
        self.missing_files.clear()
        for i, entry in enumerate(self.entries):
            full_path = self.library_dir / entry.path / entry.filename
            if not full_path.is_file():
                self.missing_files.append(full_path.resolve())
            yield i

    def remove_entry(self, entry_id: int) -> None:
        """Removes an Entry from the Library."""
        # del self.entries[entry_index]
        # self._map_filenames_to_entry_indices()

        # Step [1/2]:
        # Remove this Entry from the Entries list.
        entry = self.get_entry(entry_id)
        path = entry.path / entry.filename
        # logging.info(f'Removing path: {path}')

        del self.filename_to_entry_id_map[path]

        del self.entries[self._entry_id_to_index_map[entry_id]]

        # self.entries.remove(self.entries[self._entry_id_to_index_map[entry_id]])

        # Step [2/2]:
        # Remap the other Entry IDs to their new indices in the Entries list.
        self._entry_id_to_index_map.clear()
        for i, e in enumerate(self.entries):
            self._map_entry_id_to_index(e, i)

        # # Step [3/3]:
        # # Remap filenames to new indices.
        # self._map_filenames_to_entry_ids()

    def refresh_dupe_entries(self):
        """
        Refreshes the list of duplicate Entries.
        A duplicate Entry is defined as an Entry pointing to a file that one or more
        other Entries are also pointing to.\n
        `dupe_entries = tuple(int, list[int])`
        """

        self.dupe_entries.clear()
        registered: dict = {}  # string: list[int]

        # Registered: filename : list[ALL entry IDs pointing to this filename]
        # Dupe Entries: primary ID : list of [every OTHER entry ID pointing]

        for i, e in enumerate(self.entries):
            file: Path = Path() / e.path / e.filename
            # If this unique filepath has not been marked as checked,
            if not registered.get(file, None):
                # Register the filepath as having been checked, and include
                # its entry ID as the first entry in the corresponding list.
                registered[file] = [e.id]
            # Else if the filepath is already been seen in another entry,
            else:
                # Add this new entry ID to the list of entry ID(s) pointing to
                # the same file.
                registered[file].append(e.id)
            yield i - 1  # The -1 waits for the next step to finish

        for k, v in registered.items():
            if len(v) > 1:
                self.dupe_entries.append((v[0], v[1:]))
                # logging.info(f"DUPLICATE FOUND: {(v[0], v[1:])}")
                # for id in v:
                #     logging.info(f"\t{(Path()/self.get_entry(id).path/self.get_entry(id).filename)}")

        yield len(self.entries)

    def merge_dupe_entries(self):
        """
        Merges duplicate Entries.
        A duplicate Entry is defined as an Entry pointing to a file that one or more
        other Entries are also pointing to.\n
        `dupe_entries = tuple(int, list[int])`
        """

        logging.info("[LIBRARY] Mirroring Duplicate Entries...")
        id_to_entry_map: dict = {}

        for dupe in self.dupe_entries:
            # Store the id to entry relationship as the library one is about to
            # be destroyed.
            # NOTE: This is not a good solution, but will be upended by the
            # database migration soon anyways.
            for id in dupe[1]:
                id_to_entry_map[id] = self.get_entry(id)
            self.mirror_entry_fields([dupe[0]] + dupe[1])

        logging.info(
            "[LIBRARY] Consolidating Entries... (This may take a while for larger libraries)"
        )
        for i, dupe in enumerate(self.dupe_entries):
            for id in dupe[1]:
                # NOTE: Instead of using self.remove_entry(id), I'm bypassing it
                # because it's currently inefficient in how it needs to remap
                # every ID to every list index. I'm recreating the steps it
                # takes but in a batch-friendly way here.
                # NOTE: Couldn't use get_entry(id) because that relies on the
                # entry's index in the list, which is currently being messed up.
                logging.info(f"[LIBRARY] Removing Unneeded Entry {id}")
                self.entries.remove(id_to_entry_map[id])
            yield i - 1  # The -1 waits for the next step to finish

        self._entry_id_to_index_map.clear()
        for i, e in enumerate(self.entries, start=0):
            self._map_entry_id_to_index(e, i)
        self._map_filenames_to_entry_ids()

    def refresh_dupe_files(self, results_filepath: str | Path):
        """
        Refreshes the list of duplicate files.
        A duplicate file is defined as an identical or near-identical file as determined
        by a DupeGuru results file.
        """

        full_results_path: Path = Path(results_filepath)
        if self.library_dir not in full_results_path.parents:
            full_results_path = self.library_dir / full_results_path

        if full_results_path.is_file():
            self.dupe_files.clear()
            self._map_filenames_to_entry_ids()
            tree = ET.parse(full_results_path)
            root = tree.getroot()
            for i, group in enumerate(root):
                # print(f'-------------------- Match Group {i}---------------------')
                files: list[Path] = []
                # (File Index, Matched File Index, Match Percentage)
                matches: list[tuple[int, int, int]] = []
                for element in group:
                    if element.tag == "file":
                        file = Path(element.attrib.get("path"))
                        files.append(file)
                    if element.tag == "match":
                        matches.append(
                            (
                                int(element.attrib.get("first")),
                                int(element.attrib.get("second")),
                                int(element.attrib.get("percentage")),
                            )
                        )
                for match in matches:
                    # print(f'MATCHED ({match[2]}%): \n   {files[match[0]]} \n-> {files[match[1]]}')
                    file_1 = files[match[0]].relative_to(self.library_dir)
                    file_2 = files[match[1]].relative_to(self.library_dir)

                    if (
                        file_1.resolve in self.filename_to_entry_id_map.keys()
                        and file_2 in self.filename_to_entry_id_map.keys()
                    ):
                        self.dupe_files.append(
                            (files[match[0]], files[match[1]], match[2])
                        )
                print("")

            for dupe in self.dupe_files:
                print(
                    f"[LIBRARY] MATCHED ({dupe[2]}%): \n   {dupe[0]} \n-> {dupe[1]}",
                    end="\n",
                )
                # self.dupe_files.append(full_path)

    def remove_missing_files(self):
        deleted = []
        for i, missing in enumerate(self.missing_files):
            # pb.setValue(i)
            # pb.setLabelText(f'Deleting {i}/{len(self.lib.missing_files)} Unlinked Entries')
            try:
                id = self.get_entry_id_from_filepath(missing)
                logging.info(f"Removing Entry ID {id}:\n\t{missing}")
                self.remove_entry(id)
                # self.driver.purge_item_from_navigation(ItemType.ENTRY, id)
                deleted.append(missing)
            except KeyError:
                logging.info(
                    f'[LIBRARY][ERROR]: "{id}" was reported as missing, but is not in the file_to_entry_id map.'
                )
            yield (i, id)
        for d in deleted:
            self.missing_files.remove(d)

    def remove_missing_matches(self, fixed_indices: list[int]):
        """Removes a list of fixed Entry indices from the internal missing_matches list."""
        for i in fixed_indices:
            del self.missing_matches[i]

    def fix_missing_files(self):
        """
        Attempts to repair Entries that point to invalid file paths.
        """

        # self.refresh_missing_files()

        # matched_json_filepath = os.path.normpath(
        # 	f'{self.library_dir}/{TS_FOLDER_NAME}/missing_matched.json')
        # # if not os.path.exists(matched_json_filepath):
        # # 	self.match_missing_files()

        self.missing_matches.clear()

        fixed_indices = []
        # if os.path.exists(matched_json_filepath):
        # 	with open(matched_json_filepath, "r", encoding="utf8") as f:
        # 		self.missing_matches = json.load(f)

        # 	self.refresh_missing_files()
        for i, missing in enumerate(self.missing_files):
            print(missing)
            if missing not in self.missing_matches.keys():
                matches = self._match_missing_file(missing)
                if matches:
                    print(f"[LIBRARY] Adding key {missing} with matches {matches}")
                    self.missing_matches[missing] = matches
                    yield (i, True)
                else:
                    yield (i, False)

        # self._purge_empty_missing_entries()

        for i, matches in enumerate(self.missing_matches):
            if len(self.missing_matches[matches]) == 1:
                id = self.get_entry_id_from_filepath(matches)
                self.update_entry_path(id, self.missing_matches[matches][0])
                fixed_indices.append(matches)
                # print(f'Fixed {self.entries[self.get_entry_index_from_filename(i)].filename}')
                print(f"[LIBRARY] Fixed {self.get_entry(id).filename}")
            # (int, str)

        # Consolidate new matches with existing unlinked entries.
        self.refresh_dupe_entries()
        if self.dupe_entries:
            self.merge_dupe_entries()

        # Remap filenames to entry IDs.
        self._map_filenames_to_entry_ids()
        # TODO - the type here doesnt match but I cant reproduce calling this
        self.remove_missing_matches(fixed_indices)

    def _match_missing_file(self, file: str) -> list[Path]:
        """
        Tries to find missing entry files within the library directory.
        Works if files were just moved to different subfolders and don't have duplicate names.
        """

        # self.refresh_missing_files()

        matches = []

        # for file in self.missing_files:
        path = Path(file)
        for root, dirs, files in os.walk(self.library_dir):
            for f in files:
                # print(f'{tail} --- {f}')
                if path.name == f and "$recycle.bin" not in str(root).lower():
                    # self.fixed_files.append(tail)

                    new_path = Path(root).relative_to(self.library_dir)

                    matches.append(new_path)

                    # if file not in matches.keys():
                    # 	matches[file] = []
                    # matches[file].append(new_path)

                    print(
                        f"[LIBRARY] MATCH: {file} \n\t-> {self.library_dir / new_path / path.name}\n"
                    )

        if not matches:
            print(f"[LIBRARY] No matches found for: {file}")

        return matches

        # print(f'╡ {os.path.normpath(os.path.relpath(file, self.library_dir))} ╞'.center(
        #     os.get_terminal_size()[0], "═"))
        # print('↓ ↓ ↓'.center(os.get_terminal_size()[0], " "))
        # print(
        #     f'╡ {os.path.normpath(new_path + "/" + tail)} ╞'.center(os.get_terminal_size()[0], "═"))
        # print(self.entries[self.file_to_entry_index_map[str(
        #     os.path.normpath(os.path.relpath(file, self.library_dir)))]])

        # # print(
        # #     f'{file} -> {os.path.normpath(self.library_dir + "/" + new_path + "/" + tail)}')
        # # # TODO: Update the Entry path with the 'new_path' variable via a completed update_entry() method.

        # if (str(os.path.normpath(new_path + "/" + tail))) in self.file_to_entry_index_map.keys():
        #     print(
        #         'Existing Entry ->'.center(os.get_terminal_size()[0], " "))
        #     print(self.entries[self.file_to_entry_index_map[str(
        #         os.path.normpath(new_path + "/" + tail))]])

        # print(f''.center(os.get_terminal_size()[0], "─"))
        # print('')

        # for match in matches.keys():
        #     self.fixed_files.append(match)
        #     # print(match)
        #     # print(f'\t{matches[match]}')

        # with open(
        #    self.library_dir / TS_FOLDER_NAME / "missing_matched.json", "w"
        # ) as outfile:
        #    outfile.flush()
        #    json.dump(matches, outfile, indent=4)
        # print(
        #    f'[LIBRARY] Saved to disk at {self.library_dir / TS_FOLDER_NAME / "missing_matched.json"}'
        # )

    def count_tag_entry_refs(self) -> None:
        """
        Counts the number of entry references for each tag. Stores results
        in `tag_entry_ref_map`.
        """
        self._tag_entry_ref_map.clear()
        self.tag_entry_refs.clear()
        local_hits: set = set()

        for entry in self.entries:
            local_hits.clear()
            if entry.fields:
                for field in entry.fields:
                    if self.get_field_attr(field, "type") == "tag_box":
                        for tag_id in self.get_field_attr(field, "content"):
                            local_hits.add(tag_id)

            for hit in list(local_hits):
                try:
                    _ = self._tag_entry_ref_map[hit]
                except KeyError:
                    self._tag_entry_ref_map[hit] = 0
                self._tag_entry_ref_map[hit] += 1

        # keys = list(self.tag_entry_ref_map.keys())
        # values = list(self.tag_entry_ref_map.values())
        self.tag_entry_refs = sorted(
            self._tag_entry_ref_map.items(), key=lambda x: x[1], reverse=True
        )

    def add_entry_to_library(self, entry: Entry):
        """Adds a new Entry to the Library."""
        self.entries.append(entry)
        self._map_entry_id_to_index(entry, -1)

    def add_new_files_as_entries(self) -> list[int]:
        """Adds files from the `files_not_in_library` list to the Library as Entries. Returns list of added indices."""
        new_ids: list[int] = []
        for file in self.files_not_in_library:
            path = Path(file)
            # print(os.path.split(file))
            entry = Entry(
                id=self._next_entry_id, filename=path.name, path=path.parent, fields=[]
            )
            self._next_entry_id += 1
            self.add_entry_to_library(entry)
            new_ids.append(entry.id)
        self._map_filenames_to_entry_ids()
        self.files_not_in_library.clear()
        return new_ids

        self.files_not_in_library.clear()

    def get_entry(self, entry_id: int) -> Entry:
        """Returns an Entry object given an Entry ID."""
        return self.entries[self._entry_id_to_index_map[int(entry_id)]]

    def get_collation(self, collation_id: int) -> Collation:
        """Returns a Collation object given an Collation ID."""
        return self.collations[self._collation_id_to_index_map[int(collation_id)]]

    # @deprecated('Use new Entry ID system.')
    def get_entry_from_index(self, index: int) -> Entry | None:
        """Returns a Library Entry object given its index in the unfiltered Entries list."""
        if self.entries:
            return self.entries[int(index)]
        return None

    # @deprecated('Use new Entry ID system.')
    def get_entry_id_from_filepath(self, filename: Path):
        """Returns an Entry ID given the full filepath it points to."""
        try:
            if self.entries:
                return self.filename_to_entry_id_map[
                    Path(filename).relative_to(self.library_dir)
                ]
        except KeyError:
            return -1

    def search_library(
        self,
        query: str = None,
        entries=True,
        collations=True,
        tag_groups=True,
        search_mode=SearchMode.AND,
    ) -> list[tuple[ItemType, int]]:
        """
        Uses a search query to generate a filtered results list.
        Returns a list of (str, int) tuples consisting of a result type and ID.
        """

        # self.filtered_entries.clear()
        results: list[tuple[ItemType, int]] = []
        collations_added = []
        # print(f"Searching Library with query: {query} search_mode: {search_mode}")
        if query:
            # start_time = time.time()
            query = query.strip().lower()
            query_words: list[str] = query.split(" ")
            all_tag_terms: list[str] = []
            only_untagged: bool = "untagged" in query or "no tags" in query
            only_empty: bool = "empty" in query or "no fields" in query
            only_missing: bool = "missing" in query or "no file" in query
            allow_adv: bool = "filename:" in query_words
            tag_only: bool = "tag_id:" in query_words
            if allow_adv:
                query_words.remove("filename:")
            if tag_only:
                query_words.remove("tag_id:")
            # TODO: Expand this to allow for dynamic fields to work.
            only_no_author: bool = "no author" in query or "no artist" in query

            # Preprocess the Tag terms.
            if query_words:
                # print(query_words, self._tag_strings_to_id_map)
                for i, term in enumerate(query_words):
                    for j, term in enumerate(query_words):
                        if (
                            query_words[i : j + 1]
                            and " ".join(query_words[i : j + 1])
                            in self._tag_strings_to_id_map
                        ):
                            all_tag_terms.append(" ".join(query_words[i : j + 1]))
                        # print(all_tag_terms)

                # This gets rid of any accidental term inclusions because they were words
                # in another term. Ex. "3d" getting added in "3d art"
                for i, term in enumerate(all_tag_terms):
                    for j, term2 in enumerate(all_tag_terms):
                        if i != j and all_tag_terms[i] in all_tag_terms[j]:
                            # print(
                            #     f'removing {all_tag_terms[i]} because {all_tag_terms[i]} was in {all_tag_terms[j]}')
                            all_tag_terms.remove(all_tag_terms[i])
                            break

            # print(all_tag_terms)

            # non_entry_count = 0
            # Iterate over all Entries =============================================================
            for entry in self.entries:
                allowed_ext: bool = entry.filename.suffix not in self.ignored_extensions
                # try:
                # entry: Entry = self.entries[self.file_to_library_index_map[self._source_filenames[i]]]
                # print(f'{entry}')

                if allowed_ext:
                    # If the entry has tags of any kind, append them to this main tag list.
                    entry_tags: list[int] = []
                    entry_authors: list[str] = []
                    if entry.fields:
                        for field in entry.fields:
                            field_id = list(field.keys())[0]
                            if self.get_field_obj(field_id)["type"] == "tag_box":
                                entry_tags.extend(field[field_id])
                            if self.get_field_obj(field_id)["name"] == "Author":
                                entry_authors.extend(field[field_id])
                            if self.get_field_obj(field_id)["name"] == "Artist":
                                entry_authors.extend(field[field_id])

                    # print(f'Entry Tags: {entry_tags}')

                    # Add Entries from special flags -------------------------------
                    # TODO: Come up with a more user-resistent way to 'archived' and 'favorite' tags.
                    if only_untagged:
                        if not entry_tags:
                            results.append((ItemType.ENTRY, entry.id))
                    elif only_no_author:
                        if not entry_authors:
                            results.append((ItemType.ENTRY, entry.id))
                    elif only_empty:
                        if not entry.fields:
                            results.append((ItemType.ENTRY, entry.id))
                    elif only_missing:
                        if (
                            self.library_dir / entry.path / entry.filename
                        ).resolve() in self.missing_files:
                            results.append((ItemType.ENTRY, entry.id))

                    # elif query == "archived":
                    #     if entry.tags and self._tag_names_to_tag_id_map[self.archived_word.lower()][0] in entry.tags:
                    #         self.filtered_file_list.append(file)
                    #         pb.value = len(self.filtered_file_list)
                    # elif query in entry.path.lower():

                    # NOTE: This searches path and filenames.

                    if allow_adv:
                        if [q for q in query_words if (q in str(entry.path).lower())]:
                            results.append((ItemType.ENTRY, entry.id))
                        elif [
                            q for q in query_words if (q in str(entry.filename).lower())
                        ]:
                            results.append((ItemType.ENTRY, entry.id))
                    elif tag_only:
                        if entry.has_tag(self, int(query_words[0])):
                            results.append((ItemType.ENTRY, entry.id))

                    # elif query in entry.filename.lower():
                    # 	self.filtered_entries.append(index)
                    elif entry_tags:
                        # function to add entry to results
                        def add_entry(entry: Entry):
                            # self.filter_entries.append()
                            # self.filtered_file_list.append(file)
                            # results.append((SearchItemType.ENTRY, entry.id))
                            added = False
                            for f in entry.fields:
                                if self.get_field_attr(f, "type") == "collation":
                                    if (
                                        self.get_field_attr(f, "content")
                                        not in collations_added
                                    ):
                                        results.append(
                                            (
                                                ItemType.COLLATION,
                                                self.get_field_attr(f, "content"),
                                            )
                                        )
                                        collations_added.append(
                                            self.get_field_attr(f, "content")
                                        )
                                    added = True

                            if not added:
                                results.append((ItemType.ENTRY, entry.id))

                        if search_mode == SearchMode.AND:  # Include all terms
                            # For each verified, extracted Tag term.
                            failure_to_union_terms = False
                            for term in all_tag_terms:
                                # If the term from the previous loop was already verified:
                                if not failure_to_union_terms:
                                    cluster: set = set()
                                    # Add the immediate associated Tags to the set (ex. Name, Alias hits)
                                    # Since this term could technically map to multiple IDs, iterate over it
                                    # (You're 99.9999999% likely to just get 1 item)
                                    for id in self._tag_strings_to_id_map[term]:
                                        cluster.add(id)
                                        cluster = cluster.union(
                                            set(self.get_tag_cluster(id))
                                        )
                                    # print(f'Full Cluster: {cluster}')
                                    # For each of the Tag IDs in the term's ID cluster:
                                    for t in cluster:
                                        # Assume that this ID from the cluster is not in the Entry.
                                        # Wait to see if proven wrong.
                                        failure_to_union_terms = True
                                        # If the ID actually is in the Entry,
                                        if t in entry_tags:
                                            # There wasn't a failure to find one of the term's cluster IDs in the Entry.
                                            # There is also no more need to keep checking the rest of the terms in the cluster.
                                            failure_to_union_terms = False
                                            # print(f"FOUND MATCH: {t}")
                                            break
                                        # print(f'\tFailure to Match: {t}')
                            # # failure_to_union_terms is used to determine if all terms in the query were found in the entry.
                            # # If there even were tag terms to search through AND they all match an entry
                            if all_tag_terms and not failure_to_union_terms:
                                add_entry(entry)

                        if search_mode == SearchMode.OR:  # Include any terms
                            # For each verified, extracted Tag term.
                            for term in all_tag_terms:
                                # Add the immediate associated Tags to the set (ex. Name, Alias hits)
                                # Since this term could technically map to multiple IDs, iterate over it
                                # (You're 99.9999999% likely to just get 1 item)
                                for id in self._tag_strings_to_id_map[term]:
                                    # If the ID actually is in the Entry,
                                    if id in entry_tags:
                                        # check if result already contains the entry
                                        if (ItemType.ENTRY, entry.id) not in results:
                                            add_entry(entry)
                                        break

                # sys.stdout.write(
                #     f'\r[INFO][FILTER]: {len(self.filtered_file_list)} matches found')
                # sys.stdout.flush()

                # except:
                #     # # Put this here to have new non-registered images show up
                #     # if query == "untagged" or query == "no author" or query == "no artist":
                #     #     self.filtered_file_list.append(file)
                #     # non_entry_count = non_entry_count + 1
                #     pass

            # end_time = time.time()
            # print(
            # 	f'[INFO][FILTER]: {len(self.filtered_entries)} matches found ({(end_time - start_time):.3f} seconds)')

            # if non_entry_count:
            # 	print(
            # 		f'[INFO][FILTER]: There are {non_entry_count} new files in {self.source_dir} that do not have entries. These will not appear in most filtered results.')
            # if not self.filtered_entries:
            # 	print("[INFO][FILTER]: Filter returned no results.")
        else:
            for entry in self.entries:
                added = False
                allowed_ext = entry.filename.suffix not in self.ignored_extensions
                if allowed_ext:
                    for f in entry.fields:
                        if self.get_field_attr(f, "type") == "collation":
                            if (
                                self.get_field_attr(f, "content")
                                not in collations_added
                            ):
                                results.append(
                                    (
                                        ItemType.COLLATION,
                                        self.get_field_attr(f, "content"),
                                    )
                                )
                                collations_added.append(
                                    self.get_field_attr(f, "content")
                                )
                            added = True

                    if not added:
                        results.append((ItemType.ENTRY, entry.id))
            # for file in self._source_filenames:
            #     self.filtered_file_list.append(file)
        results.reverse()
        return results

    def search_tags(
        self,
        query: str,
        include_cluster=False,
        ignore_builtin=False,
        threshold: int = 1,
        context: list[str] = None,
    ) -> list[int]:
        """Returns a list of Tag IDs returned from a string query."""
        # tag_ids: list[int] = []
        # if query:
        # 	query = query.lower()
        # 	query_words = query.split(' ')
        # 	all_tag_terms: list[str] = []

        # 	# Preprocess the Tag terms.
        # 	if len(query_words) > 0:
        # 		for i, term in enumerate(query_words):
        # 			for j, term in enumerate(query_words):
        # 				if query_words[i:j+1] and " ".join(query_words[i:j+1]) in self._tag_names_to_tag_id_map:
        # 					all_tag_terms.append(" ".join(query_words[i:j+1]))
        # 		# This gets rid of any accidental term inclusions because they were words
        # 		# in another term. Ex. "3d" getting added in "3d art"
        # 		for i, term in enumerate(all_tag_terms):
        # 			for j, term2 in enumerate(all_tag_terms):
        # 				if i != j and all_tag_terms[i] in all_tag_terms[j]:
        # 					# print(
        # 					#     f'removing {all_tag_terms[i]} because {all_tag_terms[i]} was in {all_tag_terms[j]}')
        # 					all_tag_terms.remove(all_tag_terms[i])
        # 					break

        # 		for term in all_tag_terms:
        # 			for id in self._tag_names_to_tag_id_map[term]:
        # 				if id not in tag_ids:
        # 					tag_ids.append(id)
        # return tag_ids

        # NOTE: I'd expect a blank query to return all with the other implementation, but
        # it misses stuff like Archive (id 0) so here's this as a catch-all.

        if not query:
            all: list[int] = []
            for tag in self.tags:
                if ignore_builtin and tag.id >= 1000:
                    all.append(tag.id)
                elif not ignore_builtin:
                    all.append(tag.id)
            return all

        # Direct port from Version 8 ===========================================
        # TODO: Make this more efficient (if needed)
        # ids: list[int] = []
        id_weights: list[tuple[int, int]] = []
        # partial_id_weights: list[int] = []
        priority_ids: list[int] = []
        # print(f'Query: \"{query}\" -------------------------------------')
        for string in self._tag_strings_to_id_map:  # O(n), n = tags
            exact_match: bool = False
            partial_match: bool = False
            query = strip_punctuation(query).lower()
            string = strip_punctuation(string).lower()

            if query == string:
                exact_match = True
            elif string.startswith(query):
                if len(query) >= (
                    len(string) // (len(string) if threshold == 1 else threshold)
                ):
                    partial_match = True

            if exact_match or partial_match:
                # Avg O(1), usually 1 item
                for tag_id in self._tag_strings_to_id_map[string]:
                    proceed: bool = False
                    if ignore_builtin and tag_id >= 1000:
                        proceed = True
                    elif not ignore_builtin:
                        proceed = True

                    if proceed:
                        if tag_id not in [x[0] for x in id_weights]:
                            if exact_match:
                                # print(f'[{query}] EXACT MATCH:')
                                # print(self.get_tag_from_id(tag_id).display_name(self))
                                # print('')
                                # time.sleep(0.1)
                                priority_ids.append(tag_id)
                                id_weights.append((tag_id, 100000000))
                            else:
                                # print(f'[{query}] Partial Match:')
                                # print(self.get_tag_from_id(tag_id).display_name(self))
                                # print('')
                                # time.sleep(0.1)
                                # ids.append(id)
                                id_weights.append((tag_id, 0))
                        # O(m), m = # of references
                        if include_cluster:
                            for id in self.get_tag_cluster(tag_id):
                                if (id, 0) not in id_weights:
                                    id_weights.append((id, 0))

        # Contextual Weighing
        if context and (
            (len(id_weights) > 1 and len(priority_ids) > 1) or (len(priority_ids) > 1)
        ):
            context_strings: list[str] = [
                s.replace(" ", "")
                .replace("_", "")
                .replace("-", "")
                .replace("'", "")
                .replace("(", "")
                .replace(")", "")
                .replace("[", "")
                .replace("]", "")
                .lower()
                for s in context
            ]
            for term in context:
                if len(term.split(" ")) > 1:
                    context_strings += term.split(" ")
                if len(term.split("_")) > 1:
                    context_strings += term.split("_")
                if len(term.split("-")) > 1:
                    context_strings += term.split("-")
            context_strings = list(set(context_strings))
            # context_strings.sort() # NOTE: TEMP!!!!!!!!!!!!!!!!!!
            # print(f'Context Strings: {context_strings}')
            # time.sleep(3)
            # for term in context:
            # 	context_ids += self.filter_tags(query=term, include_cluster=True, ignore_builtin=ignore_builtin)
            for i, idw in enumerate(id_weights, start=0):
                weight: int = 0
                tag_strings: list[str] = []
                subtag_ids: list[int] = self.get_all_child_tag_ids(idw[0])
                for id in self.get_tag_cluster(idw[0]):
                    subtag_ids += self.get_all_child_tag_ids(id)
                subtag_ids = list(set(subtag_ids))

                for sub_id in subtag_ids:
                    tag_strings += (
                        [self.get_tag(sub_id).name]
                        + [self.get_tag(sub_id).shorthand]
                        + self.get_tag(sub_id).aliases
                    )

                # for id in self.get_tag_cluster(idw[0]):
                # 	tag_strings += [self.get_tag_from_id(id).name] + [self.get_tag_from_id(id).shorthand] + self.get_tag_from_id(id).aliases
                split: list[str] = []
                for ts in tag_strings:
                    if len(ts.split(" ")) > 1:
                        split += ts.split(" ")
                tag_strings += split
                tag_strings = [
                    s.replace(" ", "")
                    .replace("_", "")
                    .replace("-", "")
                    .replace("'", "")
                    .lower()
                    for s in tag_strings
                ]
                while "" in tag_strings:
                    tag_strings.remove("")
                tag_strings = list(set(tag_strings))
                # tag_strings.sort() # NOTE: TEMP!!!!!!!!!!!!!!!!!!
                for ts in tag_strings:
                    weight += context_strings.count(ts)
                id_weights[i] = (idw[0], idw[1] + weight)

                # print(f'Tag Strings for {self.get_tag_from_id(idw[0]).display_name(self)}: {tag_strings}')
                # time.sleep(3)
        id_weights = sorted(id_weights, key=lambda id: id[1], reverse=True)

        # if len(id_weights) > 1:
        # 	print(f'Context Weights: \"{id_weights}\"')

        final: list[int] = []

        # if context and id_weights:
        # 	time.sleep(3)
        [final.append(idw[0]) for idw in id_weights if idw[0] not in final]  # type: ignore
        # print(f'Final IDs: \"{[self.get_tag_from_id(id).display_name(self) for id in final]}\"')
        # print('')
        return final

    def get_all_child_tag_ids(self, tag_id: int) -> list[int]:
        """Recursively traverse a Tag's subtags and return a list of all children tags."""
        subtag_ids: list[int] = []
        if self.get_tag(tag_id).subtag_ids:
            for sub_id in self.get_tag(tag_id).subtag_ids:
                if sub_id not in subtag_ids:
                    subtag_ids.append(sub_id)
                    subtag_ids += self.get_all_child_tag_ids(sub_id)
        else:
            return [tag_id]

        return subtag_ids

    def filter_field_templates(self, query: str) -> list[int]:
        """Returns a list of Field Template IDs returned from a string query."""

        matches: list[int] = []
        for ft in self.default_fields:
            if ft["name"].lower().startswith(query.lower()):
                matches.append(ft["id"])

        return matches

    def update_tag(self, tag: Tag) -> None:
        """
        Edits a Tag in the Library.
        This function undoes and redos the following parts of the 'add_tag_to_library()' process:\n
        - Un-maps the old Tag name, shorthand, and aliases from the Tag ID
        and re-maps the new strings to its ID via '_map_tag_names_to_tag_id()'.\n
        - Un
        """
        tag.subtag_ids = [x for x in tag.subtag_ids if x != tag.id]

        # Since the ID stays the same when editing, only the Tag object is needed.
        # Merging Tags is handled in a different function.
        old_tag: Tag = self.get_tag(tag.id)

        # Undo and Redo 'self._map_tag_names_to_tag_id(tag)' ===========================================================
        # got to map[old names] and remove reference to this id.
        # Remember that _tag_names_to_tag_id_map maps strings to a LIST of ids.
        # print(
        #     f'Removing connection from "{old_tag.name.lower()}" to {old_tag.id} in {self._tag_names_to_tag_id_map[old_tag.name.lower()]}')
        old_name: str = strip_punctuation(old_tag.name).lower()
        self._tag_strings_to_id_map[old_name].remove(old_tag.id)
        # Delete the map key if it doesn't point to any other IDs.
        if not self._tag_strings_to_id_map[old_name]:
            del self._tag_strings_to_id_map[old_name]
        if old_tag.shorthand:
            old_sh: str = strip_punctuation(old_tag.shorthand).lower()
            # print(
            #     f'Removing connection from "{old_tag.shorthand.lower()}" to {old_tag.id} in {self._tag_names_to_tag_id_map[old_tag.shorthand.lower()]}')
            self._tag_strings_to_id_map[old_sh].remove(old_tag.id)
            # Delete the map key if it doesn't point to any other IDs.
            if not self._tag_strings_to_id_map[old_sh]:
                del self._tag_strings_to_id_map[old_sh]
        if old_tag.aliases:
            for alias in old_tag.aliases:
                old_a: str = strip_punctuation(alias).lower()
                # print(
                #     f'Removing connection from "{alias.lower()}" to {old_tag.id} in {self._tag_names_to_tag_id_map[alias.lower()]}')
                self._tag_strings_to_id_map[old_a].remove(old_tag.id)
                # Delete the map key if it doesn't point to any other IDs.
                if not self._tag_strings_to_id_map[old_a]:
                    del self._tag_strings_to_id_map[old_a]
        # then add new reference to this id at map[new names]
        # print(f'Mapping new names for "{tag.name.lower()}" (ID: {tag.id})')
        self._map_tag_strings_to_tag_id(tag)

        # Redo 'self.tags.append(tag)' =================================================================================
        # then swap out the tag in the tags list to this one
        # print(f'Swapping {self.tags[self._tag_id_to_index_map[old_tag.id]]} *FOR* {tag} in tags list.')
        self.tags[self._tag_id_to_index_map[old_tag.id]] = tag
        print(f"Edited Tag: {tag}")

        # Undo and Redo 'self._map_tag_id_to_cluster(tag)' =============================================================
        # NOTE: Currently the tag is getting updated outside of this due to python
        # entanglement shenanigans so for now this method will always update the cluster maps.
        # if old_tag.subtag_ids != tag.subtag_ids:
        # TODO: Optimize this by 1,000,000% buy building an inverse recursive map function
        # instead of literally just deleting the whole map and building it again
        # print('Reticulating Splines...')
        self._tag_id_to_cluster_map.clear()
        for tag in self.tags:
            self._map_tag_id_to_cluster(tag)
            # print('Splines Reticulated.')

            self._map_tag_id_to_cluster(tag)

    def remove_tag(self, tag_id: int) -> None:
        """
        Removes a Tag from the Library.
        Disconnects it from all internal lists and maps, then remaps others as needed.
        """
        tag = self.get_tag(tag_id)

        # Step [1/7]:
        # Remove from Entries.
        for e in self.entries:
            if e.fields:
                for f in e.fields:
                    if self.get_field_attr(f, "type") == "tag_box":
                        if tag_id in self.get_field_attr(f, "content"):
                            self.get_field_attr(f, "content").remove(tag.id)

        # Step [2/7]:
        # Remove from Subtags.
        for t in self.tags:
            if t.subtag_ids:
                if tag_id in t.subtag_ids:
                    t.subtag_ids.remove(tag.id)

        # Step [3/7]:
        # Remove ID -> cluster reference.
        if tag_id in self._tag_id_to_cluster_map:
            del self._tag_id_to_cluster_map[tag.id]
        # Remove mentions of this ID in all clusters.
        for key, values in self._tag_id_to_cluster_map.items():
            if tag_id in values:
                values.remove(tag.id)

        # Step [4/7]:
        # Remove mapping of this ID to its index in the tags list.
        if tag.id in self._tag_id_to_index_map:
            del self._tag_id_to_index_map[tag.id]

        # Step [5/7]:
        # Remove this Tag from the tags list.
        self.tags.remove(tag)

        # Step [6/7]:
        # Remap the other Tag IDs to their new indices in the tags list.
        self._tag_id_to_index_map.clear()
        for i, t in enumerate(self.tags):
            self._map_tag_id_to_index(t, i)

        # Step [7/7]:
        # Remap all existing Tag names.
        self._tag_strings_to_id_map.clear()
        for t in self.tags:
            self._map_tag_strings_to_tag_id(t)

    def get_tag_ref_count(self, tag_id: int) -> tuple[int, int]:
        """Returns an int tuple (entry_ref_count, subtag_ref_count) of Tag reference counts."""
        entry_ref_count: int = 0
        subtag_ref_count: int = 0

        for e in self.entries:
            if e.fields:
                for f in e.fields:
                    if self.get_field_attr(f, "type") == "tag_box":
                        if tag_id in self.get_field_attr(f, "content"):
                            entry_ref_count += 1
                            break

        for t in self.tags:
            if t.subtag_ids:
                if tag_id in t.subtag_ids:
                    subtag_ref_count += 1

        # input()
        return (entry_ref_count, subtag_ref_count)

    def update_entry_path(self, entry_id: int, path: str | Path) -> None:
        """Updates an Entry's path."""
        self.get_entry(entry_id).path = Path(path)

    def update_entry_filename(self, entry_id: int, filename: str | Path) -> None:
        """Updates an Entry's filename."""
        self.get_entry(entry_id).filename = Path(filename)

    def update_entry_field(self, entry_id: int, field_index: int, content, mode: str):
        """Updates an Entry's specific field. Modes: append, remove, replace."""

        field_id: int = list(self.get_entry(entry_id).fields[field_index].keys())[0]
        if mode.lower() == "append" or mode.lower() == "extend":
            for i in content:
                if i not in self.get_entry(entry_id).fields[field_index][field_id]:
                    self.get_entry(entry_id).fields[field_index][field_id].append(i)
        elif mode.lower() == "replace":
            self.get_entry(entry_id).fields[field_index][field_id] = content
        elif mode.lower() == "remove":
            for i in content:
                self.get_entry(entry_id).fields[field_index][field_id].remove(i)

    def does_field_content_exist(self, entry_id: int, field_id: int, content) -> bool:
        """Returns whether or not content exists in a specific entry field type."""
        # entry = self.entries[entry_index]
        entry = self.get_entry(entry_id)
        indices = self.get_field_index_in_entry(entry, field_id)
        for i in indices:
            if self.get_field_attr(entry.fields[i], "content") == content:
                return True
        return False

    def add_generic_data_to_entry(self, data, entry_id: int):
        """Adds generic data to an Entry on a "best guess" basis. Used in adding scraped data."""
        if data:
            # Add a Title Field if the data doesn't already exist.
            if data.get("title"):
                field_id = 0  # Title Field ID
                if not self.does_field_content_exist(entry_id, field_id, data["title"]):
                    self.add_field_to_entry(entry_id, field_id)
                    self.update_entry_field(entry_id, -1, data["title"], "replace")

            # Add an Author Field if the data doesn't already exist.
            if data.get("author"):
                field_id = 1  # Author Field ID
                if not self.does_field_content_exist(
                    entry_id, field_id, data["author"]
                ):
                    self.add_field_to_entry(entry_id, field_id)
                    self.update_entry_field(entry_id, -1, data["author"], "replace")

            # Add an Artist Field if the data doesn't already exist.
            if data.get("artist"):
                field_id = 2  # Artist Field ID
                if not self.does_field_content_exist(
                    entry_id, field_id, data["artist"]
                ):
                    self.add_field_to_entry(entry_id, field_id)
                    self.update_entry_field(entry_id, -1, data["artist"], "replace")

            # Add a Date Published Field if the data doesn't already exist.
            if data.get("date_published"):
                field_id = 14  # Date Published Field ID
                date = str(
                    datetime.datetime.strptime(
                        data["date_published"], "%Y-%m-%d %H:%M:%S"
                    )
                )
                if not self.does_field_content_exist(entry_id, field_id, date):
                    self.add_field_to_entry(entry_id, field_id)
                    # entry = self.entries[entry_id]
                    self.update_entry_field(entry_id, -1, date, "replace")

            # Process String Tags if the data doesn't already exist.
            if data.get("tags"):
                tags_field_id = 6  # Tags Field ID
                content_tags_field_id = 7  # Content Tags Field ID
                meta_tags_field_id = 8  # Meta Tags Field ID
                notes_field_id = 5  # Notes Field ID
                tags: list[str] = data["tags"]
                # extra: list[str] = []
                # for tag in tags:
                # 	if len(tag.split(' ')) > 1:
                # 		extra += tag.split(' ')
                # 	if len(tag.split('_')) > 1:
                # 		extra += tag.split('_')
                # 	if len(tag.split('-')) > 1:
                # 		extra += tag.split('-')
                # tags = tags + extra
                # tags = list(set(tags))
                extra: list[str] = []
                for tag in tags:
                    if len(tag.split("_(")) > 1:
                        extra += tag.replace(")", "").split("_(")
                tags += extra
                tags = list(set(tags))
                tags.sort()

                while "" in tags:
                    tags.remove("")

                # # If the tags were a single string (space delimitated), split them into a list.
                # if isinstance(data["tags"], str):
                # 	tags.clear()
                # 	tags = data["tags"].split(' ')

                # Try to add matching tags in library.
                for tag in tags:
                    matching: list[int] = self.search_tags(
                        tag.replace("_", " ").replace("-", " "),
                        include_cluster=False,
                        ignore_builtin=True,
                        threshold=2,
                        context=tags,
                    )
                    priority_field_index = -1
                    if matching:
                        # NOTE: The following commented-out code enables the ability
                        # to prefer an existing built-in tag_box field to add to
                        # rather than preferring or creating a 'Content Tags' felid.
                        # In my experience, this feature isn't actually what I want,
                        # but the idea behind it isn't bad. Maybe this could be
                        # user configurable and scale with custom fields.

                        # tag_field_indices = self.get_field_index_in_entry(
                        # 	entry_index, tags_field_id)
                        content_tags_field_indices = self.get_field_index_in_entry(
                            self.get_entry(entry_id), content_tags_field_id
                        )
                        # meta_tags_field_indices = self.get_field_index_in_entry(
                        # 	entry_index, meta_tags_field_id)

                        if content_tags_field_indices:
                            priority_field_index = content_tags_field_indices[0]
                        # elif tag_field_indices:
                        # 	priority_field_index = tag_field_indices[0]
                        # elif meta_tags_field_indices:
                        # 	priority_field_index = meta_tags_field_indices[0]

                        if priority_field_index > 0:
                            self.update_entry_field(
                                entry_id, priority_field_index, [matching[0]], "append"
                            )
                        else:
                            self.add_field_to_entry(entry_id, content_tags_field_id)
                            self.update_entry_field(
                                entry_id, -1, [matching[0]], "append"
                            )

                # Add all original string tags as a note.
                str_tags = f"Original Tags: {tags}"
                if not self.does_field_content_exist(
                    entry_id, notes_field_id, str_tags
                ):
                    self.add_field_to_entry(entry_id, notes_field_id)
                    self.update_entry_field(entry_id, -1, str_tags, "replace")

            # Add a Description Field if the data doesn't already exist.
            if "description" in data.keys() and data["description"]:
                field_id = 4  # Description Field ID
                if not self.does_field_content_exist(
                    entry_id, field_id, data["description"]
                ):
                    self.add_field_to_entry(entry_id, field_id)
                    self.update_entry_field(
                        entry_id, -1, data["description"], "replace"
                    )
            if "content" in data.keys() and data["content"]:
                field_id = 4  # Description Field ID
                if not self.does_field_content_exist(
                    entry_id, field_id, data["content"]
                ):
                    self.add_field_to_entry(entry_id, field_id)
                    self.update_entry_field(entry_id, -1, data["content"], "replace")
            if "source" in data.keys() and data["source"]:
                field_id = 21  # Source Field ID
                for source in data["source"].split(" "):
                    if source and source != " ":
                        source = strip_web_protocol(string=source)
                        if not self.does_field_content_exist(
                            entry_id, field_id, source
                        ):
                            self.add_field_to_entry(entry_id, field_id)
                            self.update_entry_field(entry_id, -1, source, "replace")

    def add_field_to_entry(self, entry_id: int, field_id: int) -> None:
        """Adds an empty Field, specified by Field ID, to an Entry via its index."""
        # entry = self.entries[entry_index]
        entry = self.get_entry(entry_id)
        field_type = self.get_field_obj(field_id)["type"]
        if field_type in TEXT_FIELDS:
            entry.fields.append({int(field_id): ""})
        elif field_type == "tag_box":
            entry.fields.append({int(field_id): []})
        elif field_type == "datetime":
            entry.fields.append({int(field_id): ""})
        else:
            logging.info(
                f"[LIBRARY][ERROR]: Unknown field id attempted to be added to entry: {field_id}"
            )

    def mirror_entry_fields(self, entry_ids: list[int]) -> None:
        """Combines and mirrors all fields across a list of given Entry IDs."""

        all_fields: list = []
        all_ids: list = []  # Parallel to all_fields
        # Extract and merge all fields from all given Entries.
        for id in entry_ids:
            if id:
                entry = self.get_entry(id)
                if entry and entry.fields:
                    for field in entry.fields:
                        # First checks if their are matching tag_boxes to append to
                        if (
                            self.get_field_attr(field, "type") == "tag_box"
                            and self.get_field_attr(field, "id") in all_ids
                        ):
                            content = self.get_field_attr(field, "content")
                            for i in content:
                                id = int(self.get_field_attr(field, "id"))
                                field_index = all_ids.index(id)
                                if i not in all_fields[field_index][id]:
                                    all_fields[field_index][id].append(i)
                        # If not, go ahead and whichever new field.
                        elif field not in all_fields:
                            all_fields.append(field)
                            all_ids.append(int(self.get_field_attr(field, "id")))

        # Replace each Entry's fields with the new merged ones.
        for id in entry_ids:
            entry = self.get_entry(id)
            if entry:
                entry.fields = all_fields

                # TODO: Replace this and any in CLI with a proper user-defined
                # field storing method.
                order: list[int] = (
                    [0]
                    + [1, 2]
                    + [9, 17, 18, 19, 20]
                    + [10, 14, 11, 12, 13, 22]
                    + [4, 5]
                    + [8, 7, 6]
                    + [3, 21]
                )

                # NOTE: This code is copied from the sort_fields() method.
                entry.fields = sorted(
                    entry.fields,
                    key=lambda x: order.index(self.get_field_attr(x, "id")),
                )

    # def move_entry_field(self, entry_index, old_index, new_index) -> None:
    # 	"""Moves a field in entry[entry_index] from position entry.fields[old_index] to entry.fields[new_index]"""
    # 	entry = self.entries[entry_index]
    # 	pass
    # 	# TODO: Implement.

    def get_field_attr(self, entry_field: dict, attribute: str):
        """Returns the value of a specified attribute inside an Entry field."""
        if attribute.lower() == "id":
            return list(entry_field.keys())[0]
        elif attribute.lower() == "content":
            return entry_field[self.get_field_attr(entry_field, "id")]
        else:
            return self.get_field_obj(self.get_field_attr(entry_field, "id"))[
                attribute.lower()
            ]

    def get_field_obj(self, field_id: int) -> dict:
        """
        Returns a field template object associated with a field ID.
        The objects have "id", "name", and "type" fields.
        """
        if int(field_id) < len(self.default_fields):
            return self.default_fields[int(field_id)]
        else:
            return {"id": -1, "name": "Unknown Field", "type": "unknown"}

    def get_field_index_in_entry(self, entry: Entry, field_id: int) -> list[int]:
        """
        Returns matched indices for the field type in an entry.\n
        Returns an empty list of no field of that type is found in the entry.
        """
        matched = []
        # entry: Entry = self.entries[entry_index]
        # entry = self.get_entry(entry_id)
        if entry.fields:
            for i, field in enumerate(entry.fields):
                if self.get_field_attr(field, "id") == int(field_id):
                    matched.append(i)

        return matched

    def _map_tag_strings_to_tag_id(self, tag: Tag) -> None:
        """
        Maps a Tag's name, shorthand, and aliases to their ID's (in the form of a list).\n
        ⚠️DO NOT USE FOR CONFIDENT DATA REFERENCES!⚠️\n
        This is intended to be used for quick search queries.\n
        Uses name_and_alias_to_tag_id_map.
        """
        # tag_id: int, tag_name: str, tag_aliases: list[str] = []
        name: str = strip_punctuation(tag.name).lower()
        if name not in self._tag_strings_to_id_map:
            self._tag_strings_to_id_map[name] = []
        self._tag_strings_to_id_map[name].append(tag.id)

        shorthand: str = strip_punctuation(tag.shorthand).lower()
        if shorthand not in self._tag_strings_to_id_map:
            self._tag_strings_to_id_map[shorthand] = []
        self._tag_strings_to_id_map[shorthand].append(tag.id)

        for alias in tag.aliases:
            alias = strip_punctuation(alias).lower()
            if alias not in self._tag_strings_to_id_map:
                self._tag_strings_to_id_map[alias] = []
            self._tag_strings_to_id_map[alias].append(tag.id)
            # print(f'{alias.lower()} -> {tag.id}')

    def _map_tag_id_to_cluster(self, tag: Tag, subtags: list[Tag] = None) -> None:
        """
        Maps a Tag's subtag's ID's back to it's parent Tag's ID (in the form of a list).
        Uses tag_id_to_cluster_map.\n
        EX: Tag: "Johnny Bravo", Subtags: "Cartoon Network (TV)", "Character".\n
        Maps "Cartoon Network" -> Johnny Bravo, "Character" -> "Johnny Bravo", and "TV" -> Johnny Bravo."
        """
        # If a list of subtags is not provided, the method will revert to a level 1-depth
        # mapping based on the given Tag's own subtags.
        if not subtags:
            subtags = [self.get_tag(sub_id) for sub_id in tag.subtag_ids]
        for subtag in subtags:
            if subtag.id not in self._tag_id_to_cluster_map.keys():
                self._tag_id_to_cluster_map[subtag.id] = []
            # Stops circular references
            if tag.id not in self._tag_id_to_cluster_map[subtag.id]:
                self._tag_id_to_cluster_map[subtag.id].append(tag.id)
                # If the subtag has subtags of it own, recursively link those to the original Tag.
                if subtag.subtag_ids:
                    self._map_tag_id_to_cluster(
                        tag,
                        [
                            self.get_tag(sub_id)
                            for sub_id in subtag.subtag_ids
                            if sub_id != tag.id
                        ],
                    )

    def _map_tag_id_to_index(self, tag: Tag, index: int) -> None:
        """
        Maps a Tag's ID to the Tag's Index in self.tags.
        Uses _tag_id_to_index_map.
        """
        # self._tag_id_to_index_map[tag.id_] = self.tags.index(tag)
        if index < 0:
            index = len(self.tags) + index
        self._tag_id_to_index_map[tag.id] = index
        # print(f'{tag.id} - {self._tag_id_to_index_map[tag.id]}')

    def _map_entry_id_to_index(self, entry: Entry, index: int) -> None:
        """
        Maps an Entry's ID to the Entry's Index in self.entries.
        Uses _entry_id_to_index_map.
        """
        # if index != None:
        if index < 0:
            index = len(self.entries) + index
        self._entry_id_to_index_map[entry.id] = index
        # else:
        # 	self._entry_id_to_index_map[entry.id_] = self.entries.index(entry)

    def _map_collation_id_to_index(self, collation: Collation, index: int) -> None:
        """
        Maps a Collation's ID to the Collation's Index in self.collations.
        Uses _entry_id_to_index_map.
        """
        # if index != None:
        if index < 0:
            index = len(self.collations) + index
        self._collation_id_to_index_map[collation.id] = index

    def add_tag_to_library(self, tag: Tag) -> int:
        """
        Adds a Tag to the Library. ⚠️Only use at runtime! (Cannot reference tags that are not loaded yet)⚠️\n
        For adding Tags from the Library save file, append Tags to the Tags list
        and then map them using map_library_tags().
        """
        tag.subtag_ids = [x for x in tag.subtag_ids if x != tag.id]
        tag.id = self._next_tag_id
        self._next_tag_id += 1

        self._map_tag_strings_to_tag_id(tag)
        self.tags.append(tag)  # Must be appended before mapping the index!
        self._map_tag_id_to_index(tag, -1)
        self._map_tag_id_to_cluster(tag)

        return tag.id

    def get_tag(self, tag_id: int) -> Tag:
        """Returns a Tag object given a Tag ID."""
        return self.tags[self._tag_id_to_index_map[int(tag_id)]]

    def get_tag_cluster(self, tag_id: int) -> list[int]:
        """Returns a list of Tag IDs that reference this Tag."""
        if tag_id in self._tag_id_to_cluster_map:
            return self._tag_id_to_cluster_map[int(tag_id)]
        return []

    def sort_fields(self, entry_id: int, order: list[int]) -> None:
        """Sorts an Entry's Fields given an ordered list of Field IDs."""
        entry = self.get_entry(entry_id)
        entry.fields = sorted(
            entry.fields, key=lambda x: order.index(self.get_field_attr(x, "id"))
        )
