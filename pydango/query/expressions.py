import datetime
import sys
from abc import ABC, abstractmethod
from copy import deepcopy
from enum import Enum
from functools import lru_cache
from typing import Any, Mapping, Optional, Sequence, Type, Union, cast

from pydango.query.consts import DYNAMIC_ALIAS

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias


class SortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class ReturnableExpression(ABC):
    """
    Base class for returnable expressions
    """


class Expression(ABC):
    @abstractmethod
    def compile(self, query_ref: "QueryExpression") -> str:
        raise NotImplementedError

    def __deepcopy__(self, memodict=None):
        return self


class BindableExpression(Expression):
    def __init__(self, value: Any) -> None:
        self.value = value

    def compile(self, query_ref: "QueryExpression") -> str:
        # Mypy: Argument 1 to "bind_parameter" of "AQLQuery"
        # has incompatible type "expressions.LiteralExpression";
        # expected "Union[pydango.query.expressions.LiteralExpression, FigurativeExpression]"  [arg-type]
        return query_ref.bind_parameter(self)  # type: ignore[arg-type]


class LiteralExpression(BindableExpression):
    def __repr__(self):
        return "?"


class VariableExpression(Expression, ReturnableExpression):
    def __init__(self, var_name: Optional[str] = None):
        self.var_name = var_name

    def compile(self, query_ref: "QueryExpression") -> str:
        if self.var_name is None:
            self.var_name = query_ref.bind_variable()

        return self.var_name

    def __repr__(self):
        return self.var_name or DYNAMIC_ALIAS

    def __getattr__(self, item):
        if item in self.__dict__:
            return getattr(self, item)
        else:
            return FieldExpression(item, self)

    def __getitem__(self, item):
        return FieldExpression(item, self)


class ModificationVariable(VariableExpression, ABC):
    _keyword: str

    def compile(self, query_ref: "QueryExpression") -> str:
        if not query_ref.__is_modification_query__:
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


class FieldExpression(Expression, ReturnableExpression):
    """
    Expression class for field access of objects and documents
    """

    def __init__(
        self, field: Union[str, Expression], parent: Union[VariableExpression, "FieldExpression", None] = None
    ):
        self.parent = parent
        self.field = field

    def compile(self, query_ref: "QueryExpression") -> str:
        if self.parent is None:
            raise ValueError("field parent must be populated")
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

    def __eq__(self, other) -> "ConditionExpression":  # type: ignore[override]
        return cast(ConditionExpression, _set_operator(self, "==", other, ConditionExpression))

    def __ge__(self, other) -> "ConditionExpression":
        return cast(ConditionExpression, _set_operator(self, ">=", other, ConditionExpression))

    def __gt__(self, other) -> "ConditionExpression":
        return cast(ConditionExpression, _set_operator(self, ">", other, ConditionExpression))

    def __le__(self, other) -> "ConditionExpression":
        return cast(ConditionExpression, _set_operator(self, "<=", other, ConditionExpression))

    def __lt__(self, other) -> "ConditionExpression":
        return cast(ConditionExpression, _set_operator(self, "<", other, ConditionExpression))

    def __mul__(self, other) -> "ArithmeticExpression":
        return cast(ArithmeticExpression, _set_operator(self, "*", other, ArithmeticExpression))

    def __sub__(self, other) -> "ArithmeticExpression":
        return cast(ArithmeticExpression, _set_operator(self, "-", other, ArithmeticExpression))

    def __add__(self, other) -> "ArithmeticExpression":
        return cast(ArithmeticExpression, _set_operator(self, "+", other, ArithmeticExpression))

    def __truediv__(self, other) -> "ArithmeticExpression":
        return cast(ArithmeticExpression, _set_operator(self, "/", other, ArithmeticExpression))

    def __mod__(self, other) -> "ArithmeticExpression":
        return cast(ArithmeticExpression, _set_operator(self, "%", other, ArithmeticExpression))


class IteratorExpression(VariableExpression):
    def __repr__(self):
        return f"<Iterator: {str(self.var_name or DYNAMIC_ALIAS)} {id(self)}>"

    def __getattr__(self, item):
        if item in self.__dict__:
            return getattr(self, item)
        else:
            return FieldExpression(item, self)

    def __gt__(self, other):
        return _set_operator(self, ">", other, ConditionExpression)

    def __ge__(self, other) -> "ConditionExpression":
        return cast(ConditionExpression, _set_operator(self, ">=", other, ConditionExpression))

    def __lt__(self, other):
        return _set_operator(self, "<", other, ConditionExpression)

    def __le__(self, other) -> "ConditionExpression":
        return cast(ConditionExpression, _set_operator(self, "<=", other, ConditionExpression))

    def __eq__(self, other):
        return cast(ConditionExpression, _set_operator(self, "==", other, ConditionExpression))

    def __ne__(self, other):
        return cast(ConditionExpression, _set_operator(self, "!=", other, ConditionExpression))

    def __mul__(self, other) -> "ArithmeticExpression":
        return cast(ArithmeticExpression, _set_operator(self, "*", other, ArithmeticExpression))

    def __sub__(self, other) -> "ArithmeticExpression":
        return cast(ArithmeticExpression, _set_operator(self, "-", other, ArithmeticExpression))

    def __add__(self, other) -> "ArithmeticExpression":
        return cast(ArithmeticExpression, _set_operator(self, "+", other, ArithmeticExpression))

    def __truediv__(self, other) -> "ArithmeticExpression":
        return cast(ArithmeticExpression, _set_operator(self, "/", other, ArithmeticExpression))

    def __mod__(self, other) -> "ArithmeticExpression":
        return cast(ArithmeticExpression, _set_operator(self, "%", other, ArithmeticExpression))


