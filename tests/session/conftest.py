import pytest
from aioarango.database import StandardDatabase
from pydiction import Matcher

from pydango.connection.session import PydangoSession
from tests.conftest import AsyncFixture


@pytest.fixture(scope="package")
async def session(database: StandardDatabase) -> AsyncFixture[PydangoSession]:
    yield PydangoSession(database=database)


@pytest.fixture(scope="package")
def matcher():
    return Matcher()
