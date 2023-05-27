from enum import Enum
from typing import TYPE_CHECKING, Mapping, Optional, Sequence, Union, overload

from pydango.query.expressions import (
    AssignmentExpression,
    CollectionExpression,
    Expression,
    FieldExpression,
    IterableExpression,
    IteratorExpression,
    ListExpression,
    LiteralExpression,
    LogicalExpression,
    NotSet,
    ObjectExpression,
    QueryExpression,
    ReturnableMixin,
    SortExpression,
    VariableExpression,
)
from pydango.query.options import (
    CollectOptions,
    LoopOptions,
    RemoveOptions,
    ReplaceOptions,
    UpdateOptions,
    UpsertOptions,
)
from pydango.query.utils import Compilable, SortDirection

if TYPE_CHECKING:
    from pydango.query.query import AQLQuery


class Operation(Compilable):
    def __init__(self, query_ref: "AQLQuery"):
        self.query_ref = query_ref

    def compile(self, *args, **kwargs):
        raise NotImplementedError


ForParams = Union[str, IteratorExpression, IterableExpression, "AQLQuery"]

MANUAL_TYPES = (str, IteratorExpression)
AUTOMATIC_TYPES = (
    ListExpression,
    CollectionExpression,
    # Aliased,
)
try:
    from typing import TypeAlias
except ImportError:
    from typing_extensions import TypeAlias


class ForOperation(Operation):
    def __init__(
        self,
        collection_or_variable: ForParams,
        in_: Optional[Union[IterableExpression, list]] = None,
        *,
        query_ref: "AQLQuery",
        options: LoopOptions = None,
    ):
        super().__init__(query_ref)
        self.options = options
        self.query_ref = query_ref

        if isinstance(collection_or_variable, MANUAL_TYPES):
            if isinstance(in_, list):
                in_ = ListExpression(tuple(in_))
            elif isinstance(in_, tuple):
                in_ = ListExpression(in_)

            elif in_ is None:
                raise AssertionError(f"you must provide in_ field when using {MANUAL_TYPES}")
            elif not isinstance(in_, (IterableExpression, VariableExpression)):
                raise AssertionError(f"in_ should be instance of {IterableExpression.__name__}")

            if isinstance(collection_or_variable, IteratorExpression):
                if collection_or_variable.var_name in query_ref.__used_vars__:
                    raise AttributeError(f"{collection_or_variable.var_name} variable is already defined")

                if collection_or_variable.var_name is NotSet:
                    self.query_ref.__dynamic_vars__.append(collection_or_variable)

                else:
                    self.query_ref.__used_vars__.add(collection_or_variable.var_name)

            self.variable = collection_or_variable
            self.in_ = in_

        # elif in_ is not None and isinstance(collection_or_variable, AUTOMATIC_TYPES):
        #     raise AssertionError(
        #         f"you must not provide in_ field when using {AUTOMATIC_TYPES}"
        #     )

        elif isinstance(collection_or_variable, AUTOMATIC_TYPES):
            if isinstance(collection_or_variable, CollectionExpression):
                if collection_or_variable.iterator.var_name is NotSet:
                    self.query_ref.__dynamic_vars__.append(collection_or_variable.iterator)
                elif not collection_or_variable.iterator:
                    i = IteratorExpression()
                    collection_or_variable.iterator = i
                    self.query_ref.__dynamic_vars__.append(i)
                elif collection_or_variable.iterator.var_name in query_ref.__used_vars__:
                    raise ValueError(f"{collection_or_variable.iterator.var_name} variable is already defined")
                else:
                    query_ref.__used_vars__.add(collection_or_variable.iterator.var_name)

                self.in_ = collection_or_variable
                self.variable = collection_or_variable.iterator or IteratorExpression(collection_or_variable.value)

            elif isinstance(collection_or_variable, ListExpression):
                if not collection_or_variable.iterator:
                    i = IteratorExpression()
                    collection_or_variable.iterator = i
                elif collection_or_variable.iterator.var_name in query_ref.__used_vars__:
                    raise ValueError(f"{collection_or_variable.iterator.var_name} variable is already defined")
                else:
                    query_ref.__used_vars__.add(collection_or_variable.iterator.var_name)

                self.in_ = collection_or_variable
                self.variable = collection_or_variable.iterator or IteratorExpression(collection_or_variable.value)

        else:
            self.variable = collection_or_variable
            self.in_ = in_

    def compile(self) -> str:
        compiled = f"FOR {self.variable.compile(self.query_ref)} IN {self.in_.compile(self.query_ref)}"
        if self.options:
            options_compile = self.options.compile()
            compiled += options_compile and f"OPTIONS {options_compile}"
        return compiled

    def __repr__(self):
        _repr = f"FOR {self.variable} IN {self.in_}"
        if self.options:
            options_compile = self.options.compile()
            _repr += options_compile and f"OPTIONS {options_compile}"
        return _repr


