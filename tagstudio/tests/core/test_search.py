from src.core.library import ItemType, Library, Filter, Entry, SpecialFlag
from src.core.enums import SearchMode
import pytest


test_library = Library()

test_entry_one = Entry(
    id=0,
    filename="test_file1.png",
    path=".",
    fields=[{"6": [1000, 1001]}, {"1": ["James"]}],
)
test_entry_two = Entry(id=1, filename="test_file2.png", path="test_folder", fields=[{}])
test_entry_three = Entry(
    id=2,
    filename="test_file3.png",
    path="test_folder",
    fields=[{"6": [1001]}, {"4": "description"}],
)
test_entry_four = Entry(
    id=3,
    filename="test_file4.png",
    path="test_folder",
    fields=[{"1": ["Victor"]}, {"4": "description"}],
)
test_entry_five = Entry(
    id=4,
    filename="test_file5.png",
    path="test_folder",
    fields=[{"1": ["Victor"]}, {"1": ["James"]}],
)
test_entry_six = Entry(
    id=5,
    filename="test_file6.png",
    path=".",
    fields=[{"4": "description"}, {"4": "foo"}],
)

test_library.entries = [
    test_entry_one,
    test_entry_two,
    test_entry_three,
    test_entry_four,
    test_entry_five,
    test_entry_six,
]

filter = Filter(test_library)

### CASES ###


decomposition_cases: list[tuple] = [
    ("tag1 tag2", [{"unbound": ["tag1", "tag2"]}]),
    ("tag1 | tag2", [{"unbound": ["tag1"]}, {"unbound": ["tag2"]}]),
    ("tag1 tag2 | tag3", [{"unbound": ["tag1", "tag2"]}, {"unbound": ["tag3"]}]),
    ("tag1; description: desc", [{"unbound": ["tag1"], "description": "desc"}]),
    ("tag1; description: desc", [{"unbound": ["tag1"], "description": "desc"}]),
    (
        "tag1 -description | description: desc",
        [{"unbound": ["tag1"], "EMPTY": ["description"]}, {"description": "desc"}],
    ),
]

remap_cases: list[tuple] = [
    (test_entry_one, {"tags": [1000, 1001], "author": ["James"]}),
    (test_entry_two, {}),
    (test_entry_three, {"tags": [1001], "description": ["description"]}),
    (test_entry_four, {"author": ["Victor"], "description": ["description"]}),
    (test_entry_five, {"author": ["Victor", "James"]}),
]

filename_cases: list[tuple] = [
    (test_entry_two, "2", True),
    (test_entry_one, ".png", True),
    (test_entry_three, "test_folder", True),
    (test_entry_one, "file", True),
    (test_entry_four, None, False),
]

populate_tags_cases: list[tuple] = [
    (test_entry_one, ([1000, 1001], ["James"])),
    (test_entry_two, ([], [])),
    (test_entry_three, ([1001], [])),
    (test_entry_four, ([], ["Victor"])),
]

# no_author, untagged, empty, missing
special_flag_cases: list[tuple] = [
    ("no author untagged", (True, True, False, False)),
    ("empty no file", (False, False, True, True)),
    ("missing untagged no artist", (True, True, False, True)),
]

add_entries_from_special_cases: list[tuple] = [
    (test_entry_one, "no author", False),
    (test_entry_two, "empty", True),
    (test_entry_three, "no author", True),
    (test_entry_four, "untagged", True),
]

required_fields_empty_cases: list[tuple] = [
    (test_entry_one, ["author"], False),
    (test_entry_one, ["description"], True),
    (test_entry_two, ["description", "author"], True),
    (test_entry_three, ["author"], True),
]

filter_case_one: tuple = (
    [{"unbound": "no author", "description": "des"}],
    SearchMode.OR,
    [(ItemType.ENTRY, 2), (ItemType.ENTRY, 5)],
)
filter_case_two: tuple = (
    [{"unbound": "no tags"}, {"description": "des"}],
    SearchMode.OR,
    [
        (ItemType.ENTRY, 1),
        (ItemType.ENTRY, 2),
        (ItemType.ENTRY, 3),
        (ItemType.ENTRY, 4),
        (ItemType.ENTRY, 5),
    ],
)
filter_case_three: tuple = (
    [{"tag_id": "1000"}, {"unbound": "no author"}],
    SearchMode.AND,
    [],
)
filter_case_four: tuple = (
    [{"tag_id": "1001", "unbound": "no author"}],
    SearchMode.OR,
    [(ItemType.ENTRY, 2)],
)

