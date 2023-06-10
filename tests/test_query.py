import pytest

from pydango.query.consts import DYNAMIC_ALIAS
from pydango.query.expressions import (
    NEW,
    AndExpression,
    AssignmentExpression,
    CollectionExpression,
    In,
    IteratorExpression,
    ListExpression,
    ObjectExpression,
    VariableExpression,
)
from pydango.query.functions import Sum
from pydango.query.operations import RangeExpression, TraversalDirection
from pydango.query.query import AQLQuery
from tests.queries import (  # multiple_collections_query,
    delete_query,
    insert_query,
    insert_return_new_query,
    multiple_filters_query,
    projection_complex_query,
    replace_query,
    simple_query,
    sort_filter_query,
    update_query,
    upsert_query,
)


def test_simple_query():
    param1 = 2
    aql_query, coll = simple_query(param1)
    expected_compiled = "FOR u IN `users` FILTER u.age > @param1 SORT u.age ASC RETURN u"
    repr_i = repr(coll.iterator)
    expected_repr = f"FOR {repr_i} IN {repr(coll)} FILTER {repr_i}.age > ? SORT {repr_i}.age ASC RETURN {repr_i}"
    repr_query = repr(aql_query)
    assert repr_query == expected_repr
    assert aql_query.compile() == expected_compiled
    assert aql_query.bind_vars == {"param1": param1}


def test_complex_query():
    param1 = 20
    aql_query, coll1, coll2 = sort_filter_query(param1)
    expected_compiled = (
        "FOR u1 IN `users` FILTER u1.age > @param1 FOR u2 IN `users` FILTER u2.date > u1.date SORT u1.name ASC"
        " RETURN u1"
    )
    expected_repr = (
        f"FOR {repr(coll1.iterator)} IN {repr(coll1)} "
        f"FILTER {repr(coll1.iterator)}.age > ? "
        f"FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.date > {repr(coll1.iterator)}.date "
        f"SORT {repr(coll1.iterator)}.name ASC "
        f"RETURN {repr(coll1.iterator)}"
    )
    repr_query = repr(aql_query)
    assert repr_query == expected_repr
    assert aql_query.compile() == expected_compiled
    assert aql_query.bind_vars == {"param1": param1}


def test_projection():
    param1 = 10
    param2 = 20
    aql, coll, i = projection_complex_query(param1, param2)
    expected_repr = (
        f"FOR {repr(i)} IN {repr(coll)} FILTER {repr(i)}.name == ? && {repr(i)}.age == ? RETURN {{a: {repr(i)}.name}}"
    )
    expected_compiled = "FOR var1 IN `users` FILTER (var1.name == @param1 && var1.age == @param2) RETURN {a: var1.name}"
    repr_query = repr(aql)
    assert repr_query == expected_repr
    assert aql.compile() == expected_compiled


def test_multiple_filters():
    param1 = 20
    param2 = "male"
    aql_query, coll = multiple_filters_query(param1, param2)
    expected_compiled = "FOR u IN `users` FILTER u.age > @param1 FILTER u.gender == @param2 SORT u.name ASC RETURN u"
    expected_repr = (
        f"FOR {repr(coll.iterator)} IN {repr(coll)} "
        f"FILTER {repr(coll.iterator)}.age > ? "
        f"FILTER {repr(coll.iterator)}.gender == ? "
        f"SORT {repr(coll.iterator)}.name ASC "
        f"RETURN {repr(coll.iterator)}"
    )
    repr_query = repr(aql_query)
    assert repr_query == expected_repr
    assert aql_query.compile() == expected_compiled
    assert aql_query.bind_vars == {"param1": param1, "param2": param2}


def test_subquery_in_for():
    coll = CollectionExpression("users", "u")

    subquery = AQLQuery().for_(coll).filter(coll.name == 2).sort(+coll.name).return_(coll)
    it = IteratorExpression("var1")
    aql_query = AQLQuery().for_(it, in_=subquery).filter(it.a == 10).return_(it)

    expected_repr = (
        f"FOR {repr(it)} IN (FOR {repr(coll.iterator)} IN {repr(coll)} "
        f"FILTER {repr(coll.iterator)}.name == ? "
        f"SORT {repr(coll.iterator)}.name ASC "
        f"RETURN {repr(coll.iterator)}) FILTER {repr(it)}.a == ? "
        f"RETURN {repr(it)}"
    )
    # fmt: off
    expected_compiled = (
        "FOR var1 IN (FOR u IN `users` FILTER u.name == @param1 SORT u.name ASC RETURN u) "
        "FILTER var1.a == @param2 "
        "RETURN var1"
    )
    # fmt: on

    repr_query = repr(aql_query)
    assert repr_query == expected_repr
    assert aql_query.compile() == expected_compiled
    assert aql_query.bind_vars == {"param1": 2, "param2": 10}