class IterableExpression(Expression, ReturnableExpression, ABC):
    """
    Base class for iterable expressions
    """

    # todo: move this to a more relevant place
    def __init__(self, iterator: Optional[Union[IteratorExpression, str]] = None):
        if iterator is None:
            self.iterator = IteratorExpression()
        elif isinstance(iterator, str):
            self.iterator = IteratorExpression(iterator)
        else:
            self.iterator = iterator


class QueryExpression(Expression, ABC):
    parent: Optional["QueryExpression"] = None
    sep = " "
    __used_vars__: set[str]
    __is_modification_query__: bool

    @abstractmethod
    def bind_variable(self) -> str: ...

    @abstractmethod
    def bind_parameter(self, parameter: "BindableExpression", override_var_name: Optional[str] = None) -> str: ...


class RangeExpression(IterableExpression):
    def __init__(self, start, end):
        super().__init__()
        self.end = end
        self.start = start

    def compile(self, query_ref: "QueryExpression"):
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


class AssignmentExpression(Expression):
    def __init__(self, variable: VariableExpression, expression: Expression):
        self.variable = variable
        self.expression = expression

    def compile(self, query_ref: "QueryExpression"):
        expression_compile = self.expression.compile(query_ref)
        if isinstance(self.expression, QueryExpression):
            self.expression.parent = query_ref
            expression_compile = f"({expression_compile})"
        return f"{self.variable.compile(query_ref)} = {expression_compile}"

    def __repr__(self):
        expression_repr = repr(self.expression)
        if isinstance(self.expression, QueryExpression):
            expression_repr = f"({expression_repr})"
        return f"{repr(self.variable)} = {expression_repr}"


class UnaryExpression(Expression, ReturnableExpression):
    """
    Expression class for unary operations
    """

    def __init__(self, operand: Expression, operator: str):
        self.operand = operand
        self.operator = operator

    def compile(self, query_ref: "QueryExpression") -> str:
        return f"{self.operator}({self.operand.compile(query_ref)})"


class BinaryExpression(Expression, ReturnableExpression):
    """
    Expression class for binary operations
    """

    def __init__(self, op: str, left: Expression, right: Expression) -> None:
        self.left = left
        self.op = op
        self.right = right

    @lru_cache(maxsize=1)
    def compile(self, query_ref: "QueryExpression") -> str:
        left_compile = self.left.compile(query_ref)
        right_compile = self.right.compile(query_ref)
        return f"{left_compile} {self.op} {right_compile}"

    def __repr__(self):
        return f"{self.left} {self.op} {self.right}"


class LogicalExpression(Expression, ReturnableExpression, ABC):
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
    def compile(self, query_ref: "QueryExpression") -> str:
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


class BaseArithmeticExpression(Expression, ReturnableExpression, ABC):
    """
    Base class for arithmetic expressions
    """


class UnaryArithmeticExpression(UnaryExpression, BaseArithmeticExpression): ...


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


class ReturnableIterableExpression(IterableExpression, ReturnableExpression, ABC):
    def __init__(self, iterator):
        super().__init__(iterator)


class SubQueryExpression(Expression, ReturnableExpression):
    def __init__(self, query: QueryExpression):
        self.query = query
        self.query.sep = " "

    def __repr__(self):
        if self.query.sep == "\n":
            return f"({repr(self.query)})"
        return f"({repr(self.query)})"

    def compile(self, query_ref) -> str:
        # self.query.sep = "\n"
        if self.query.sep == "\n":
            return f"({self.query.compile(query_ref)})"
        return f"({self.query.compile(query_ref)})"


class ScalarSubQuery(SubQueryExpression): ...


class VectorSubQueryExpression(SubQueryExpression, IterableExpression):
    def __init__(self, query: "QueryExpression"):
        super().__init__(query)
        super(SubQueryExpression, self).__init__(IteratorExpression())

        if self.query.sep == "\n":
            self.query.sep = f"{self.query.sep}\t"


class CollectionExpression(IterableExpression):
    def __init__(self, collection_name: str, iterator: Optional[Union[str, IteratorExpression]] = None):
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


