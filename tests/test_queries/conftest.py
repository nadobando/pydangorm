from collections import defaultdict

import pytest_asyncio
from aioarango.database import Database

from pydango.query.expressions import NEW
from tests.queries import insert_return_new_query
from tests.test_queries.data import DATA


@pytest_asyncio.fixture(scope="package", autouse=True)
async def populate(database: Database):
    responses = defaultdict(list)
    for coll in DATA:
        await database.delete_collection(coll, ignore_missing=True)
        await database.create_collection(coll)
    for coll in DATA:
        for i, row in enumerate(DATA[coll]):
            aql, _, __ = insert_return_new_query(coll, row, NEW())
            response = await aql.execute(database)
            next_ = await response.next()
            DATA[coll][i] = next_
            responses[coll].append(next_)
    yield
