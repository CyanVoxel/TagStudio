# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio

"""The Library object and related methods for TagStudio."""

import datetime
import logging
import os
import time
import typing
from pathlib import Path
from typing import Iterator, Literal, cast
from alt_core import constants

from sqlalchemy import and_, select
from sqlalchemy.orm import Session
from src.alt_core.constants import DEFAULT_FIELDS
from src.alt_core.types import EntrySearchResult, SearchResult
from src.core.json_typing import JsonCollation, JsonTag
from src.database.manage import make_engine, make_tables
from src.database.queries import path_in_db
from src.database.table_declarations.entry import Entry
from src.database.table_declarations.field import (
    DatetimeField,
    Field,
    TagBoxField,
    TagBoxTypes,
    TextField,
)
from src.database.table_declarations.tag import Tag, TagAlias, TagColor, TagInfo
from typing_extensions import Self

logging.basicConfig(format="%(message)s", level=logging.INFO)
LOGGER = logging.getLogger(__name__)


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

    @typing.no_type_check
    def __eq__(self, __value: object) -> bool:
        __value = cast(Self, __value)
        if os.name == "nt":
            return (
                int(self.id) == int(__value.id)
                and self.filename.lower() == __value.filename.lower()
                and self.path.lower() == __value.path.lower()
                and self.fields == __value.fields
            )
        else:
            return (
                int(self.id) == int(__value.id)
                and self.filename == __value.filename
                and self.path == __value.path
                and self.fields == __value.fields
            )

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


def library_defaults() -> list[Tag]:
    archive_tag = Tag(
        name="Archived",
        aliases=set([TagAlias(name="Archive")]),
        color=TagColor.red,
    )

    favorite_tag = Tag(
        name="Favorite",
        aliases=set(
            [
                TagAlias(name="Favorited"),
                TagAlias(name="Favorites"),
            ]
        ),
        color=TagColor.yellow,
    )

    return [archive_tag, favorite_tag]


