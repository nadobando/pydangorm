from dataclasses import dataclass
from typing import Optional, Sequence

import aioarango.database
from aioarango.typings import Fields


@dataclass()
class Index:
    ...


@dataclass()
class GeoIndex(Index):
    fields: Fields
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


mapping = {
    GeoIndex: aioarango.database.StandardCollection.add_geo_index,
    PersistentIndex: aioarango.database.StandardCollection.add_persistent_index,
    FullTextIndex: aioarango.database.StandardCollection.add_fulltext_index,
    SkipListIndex: aioarango.database.StandardCollection.add_skiplist_index,
    TTLIndex: aioarango.database.StandardCollection.add_ttl_index,
    HashIndex: aioarango.database.StandardCollection.add_hash_index,
}
