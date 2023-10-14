# Pydango - Asynchronous Pydantic ArangoDB ORM

`pydangorm` is a Python ORM (Object-Relational Mapping) system tailored for [ArangoDB](https://www.arangodb.com/), a multi-model NoSQL database. It provides a Pythonic interface for defining models, constructing queries, and interacting with ArangoDB, abstracting away the direct complexities of database interactions.

## Features

- **Model Definitions with pydantic(v1)**: Easily define and validate your database models using `pydantic`.

  - VertexModel
  - EdgeModel

- **Pythonic Query Building**: Construct complex ArangoDB queries with a Pythonic API.

- **Session Management**: Streamlined management of database sessions and connections.

- **Collection Management**: Create indices, truncate collections, and perform other collection operations.

- **Asynchronous Support**: Perform asynchronous database operations for optimized I/O-bound tasks.

______________________________________________________________________

## [Full Documentation](https://nadobando.github.io/pydangorm)

## Installation

```shell
pip install pydangorm
```

## Quick Start & Usage Examples

### Defining Models

Using `pydangorm`, you can define vertex and edge models with ease:

```python
import datetime
from typing import Annotated

from pydango import (
    EdgeModel,
    VertexModel,
    EdgeCollectionConfig,
    VertexCollectionConfig,
    Relation,
)
from pydango.indexes import PersistentIndex


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
        indexes = [
            PersistentIndex(fields=["name"]),
            PersistentIndex(fields=["population"]),
        ]
```

### Querying Data

Construct and execute queries in a Pythonic manner:

```python
from aioarango import ArangoClient
from app.models import Person, City, Visited, LivesIn

from pydango import PydangoSession
from pydango.orm import for_
from pydango.connection.utils import get_or_create_db, deplete_cursor

person = Person(
    name="John",
    age=35,
    lives_in=City(name="Buenos Aires", population=30000000),
    visited=[
        City(name="Amsterdam", population=123),
        City(name="New Delhi", population=123),
    ],
    edges={
        Person.lives_in: LivesIn(since=datetime.datetime.now()),
        Person.visited: [
            Visited(rating=10, on_date=datetime.date.today()),
            Visited(rating=10, on_date=datetime.date.today()),
        ],
    },
)


async def main():
    db = await get_or_create_db(ArangoClient(), "app")
    session = PydangoSession(database=db)
    # Retrieving users older than 10 years
    await session.save(person)
    assert person.id.startswith("people/")

    db_person = await session.get(Person, person.key, fetch_edges=True, depth=(1, 1))
    assert db_person == person

    query = for_(Person).filter(Person.age > 10).sort(-Person.age).return_(Person)
    query_result = await session.execute(query)
    result = await deplete_cursor(query_result)
```

More detailed examples and scenarios can be found in the `tests` directory, which showcases modeling and querying for different use-cases like cities, families, and e-commerce operations.

## Detailed Documentation

For detailed documentation, please refer to the [documentation](https://nadobando.github.io/pydangorm).

## Contributing

Contributions to `pydangorm` are welcome! Please refer to the `CONTRIBUTING.md` file for guidelines.

## License

`pydangorm` is licensed under [MIT](./LICENSE). See the `LICENSE` file for details.
