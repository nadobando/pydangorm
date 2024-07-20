from abc import ABC
from typing import TYPE_CHECKING, Generic, Optional, TypeVar, Union

from pydantic.v1 import BaseModel, Field

from pydango.orm.encoders import jsonable_encoder
from pydango.orm.models import BaseArangoModel, CollectionConfig, CollectionType
from pydango.query.consts import FROM, TO

if TYPE_CHECKING:
    from pydantic.v1.typing import DictStrAny

TEdge = TypeVar("TEdge", bound="EdgeModel")


class EdgeCollectionConfig(CollectionConfig):
    type = CollectionType.EDGE


class EdgeModel(BaseArangoModel, ABC):
    from_: Optional[str] = Field(None, alias=FROM)
    to: Optional[Union[str]] = Field(None, alias=TO)

    class Collection(EdgeCollectionConfig):
        pass

    def save_dict(self) -> "DictStrAny":
        exclude: set[Union[int, str]] = set()
        for key in ["from_", "to"]:
            if self.__getattribute__(key) is None:
                exclude.add(key)
        return jsonable_encoder(self, by_alias=True, exclude=exclude)
        # return self.dict(by_alias=True, exclude=exclude)


T = TypeVar("T", bound=BaseModel)


class EdgeData(BaseModel, ABC, Generic[T]):
    pass


class EdgeDict(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{item}'")

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, item):
        try:
            del self[item]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{item}'")
