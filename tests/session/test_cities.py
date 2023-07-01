import datetime
from typing import TYPE_CHECKING, Annotated

import pytest

from pydango.connection.session import PydangoSession
from pydango.index import PersistentIndex
from pydango.orm.models import (
    EdgeCollectionConfig,
    EdgeModel,
    Relation,
    VertexCollectionConfig,
    VertexModel,
)
from tests.utils import assert_equals_dicts

if TYPE_CHECKING:
    from aioarango.database import StandardDatabase


class Visited(EdgeModel):
    rating: int
    on_date: datetime.date

    class Collection(EdgeCollectionConfig):
        name = "visited"
        indexes = [
            PersistentIndex(fields=["rating"]),
        ]


class LivesIn(EdgeModel):
    since: datetime.datetime

    class Collection(EdgeCollectionConfig):
        name = "lives_in"


class Person(VertexModel):
    name: str
    age: int
    lives_in: Annotated["City", Relation[LivesIn]]
    visited: Annotated[list["City"], Relation[Visited]]

    class Collection(VertexCollectionConfig):
        name = "people"
        indexes = [
            PersistentIndex(fields=["name"]),
            PersistentIndex(fields=["age"]),
        ]


class City(VertexModel):
    name: str
    population: int

    class Collection(VertexCollectionConfig):
        name = "cities"
        indexes = [PersistentIndex(fields=["name"]), PersistentIndex(fields=["population"])]


city = City(name="tlv", population=123)
Person.update_forward_refs()


# LivesIn.update_forward_refs()
# Person.update_forward_refs()


@pytest.mark.asyncio
async def test_save(database: "StandardDatabase"):
    session = PydangoSession(database)
    await session.init(Person)
    await session.init(City)
    await session.init(LivesIn)
    await session.init(Visited)
    p = Person(
        name="John",
        age=35,
        lives_in=city,
        visited=[
            City(name="New York", population=123),
            City(name="Amsterdam", population=123),
        ],
        edges={
            Person.lives_in: LivesIn(since=datetime.datetime.now()),
            Person.visited: [
                Visited(rating=10, on_date=datetime.date.today()),
                Visited(rating=10, on_date=datetime.date.today()),
            ],
        },
    )

    p = await session.save(p)
    from unittest.mock import ANY

    expected = {
        "age": 35,
        "edges": {
            "lives_in": {
                "from_": ANY,
                "id": ANY,
                "key": ANY,
                "rev": ANY,
                "since": datetime.datetime(2023, 7, 1, 18, 16, 38, 350095),
                "to": ANY,
            },
            "visited": [
                {
                    "from_": ANY,
                    "id": ANY,
                    "key": ANY,
                    "on_date": datetime.date(2023, 7, 1),
                    "rating": 10,
                    "rev": ANY,
                    "to": ANY,
                },
                {
                    "from_": ANY,
                    "id": ANY,
                    "key": ANY,
                    "on_date": datetime.date(2023, 7, 1),
                    "rating": 10,
                    "rev": ANY,
                    "to": ANY,
                },
            ],
        },
        "id": ANY,
        "key": ANY,
        "lives_in": {"id": ANY, "key": ANY, "name": "tlv", "population": 123, "rev": ANY},
        "name": "John",
        "rev": ANY,
        "visited": [
            {"id": ANY, "key": ANY, "name": "New York", "population": 123, "rev": ANY},
            {"id": ANY, "key": ANY, "name": "Amsterdam", "population": 123, "rev": ANY},
        ],
    }

    assert_equals_dicts(p.dict(include_edges=True), expected)
