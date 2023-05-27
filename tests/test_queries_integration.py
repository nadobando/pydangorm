# Example data for populating the database
from typing import Sequence

import pytest
from aioarango.database import Database

from pydango.connection.utils import deplete_cursor, iterate_cursor
from tests.data import DATA
from tests.queries import (  # multiple_collections_query,
    multiple_filters_query,
    projection_complex_query,
    simple_query,
    sort_filter_query,
)


@pytest.mark.asyncio
async def test_simple_query(database: Database):
    query, _ = simple_query(29)

    results = await deplete_cursor(await query.execute(database))
    expected = get_at(DATA["users"], 2, 6, 4, 3)

    assert results == expected


def get_at(lst: Sequence, *indexes: int):
    return [lst.__getitem__(i) for i in indexes]


@pytest.mark.asyncio
async def test_multiple_filters_query(database: Database):
    query, _ = multiple_filters_query(25, "Female")
    results = await deplete_cursor(await query.execute(database))
    expected = get_at(DATA["users"], 1, 4, 6)
    assert expected == results


@pytest.mark.asyncio
async def test_projection_complex_query(database: Database):
    query, _, _ = projection_complex_query("Jane Smith", 25)
    results = await iterate_cursor(await query.execute(database))
    expected_results = [
        {"a": "Jane Smith"},
    ]
    assert expected_results == results


# @pytest.mark.asyncio
# async def test_sort_filter_query(database: Database):
#     query, _, _ = sort_filter_query(28)
#     query.sep="\n"
#     query.compile()
#     print()
#     print(query)
#     results = await deplete_cursor(await query.execute(database))
#     expected_results = get_at(DATA["users"], 1, 2, 3)
#     assert results == expected_results


# @pytest.mark.asyncio
# async def test_multiple_collections_query(database: Database):
#     query, _, _ = multiple_collections_query(25)
#     results = await deplete_cursor(await query.execute(database))
#     assert   results == DATA["users"][0:2]
