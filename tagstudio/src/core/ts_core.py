# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio

"""The core classes and methods of TagStudio."""

import json
from pathlib import Path

from src.core.library import Entry, Library
from src.core.constants import TS_FOLDER_NAME, TEXT_FIELDS


class TagStudioCore:
    """
    Instantiate this to establish a TagStudio session.
    Holds all TagStudio session data and provides methods to manage it.
    """

    def __init__(self):
        self.lib: Library = Library()

    def get_gdl_sidecar(self, filepath: str | Path, source: str = "") -> dict:
        """
        Attempts to open and dump a Gallery-DL Sidecar sidecar file for
        the filepath.\n Returns a formatted object with notable values or an
        empty object if none is found.
        """
        json_dump = {}
        info = {}
        _filepath: Path = Path(filepath)
        _filepath = _filepath.parent / (_filepath.stem + ".json")

        # NOTE: This fixes an unknown (recent?) bug in Gallery-DL where Instagram sidecar
        # files may be downloaded with indices starting at 1 rather than 0, unlike the posts.
        # This may only occur with sidecar files that are downloaded separate from posts.
        if source == "instagram":
            if not _filepath.is_file():
                newstem = _filepath.stem[:-16] + "1" + _filepath.stem[-15:]
                _filepath = _filepath.parent / (newstem + ".json")

        try:
            with open(_filepath, "r", encoding="utf8") as f:
                json_dump = json.load(f)

                if json_dump:
                    if source == "twitter":
                        info["content"] = json_dump["content"].strip()
                        info["date_published"] = json_dump["date"]
                    elif source == "instagram":
                        info["description"] = json_dump["description"].strip()
                        info["date_published"] = json_dump["date"]
                    elif source == "artstation":
                        info["title"] = json_dump["title"].strip()
                        info["artist"] = json_dump["user"]["full_name"].strip()
                        info["description"] = json_dump["description"].strip()
                        info["tags"] = json_dump["tags"]
                        # info["tags"] = [x for x in json_dump["mediums"]["name"]]
                        info["date_published"] = json_dump["date"]
                    elif source == "newgrounds":
                        # info["title"] = json_dump["title"]
                        # info["artist"] = json_dump["artist"]
                        # info["description"] = json_dump["description"]
                        info["tags"] = json_dump["tags"]
                        info["date_published"] = json_dump["date"]
                        info["artist"] = json_dump["user"].strip()
                        info["description"] = json_dump["description"].strip()
                        info["source"] = json_dump["post_url"].strip()
                    # else:
                    # 	print(
                    # 		f'[INFO]: TagStudio does not currently support sidecar files for "{source}"')

        # except FileNotFoundError:
        except Exception:
            # print(
            # 	f'[INFO]: No sidecar file found at "{os.path.normpath(file_path + ".json")}"')
            pass

        return info

    # def scrape(self, entry_id):
    # 	entry = self.lib.get_entry(entry_id)
    # 	if entry.fields:
    # 		urls: list[str] = []
    # 		if self.lib.get_field_index_in_entry(entry, 21):
    # 			urls.extend([self.lib.get_field_attr(entry.fields[x], 'content')
    # 						for x in self.lib.get_field_index_in_entry(entry, 21)])
    # 		if self.lib.get_field_index_in_entry(entry, 3):
    # 			urls.extend([self.lib.get_field_attr(entry.fields[x], 'content')
    # 						for x in self.lib.get_field_index_in_entry(entry, 3)])
    # 	# try:
    # 	if urls:
    # 		for url in urls:
    # 			url = "https://" + url if 'https://' not in url else url
    # 			html_doc = requests.get(url).text
    # 			soup = bs(html_doc, "html.parser")
    # 			print(soup)
    # 			input()

    # 	# except:
    # 	# 	# print("Could not resolve URL.")
    # 	# 	pass

    def match_conditions(self, entry_id: int) -> None:
        """Matches defined conditions against a file to add Entry data."""

        cond_file = self.lib.library_dir / TS_FOLDER_NAME / "conditions.json"
        # TODO: Make this stored somewhere better instead of temporarily in this JSON file.
        entry: Entry = self.lib.get_entry(entry_id)
        try:
            if cond_file.is_file():
                with open(cond_file, "r", encoding="utf8") as f:
                    json_dump = json.load(f)
                    for c in json_dump["conditions"]:
                        match: bool = False
                        for path_c in c["path_conditions"]:
                            if str(Path(path_c).resolve()) in str(entry.path):
                                match = True
                                break
                        if match:
                            if fields := c.get("fields"):
                                for field in fields:
                                    field_id = self.lib.get_field_attr(field, "id")
                                    content = field[field_id]

                                    if (
                                        self.lib.get_field_obj(int(field_id))["type"]
                                        == "tag_box"
                                    ):
                                        existing_fields: list[int] = (
                                            self.lib.get_field_index_in_entry(
                                                entry, field_id
                                            )
                                        )
                                        if existing_fields:
                                            self.lib.update_entry_field(
                                                entry_id,
                                                existing_fields[0],
                                                content,
                                                "append",
                                            )
                                        else:
                                            self.lib.add_field_to_entry(
                                                entry_id, field_id
                                            )
                                            self.lib.update_entry_field(
                                                entry_id, -1, content, "append"
                                            )

                                    if (
                                        self.lib.get_field_obj(int(field_id))["type"]
                                        in TEXT_FIELDS
                                    ):
                                        if not self.lib.does_field_content_exist(
                                            entry_id, field_id, content
                                        ):
                                            self.lib.add_field_to_entry(
                                                entry_id, field_id
                                            )
                                            self.lib.update_entry_field(
                                                entry_id, -1, content, "replace"
                                            )
        except Exception:
            print("Error in match_conditions...")
            # input()
            pass

    def build_url(self, entry_id: int, source: str):
        """Tries to rebuild a source URL given a specific filename structure."""

        source = source.lower().replace("-", " ").replace("_", " ")
        if "twitter" in source:
            return self._build_twitter_url(entry_id)
        elif "instagram" in source:
            return self._build_instagram_url(entry_id)

    def _build_twitter_url(self, entry_id: int):
        """
        Builds an Twitter URL given a specific filename structure.
        Method expects filename to be formatted as 'USERNAME_TWEET-ID_INDEX_YEAR-MM-DD'
        """
        try:
            entry = self.lib.get_entry(entry_id)
            stubs = str(entry.filename).rsplit("_", 3)
            # print(stubs)
            # source, author = os.path.split(entry.path)
            url = f"www.twitter.com/{stubs[0]}/status/{stubs[-3]}/photo/{stubs[-2]}"
            return url
        except Exception:
            return ""

    def _build_instagram_url(self, entry_id: int):
        """
        Builds an Instagram URL given a specific filename structure.
        Method expects filename to be formatted as 'USERNAME_POST-ID_INDEX_YEAR-MM-DD'
        """
        try:
            entry = self.lib.get_entry(entry_id)
            stubs = str(entry.filename).rsplit("_", 2)
            # stubs[0] = stubs[0].replace(f"{author}_", '', 1)
            # print(stubs)
            # NOTE: Both Instagram usernames AND their ID can have underscores in them,
            # so unless you have the exact username (which can change) on hand to remove,
            # your other best bet is to hope that the ID is only 11 characters long, which
            # seems to more or less be the case... for now...
            url = f"www.instagram.com/p/{stubs[-3][-11:]}"
            return url
        except Exception:
            return ""
