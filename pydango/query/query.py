import json
import logging
import sys
from typing import Any, Dict, List, Optional, Union, overload

# from pydango.orm.models import BaseArangoModel, save_dict

if sys.version_info >= (3, 10):
    from typing import Self, TypeAlias
else:
    from typing_extensions import Self, TypeAlias

from aioarango.database import Database

from pydango.orm.encoders import jsonable_encoder

# if TYPE_CHECKING:
from pydango.query.expressions import (
    BindableExpression,
    CollectionExpression,
    ConditionExpression,
    Expression,
    FieldExpression,
    In,
    IterableExpression,
    IteratorExpression,
    LiteralExpression,
    ObjectExpression,
    QueryExpression,
    ReturnableMixin,
    SubQueryExpression,
    VariableExpression,
    VectorSubQueryExpression,
)
from pydango.query.operations import (
    AssignmentParam,
    AssignmentParams,
    CollectOperation,
    FilterOperation,
    ForOperation,
    ForParams,
    InsertOperation,
    LetOperation,
    LimitOperation,
    Operation,
    RangeExpression,
    RemoveOperation,
    ReplaceOperation,
    ReturnOperation,
    SortOperation,
    SortParams,
    TraversalDirection,
    TraversalOperation,
    UpdateOperation,
    UpsertOperation,
)
from pydango.query.options import (
    CollectOptions,
    RemoveOptions,
    ReplaceOptions,
    UpdateOptions,
    UpsertOptions,
)

logger = logging.getLogger(__name__)

JsonType: TypeAlias = Union[None, int, str, bool, List["JsonType"], Dict[str, "JsonType"]]