class RangeExpression(IterableExpression):
    def __init__(self, start, end):
        super().__init__()
        self.end = end
        self.start = start

    def compile(self, query_ref: "AQLQuery"):
        if isinstance(self.start, Expression):
            start = self.start.compile(query_ref)
        else:
            start = self.start
        if isinstance(self.end, Expression):
            end = self.end.compile(query_ref)
        else:
            end = self.end

        return f"{start}..{end}"

    def __repr__(self):
        return f"{self.start}..{self.end}"


class TraversalDirection(str, Enum):
    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"
    ANY = "ANY"


class TraversalOperation(Operation):
    def __init__(
        self,
        iterators: Union[
            IteratorExpression,
            tuple[IteratorExpression],
            tuple[IteratorExpression, IteratorExpression],
            tuple[IteratorExpression, IteratorExpression, IteratorExpression],
        ],
        edge: Union[str, CollectionExpression],
        start: Union[LiteralExpression, str],
        depth: Union[RangeExpression, range, tuple[int, int]],
        direction: TraversalDirection,
        query_ref: "AQLQuery",
    ):
        super().__init__(query_ref)
        if isinstance(edge, str):
            edge = CollectionExpression(edge)
        if isinstance(iterators, IteratorExpression):
            iterators = [iterators]
        if isinstance(depth, tuple):
            depth = RangeExpression(depth[0], depth[1])
        elif isinstance(depth, range):
            depth = RangeExpression(depth.start, depth.stop)
        if isinstance(start, str):
            start = LiteralExpression(start)
        self.iterators = iterators
        self.edge = edge
        self.start = start
        self.direction = direction
        self.depth = depth

    def compile(self, *args, **kwargs):
        compiled_iterators = []
        for i in self.iterators:
            compiled_iterators.append(i.compile(self.query_ref))

        return (
            f"FOR {', '.join(compiled_iterators)} IN"
            f" {self.depth.compile(self.query_ref)} {self.direction.value} {self.start.compile(self.query_ref)} {self.edge.compile(self.query_ref)}"
        )

    def __repr__(self):
        compiled_iterators = []
        for i in self.iterators:
            compiled_iterators.append(repr(i))

        return (
            f"FOR {', '.join(compiled_iterators)} IN {repr(self.depth)} {self.direction.value} {self.start} {self.edge}"
        )


class LetOperation(Operation):
    def __init__(
        self,
        variable: Union[VariableExpression, str],
        expression: Expression,
        *,
        query_ref: "AQLQuery",
    ):
        super().__init__(query_ref=query_ref)
        if isinstance(variable, str):
            variable = VariableExpression(variable)

        if variable.var_name is NotSet:
            self.query_ref.__dynamic_vars__.append(variable)
        else:
            self.query_ref.__used_vars__.add(variable.var_name)

        if isinstance(expression, QueryExpression):
            expression._parent = self.query_ref
            self._is_query = True

        if isinstance(expression, list):
            expression = ListExpression(expression)

        if isinstance(expression, dict):
            expression = ObjectExpression(expression)

        self.expression = AssignmentExpression(variable, expression)

    def compile(self, *args, **kwargs):
        return f"LET {self.expression.compile(self.query_ref)}"

    def __repr__(self):
        return f"LET {repr(self.expression)}"


class FilterOperation(Operation):
    def __init__(self, condition: "LogicalExpression", query_ref: "AQLQuery"):
        super().__init__(query_ref=query_ref)
        self.condition = condition

    def compile(self):
        return f"FILTER {self.condition.compile(self.query_ref)}"

    def __repr__(self):
        return f"FILTER {repr(self.condition)}"


