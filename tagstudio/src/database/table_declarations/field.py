from __future__ import annotations

import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .tag import TagCategory


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str]

    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "field",
    }

    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"))

    name: Mapped[str]

    position: Mapped[int]

    def __init__(
        self,
        name: str,
    ):
        self.name = name

        super().__init__()

    def __key(self):
        return (self.type, self.entry_id, self.name)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, value: object) -> bool:
        if isinstance(value, TextField):
            return self.__key() == value.__key()
        elif isinstance(value, TagBoxField):
            return False
        elif isinstance(value, DatetimeField):
            return False
        raise NotImplementedError


class TextField(Field):
    value: Mapped[str] = mapped_column("text_value", nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "text_field",
    }

    def __init__(
        self,
        value: str,
        name: str,
    ):
        self.value = value

        super().__init__(
            name=name,
        )


class IntegerField(Field):
    value: Mapped[int] = mapped_column("integer_value", nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "integer_field",
    }

    def __init__(
        self,
        name: str,
        value: int = 0,
    ):
        self.value = value

        super().__init__(
            name=name,
        )


class FloatField(Field):
    value: Mapped[float] = mapped_column("float_value", nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "float_field",
    }

    def __init__(
        self,
        name: str,
        value: float = 0.0,
    ):
        self.value = value

        super().__init__(
            name=name,
        )


class DatetimeField(Field):
    value: Mapped[datetime.datetime] = mapped_column("datetime_value", nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "date_field",
    }

    def __init__(
        self,
        value: datetime.datetime,
        name: str,
    ):
        self.value = value

        super().__init__(
            name=name,
        )


class TagBoxField(Field):
    value: Mapped[TagCategory] = mapped_column("tag_box_value", nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "tag_box_field",
    }

    def __init__(
        self,
        value: TagCategory,
        name: str,
    ):
        self.value = value

        super().__init__(
            name=name,
        )
