import logging
import sys
from typing import TYPE_CHECKING, Optional, Sequence, Type, Union, cast, overload

from pydantic import BaseModel
from pydantic.utils import lenient_issubclass

from pydango.orm.encoders import jsonable_encoder
from pydango.orm.models.base import Aliased, BaseArangoModel, LazyProxy
from pydango.orm.models.fields import ModelFieldExpression
from pydango.orm.models.utils import save_dict
from pydango.query.expressions import (
    BinaryExpression,
    CollectionExpression,
    FieldExpression,
    IteratorExpression,
    LiteralExpression,
    ReturnableExpression,
    SortExpression,
)
from pydango.query.options import (
    RemoveOptions,
    ReplaceOptions,
    UpdateOptions,
    UpsertOptions,
)
from pydango.query.query import AQLQuery, TraverseIterators

if sys.version_info >= (3, 11):
    from typing import Self, TypeAlias
else:
    from typing_extensions import Self, TypeAlias

if TYPE_CHECKING:
    from pydango.orm.models.base import ArangoModel
    from pydango.query.expressions import (
        BinaryLogicalExpression,
        ConditionExpression,
        Expression,
        IterableExpression,
        ObjectExpression,
        RangeExpression,
        VariableExpression,
    )
    from pydango.query.operations import ForParams, SortParams, TraversalDirection

logger = logging.getLogger(__name__)

ORMForParams: TypeAlias = Union["ForParams", Type[BaseArangoModel], Aliased[BaseArangoModel]]
IMPLICIT_COLLECTION_ERROR = "you must specify collection when the collection cannot be implicitly resolved"
MULTIPLE_COLLECTIONS_RESOLVED = "multiple collections resolved"


def _bind(query: "ORMQuery", node: "Expression"):
    if isinstance(node, FieldExpression):
        if node.parent and isinstance(node.parent, type) and issubclass(node.parent, BaseArangoModel):
            node.parent = query.orm_bound_vars[cast(Type[BaseArangoModel], node.parent)]

    # if isinstance(node.parent, Aliased):
    if isinstance(node, FieldExpression) and isinstance(node.parent, Aliased):
        node.parent = query.orm_bound_vars[node.parent]


def _find_models_and_bind(condition: Union["ConditionExpression", "BinaryLogicalExpression"], query: "ORMQuery"):
    stack: list[Union[BinaryExpression, "Expression"]] = [condition]
    while stack:
        current = stack.pop()
        if isinstance(current, (LiteralExpression, FieldExpression)):
            continue
        if isinstance(current, BinaryExpression):
            if isinstance(current.left, (FieldExpression, AQLQuery)):
                _bind(query, current.left)
            else:
                stack.append(current.left)

            if isinstance(current.right, (FieldExpression, AQLQuery)):
                _bind(query, current.right)
            else:
                stack.append(current.right)
        else:
            raise Exception("need to check this error")


