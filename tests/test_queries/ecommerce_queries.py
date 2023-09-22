from pydango.query.expressions import CollectionExpression, In, ObjectExpression
from pydango.query.query import AQLQuery


def get_user_orders_query(user_id):
    users_coll = CollectionExpression("users", "u")
    orders_coll = CollectionExpression("orders", "o")
    aql_query = (
        AQLQuery()
        .for_(users_coll)
        .filter(users_coll._key == user_id)
        .for_(orders_coll)
        .filter(users_coll._key == orders_coll.user)
        .sort(+orders_coll.order_date)
        .return_(orders_coll)
    )
    return aql_query, orders_coll


def get_product_reviews_query(product_id):
    products_coll = CollectionExpression("products", "p")
    reviews_coll = CollectionExpression("reviews", "r")
    aql_query = (
        AQLQuery()
        .for_(products_coll)
        .filter(products_coll._key == product_id)
        .for_(reviews_coll)
        .filter(products_coll._key == reviews_coll.product)
        .sort(-reviews_coll.rating)
        .return_(reviews_coll)
    )
    return aql_query


def get_user_reviews_query(user_id):
    users_coll = CollectionExpression("users", "u")
    reviews_coll = CollectionExpression("reviews", "r")
    aql_query = (
        AQLQuery()
        .for_(users_coll)
        .filter(users_coll._key == user_id)
        .for_(reviews_coll)
        .filter(users_coll._key == reviews_coll.user)
        .sort(-reviews_coll.rating)
        .return_(reviews_coll)
    )
    return aql_query, reviews_coll


def get_product_orders_reviews_query(product_id):
    products_coll = CollectionExpression("products", "p")
    orders_coll = CollectionExpression("orders", "o")
    reviews_coll = CollectionExpression("reviews", "r")
    aql_query = (
        AQLQuery()
        .for_(products_coll)
        .filter(products_coll._key == product_id)
        .for_(orders_coll)
        .filter(In(products_coll._key, orders_coll.products))
        .for_(reviews_coll)
        .filter(products_coll._key == reviews_coll.product)
        .sort(+orders_coll.order_date, -reviews_coll.rating)
        .return_(
            ObjectExpression(
                {"product": products_coll.iterator, "orders": orders_coll.iterator, "reviews": reviews_coll.iterator}
            )
        )
    )
    return aql_query


# def get_user_with_most_orders_query():
#     users_coll = CollectionExpression("users", "u")
#     orders_coll = CollectionExpression("orders", "o")
#     aql_query = (
#         AQLQuery()
#         .for_(users_coll)
#         .for_(orders_coll)
#         .filter(users_coll._key == orders_coll.user)
#         .group_by(users_coll._key)
#         .sort(-AQLQuery.count(orders_coll._key))
#         .limit(1)
#         .return_(users_coll)
#     )
#     return aql_query, users_coll


# def get_product_with_highest_rating_query():
#     products_coll = CollectionExpression("products", "p")
#     reviews_coll = CollectionExpression("reviews", "r")
#     aql_query = (
#         AQLQuery()
#         .for_(products_coll)
#         .for_(reviews_coll)
#         .filter(products_coll._key == reviews_coll.product)
#         .group_by(products_coll._key)
#         .sort(-AQLQuery.avg(reviews_coll.rating))
#         .limit(1)
#         .return_(products_coll)
#     )
#     return aql_query, products_coll


# def get_users_with_multiple_orders_query(min_orders):
#     users_coll = CollectionExpression("users", "u")
#     orders_coll = CollectionExpression("orders", "o")
#     aql_query = (
#         AQLQuery()
#         .for_(users_coll)
#         .for_(orders_coll)
#         .filter(users_coll._key == orders_coll.user)
#         .group_by(users_coll._key)
#         .filter(AQLQuery.count(orders_coll._key) > min_orders)
#         .return_(users_coll)
#     )
#     return aql_query, users_coll


# def get_products_without_reviews_query():
#     products_coll = CollectionExpression("products", "p")
#     reviews_coll = CollectionExpression("reviews", "r")
#     aql_query = (
#         AQLQuery()
#         .for_(products_coll)
#         .not_for_(reviews_coll)
#         .filter(products_coll._key != reviews_coll.product)
#         .return_(products_coll)
#     )
#     return aql_query, products_coll


# def get_users_with_high_total_order_amount_query(min_amount):
#     users_coll = CollectionExpression("users", "u")
#     orders_coll = CollectionExpression("orders", "o")
#     aql_query = (
#         AQLQuery()
#         .for_(users_coll)
#         .for_(orders_coll)
#         .filter(users_coll._key == orders_coll.user)
#         .group_by(users_coll._key)
#         .filter(AQLQuery.sum(orders_coll.total_amount) > min_amount)
#         .return_(users_coll)
#     )
#     return aql_query, users_coll


def get_ordered_products_with_reviews_query():
    products_coll = CollectionExpression("products", "p")
    orders_coll = CollectionExpression("orders", "o")
    reviews_coll = CollectionExpression("reviews", "r")
    aql_query = (
        AQLQuery()
        .for_(products_coll)
        .for_(orders_coll)
        .for_(reviews_coll)
        .filter(In(products_coll._key, orders_coll.products))
        .filter(products_coll._key == reviews_coll.product)
        .sort(+orders_coll.order_date)
        .return_(
            ObjectExpression(
                {"product": products_coll.iterator, "orders": orders_coll.iterator, "reviews": reviews_coll.iterator}
            )
        )
    )
    return aql_query


# def get_users_with_most_recent_order_query():
#     users_coll = CollectionExpression("users", "u")
#     orders_coll = CollectionExpression("orders", "o")
#     aql_query = (
#         AQLQuery()
#         .for_(users_coll)
#         .for_(orders_coll)
#         .filter(users_coll._key == orders_coll.user)
#         .group_by(users_coll._key)
#         .sort(-AQLQuery.max(orders_coll.order_date))
#         .limit(1)
#         .return_(users_coll)
#     )
#     return aql_query, users_coll


# def get_users_with_common_ordered_products_query(user_id):
#     users_coll = CollectionExpression("users", "u")
#     orders_coll = CollectionExpression("orders", "o")
#     products_coll = CollectionExpression("products", "p")
#     aql_query = (
#         AQLQuery()
#         .for_(users_coll)
#         .for_(orders_coll)
#         .for_(products_coll)
#         .filter(users_coll._key == user_id)
#         .filter(users_coll._key == orders_coll.user)
#         .filter(orders_coll.product == products_coll._key)
#         .group_by(users_coll._key)
#         .sort(-AQLQuery.count(products_coll._key))
#         .limit(1)
#         .return_(users_coll)
#     )
#     return aql_query, users_coll
