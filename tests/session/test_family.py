from typing import Annotated, Optional

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


class Person(VertexModel):
    name: str
    age: int
    brothers: Annotated[Optional[list["Person"]], Relation["Sibling"]]
    sisters: Annotated[Optional[list["Person"]], Relation["Sibling"]]
    father: Annotated[Optional["Person"], Relation["Sibling"]]
    mother: Annotated[Optional["Person"], Relation["Sibling"]]

    class Collection(VertexCollectionConfig):
        name = "people"
        indexes = [PersistentIndex(fields=["name"]), PersistentIndex(fields=["age"])]


class Sibling(EdgeModel):
    connection: str

    class Collection(EdgeCollectionConfig):
        name = "siblings"


Person.update_forward_refs()


@pytest.mark.asyncio
async def test_save(database):
    session = PydangoSession(database)
    await session.init(Person)
    await session.init(Sibling)
    fiona = Person(name="Fiona", age=12)
    jessica = Person(name="Jessica", age=12)
    ben = Person(name="Ben", age=45)
    john = Person(name="John", age=35)
    father = Person(name="Father", age=70)
    mother = Person(name="Mother", age=70)

    sister_edges = {
        Person.father: Sibling(connection="Father"),
        Person.mother: Sibling(connection="Mother"),
        Person.sisters: [Sibling(connection="Sister")],
        Person.brothers: [Sibling(connection="Brother"), Sibling(connection="Brother")],
    }

    brother_edges = {
        Person.father: Sibling(connection="Father"),
        Person.mother: Sibling(connection="Mother"),
        Person.sisters: [Sibling(connection="Sister"), Sibling(connection="Sister")],
        Person.brothers: [Sibling(connection="Brother")],
    }

    fiona.sisters = [jessica]
    fiona.brothers = [ben, john]
    fiona.father = father
    fiona.mother = mother

    fiona.edges = sister_edges.copy()

    jessica.sisters = [fiona]
    jessica.brothers = [ben, john]
    jessica.father = father
    jessica.mother = mother

    jessica.edges = sister_edges.copy()

    john.sisters = [fiona, jessica]
    john.brothers = [ben]
    john.father = father
    john.mother = mother

    john.edges = brother_edges.copy()

    ben.sisters = [fiona, jessica]
    ben.brothers = [john]
    ben.father = father
    ben.mother = mother

    ben.edges = brother_edges.copy()

    p = await session.save(john)

    print(p)
