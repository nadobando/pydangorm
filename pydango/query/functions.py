import json
from typing import TYPE_CHECKING, Optional, Union

from pydango.query.expressions import (
    Expression,
    IterableExpression,
    ListExpression,
    LiteralExpression,
    ObjectExpression,
    QueryExpression,
)

if TYPE_CHECKING:
    from pydango.query import AQLQuery


class BaseFunctionExpression(Expression):
    returns = None

    def __init__(self, name, *arguments):
        self.name = name
        arguments = list(arguments)

        for i, arg in enumerate(arguments):
            if isinstance(arg, dict):
                arguments[i] = ObjectExpression(arg)
            if isinstance(arg, list):
                arguments[i] = ListExpression(arg)

        self.arguments = arguments

    def compile(self, query_ref: "AQLQuery") -> str:
        arguments = []
        for arg in self.arguments:
            if isinstance(arg, QueryExpression):
                arg._parent = query_ref

            if isinstance(arg, Expression):
                value = arg.compile(query_ref)
            elif isinstance(arg, (int, float, str, bool)):
                value = json.dumps(arg)
            else:
                value = arg
            arguments.append(value)

        return f"{self.name}({', '.join(arguments)})"

    def __repr__(self) -> str:
        arguments = [repr(arg) for arg in self.arguments]
        return f"{self.name}({', '.join(arguments)})"


class FunctionExpression(BaseFunctionExpression):
    name = None

    def __init__(self, *arguments):
        if not isinstance(self.name, str):
            raise ValueError("function name not defined")
        super().__init__(self.name, *arguments)


# document
class Unset(FunctionExpression):
    name = "UNSET"

    def __init__(self, collection, *fields):
        fields = list(fields)
        for i, field in enumerate(fields):
            if not isinstance(field, LiteralExpression):
                fields[i] = LiteralExpression(field)
        super().__init__(collection, *fields)


class Merge(
    FunctionExpression,
    ObjectExpression,
):
    name = "MERGE"

    def __init__(self, *objects):
        objects_ = []
        for o in objects:
            if isinstance(o, dict):
                objects_.append(ObjectExpression(o))
            else:
                objects_.append(o)
        super().__init__(*objects_)


class Has(FunctionExpression):
    name = "HAS"

    def __init__(self, collection: str, attr: str):
        super().__init__(collection, attr)


class Zip(FunctionExpression):
    name = "ZIP"


# aggs
class Sum(FunctionExpression):
    name = "SUM"


class Length(FunctionExpression):
    name = "LENGTH"
    further = ""

    def __sub__(self, other):
        self.further = f" - {other}"
        return self

    def __add__(self, other):
        self.further = f" + {other}"
        return self

    def compile(self, query_ref: "AQLQuery") -> str:
        return super().compile(query_ref) + self.further


class CollectionsExpression(FunctionExpression):
    name = "COLLECTIONS"

    def __init__(self):
        super().__init__()


# strings
class RegExMatch(FunctionExpression):
    name = "REGEX_MATCHES"

    def __init__(
        self,
        string,
        pattern,
        case_insensitive: bool,
    ):
        super().__init__(string, pattern, case_insensitive)


# arrays
class ReturnsArray(IterableExpression):
    pass


class Append(FunctionExpression):
    name = "APPEND"

    def __init__(self, array, value):
        super().__init__(array, value)


class Concat(FunctionExpression, ReturnsArray):
    name = "CONCAT"

    def __init__(self, *arrays):
        super().__init__(*arrays)


class Count(FunctionExpression):
    name = "COUNT"

    def __init__(self, array):
        super().__init__(array)


class CountDistinct(FunctionExpression):
    name = "COUNT_DISTINCT"

    def __init__(self, array):
        super().__init__(array)


CountUnique = CountDistinct


class First(FunctionExpression):
    name = "FIRST"

    def __init__(self, array):
        super().__init__(array)


class Flatten(FunctionExpression):
    name = "FLATTEN"

    def __init__(self, array):
        super().__init__(array)


class Interleave(FunctionExpression):
    name = "INTERLEAVE"

    def __init__(self, *array):
        super().__init__(*array)


class Jaccard(FunctionExpression):
    name = "JACCARD"

    def __init__(self, array1, array2):
        super().__init__(array1, array2)


class Last(FunctionExpression):
    name = "LAST"

    def __init__(self, array):
        super().__init__(array)


class Nth(FunctionExpression):
    name = "NTH"

    def __init__(self, array, index):
        super().__init__(array, index)


class Push(FunctionExpression):
    name = "PUSH"

    def __init__(self, array, value):
        super().__init__(array, value)


class Pop(FunctionExpression):
    name = "POP"

    def __init__(self, array):
        super().__init__(array)