def test_subquery_in_filter():
    coll1 = CollectionExpression("users", "u")
    coll2 = CollectionExpression("orders", "o")

    subquery = (
        AQLQuery()
        .for_(coll2)
        .filter(AndExpression(coll2.user == coll1.id, coll2.order_status == "COMPLETED"))
        .return_(coll2.user)
    )

    aql_query = AQLQuery().for_(coll1).filter(coll1.age > 25).filter(In(coll1.id, subquery)).return_(coll1)

    expected_compiled = (
        "FOR u IN `users` FILTER u.age > @param1 FILTER u.id IN (FOR o IN `orders` "
        "FILTER (o.user == u.id && o.order_status == @param2) RETURN o.user) RETURN u"
    )

    expected_repr = (
        f"FOR {repr(coll1.iterator)} IN {repr(coll1)} "
        f"FILTER {repr(coll1.iterator)}.age > ? "
        f"FILTER {repr(coll1.iterator)}.id IN (FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.user == {repr(coll1.iterator)}.id && "
        f"{repr(coll2.iterator)}.order_status == ? "
        f"RETURN {repr(coll2.iterator)}.user) "
        f"RETURN {repr(coll1.iterator)}"
    )
    repr_query = repr(aql_query)
    assert repr_query == expected_repr
    assert aql_query.compile() == expected_compiled
    assert aql_query.bind_vars == {"param1": 25, "param2": "COMPLETED"}


def test_subquery_in_return():
    coll1 = CollectionExpression("users", "u")
    coll2 = CollectionExpression("orders", "o")
    subquery = (
        AQLQuery()
        .for_(coll2)
        .filter(AndExpression(coll2.user == coll1.id, coll2.order_status == "COMPLETED"))
        .return_(coll2.user)
    )

    aql_query = AQLQuery().for_(coll1).filter(coll1.age > 25).return_(subquery)

    expected_compiled = (
        "FOR u IN `users` FILTER u.age > @param1 RETURN (FOR o IN `orders` "
        "FILTER (o.user == u.id && o.order_status == @param2) RETURN o.user)"
    )

    expected_repr = (
        f"FOR {repr(coll1.iterator)} IN {repr(coll1)} "
        f"FILTER {repr(coll1.iterator)}.age > ? "
        f"RETURN (FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.user == {repr(coll1.iterator)}.id && "
        f"{repr(coll2.iterator)}.order_status == ? "
        f"RETURN {repr(coll2.iterator)}.user)"
    )

    repr_query = repr(aql_query)
    assert repr_query == expected_repr
    assert aql_query.compile() == expected_compiled
    assert aql_query.bind_vars == {"param1": 25, "param2": "COMPLETED"}


def test_subquery_in_object():
    coll1 = CollectionExpression("users", "u")
    coll2 = CollectionExpression("orders", "o")

    subquery = (
        AQLQuery()
        .for_(coll2)
        .filter(AndExpression(coll2.user == coll1.id, coll2.order_status == "COMPLETED"))
        .return_(coll2.user)
    )

    aql_query = (
        AQLQuery()
        .for_(coll1)
        .filter(coll1.age > 25)
        .return_(ObjectExpression({"id": coll1.id, "completed_orders": subquery}, coll1))
    )

    expected_compiled = (
        "FOR u IN `users` FILTER u.age > @param1 "
        "RETURN {id: u.id, completed_orders: (FOR o IN `orders` "
        "FILTER (o.user == u.id && o.order_status == @param2) RETURN o.user)}"
    )

    expected_repr = (
        f"FOR {repr(coll1.iterator)} IN {repr(coll1)} "
        f"FILTER {repr(coll1.iterator)}.age > ? "
        f"RETURN {{id: {repr(coll1.iterator)}.id, "
        f"completed_orders: (FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.user == {repr(coll1.iterator)}.id && "
        f"{repr(coll2.iterator)}.order_status == ? "
        f"RETURN {repr(coll2.iterator)}.user)}}"
    )

    repr_query = repr(aql_query)
    assert repr_query == expected_repr
    assert aql_query.compile() == expected_compiled
    assert aql_query.bind_vars == {"param1": 25, "param2": "COMPLETED"}


