from pprint import pprint
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


def test_obj():
    a = Person.parse_obj(
        {
            "_id": "people/29887",
            "_key": "29887",
            "_rev": "_gO2JSqS---",
            "age": 35,
            "brothers": [{"_key": "29888", "_id": "people/29888", "_rev": "_gO2JSqS--_", "name": "Ben", "age": 45}],
            "father": {"_key": "29891", "_id": "people/29891", "_rev": "_gO2JSqS--C", "name": "Father", "age": 70},
            "mother": {"_key": "29892", "_id": "people/29892", "_rev": "_gO2JSqS--D", "name": "Mother", "age": 70},
            "name": "John",
            "sisters": [
                {"_key": "29889", "_id": "people/29889", "_rev": "_gO2JSqS--A", "name": "Fiona", "age": 12},
                {"_key": "29890", "_id": "people/29890", "_rev": "_gO2JSqS--B", "name": "Jessica", "age": 12},
            ],
            "edges": {
                "brothers": [
                    {
                        "_key": "29893",
                        "_id": "siblings/29893",
                        "_from": "people/29887",
                        "_to": "people/29888",
                        "_rev": "_gO2JSqW---",
                        "connection": "Brother",
                    }
                ],
                "sisters": [
                    {
                        "_key": "29894",
                        "_id": "siblings/29894",
                        "_from": "people/29887",
                        "_to": "people/29889",
                        "_rev": "_gO2JSqm---",
                        "connection": "Sister",
                    },
                    {
                        "_key": "29895",
                        "_id": "siblings/29895",
                        "_from": "people/29887",
                        "_to": "people/29890",
                        "_rev": "_gO2JSqm--_",
                        "connection": "Sister",
                    },
                ],
                "father": {
                    "_key": "29896",
                    "_id": "siblings/29896",
                    "_from": "people/29887",
                    "_to": "people/29891",
                    "_rev": "_gO2JSqq---",
                    "connection": "Father",
                },
                "mother": {
                    "_key": "29897",
                    "_id": "siblings/29897",
                    "_from": "people/29887",
                    "_to": "people/29892",
                    "_rev": "_gO2JSqq--_",
                    "connection": "Mother",
                },
            },
        }
    )


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

    pprint(p.dict(include_edges=True))
