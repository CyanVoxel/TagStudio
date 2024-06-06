from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from tagstudio.src.database.manage import drop_tables, make_engine, make_tables
from tagstudio.src.database.table_declarations.entry import Entry
from tagstudio.src.database.table_declarations.field import (
    DatetimeField,
    FloatField,
    IntegerField,
    TagBoxField,
    TextField,
)
from tagstudio.src.database.table_declarations.tag import Tag, TagCategory

CONNECTION_STRING = "sqlite:///./example_database.sqlite"

ENGINE = make_engine(connection_string=CONNECTION_STRING)

# If prior schema defs
drop_tables(engine=ENGINE)
make_tables(engine=ENGINE)

# Populate with mock data
with Session(bind=ENGINE) as session, session.begin():
    mock_entry = Entry(path=Path("/mock_path/to/item.jpg"))

    archived_tag = Tag(name="Archived", category=TagCategory.meta_tag)
    favorited_tag = Tag(name="Favorited", category=TagCategory.meta_tag)

    user_tag = Tag(name="User Made Tag", category=TagCategory.user_tag)
    user_subtag = Tag(
        name="Subtag", category=TagCategory.user_tag, parent_tags=set([user_tag])
    )

    note_field = TextField(
        value="Example text value",
        name="Example Note",
    )
    integer_field = IntegerField(
        value=100,
        name="Example Integer",
    )
    float_field = FloatField(
        value=100.10,
        name="Example Float",
    )
    datetime_field = DatetimeField(
        value=datetime.now(),
        name="Example Datetime",
    )
    meta_tag_box_field = TagBoxField(
        value=TagCategory.meta_tag,
        name="Meta Tag Box",
    )
    user_tag_box_field = TagBoxField(
        value=TagCategory.user_tag,
        name="User Tag Box",
    )

    mock_entry.tags.update(
        [
            archived_tag,
            favorited_tag,
            user_tag,
        ]
    )

    mock_entry.fields.extend(
        [
            note_field,
            integer_field,
            float_field,
            datetime_field,
            meta_tag_box_field,
            user_tag_box_field,
        ]
    )

    session.add(mock_entry)


with Session(bind=ENGINE) as session, session.begin():
    entry = session.scalars(select(Entry).where(Entry.id == 1)).one()

    print("Entry information:")
    print(
        f"\tMeta tags: {[tag.name for tag in entry.category_tags(category=TagCategory.meta_tag)]}"
    )
    print(
        f"\tUser tags: {[tag.name for tag in entry.category_tags(category=TagCategory.user_tag)]}"
    )
    print(
        f"\t\tUser Tags' Subtags: {[(tag.name, [tag.name for tag in tag.subtags]) for tag in entry.category_tags(category=TagCategory.user_tag)]}"
    )
    print(f"\tIs archived: {entry.archived}")
    print(f"\tIs favorited: {entry.archived}")
    print(
        f"\tOrdered Fields: \n\t\t{"\n\t\t".join([f"{(i, field.name, field.value)}" for i, field in enumerate(entry.fields)])}"  # type: ignore
    )

    print("\nMoving first field to end, reordering, and committing to DB...\n")

    # Move field entry
    first_field = entry.fields.pop(0)
    entry.fields.append(first_field)
    # Reorder entries
    entry.fields.reorder()
    # Commit on context close

with Session(bind=ENGINE) as session, session.begin():
    entry = session.scalars(select(Entry).where(Entry.id == 1)).one()

    print("Entry information:")
    print(
        f"\tOrdered Fields: \n\t\t{"\n\t\t".join([f"{(i, field.name, field.value)}" for i, field in enumerate(entry.fields)])}"  # type: ignore
    )
