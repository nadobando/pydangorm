import json
from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

from pydango.query.utils import Compilable


class Options(Compilable):
    _map: dict = {}

    def compile(self):
        pairs = []

        for field, value in self._map.items():
            if value is None:
                continue
            pairs.append(f"{field}: {json.dumps(value)}")
        if pairs:
            return f"{{{', '.join(pairs)}}}"


@dataclass
class LoopOptions(Options):
    index_hint: Optional[Union[list[str], str]] = None
    force_index_hint: Optional[bool] = None
    disable_index: Optional[bool] = None
    max_projections: Optional[int] = None
    use_cache: Optional[bool] = None
    look_ahead: Optional[int] = None

    def __post_init__(self):
        self._map = {
            "IndexHint": self.index_hint,
            "forceIndexHint": self.force_index_hint,
            "disableIndex": self.disable_index,
            "maxProjections": self.max_projections,
            "useCache": self.use_cache,
            "lookAhead": self.look_ahead,
        }


# noinspection DuplicatedCode
@dataclass
class BaseModificationOptions(Options, ABC):
    ignore_errors: Optional[bool] = None
    wait_for_sync: Optional[bool] = None
    ignore_revs: Optional[bool] = None
    exclusive: Optional[bool] = None
    refill_index_caches: Optional[bool] = None

    def __post_init__(self):
        self._map = {
            "ignoreErrors": self.ignore_errors,
            "waitForSync": self.wait_for_sync,
            "ignoreRevs": self.ignore_revs,
            "exclusive": self.exclusive,
            "refillIndexCaches": self.refill_index_caches,
        }


# noinspection DuplicatedCode
@dataclass()
class RemoveOptions(BaseModificationOptions):
    ignore_errors: Optional[bool] = None
    wait_for_sync: Optional[bool] = None
    ignore_revs: Optional[bool] = None
    exclusive: Optional[bool] = None
    refill_index_caches: Optional[bool] = None

    def __post_init__(self):
        self._map = {
            "ignoreErrors": self.ignore_errors,
            "waitForSync": self.wait_for_sync,
            "ignoreRevs": self.ignore_revs,
            "exclusive": self.exclusive,
            "refillIndexCaches": self.refill_index_caches,
        }


@dataclass()
class UpdateOptions(BaseModificationOptions):
    ignore_errors: Optional[bool] = None
    keep_null: Optional[bool] = None
    merge_objects: Optional[bool] = None
    wait_for_sync: Optional[bool] = None
    ignore_revs: Optional[bool] = None
    exclusive: Optional[bool] = None
    refill_index_caches: Optional[bool] = None

    def __post_init__(self):
        self._map = {
            "ignoreErrors": self.ignore_errors,
            "keepNull": self.keep_null,
            "mergeObjects": self.merge_objects,
            "waitForSync": self.wait_for_sync,
            "ignoreRevs": self.ignore_revs,
            "exclusive": self.exclusive,
            "refillIndexCaches": self.refill_index_caches,
        }


# noinspection DuplicatedCode
@dataclass()
class ReplaceOptions(BaseModificationOptions):
    ignore_errors: Optional[bool] = None
    wait_for_sync: Optional[bool] = None
    ignore_revs: Optional[bool] = None
    exclusive: Optional[bool] = None
    refill_index_caches: Optional[bool] = None

    def __post_init__(self):
        self._map = {
            "ignoreErrors": self.ignore_errors,
            "waitForSync": self.wait_for_sync,
            "ignoreRevs": self.ignore_revs,
            "exclusive": self.exclusive,
            "refillIndexCaches": self.refill_index_caches,
        }


@dataclass()
class UpsertOptions(BaseModificationOptions):
    ignore_errors: Optional[bool] = None
    keep_null: Optional[bool] = None
    merge_objects: Optional[bool] = None
    wait_for_sync: Optional[bool] = None
    ignore_revs: Optional[bool] = None
    exclusive: Optional[bool] = None
    index_hint: Optional[Union[list[str], str]] = None
    force_index_hint: Optional[bool] = None

    def __post_init__(self):
        self._map = {
            "ignoreErrors": self.ignore_errors,
            "keepNull": self.keep_null,
            "mergeObjects": self.merge_objects,
            "waitForSync": self.wait_for_sync,
            "ignoreRevs": self.ignore_revs,
            "exclusive": self.exclusive,
            "indexHint": self.index_hint,
            "forceIndexHint": self.force_index_hint,
        }


class CollectMethod(str, Enum):
    SORTED = "sorted"
    HASH = "hash"


@dataclass()
class CollectOptions(Options):
    method: CollectMethod
