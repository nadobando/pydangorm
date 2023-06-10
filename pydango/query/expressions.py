import datetime
from abc import ABC
from copy import deepcopy
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence, Type, Union

try:
    from typing import TypeAlias  # type: ignore[attr-defined]
except ImportError:
    from typing_extensions import TypeAlias

from pydango.query.utils import Compilable, SortDirection

if TYPE_CHECKING:
    from pydango.query.query import AQLQuery


class _NotSet:
    _name__ = "DynamicAlias"

    def __repr__(self):
        return f"{self._name__}:{id(self)}"

    def __str__(self):
        return self._name__


NotSetCls = _NotSet
NotSet = NotSetCls()


class ReturnableMixin(Compilable, ABC):
    """
    Base class for returnable expressions
    """


class Expression(Compilable):
    # def __add__(self, other: Union["Expression", int, float, str]) -> "ArithmeticExpression":
    # return ArithmeticExpression(self, "+", to_expression(other))
    ##
    # def __sub__(self, other: Union["Expression", int, float, str]) -> "ArithmeticExpression":
    # return ArithmeticExpression(self, "-", to_expression(other))
    ##
    # def __mul__(self, other: Union["Expression", int, float, str]) -> "ArithmeticExpression":
    # return ArithmeticExpression(self, "*", to_expression(other))
    ##
    # def __truediv__(self, other: Union["Expression", int, float, str]) -> "ArithmeticExpression":
    # return ArithmeticExpression(self, "/", to_expression(other))
    ##
    # def __floordiv__(self, other: Union["Expression", int, float, str]) -> "ArithmeticExpression":
    # return ArithmeticExpression(self, "//", to_expression(other))
    ##
    # def __mod__(self, other: Union["Expression", int, float, str]) -> "ArithmeticExpression":
    # return ArithmeticExpression(self, "%", to_expression(other))
    ##
    # def __lt__(self, other: Union["Expression", int, float, str]) -> "LogicalExpression":
    # return LogicalExpression(self, "<", to_expression(other))
    ##
    # def __le__(self, other: Union["Expression", int, float, str]) -> "LogicalExpression":
    # return LogicalExpression(self, "<=", to_expression(other))
    ##
    # def __eq__(self, other: Union["Expression", int, float, str, bool, None]) -> "LogicalExpression":
    # return LogicalExpression(self, "==", to_expression(other))
    ##
    # def __ne__(self, other: Union["Expression", int, float, str, bool, None]) -> "LogicalExpression":
    # return LogicalExpression(self, "!=", to_expression(other))
    ##
    # def __gt__(self, other: Union["Expression", int, float, str]) -> "LogicalExpression":
    # return LogicalExpression(self, ">", to_expression(other))
    ##
    # def __ge__(self, other: Union["Expression", int, float, str]) -> "LogicalExpression":
    # return LogicalExpression(self, ">=", to_expression(other))
    ##
    # def __and__(self, other: Union["Expression", int, float, str]) -> "LogicalExpression":
    # return LogicalExpression(self, "&&", to_expression(other))
    ##
    # def __or__(self, other: Union["Expression", int, float, str]) -> "LogicalExpression":
    # return LogicalExpression(self, "||", to_expression(other))
    ##
    # def __invert__(self) -> "UnaryExpression":
    # return UnaryExpression("NOT", self)
    ##
    # def __neg__(self) -> "UnaryExpression":
    # return UnaryExpression("-", self)
    ##
    # def __pos__(self) -> "UnaryExpression":
    # return UnaryExpression("+", self)

    # def __str__(self) -> str:
    #     return self.compile()

    def compile(self, query_ref: "AQLQuery") -> str:
        raise NotImplementedError

    def __deepcopy__(self, memodict={}):
        return self


class LiteralExpression(Expression):
    def __init__(self, value: Any) -> None:
        self.value = value

    def compile(self, query_ref: "AQLQuery") -> str:
        return query_ref.bind_parameter(self)

    def __repr__(self):
        return "?"


