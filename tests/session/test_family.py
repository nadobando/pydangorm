from typing import Annotated, Iterable, Optional, Type

import pytest
from _pytest.fixtures import FixtureRequest
from pydiction import ANY_NOT_NONE, Contains, Matcher

from pydango.connection.session import PydangoSession
from pydango.indexes import PersistentIndex
from pydango.orm.models import BaseArangoModel, EdgeModel, VertexModel
from pydango.orm.models.base import Relation
from pydango.orm.models.edge import EdgeCollectionConfig
from pydango.orm.models.vertex import VertexCollectionConfig
from pydango.utils import init_models


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

        @staticmethod
        def brothers(e: dict, _: dict) -> bool:
            return e["connection"] == "Brother"

        @staticmethod
        def sisters(e: dict, _: dict) -> bool:
            return e["connection"] == "Sister"

        @staticmethod
        def father(e: dict, _: dict) -> bool:
            return e["connection"] == "Father"

        @staticmethod
        def mother(e: dict, _: dict) -> bool:
            return e["connection"] == "Mother"


class Sibling(EdgeModel):
    connection: str

    class Collection(EdgeCollectionConfig):
        name = "siblings"


Person.update_forward_refs()


def test_obj():
    Person.parse_obj(
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


@pytest.fixture(scope="module", autouse=True)
async def init_collections(session: PydangoSession):
    models: Iterable[Type[BaseArangoModel]] = (Person, Sibling)
    await init_models(session, *models)


def expected_person(person: Person):
    assert person.sisters
    assert person.brothers
    assert person.father
    assert person.mother
    return {
        "_id": ANY_NOT_NONE,
        "_key": ANY_NOT_NONE,
        "_rev": ANY_NOT_NONE,
        "age": person.age,
        "brothers": [
            {
                "_id": ANY_NOT_NONE,
                "_key": ANY_NOT_NONE,
                "_rev": ANY_NOT_NONE,
                "age": person.brothers[0].age,
                "brothers": None,
                "edges": None,
                "father": None,
                "mother": None,
                "name": person.brothers[0].name,
                "sisters": None,
            }
        ],
        "edges": {
            "brothers": [
                {
                    "_from": ANY_NOT_NONE,
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "_to": ANY_NOT_NONE,
                    "connection": person.edges.brothers[0].connection,
                }
            ],
            "father": {
                "_from": ANY_NOT_NONE,
                "_id": ANY_NOT_NONE,
                "_key": ANY_NOT_NONE,
                "_rev": ANY_NOT_NONE,
                "_to": ANY_NOT_NONE,
                "connection": person.edges.father.connection,
            },
            "mother": {
                "_from": ANY_NOT_NONE,
                "_id": ANY_NOT_NONE,
                "_key": ANY_NOT_NONE,
                "_rev": ANY_NOT_NONE,
                "_to": ANY_NOT_NONE,
                "connection": person.edges.mother.connection,
            },
            "sisters": [
                {
                    "_from": ANY_NOT_NONE,
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "_to": ANY_NOT_NONE,
                    "connection": person.edges.sisters[0].connection,
                },
                {
                    "_from": ANY_NOT_NONE,
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "_to": ANY_NOT_NONE,
                    "connection": person.edges.sisters[1].connection,
                },
            ],
        },
        "father": {
            "_id": ANY_NOT_NONE,
            "_key": ANY_NOT_NONE,
            "_rev": ANY_NOT_NONE,
            "age": person.father.age,
            "brothers": None,
            "edges": None,
            "father": None,
            "mother": None,
            "name": person.father.name,
            "sisters": None,
        },
        "mother": {
            "_id": ANY_NOT_NONE,
            "_key": ANY_NOT_NONE,
            "_rev": ANY_NOT_NONE,
            "age": person.mother.age,
            "brothers": None,
            "edges": None,
            "father": None,
            "mother": None,
            "name": person.mother.name,
            "sisters": None,
        },
        "name": person.name,
        "sisters": Contains(
            [
                {
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "age": person.sisters[0].age,
                    "brothers": None,
                    "edges": None,
                    "father": None,
                    "mother": None,
                    "name": person.sisters[0].name,
                    "sisters": None,
                },
                {
                    "_id": ANY_NOT_NONE,
                    "_key": ANY_NOT_NONE,
                    "_rev": ANY_NOT_NONE,
                    "age": person.sisters[1].age,
                    "brothers": None,
                    "edges": None,
                    "father": None,
                    "mother": None,
                    "name": person.sisters[1].name,
                    "sisters": None,
                },
            ]
        ),
    }


@pytest.mark.run(order=1)
@pytest.mark.asyncio
async def test_save(session: PydangoSession, request: FixtureRequest):
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

    fiona.edges = sister_edges.copy()  # type: ignore[assignment]

    jessica.sisters = [fiona]
    jessica.brothers = [ben, john]
    jessica.father = father
    jessica.mother = mother

    jessica.edges = sister_edges.copy()  # type: ignore[assignment]

    john.sisters = [fiona, jessica]
    john.brothers = [ben]
    john.father = father
    john.mother = mother

    john.edges = brother_edges.copy()  # type: ignore[assignment]

    ben.sisters = [fiona, jessica]
    ben.brothers = [john]
    ben.father = father
    ben.mother = mother

    ben.edges = brother_edges.copy()  # type: ignore[assignment]

    p = await session.save(john)
    request.config.cache.set("person_key", p.key)  # type: ignore[union-attr]

    # todo: there is currently a caveat with pydantic v1 with circular references, in pydantic v2 this is resolved
    # def traverse_recursive_fields(p, recursive_fields, visited):
    #     if isinstance(p, Sequence):
    #         for i in p:
    #             traverse_recursive_fields(i, exclude, visited)
    #
    #     else:
    #         d = p.dict(include_edges=False, by_alias=True, exclude=recursive_fields)
    #         for recursive_field in recursive_fields:
    #             attr = getattr(p, recursive_field)
    #
    #             for i in attr:
    #                 d[recursive_field] = i.dict(include_edges=False, by_alias=True, exclude=recursive_fields)
    #                 visited.add(id(i))
    #             if id(attr) in visited:
    #                 return d
    #             visited.add(id(attr))
    #             traverse_recursive_fields(attr, exclude, visited)
    #         return d
    # exclude = {
    #     "brothers",
    #     "sisters",
    # }
    # actual = traverse_recursive_fields(p, exclude, visited=set())
    # person = expected_person(p)
    # Matcher().assert_declarative_object(actual, person)


@pytest.mark.run(order=2)
async def test_get(matcher: Matcher, session: PydangoSession, request: FixtureRequest):
    _id = request.config.cache.get("person_key", None)  # type: ignore[union-attr]
    result = await session.get(Person, _id, fetch_edges=True)
    assert result
    result_dict = result.dict(by_alias=True, include_edges=True)
    person = expected_person(result)
    matcher.assert_declarative_object(result_dict, person)
