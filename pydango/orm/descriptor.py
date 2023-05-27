from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Optional, Type, TypeVar, Union

from pydantic.fields import ModelField

from pydango.connection import DALI_SESSION_KW
from pydango.orm.fields import ModelFieldExpression
from pydango.orm.proxy import LazyProxy

if TYPE_CHECKING:
    from pydango.orm.models import Relationship
    from pydango.orm.types import ArangoModel

FieldType = TypeVar("FieldType")


class DocFieldDescriptor(Generic[FieldType]):
    def __init__(self, field: ModelField, relation: Optional[Relationship] = None):
        self.relation = relation
        self.field = field

    def __set__(self, instance, value):
        raise AssertionError()
        # instance.__dict__[self.name] = LazyProxy(value)

    def __get__(
        self, instance: Optional[ArangoModel], owner: Type[FieldType]
    ) -> Union[LazyProxy, ModelFieldExpression, None]:
        if not instance and self.field.name in owner.__fields__.keys():
            return ModelFieldExpression(self.field.name, owner)

        field_value = instance.__dict__.get(self.field.name)
        if field_value is not None:
            return field_value

        if self.relation:
            return LazyProxy[instance.__class__](field_value, self.field, getattr(instance, DALI_SESSION_KW, None))

    def __set_name__(self, owner, name):
        self.name = name

    # def __repr__(self):
    #     return repr(self.field)
