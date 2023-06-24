from pydango.query.expressions import (
    CollectionExpression,
    IteratorExpression,
    ObjectExpression,
)
from pydango.query.query import AQLQuery


def simple_query(age):
    coll = CollectionExpression("users", "u")
    aql_query = AQLQuery().for_(coll).filter(coll.age > age).sort(+coll.age).return_(coll)
    return aql_query, coll


def multiple_filters_query(age, gender):
    coll = CollectionExpression("users", "u")
    aql_query = (
        AQLQuery().for_(coll).filter(coll.age > age).filter(coll.gender == gender).sort(+coll.name).return_(coll)
    )
    return aql_query, coll


def projection_complex_query(name, age):
    coll = CollectionExpression("users")
    i = IteratorExpression()
    aql = (
        AQLQuery()
        .for_(i, in_=coll)
        .filter(
            (i.name == name) & (i.age == age),
        )
        .return_(ObjectExpression({"a": i.name}, i))
    )
    return aql, coll, i


def sort_filter_query(age):
    coll1 = CollectionExpression("users", "u1")
    coll2 = CollectionExpression("users", "u2")
    aql_query = (
        AQLQuery()
        .for_(coll1)
        .filter(coll1.age > age)
        .for_(coll2)
        .filter(coll2.date > coll1.date)
        .sort(+coll1.name)
        .return_(coll1)
    )
    return aql_query, coll1, coll2


# def multiple_collections_query(age):
#     coll1 = CollectionExpression("users", "u1")
#     coll2 = CollectionExpression("orders", "o")
#     aql_query = (
#         AQLQuery()
#         .for_(coll1)
#         .filter(coll1.age > age)
#         .for_(coll2)
#         .filter(coll2.date > coll1.date)
#         .sort(+coll1.name)
#         .return_(coll1)
#     )
#     return aql_query, coll1, coll2


def insert_query(coll, doc):
    obj = ObjectExpression(doc)
    coll = CollectionExpression(coll)
    aql_query = AQLQuery().insert(obj, coll)
    return aql_query, coll, obj


def delete_query(coll, key: str):
    coll = CollectionExpression(coll)
    aql_query = AQLQuery().remove(key, coll)
    return aql_query, coll


def insert_return_new_query(coll, doc, new):
    obj = ObjectExpression(doc)
    coll = CollectionExpression(coll)
    aql_query = AQLQuery().insert(obj, coll).return_(new)
    return aql_query, coll, obj


def update_query(coll, key: str, doc):
    coll = CollectionExpression(coll)
    aql_query = AQLQuery().update(key, ObjectExpression(doc), coll)
    return aql_query, coll


def replace_query(coll, key: str, doc):
    coll = CollectionExpression(coll)
    aql_query = AQLQuery().replace(key, ObjectExpression(doc), coll)
    return aql_query, coll


def upsert_query(coll, filter_, insert=None, update=None, replace=None):
    coll = CollectionExpression(coll)
    aql_query = AQLQuery().upsert(
        ObjectExpression(filter_),
        insert=ObjectExpression(insert),
        replace=replace and ObjectExpression(replace),
        update=update and ObjectExpression(update),
        collection=coll,
    )
    return aql_query, coll
