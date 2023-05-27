import json
import logging
from typing import Optional, Union, overload

from pydango.orm.encoders import jsonable_encoder

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from aioarango.database import Database

from pydango.query.expressions import (
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
)

logger = logging.getLogger(__name__)


class AQLQuery(QueryExpression):
    sep = " "

    def __init__(self, parent=None):
        super().__init__()
        self.compiled_vars = None
        self.bind_vars = {}
        self.__dynamic_vars__: list[VariableExpression] = []
        self.__used_vars__ = set()
        self._parameters = {}
        self._var_counter = 0
        self._param_counter = 0
        self._parent: AQLQuery = parent
        self._ops: list[Operation] = []
        self._compiled = None
        self._is_modification_query = False

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

    def get_var_name(self):
        if self._parent:
            return self._parent.get_var_name()
        self._var_counter += 1
        return f"var{self._var_counter}"

    def _get_param_var(self):
        if self._parent:
            return self._parent._get_param_var()
        self._param_counter += 1
        return f"@param{self._param_counter}"

    def for_(
        self,
        collection_or_variable: ForParams,
        in_: Optional[IterableExpression] = None,
    ) -> "AQLQuery":
        if self == in_:
            raise ValueError("is not possible to loop over the same query")

        if isinstance(in_, AQLQuery):
            in_._parent = self
            in_ = VectorSubQueryExpression(in_)

        self._ops.append(ForOperation(collection_or_variable, in_, query_ref=self))
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
        start: Union[LiteralExpression, VariableExpression, FieldExpression, str],
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
                query_ref=self,
            )
        )
        return self

    def filter(self, condition: ConditionExpression) -> "AQLQuery":
        if isinstance(condition, In) and isinstance(condition.right, AQLQuery):
            condition.right._parent = self
            condition.right = VectorSubQueryExpression(condition.right)

        self._ops.append(FilterOperation(condition, query_ref=self))
        return self

    def sort(self, *sort_list: SortParams) -> "AQLQuery":
        self._ops.append(SortOperation(*sort_list, query_ref=self))
        return self

    @overload
    def let(self, variable: VariableExpression, expression: Expression) -> "AQLQuery":
        ...

    @overload
    def let(self, variable: str, expression: Expression) -> "VariableExpression":
        ...

    def let(
        self, variable: Union[VariableExpression, str], expression: Optional[Expression]
    ) -> Union["AQLQuery", VariableExpression]:
        let_operation = LetOperation(variable, expression, query_ref=self)
        self._ops.append(let_operation)
        if isinstance(variable, str):
            return let_operation.variable
        return self

    def return_(self, return_expr: Union[ReturnableMixin, CollectionExpression, dict]) -> Self:
        if isinstance(return_expr, AQLQuery):
            return_expr._parent = self
            return_expr = SubQueryExpression(return_expr)
        self._ops.append(ReturnOperation(return_expr, query_ref=self))
        return self

    def compile(self, *args, **kwargs) -> str:
        if self._compiled:
            return self._compiled
        aql = []

        for var in self.__dynamic_vars__:
            var.var_name = self.get_var_name()

        for i in self._ops:
            aql.append(i.compile())

        self._compiled = self.sep.join(aql)
        return self._compiled

    def bind_variable(self, variable: VariableExpression):
        # todo: bind variable
        ...

    def bind_parameter(self, literal: LiteralExpression) -> Union[str, None]:
        if self._parent:
            return self._parent.bind_parameter(literal)
        is_hashable = False
        try:
            hash(literal.value)
            is_hashable = True
            if literal.value in self._parameters or literal.value in self.bind_vars.keys():
                return self._parameters[literal.value]
        except TypeError:
            if str(literal.value) in self._parameters:
                return self._parameters[str(literal.value)]

        var = self._get_param_var()

        self.bind_vars[var[1:]] = literal.value

        if is_hashable:
            self._parameters[literal.value] = var
        else:
            self._parameters[str(literal.value)] = var

        return var

    def limit(self, limit) -> Self:
        self._ops.append(LimitOperation(limit, self))
        return self

    def insert(self, doc: Union[dict, ObjectExpression], collection: Union[str, CollectionExpression]) -> Self:
        self._is_modification_query = True
        self._ops.append(InsertOperation(doc, collection, self))
        return self

    def remove(
        self,
        expression: Union[FieldExpression, VariableExpression, ObjectExpression, str],
        collection,
        *,
        options: Optional[RemoveOptions] = None,
    ) -> Self:
        self._is_modification_query = True
        self._ops.append(RemoveOperation(expression, collection, options=options, query_ref=self))
        return self

    def update(self, key, doc, coll, *, options: Optional[UpdateOptions] = None) -> Self:
        self._is_modification_query = True
        self._ops.append(
            UpdateOperation(key, doc, coll, query_ref=self, options=options),
        )
        return self

    def replace(self, key, doc, coll, *, options: Optional[ReplaceOptions] = None) -> Self:
        self._is_modification_query = True
        self._ops.append(
            ReplaceOperation(key, doc, coll, query_ref=self, options=options),
        )
        return self

    @overload
    def upsert(self, filter_, insert, coll, replace=None, *, options=None) -> Self:
        ...

    @overload
    def upsert(self, filter_, insert, coll, update=None, *, options=None) -> Self:
        ...

    def upsert(self, filter_, insert, coll, update=None, replace=None, *, options=None) -> Self:
        self._is_modification_query = True
        self._ops.append(
            UpsertOperation(
                self, filter_=filter_, insert=insert, update=update, replace=replace, collection=coll, options=options
            )
        )
        return self

    @overload
    def collect(
        self,
        collect: Optional[AssignmentParams] = None,
        into: Optional[Union[VariableExpression, AssignmentParam]] = None,
        keep: Optional[VariableExpression] = None,
        options: Optional[CollectOptions] = None,
    ):
        ...

    @overload
    def collect(
        self,
        collect: Optional[AssignmentParams] = None,
        with_count_into: Optional[VariableExpression] = None,
        options: Optional[CollectOptions] = None,
    ):
        ...

    @overload
    def collect(
        self,
        collect: Optional[AssignmentParams] = None,
        aggregate: Optional[AssignmentParams] = None,
        into: Optional[Union[VariableExpression, AssignmentParam]] = None,
        options: Optional[CollectOptions] = None,
    ):
        ...

    @overload
    def collect(
        self,
        aggregate: Optional[AssignmentParams] = None,
        into: Optional[Union[VariableExpression, AssignmentParam]] = None,
        options: Optional[CollectOptions] = None,
    ):
        ...

    @overload
    def collect(
        self,
        with_count_into: Optional[VariableExpression] = None,
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

    async def execute(self, db: Database, **options):
        compiled = self.compile()
        self.compiled_vars = jsonable_encoder(self.bind_vars)
        logger.debug("executing query", extra={"query": compiled, "bind_vars": json.dumps(self.compiled_vars)})
        return await db.aql.execute(compiled, bind_vars=self.compiled_vars, **options)
