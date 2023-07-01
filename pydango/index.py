import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Awaitable, Callable, Optional, Sequence, Type, Union

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

from aioarango.collection import Collection
from aioarango.result import Result
from aioarango.typings import Json

if TYPE_CHECKING:
    from aioarango.typings import Fields


@dataclass()
class Index:
    ...


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

mapping: dict[Type[Indexes], Callable[..., Awaitable[Result[Json]]]] = {
    GeoIndex: Collection.add_geo_index,
    HashIndex: Collection.add_hash_index,
    SkipListIndex: Collection.add_skiplist_index,
    FullTextIndex: Collection.add_fulltext_index,
    PersistentIndex: Collection.add_persistent_index,
    TTLIndex: Collection.add_ttl_index,
}