def test_multiple_subqueries():
    coll1 = CollectionExpression("users", "u")
    coll2 = CollectionExpression("orders", "o")
    coll3 = CollectionExpression("products", "p")

    subquery1 = AQLQuery().for_(coll2).filter(coll2.user == coll1.id).return_(coll2.order_id)

    subquery2 = AQLQuery().for_(coll3).filter(In(coll3.order_id, subquery1)).return_(coll3.product_name)

    aql_query = AQLQuery().for_(coll1).filter(coll1.age > 25).return_(subquery2)

    expected_compiled = (
        "FOR u IN `users` FILTER u.age > @param1 "
        "RETURN (FOR p IN `products` "
        "FILTER p.order_id IN (FOR o IN `orders` FILTER o.user == u.id RETURN o.order_id) "
        "RETURN p.product_name)"
    )

    expected_repr = (
        f"FOR {repr(coll1.iterator)} IN {repr(coll1)} "
        f"FILTER {repr(coll1.iterator)}.age > ? "
        f"RETURN (FOR {repr(coll3.iterator)} IN {repr(coll3)} "
        f"FILTER {repr(coll3.iterator)}.order_id IN (FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.user == {repr(coll1.iterator)}.id "
        f"RETURN {repr(coll2.iterator)}.order_id) "
        f"RETURN {repr(coll3.iterator)}.product_name)"
    )

    repr_query = repr(aql_query)
    assert repr_query == expected_repr
    assert aql_query.compile() == expected_compiled
    assert aql_query.bind_vars == {"param1": 25}


def test_multiple_subqueries_with_multiple_params():
    coll1 = CollectionExpression("users", "u")
    coll2 = CollectionExpression("orders", "o")

    subquery1 = AQLQuery().for_(coll1).filter(coll1.age > 20).sort(+coll1.name).return_(coll1)

    subquery2 = AQLQuery().for_(coll2).filter(coll2.status == "completed").sort(-coll2.date).return_(coll2)

    aql_query = (
        AQLQuery()
        .for_(coll1)
        .filter(coll1.id == 1)
        .for_(coll2)
        .filter(coll2.user_id == coll1.id)
        .sort(coll2.total_amount)
        .return_(ObjectExpression({"user": coll1.name, "latest_order": subquery2, "active_users": subquery1}, coll1))
    )

    expected_compiled = (
        "FOR u IN `users` FILTER u.id == @param1 "
        "FOR o IN `orders` FILTER o.user_id == u.id "
        "SORT o.total_amount "
        "RETURN {user: u.name, latest_order: "
        "(FOR o IN `orders` FILTER o.status == @param2 "
        "SORT o.date DESC "
        "RETURN o), active_users: "
        "(FOR u IN `users` FILTER u.age > @param3 "
        "SORT u.name ASC "
        "RETURN u)}"
    )

    expected_repr = (
        f"FOR {repr(coll1.iterator)} IN {repr(coll1)} "
        f"FILTER {repr(coll1.iterator)}.id == ? "
        f"FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.user_id == {repr(coll1.iterator)}.id "
        f"SORT {repr(coll2.iterator)}.total_amount "
        f"RETURN {{user: {repr(coll1.iterator)}.name, latest_order: "
        f"(FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.status == ? "
        f"SORT {repr(coll2.iterator)}.date DESC "
        f"RETURN {repr(coll2.iterator)}), active_users: "
        f"(FOR {repr(coll1.iterator)} IN {repr(coll1)} "
        f"FILTER {repr(coll1.iterator)}.age > ? "
        f"SORT {repr(coll1.iterator)}.name ASC "
        f"RETURN {repr(coll1.iterator)})}}"
    )

    repr_query = repr(aql_query)
    assert repr_query == expected_repr
    assert aql_query.compile() == expected_compiled
    assert aql_query.bind_vars == {"param1": 1, "param2": "completed", "param3": 20}


def test_nested_return_expression():
    coll1 = CollectionExpression("users", "u")
    coll2 = CollectionExpression("orders", "o")
    coll3 = CollectionExpression("products", "p")

    param2 = "completed"
    subquery1 = AQLQuery().for_(coll2).filter(coll2.status == param2).sort(-coll2.date).return_(coll2)

    param3 = 100
    subquery2 = AQLQuery().for_(coll3).filter(coll3.price > param3).sort(-coll3.price).return_(coll3)

    param4 = ["product1", "product2", "product3"]
    param1 = 1
    aql_query = (
        AQLQuery()
        .for_(coll1)
        .filter(coll1.id == param1)
        .return_(
            ObjectExpression(
                {
                    "user": coll1.name,
                    "latest_order": subquery1,
                    "top_products": ObjectExpression(
                        {"expensive_products": subquery2, "cheap_products": param4}, coll3
                    ),
                },
                coll1,
            )
        )
    )

    expected_compiled = (
        "FOR u IN `users` FILTER u.id == @param1 "
        "RETURN {user: u.name, latest_order: "
        "(FOR o IN `orders` FILTER o.status == @param2 "
        "SORT o.date DESC "
        "RETURN o), top_products: {expensive_products: "
        "(FOR p IN `products` FILTER p.price > @param3 "
        "SORT p.price DESC "
        "RETURN p), cheap_products: @param4}}"
    )

    expected_repr = (
        f"FOR {repr(coll1.iterator)} IN {repr(coll1)} "
        f"FILTER {repr(coll1.iterator)}.id == ? "
        f"RETURN {{user: {repr(coll1.iterator)}.name, latest_order: "
        f"(FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.status == ? "
        f"SORT {repr(coll2.iterator)}.date DESC "
        f"RETURN {repr(coll2.iterator)}), top_products: {{expensive_products: "
        f"(FOR {repr(coll3.iterator)} IN {repr(coll3)} "
        f"FILTER {repr(coll3.iterator)}.price > ? "
        f"SORT {repr(coll3.iterator)}.price DESC "
        f"RETURN {repr(coll3.iterator)}), cheap_products: ?}}}}"
    )

    repr_query = repr(aql_query)
    assert repr_query == expected_repr
    assert aql_query.compile() == expected_compiled
    assert aql_query.bind_vars == {"param1": param1, "param2": param2, "param3": param3, "param4": tuple(param4)}


