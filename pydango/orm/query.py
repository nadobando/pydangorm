from typing import Optional, Type, Union, overload

from pydantic import BaseModel

from pydango.orm.proxy import LazyProxy
from pydango.query.functions import FunctionExpression
from pydango.query.options import (
    RemoveOptions,
    ReplaceOptions,
    UpdateOptions,
    UpsertOptions,
)

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from pydantic.utils import lenient_issubclass

from pydango.orm.models import BaseArangoModel
from pydango.orm.utils import Aliased
from pydango.query.expressions import (
    BinaryLogicalExpression,
    CollectionExpression,
    ConditionExpression,
    FieldExpression,
    IterableExpression,
    IteratorExpression,
    LiteralExpression,
    NotSet,
    ObjectExpression,
    ReturnableMixin,
    VariableExpression,
)
from pydango.query.operations import ForParams, SortParams
from pydango.query.query import AQLQuery

ORMForParams = Union[ForParams, Type[BaseArangoModel], Aliased[Type[BaseArangoModel]]]


def walk_and_replace(condition: Union[ConditionExpression, BinaryLogicalExpression], query: "ORMQuery"):
    stack = [condition]
    while stack:
        current = stack.pop()
        if isinstance(current, (LiteralExpression, FieldExpression)):
            pass

        elif hasattr(current.left, "parent"):
            if lenient_issubclass(current.left.parent, BaseArangoModel):
                current.left.parent = query.orm_bound_vars[current.left.parent]

            if isinstance(current.left.parent, Aliased):
                left_ref = query.orm_bound_vars[current.left.parent]
                current.left.parent = left_ref
        else:
            if not isinstance(current, (LiteralExpression, FieldExpression)):
                stack.append(current.left)

        if isinstance(current, (LiteralExpression, FieldExpression)):
            pass
        elif hasattr(current.right, "parent"):
            if lenient_issubclass(current.right.parent, BaseArangoModel):
                current.right.parent = query.orm_bound_vars[current.right.parent]

            if isinstance(current.right, FieldExpression) and isinstance(current.right.parent, Aliased):
                current.right.parent = query.orm_bound_vars[current.right.parent]
        else:
            if not isinstance(current, (LiteralExpression, FieldExpression)):
                stack.append(current.right)


