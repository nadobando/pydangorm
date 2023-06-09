from __future__ import annotations

import sys
from abc import ABC
from enum import Enum
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Annotated,
    Any,
    Dict,
    ForwardRef,
    Generic,
    Mapping,
    Optional,
    Type,
    Union,
    cast,
    get_args,
    get_origin,
)

import pydantic.typing

from pydango.orm.consts import EDGES
from pydango.orm.types import ArangoModel, TEdge
from pydango.orm.utils import convert_edge_data_to_valid_kwargs, get_globals
from pydango.query.consts import FROM, ID, KEY, REV, TO

if sys.version_info >= (3, 10):
    from typing import TypeAlias, dataclass_transform
else:
    from typing_extensions import TypeAlias, dataclass_transform

from pydantic import BaseConfig, BaseModel
from pydantic.fields import (
    SHAPE_FROZENSET,
    SHAPE_ITERABLE,
    SHAPE_LIST,
    SHAPE_SEQUENCE,
    SHAPE_SET,
    SHAPE_SINGLETON,
    SHAPE_TUPLE_ELLIPSIS,
    Field,
    ModelField,
    PrivateAttr,
    Undefined,
)
from pydantic.main import (  # noqa: ignore
    ModelMetaclass,
    create_model,
    object_setattr,
    validate_model,
)
from pydantic.typing import resolve_annotations
from pydantic.utils import GetterDict

from pydango import NAO
from pydango.index import Index
from pydango.orm.fields import DocFieldDescriptor
from pydango.orm.relations import LIST_TYPES, LinkTypes

if TYPE_CHECKING:
    from pydantic.fields import LocStr, ValidateReturn
    from pydantic.main import Model
    from pydantic.types import ModelOrDc
    from pydantic.typing import DictStrAny, MappingIntStrAny, ReprArgs

    from pydango.connection.session import PydangoSession

LIST_SHAPES = {
    SHAPE_LIST,
    SHAPE_TUPLE_ELLIPSIS,
    SHAPE_SEQUENCE,
    SHAPE_SET,
    SHAPE_FROZENSET,
    SHAPE_ITERABLE,
}


class RelationMetaclass(type):
    def __new__(mcs, name, bases, namespace, **kwargs):
        parents = [b for b in bases if isinstance(b, mcs)]
        if not parents:
            return super().__new__(mcs, name, bases, namespace)

        model = namespace["__orig_bases__"][0].__args__[0]

        if model is ArangoModel:
            return super().__new__(mcs, name, bases, namespace)

        return super().__new__(mcs, name, bases, {"model": model, **namespace})


class Relation(Generic[ArangoModel]):
    def __init__(self, *args, **kwargs):
        pass


class EdgeRelation(Relation[ArangoModel]):
    pass


class Relationship:
    def __init__(
        self,
        *,
        field: ModelField,
        back_populates: Optional[str] = None,
        link_model: Type[VertexModel],
        via_model: Optional[Type[TEdge]] = None,
        link_type: LinkTypes,
    ):
        self.via_model = via_model
        self.link_type = link_type
        self.field = field
        self.link_model = link_model
        self.back_populates = back_populates

    def __repr_args__(self) -> ReprArgs:
        name = self.link_model.__name__ if not isinstance(self.link_model, ForwardRef) else self.link_model
        args = [("link_model", name), ("link_type", self.link_type.value)]
        if self.via_model:
            args.append(("via_model", self.via_model.__name__))
        return args


def get_relation(field_name: str, annotation: Any, value: Any, config: Type[BaseConfig]) -> Optional[Relationship]:
    if get_origin(annotation) is not Annotated:
        return None

    args = get_args(annotation)
    relation_infos = [arg for arg in args[1:] if arg is Relation or get_origin(arg) is Relation]
    if len(relation_infos) > 1:
        raise ValueError(f"cannot specify multiple `Annotated` `Field`s for {field_name!r}")
    relation_info = next(iter(relation_infos), None)
    via_model = get_args(relation_info)[0] if relation_info else None
    field = ModelField.infer(
        name=field_name,
        value=value,
        annotation=annotation,
        class_validators=None,
        config=BaseConfig,
    )
    if field.shape in LIST_SHAPES:
        if field.sub_fields:
            link_model = field.sub_fields[0].type_

        if field.allow_none is True:
            link_type = via_model and LinkTypes.OPTIONAL_EDGE_LIST or LinkTypes.OPTIONAL_LIST
        else:
            link_type = via_model and LinkTypes.EDGE_LIST or LinkTypes.LIST

    elif field.shape == SHAPE_SINGLETON:
        link_model = field.type_
        if field.allow_none is True:
            link_type = via_model and LinkTypes.OPTIONAL_EDGE or LinkTypes.OPTIONAL_DIRECT
        else:
            link_type = via_model and LinkTypes.EDGE or LinkTypes.DIRECT
    else:
        raise AssertionError()

    return Relationship(
        field=field,
        link_model=link_model,
        link_type=link_type,
        via_model=via_model,
    )


