from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic.fields import ModelField

from pydango.query.expressions import (
    BinaryLogicalExpression,
    ConditionExpression,
    Expression,
    FieldExpression,
    IteratorExpression,
    LiteralExpression,
    SortExpression,
)
from pydango.query.utils import SortDirection

if TYPE_CHECKING:
    from pydango.orm.query import ORMQuery


# class LateBindVariable(Expression):
#     def __init__(self, model, field):
#         self.field = field
#         self.model = model
#         self.value = None
#
#     def bind(self, value):
#         self.value = value
#
#     def __str__(self):
#         if self.value is None:
#             raise ValueError("Value for LateBindParam has not been bound.")
#         return str(self.value)


@dataclass
class Sort:
    model: Any = None
    field: ModelField = None
    direction: str = None


class ExpressionField:
    def __init__(self, model, field: ModelField):
        self.__model__ = model
        self.field = field

    def __getattr__(self, item):
        return getattr(self.field.type_, item)

    def __repr__(self):
        return f"<ExpressionField: {self.field.name} -> {self.field.annotation}>"

    @staticmethod
    def __get_other__(other):
        if isinstance(other, ExpressionField):
            other = FieldExpression(other.field.name, other.__model__)
        if isinstance(other, Expression):
            return other
        else:
            other = LiteralExpression(other)
        return other

    def __eq__(self, other):
        other = self.__get_other__(other)
        return ConditionExpression("==", FieldExpression(self.field.name, self.__model__), other)

    def __gt__(self, other):
        other = self.__get_other__(other)
        return ConditionExpression(">", FieldExpression(self.field.name, self.__model__), other)

    def __lt__(self, other):
        other = self.__get_other__(other)
        return ConditionExpression(">", FieldExpression(self.field.name, self.__model__), other)

    def __neg__(self):
        return SortExpression(FieldExpression(self.field.name, self.__model__), SortDirection.DESC)

    def __pos__(self):
        return SortExpression(FieldExpression(self.field.name, self.__model__), SortDirection.ASC)

    def __and__(self, other):
        other = self.__get_other__(other)
        return BinaryLogicalExpression("&&", FieldExpression(self.field.name, self.__model__), other)


class ModelFieldExpression(FieldExpression):
    def compile(self, query_ref: "ORMQuery") -> str:
        if isinstance(self.field, Expression):
            return f"{self.parent.compile(query_ref)}[{self.field.compile(query_ref)}]"
        else:
            if not isinstance(self.parent, IteratorExpression):
                compiled = query_ref.orm_bound_vars[self.parent]
                return f"{compiled.compile(query_ref)}.{self.field}"
            return super().compile(query_ref)

    # def __str__(self):
    #     return self.field

    def __hash__(self):
        return hash(self.field)