class VariableExpression(Expression, ReturnableMixin):
    def __init__(self, var_name: Optional[str] = None):
        self.var_name = var_name or NotSet

    def compile(self, query_ref: "AQLQuery") -> str:
        if isinstance(self.var_name, _NotSet):
            self.var_name = query_ref.bind_variable()

        return self.var_name

    def __repr__(self):
        return str(self.var_name)

    def __getattr__(self, item):
        if item in self.__dict__:
            return getattr(self, item)
        else:
            return FieldExpression(item, self)

    def __getitem__(self, item):
        return FieldExpression(item, self)
        # self.subs = item
        # return self


class ModificationVariable(VariableExpression, ABC):
    _keyword = None

    def compile(self, query_ref: "AQLQuery") -> str:
        if not query_ref._is_modification_query:
            raise AssertionError(f"no modification operation defined to use {self._keyword} keyword")

        return self._keyword

    def __repr__(self):
        return self._keyword

    def __getattr__(self, item):
        if item in self.__dict__:
            return getattr(self, item)
        else:
            return FieldExpression(item, self)


class NEW(ModificationVariable):
    _keyword = "NEW"


class OLD(ModificationVariable):
    _keyword = "OLD"


# noinspection PyTypeChecker
class FieldExpression(Expression, ReturnableMixin):
    """
    Expression class for field access of objects and documents
    """

    def __init__(self, field: Union[str, Expression], parent: VariableExpression = None):
        self.parent = parent
        self.field = field

    def compile(self, query_ref: "AQLQuery") -> str:
        if isinstance(self.field, Expression):
            return f"{self.parent.compile(query_ref)}[{self.field.compile(query_ref)}]"
        if isinstance(self.field, int):
            return f"{self.parent.compile(query_ref)}[{self.field}]"
        else:
            return f"{self.parent.compile(query_ref)}.{self.field}"

    def __getattr__(self, item):
        return FieldExpression(item, self)

    def __repr__(self):
        return f"{repr(self.parent)}.{str(self.field)}"

    def __pos__(self) -> "SortExpression":
        return SortExpression(self, SortDirection.ASC)

    def __neg__(self) -> "SortExpression":
        return SortExpression(self, SortDirection.DESC)

    def __eq__(self, other) -> "ConditionExpression":
        return _set_operator(self, "==", other, ConditionExpression)

    def __ge__(self, other) -> "ConditionExpression":
        return _set_operator(self, ">=", other, ConditionExpression)

    def __gt__(self, other) -> "ConditionExpression":
        return _set_operator(self, ">", other, ConditionExpression)

    def __le__(self, other) -> "ConditionExpression":
        return _set_operator(self, "<=", other, ConditionExpression)

    def __lt__(self, other) -> "ConditionExpression":
        return _set_operator(self, "<", other, ConditionExpression)

    def __mul__(self, other) -> "ArithmeticExpression":
        return _set_operator(self, "*", other, ArithmeticExpression)

    def __sub__(self, other) -> "ArithmeticExpression":
        return _set_operator(self, "-", other, ArithmeticExpression)

    def __add__(self, other) -> "ArithmeticExpression":
        return _set_operator(self, "+", other, ArithmeticExpression)

    def __truediv__(self, other) -> "ArithmeticExpression":
        return _set_operator(self, "/", other, ArithmeticExpression)

    def __mod__(self, other) -> "ArithmeticExpression":
        return _set_operator(self, "%", other, ArithmeticExpression)


class IteratorExpression(VariableExpression):
    def __repr__(self):
        return f"<Iterator: {str(self.var_name)} {id(self)}>"

    def __getattr__(self, item):
        if item in self.__dict__:
            return getattr(self, item)
        else:
            return FieldExpression(item, self)

    def __gt__(self, other):
        return _set_operator(self, ">", other, ConditionExpression)

    def __ge__(self, other) -> "ConditionExpression":
        return _set_operator(self, ">=", other, ConditionExpression)

    def __lt__(self, other):
        return _set_operator(self, "<", other, ConditionExpression)

    def __le__(self, other) -> "ConditionExpression":
        return _set_operator(self, "<=", other, ConditionExpression)

    def __eq__(self, other):
        return _set_operator(self, "==", other, ConditionExpression)

    def __ne__(self, other):
        return _set_operator(self, "!=", other, ConditionExpression)

    def __mul__(self, other) -> "ArithmeticExpression":
        return _set_operator(self, "*", other, ArithmeticExpression)

    def __sub__(self, other) -> "ArithmeticExpression":
        return _set_operator(self, "-", other, ArithmeticExpression)

    def __add__(self, other) -> "ArithmeticExpression":
        return _set_operator(self, "+", other, ArithmeticExpression)

    def __truediv__(self, other) -> "ArithmeticExpression":
        return _set_operator(self, "/", other, ArithmeticExpression)

    def __mod__(self, other) -> "ArithmeticExpression":
        return _set_operator(self, "%", other, ArithmeticExpression)