class CollectionType(int, Enum):
    NODE = 2
    EDGE = 3


class CollectionConfig:
    name: str
    type: CollectionType
    wait_for_sync: Optional[bool] = False
    sync_json_schema: Optional[bool] = True
    indexes: Optional[list[Union[Index, dict]]] = []


OPERATIONAL_FIELDS = {"key", "id", "rev"}


# todo: check if this is in use
# class PydangoModelField(ModelField, Compilable):
#     pass


class RelationModelField(ModelField):
    def validate(
        self,
        v: Any,
        values: Dict[str, Any],
        *,
        loc: LocStr,
        cls: Optional[ModelOrDc] = None,
    ) -> ValidateReturn:
        return super().validate(v, values, loc=loc, cls=cls) if v is not NAO else (v, None)


def get_pydango_field(field, cls=RelationModelField):
    return cls(
        name=field.name,
        type_=field.annotation,
        alias=field.alias,
        class_validators=field.class_validators,
        default=field.default,
        default_factory=field.default_factory,
        required=field.required,
        model_config=field.model_config,
        final=field.final,
        field_info=field.field_info,
    )


# noinspection PyPep8Naming
def ArangoField(model_field, relation) -> DocFieldDescriptor:
    return DocFieldDescriptor(model_field, relation)


def edge_data_validator(*args, **kwargs):
    print(args, kwargs)
    return args, kwargs


class EdgeData(BaseModel):
    pass


@dataclass_transform(kw_only_default=True, field_specifiers=(ArangoField,))
class ArangoModelMeta(ModelMetaclass):
    def __new__(mcs, name, bases, namespace, **kwargs):
        parents = [b for b in bases if isinstance(b, mcs)]
        if not parents or BaseArangoModel in parents:
            new_cls = super().__new__(mcs, name, bases, namespace, **kwargs)
            new_cls.__relationships__ = {}
            new_cls.__relationships_fields__ = {}
            return new_cls
        relationships = {}

        original_annotations = resolve_annotations(
            namespace.get("__annotations__", {}), namespace.get("__module__", None)
        )

        for k, v in original_annotations.items():
            relation = get_relation(k, v, namespace.get(k, Undefined), BaseConfig)
            if relation:
                relationships[k] = relation
                original_annotations[k] = Union[original_annotations[k]]

        if VertexModel in bases:
            __edge_namespace__ = {}
            for field, relation_info in relationships.items():
                if relation_info.link_type in LIST_TYPES:
                    __edge_namespace__[field] = (list[relation_info.via_model], ...)
                else:
                    __edge_namespace__[field] = (relation_info.via_model, ...)

            m = create_model(f"{name}Edges", **__edge_namespace__, __base__=EdgeData)
            namespace[EDGES] = Field(None, exclude=True)

            original_annotations[EDGES] = Optional[m]

        dict_used = {
            **namespace,
            "__weakref__": None,
            "__annotations__": original_annotations,
            "__relationships__": relationships,
        }

        new_cls = super().__new__(
            mcs,
            name,
            bases,
            dict_used,
            **kwargs,
        )
        relationship_fields = {}

        for field_name, field in [(k, v) for k, v in new_cls.__fields__.items() if k != EDGES]:
            if field_name in relationships:
                model_field = get_pydango_field(field, RelationModelField)
                # todo improve this
                relationships[field_name].field = model_field
                relationship_fields[field_name] = model_field
                new_cls.__fields__[field_name] = model_field

                setattr(
                    new_cls,
                    field_name,
                    DocFieldDescriptor[model_field.type_](model_field, relationships[field_name]),
                )
                new_cls.__annotations__.update({field_name: DocFieldDescriptor[model_field.type_]})
                # if issubclass(new_cls, VertexModel):
                #     pass
            else:
                setattr(new_cls, field_name, DocFieldDescriptor[field.type_](field))

        new_cls.__relationships__ = relationships

        new_cls.__relationships_fields__ = relationship_fields
        new_cls.__annotations__ = {
            # **relationship_annotations,
            **original_annotations,
            **new_cls.__annotations__,
        }

        return new_cls

    # def __hash__(self):
    #     return hash(self.Collection.name)


