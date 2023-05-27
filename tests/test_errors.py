import pytest

from pydango.query.expressions import CollectionExpression
from pydango.query.query import AQLQuery


def test_invalid_for_expression():
    with pytest.raises(AssertionError):
        AQLQuery().for_(
            "users"
        )  # should raise TypeError since the expression should be an instance of CollectionExpression or IteratorExpression


def test_duplicate_iterator_alias():
    coll1 = CollectionExpression("users", "u")
    coll2 = CollectionExpression("posts", "u")
    with pytest.raises(ValueError):
        AQLQuery().for_(coll1).for_(
            coll2
        )  # should raise ValueError since the iterator alias "u" is already used in the first FOR clause


# def test_missing_return_expression():
#     coll = CollectionExpression("users", "u")
#     with pytest.raises(ValueError):
#         AQLQuery().for_(coll).compile()  # should raise ValueError since no RETURN clause is defined in the query
