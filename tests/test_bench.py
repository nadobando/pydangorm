import timeit

import pytest
from aioarango.database import Database

from tests.queries import simple_query
from tests.test_queries_integration import deplete_cursor, iterate_cursor


@pytest.mark.skip
async def test_benchmark(database: Database):
    query, _ = simple_query(10)

    times = 1
    # result = await deplete_cursor(cursor)
    winner = {1: 0, 2: 0}

    for i in range(1000):
        cursor = await query.execute(database)
        execution_time_function1 = timeit.timeit(lambda: deplete_cursor(cursor), number=times)
        cursor = await query.execute(database)
        execution_time_function2 = timeit.timeit(lambda: iterate_cursor(cursor), number=times)
        if execution_time_function1 > execution_time_function2:
            winner[1] += 1
        else:
            winner[2] += 1
    print(winner)