class IterableExpression(Expression, ABC):
    """
    Base class for iterable expressions
    """

    def __init__(self, iterator: Optional[Union[IteratorExpression, str]] = None):
        if iterator is None or iterator is NotSet:
            self.iterator = IteratorExpression()
        elif isinstance(iterator, str):
            self.iterator = IteratorExpression(iterator)
        else:
            self.iterator = iterator


class AssignmentExpression(Expression):
    def __init__(self, variable: VariableExpression, expression: Expression):
        self.variable = variable
        self.expression = expression
        self._is_query = isinstance(self.expression, QueryExpression) and True or False

    def compile(self, query_ref: "AQLQuery"):
        expression_compile = self.expression.compile(query_ref)
        if self._is_query:
            self.expression._parent = query_ref
            expression_compile = f"({expression_compile})"
        return f"{self.variable.compile(query_ref)} = {expression_compile}"

    def __repr__(self):
        expression_repr = repr(self.expression)
        if self._is_query:
            expression_repr = f"({expression_repr})"
        return f"{repr(self.variable)} = {expression_repr}"


class UnaryExpression(Expression, ReturnableMixin):
    """
    Expression class for unary operations
    """

    def __init__(self, operand: Expression, operator: str):
        self.operand = operand
        self.operator = operator

    def compile(self) -> str:
        return f"{self.operator}({self.operand.compile()})"


class BinaryExpression(Expression, ReturnableMixin):
    """
    Expression class for binary operations
    """

    def __init__(self, op: str, left: Expression, right: Expression) -> None:
        self.left = left
        self.op = op
        self.right = right

    @lru_cache(maxsize=1)
    def compile(self, query_ref: "AQLQuery") -> str:
        left_compile = self.left.compile(query_ref)
        right_compile = self.right.compile(query_ref)
        return f"{left_compile} {self.op} {right_compile}"

    def __repr__(self):
        return f"{self.left} {self.op} {self.right}"


class LogicalExpression(Expression, ReturnableMixin, ABC):
    """
    Base class for logical expressions
    """


class UnaryLogicalExpression(UnaryExpression, LogicalExpression):
    pass


class ConditionExpression(BinaryExpression, LogicalExpression):
    """
    valid operators >, >=, ==, !=, <, <=
    """

    def __repr__(self):
        return f"{str(self.left)} {self.op} {str(self.right)}"

    def __and__(self, other):
        return AndExpression(self, other)

    def __or__(self, other):
        return OrExpression(self, other)


class BinaryLogicalExpression(ConditionExpression):
    """
    Expression class for binary logical operations
    valid operators &&, AND, ||, OR
    """

    @lru_cache(maxsize=1)
    def compile(self, query_ref: "AQLQuery") -> str:
        return f"({self.left.compile(query_ref)} {self.op} {self.right.compile(query_ref)})"


class AndExpression(BinaryLogicalExpression):
    """
    Expression class for binary logical operations
    valid operators &&, AND, ||, OR
    """

    def __init__(self, left: Expression, right: Expression):
        super().__init__("&&", left, right)


class OrExpression(BinaryLogicalExpression):
    """
    Expression class for binary logical operations
    valid operators &&, AND, ||, OR
    """

    def __init__(self, left: Expression, right: Expression):
        super().__init__("||", left, right)


class In(ConditionExpression):
    def __init__(self, obj: LiteralExpression, iterable: IterableExpression):
        super().__init__("IN", obj, iterable)