SortParams = Union[SortExpression, tuple[FieldExpression, SortDirection]]


class SortOperation(Operation):
    def __init__(self, *sort_list: SortParams, query_ref: "AQLQuery"):
        super().__init__(query_ref=query_ref)
        self.query_ref = query_ref
        self.sort_list = sort_list

    def compile(self, *args, **kwargs) -> str:
        return f"SORT {', '.join(i.compile(self.query_ref) for i in self.sort_list)}"

    def __repr__(self):
        return f"SORT {', '.join(repr(i) for i in self.sort_list)}"


class ReturnOperation(Operation):
    def __init__(self, return_expr: ReturnableMixin, query_ref: "AQLQuery", *, distinct=None):
        super().__init__(query_ref=query_ref)

        if isinstance(return_expr, CollectionExpression):
            return_expr = return_expr.iterator

        elif isinstance(return_expr, list):
            for i in return_expr:
                if not isinstance(i, FieldExpression):
                    raise "Not Field"
        elif isinstance(return_expr, Mapping):
            return_expr = ObjectExpression(return_expr)

        self.distinct = distinct
        self.return_expr = return_expr
        self.query_ref = query_ref

    def compile(self, *args, **kwargs):
        start = "RETURN"
        if self.distinct:
            start += " DISTINCT"

        return f"{start} {self.return_expr.compile(self.query_ref)}"

    def __repr__(self):
        start = "RETURN"
        if self.distinct:
            start += " DISTINCT"
        return f"{start} {repr(self.return_expr)}"


class LimitOperation(Operation):
    def __init__(
        self,
        limit: int,
        query_ref: "AQLQuery",
        offset=None,
    ):
        super().__init__(query_ref=query_ref)
        self.offset = offset
        self.limit = limit

    def compile(self, *args, **kwargs):
        if self.offset:
            return f"LIMIT {self.offset},{self.limit}"
        else:
            return f"LIMIT {self.limit}"

    def __repr__(self):
        return f"LIMIT {self.limit}"


class InsertOperation(Operation):
    def __init__(self, doc, collection, query_ref: "AQLQuery"):
        super().__init__(query_ref=query_ref)
        if isinstance(doc, dict):
            doc = ObjectExpression(doc)
        if isinstance(collection, str):
            collection = CollectionExpression(collection)
        self.collection = collection
        self.doc = doc

    def compile(self, *args, **kwargs):
        return f"INSERT {self.doc.compile(self.query_ref)} INTO {self.collection.compile(self.query_ref)}"

    def __repr__(self):
        return f"INSERT {repr(self.doc)} INTO {repr(self.collection)}"


class RemoveOperation(Operation):
    def __init__(self, expression, collection, *, options: RemoveOptions, query_ref: "AQLQuery"):
        super().__init__(query_ref=query_ref)
        self.options = options

        if isinstance(expression, dict):
            expression = ObjectExpression(expression)
        if isinstance(expression, str):
            expression = LiteralExpression(expression)
        if isinstance(collection, str):
            collection = CollectionExpression(collection)
        self.expression = expression
        self.collection = collection

    def compile(self, *args, **kwargs):
        compiled = f"REMOVE {self.expression.compile(self.query_ref)} IN {self.collection.compile(self.query_ref)}"
        if self.options:
            options_compile = self.options.compile()
            compiled += options_compile and f"OPTIONS {options_compile}"
        return compiled

    def __repr__(self):
        _repr = f"REMOVE {repr(self.expression)} IN {repr(self.collection)}"
        if self.options:
            options_compile = self.options.compile()
            _repr += options_compile and f"OPTIONS {options_compile}"
        return _repr


class UpdateOperation(Operation):
    def __init__(
        self,
        key: str,
        obj: Union[ObjectExpression, dict],
        collection: Union[CollectionExpression, str],
        *,
        options: Optional[UpdateOptions],
        query_ref,
    ):
        super().__init__(query_ref=query_ref)
        if isinstance(key, dict):
            key = ObjectExpression(key)
        if isinstance(obj, dict):
            obj = ObjectExpression(obj)
        if isinstance(collection, str):
            collection = CollectionExpression(collection)
        self.options = options
        self.key = key
        self.obj = obj
        self.collection = collection

    def compile(self, *args, **kwargs):
        compiled = f"UPDATE {self.obj.compile(self.query_ref)} IN {self.collection.compile(self.query_ref)}"
        if self.options:
            options_compile = self.options.compile()
            compiled += options_compile and f"OPTIONS {options_compile}"
        return compiled

    def __repr__(self):
        _repr = f"UPDATE {repr(self.obj)} IN {repr(self.collection)}"
        if self.options:
            options_compile = self.options.compile()
            _repr += options_compile and f"OPTIONS {options_compile}"
        return _repr