def test_filter_and_return():
    i = ListExpression((1, 2, 3), "i")
    aql_query = AQLQuery().for_(i).filter(i.iterator > 1).return_(i.iterator)

    expected_compiled = "FOR i IN @param1 FILTER i > @param2 RETURN i"

    expected_repr = f"FOR {repr(i.iterator)} IN ? FILTER {repr(i.iterator)} > ? RETURN {repr(i.iterator)}"

    repr_query = repr(aql_query)
    assert aql_query.compile() == expected_compiled
    assert repr_query == expected_repr
    assert aql_query.bind_vars == {"param1": (1, 2, 3), "param2": 1}


def test_subquery_in_list():
    coll = CollectionExpression("users", "u")
    param1 = 1
    param2 = 20
    param3 = 3
    subquery = AQLQuery().for_(coll).filter(coll.age > param2).return_(coll)
    i = ListExpression((param1, subquery, param3), "i")

    aql_query = AQLQuery().for_(i).filter(i.iterator > param1).return_(i.iterator)

    expected_compiled = (
        "FOR i IN [@param1, (FOR u IN `users` FILTER u.age > @param2 RETURN u), @param3] FILTER i > @param1 RETURN i"
    )

    expected_repr = (
        f"FOR {repr(i.iterator)} IN [?, (FOR {repr(coll.iterator)} IN {repr(coll)} FILTER {repr(coll.iterator)}.age > ?"
        f" RETURN {repr(coll.iterator)}), ?] FILTER {repr(i.iterator)} > ? RETURN {repr(i.iterator)}"
    )

    repr_query = repr(aql_query)
    assert aql_query.compile() == expected_compiled
    assert repr_query == expected_repr
    assert aql_query.bind_vars == {"param1": param1, "param2": param2, "param3": param3}


def test_complex_query2():
    coll1 = CollectionExpression("users", "u")
    coll2 = CollectionExpression("orders", "o")
    coll3 = CollectionExpression("products", "p")

    subquery1 = (
        AQLQuery().for_(coll2).filter(coll2.user_id == coll1.id).sort(-coll2.total_amount).limit(10).return_(coll2)
    )

    subquery2 = AQLQuery().for_(coll3).filter(coll3.order_id == coll2.id).sort(+coll3.price).limit(5).return_(coll3)

    aql_query = (
        AQLQuery()
        .for_(coll1)
        .filter(coll1.age > 25)
        .filter(coll1.gender == "male")
        .for_(coll2)
        .filter(coll2.date >= "2023-01-01")
        .sort(-coll2.date)
        .limit(100)
        .return_(ObjectExpression({"user": coll1.name, "top_orders": subquery1, "products": subquery2}, coll1))
    )

    expected_compiled = (
        "FOR u IN `users` FILTER u.age > @param1 FILTER u.gender == @param2 "
        "FOR o IN `orders` FILTER o.date >= @param3 SORT o.date DESC LIMIT 100 "
        "RETURN {user: u.name, top_orders: (FOR o IN `orders` FILTER o.user_id == u.id "
        "SORT o.total_amount DESC LIMIT 10 RETURN o), products: (FOR p IN `products` "
        "FILTER p.order_id == o.id SORT p.price ASC LIMIT 5 RETURN p)}"
    )

    expected_repr = (
        f"FOR {repr(coll1.iterator)} IN {repr(coll1)} "
        f"FILTER {repr(coll1.iterator)}.age > ? FILTER {repr(coll1.iterator)}.gender == ? "
        f"FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.date >= ? SORT {repr(coll2.iterator)}.date DESC LIMIT 100 "
        f"RETURN {{user: {repr(coll1.iterator)}.name, "
        f"top_orders: (FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.user_id == {repr(coll1.iterator)}.id "
        f"SORT {repr(coll2.iterator)}.total_amount DESC LIMIT 10 "
        f"RETURN {repr(coll2.iterator)}), "
        f"products: (FOR {repr(coll3.iterator)} IN {repr(coll3)} "
        f"FILTER {repr(coll3.iterator)}.order_id == {repr(coll2.iterator)}.id "
        f"SORT {repr(coll3.iterator)}.price ASC LIMIT 5 "
        f"RETURN {repr(coll3.iterator)})}}"
    )

    repr_query = repr(aql_query)
    assert repr_query == expected_repr
    assert aql_query.compile() == expected_compiled
    assert aql_query.bind_vars == {"param1": 25, "param2": "male", "param3": "2023-01-01"}


