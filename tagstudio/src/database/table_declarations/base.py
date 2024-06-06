from pathlib import Path
from typing import Any

from sqlalchemy import (
    Dialect,
    String,
    TypeDecorator,
)
from sqlalchemy.orm import DeclarativeBase


class PathType(TypeDecorator):  # type: ignore
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect):
        if value is not None:
            return str(value)
        return None

    def process_result_value(self, value: Any, dialect: Dialect):
        if value is not None:
            return Path(value)
        return None


class Base(DeclarativeBase):
    type_annotation_map = {Path: PathType}