class FigurativeExpression(BindableExpression, ReturnableExpression, ABC):
    pass


ListItems: TypeAlias = Union[
    QueryExpression, LiteralExpression, FigurativeExpression, Mapping, Sequence, int, float, str, bool
]
ListValues: TypeAlias = Union[
    tuple[
        ListItems,
        ...,
    ],
    list[ListItems],
]


class ListExpression(
    BindableExpression,
    IterableExpression,
):
    def __init__(self, value: ListValues, iterator: Optional[Union[IteratorExpression, str]] = None, brackets=True):
        if isinstance(value, list):
            value = tuple(value)

        super().__init__(value)
        super(BindableExpression, self).__init__(iterator)
        self._copy: list[Expression] = []
        self._need_compile = False
        self._brackets = brackets
        for i in self.value:
            if isinstance(i, QueryExpression):
                self._copy.append(SubQueryExpression(i))
                self._need_compile = True
            elif isinstance(i, (VariableExpression, FieldExpression)):
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
                self._need_compile = not expression.__all_literals__ or self._need_compile
            else:
                self._copy.append(LiteralExpression(i))

    def compile(self, query_ref: "QueryExpression", **kwargs) -> str:
        if self._need_compile:
            result = []
            for i in self._copy:
                if isinstance(i, SubQueryExpression):
                    i.query.parent = query_ref
                result.append(i.compile(query_ref))
            if self._brackets:
                return f'[{", ".join(result)}]'
            else:
                return ", ".join(result)

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


class ObjectExpression(BindableExpression, ReturnableExpression):
    def __init__(self, value: ObjectParams, parent: Optional[Union[VariableExpression, CollectionExpression]] = None):
        super().__init__(value)
        self.parent = parent
        self._bind = {}
        self.__all_literals__ = True
        if isinstance(value, dict):
            self.value = deepcopy(value)
            for field, mapped_field in self.value.items():
                if isinstance(mapped_field, list):
                    self.value[field] = ListExpression(mapped_field)
                    self.__all_literals__ = self.__all_literals__ or not self.value[field]._need_compile
                elif isinstance(mapped_field, dict):
                    self.value[field] = ObjectExpression(mapped_field, self.parent)
                    self.__all_literals__ = self.__all_literals__ or self.value[field].__all_literals__
                elif isinstance(mapped_field, QueryExpression):
                    subquery = SubQueryExpression(mapped_field)
                    self.value[field] = subquery
                    self._bind[mapped_field] = subquery
                    self.__all_literals__ = False
                elif isinstance(mapped_field, (VariableExpression, FieldExpression)):
                    self.__all_literals__ = False
                elif (
                    isinstance(mapped_field, (int, float, str, bool, datetime.datetime, datetime.date))
                    or mapped_field is None
                ):
                    self.value[field] = LiteralExpression(mapped_field)

    def compile(self, query_ref: "QueryExpression") -> str:
        for bind in self._bind.values():
            bind.query.parent = query_ref

        pairs = []

        if isinstance(self.value, dict):
            for field, mapped_field in self.value.items():
                if isinstance(field, Expression):
                    field = field.compile(query_ref)
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


class BaseAQLVariableExpressionMixin(Expression):
    def __init__(self, value: str):
        self.value = value


# class AQLVariableExpression(BaseAQLVariableExpressionMixin):
#     def __init__(self, var_name: str):
#         super().__init__(var_name)
#
#     def compile(self, *args, **kwargs) -> str:
#         return f"@{super().compile(*args, **kwargs)}"


class AQLCollectionVariableExpression(VariableExpression):
    def __init__(self, value: str):
        super().__init__(value)

    def compile(self, *args, **kwargs) -> str:
        return f"@@{super().compile(*args, **kwargs)}"


def _set_operator(self, operator, other, cls: Type[BinaryExpression]) -> BinaryExpression:
    if not isinstance(other, Expression):
        other = LiteralExpression(other)
    return cls(operator, self, other)


class SortExpression(Expression):
    def __init__(self, field: FieldExpression, direction: Optional[SortDirection] = None):
        self.field = field
        self.direction = direction

    def compile(self, query_ref: "QueryExpression") -> str:
        compiled = f"{self.field.compile(query_ref)}"
        if self.direction:
            compiled += f" {self.direction.value}"
        return compiled

    def __repr__(self):
        if hasattr(self, "field") and hasattr(self, "direction"):
            return f"{self.field} {self.direction}"
        return super().__repr__()

    def __invert__(self):
        if self.direction == SortDirection.ASC:
            self.direction = SortDirection.DESC
        else:
            self.direction = SortDirection.ASC


class DynamicFieldExpression(FieldExpression):
    def compile(self, query_ref: "QueryExpression") -> str:
        return f"[{super().compile(query_ref)}]"

    def __hash__(self):
        field = ""
        if self.parent:
            field += f"{self.parent}."
        field += f"{self.field}"
        return hash(field)