class BaseArithmeticExpression(Expression, ReturnableMixin, ABC):
    """
    Base class for arithmetic expressions
    """


class UnaryArithmeticExpression(UnaryExpression, BaseArithmeticExpression):
    ...


class ArithmeticExpression(BinaryExpression, BaseArithmeticExpression):
    def __lt__(self, other):
        return ConditionExpression("<", self, other)

    def __le__(self, other):
        return ConditionExpression("<=", self, other)

    def __gt__(self, other):
        return ConditionExpression(">", self, other)

    def __ge__(self, other):
        return ConditionExpression(">=", self, other)

    def __eq__(self, other):
        return ConditionExpression("==", self, other)

    def __hash__(self):
        return id(self)


class ReturnableIterableExpression(IterableExpression, ReturnableMixin, ABC):
    def __init__(self, iterator):
        super().__init__(iterator)


class QueryExpression(Expression, ABC):
    _parent: "QueryExpression" = None
    sep = " "


class SubQueryExpression(Expression, ReturnableMixin):
    def __init__(self, query: QueryExpression):
        self.query = query

    def __repr__(self):
        if self.query.sep == "\n":
            return f"({repr(self.query)})"
        return f"({repr(self.query)})"

    def compile(self, query_ref) -> str:
        if self.query.sep == "\n":
            return f"(\t{self.query.compile()})"
        return f"({self.query.compile()})"


class ScalarSubQuery(SubQueryExpression):
    ...


class VectorSubQueryExpression(SubQueryExpression, IterableExpression):
    def __init__(self, query: "AQLQuery"):
        super().__init__(query)
        super(SubQueryExpression, VectorSubQueryExpression).__init__(IteratorExpression())
        if self.query.sep == "\n":
            self.query.sep = f"{self.query.sep}\t"


class CollectionExpression(IterableExpression):
    """
    class for marking array expressions which can be used:
     in FOR:
      (FOR {var} IN CollectionExpression)
    """

    def __init__(self, collection_name: str, iterator: Union[str, IteratorExpression] = None):
        super().__init__(iterator)
        self.collection_name = collection_name

    def __repr__(self):
        return f"<CollectionExpression: {str(self.collection_name)}>"

    def __getattr__(self, item) -> Union[Any, FieldExpression]:
        if item in self.__dict__:
            return getattr(self, item)
        else:
            return getattr(self.iterator, item)

    def compile(self, *args, **kwargs) -> str:
        return f"`{self.collection_name}`"


class FigurativeExpression(Expression, ReturnableMixin, ABC):
    def __init__(self, value: Any) -> None:
        self.value = value

    def compile(self, query_ref: "AQLQuery") -> str:
        return query_ref.bind_parameter(self)


ListValues: TypeAlias = tuple[
    Union[
        QueryExpression,
        LiteralExpression,
        FigurativeExpression,
        Mapping,
        Sequence,
        int,
        float,
        str,
        bool,
    ],
    ...,
]


class ListExpression(FigurativeExpression, IterableExpression):
    def __init__(self, value: ListValues, iterator: Union[IteratorExpression, str] = None):
        super().__init__(value)
        super(FigurativeExpression, self).__init__(iterator)
        self._copy: list[Expression] = []
        self._need_compile = False
        for i in self.value:
            if isinstance(i, QueryExpression):
                self._copy.append(SubQueryExpression(i))
                self._need_compile = True
            elif isinstance(i, VariableExpression):
                self._copy.append(i)
                self._need_compile = True
            elif isinstance(i, Expression):
                self._copy.append(i)
            elif isinstance(i, list):  # todo review this
                self._copy.append(ListExpression(i))
                self._need_compile = True
            elif isinstance(i, dict):
                expression = ObjectExpression(i)
                self._copy.append(expression)
                self._need_compile = not expression._all_literals or self._need_compile
            else:
                self._copy.append(LiteralExpression(i))

    def compile(self, query_ref: "AQLQuery", **kwargs) -> str:
        if self._need_compile:
            result = []
            for i in self._copy:
                if isinstance(i, SubQueryExpression):
                    i.query._parent = query_ref
                result.append(i.compile(query_ref))
            return f'[{", ".join(result)}]'

        return super().compile(query_ref)

    def __repr__(self):
        if self._need_compile:
            result = []
            for i in self._copy:
                result.append(repr(i))
            return f'[{", ".join(result)}]'

        return "?"


