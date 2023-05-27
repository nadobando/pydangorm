import asyncio
import logging
import sys
from collections import defaultdict

import pytest
import pytest_asyncio
from aioarango import ArangoClient
from aioarango.database import Database

from pydango.connection.utils import get_or_create_db
from pydango.query.expressions import NEW
from tests.data import DATA
from tests.queries import insert_return_new_query


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


exclude = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
}


@pytest.fixture(autouse=True)
def add_log(caplog):
    class CustomFormatter(logging.Formatter):
        def format(self, record):
            formatted_record = record.getMessage()

            for i in record.__dict__:
                if i not in exclude:
                    formatted_record += f" | {i}={record.__dict__[i]}"

            return formatted_record

    formatter = CustomFormatter()
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    logging.getLogger("pydango").addHandler(handler)
    with caplog.at_level(logging.DEBUG, "pydango"):
        yield


@pytest_asyncio.fixture(scope="session")
async def client() -> ArangoClient:
    client = ArangoClient()
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="session")
async def database(client: ArangoClient) -> Database:
    db = await get_or_create_db(client, "pydango")
    yield db
    # await (await client.db("_system")).delete_database("pydango")


@pytest_asyncio.fixture(scope="session", autouse=True)
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
