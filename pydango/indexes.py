import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Sequence, Union

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias


if TYPE_CHECKING:
    from aioarango.typings import Fields


@dataclass()
class Index: ...


@dataclass()
class GeoIndex(Index):
    fields: "Fields"
    ordered: Optional[bool] = None
    name: Optional[str] = None
    in_background: Optional[bool] = None


@dataclass
class HashIndex(Index):
    fields: Sequence[str]
    unique: Optional[bool] = None
    sparse: Optional[bool] = None
    deduplicate: Optional[bool] = None
    name: Optional[str] = None
    in_background: Optional[bool] = None


@dataclass
class SkipListIndex(Index):
    fields: Sequence[str]
    unique: Optional[bool] = None
    sparse: Optional[bool] = None
    deduplicate: Optional[bool] = None
    name: Optional[str] = None
    in_background: Optional[bool] = None


@dataclass
class FullTextIndex(Index):
    fields: Sequence[str]
    min_length: Optional[int] = None
    name: Optional[str] = None
    in_background: Optional[bool] = None


@dataclass
class PersistentIndex(Index):
    fields: Sequence[str]
    unique: Optional[bool] = None
    sparse: Optional[bool] = None
    name: Optional[str] = None
    in_background: Optional[bool] = None


@dataclass
class TTLIndex(Index):
    fields: Sequence[str]
    expiry_time: int
    name: Optional[str] = None
    in_background: Optional[bool] = None


Indexes: TypeAlias = Union[GeoIndex, HashIndex, SkipListIndex, FullTextIndex, PersistentIndex, TTLIndex]
