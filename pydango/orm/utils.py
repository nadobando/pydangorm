from typing import TYPE_CHECKING, Generic, TypeVar, cast

from pydantic import BaseModel

from pydango.orm.fields import DocFieldDescriptor
from pydango.query.expressions import Expression, FieldExpression, IteratorExpression

if TYPE_CHECKING:
    from pydango.orm.query import ORMQuery
    from pydango.query import AQLQuery


class QueryableProjectableModelMeta(BaseModel.__class__, Expression.__class__):
    def __new__(mcs, name, bases, namespace, **kwargs):
        parents = [b for b in bases if isinstance(b, mcs)]
        if not parents:
            return cast(QueryableProjectableModelMeta, super().__new__(mcs, name, bases, namespace))

        new_cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        for field_name, field in new_cls.__fields__.items():
            # model_field = get_pydango_field(field)
            setattr(new_cls, field_name, DocFieldDescriptor(field))

        return new_cls


class PydangoSchema(BaseModel, Expression, metaclass=QueryableProjectableModelMeta):
    @classmethod
    def compile(cls, query_ref: "AQLQuery"):
        d = {}
        for name, field_info in cls.__fields__.items():
            d[name] = field_info.default_factory and field_info.default_factory() or field_info.default
        return str(d)

    def __repr__(self):
        d = {}
        for name, field_info in self.__fields__.items():
            d[name] = field_info.default_factory and field_info.default_factory() or field_info.default
        return str(d)

    @classmethod
    def to_aql(cls, iterator: IteratorExpression) -> dict:
        def create_fields_dict(fields):
            result = {}
            for name, field in fields.items():
                if issubclass(field.type_, BaseModel):
                    result[name] = create_fields_dict(field.type_.__fields__)
                else:
                    result[name] = f"{iterator}.{name}"
            return result

        result = create_fields_dict(cls.__fields__)
        return result


T = TypeVar("T")


class Aliased(Generic[T]):
    def __init__(self, entity, alias=None):
        self.entity = entity
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

    def compile(self, query_ref: "ORMQuery") -> str:
        return query_ref.orm_bound_vars[self].compile(query_ref)