filter_case_five: tuple = (
    [{"tag_id": "1000"}, {"unbound": "no author"}],
    SearchMode.OR,
    [
        (ItemType.ENTRY, 0),
        (ItemType.ENTRY, 1),
        (ItemType.ENTRY, 2),
        (ItemType.ENTRY, 5),
    ],
)

negative_filter_case_one: tuple = (
    [{"EMPTY": "description"}],
    SearchMode.OR,
    [(ItemType.ENTRY, 0), (ItemType.ENTRY, 1), (ItemType.ENTRY, 4)],
)

negative_filter_case_two: tuple = (
    [{"EMPTY": "author"}],
    SearchMode.OR,
    [(ItemType.ENTRY, 1), (ItemType.ENTRY, 2), (ItemType.ENTRY, 5)],
)

negative_filter_case_three: tuple = (
    [{"-description": "foo"}],
    SearchMode.OR,
    [
        (ItemType.ENTRY, 0),
        (ItemType.ENTRY, 1),
        (ItemType.ENTRY, 2),
        (ItemType.ENTRY, 3),
        (ItemType.ENTRY, 4),
    ],
)

negative_filter_case_four: tuple = (
    [{"-description": "desc", "description": "foo"}],
    SearchMode.OR,
    [],
)


filter_results_cases: list[tuple] = [
    filter_case_one,
    filter_case_two,
    filter_case_three,
    filter_case_four,
    filter_case_five,
    negative_filter_case_one,
    negative_filter_case_two,
    negative_filter_case_three,
    negative_filter_case_four,
]

### TESTS ###


@pytest.mark.parametrize("input,expected", decomposition_cases)
def test_query_decomposition(input: str, expected: list[dict]):
    assert test_library.parse_metadata(input) == expected
    pass


@pytest.mark.parametrize("entry,expected", remap_cases)
def test_remap_one(entry: Entry, expected: dict):
    assert filter.remap_fields(entry) == expected


@pytest.mark.parametrize("entry,query,result", filename_cases)
def test_filename(entry: Entry, query: str, result: bool):
    assert filter.check_filename(entry, query) == result


@pytest.mark.parametrize("entry,expected", populate_tags_cases)
def test_populate_tags(entry: Entry, expected: tuple):
    assert filter.populate_tags(entry) == expected
    pass


@pytest.mark.parametrize("query,flags", special_flag_cases)
def test_special_flag(query: str, flags: tuple[bool, bool, bool, bool]):
    special_flags = SpecialFlag(query)
    result = (
        special_flags.only_no_author,
        special_flags.only_untagged,
        special_flags.only_empty,
        special_flags.only_missing,
    )
    assert result == flags


@pytest.mark.parametrize("entry,unbound_query,expected", add_entries_from_special_cases)
def test_add_entries_from_special(entry: Entry, unbound_query: str, expected: bool):
    special_flags = SpecialFlag(unbound_query)
    (entry_tags, entry_authors) = filter.populate_tags(entry)
    result = filter.add_entries_from_special_flags(
        special_flags, entry_tags, entry_authors, entry
    )
    assert result == expected


@pytest.mark.parametrize("entry,empty_fields,expected", required_fields_empty_cases)
def test_required_fields_empty(entry: Entry, empty_fields: list[str], expected: bool):
    entry_fields: dict = filter.remap_fields(entry)
    result = filter.required_fields_empty(entry_fields, empty_fields)
    assert result == expected


@pytest.mark.parametrize("split_query,search_mode,expected", filter_results_cases)
def test_filter_results(
    split_query: list[dict], search_mode: SearchMode, expected: list[tuple | None]
):
    # result_set: set = set()
    # expected_set: set = set()
    assert set(filter.filter_results("", split_query, search_mode)) == set(expected)