class ReplaceOperation(Operation):
    def __init__(
        self,
        key: str,
        obj: Union[ObjectExpression, dict],
        collection: Union[CollectionExpression, str],
        *,
        options: Optional[ReplaceOptions],
        query_ref,
    ):
        super().__init__(query_ref=query_ref)
        if isinstance(key, dict):
            key = ObjectExpression(key)
        if isinstance(obj, dict):
            obj = ObjectExpression(obj)
        if isinstance(collection, str):
            collection = CollectionExpression(collection)
        self.options = options
        self.key = key
        self.obj = obj
        self.collection = collection

    def compile(self, *args, **kwargs):
        compiled = f"REPLACE {self.obj.compile(self.query_ref)} IN {self.collection.compile(self.query_ref)}"
        if self.options:
            options_compile = self.options.compile()
            compiled += options_compile and f"OPTIONS {options_compile}"
        return compiled

    def __repr__(self):
        _repr = f"REPLACE {repr(self.obj)} IN {repr(self.collection)}"
        if self.options:
            options_compile = self.options.compile()
            _repr += options_compile and f"OPTIONS {options_compile}"
        return _repr


class UpsertOperation(Operation):
    @overload
    def __init__(
        self,
        query_ref: "AQLQuery",
        filter_: Union[ObjectExpression, dict],
        insert: Union[ObjectExpression, dict],
        update: Union[ObjectExpression, dict],
        collection: Union[CollectionExpression, str],
        options: Optional[UpsertOptions] = None,
    ):
        ...

    @overload
    def __init__(
        self,
        query_ref: "AQLQuery",
        filter_: Union[ObjectExpression, dict],
        insert: Union[ObjectExpression, dict],
        replace: Union[ObjectExpression, dict],
        collection: Union[CollectionExpression, str],
        options: Optional[UpsertOptions] = None,
    ):
        ...

    def __init__(
        self,
        query_ref: "AQLQuery",
        filter_: Union[ObjectExpression, dict],
        collection: Union[CollectionExpression, str],
        insert: Union[ObjectExpression, dict],
        update: Union[ObjectExpression, dict] = None,
        replace: Union[ObjectExpression, dict] = None,
        options: Optional[UpsertOptions] = None,
    ):
        super().__init__(query_ref)
        self.options = options
        if update and replace:
            raise ValueError("cannot set both update and replace")
        if not (update or replace):
            raise ValueError("you need to specify update or replace")
        if isinstance(replace, dict):
            replace = ObjectExpression(replace)

        if isinstance(update, dict):
            update = ObjectExpression(update)

        if isinstance(insert, dict):
            insert = ObjectExpression(insert)
        if isinstance(collection, str):
            collection = CollectionExpression(collection)

        if isinstance(filter_, dict):
            filter_ = ObjectExpression(filter_)

        self.replace = replace
        self.filter = filter_
        self.collection = collection
        self.update = update
        self.insert = insert

    def compile(self, *args, **kwargs):
        if self.update:
            modification = f"UPDATE {self.update.compile(self.query_ref)}"
        else:
            modification = f"REPLACE {self.replace.compile(self.query_ref)}"
        compiled = (
            f"UPSERT {self.filter.compile(self.query_ref)} INSERT {self.insert.compile(self.query_ref)} "
            f"{modification} IN {self.collection.compile(self.query_ref)}"
        )
        if self.options:
            options_compile = self.options.compile()
            compiled += options_compile and f"OPTIONS {options_compile}"
        return compiled

    def __repr__(self):
        if self.update:
            modification = f"UPDATE {repr(self.update)}"
        else:
            modification = f"REPLACE {repr(self.replace)}"
        _repr = f"UPSERT {repr(self.filter)} INSERT {repr(self.insert)} {modification} IN {repr(self.collection)}"

        if self.options:
            options_compile = self.options.compile()
            _repr += options_compile and f"OPTIONS {options_compile}"
        return _repr


