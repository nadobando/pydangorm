from pydantic.fields import (
    SHAPE_FROZENSET,
    SHAPE_ITERABLE,
    SHAPE_LIST,
    SHAPE_SEQUENCE,
    SHAPE_SET,
    SHAPE_TUPLE_ELLIPSIS,
)

LIST_SHAPES = {
    SHAPE_LIST,
    SHAPE_TUPLE_ELLIPSIS,
    SHAPE_SEQUENCE,
    SHAPE_SET,
    SHAPE_FROZENSET,
    SHAPE_ITERABLE,
}