def test_nested_subqueries():
    coll1 = CollectionExpression("users", "u")
    coll2 = CollectionExpression("orders", "o")
    coll3 = CollectionExpression("products", "p")

    subquery1 = (
        AQLQuery().for_(coll2).filter(coll2.user_id == coll1.id).sort(-coll2.total_amount).limit(10).return_(coll2)
    )

    subquery2 = AQLQuery().for_(coll3).filter(coll3.order_id == coll2.id).sort(+coll3.price).limit(5).return_(coll3)

    subquery3 = AQLQuery().for_(coll2).filter(coll2.user_id == coll1.id).sort(-coll2.date).limit(1).return_(coll2)

    aql_query = (
        AQLQuery()
        .for_(coll1)
        .filter(coll1.age > 25)
        .for_(coll2)
        .filter(coll2.date >= "2023-01-01")
        .sort(-coll2.date)
        .limit(100)
        .return_(
            ObjectExpression(
                {"user": coll1.name, "top_orders": subquery1, "latest_order": subquery3, "products": subquery2}, coll1
            )
        )
    )

    expected_compiled = (
        "FOR u IN `users` FILTER u.age > @param1 "
        "FOR o IN `orders` FILTER o.date >= @param2 SORT o.date DESC LIMIT 100 "
        "RETURN {user: u.name, top_orders: (FOR o IN `orders` FILTER o.user_id == u.id "
        "SORT o.total_amount DESC LIMIT 10 RETURN o), "
        "latest_order: (FOR o IN `orders` FILTER o.user_id == u.id "
        "SORT o.date DESC LIMIT 1 RETURN o), "
        "products: (FOR p IN `products` FILTER p.order_id == o.id "
        "SORT p.price ASC LIMIT 5 RETURN p)}"
    )

    expected_repr = (
        f"FOR {repr(coll1.iterator)} IN {repr(coll1)} "
        f"FILTER {repr(coll1.iterator)}.age > ? "
        f"FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.date >= ? "
        f"SORT {repr(coll2.iterator)}.date DESC LIMIT 100 "
        f"RETURN {{user: {repr(coll1.iterator)}.name, "
        f"top_orders: (FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.user_id == {repr(coll1.iterator)}.id "
        f"SORT {repr(coll2.iterator)}.total_amount DESC LIMIT 10 "
        f"RETURN {repr(coll2.iterator)}), "
        f"latest_order: (FOR {repr(coll2.iterator)} IN {repr(coll2)} "
        f"FILTER {repr(coll2.iterator)}.user_id == {repr(coll1.iterator)}.id "
        f"SORT {repr(coll2.iterator)}.date DESC LIMIT 1 "
        f"RETURN {repr(coll2.iterator)}), "
        f"products: (FOR {repr(coll3.iterator)} IN {repr(coll3)} "
        f"FILTER {repr(coll3.iterator)}.order_id == {repr(coll2.iterator)}.id "
        f"SORT {repr(coll3.iterator)}.price ASC LIMIT 5 "
        f"RETURN {repr(coll3.iterator)})}}"
    )

    repr_query = repr(aql_query)
    assert repr_query == expected_repr
    assert aql_query.compile() == expected_compiled
    assert aql_query.bind_vars == {"param1": 25, "param2": "2023-01-01"}


def test_insert():
    param1 = 1
    doc = {"a": param1}
    coll = "test"
    aql_query, coll, obj = insert_query(coll, doc)

    repr_query = repr(aql_query)
    assert repr_query == f"INSERT {repr(obj)} INTO {repr(coll)}"
    assert aql_query.compile() == "INSERT {a: @param1} INTO `test`"
    assert aql_query.bind_vars == {"param1": param1}


def test_insert_return_new():
    doc = {"a": 1}
    coll = "test"
    new = NEW()
    aql_query, coll, obj = insert_return_new_query(coll, doc, new)

    repr_query = repr(aql_query)
    assert repr_query == f"INSERT {repr(obj)} INTO {repr(coll)} RETURN NEW"
    assert aql_query.compile() == "INSERT {a: @param1} INTO `test` RETURN NEW"
    assert aql_query.bind_vars == {"param1": 1}


