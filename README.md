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

### [Full Documentation](https://nadobando.github.io/pydangorm)

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
from pydango.index import PersistentIndex


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
from models import Person, City, Visited, LivesIn

from pydango import PydangoSession, ORMQuery
from pydango.connection.utils import get_or_create_db

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
    session = PydangoSession(db)
    # Retrieving users older than 10 years
    await session.save(person)
    assert person.id.startswith("people/")

    db_person = await session.get(Person, person.key, include_edges=True, depth=(1, 1))
    assert db_person == person

    query = (
        ORMQuery()
        .for_(Person)
        .filter(Person.age > 10)
        .sort(-Person.age)
        .return_(Person)
    )
    query_result = await query.execute(session)
    db.find(Person).filter(Person.age > 10).all()
    users = Person.query().filter(User.age > 10).all()

    # Fetching related data with edges
    visits = Visited.query().filter(Visited.rating > 4.0).join(User).all()
```

More detailed examples and scenarios can be found in the `tests` directory, which showcases modeling and querying for different use-cases like cities, families, and e-commerce operations.

## Detailed Documentation

For a comprehensive understanding of `pydangorm`'s capabilities, refer to the documentation:

- **[Query Package Documentation](./docs/query)**: Dive deep into query construction, operations, and functionalities.
- **[ORM Package Documentation](./docs/orm)**: Understand model definitions, relationships, and ORM-specific operations.
- **[Connection Package Documentation](./docs/connection)**: Explore session management, database connections, and related utilities.

## Contributing

Contributions to `pydangorm` are welcome! Please refer to the `CONTRIBUTING.md` file for guidelines.

## License

`pydangorm` is licensed under \[specific license name\]. See the `LICENSE` file for details.
