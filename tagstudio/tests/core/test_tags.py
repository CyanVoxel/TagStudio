import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.core.library import Tag

@pytest.fixture
def mock_library(mocker):
    return mocker.Mock()

@pytest.fixture
def mock_subtag(mocker):
    return mocker.Mock()

@pytest.fixture
def test_tag1():
    return Tag(id=1, name="tag1 Name", shorthand="tag1", aliases=[], subtags_ids=[2], color="")

@pytest.fixture
def test_tag2():
    return Tag(id=2, name="tag2 Name", shorthand="tag2", aliases=[], subtags_ids=[3], color="")

@pytest.fixture
def test_tag3():
    return Tag(id=3, name="tag3 Name", shorthand="tag3", aliases=[], subtags_ids=[], color="")

class TestTags():
    def test_construction(self):
        tag = Tag(
            id=1,
            name="Tag Name",
            shorthand="TN",
            aliases=["First A", "Second A"],
            subtags_ids=[2, 3, 4],
            color="",
        )
        assert tag
        assert tag.id == 1
        assert tag.name == "Tag Name"
        assert tag.shorthand == "TN"
        assert tag.aliases == ["First A", "Second A"]
        assert tag.subtag_ids == [2, 3, 4]
        assert tag.color == ""

    def test_empty_construction(self):
        tag = Tag(id=1, name="", shorthand="", aliases=[], subtags_ids=[], color="")
        assert tag.id == 1
        assert tag.name == ""
        assert tag.shorthand == ""
        assert tag.aliases == []
        assert tag.subtag_ids == []
        assert tag.color == ""

    def test_add_subtag(self, test_tag1):
        test_tag1.subtag_ids = []
        assert test_tag1.subtag_ids == []
        assert len(test_tag1.subtag_ids) == 0

        test_tag1.add_subtag(2)
        test_tag1.add_subtag(3)
        assert test_tag1.subtag_ids == [2,3]
        assert len(test_tag1.subtag_ids) == 2

        #No Duplicates added
        test_tag1.add_subtag(2)
        assert len(test_tag1.subtag_ids) == 2
        assert test_tag1.subtag_ids == [2,3]

    def test_remove_subtag(self, test_tag1):
        test_tag1.subtag_ids = [1,2,3,4,5]
        assert len(test_tag1.subtag_ids) == 5

        test_tag1.remove_subtag(3)
        assert len(test_tag1.subtag_ids) == 4
        assert test_tag1.subtag_ids == [1,2,4,5]

        test_tag1.remove_subtag(2)
        assert len(test_tag1.subtag_ids) == 3
        assert test_tag1.subtag_ids == [1,4,5]

    def test_remove_subtag_not_in_subtag_ids(self, test_tag1):
        test_tag1.remove_subtag(1)
        assert test_tag1.subtag_ids == [2]
        test_tag1.remove_subtag(2)
        assert test_tag1.subtag_ids == []
        test_tag1.remove_subtag(2)
        assert test_tag1.subtag_ids == []

    def test_debug_name(self, test_tag1, test_tag2):
        assert test_tag1.debug_name() == "tag1 Name (ID: 1)"
        assert test_tag2.debug_name() == "tag2 Name (ID: 2)"

    def test_display_name_no_shorthand(self, mock_library, test_tag1, test_tag2):
        test_tag2.shorthand = ""
        mock_library.get_tag.return_value = test_tag2
        result = test_tag1.display_name(mock_library)
        assert result == "tag1 Name (tag2 Name)"

    def test_display_name_with_shorthand(self, mock_library, test_tag1, test_tag2):
        mock_library.get_tag.return_value = test_tag2
        result = test_tag1.display_name(mock_library)
        assert result == "tag1 Name (tag2)"

    def test_display_name_no_subtags(self, mock_library, test_tag1):
        test_tag1.subtag_ids = []
        result = test_tag1.display_name(mock_library)
        assert result == "tag1 Name"
'''
    #This probably isn't how we want display_names to work. But these tests pass if uncommented
    def test_display_name_no_name(self, mock_library, test_tag1, test_tag2):
        test_tag2.name = ""
        test_tag1.name = ""
        test_tag2.shorthand = ""
        test_tag1.shorthand = ""

        mock_library.get_tag.return_value = test_tag2
        result = test_tag1.display_name(mock_library)
        assert result == " ()"

    def test_display_name_no_name_no_subtag_ids(self, mock_library, test_tag1):
        test_tag1.name = ""
        test_tag1.shorthand = ""
        test_tag1.subtag_ids = []

        result = test_tag1.display_name(mock_library)
        assert result == ""

    def test_display_name_no_name_with_subtag_name(self, mock_library, test_tag1, test_tag2):
        test_tag1.name = ""
        test_tag1.shorthand = ""
        test_tag1.subtag_ids = [2]

        mock_library.get_tag.return_value = test_tag2
        result = test_tag1.display_name(mock_library)
        assert result == " (tag2)"

    def test_display_name_no_name_with_subtag_name_no_shorthand(self, mock_library, test_tag1, test_tag2):
        test_tag1.name = ""
        test_tag1.shorthand = ""
        test_tag1.subtag_ids = [2]
        test_tag2.shorthand = ""

        mock_library.get_tag.return_value = test_tag2
        result = test_tag1.display_name(mock_library)
        assert result == " (tag2 Name)"

    def test_display_name_2_subtags_no_shorthand(self, mock_library, test_tag1, test_tag2, test_tag3):
        test_tag2.shorthand = ""
        test_tag3.shorthand = ""
        test_tag1.subtag_ids = [2,3]

        mock_library.get_tag.return_value = test_tag2
        result = test_tag1.display_name(mock_library)
        assert result == "tag1 Name (tag2 Name)"
'''