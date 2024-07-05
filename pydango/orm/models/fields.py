from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union, cast

from pydantic.v1.fields import ModelField

from pydango.orm.models.sentinel import LazyFetch
from pydango.query.expressions import (
    Expression,
    FieldExpression,
    IteratorExpression,
    VariableExpression,
)

if TYPE_CHECKING:
    from pydantic.v1.fields import LocStr, ModelOrDc, ValidateReturn

    from pydango.orm.models.vertex import TVertexModel
    from pydango.query.expressions import QueryExpression


class ModelFieldExpression(FieldExpression):
    def __init__(self, field: Union[str, Expression], parent: Type["TVertexModel"]):
        super().__init__(field, cast(VariableExpression, parent))
        self.parent = parent  # type: ignore[assignment]

    def compile(self, query_ref: "QueryExpression") -> str:
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


class RelationModelField(ModelField):
    def validate(
        self,
        v: Any,
        values: Dict[str, Any],
        *,
        loc: "LocStr",
        cls: Optional["ModelOrDc"] = None,
    ) -> "ValidateReturn":
        return super().validate(v, values, loc=loc, cls=cls) if not isinstance(v, LazyFetch) else (v, None)


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
