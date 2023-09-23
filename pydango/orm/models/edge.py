from abc import ABC
from typing import TYPE_CHECKING, Generic, Optional, TypeVar, Union

from pydantic import BaseModel, Field

from pydango.orm.encoders import jsonable_encoder
from pydango.orm.models import BaseArangoModel, CollectionConfig, CollectionType
from pydango.query.consts import FROM, TO

if TYPE_CHECKING:
    from pydantic.typing import DictStrAny

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
