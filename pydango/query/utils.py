# utils.py
from enum import Enum
from typing import Protocol, TypeVar


class Compilable(Protocol):
    def compile(self, *args, **kwargs) -> str:
        ...


class SortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


T = TypeVar("T")