RelationshipFields: TypeAlias = dict[str, RelationModelField]
Relationships: TypeAlias = dict[str, Relationship]


class BaseArangoModel(BaseModel, ABC, metaclass=ArangoModelMeta):
    id: Optional[str] = Field(None, alias=ID)
    key: Optional[str] = Field(None, alias=KEY)
    rev: Optional[str] = Field(None, alias=REV)

    __dali__session__: Optional[PydangoSession] = PrivateAttr()

    if TYPE_CHECKING:
        __relationships__: Relationships = {}
        __relationships_fields__: RelationshipFields = {}

    class Config(BaseConfig):
        arbitrary_types_allowed = True
        orm_mode = True
        # getter_dict = dict
        allow_population_by_field_name = True

    class Collection(CollectionConfig):
        ...

    @classmethod
    def _decompose_class(cls: Type[Model], obj: Any) -> Union[GetterDict, dict]:  # type: ignore[override]
        if isinstance(obj, dict):
            return obj
        decompose_class = super()._decompose_class(obj)
        return decompose_class

    def _calculate_keys(
        self,
        include: Optional[MappingIntStrAny],
        exclude: Optional[MappingIntStrAny],
        exclude_unset: bool,
        update: Optional[DictStrAny] = None,
    ) -> Optional[AbstractSet[str]]:
        field_set = self.__fields_set__.copy()
        keys = self.__dict__.keys()
        unset = keys - field_set
        if not exclude_unset:
            _exclude = cast(Mapping, {field: True for field in unset if field in OPERATIONAL_FIELDS})
            if not exclude:
                exclude = _exclude
            else:
                exclude.update(_exclude)  # type: ignore[attr-defined]

        return super()._calculate_keys(include, exclude, exclude_unset, update)

    @classmethod
    def from_orm(cls: Type[ArangoModel], obj: Any, *, session=None) -> ArangoModel:  # type: ignore[misc]
        for field_name, field in cls.__relationships_fields__.items():
            exists_in_orm = obj.get(field_name, None)
            if exists_in_orm:
                obj[field_name] = exists_in_orm
                continue
            if field.required:
                obj[field_name] = NAO

        obj = super().from_orm(obj)
        obj.__dali__session__ = session
        # object_setattr(obj, DALI_SESSION_KW, session)
        return obj

    @classmethod
    def update_forward_refs(cls, **localns: Any) -> None:
        super().update_forward_refs(**localns)
        for name in cls.__relationships_fields__.keys():
            cls.__relationships_fields__[name] = cast(RelationModelField, cls.__fields__[name])
            relation = cls.__relationships__[name]
            relation.field = cls.__fields__[name]
            relation.link_model = cls.__fields__[name].type_
            if isinstance(relation.via_model, ForwardRef):
                relation.via_model = pydantic.typing.evaluate_forwardref(relation.via_model, get_globals(cls), localns)


class VertexCollectionConfig(CollectionConfig):
    type = CollectionType.NODE


class EdgeCollectionConfig(CollectionConfig):
    type = CollectionType.EDGE


class EdgeModel(BaseArangoModel, ABC):
    from_: Optional[Union[str, VertexModel]] = Field(None, alias=FROM)
    to: Optional[Union[str, VertexModel]] = Field(None, alias=TO)

    class Collection(EdgeCollectionConfig):
        pass

    def save_dict(self) -> DictStrAny:
        exclude = set()
        for key in ["from_", "to"]:
            if self.__getattribute__(key) is None:
                exclude.add(key)

        return self.dict(by_alias=True, exclude=exclude)


# EdgeModel.update_forward_refs()
# VertexModel.update_forward_refs()


class VertexModel(BaseArangoModel, ABC):
    if TYPE_CHECKING:
        edges: Union[dict, EdgeData, None] = None

    class Collection(VertexCollectionConfig):
        ...

    def __init__(self, **data: Any):
        if EDGES in data:
            convert_edge_data_to_valid_kwargs(data[EDGES])
        super().__init__(**data)

    def save_dict(self) -> DictStrAny:
        return self.dict(by_alias=True, exclude=self.__relationships_fields__.keys())

    @classmethod
    def update_forward_refs(cls, **localns: Any) -> None:
        super().update_forward_refs(**localns)
        globalns = get_globals(cls)

        for fields, model_field in cls.__fields__[EDGES].type_.__fields__.items():
            if isinstance(model_field.type_, ForwardRef):
                model_field.type_ = pydantic.typing.evaluate_forwardref(model_field.type_, globalns, localns)

        cls.__fields__[EDGES].type_.update_forward_refs(**localns, **globalns)
