## **`query.py`**

The module within the orm sub-package provides functionalities and structures for ORM-based querying in
relation to ArangoDB.
It integrates with various parts of the ORM and aids in constructing and executing queries.

#### Key Features

- Automatic binding
- `AQL` injection protection
- query building

## **`ORMQuery`**

The `ORMQuery` class is a subclass of `AQLQuery`.
It provides a Pythonic API for constructing queries for ArangoDB.

## builder helpers

### `for_()`

the `for_()` method is used to specify the target vertex/edge collection of the query.

```python
from pydango.orm import for_


for_(User).filter(User.name == "John Doe").return_(User)
```

### `traverse()`

```python
from pydango.orm import traverse
from pydango.query.expressions import IteratorExpression
from pydango.query import TraversalDirection

edge = IteratorExpression()
traverse(
    (User, edge),
    edges={"friends"},
    start="people/1",
    depth=(0, 1),
    direction=TraversalDirection.OUTBOUND,
).filter(User.name == "John Doe").return_(User)
```
