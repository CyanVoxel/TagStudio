from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SettingItems(str, Enum):
    """List of setting item names."""

    START_LOAD_LAST = "start_load_last"
    LAST_LIBRARY = "last_library"
    LIBS_LIST = "libs_list"
    WINDOW_SHOW_LIBS = "window_show_libs"


class Theme(str, Enum):
    COLOR_BG = "#65000000"
    COLOR_HOVER = "#65AAAAAA"
    COLOR_PRESSED = "#65EEEEEE"


@dataclass
class EntrySearchResult:
    id: int
    path: Path
    favorited: bool
    archived: bool

    @property
    def __key(self) -> tuple[int, str, bool, bool]:
        return (self.id, str(self.path), self.favorited, self.archived)

    def __hash__(self) -> int:
        return hash(self.__key)

    def __eq__(self, value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, EntrySearchResult):
            return value.__key == self.__key
        elif isinstance(value, (CollationSearchResult, TagGroupSearchResult)):
            return False
        raise ValueError(f"Type {type(value)} not comparable.")


@dataclass
class CollationSearchResult:
    id: int

    @property
    def __key(self) -> int:
        return self.id

    def __hash__(self) -> int:
        return hash(self.__key)

    def __eq__(self, value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, CollationSearchResult):
            return value.__key == self.__key
        elif isinstance(value, (EntrySearchResult, TagGroupSearchResult)):
            return False
        raise ValueError(f"Type {type(value)} not comparable.")


@dataclass
class TagGroupSearchResult:
    id: int

    @property
    def __key(self) -> int:
        return self.id

    def __hash__(self) -> int:
        return hash(self.__key)

    def __eq__(self, value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, TagGroupSearchResult):
            return value.__key == self.__key
        elif isinstance(value, (EntrySearchResult, CollationSearchResult)):
            return False
        raise ValueError(f"Type {type(value)} not comparable.")


SearchResult = EntrySearchResult | CollationSearchResult | TagGroupSearchResult
Frame = list[SearchResult]
Frames = list[Frame]


class TagColor(Enum):
    default = ""
    black = "black"
    dark_gray = "dark gray"
    gray = "gray"
    light_gray = "light gray"
    white = "white"
    light_pink = "light pink"
    pink = "pink"
    red = "red"
    red_orange = "red orange"
    orange = "orange"
    yellow_orange = "yellow orange"
    yellow = "yellow"
    lime = "lime"
    light_green = "light green"
    mint = "mint"
    green = "green"
    teal = "teal"
    cyan = "cyan"
    light_blue = "light blue"
    blue = "blue"
    blue_violet = "blue violet"
    violet = "violet"
    purple = "purple"
    lavender = "lavender"
    berry = "berry"
    magenta = "magenta"
    salmon = "salmon"
    auburn = "auburn"
    dark_brown = "dark brown"
    brown = "brown"
    light_brown = "light brown"
    blonde = "blonde"
    peach = "peach"
    warm_gray = "warm gray"
    cool_gray = "cool gray"
    olive = "olive"