class AQLQuery(QueryExpression):
    sep = " "

    def __init__(self, parent: Optional["AQLQuery"] = None):
        super().__init__()
        self.compiled_vars = None
        self.bind_vars: dict[str, Union[bool, str, int, float, dict, list]] = {}
        self.__dynamic_vars__: list[VariableExpression] = []
        self.__used_vars__: set[str] = set()
        self._parameters: dict[Any, str] = {}
        self._var_counter = 0
        self._param_counter = 0
        self.parent: Optional[AQLQuery] = parent
        self._ops: list[Operation] = []
        self._compiled = ""
        self.__is_modification_query__ = False

    def __str__(self):
        if self._compiled:
            return f"{self._compiled}{self.sep}{self.bind_vars}"
        else:
            return repr(self)

    def __repr__(self):
        aql = []
        for i in self._ops:
            if i == self:
                continue
            aql.append(repr(i))
        return self.sep.join(aql)

    def _get_var_name(self):
        if self.parent:
            return self.parent._get_var_name()
        self._var_counter += 1
        return f"var{self._var_counter}"

    def _get_param_var(self):
        if self.parent:
            return self.parent._get_param_var()
        self._param_counter += 1
        return f"@param{self._param_counter}"

    def for_(
        self,
        collection_or_variable: ForParams,
        in_: Optional[Union[IterableExpression, list, VariableExpression, list[VariableExpression], "AQLQuery"]] = None,
    ) -> Self:
        if self == in_:
            raise ValueError("is not possible to loop over the same query")

        if isinstance(in_, AQLQuery):
            in_.parent = self
            in_ = VectorSubQueryExpression(in_)

        self._ops.append(ForOperation(collection_or_variable, in_, query_ref=self))  # type: ignore[arg-type]
        return self

    def traverse(
        self,
        iterators: Union[
            IteratorExpression,
            tuple[IteratorExpression],
            tuple[IteratorExpression, IteratorExpression],
            tuple[IteratorExpression, IteratorExpression, IteratorExpression],
        ],
        edge: Union[str, CollectionExpression],
        start: Union["LiteralExpression", VariableExpression, FieldExpression, str],
        depth: Union[RangeExpression, range, tuple[int, int]],
        direction: TraversalDirection,
    ):
        self._ops.append(
            TraversalOperation(
                iterators=iterators,
                edge=edge,
                start=start,
                depth=depth,
                direction=direction,
                query_ref=self,  # type: ignore[arg-type]
            )
        )
        return self

    def filter(self, condition: ConditionExpression) -> "AQLQuery":
        if isinstance(condition, In) and isinstance(condition.right, AQLQuery):
            condition.right.parent = self
            condition.right = VectorSubQueryExpression(condition.right)

        self._ops.append(FilterOperation(condition, query_ref=self))  # type: ignore[arg-type]
        return self

    def sort(self, *sort_list: SortParams) -> "AQLQuery":
        self._ops.append(SortOperation(*sort_list, query_ref=self))  # type: ignore[arg-type]
        return self

    @overload
    def let(self, variable: VariableExpression, expression: Expression) -> "AQLQuery":
        ...

    @overload
    def let(self, variable: str, expression: Expression) -> "VariableExpression":
        ...

    def let(
        self, variable: Union[VariableExpression, str], expression: Expression
    ) -> Union["AQLQuery", VariableExpression]:
        let_operation = LetOperation(variable, expression, query_ref=self)  # type: ignore[arg-type]
        self._ops.append(let_operation)
        if isinstance(variable, str):
            return let_operation.expression.variable
        return self

    def return_(self, return_expr: Union[ReturnableMixin, dict]) -> Self:
        if isinstance(return_expr, AQLQuery):
            return_expr.parent = self
            return_expr = SubQueryExpression(return_expr)
        self._ops.append(ReturnOperation(return_expr, query_ref=self))  # type: ignore[arg-type]
        return self

    def compile(self, *args, **kwargs) -> str:
        if self._compiled:
            return self._compiled
        aql = []

        for i in self._ops:
            aql.append(i.compile())

        self._compiled = self.sep.join(aql)
        return self._compiled

    def bind_variable(self) -> str:
        return self._get_var_name()

    def bind_parameter(self, parameter: BindableExpression, override_var_name: Optional[str] = None) -> str:
        if self.parent:
            return self.parent.bind_parameter(parameter)
        is_hashable = False
        try:
            hash(parameter.value)
            is_hashable = True
            if parameter.value in self._parameters or parameter.value in self.bind_vars.keys():
                return self._parameters[parameter.value]
        except TypeError:
            if str(parameter.value) in self._parameters:
                return self._parameters[str(parameter.value)]

        var = override_var_name or self._get_param_var()

        self.bind_vars[var[1:]] = parameter.value

        if is_hashable:
            self._parameters[parameter.value] = var
        else:
            self._parameters[str(parameter.value)] = var

        return var

    def limit(self, limit) -> Self:
        self._ops.append(LimitOperation(limit, self))  # type: ignore[arg-type]
        return self

    def insert(
        self, doc: Union[dict, ObjectExpression, VariableExpression], collection: Union[str, CollectionExpression]
    ) -> Self:
        self.__is_modification_query__ = True
        self._ops.append(InsertOperation(doc, collection, self))  # type: ignore[arg-type]
        return self

    def remove(
        self,
        expression: Union[dict, LiteralExpression, FieldExpression, VariableExpression, ObjectExpression, str],
        collection: Union[str, CollectionExpression],
        *,
        options: Optional[RemoveOptions] = None,
    ) -> Self:
        self.__is_modification_query__ = True
        self._ops.append(
            RemoveOperation(expression, collection, options=options, query_ref=self)
        )  # type: ignore[arg-type]
        return self

    def update(self, key, doc, coll, *, options: Optional[UpdateOptions] = None) -> Self:
        self.__is_modification_query__ = True
        self._ops.append(
            UpdateOperation(key, doc, coll, query_ref=self, options=options),
        )
        return self

    def replace(
        self,
        key: Union[str, dict, ObjectExpression],
        doc: Union[ObjectExpression, dict],
        collection: Union[CollectionExpression, str],
        *,
        options: Optional[ReplaceOptions] = None,
    ) -> Self:
        self.__is_modification_query__ = True
        self._ops.append(
            ReplaceOperation(key, doc, collection, query_ref=self, options=options),
        )
        return self

    @overload
    def upsert(
        self,
        filter_: Union[dict, ObjectExpression, VariableExpression],
        insert: Union[dict, ObjectExpression, VariableExpression],
        collection: Union[str, CollectionExpression],
        *,
        replace: Union[dict, ObjectExpression, VariableExpression],
        options: Optional[UpsertOptions] = None,
    ) -> Self:
        ...

    @overload
    def upsert(
        self,
        filter_: Union[dict, ObjectExpression, VariableExpression],
        insert: Union[dict, ObjectExpression, VariableExpression],
        collection: Union[str, CollectionExpression],
        *,
        update: Union[dict, ObjectExpression, VariableExpression],
        options: Optional[UpsertOptions] = None,
    ) -> Self:
        ...

    def upsert(
        self,
        filter_: Union[dict, ObjectExpression, VariableExpression],
        insert: Union[dict, ObjectExpression, VariableExpression],
        collection: Union[str, CollectionExpression],
        *,
        update: Union[dict, ObjectExpression, VariableExpression, None] = None,
        replace: Union[dict, ObjectExpression, VariableExpression, None] = None,
        options: Optional[UpsertOptions] = None,
    ) -> Self:
        self.__is_modification_query__ = True

        if update:
            upsert_operation = UpsertOperation(
                self, filter_=filter_, insert=insert, collection=collection, update=update, options=options
            )
        elif replace:
            upsert_operation = UpsertOperation(
                self, filter_=filter_, insert=insert, collection=collection, replace=replace, options=options
            )
        else:
            raise ValueError("you must pass update or replace")

        self._ops.append(upsert_operation)
        return self

    @overload
    def collect(
        self,
        *,
        collect: Optional[AssignmentParams] = None,
        into: Optional[Union[VariableExpression, AssignmentParam]] = None,
        keep: Optional[VariableExpression] = None,
        options: Optional[CollectOptions] = None,
    ):
        ...

    @overload
    def collect(
        self,
        *,
        with_count_into: Optional[VariableExpression] = None,
        options: Optional[CollectOptions] = None,
    ):
        ...

    @overload
    def collect(
        self,
        *,
        collect: Optional[AssignmentParams] = None,
        with_count_into: Optional[VariableExpression] = None,
        options: Optional[CollectOptions] = None,
    ):
        ...

    @overload
    def collect(
        self,
        *,
        aggregate: Optional[AssignmentParams] = None,
        into: Optional[Union[VariableExpression, AssignmentParam]] = None,
        options: Optional[CollectOptions] = None,
    ):
        ...

    @overload
    def collect(
        self,
        *,
        collect: Optional[AssignmentParams] = None,
        aggregate: Optional[AssignmentParams] = None,
        into: Optional[Union[VariableExpression, AssignmentParam]] = None,
        options: Optional[CollectOptions] = None,
    ):
        ...

    def collect(
        self,
        *,
        collect: Optional[AssignmentParams] = None,
        aggregate: Optional[AssignmentParams] = None,
        into: Optional[Union[VariableExpression, AssignmentParam]] = None,
        keep: Optional[VariableExpression] = None,
        with_count_into: Optional[VariableExpression] = None,
        options: Optional[CollectOptions] = None,
    ) -> Self:
        self._ops.append(
            CollectOperation(
                collect=collect,
                aggregate=aggregate,
                into=into,
                keep=keep,
                with_count_into=with_count_into,
                options=options,
                query_ref=self,
            )
        )
        return self

    def _serialize_vars(self):
        return jsonable_encoder(self.bind_vars, by_alias=True)

    async def execute(self, db: Database, **options):
        compiled = self.compile()
        self.compiled_vars = self._serialize_vars()
        logger.debug("executing query", extra={"query": compiled, "bind_vars": json.dumps(self.compiled_vars)})
        return await db.aql.execute(compiled, bind_vars=self.compiled_vars, **options)