class ORMQuery(AQLQuery):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.orm_bound_vars = {}

    def for_(
        self,
        collection_or_variable: ORMForParams,
        in_: Optional[Union[IterableExpression, list]] = None,
    ) -> Self:
        if lenient_issubclass(collection_or_variable, BaseArangoModel):
            if in_ is not None:
                raise AssertionError(f"you should not pass in_ when using {collection_or_variable.__name__}")
            collection_expression = CollectionExpression(collection_or_variable.Collection.name)
            super().for_(collection_expression, in_)
            self.orm_bound_vars[collection_or_variable] = collection_expression.iterator
            return self
        elif isinstance(collection_or_variable, Aliased):
            if in_ is not None:
                raise AssertionError(f"you should not pass in_ when using {collection_or_variable.__name__}")
            if collection_or_variable.alias is NotSet:
                collection_or_variable.alias = None
            collection_expression = CollectionExpression(
                collection_or_variable.entity.Collection.name, collection_or_variable.alias
            )

            self.orm_bound_vars[collection_or_variable] = collection_expression.iterator
            return super().for_(collection_expression, in_)
        elif isinstance(in_, ORMQuery):
            self.orm_bound_vars.update(in_.orm_bound_vars)
            return super().for_(collection_or_variable, in_)

        elif isinstance(in_, LazyProxy):
            # if isinstance()
            return super().for_(collection_or_variable, in_.dict(by_alias=True))

        return super().for_(collection_or_variable, in_)

    def filter(self, condition: Union[ConditionExpression, BinaryLogicalExpression]) -> Self:
        walk_and_replace(condition, self)
        super().filter(condition)
        return self

    def sort(self, *sort_list: SortParams) -> Self:
        for i in range(len(sort_list)):
            # if isinstance(sort_list[i].field.parent, Aliased):
            sort_list[i].field.parent = self.orm_bound_vars[sort_list[i].field.parent]
            # if lenient_issubclass(sort_list[i].field.parent, BaseArangoModel):
            #     sort_list[i].field.parent = self.orm_bound_vars[sort_list[i].field.parent]
        # for i, s in enumerate(sort_list):
        #     a.append(self.orm_bound_vars[i])

        super().sort(*sort_list)
        return self

    @overload
    def insert(
        self, doc: Union[dict, ObjectExpression, IteratorExpression], collection: Union[str, CollectionExpression]
    ) -> Self:
        ...

    @overload
    def insert(self, doc: BaseArangoModel) -> Self:
        ...

    def insert(
        self,
        doc: Union[dict, ObjectExpression, BaseArangoModel, IteratorExpression],
        collection: Union[str, CollectionExpression] = None,
    ) -> Self:
        if isinstance(doc, (BaseArangoModel, LazyProxy)):
            collection = doc.Collection.name
            doc = doc.dict(by_alias=True, exclude=doc.__relationships__.keys())
        return super().insert(doc, collection)

    @overload
    def remove(self, model):
        ...

    def remove(
        self,
        expression: Union[FieldExpression, VariableExpression, ObjectExpression, str, BaseArangoModel],
        collection=None,
        *,
        options: Optional[RemoveOptions] = None,
    ) -> Self:
        if isinstance(expression, BaseArangoModel):
            collection = CollectionExpression(expression.Collection.name)
            expression = expression.dict()

        return super().remove(expression, collection, options=options)

    @overload
    def update(self, key, doc, *, options: Optional[UpdateOptions] = None) -> Self:
        ...

    @overload
    def update(self, key, doc, coll, *, options: Optional[UpdateOptions] = None) -> Self:
        ...

    def update(self, key, doc, coll=None, *, options: Optional[UpdateOptions] = None) -> Self:
        if isinstance(key, BaseArangoModel):
            coll = key.Collection.name
            key = key.dict()
        if isinstance(doc, BaseModel):
            doc = doc.dict()
        super().update(key, doc, coll, options=options)
        return self

    @overload
    def replace(self, key: BaseArangoModel, *, options: Optional[ReplaceOptions] = None) -> Self:
        ...

    @overload
    def replace(self, key, doc, coll, *, options: Optional[ReplaceOptions] = None) -> Self:
        ...

    def replace(self, key, doc, coll=None, *, options: Optional[ReplaceOptions] = None) -> Self:
        if isinstance(key, BaseArangoModel):
            coll = key.Collection.name
            key = key.dict()
        if isinstance(doc, BaseModel):
            doc = doc.dict()
        return super().replace(key, doc, coll, options=options)

    @overload
    def upsert(
        self,
        filter_: BaseArangoModel,
        insert: Union[dict, BaseModel, ObjectExpression],
        *,
        update: Optional[Union[dict, BaseModel, ObjectExpression]] = None,
        replace: Optional[Union[dict, BaseModel, ObjectExpression]] = None,
        options: Optional[UpsertOptions] = None,
    ) -> Self:
        ...

    @overload
    def upsert(
        self,
        filter_: Union[dict, BaseModel, ObjectExpression],
        insert: Union[dict, BaseModel, ObjectExpression],
        coll: Union[str, CollectionExpression] = None,
        *,
        update: Optional[Union[dict, BaseModel, ObjectExpression]] = None,
        replace: Optional[Union[dict, BaseModel, ObjectExpression]] = None,
        options: Optional[UpsertOptions] = None,
    ) -> Self:
        ...

    def upsert(
        self,
        filter_: Union[BaseArangoModel, dict],
        insert: Union[dict, BaseModel, ObjectExpression],
        coll: Union[str, CollectionExpression] = None,
        *,
        update: Optional[Union[dict, BaseModel, ObjectExpression]] = None,
        replace: Optional[Union[dict, BaseModel, ObjectExpression]] = None,
        options: Optional[UpsertOptions] = None,
    ) -> Self:
        if isinstance(filter_, BaseArangoModel):
            coll = filter_.Collection.name
            filter_ = filter_.dict()

        if isinstance(insert, BaseModel):
            insert = insert.dict()
        if isinstance(update, BaseModel):
            update = update.dict()
        if isinstance(replace, BaseModel):
            replace = replace.dict()

        super().upsert(filter_, insert, coll, update=update, replace=replace, options=options)
        return self

    def return_(
        self, return_expr: Union[Type[BaseArangoModel], ReturnableMixin, Aliased, dict, FunctionExpression]
    ) -> Self:
        if lenient_issubclass(return_expr, (BaseArangoModel, Aliased)):
            return_expr = self.orm_bound_vars[return_expr]
        elif isinstance(return_expr, Aliased):
            return_expr = self.orm_bound_vars[return_expr]

            # return_expr = ObjectExpression(variable, projection.__fields__)
        super().return_(return_expr)
        return self


def for_(collection_or_variable: ORMForParams, in_: Optional[Union[IterableExpression, list]] = None) -> ORMQuery:
    return ORMQuery().for_(collection_or_variable, in_)
