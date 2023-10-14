from abc import ABCMeta, abstractmethod
from enum import Enum, IntEnum
from functools import partial
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ForwardRef,
    Generic,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import BaseConfig, ConfigError, Field
from pydantic.fields import SHAPE_SINGLETON, ModelField, PrivateAttr, Undefined
from pydantic.main import BaseModel, ModelMetaclass
from pydantic.typing import resolve_annotations

from pydango.connection.consts import PYDANGO_SESSION_KEY
from pydango.indexes import Indexes
from pydango.orm.consts import EDGES
from pydango.orm.encoders import jsonable_encoder
from pydango.orm.models.fields import (
    ModelFieldExpression,
    RelationModelField,
    get_pydango_field,
)
from pydango.orm.models.relations import Relationship
from pydango.orm.models.sentinel import LazyFetch
from pydango.orm.models.shapes import LIST_SHAPES
from pydango.orm.utils import evaluate_forward_ref
from pydango.query.consts import ID, KEY, REV
from pydango.query.expressions import FieldExpression, ObjectExpression

if TYPE_CHECKING:
    from pydantic.main import GetterDict, Model
    from pydantic.typing import AbstractSet, DictStrAny, MappingIntStrAny

    from pydango.connection.session import PydangoSession
    from pydango.orm.models.types import RelationshipFields, Relationships
    from pydango.orm.models.vertex import TVertexModel

ArangoModel = TypeVar("ArangoModel", bound="BaseArangoModel")
FieldType = TypeVar("FieldType")
OPERATIONAL_FIELDS = {"key", "id", "rev"}


class LinkTypes(str, Enum):
    DIRECT = "DIRECT"
    OPTIONAL_DIRECT = "OPTIONAL_DIRECT"
    LIST = "LIST"
    OPTIONAL_LIST = "OPTIONAL_LIST"
    EDGE = "EDGE"
    OPTIONAL_EDGE = "OPTIONAL_EDGE"
    EDGE_LIST = "EDGE_LIST"
    OPTIONAL_EDGE_LIST = "OPTIONAL_EDGE_LIST"


EDGE_TYPES = (
    LinkTypes.EDGE,
    LinkTypes.OPTIONAL_EDGE,
    LinkTypes.OPTIONAL_EDGE_LIST,
    LinkTypes.EDGE_LIST,
)

LIST_TYPES = (
    LinkTypes.EDGE_LIST,
    LinkTypes.OPTIONAL_EDGE_LIST,
    LinkTypes.LIST,
    LinkTypes.OPTIONAL_LIST,
)

SINGLETON_TYPES = (
    LinkTypes.EDGE,
    LinkTypes.DIRECT,
    LinkTypes.OPTIONAL_EDGE,
    LinkTypes.OPTIONAL_DIRECT,
)


def get_relation(field_name: str, annotation: Any, value: Any, _: Type["BaseConfig"]) -> Optional["Relationship"]:
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


class Relation(Generic[ArangoModel]):
    def __init__(self, *args, **kwargs):
        pass


class LazyProxy(Generic[ArangoModel]):
    _initialized: bool = False
    __instance__: Union[ArangoModel, "LazyFetch"]

    def __init__(
        self, instance: Union[ArangoModel, "LazyFetch"], field, parent: ArangoModel, session: Optional["PydangoSession"]
    ):
        self.parent = parent
        self.session = session
        self._relation_field = field
        if not isinstance(instance, LazyFetch):
            self._initialized = True

        self.__instance__ = instance

    def __getattr__(self, item):
        if item in getattr(self, "__dict__"):
            return getattr(self, item)

        if isinstance(self.__instance__, list):
            if item in ["dict"]:
                return partial(jsonable_encoder, obj=self.__instance__)

        attr = getattr(self.__instance__, item, None)
        if attr:
            return attr
        else:
            return getattr(self._relation_field.type_, item)

    def __repr__(self):
        return repr(self.__instance__)

    def __getitem__(self, item):
        if self:
            return self.__instance__[item]
        raise AttributeError(
            f"you are attempting to access {self._relation_field.field.type_.__name__} via"
            f" {self._relation_field.field.name} which is not initialized yet, use fetch"
        )

    def __bool__(self):
        return self._initialized and bool(self.__instance__)

    async def fetch(
        self,
    ):
        if not self.session:
            raise "Kusomo"

        model = await self.session.get(
            self.parent.__class__,
            # self._relation_field.field.type_,
            self.parent.key,
            fetch_edges={self._relation_field.via_model.Collection.name},
            depth=range(1, 1),
        )
        model = getattr(model, self._relation_field.field.name)
        setattr(self.parent, self._relation_field.field.name, model)
        self.__instance__ = model
        self._initialized = True
        return model

    def compile(self, query_ref):
        return ObjectExpression(self.dict()).compile(query_ref)

    def dict(self, *args, by_alias=True, **kwargs):
        return jsonable_encoder(self.__instance__, by_alias=by_alias, *args, **kwargs)


