import pytest
from aioarango.database import Database

from pydango.connection.utils import deplete_cursor
from tests.test_queries.data import DATA
from tests.test_queries.ecommerce_queries import (
    get_ordered_products_with_reviews_query,
    get_product_orders_reviews_query,
    get_product_reviews_query,
    get_user_orders_query,
    get_user_reviews_query,
)
from tests.test_queries.utils import execute_query


@pytest.mark.asyncio
async def test_get_user_orders_query(database: Database):
    query, orders_coll = get_user_orders_query("1")
    results = await deplete_cursor(await execute_query(query, database))
    expected = [
        DATA["orders"][0],
        DATA["orders"][1],
    ]
    assert expected == results


@pytest.mark.asyncio
async def test_get_product_reviews_query(database: Database):
    query = get_product_reviews_query("1")
    results = await deplete_cursor(await execute_query(query, database))
    expected = [
        DATA["reviews"][1],
        DATA["reviews"][0],
    ]
    assert expected == results


@pytest.mark.asyncio
async def test_get_user_reviews_query(database: Database):
    query, reviews_coll = get_user_reviews_query("2")
    results = await deplete_cursor(await execute_query(query, database))
    expected = [
        DATA["reviews"][1],
    ]
    assert expected == results


@pytest.mark.asyncio
async def test_get_product_orders_reviews_query(database: Database):
    query = get_product_orders_reviews_query("1")
    results = await deplete_cursor(await execute_query(query, database))
    expected = [
        {"product": DATA["products"][0], "orders": DATA["orders"][0], "reviews": DATA["reviews"][1]},
        {"product": DATA["products"][0], "orders": DATA["orders"][0], "reviews": DATA["reviews"][0]},
    ]
    assert results == expected


@pytest.mark.asyncio
async def test_get_ordered_products_with_reviews_query(database: Database):
    query = get_ordered_products_with_reviews_query()
    results = await deplete_cursor(await execute_query(query, database))
    expected = [
        {"product": DATA["products"][0], "orders": DATA["orders"][0], "reviews": DATA["reviews"][0]},
        {"product": DATA["products"][0], "orders": DATA["orders"][0], "reviews": DATA["reviews"][1]},
        {"product": DATA["products"][1], "orders": DATA["orders"][0], "reviews": DATA["reviews"][2]},
        # (DATA["products"][2], DATA["orders"][3], DATA["reviews"][3]),
        # (DATA["products"][3], DATA["orders"][4], DATA["reviews"][4]),
        # (DATA["products"][4], DATA["orders"][5], DATA["reviews"][5]),
        # (DATA["products"][5], DATA["orders"][6], DATA["reviews"][6]),
        # (DATA["products"][6], DATA["orders"][7], DATA["reviews"][7]),
    ]
    assert results == expected