def test_insert_return_new_a_b():
    param1 = 1
    param2 = "2"
    coll = "test"
    new = NEW()
    new_doc = ObjectExpression({"a": new.a, "b": new.b})
    doc = {"a": param1, "b": param2}
    aql_query, coll_expr, obj_expr = insert_return_new_query(coll, doc, new_doc)
    repr_query = repr(aql_query)
    assert aql_query.compile() == "INSERT {a: @param1, b: @param2} INTO `test` RETURN {a: NEW.a, b: NEW.b}"
    assert repr_query == f"INSERT {repr(obj_expr)} INTO {repr(coll_expr)} RETURN {{a: NEW.a, b: NEW.b}}"
    assert aql_query.bind_vars == {"param1": param1, "param2": param2}


def test_insert_return_new_a_b2():
    param1 = 1
    param2 = "2"
    coll = "test"
    new = NEW()
    new_doc = {"a": new.a, "b": new.b}
    doc = {"a": param1, "b": param2}
    aql_query, coll_expr, obj_expr = insert_return_new_query(coll, doc, new_doc)
    repr_query = repr(aql_query)
    assert aql_query.compile() == "INSERT {a: @param1, b: @param2} INTO `test` RETURN {a: NEW.a, b: NEW.b}"
    assert repr_query == f"INSERT {repr(obj_expr)} INTO {repr(coll_expr)} RETURN {{a: NEW.a, b: NEW.b}}"
    assert aql_query.bind_vars == {"param1": param1, "param2": param2}


def test_no_modification_query():
    new = NEW()
    aql_query = AQLQuery().return_(ObjectExpression({"a": new.a, "b": new.b}))
    with pytest.raises(AssertionError, match="no modification operation defined to use NEW keyword"):
        aql_query.compile()


def test_remove():
    param1 = 1
    doc = {"a": param1}
    coll = "test"
    aql_query, coll = delete_query(coll, doc)

    repr_query = repr(aql_query)
    assert repr_query == f"REMOVE {repr(ObjectExpression(doc))} IN {repr(coll)}"
    assert aql_query.compile() == "REMOVE {a: @param1} IN `test`"
    assert aql_query.bind_vars == {"param1": param1}


def test_update():
    param1 = 1
    doc = {"a": param1}
    coll = "test"
    aql_query, coll = update_query(coll, "1", doc)

    repr_query = repr(aql_query)
    assert repr_query == f"UPDATE {repr(ObjectExpression(doc))} IN {repr(coll)}"
    assert aql_query.compile() == "UPDATE {a: @param1} IN `test`"
    assert aql_query.bind_vars == {"param1": param1}


def test_replace():
    param1 = 1
    doc = {"a": param1}
    coll = "test"
    aql_query, coll = replace_query(coll, "1", doc)

    repr_query = repr(aql_query)
    assert repr_query == f"REPLACE {repr(ObjectExpression(doc))} IN {repr(coll)}"
    assert aql_query.compile() == "REPLACE {a: @param1} IN `test`"
    assert aql_query.bind_vars == {"param1": param1}


def test_upsert_update():
    coll = "test"
    param1 = "churrasco"
    param2 = 1
    aql_query, coll = upsert_query(coll, {"_key": param2}, insert={"name": param2}, update={"food": param1})

    repr_query = repr(aql_query)
    assert repr_query == f"UPSERT {{_key: ?}} INSERT {{name: ?}} UPDATE {{food: ?}} IN {repr(coll)}"
    assert aql_query.compile() == "UPSERT {_key: @param2} INSERT {name: @param2} UPDATE {food: @param1} IN `test`"

    assert aql_query.bind_vars == {"param1": param1, "param2": param2}


def test_upsert_replace():
    coll = "test"
    param1 = "milanesa"
    param2 = 1
    aql_query, coll = upsert_query(coll, {"_key": param2}, insert={"name": param2}, replace={"food": param1})

    repr_query = repr(aql_query)
    assert repr_query == f"UPSERT {{_key: ?}} INSERT {{name: ?}} REPLACE {{food: ?}} IN {repr(coll)}"
    assert aql_query.compile() == "UPSERT {_key: @param2} INSERT {name: @param2} REPLACE {food: @param1} IN `test`"

    assert aql_query.bind_vars == {"param1": param1, "param2": param2}


def test_traverse_v():
    v = IteratorExpression("v")
    param1 = "persons/123"
    query = AQLQuery().traverse(v, "knows", param1, RangeExpression(1, 2), TraversalDirection.OUTBOUND).return_(v)
    query.compile()
    assert query.compile() == "FOR v IN 1..2 OUTBOUND @param1 `knows` RETURN v"
    assert repr(query) == f"FOR {repr(v)} IN 1..2 OUTBOUND ? <CollectionExpression: knows> RETURN {repr(v)}"
    assert query.bind_vars == {"param1": param1}


