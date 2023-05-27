import datetime
from typing import Annotated

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
async def test_save(database):
    # await get_or_create_db(client, "pydango")
    # db = await client.db("pydango")

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

    print(p)
    # city = City(name="BsAs", population=33)
    # await session.save(city)
    # p = await session.get(Person, "356900")
    # await session.save()

    # new_q = NEW()
    # city_q = ORMQuery().insert(city).return_(new_q._id)
    # new_p = NEW()
    # person_q = ORMQuery().insert(p).return_(new_p)
    # lives_in_q = ORMQuery().insert(LivesIn(from_=new_p._id, to=new_q._id))

    # await p.lives_in

    # print(type(p.lives_in))
    # print(id(p.lives_in.name))
    # print(p.lives_in.fetch())

    # print(p.dict(exclude={"id"}))


# if __name__ == "__main__":
#     asyncio.run(run())
