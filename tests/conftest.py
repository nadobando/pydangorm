import asyncio
import logging
import sys
from typing import AsyncGenerator, TypeVar

import pytest
from aioarango import ArangoClient
from aioarango.database import StandardDatabase

from pydango.connection.utils import get_or_create_db


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
                    formatted_record += f"\n{i}=\n{record.__dict__[i]}"

            return formatted_record

    formatter = CustomFormatter()
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    logging.getLogger("pydango").addHandler(handler)
    with caplog.at_level(logging.DEBUG, "pydango"):
        yield


T = TypeVar("T")

AsyncFixture = AsyncGenerator[T, None]


@pytest.fixture(scope="session")
async def client() -> AsyncFixture[ArangoClient]:
    client = ArangoClient()
    yield client
    await client.close()


@pytest.fixture(scope="session")
async def database(client: ArangoClient) -> AsyncFixture[StandardDatabase]:
    # await (await client.db("_system")).delete_database("pydango")
    # exit()

    db = await get_or_create_db(client, "pydango")
    yield db
    await (await client.db("_system")).delete_database("pydango")
