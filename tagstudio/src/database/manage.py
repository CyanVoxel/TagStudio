from sqlalchemy import Engine, create_engine

from .table_declarations.base import Base
from .table_declarations.entry import Entry
from .table_declarations.field import Field
from .table_declarations.tag import Tag, TagAlias

# Need to load subclasses for Base.metadata to function as intended
force_access = [
    Entry,
    Field,
    Tag,
    TagAlias,
]


def make_engine(connection_string: str) -> Engine:
    return create_engine(connection_string)


def make_tables(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def drop_tables(engine: Engine) -> None:
    Base.metadata.drop_all(engine)
