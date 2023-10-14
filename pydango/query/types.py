import sys
from typing import TYPE_CHECKING, Union

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from pydango.query.expressions import RangeExpression

Range: TypeAlias = Union["RangeExpression", range, tuple[int, int]]
