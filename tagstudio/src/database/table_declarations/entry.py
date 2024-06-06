from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.orderinglist import OrderingList, ordering_list  # type: ignore
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .field import Field
from .joins import tag_entries
from .tag import Tag, TagCategory


class Entry(Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)

    path: Mapped[Path] = mapped_column(unique=True)

    fields: Mapped[OrderingList[Field]] = relationship(
        order_by="Field.position",
        collection_class=ordering_list("position"),  # type: ignore
    )

    tags: Mapped[set[Tag]] = relationship(
        secondary=tag_entries,
        back_populates="entries",
    )

    @property
    def favorited(self) -> bool:
        for tag in self.tags:
            if tag.name == "Favorite":
                return True
        return False

    @property
    def archived(self) -> bool:
        for tag in self.tags:
            if tag.name == "Archived":
                return True
        return False

    def category_tags(self, category: TagCategory) -> set[Tag]:
        return_tags: set[Tag] = set()
        for tag in self.tags:
            if tag.category == category:
                return_tags.add(tag)
        return return_tags

    # TODO
    # # Any Type
    # alts: Mapped[list[Entry]] = None

    # # Image/Video
    # self.dimensions: tuple[int, int] = None
    # self.crop: tuple[int, int, int, int] = None
    # self.mask: list[id] = None

    # # Video
    # self.length: float = None
    # self.trim: tuple[float, float] = None

    # # Text
    # self.word_count: int = None

    def __init__(
        self,
        path: Path,
        fields: list[Field] = [],
    ) -> None:
        self.path = path
        self.type = None

        ordering_list_: OrderingList[Field] = OrderingList()  # type: ignore
        ordering_list_.extend(fields)
        self.fields = ordering_list_

    def has_tag(self, tag: Tag) -> bool:
        return tag in self.tags

    def remove_tag(self, tag: Tag) -> None:
        if tag in self.tags:
            self.tags.remove(tag)

    def add_tag(self, tag: Tag) -> None:
        self.tags.add(tag)
