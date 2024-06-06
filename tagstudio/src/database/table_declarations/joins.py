from sqlalchemy import Column, ForeignKey, Integer, Table

from .base import Base

tag_subtags = Table(
    "tag_subtags",
    Base.metadata,
    Column("parent_tag_id", Integer, ForeignKey("tags.id")),
    Column("subtag_id", Integer, ForeignKey("tags.id")),
)

tag_entries = Table(
    "tag_entries",
    Base.metadata,
    Column("entry_id", Integer, ForeignKey("entries.id")),
    Column("tag_id", Integer, ForeignKey("tags.id")),
)