class RemoveNth(FunctionExpression):
    name = "REMOVE_NTH"

    def __init__(self, array, index):
        super().__init__(array, index)


class ReplaceNth(FunctionExpression):
    name = "REPLACE_NTH"

    def __init__(self, array, index):
        super().__init__(array, index)


class RemoveValue(FunctionExpression):
    name = "REMOVE_VALUE"

    def __init__(self, array, value, limit: Optional[int] = None):
        super().__init__(array, value, limit)


class Reverse(FunctionExpression):
    name = "REVERSE"

    def __init__(self, array):
        super().__init__(array)


class Shift(FunctionExpression):
    name = "SHIFT"

    def __init__(self, array):
        super().__init__(array)


class Slice(FunctionExpression, IterableExpression):
    name = "SLICE"

    def __init__(self, array, start, count=None):
        if count is None:
            super().__init__(array, start)
        else:
            super().__init__(array, start, count)


class UnionArrays(FunctionExpression, IterableExpression):
    name = "UNION"

    def __init__(self, *arrays: Union[list, ListExpression]):
        super().__init__(*arrays)


class Difference(FunctionExpression):
    name = "DIFFERENCE"

    def __init__(self, array1, array2):
        super().__init__(array1, array2)


class Intersection(FunctionExpression):
    name = "INTERSECTION"

    def __init__(self, *arrays):
        super().__init__(*arrays)


class Outersection(FunctionExpression):
    name = "OUTERSECTION"

    def __init__(self, *array):
        super().__init__(*array)


class Minus(FunctionExpression):
    name = "MINUS"

    def __init__(self, array1, array2):
        super().__init__(array1, array2)


class Position(FunctionExpression):
    name = "POSITION"

    def __init__(self, array, value):
        super().__init__(array, value)


Contains = Position


class UnionDistinct(FunctionExpression):
    name = "UNION_DISTINCT"

    def __init__(self, *arrays):
        super().__init__(*arrays)


# bit


class BitAnd(FunctionExpression):
    name = "BIT_AND"

    def __init__(self, value1, value2):
        super().__init__(value1, value2)


class BitNot(FunctionExpression):
    name = "BIT_NOT"

    def __init__(self, value):
        super().__init__(value)


class BitOr(FunctionExpression):
    name = "BIT_OR"

    def __init__(self, value1, value2):
        super().__init__(value1, value2)


class BitXor(FunctionExpression):
    name = "BIT_XOR"

    def __init__(self, value1, value2):
        super().__init__(value1, value2)


# date


class DateAdd(FunctionExpression):
    name = "DATE_ADD"

    def __init__(self, date, amount, unit):
        super().__init__(date, amount, unit)


class DateCompare(FunctionExpression):
    name = "DATE_COMPARE"

    def __init__(self, date1, date2):
        super().__init__(date1, date2)


class DateDay(FunctionExpression):
    name = "DATE_DAY"

    def __init__(self, date):
        super().__init__(date)


class DateDayOfWeek(FunctionExpression):
    name = "DATE_DAY_OF_WEEK"

    def __init__(self, date):
        super().__init__(date)


class DateDaysInMonth(FunctionExpression):
    name = "DATE_DAYS_IN_MONTH"

    def __init__(self, date):
        super().__init__(date)


class DateDiff(FunctionExpression):
    name = "DATE_DIFF"

    def __init__(self, date1, date2, unit):
        super().__init__(date1, date2, unit)


class DateHour(FunctionExpression):
    name = "DATE_HOUR"

    def __init__(self, date):
        super().__init__(date)


class DateMilliseconds(FunctionExpression):
    name = "DATE_MILLISECONDS"

    def __init__(self, date):
        super().__init__(date)


class DateMinute(FunctionExpression):
    name = "DATE_MINUTE"

    def __init__(self, date):
        super().__init__(date)


class DateMonth(FunctionExpression):
    name = "DATE_MONTH"

    def __init__(self, date):
        super().__init__(date)


class DateNow(FunctionExpression):
    name = "DATE_NOW"

    def __init__(self):
        super().__init__()


class DateSecond(FunctionExpression):
    name = "DATE_SECOND"

    def __init__(self, date):
        super().__init__(date)


class DateSubtract(FunctionExpression):
    name = "DATE_SUBTRACT"

    def __init__(self, date, amount, unit):
        super().__init__(date, amount, unit)


class DateTimestamp(FunctionExpression):
    name = "DATE_TIMESTAMP"

    def __init__(self, date):
        super().__init__(date)


class DateYear(FunctionExpression):
    name = "DATE_YEAR"

    def __init__(self, date):
        super().__init__(date)
