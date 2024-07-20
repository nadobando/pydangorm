from typing import (
    TYPE_CHECKING,
    Any,
    ForwardRef,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from pydantic.v1.fields import Field, ModelField
from pydantic.v1.main import create_model
from pydantic.v1.typing import evaluate_forwardref

from pydango.orm.consts import EDGES
from pydango.orm.encoders import jsonable_encoder
from pydango.orm.models import BaseArangoModel, CollectionConfig, CollectionType
from pydango.orm.models.base import LIST_TYPES, ArangoModelMeta, LinkTypes
from pydango.orm.models.edge import EdgeData, EdgeDict
from pydango.orm.models.types import EdgeFieldMapping, Relationships
from pydango.orm.models.utils import convert_edge_data_to_valid_kwargs
from pydango.orm.utils import evaluate_forward_ref, get_globals

if TYPE_CHECKING:
    from pydantic.v1.typing import AbstractSetIntStr, DictStrAny, MappingIntStrAny

TVertexModel = TypeVar("TVertexModel", bound="VertexModel")
TEdges = TypeVar("TEdges", bound=EdgeData)


class VertexCollectionConfig(CollectionConfig):
    type = CollectionType.NODE


class VertexMeta(ArangoModelMeta):
    def __new__(mcs, name: str, bases: tuple[Type], namespace: dict, **kwargs: Any):
        parents = [b for b in bases if isinstance(b, mcs)]
        if not parents:
            return super().__new__(mcs, name, bases, namespace, **kwargs)
        _relationships, original_annotations = mcs.get_relations_from_namespace(namespace)
        __edge_to_field_mapping__, edge_annotation = mcs.build_edges_model(_relationships, bases, name, namespace)

        namespace["__edge_to_field_mapping__"] = __edge_to_field_mapping__
        namespace["__annotations__"][EDGES] = edge_annotation

        return super().__new__(mcs, name, bases, namespace, **kwargs)

    @staticmethod
    def build_edges_model(
        _relationships: Relationships, bases: tuple[Type[Any]], name: str, namespace: dict[str, Any]
    ) -> tuple[EdgeFieldMapping, ModelField]:
        if VertexModel in bases:
            edges_model = VertexMeta._build_model(_relationships, name)
            namespace[EDGES] = Field(None, exclude=True)
            edge_annotation = cast(Any, Optional[edges_model])
        else:
            namespace[EDGES] = Field(None, exclude=True)
            edge_annotation = cast(Any, None)

        __edge_to_field_mapping__ = VertexMeta._build_edge_to_field_mapping(_relationships)

        VertexMeta._validate_edges(__edge_to_field_mapping__, namespace)
        return __edge_to_field_mapping__, edge_annotation

    @staticmethod
    def _build_edge_to_field_mapping(relationships: Relationships) -> EdgeFieldMapping:
        __edge_to_field_mapping__: EdgeFieldMapping = {}
        for relation_field, relation_info in relationships.items():
            if not relation_info.via_model:
                continue
            if isinstance(relation_info.via_model, ForwardRef):
                __edge_to_field_mapping__.setdefault(relation_info.via_model, []).append(cast(str, relation_field))
            elif issubclass(relation_info.via_model, BaseArangoModel):
                __edge_to_field_mapping__.setdefault(relation_info.via_model.Collection.name, []).append(relation_field)
        return __edge_to_field_mapping__

    @staticmethod
    def _validate_edges(edge_to_field_mapping: EdgeFieldMapping, namespace: dict[str, Any]) -> None:
        errors: dict[Union[str, ForwardRef], list[str]] = {}
        items = edge_to_field_mapping.items()
        for coll_or_forward_ref, fields in items:
            if len(fields) > 1:
                for i, f in enumerate(fields):
                    func = getattr(namespace.get("Collection"), f)
                    if func:
                        if not callable(func):
                            raise ValueError(f"{func} is not callable")
                        fields[i] = func

                    else:
                        errors.setdefault(coll_or_forward_ref, []).append(f)
        if errors:
            raise AttributeError(f"you must define the following Collection functions for distinction {dict(errors)}")

    @staticmethod
    def _build_model(relationships: Relationships, name: str):
        __edge_namespace__: dict[str, Any] = {}
        for field, relation_info in relationships.items():
            via_model = relation_info.via_model
            if relation_info.link_type in LIST_TYPES:
                if relation_info.link_type in (LinkTypes.OPTIONAL_EDGE_LIST, LinkTypes.OPTIONAL_LIST):
                    __edge_namespace__[field] = (Optional[list[via_model]], None)  # type: ignore[valid-type]
                else:
                    __edge_namespace__[field] = (list[via_model], ...)  # type: ignore[valid-type]

            elif relation_info.link_type in (LinkTypes.OPTIONAL_EDGE, LinkTypes.OPTIONAL_DIRECT):
                __edge_namespace__[field] = (Optional[via_model], None)
            else:
                __edge_namespace__[field] = (via_model, ...)  # type: ignore[assignment]
        m = create_model(f"{name}Edges", **__edge_namespace__, __base__=EdgeData)
        return m


class VertexModel(BaseArangoModel, Generic[TEdges], metaclass=VertexMeta):
    if TYPE_CHECKING:
        edges: TEdges
        __edge_to_field_mapping__: dict[Union[str, ForwardRef], list[str]] = {}

    class Collection(VertexCollectionConfig): ...

    def __init__(self, **data: Any):
        if EDGES in data:
            convert_edge_data_to_valid_kwargs(data[EDGES])

        super().__init__(**data)

        if EDGES not in data:  # note: enables dot notation for edges field
            object.__setattr__(self, EDGES, EdgeDict())

    def dict(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = False,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        include_edges: bool = False,
    ) -> "DictStrAny":
        if include_edges and self.__exclude_fields__:
            cast(dict, self.__exclude_fields__).pop("edges")

        try:
            super__dict = super().dict(
                include=include,
                exclude=exclude,
                by_alias=by_alias,
                skip_defaults=skip_defaults,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )
        except RecursionError as e:
            raise AssertionError(
                "is not possible to call .dict() when using recursive model, instead traverse the graph and collect"
                " data or exclude recursive fields"
            ) from e

        if (
            self.__exclude_fields__ is None
            or EDGES not in self.__exclude_fields__
            and isinstance(self.edges, EdgeDict)
            and self.edges.__class__ == EdgeDict
            and not self.edges
        ):
            super__dict[EDGES] = None

        return super__dict

    def save_dict(self) -> "DictStrAny":
        return jsonable_encoder(self, by_alias=True, exclude=cast(set, self.__relationships_fields__.keys()))

    @classmethod
    def update_forward_refs(cls, **localns: Any) -> None:
        super().update_forward_refs(**localns)

        for k in cls.__edge_to_field_mapping__.copy():
            if isinstance(k, ForwardRef):
                funcs = cls.__edge_to_field_mapping__.pop(k)
                new_k = evaluate_forward_ref(cls, k, **localns)
                if new_k in cls.__edge_to_field_mapping__:
                    cls.__edge_to_field_mapping__[new_k.Collection.name].extend(funcs)
                else:
                    cls.__edge_to_field_mapping__[new_k.Collection.name] = funcs

        globalns = get_globals(cls)

        for fields, model_field in cls.__fields__[EDGES].type_.__fields__.items():
            if isinstance(model_field.type_, ForwardRef):
                model_field.type_ = evaluate_forwardref(model_field.type_, globalns, localns)

        cls.__fields__[EDGES].type_.update_forward_refs(**localns, **globalns)