class ORMQuery(AQLQuery):
    def __init__(self, parent: Optional[AQLQuery] = None):
        super().__init__(parent)
        # self.bind_parameter_to_sequence = {}
        self.orm_bound_vars: dict[Union[Type[BaseArangoModel], Aliased, "ModelFieldExpression"], VariableExpression] = (
            {}
        )

    def for_(
        self,
        collection_or_variable: ORMForParams,
        in_: Optional[
            Union[AQLQuery, "IterableExpression", list, "VariableExpression", list["VariableExpression"]]
        ] = None,
    ) -> Self:
        if lenient_issubclass(collection_or_variable, BaseArangoModel):
            model = cast(BaseArangoModel, collection_or_variable)
            if in_ is not None:
                raise AssertionError(
                    f"you should not pass in_ when using {collection_or_variable.__name__}"  # type: ignore[union-attr]
                )
            collection_expression = CollectionExpression(model.Collection.name)
            super().for_(collection_expression, in_)
            self.orm_bound_vars[cast(Type[BaseArangoModel], collection_or_variable)] = collection_expression.iterator

        elif isinstance(collection_or_variable, Aliased):
            if in_ is not None:
                raise AssertionError(
                    f"you should not pass in_ when using {collection_or_variable.__name__}"  # type: ignore[union-attr]
                )
            collection_expression = CollectionExpression(
                collection_or_variable.entity.Collection.name, collection_or_variable.alias
            )

            self.orm_bound_vars[collection_or_variable] = collection_expression.iterator
            super().for_(collection_expression, in_)

        elif isinstance(in_, ORMQuery):
            self.orm_bound_vars.update(in_.orm_bound_vars)
            super().for_(cast(Union[str, IteratorExpression], collection_or_variable), cast(AQLQuery, in_))

        elif isinstance(in_, LazyProxy):
            super().for_(collection_or_variable, in_.dict(by_alias=True))
        elif isinstance(in_, Sequence):
            # if in_ and isinstance(in_[0], BaseArangoModel) and len(set([x.Collection.name for x in in_])) == 1:
            #     self.bind_parameter_to_sequence[id(in_[0])] = in_[0].Collection.name
            super().for_(cast(Union[str, IteratorExpression], collection_or_variable), cast(list, in_))
        else:
            # logger.info("couldn't resolver at orm layer",extra={"vars":[collection_or_variable,in_]})
            super().for_(cast(Union[str, IteratorExpression], collection_or_variable), in_)

        return self

    def filter(self, condition: Union["ConditionExpression", "BinaryLogicalExpression"]) -> Self:
        _find_models_and_bind(condition, self)
        super().filter(condition)
        return self

    def sort(self, *sort_list: "SortParams") -> Self:
        for i in range(len(sort_list)):
            sort = sort_list[i]
            if isinstance(sort, SortExpression) and isinstance(sort.field, ModelFieldExpression):
                sort.field.parent = self.orm_bound_vars[cast(Type[BaseArangoModel], sort.field.parent)]
            if isinstance(sort, ModelFieldExpression):
                sort.parent = self.orm_bound_vars[cast(Type[BaseArangoModel], sort.parent)]

        super().sort(*sort_list)
        return self

    # noinspection PyMethodOverriding
    @overload
    def insert(self, doc: "ArangoModel") -> Self: ...

    @overload
    def insert(
        self, doc: Union[dict, "ObjectExpression", "VariableExpression"], collection: Union[str, CollectionExpression]
    ) -> Self: ...

    def insert(
        self,
        doc: Union[dict, "ObjectExpression", BaseArangoModel, "VariableExpression"],
        collection: Optional[Union[str, CollectionExpression]] = None,
    ) -> Self:
        if isinstance(doc, (BaseArangoModel, LazyProxy)):
            collection = doc.Collection.name
            doc = doc.save_dict()
        elif collection is None:
            raise ValueError(IMPLICIT_COLLECTION_ERROR)
        return super().insert(doc, collection)

    @overload
    def remove(  # noqa: PyMethodOverriding
        self, expression: BaseArangoModel, *, options: Optional[RemoveOptions] = None
    ): ...

    @overload
    def remove(
        self,
        expression: Union[dict, LiteralExpression, FieldExpression, "VariableExpression", "ObjectExpression", str],
        collection: Union[str, CollectionExpression],
        *,
        options: Optional[RemoveOptions] = None,
    ): ...

    def remove(
        self,
        expression: Union[
            BaseArangoModel, dict, LiteralExpression, FieldExpression, "VariableExpression", "ObjectExpression", str
        ],
        collection: Union[str, CollectionExpression, None] = None,
        *,
        options: Optional[RemoveOptions] = None,
    ) -> Self:
        if isinstance(expression, BaseArangoModel):
            collection = CollectionExpression(expression.Collection.name)
            expression = expression.dict(include={"key"}, by_alias=True)
        elif collection is None:
            raise ValueError(IMPLICIT_COLLECTION_ERROR)

        return super().remove(expression, collection, options=options)

    @overload
    def update(self, key, doc, *, options: Optional[UpdateOptions] = None) -> Self:  # noqa: PyMethodOverriding
        ...

    @overload
    def update(self, key, doc, coll, *, options: Optional[UpdateOptions] = None) -> Self: ...

    def update(self, key, doc, coll=None, *, options: Optional[UpdateOptions] = None) -> Self:
        if isinstance(key, BaseArangoModel):
            coll = key.Collection.name
            key = key.dict()
        if isinstance(doc, BaseModel):
            doc = doc.dict()
        super().update(key, doc, coll, options=options)
        return self

    @overload
    def replace(  # noqa: PyMethodOverriding
        self,
        key: Union[str, dict, BaseArangoModel],
        doc: BaseArangoModel,
        *,
        options: Optional[ReplaceOptions] = None,
    ) -> Self: ...

    @overload
    def replace(  # noqa: PyMethodOverriding
        self,
        key: BaseArangoModel,
        doc: Union[dict, BaseArangoModel],
        *,
        options: Optional[ReplaceOptions] = None,
    ) -> Self: ...

    @overload
    def replace(
        self,
        key: Union[str, dict, "ObjectExpression"],
        doc: Union[dict, "ObjectExpression"],
        collection: Union[str, CollectionExpression],
        *,
        options: Optional[ReplaceOptions] = None,
    ) -> Self: ...

    def replace(
        self,
        key: Union[str, dict, "ObjectExpression", BaseArangoModel],
        doc: Union[dict, "ObjectExpression", BaseArangoModel],
        collection: Union[str, CollectionExpression, None] = None,
        *,
        options: Optional[ReplaceOptions] = None,
    ) -> Self:
        if isinstance(key, BaseArangoModel):
            collection = key.Collection.name
            key = key.dict(include={"key"}, by_alias=True)
        if isinstance(doc, BaseModel):
            doc = doc.dict()
        if isinstance(doc, BaseArangoModel):
            if collection is None:
                collection = doc.Collection.name
            elif collection != doc.Collection:
                raise AssertionError(MULTIPLE_COLLECTIONS_RESOLVED)
        if collection is None:
            raise ValueError(IMPLICIT_COLLECTION_ERROR)
        return super().replace(key, doc, collection, options=options)

    @overload
    def upsert(  # noqa: PyMethodOverriding
        self,
        filter_: BaseArangoModel,
        insert: Union[dict, BaseModel, "ObjectExpression", BaseArangoModel, "VariableExpression"],
        *,
        replace: Union[dict, BaseModel, "ObjectExpression", BaseArangoModel, "VariableExpression"],
        options: Optional[UpsertOptions] = None,
    ) -> Self: ...

    @overload
    def upsert(  # noqa: PyMethodOverriding
        self,
        filter_: BaseArangoModel,
        insert: Union[dict, BaseModel, "ObjectExpression", BaseArangoModel, "VariableExpression"],
        *,
        update: Union[dict, BaseModel, "ObjectExpression", BaseArangoModel, "VariableExpression"],
        options: Optional[UpsertOptions] = None,
    ) -> Self: ...

    @overload
    def upsert(  # noqa: PyMethodOverriding
        self,
        filter_: Union[dict, BaseModel, "ObjectExpression", "VariableExpression"],
        insert: Union[dict, BaseModel, "ObjectExpression", "VariableExpression"],
        collection: Union[str, CollectionExpression],
        *,
        replace: Union[dict, BaseModel, "ObjectExpression", "VariableExpression"],
        options: Optional[UpsertOptions] = None,
    ) -> Self: ...

    @overload
    def upsert(  # noqa: PyMethodOverriding
        self,
        filter_: Union[dict, BaseModel, "ObjectExpression", "VariableExpression"],
        insert: Union[dict, BaseModel, "ObjectExpression", "VariableExpression"],
        collection: Union[str, CollectionExpression],
        *,
        update: Union[dict, BaseModel, "ObjectExpression", "VariableExpression"],
        options: Optional[UpsertOptions] = None,
    ) -> Self: ...

    def upsert(
        self,
        filter_: Union[dict, "ObjectExpression", BaseModel, BaseArangoModel, "VariableExpression"],
        insert: Union[dict, "ObjectExpression", BaseModel, BaseArangoModel, "VariableExpression"],
        collection: Union[str, CollectionExpression, None] = None,
        **kwargs,
        # update: Union[dict,"ObjectExpression", BaseModel, BaseArangoModel, None] = None,
        # replace: Union[dict, "ObjectExpression", BaseModel,BaseArangoModel, None] = None,
        # options: Optional[UpsertOptions] = None,
    ) -> Self:
        update = kwargs.get("update")
        replace = kwargs.get("replace")

        if isinstance(filter_, BaseArangoModel):
            collection = filter_.Collection.name

            if update and isinstance(update, BaseArangoModel) and update.Collection.name != collection:
                raise AssertionError(MULTIPLE_COLLECTIONS_RESOLVED)

            if replace and isinstance(replace, BaseArangoModel) and replace.Collection.name != collection:
                raise AssertionError(MULTIPLE_COLLECTIONS_RESOLVED)

        if isinstance(filter_, BaseModel):
            filter_ = filter_.dict()

        if collection is None:
            if isinstance(insert, BaseArangoModel):
                collection = insert.Collection.name
            elif update and isinstance(update, BaseArangoModel):
                collection = update.Collection.name
            elif replace and isinstance(replace, BaseArangoModel):
                collection = replace.Collection.name
            else:
                raise ValueError(IMPLICIT_COLLECTION_ERROR)

        if isinstance(insert, BaseModel):
            insert = insert.dict()
        if update and isinstance(update, BaseModel):
            kwargs["update"] = update.dict()
        if replace and isinstance(replace, BaseModel):
            kwargs["replace"] = replace.dict()

        super().upsert(filter_, insert, collection, **kwargs)
        return self

    def return_(self, return_expr: Union[Type[BaseArangoModel], Aliased, "ReturnableExpression", dict]) -> Self:
        if isinstance(return_expr, type) and issubclass(return_expr, (BaseArangoModel,)):
            return_expr = self.orm_bound_vars[return_expr]
        elif isinstance(return_expr, Aliased):
            return_expr = cast("ReturnableExpression", self.orm_bound_vars[return_expr])

        super().return_(return_expr)
        return self

    def _serialize_vars(self):
        return jsonable_encoder(self.bind_vars, by_alias=True, custom_encoder={BaseArangoModel: save_dict})

    def traverse(
        self,
        iterators: TraverseIterators,
        edges: Union[str, CollectionExpression, Sequence[Union[str, CollectionExpression]]],
        start: Union["LiteralExpression", "VariableExpression", FieldExpression, str],
        depth: Union["RangeExpression", range, tuple[int, int]],
        direction: "TraversalDirection",
    ):
        return super().traverse(iterators, edges, start, depth, direction)
        # return self


def for_(
    collection_or_variable: ORMForParams,
    in_: Optional[Union["IterableExpression", "VariableExpression", list["VariableExpression"], list]] = None,
) -> ORMQuery:
    return ORMQuery().for_(collection_or_variable, in_)


def traverse(
    collection_or_variable: ORMForParams,
    in_: Optional[Union["IterableExpression", "VariableExpression", list["VariableExpression"], list]] = None,
) -> ORMQuery:
    return ORMQuery().for_(collection_or_variable, in_)
