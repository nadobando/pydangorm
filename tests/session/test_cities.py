import asyncio
import datetime
from typing import TYPE_CHECKING, Annotated, Iterable, Type

import pytest
from _pytest.fixtures import FixtureRequest
from pydantic import Field
from pydiction import ANY_NOT_NONE, Matcher

from pydango.connection.session import PydangoSession
from pydango.index import PersistentIndex
from pydango.orm.models import (
    BaseArangoModel,
    EdgeCollectionConfig,
    EdgeModel,
    Relation,
    VertexCollectionConfig,
    VertexModel,
)
from pydango.query.consts import ID

# from tests.utils import find_dict_diffs, ANY_NOT_NONE
# from tests.utils2 import Matcher

if TYPE_CHECKING:
    pass


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
def expected_person(person: Person):
    expected = {
        "_id": ANY_NOT_NONE,
        "_key": ANY_NOT_NONE,
        "_rev": ANY_NOT_NONE,
        "name": person.name,
        "age": person.age,
        "lives_in": {
            "_id": ANY_NOT_NONE,
            "_key": ANY_NOT_NONE,
            "_rev": ANY_NOT_NONE,
            "name": "tlv",
            "population": person.lives_in.population,
        },
        "visited": [
            {
                "_id": ANY_NOT_NONE,
                "_key": ANY_NOT_NONE,
                "_rev": ANY_NOT_NONE,
                "name": person.visited[0].name,
                "population": person.visited[0].population,
            },
            {
                "_id": ANY_NOT_NONE,
                "_key": ANY_NOT_NONE,
                "_rev": ANY_NOT_NONE,
                "name": person.visited[1].name,
                "population": person.visited[1].population,
            },
        ],
        "edges": {
            "lives_in": {
                "_id": ANY_NOT_NONE,
                "_key": ANY_NOT_NONE,
                "_rev": ANY_NOT_NONE,
                "_from": ANY_NOT_NONE,
                "_to": ANY_NOT_NONE,
                "since": person.edges.lives_in.since,
            },
            "visited": [
                {
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "_from": ANY_NOT_NONE,
                    "_to": ANY_NOT_NONE,
                    "on_date": person.edges.visited[0].on_date,
                    "rating": person.edges.visited[0].rating,
                },
                {
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "_from": ANY_NOT_NONE,
                    "_to": ANY_NOT_NONE,
                    "on_date": person.edges.visited[1].on_date,
                    "rating": person.edges.visited[1].rating,
                },
            ],
        },
    }
    return expected


@pytest.fixture(scope="module", autouse=True)
async def init_collections(session: PydangoSession):
    models: Iterable[Type[BaseArangoModel]] = (Person, City, LivesIn, Visited)
    await asyncio.gather(*[session.init(coll) for coll in models])


@pytest.mark.run(order=1)
@pytest.mark.asyncio
async def test_save(matcher: Matcher, session: PydangoSession, request: FixtureRequest, person):
    p = await session.save(person)
    print(p)
    request.config.cache.set("person_key", p.key)  # type: ignore[union-attr]
    matcher.assert_declarative_object(p.dict(by_alias=True, include_edges=True), expected_person(p))


@pytest.fixture
def person():
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
    return p


class IdProjection(VertexModel):
    id: str = Field(alias=ID)


@pytest.mark.run(order=2)
async def test_get(matcher: Matcher, session: PydangoSession, request: FixtureRequest):
    _id = request.config.cache.get("person_key", None)  # type: ignore[union-attr]
    result = await session.get(Person, _id, fetch_edges=True)
    assert result is not None
    matcher.assert_declarative_object(result.dict(by_alias=True, include_edges=True), expected_person(result))
