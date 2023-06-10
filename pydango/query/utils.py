from enum import Enum
from typing import Protocol, TypeVar, Union


class Compilable(Protocol):
    def compile(self, *args, **kwargs) -> Union[str, None]:
        ...


class SortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


T = TypeVar("T")