ObjectKeys = Union[str, VariableExpression, CollectionExpression, IteratorExpression]

ObjectValues = Union[
    LiteralExpression, FigurativeExpression, FieldExpression, Mapping, Sequence, int, float, str, bool, None
]

ObjectParams: TypeAlias = Mapping[
    ObjectKeys,
    ObjectValues,
]


class ObjectExpression(FigurativeExpression):
    def __init__(self, value: ObjectParams, parent: Optional[Union[VariableExpression, CollectionExpression]] = None):
        super().__init__(value)
        self.parent = parent
        self._bind = {}
        self._all_literals = True
        if isinstance(value, dict):
            self.value = deepcopy(value)
            for field, mapped_field in self.value.items():
                if isinstance(mapped_field, list):
                    self.value[field] = ListExpression(mapped_field)
                    self._all_literals = False
                elif isinstance(mapped_field, dict):
                    self.value[field] = ObjectExpression(mapped_field, self.parent)
                    self._all_literals = False

                elif isinstance(mapped_field, QueryExpression):
                    subquery = SubQueryExpression(mapped_field)
                    self.value[field] = subquery
                    self._bind[mapped_field] = subquery
                    self._all_literals = False
                elif isinstance(mapped_field, (VariableExpression, FieldExpression)):
                    self._all_literals = False
                elif (
                    isinstance(mapped_field, (int, float, str, bool, datetime.datetime, datetime.date))
                    or mapped_field is None
                ):
                    self.value[field] = LiteralExpression(mapped_field)

    def compile(self, query_ref: "AQLQuery") -> str:
        # if self._all_literals:
        #     return super().compile(query_ref)
        for bind in self._bind.values():
            bind.query._parent = query_ref

        pairs = []

        # if isinstance(self.value, list):
        #     for field in self.value:
        #         pairs.append(f"{field}: {self.parent.compile(query_ref)}.{field}")
        if isinstance(self.value, dict):
            for field, mapped_field in self.value.items():
                pairs.append(f"{field}: {mapped_field.compile(query_ref)}")

        return f"{{{', '.join(pairs)}}}"

    def __repr__(self):
        pairs = []
        # if isinstance(self.value, list):
        #     for field in self.value:
        #         pairs.append(f"{field}: {self.parent}.{field}")
        if isinstance(self.value, dict):
            for field, mapped_field in self.value.items():
                pairs.append(f"{field}: {mapped_field}")
        return f"{{{', '.join(pairs)}}}"


class BaseAQLVariableExpressionMixin:
    ...


class AQLVariableExpression(BaseAQLVariableExpressionMixin):
    def __init__(self, var_name: str):
        super().__init__(var_name)

    def compile(self, *args, **kwargs) -> str:
        return f"@{super().compile(*args, **kwargs)}"


class AQLCollectionVariableExpression(BaseAQLVariableExpressionMixin):
    def compile(self, *args, **kwargs) -> str:
        return f"@@{super().compile(*args, **kwargs)}"


def _set_operator(self, operator, other, cls: Type[BinaryExpression]) -> BinaryExpression:
    if not isinstance(other, Expression):
        other = LiteralExpression(other)
    return cls(operator, self, other)


class SortExpression(Expression):
    def __init__(self, field: FieldExpression, direction: SortDirection):
        self.field = field
        self.direction = direction

    def compile(self, query_ref: "AQLQuery") -> str:
        return f"{self.field.compile(query_ref)} {self.direction.value}"

    def __repr__(self):
        if hasattr(self, "field") and hasattr(self, "direction"):
            return f"{self.field} {self.direction}"
        return super().__repr__()

    def __invert__(self):
        if self.direction == SortDirection.ASC:
            self.direction = SortDirection.DESC
        else:
            self.direction = SortDirection.ASC