class Library:
    """Class for the Library object, and all CRUD operations made upon it."""

    # Cache common tags
    __favorite_tag: Tag | None = None
    __archived_tag: Tag | None = None

    @property
    def entries(self) -> list[Entry]:
        with Session(self.engine) as session, session.begin():
            entries = list(session.scalars(select(Entry)).all())
            session.expunge_all()
        return entries

    @property
    def tags(self) -> list[Tag]:
        with Session(self.engine) as session, session.begin():
            tags = list(session.scalars(select(Tag)).all())
            session.expunge_all()
        return tags

    @property
    def archived_tag(self) -> Tag:
        if self.__archived_tag is None:
            with Session(self.engine) as session, session.begin():
                tag = session.scalars(select(Tag).where(Tag.name == "Archived")).one()
                session.expunge(tag)
            self.__archived_tag = tag
        return self.__archived_tag

    @property
    def favorite_tag(self) -> Tag:
        if self.__favorite_tag is None:
            with Session(self.engine) as session, session.begin():
                tag = session.scalars(select(Tag).where(Tag.name == "Favorite")).one()
                session.expunge(tag)
            self.__favorite_tag = tag
        return self.__favorite_tag

    def __init__(self) -> None:
        # Library Info =========================================================
        self.root_path: Path | None = None
        # Collations ===========================================================
        # List of every Collation object.
        self.collations: list[Collation] = []
        # File Interfacing =====================================================
        self.dir_file_count: int = -1
        self.files_not_in_library: list[str] = []
        self.missing_files: list[str] = []
        self.dupe_files: list[tuple[str, str, int]] = []
        self.filename_to_entry_id_map: dict[str, int] = {}
        self.default_ext_blacklist: list[str] = ["json", "xmp", "aae"]
        self.ignored_extensions: list[str] = self.default_ext_blacklist

    def create_library(self, path: str | Path) -> bool:
        """Creates an SQLite DB at path.

        Args:
            path (str): Path for database

        Returns:
            bool: True if created, False if error.
        """

        if isinstance(path, str):
            path = Path(path)

        # If '.TagStudio' is the name, raise path by one.
        if constants.TS_FOLDER_NAME == path.name:
            path = path.parent

        try:
            self.clear_internal_vars()
            self.root_path = path
            self.verify_ts_folders()

            connection_string = (
                f"sqlite:///{path / constants.TS_FOLDER_NAME / constants.LIBRARY_FILENAME}"
            )
            self.engine = make_engine(connection_string=connection_string)
            make_tables(engine=self.engine)

            session = Session(self.engine)
            with session.begin():
                session.add_all(library_defaults())

        except Exception as e:
            LOGGER.exception(e)
            return False

        return True

    def verify_ts_folders(self) -> None:
        """Verifies/creates folders required by TagStudio."""

        if self.root_path is None:
            raise ValueError("No path set.")

        full_ts_path = self.root_path / constants.TS_FOLDER_NAME
        full_backup_path = full_ts_path / constants.BACKUP_FOLDER_NAME
        full_collage_path = full_ts_path / constants.COLLAGE_FOLDER_NAME

        for path in [full_ts_path, full_backup_path, full_collage_path]:
            if not path.exists() and not path.is_dir():
                path.mkdir(parents=True, exist_ok=True)

    def verify_default_tags(self, tag_list: list[JsonTag]) -> list[JsonTag]:
        """
        Ensures that the default builtin tags  are present in the Library's
        save file. Takes in and returns the tag dictionary from the JSON file.
        """
        missing: list[JsonTag] = []

        for m in missing:
            tag_list.append(m)

        return tag_list

    def open_library(self, path: str | Path) -> bool:
        """Opens an SQLite DB at path.

        Args:
            path (str): Path for database

        Returns:
            bool: True if exists/opened, False if not.
        """
        if isinstance(path, str):
            path = Path(path)

        # If '.TagStudio' is the name, raise path by one.
        if constants.TS_FOLDER_NAME == path.name:
            path = path.parent

        sqlite_path = path / constants.TS_FOLDER_NAME / constants.LIBRARY_FILENAME

        if sqlite_path.exists() and sqlite_path.is_file():
            logging.info("[LIBRARY] Opening Library")
            connection_string = f"sqlite:///{sqlite_path}"
            self.engine = make_engine(connection_string=connection_string)
            make_tables(engine=self.engine)
            self.root_path = path

            return True
        else:
            logging.info("[LIBRARY] Creating Library")
            return self.create_library(path=path)

    def clear_internal_vars(self):
        """Clears the internal variables of the Library object."""
        self.root_path = None
        self.missing_matches = {}
        self.dir_file_count = -1
        self.files_not_in_library.clear()
        self.missing_files.clear()
        self.filename_to_entry_id_map = {}
        self.ignored_extensions = self.default_ext_blacklist

    def refresh_dir(self) -> Iterator[int]:
        """Scans a directory for files, and adds those relative filenames to internal variables."""

        if self.root_path is None:
            raise ValueError("No library path set.")

        self.dir_file_count = 0

        # Scans the directory for files, keeping track of:
        #   - Total file count
        start_time = time.time()
        for path in self.root_path.glob("**/*"):
            str_path = str(path)
            if (
                not path.is_dir()
                and "$RECYCLE.BIN" not in str_path
                and constants.TS_FOLDER_NAME not in str_path
                and "tagstudio_thumbs" not in str_path
            ):
                suffix = path.suffix.lower()
                if suffix != "" and suffix[0] == ".":
                    suffix = suffix[1:]

                if suffix not in self.ignored_extensions:
                    self.dir_file_count += 1

                    relative_path = path.relative_to(self.root_path)
                    if not path_in_db(path=relative_path, engine=self.engine):
                        self.add_entry_to_library(entry=Entry(path=relative_path))

            end_time = time.time()
            # Yield output every 1/30 of a second
            if (end_time - start_time) > 0.034:
                yield self.dir_file_count
                start_time = time.time()

    def refresh_missing_files(self) -> Iterator[int]:
        """Tracks the number of Entries that point to an invalid file path."""
        self.missing_files.clear()

        if self.root_path is None:
            raise ValueError("No library path set.")

        for i, entry in enumerate(self.entries):
            full_path = self.root_path / entry.path
            if not full_path.exists() or not full_path.is_file():
                self.missing_files.append(str(full_path))
            yield i

    def remove_entry(self, entry_id: int) -> None:
        """Removes an Entry from the Library."""

        with Session(self.engine) as session, session.begin():
            entry = session.scalar(select(Entry).where(Entry.id == entry_id))
            if entry is None:
                raise ValueError("")
            session.delete(entry)

    # TODO
    def refresh_dupe_entries(self):
        """
        Refreshes the list of duplicate Entries.
        A duplicate Entry is defined as an Entry pointing to a file that one or more
        other Entries are also pointing to.\n
        `dupe_entries = tuple(int, list[int])`
        """
        pass

    # TODO
    def merge_dupe_entries(self):
        """
        Merges duplicate Entries.
        A duplicate Entry is defined as an Entry pointing to a file that one or more
        other Entries are also pointing to.\n
        `dupe_entries = tuple(int, list[int])`
        """
        pass

    # TODO
    def refresh_dupe_files(self):
        """
        Refreshes the list of duplicate files.
        A duplicate file is defined as an identical or near-identical file as determined
        by a DupeGuru results file.
        """
        pass

    # TODO
    def remove_missing_files(self):
        pass

    # TODO
    def remove_missing_matches(self, fixed_indices: list[int]):
        pass

    # TODO
    def fix_missing_files(self):
        """
        Attempts to repair Entries that point to invalid file paths.
        """

        pass

    # TODO
    def _match_missing_file(self, file: str) -> list[str]:
        """
        Tries to find missing entry files within the library directory.
        Works if files were just moved to different subfolders and don't have duplicate names.
        """

        # self.refresh_missing_files()

        matches = [""]

        return matches

    # TODO
    def count_tag_entry_refs(self) -> None:
        """
        Counts the number of entry references for each tag. Stores results
        in `tag_entry_ref_map`.
        """
        pass

    def add_entry_to_library(self, entry: Entry) -> int:
        with Session(self.engine) as session, session.begin():
            session.add(entry)
            session.flush()
            id = entry.id
        return id

    def get_entry(self, entry_id: int) -> Entry:
        """Returns an Entry object given an Entry ID."""
        with Session(self.engine) as session, session.begin():
            entry = session.scalar(select(Entry).where(Entry.id == entry_id))
            session.expunge(entry)

        if entry is None:
            raise ValueError(f"Entry with id {entry_id} not found.")

        return entry

    def get_entry_and_fields(self, entry_id: int) -> Entry:
        """Returns an Entry object given an Entry ID."""
        with Session(self.engine) as session, session.begin():
            entry = session.scalars(
                select(Entry).where(Entry.id == entry_id).limit(1)
            ).one()

            _ = entry.fields
            for tag in entry.tags:
                tag.subtags
                tag.alias_strings

            session.expunge_all()

        return entry

    # TODO
    def search_library(
        self,
        query: str | None = None,
        entries: bool = True,
        collations: bool = True,
        tag_groups: bool = True,
    ) -> list[SearchResult]:
        """
        Uses a search query to generate a filtered results list.
        Returns a list of SearchResult.
        """
        if not hasattr(self, "engine"):
            return []

        results: list[SearchResult] = []
        with Session(self.engine) as session, session.begin():
            statement = select(Entry)

            if query:
                tag_id: int | None = None

                if "tag_id:" in query:
                    potential_tag_id = query.split(":")[-1].strip()
                    if potential_tag_id.isdigit():
                        tag_id = int(potential_tag_id)

                if tag_id is not None:
                    statement = (
                        statement.join(Entry.tag_box_fields)
                        .join(TagBoxField.tags)
                        .where(Tag.id == tag_id)
                    )
                else:
                    statement = statement.where(Entry.path.like(f"%{query}%"))

            entries_ = session.scalars(statement)

            for entry in entries_:
                results.append(
                    EntrySearchResult(
                        id=entry.id,
                        path=entry.path,
                        favorited=entry.favorited,
                        archived=entry.archived,
                    )
                )

        return results

    # TODO
    def search_tags(
        self,
        query: str,
        include_cluster: bool = False,
        ignore_builtin: bool = False,
        threshold: int = 1,
        context: list[str] | None = None,
    ) -> list[Tag]:
        """Returns a list of Tag IDs returned from a string query."""

        return self.tags

    def get_all_child_tag_ids(self, tag_id: int) -> list[int]:
        """Recursively traverse a Tag's subtags and return a list of all children tags."""

        all_subtags: set[int] = set([tag_id])

        with Session(self.engine) as session, session.begin():
            tag = session.scalar(select(Tag).where(Tag.id == tag_id))
            if tag is None:
                raise ValueError(f"No tag found with id {tag_id}.")

            subtag_ids = tag.subtag_ids

        all_subtags.update(subtag_ids)

        for sub_id in subtag_ids:
            all_subtags.update(self.get_all_child_tag_ids(sub_id))

        return list(all_subtags)

    # TODO
    def filter_field_templates(self, query: str) -> list[int]:
        """Returns a list of Field Template IDs returned from a string query."""

        matches: list[int] = []

        return matches

    def update_tag(self, tag_info: TagInfo) -> None:
        """
        Edits a Tag in the Library.
        This function undoes and redos the following parts of the 'add_tag_to_library()' process:\n
        - Un-maps the old Tag name, shorthand, and aliases from the Tag ID
        and re-maps the new strings to its ID via '_map_tag_names_to_tag_id()'.\n
        - Un
        """

        with Session(self.engine) as session, session.begin():
            tag_to_update = session.scalars(
                select(Tag).where(Tag.id == tag_info.id)
            ).one()

            tag_to_update.name = tag_info.name
            tag_to_update.shorthand = tag_info.shorthand
            tag_to_update.color = tag_info.color
            tag_to_update.icon = tag_info.icon

            for old_alias in tag_to_update.aliases:
                session.delete(old_alias)

            tag_to_update.aliases = set(
                [TagAlias(name=name) for name in tag_info.aliases]
            )

            subtags = session.scalars(
                select(Tag).where(Tag.id.in_(tag_info.subtag_ids))
            ).all()
            parent_tags = session.scalars(
                select(Tag).where(Tag.id.in_(tag_info.parent_tag_ids))
            ).all()

            tag_to_update.subtags.clear()
            tag_to_update.subtags.update(subtags)

            tag_to_update.parent_tags.clear()
            tag_to_update.parent_tags.update(parent_tags)

            session.add(tag_to_update)
            session.commit()
            session.close_all()

    # TODO
    def remove_tag(self, tag_id: int) -> None:
        """
        Removes a Tag from the Library.
        Disconnects it from all internal lists and maps, then remaps others as needed.
        """
        pass

    def update_entry_path(self, entry: int | Entry, path: str) -> None:
        if isinstance(entry, Entry):
            entry = entry.id

        with Session(self.engine) as session, session.begin():
            entry_object = session.scalars(select(Entry).where(Entry.id == entry)).one()

            entry_object.path = Path(path)

    def remove_tag_from_field(self, tag: Tag, field: TagBoxField) -> None:
        with Session(self.engine) as session, session.begin():
            field_ = session.scalars(
                select(TagBoxField).where(TagBoxField.id == field.id)
            ).one()

            tag = session.scalars(select(Tag).where(Tag.id == tag.id)).one()

            field_.tags.remove(tag)

    def remove_field(
        self,
        field: Field,
        entry_ids: list[int],
    ) -> None:
        with Session(self.engine) as session, session.begin():
            fields = session.scalars(
                select(field.__class__).where(
                    and_(
                        field.__class__.name == field.name,
                        field.__class__.entry_id.in_(entry_ids),
                    )
                )
            )

            for field_ in fields:
                session.delete(field_)

    def update_field(
        self,
        field: Field,
        content: str | datetime.datetime | set[Tag],
        entry_ids: list[int],
        mode: Literal["replace", "append", "remove"],
    ):
        with Session(self.engine) as session, session.begin():
            fields = session.scalars(
                select(field.__class__).where(
                    and_(
                        field.__class__.name == field.name,
                        field.__class__.entry_id.in_(entry_ids),
                    )
                )
            )
            for field_ in fields:
                if mode == "replace":
                    field_.value = content
                else:
                    raise NotImplementedError

    def add_field_to_entry(self, entry_id: int, field_id: int) -> None:
        with Session(self.engine) as session, session.begin():
            entry = session.scalars(select(Entry).where(Entry.id == entry_id)).one()

            default_field = DEFAULT_FIELDS[field_id]
            if default_field.class_ == TextField:
                entry.text_fields.append(
                    TextField(
                        name=default_field.name, type=default_field.type_, value=""
                    )
                )
            elif default_field.class_ == TagBoxField:
                entry.tag_box_fields.append(
                    TagBoxField(name=default_field.name, type=default_field.type_)
                )
            elif default_field.class_ == DatetimeField:
                entry.datetime_fields.append(
                    DatetimeField(name=default_field.name, type=default_field.type_)
                )
            else:
                raise ValueError("Unknown field.")

    def get_field_from_stale(self, stale_field: Field, session: Session) -> Field:
        return session.scalars(
            select(stale_field.__class__).where(
                stale_field.__class__.id == stale_field.id
            )
        ).one()

    def create_tag(self, tag_info: TagInfo) -> None:
        with Session(self.engine) as session, session.begin():
            subtags = set(
                session.scalars(
                    select(Tag).where(Tag.id.in_(tag_info.subtag_ids))
                ).all()
            )
            parent_tags = set(
                session.scalars(
                    select(Tag).where(Tag.id.in_(tag_info.parent_tag_ids))
                ).all()
            )

            session.add(
                Tag(
                    name=tag_info.name,
                    shorthand=tag_info.shorthand,
                    aliases=set([TagAlias(name=name) for name in tag_info.aliases]),
                    parent_tags=parent_tags,
                    subtags=subtags,
                    color=tag_info.color,
                    icon=tag_info.icon,
                )
            )

    def get_tag(
        self,
        tag: int | Tag,
        with_subtags: bool = False,
        with_parents: bool = False,
        with_aliases: bool = False,
    ) -> Tag:
        if isinstance(tag, Tag):
            tag = tag.id

        with Session(self.engine) as session, session.begin():
            tag_object = session.scalars(select(Tag).where(Tag.id == tag)).one()

            if with_subtags:
                _ = tag_object.subtags

            if with_parents:
                _ = tag_object.parent_tags

            if with_aliases:
                _ = tag_object.aliases
                _ = tag_object.alias_strings

            session.expunge(tag_object)

        return tag_object

    def get_tag_display_name(
        self,
        tag: int | Tag,
    ) -> str:
        if isinstance(tag, Tag):
            tag = tag.id

        with Session(self.engine) as session, session.begin():
            tag_object = session.scalars(select(Tag).where(Tag.id == tag)).one()

            return tag_object.display_name

    def add_tag_to_field(
        self,
        tag: int | Tag,
        field: TagBoxField,
    ) -> None:
        if isinstance(tag, Tag):
            tag = tag.id

        with Session(self.engine) as session, session.begin():
            tag_object = session.scalars(select(Tag).where(Tag.id == tag)).one()

            field_ = session.scalars(
                select(TagBoxField).where(TagBoxField.id == field.id)
            ).one()

            field_.tags.add(tag_object)

    def add_tag_to_entry_meta_tags(self, tag: int | Tag, entry_id: int) -> None:
        if isinstance(tag, Tag):
            tag = tag.id

        with Session(self.engine) as session, session.begin():
            meta_tag_box = session.scalars(
                select(TagBoxField).where(
                    and_(
                        TagBoxField.entry_id == entry_id,
                        TagBoxField.type == TagBoxTypes.meta_tag_box,
                    )
                )
            ).one()
            tag = session.scalars(select(Tag).where(Tag.id == tag)).one()

            meta_tag_box.tags.add(tag)

    def remove_tag_from_entry_meta_tags(self, tag: int | Tag, entry_id: int) -> None:
        if isinstance(tag, Tag):
            tag = tag.id

        with Session(self.engine) as session, session.begin():
            meta_tag_box = session.scalars(
                select(TagBoxField).where(
                    and_(
                        TagBoxField.entry_id == entry_id,
                        TagBoxField.type == TagBoxTypes.meta_tag_box,
                    )
                )
            ).one()
            tag = session.scalars(select(Tag).where(Tag.id == tag)).one()

            meta_tag_box.tags.remove(tag)

    def closing_database_session(self):
        with Session(self.engine) as session, session.begin():
            return session

    def entry_archived_favorited_status(self, entry: int | Entry) -> tuple[bool, bool]:
        if isinstance(entry, Entry):
            entry = entry.id
        with Session(self.engine) as session, session.begin():
            entry_ = session.scalars(select(Entry).where(Entry.id == entry)).one()

            return (entry_.archived, entry_.favorited)
