from pathlib import Path
from typing import Sequence, Type, TypeVar

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from src.database.table_declarations.entry import Entry  # type: ignore
from src.database.table_declarations.field import (  # type: ignore
    DatetimeField,
    Field,
    TagBoxField,
    TextField,
)
from src.database.table_declarations.tag import Tag  # type: ignore

Queryable = TypeVar("Queryable", Tag, Entry, TextField, DatetimeField, TagBoxField)


def path_in_db(path: Path, engine: Engine) -> bool:
    with Session(engine) as session, session.begin():
        result = session.execute(
            select(Entry.id).where(Entry.path == path)
        ).one_or_none()

        result_bool = bool(result)

    return result_bool


def get_entry(entry: int | Entry, session: Session) -> Entry:
    if isinstance(entry, Entry):
        entry = entry.id
    return get_object_by_id(id=entry, type=Entry, session=session)


def get_tag(tag: int | Tag, session: Session) -> Tag:
    if isinstance(tag, Tag):
        tag = tag.id
    return get_object_by_id(id=tag, type=Tag, session=session)


def get_field(field: Field, session: Session) -> Field:
    return get_object_by_id(id=field.id, type=field.__class__, session=session)  # type: ignore


def get_object_by_id(
    id: int,
    type: Type[Queryable],
    session: Session,
) -> Queryable:
    result: Queryable = session.scalars(
        select(type).where(type.id == id).limit(1)  # type: ignore
    ).one()

    return result


def get_objects_by_ids(
    ids: Sequence[int],
    type: Queryable,
    session: Session,
) -> list[Queryable]:
    results: list[Queryable] = list(
        session.scalars(select(type).where(type.id.in_(ids))).all()  # type: ignore
    )

    session.expunge_all()

    return results