def test_traverse_v_e():
    v = IteratorExpression("v")
    e = IteratorExpression("e")
    param1 = "persons/123"
    query = AQLQuery().traverse((v, e), "knows", param1, RangeExpression(1, 2), TraversalDirection.OUTBOUND).return_(v)
    query.compile()
    assert query.compile() == "FOR v, e IN 1..2 OUTBOUND @param1 `knows` RETURN v"
    assert repr(query) == f"FOR {repr(v)}, {repr(e)} IN 1..2 OUTBOUND ? <CollectionExpression: knows> RETURN {repr(v)}"
    assert query.bind_vars == {"param1": param1}


def test_traverse_v_e_p():
    v = IteratorExpression("v")
    e = IteratorExpression("e")
    p = IteratorExpression("p")
    param1 = "persons/123"
    query = (
        AQLQuery().traverse((v, e, p), "knows", param1, RangeExpression(1, 2), TraversalDirection.OUTBOUND).return_(v)
    )
    expected_repr = (
        f"FOR {repr(v)}, {repr(e)}, {repr(p)} IN 1..2 OUTBOUND ? <CollectionExpression: knows> RETURN {repr(v)}"
    )
    assert query.compile() == "FOR v, e, p IN 1..2 OUTBOUND @param1 `knows` RETURN v"
    assert repr(query) == expected_repr
    assert query.bind_vars == {"param1": param1}


