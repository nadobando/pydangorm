## **Basic Setup**

Before you can interact with your ArangoDB database, you'll need to set up a connection. Here's a basic example:

```python title="Session Setup"
from aioarango import ArangoClient

from pydango import PydangoSession

client = ArangoClient()  # Add your connection parameters here
session = PydangoSession(
    client=client,
    database="your_database_name"
    # Add your database parameters here
)
```

## **Defining Models**

With `pydangorm`, you can easily define vertex and edge models:

```python
from typing import Annotated
import datetime

from pydango import (
    VertexModel,
    EdgeModel,
    EdgeCollectionConfig,
    VertexCollectionConfig,
    Relation,
)


class Visited(EdgeModel):
    rating: int
    on_date: datetime.date

    class Collection(EdgeCollectionConfig):
        name = "visited"


class LivesIn(EdgeModel):
    since: datetime.datetime

    class Collection(EdgeCollectionConfig):
        name = "lives_in"


class City(VertexModel):
    name: str
    population: int

    class Collection(VertexCollectionConfig):
        name = "cities"


class Person(VertexModel):
    name: str
    age: int
    lives_in: Annotated[City, Relation[LivesIn]]
    visited: Annotated[list[City], Relation[Visited]]

    class Collection(VertexCollectionConfig):
        name = "people"
```

## **CRUD Operations**

Perform basic CRUD operations using the models:

```python
# Create a new person
async def async_application():
    person = Person(name="Alice", age=30)
    person.lives_in = City(name="Buenos Aires", population=16_500_000)
    person.visited = [City(name="San Francisco", population=800_000)]
    person.edges.lives_in = LivesIn(since=datetime.datetime.now())
    person.edges.visited = [Visited(rating=5, on_date=datetime.date.today())]

    await session.save(person)

    # Read a person by their ID
    retrieved_person = await session.get(Person, person.id)

    # Update the person's age
    person.age = 31
    await session.save(person)
```

## **Running Queries**

### Simple Query

Construct and execute a simple query to retrieve all people over the age of 25:

```python
from pydango.orm import for_

query = for_(Person).filter(Person.age > 25).return_(Person)
people_over_25 = await session.execute(query)
```

### Traversal Query

Construct and execute a simple query to cities visited by people who visited the same cities of a person:

```python
from pydango.orm import traverse
from pydango import TraversalDirection

person_visited_cities = traverse(
    Person,
    edges=[Person.visited],
    start=person.id,
    depth=(1, 2),
    direction=TraversalDirection.INBOUND,
).return_(Person)
```