AssignmentParam: TypeAlias = Union[AssignmentExpression, tuple[VariableExpression, Expression]]
AssignmentParams: TypeAlias = Union[AssignmentParam, Sequence[AssignmentParam]]
IntoParam = Union[
    VariableExpression,
    AssignmentExpression,
]


class CollectOperation(Operation):
    def __init__(
        self,
        *,
        collect: Optional[AssignmentParams] = None,
        aggregate: Optional[AssignmentParams] = None,
        into: Optional[Union[VariableExpression, AssignmentParam]] = None,
        keep: Optional[VariableExpression] = None,
        with_count_into: Optional[VariableExpression] = None,
        options: Optional[CollectOptions] = None,
        query_ref: "AQLQuery",
    ):
        if not any((collect, aggregate, with_count_into)):
            raise ValueError("you should use one of collect, aggregate or count")
        if aggregate:
            if with_count_into:
                raise ValueError("aggregate cannot be used in conjunction of WITH COUNT IT")
            if keep:
                raise ValueError("cannot use KEEP with aggregate")

        super().__init__(query_ref)
        if collect and not isinstance(collect, Sequence):
            collect = [collect]
        if aggregate and not isinstance(aggregate, Sequence):
            aggregate = [aggregate]

        for param in [collect or [], aggregate or []]:
            for i, assignment in enumerate(param):
                if isinstance(assignment, tuple):
                    collect[i] = AssignmentExpression(assignment[0], assignment[1])
                if assignment.variable.var_name is NotSet:
                    self.query_ref.__dynamic_vars__.append(assignment.variable)
                else:
                    self.query_ref.__used_vars__.add(assignment.variable.var_name)
        for param in [into or [], with_count_into or []]:
            if isinstance(param, VariableExpression):
                if param.var_name is NotSet:
                    self.query_ref.__dynamic_vars__.append(param)
                else:
                    self.query_ref.__used_vars__.add(param.var_name)
            elif isinstance(param, AssignmentExpression):
                if into.variable.var_name is NotSet:
                    self.query_ref.__dynamic_vars__.append(param.variable)
                else:
                    self.query_ref.__used_vars__.add(param.variable.var_name)

                if isinstance(param.expression, ObjectExpression):
                    # TODO: handle object
                    pass

                elif isinstance(param.expression, ListExpression):
                    # TODO: handle list
                    pass

        self.collect = collect
        self.aggregate = aggregate
        self.into = into
        self.keep = keep
        self.with_count_into = with_count_into
        self.options = options

        params = [collect, aggregate, into, keep, with_count_into]
        keywords = ["COLLECT", "AGGREGATE", "INTO", "KEEP", "WITH COUNT INTO"]
        self.to_compile = [i for i in list(zip(keywords, params))[2:] if i[1] is not None]

    def compile(self):
        compiled = self.collect and f"COLLECT {', '.join(i.compile(self.query_ref) for i in self.collect)}" or "COLLECT"
        agg = self.aggregate and f"AGGREGATE {', '.join(i.compile(self.query_ref) for i in self.aggregate)}" or None
        compiled = agg and " ".join((compiled, agg)) or compiled

        to_compile = " ".join([f"{k} {v.compile(self.query_ref)}" for k, v in self.to_compile])
        return f"{compiled}" + (to_compile and f" {to_compile}" or "")

    def __repr__(self):
        compiled = self.collect and f"COLLECT {', '.join(repr(i) for i in self.collect)}" or "COLLECT"
        agg = self.aggregate and f"AGGREGATE {', '.join(repr(i) for i in self.aggregate)}" or None
        compiled = agg and " ".join((compiled, agg)) or compiled

        to_compile = " ".join([f"{k} {repr(v)}" for k, v in self.to_compile])
        return f"{compiled}" + (to_compile and f" {to_compile}" or "")


class WindowOperation(Operation):
    def compile(self, *args, **kwargs):
        # TODO
        pass

    ...


class WithOperation(Operation):
    def compile(self, *args, **kwargs):
        # TODO
        pass

    ...