class DocFieldDescriptor(Generic[FieldType]):
    def __init__(self, field: ModelField, relation: Optional[Relationship] = None):
        self.relation = relation
        self.field = field
        self._proxy: Optional[LazyProxy] = None

    def __set__(self, instance, value: FieldType):
        raise AssertionError()
        # instance.__dict__[self.name] = LazyProxy(value)

    def __get__(
        self, instance: Optional[ArangoModel], owner: Type["TVertexModel"]
    ) -> Union[LazyProxy[ArangoModel], ModelFieldExpression, FieldType, None]:
        if not instance and self.field.name in owner.__fields__.keys():
            return ModelFieldExpression(self.field.name, owner)
        if instance:
            field_value = instance.__dict__.get(self.field.name)
            if self.field.name in instance.__fields_set__:
                return field_value

            if self._proxy:
                return self._proxy

            if self.relation:
                session = getattr(instance, PYDANGO_SESSION_KEY, None)
                self._proxy = LazyProxy(field_value, self.relation, instance, session)
                return self._proxy  # type: ignore[valid-type]
        if not instance:
            raise ValueError("something happened open an issue :(")
        return None

    def __set_name__(self, owner, name):
        self.name = name


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
    def get_relations_from_namespace(namespace: dict[str, Any]) -> tuple["Relationships", dict[str, Any]]:
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


class CollectionType(IntEnum):
    NODE = 2
    EDGE = 3


class CollectionConfig:
    name: str
    type: CollectionType
    sync: Optional[bool] = False
    system: Optional[bool] = False
    key_generator: Literal["traditional", "autoincrement"] = "traditional"
    user_keys: Optional[bool] = False
    key_increment: Optional[int]
    key_offset: Optional[int]
    shard_fields: Optional[list[str]]
    shard_count: Optional[int]
    replication_factor: Optional[int]
    shard_like: Optional[str]  # enterprise only
    sync_replication: Optional[bool]
    enforce_replication_factor: Optional[bool]
    sharding_strategy: Literal["community-compat", "enterprise-smart-edge-compat", "enterprise-smart-edge"]
    smart_join_attribute: Optional[str]  # enterprise only
    write_concern: Optional[int]

    sync_schema: Optional[bool] = False
    indexes: Sequence[Indexes] = []


class BaseArangoModel(BaseModel, metaclass=ArangoModelMeta):
    id: Optional[str] = Field(None, alias=ID)
    key: Optional[str] = Field(None, alias=KEY)
    rev: Optional[str] = Field(None, alias=REV)

    __session__: Optional["PydangoSession"] = PrivateAttr()

    if TYPE_CHECKING:
        __relationships__: Relationships = {}
        __relationships_fields__: RelationshipFields = {}

    class Config(BaseConfig):
        arbitrary_types_allowed = True
        orm_mode = True
        # getter_dict = dict
        allow_population_by_field_name = True

    class Collection(CollectionConfig): ...

    def __init__(self, **data: Any):
        super().__init__(**data)
        object.__setattr__(self, PYDANGO_SESSION_KEY, data.get(PYDANGO_SESSION_KEY))

    @classmethod
    def _decompose_class(cls: Type["Model"], obj: Any) -> Union["GetterDict", dict]:  # type: ignore[override]
        if isinstance(obj, dict):
            return obj
        decompose_class = super()._decompose_class(obj)
        return decompose_class

    def _calculate_keys(
        self,
        include: Optional["MappingIntStrAny"],
        exclude: Optional["MappingIntStrAny"],
        exclude_unset: bool,
        update: Optional["DictStrAny"] = None,
    ) -> Optional["AbstractSet[str]"]:
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
        obj[PYDANGO_SESSION_KEY] = session
        for field_name, field in cls.__relationships_fields__.items():
            exists_in_orm = field_name in obj and obj.get(field_name, None)
            if exists_in_orm:
                if isinstance(exists_in_orm, list):
                    for i, v in enumerate(exists_in_orm):
                        exists_in_orm[i][PYDANGO_SESSION_KEY] = session
                else:
                    exists_in_orm[PYDANGO_SESSION_KEY] = session

                obj[field_name] = exists_in_orm

                continue
            if field.required:
                obj[field_name] = LazyFetch(session, obj["_id"])
            else:
                print("field not set", field_name)

        try:
            obj = cast(Type[ArangoModel], super()).from_orm(obj)
        except ConfigError as e:
            raise e

        # for field_name, field in cls.__relationships_fields__.items():
        #     setattr( getattr(obj,field_name),'__dali_session__',session)
        # object_setattr(obj, DALI_SESSION_KW, session)
        return obj

    # @classmethod
    # def validate(cls: Type['Model'], value: Any) -> 'Model':
    #     return cls.from_orm(value)

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
    def save_dict(self) -> "DictStrAny": ...


class Aliased(Generic[ArangoModel]):
    def __init__(self, entity: ArangoModel, alias=None):
        self.entity: ArangoModel = entity
        self.alias = alias

    def __getattr__(self, item):
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
