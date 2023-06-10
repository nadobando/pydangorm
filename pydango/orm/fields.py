from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Optional, Type, TypeVar, Union, cast

from pydantic.fields import ModelField

from pydango.connection import DALI_SESSION_KW
from pydango.orm.proxy import LazyProxy
from pydango.query.expressions import (
    Expression,
    FieldExpression,
    IteratorExpression,
    VariableExpression,
)

if TYPE_CHECKING:
    from pydango.orm.models import BaseArangoModel, Relationship
    from pydango.orm.types import ArangoModel
    from pydango.query import AQLQuery

FieldType = TypeVar("FieldType")


class ModelFieldExpression(FieldExpression):
    def compile(self, query_ref: AQLQuery) -> str:
        if isinstance(self.field, Expression):
            return super().compile(query_ref)
        else:
            if not isinstance(self.parent, IteratorExpression):
                # currently there is importing ORMQuery creates a circular dependency
                compiled = query_ref.orm_bound_vars[self.parent]  # type: ignore[attr-defined]
                return f"{compiled.compile(query_ref)}.{self.field}"
            return super().compile(query_ref)

    def __hash__(self):
        return hash(self.field)


class DocFieldDescriptor(Generic[FieldType]):
    def __init__(self, field: ModelField, relation: Optional[Relationship] = None):
        self.relation = relation
        self.field = field

    def __set__(self, instance, value):
        raise AssertionError()
        # instance.__dict__[self.name] = LazyProxy(value)

    def __get__(
        self, instance: Optional[ArangoModel], owner: Type[BaseArangoModel]
    ) -> Union[LazyProxy, ModelFieldExpression, None]:
        if not instance and self.field.name in owner.__fields__.keys():
            return ModelFieldExpression(self.field.name, cast(VariableExpression, owner))

        field_value = instance.__dict__.get(self.field.name)
        if field_value is not None:
            return field_value

        if self.relation:
            return LazyProxy[owner](  # type: ignore[valid-type]
                field_value, self.field, getattr(instance, DALI_SESSION_KW, None)  # type: ignore[arg-type]
            )
        return None

    def __set_name__(self, owner, name):
        self.name = name