def test_let_query():
    query, coll = simple_query(20)
    let = VariableExpression()
    aql = AQLQuery().let(let, query).return_(let)

    expected_repr = (
        f"LET {DYNAMIC_ALIAS} = (FOR {repr(coll.iterator)} IN {repr(coll)} FILTER {repr(coll.iterator)}.age > ? SORT"
        f" {repr(coll.iterator)}.age ASC RETURN {repr(coll.iterator)}) RETURN {repr(let)}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == "LET var1 = (FOR u IN `users` FILTER u.age > @param1 SORT u.age ASC RETURN u) RETURN var1"


def test_collect():
    products = CollectionExpression("products")
    category_collect = VariableExpression()
    aql = (
        AQLQuery()
        .for_(products)
        .collect(
            collect=AssignmentExpression(category_collect, products.category),
        )
        .return_(category_collect)
    )
    expected_compiled = "FOR var1 IN `products` COLLECT var2 = var1.category RETURN var2"
    expected_repr = (
        f"FOR {repr(products.iterator)} IN {repr(products)} "
        f"COLLECT {repr(category_collect)} = {repr(products.iterator)}.category "
        f"RETURN {repr(category_collect)}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_collect_into():
    products = CollectionExpression("products")
    groups = VariableExpression()
    category_collect = VariableExpression()
    aql = (
        AQLQuery()
        .for_(products)
        .collect(collect=AssignmentExpression(category_collect, products.category), into=groups)
        .return_({"groups": groups, "categories": category_collect})
    )
    expected_compiled = (
        "FOR var1 IN `products` COLLECT var2 = var1.category INTO var3 RETURN {groups: var3, categories: var2}"
    )
    expected_repr = (
        f"FOR {repr(products.iterator)} IN {repr(products)} "
        f"COLLECT {repr(category_collect)} = {repr(products.iterator)}.category "
        f"INTO {repr(groups)} "
        f"RETURN {{groups: {repr(groups)}, categories: {repr(category_collect)}}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_collect_into_projection():
    products = CollectionExpression("products")
    groups = VariableExpression()
    into_expression = AssignmentExpression(groups, products.name)
    category_collect = VariableExpression()
    aql = (
        AQLQuery()
        .for_(products)
        .collect(collect=AssignmentExpression(category_collect, products.category), into=into_expression)
        .return_({"groups": groups, "categories": category_collect})
    )
    expected_compiled = (
        "FOR var1 IN `products` "
        "COLLECT var2 = var1.category INTO var3 = var1.name "
        "RETURN {groups: var3, categories: var2}"
    )
    expected_repr = (
        f"FOR {repr(products.iterator)} IN {repr(products)} "
        f"COLLECT {repr(category_collect)} = {repr(products.iterator)}.category "
        f"INTO {repr(into_expression)} "
        f"RETURN {{groups: {repr(groups)}, categories: {repr(category_collect)}}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_collect_with_count():
    products = CollectionExpression("products")
    length = VariableExpression()
    category_collect = VariableExpression()
    aql = (
        AQLQuery()
        .for_(products)
        .collect(collect=AssignmentExpression(category_collect, products.category), with_count_into=length)
        .return_({"length": length, "categories": category_collect})
    )
    expected_compiled = (
        "FOR var1 IN `products` "
        "COLLECT var2 = var1.category WITH COUNT INTO var3 "
        "RETURN {length: var3, categories: var2}"
    )
    expected_repr = (
        f"FOR {repr(products.iterator)} IN {repr(products)} "
        f"COLLECT {repr(category_collect)} = {repr(products.iterator)}.category "
        f"WITH COUNT INTO {repr(length)} "
        f"RETURN {{length: {repr(length)}, categories: {repr(category_collect)}}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_collect_aggregate():
    products = CollectionExpression("products")
    category_collect = VariableExpression()
    category_agg = VariableExpression()
    aql = (
        AQLQuery()
        .for_(products)
        .collect(
            collect=AssignmentExpression(category_collect, products.category),
            aggregate=AssignmentExpression(category_agg, Sum(products.category)),
        )
        .return_({"groups": category_collect, "products": category_agg})
    )
    expected_compiled = (
        "FOR var1 IN `products` COLLECT var2 = var1.category AGGREGATE var3 = SUM(var1.category) "
        "RETURN {groups: var2, products: var3}"
    )
    expected_repr = (
        f"FOR {repr(products.iterator)} IN {repr(products)} "
        f"COLLECT {repr(category_collect)} = {repr(products.iterator)}.category "
        f"AGGREGATE {repr(category_agg)} = SUM({repr(products.iterator)}.category) "
        f"RETURN {{groups: {repr(category_collect)}, products: {repr(category_agg)}}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_collect_aggregate_into():
    products = CollectionExpression("products")
    groups = VariableExpression()
    category_collect = VariableExpression()
    category_agg = VariableExpression()
    aql = (
        AQLQuery()
        .for_(products)
        .collect(
            collect=AssignmentExpression(category_collect, products.category),
            aggregate=AssignmentExpression(category_agg, Sum(products.category)),
            into=groups,
        )
        .return_({"groups": groups, "products": category_agg})
    )

    expected_compiled = (
        "FOR var1 IN `products` COLLECT var2 = var1.category AGGREGATE var3 = SUM(var1.category) INTO var4 RETURN"
        " {groups: var4, products: var3}"
    )
    expected_repr = (
        f"FOR {repr(products.iterator)} IN {repr(products)} "
        f"COLLECT {repr(category_collect)} = {repr(products.iterator)}.category "
        f"AGGREGATE {repr(category_agg)} = SUM({repr(products.iterator)}.category) INTO {repr(groups)} "
        f"RETURN {{groups: {repr(groups)}, products: {repr(category_agg)}}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_aggregate():
    products = CollectionExpression("products")
    category_agg = VariableExpression()
    aql = (
        AQLQuery()
        .for_(products)
        .collect(
            aggregate=AssignmentExpression(category_agg, Sum(products.orders)),
        )
        .return_({"productOrders": category_agg})
    )
    expected_compiled = "FOR var1 IN `products` COLLECT AGGREGATE var2 = SUM(var1.orders) RETURN {productOrders: var2}"
    expected_repr = (
        f"FOR {repr(products.iterator)} IN {repr(products)} "
        "COLLECT "
        f"AGGREGATE {repr(category_agg)} = SUM({repr(products.iterator)}.orders) "
        f"RETURN {{productOrders: {repr(category_agg)}}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_aggregate_into():
    products = CollectionExpression("products")
    groups = VariableExpression()
    category_agg = VariableExpression()
    aql = (
        AQLQuery()
        .for_(products)
        .collect(
            aggregate=AssignmentExpression(category_agg, Sum(products.category)),
            into=groups,
        )
        .return_({"groups": groups, "products": category_agg})
    )
    expected_compiled = (
        "FOR var1 IN `products` COLLECT AGGREGATE var2 = SUM(var1.category) INTO var3 RETURN"
        " {groups: var3, products: var2}"
    )
    expected_repr = (
        f"FOR {repr(products.iterator)} IN {repr(products)} "
        "COLLECT "
        f"AGGREGATE {repr(category_agg)} = SUM({repr(products.iterator)}.category) INTO {repr(groups)} "
        f"RETURN {{groups: {repr(groups)}, products: {repr(category_agg)}}}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled


def test_with_count():
    products = CollectionExpression("products")
    length = VariableExpression()
    aql = (
        AQLQuery()
        .for_(products)
        .collect(
            with_count_into=length,
        )
        .return_(length)
    )
    expected_compiled = "FOR var1 IN `products` COLLECT WITH COUNT INTO var2 RETURN var2"
    expected_repr = (
        f"FOR {repr(products.iterator)} IN {repr(products)} "
        "COLLECT "
        f"WITH COUNT INTO {repr(length)} "
        f"RETURN {repr(length)}"
    )

    assert repr(aql) == expected_repr
    assert aql.compile() == expected_compiled
