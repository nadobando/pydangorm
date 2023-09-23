from __future__ import annotations

import logging
import sys
from abc import ABC, ABCMeta, abstractmethod
from enum import Enum
from functools import partial
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
    Sequence,
    Type,
    Union,
    cast,
    get_args,
    get_origin,
)

import pydantic.typing
from pydantic.fields import ConfigError  # type: ignore[attr-defined]
from pydantic.generics import GenericModel

from pydango.connection import DALI_SESSION_KW
from pydango.orm.consts import EDGES
from pydango.orm.encoders import jsonable_encoder
from pydango.orm.utils import evaluate_forward_ref, get_globals
from pydango.query.consts import FROM, ID, KEY, REV, TO
from pydango.query.expressions import (
    Expression,
    FieldExpression,
    IteratorExpression,
    ObjectExpression,
    VariableExpression,
)

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

from typing import TypeVar

from pydantic import BaseConfig
from pydantic.fields import (  # type: ignore[attr-defined]
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
from pydantic.main import BaseModel, ModelMetaclass, create_model
from pydantic.typing import resolve_annotations
from pydantic.utils import GetterDict

from pydango import NAO, NotAnObject
from pydango.index import Indexes
from pydango.orm.relations import LIST_TYPES, LinkTypes

ArangoModel = TypeVar("ArangoModel", bound="BaseArangoModel")

TVertexModel = TypeVar("TVertexModel", bound="VertexModel")

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pydantic.fields import LocStr, ValidateReturn  # type: ignore[attr-defined]
    from pydantic.main import Model
    from pydantic.types import ModelOrDc
    from pydantic.typing import (
        AbstractSetIntStr,
        DictStrAny,
        MappingIntStrAny,
        ReprArgs,
    )

    from pydango.connection.session import PydangoSession
    from pydango.query import AQLQuery
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
        via_model: Optional[Type[EdgeModel]] = None,
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
    indexes: Sequence[Indexes] = []


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


def get_pydango_field(field: ModelField, cls: Type[RelationModelField] = RelationModelField) -> RelationModelField:
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
    # print(args, kwargs)
    return args, kwargs


class VertexCollectionConfig(CollectionConfig):
    type = CollectionType.NODE


class EdgeCollectionConfig(CollectionConfig):
    type = CollectionType.EDGE


# @dataclass_transform(kw_only_default=True, field_specifiers=(ArangoField,))
class ArangoModelMeta(ModelMetaclass, ABCMeta):
    def __new__(mcs, name: str, bases: tuple[Type], namespace: dict, **kwargs: Any):
        parents = [b for b in bases if isinstance(b, mcs)]
        if not parents or BaseArangoModel in parents:
            skipped_cls: BaseArangoModel = super().__new__(mcs, name, bases, namespace, **kwargs)
            skipped_cls.__relationships__ = {}
            skipped_cls.__relationships_fields__ = {}
            return skipped_cls

        _relationships, original_annotations = ArangoModelMeta.get_relations_from_namespace(namespace)

        dict_used = {
            **namespace,
            "__weakref__": None,
            "__annotations__": original_annotations,
            "__relationships__": _relationships,
        }

        new_cls: BaseArangoModel = super().__new__(mcs, name, bases, dict_used, **kwargs)

        __relationship_fields__ = ArangoModelMeta.set_field_descriptors(_relationships, new_cls)

        new_cls.__relationships__ = _relationships
        new_cls.__relationships_fields__ = __relationship_fields__
        new_cls.__annotations__ = {
            # **relationship_annotations,
            **original_annotations,
            **new_cls.__annotations__,
        }

        return new_cls

    @staticmethod
    def get_relations_from_namespace(namespace: dict[str, Any]) -> tuple[Relationships, dict[str, Any]]:
        _relationships: dict[str, Relationship] = {}
        original_annotations = resolve_annotations(
            namespace.get("__annotations__", {}), namespace.get("__module__", None)
        )
        for k, v in original_annotations.items():
            relation = get_relation(k, v, namespace.get(k, Undefined), BaseConfig)
            if relation:
                _relationships[k] = relation
                # original_annotations[k] = Union[original_annotations[k]]
        return _relationships, original_annotations

    @staticmethod
    def set_field_descriptors(_relationships, new_cls):
        __relationship_fields__ = {}
        for field_name, model_field in [(x, y) for x, y in new_cls.__fields__.items() if x != EDGES]:
            if field_name in _relationships:
                pydango_field = get_pydango_field(model_field, RelationModelField)
                relationship = _relationships[field_name]
                relationship.field = pydango_field
                __relationship_fields__[field_name] = pydango_field
                new_cls.__fields__[field_name] = pydango_field

                type_ = cast(ModelField, pydango_field).type_
                setattr(
                    new_cls,
                    field_name,
                    DocFieldDescriptor[type_](pydango_field, relationship),  # type: ignore[valid-type]
                )

                field_annotation = {field_name: DocFieldDescriptor[type_]}  # type: ignore[valid-type]
                new_cls.__annotations__.update(field_annotation)
            else:
                setattr(
                    new_cls,
                    field_name,
                    DocFieldDescriptor[model_field.type_](model_field),  # type: ignore[name-defined]
                )
        return __relationship_fields__

    # def __hash__(self):
    #     return hash(self.Collection.name)


RelationshipFields: TypeAlias = dict[str, RelationModelField]
Relationships: TypeAlias = dict[str, Relationship]
EdgeFieldMapping: TypeAlias = dict[Union[str, ForwardRef], list[str]]


class BaseArangoModel(BaseModel, metaclass=ArangoModelMeta):
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
    def from_orm(cls: Type[ArangoModel], obj: Any, *, session=None) -> ArangoModel:
        for field_name, field in cls.__relationships_fields__.items():
            exists_in_orm = obj.get(field_name, None)
            if exists_in_orm:
                obj[field_name] = exists_in_orm
                continue
            if field.required:
                obj[field_name] = NAO
        try:
            obj = cast(Type[ArangoModel], super()).from_orm(obj)
        except ConfigError as e:
            raise e
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
                relation.via_model = evaluate_forward_ref(cls, relation.via_model, **localns)

            if isinstance(relation.link_model, ForwardRef):
                relation.link_model = evaluate_forward_ref(cls, relation.link_model, **localns)

        # for k in cls.__edge_to_field_mapping__.copy():
        #     if isinstance(k, ForwardRef):
        #         funcs = cls.__edge_to_field_mapping__.pop(k)
        #         new_k = evaluate_forward_ref(cls, k, **localns)
        #         if new_k in cls.__edge_to_field_mapping__:
        #             cls.__edge_to_field_mapping__[new_k.Collection.name].extend(funcs)
        #         else:
        #             cls.__edge_to_field_mapping__[new_k.Collection.name] = funcs

    @abstractmethod
    def save_dict(self) -> DictStrAny:
        ...


class EdgeModel(BaseArangoModel, ABC):
    from_: Optional[Union[str]] = Field(None, alias=FROM)
    to: Optional[Union[str]] = Field(None, alias=TO)

    class Collection(EdgeCollectionConfig):
        pass

    def save_dict(self) -> DictStrAny:
        exclude: set[Union[int, str]] = set()
        for key in ["from_", "to"]:
            if self.__getattribute__(key) is None:
                exclude.add(key)
        return jsonable_encoder(self, by_alias=True, exclude=exclude)
        # return self.dict(by_alias=True, exclude=exclude)


def save_dict(model: BaseArangoModel):
    return model.save_dict()


class LazyProxy(Generic[ArangoModel]):
    _initialized: bool = False
    __instance__: Union[ArangoModel, NotAnObject]

    def __init__(self, instance: Union[ArangoModel, NotAnObject], field, session: Optional[PydangoSession]):
        self.session = session
        self._field = field
        if instance is not NAO:
            self._initialized = True

        self.__instance__ = instance

    def __getattr__(self, item):
        if item in getattr(self, "__dict__"):
            return getattr(self, item)

        if isinstance(self.__instance__, list):
            if item in ["dict"]:
                return partial(jsonable_encoder, obj=self.__instance__)

            # if item in getattr(getattr(self, '_instance'), item):
        attr = getattr(self.__instance__, item, None)
        if attr:
            return attr
        else:
            return getattr(self._field.type_, item)

    def __repr__(self):
        return repr(self.__instance__)

    def __getitem__(self, item):
        if self:
            return self.__instance__[item]
        raise AttributeError(
            "you are attempting to access "
            f"{self._field.type_.__name__} via {self._field.name} which is not initialized use fetch"
        )

    def __bool__(self):
        return self._initialized and bool(self.__instance__)

    def fetch(self):
        self.session.get(
            self._field.type_,
        )

    def compile(self, query_ref):
        return ObjectExpression(self.dict()).compile(query_ref)

    def dict(self, *args, by_alias=True, **kwargs):
        return jsonable_encoder(self.__instance__, by_alias=by_alias, *args, **kwargs)


class ModelFieldExpression(FieldExpression):
    def __init__(self, field: Union[str, Expression], parent: Type[BaseArangoModel]):
        super().__init__(field, cast(VariableExpression, parent))
        self.parent = parent  # type: ignore[assignment]

    def compile(self, query_ref: AQLQuery) -> str:
        if isinstance(self.field, Expression):
            return super().compile(query_ref)
        else:
            if not isinstance(self.parent, IteratorExpression):
                # currently importing ORMQuery creates a circular dependency
                compiled = query_ref.orm_bound_vars[self.parent]  # type: ignore[attr-defined]
                return f"{compiled.compile(query_ref)}.{self.field}"
            return super().compile(query_ref)

    def __hash__(self):
        return hash(self.field)


FieldType = TypeVar("FieldType")


class DocFieldDescriptor(Generic[FieldType]):
    def __init__(self, field: ModelField, relation: Optional[Relationship] = None):
        self.relation = relation
        self.field = field

    def __set__(self, instance, value: FieldType):
        raise AssertionError()
        # instance.__dict__[self.name] = LazyProxy(value)

    def __get__(
        self, instance: Optional[ArangoModel], owner: Type[BaseArangoModel]
    ) -> Union[LazyProxy[ArangoModel], ModelFieldExpression, None]:
        if not instance and self.field.name in owner.__fields__.keys():
            return ModelFieldExpression(self.field.name, owner)

        field_value = instance.__dict__.get(self.field.name)
        if field_value is not None:
            return field_value

        if self.relation:
            return LazyProxy[owner](  # type: ignore[valid-type]
                field_value, self.field, getattr(instance, DALI_SESSION_KW, None)
            )
        return None

    def __set_name__(self, owner, name):
        self.name = name


class Aliased(Generic[ArangoModel]):
    def __init__(self, entity: ArangoModel, alias=None):
        self.entity: ArangoModel = entity
        self.alias = alias

    def __getattr__(self, item):
        # if item == "Collection":
        #     Temp = namedtuple("Temp", ["name"])
        #     return Temp(name=self.entity.Collection.name)
        #
        # if item == "var_name":
        #     return self.alias

        attr = getattr(self.entity, item)
        if isinstance(attr, FieldExpression):
            attr.parent = self

        return attr

    def __str__(self):
        return str(self.alias or "")

    def __repr__(self):
        return f"<Aliased: {self.entity.__name__}, {id(self)}>"

    # def compile(self, query_ref: "ORMQuery") -> str:
    #     return query_ref.orm_bound_vars[self].compile(query_ref)


def convert_edge_data_to_valid_kwargs(edge_dict):
    for i in edge_dict.copy():
        if isinstance(i, ModelFieldExpression):
            edge_dict[i.field] = edge_dict.pop(i)


TEdge = TypeVar("TEdge", bound="EdgeModel")


class EdgeData(GenericModel, Generic[TEdge]):
    pass


TEdges = TypeVar("TEdges", bound=EdgeData)


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

    class Collection(VertexCollectionConfig):
        ...

    def __init__(self, **data: Any):
        if EDGES in data:
            convert_edge_data_to_valid_kwargs(data[EDGES])
        super().__init__(**data)

    def dict(
        self,
        *,
        include: Optional[Union[AbstractSetIntStr, MappingIntStrAny]] = None,
        exclude: Optional[Union[AbstractSetIntStr, MappingIntStrAny]] = None,
        by_alias: bool = False,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        include_edges: bool = False,
    ) -> DictStrAny:
        d = cast(dict, self.__exclude_fields__)
        if include_edges and self.__exclude_fields__:
            d.pop("edges")

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
        if self.__exclude_fields__:
            d["edges"] = True

        return super__dict

    def save_dict(self) -> DictStrAny:
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
                model_field.type_ = pydantic.typing.evaluate_forwardref(model_field.type_, globalns, localns)

        cls.__fields__[EDGES].type_.update_forward_refs(**localns, **globalns)
