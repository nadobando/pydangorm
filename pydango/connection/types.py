import sys
from collections import defaultdict, namedtuple
from enum import Enum
from typing import Type, Union

from indexed import IndexedOrderedDict

from pydango.orm import EdgeModel, VertexModel
from pydango.orm.models import BaseArangoModel
from pydango.query.options import UpsertOptions

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

CollectionUpsertOptions: TypeAlias = dict[Union[str, Type["BaseArangoModel"]], UpsertOptions]
ModelFieldMapping: TypeAlias = dict[int, defaultdict[str, list[tuple[int, int]]]]
VerticesIdsMapping: TypeAlias = dict[Type[VertexModel], dict[int, int]]
EdgesIdsMapping: TypeAlias = dict[Type[EdgeModel], dict[int, dict[int, int]]]

EdgeCollectionsMapping: TypeAlias = dict[Type[EdgeModel], IndexedOrderedDict[list[EdgeModel]]]
EdgeVerticesIndexMapping = dict[
    Type[EdgeModel], dict[int, dict[tuple[Type[VertexModel], Type[VertexModel]], list[int]]]
]

VertexCollectionsMapping = dict[Type[VertexModel], IndexedOrderedDict[BaseArangoModel]]

RelationGroup = namedtuple("RelationGroup", ["collection", "field", "model", "via_model"])


class UpdateStrategy(str, Enum):
    UPDATE = "update"
    REPLACE = "replace"
